# Testing & Verification

This document records the testing and manual verification performed for the On-Call Copilot project.

The goal is to verify the system layer-by-layer instead of relying only on an end-to-end UI test.

---

## 1. Automated Tests

The project includes automated tests for the main application components.

Run:

```bash
pytest

The test suite covers areas including:

Database models
Retrieval logic
Agent tools
API endpoints

Example test structure:

tests/
├── test_models.py
├── test_retrieval.py
├── test_agent.py
└── test_api.py
2. Docker Compose Verification

The application runs as multiple Docker Compose services.

Check the running containers:

docker compose ps

The expected application services are:

oncall-postgres
oncall-redis
oncall-api
oncall-ui

PostgreSQL and Redis should report a healthy status.

3. PostgreSQL Verification

The project uses PostgreSQL with pgvector.

Connect to the database:

docker compose exec postgres \
psql -U oncall -d oncall_copilot

Check the database tables:

\dt

The project currently uses tables including:

chat_messages
chat_sessions
chunks
documents
incidents
4. Database Migration Verification

Alembic is used for database migrations.

Check the current migration:

DATABASE_URL='postgresql+asyncpg://oncall:oncall_dev_password@localhost:5434/oncall_copilot' \
alembic current

The verified migration state was:

0001_initial (head)

This confirms that the initial database schema has been applied.

5. Incident Data Verification

The demo environment contains historical incident records.

Query them using:

docker compose exec postgres \
psql -U oncall -d oncall_copilot \
-c "SELECT alert_name, severity, status, root_cause FROM incidents ORDER BY created_at;"

The verified demo incidents included:

HighErrorRate_payments-api
PostgreSQLConnectionPoolExhausted
PodCrashLoopBackOff
HighErrorRate_payments-api
OOMKilled_payments-api

The incidents represent different operational failure scenarios such as:

Database connection pool exhaustion
External payment provider outage
Kubernetes configuration problems
Memory/resource problems
6. Document Verification

The knowledge base contains runbooks and postmortem documents.

Query the documents:

docker compose exec postgres \
psql -U oncall -d oncall_copilot \
-c "SELECT source_type, source_id, title, length(content) AS content_length FROM documents ORDER BY created_at;"

The verified documents included:

INC-2026-0142 Payments API Outage
INC-2026-0087 Database Pool Exhaustion Cascade
Kubernetes Pod CrashLoopBackOff
Payments API High Error Rate
Database Connection Pool Exhaustion
7. Chunk Verification

Documents are split into chunks before retrieval.

Check the total number of chunks:

docker compose exec postgres \
psql -U oncall -d oncall_copilot \
-c "SELECT COUNT(*) AS total_chunks FROM chunks;"

The verified database contained:

9 chunks

Chunk distribution was verified with:

SELECT
    d.title,
    COUNT(c.id) AS chunk_count
FROM documents d
LEFT JOIN chunks c ON c.document_id = d.id
GROUP BY d.id, d.title
ORDER BY d.created_at;

Current distribution:

INC-2026-0142 Payments API Outage               1
INC-2026-0087 Database Pool Exhaustion Cascade  2
Kubernetes Pod CrashLoopBackOff                 2
Payments API High Error Rate                    2
Database Connection Pool Exhaustion             2
8. Embedding Verification

Each stored chunk should contain an embedding.

The following query was used:

docker compose exec postgres \
psql -U oncall -d oncall_copilot -c "
SELECT
    COUNT(*) AS total_chunks,
    COUNT(*) FILTER (
        WHERE embedding IS NOT NULL AND embedding <> ''
    ) AS chunks_with_embeddings,
    COUNT(*) FILTER (
        WHERE embedding IS NULL OR embedding = ''
    ) AS chunks_without_embeddings
FROM chunks;
"

Verified result:

total_chunks             9
chunks_with_embeddings   9
chunks_without_embeddings 0

This confirms that all currently stored chunks have embedding data.

9. Incident Search Tool Verification

The search_incidents agent tool was tested independently from the UI.

Example:

from app.agent.tools.search_incidents import SearchIncidentsTool

result = await SearchIncidentsTool().execute(
    alert_name="HighErrorRate_payments-api",
    limit=10,
)

The search successfully returned two historical incidents for:

HighErrorRate_payments-api

The returned incidents had different root causes:

Incident 1
Root cause:
Stripe gateway timeout during provider outage

Resolution:

Enabled circuit breaker;
routed to backup gateway;
Stripe recovered
Incident 2
Root cause:
Database connection pool exhaustion from deployment increasing
connections per request without PgBouncer scaling

Resolution:

Rolled back deployment;
deployed PgBouncer;
increased max_connections temporarily

This verifies that the incident search layer can retrieve historical operational knowledge from PostgreSQL.

10. Incident Timeline Tool Verification

The get_incident_timeline tool was tested using a real incident UUID.

The tool successfully returned:

Incident ID
Alert name
Severity
Status
Affected services
Start time
Resolution time
Root cause
Resolution steps
Tags
Raw alert payload

This verifies that an incident can be investigated in more detail after being discovered through incident search.

11. Postmortem Generation Verification

The draft_postmortem tool was also tested independently.

It successfully generated a structured postmortem containing:

Summary
Timeline
Root Cause
Impact
Resolution
Action Items
Lessons Learned

The generated document is treated as a draft and requires human review before being considered an official postmortem.

12. FastAPI Health Check

The FastAPI backend exposes a health endpoint.

Because port 8000 was already occupied on the development machine, the API is currently exposed as:

Host:      8002
Container: 8000

Health check:

curl http://localhost:8002/api/v1/health

Verified response:

{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0",
  "components": {
    "database": "healthy",
    "redis": "healthy"
  }
}

This confirms that:

FastAPI is running
PostgreSQL connectivity is healthy
Redis connectivity is healthy
13. Streamlit UI Verification

The Streamlit frontend runs on:

http://localhost:8501

Check the container:

docker compose ps

The UI service should show:

0.0.0.0:8501->8501/tcp

The UI communicates with the FastAPI backend through the Docker Compose network.

Inside Docker:

Streamlit
   ↓
http://api:8000
   ↓
FastAPI

From the host:

Browser
   ↓
http://localhost:8501
14. Docker Network Verification

The UI-to-API connection was explicitly tested from inside the UI container:

docker compose exec ui python -c \
"import requests; print(requests.get('http://api:8000/api/v1/health').text)"

The FastAPI health response was returned successfully.

This verified that Docker service-to-service networking was working correctly.

15. Demo Mode Verification

The application supports a mock/demo mode when no OpenAI API key is configured.

Current configuration:

OPENAI_API_KEY=

When the API key is missing, the agent initializes the mock LLM client.

The UI can therefore be started without requiring an OpenAI API key.

A test query was successfully submitted through the Streamlit UI:

What happened in the previous HighErrorRate_payments-api incidents?

The application returned a mock streaming response.

16. Current Known Limitation

The current retrieval service directly initializes the OpenAI-based BatchEmbedder.

Therefore, a direct retrieval test without an OpenAI API key currently fails during query embedding generation.

The project already contains a LocalEmbedder implementation, but the local embedding model currently produces a different embedding dimension from the embeddings stored in the existing database.

This is a known engineering limitation and is planned for a future improvement.

Verification Summary

The following layers have been independently verified:

Component	Verification
Docker Compose	Verified
PostgreSQL	Verified
Redis	Verified
Alembic migration	Verified
Demo incidents	Verified
Documents	Verified
Chunking	Verified
Stored embeddings	Verified
Incident search tool	Verified
Incident timeline tool	Verified
Postmortem generation	Verified
FastAPI health	Verified
Streamlit UI	Verified
Docker UI → API networking	Verified
Mock/Demo mode	Verified
Full OpenAI retrieval without API key	Known limitation
Testing Philosophy

The project was tested layer-by-layer:

Infrastructure
      ↓
Database
      ↓
Migration
      ↓
Seed Data
      ↓
Document Ingestion
      ↓
Agent Tools
      ↓
API
      ↓
Docker Networking
      ↓
Frontend
      ↓
End-to-End Interaction

This approach helped isolate configuration, database, networking, and application-level issues during development.
