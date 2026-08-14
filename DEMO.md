# On-Call Copilot — Demo Guide

This guide demonstrates the complete On-Call Copilot workflow using the included demo incidents and operational knowledge.

The demo is designed to show:

- Docker-based deployment
- PostgreSQL + pgvector
- Redis
- FastAPI backend
- Streamlit frontend
- Incident search
- Knowledge retrieval
- Agent tool usage
- Historical incident investigation
- Postmortem generation
- Streaming responses
- Health checks

---

## Table of Contents

**Setup**

1. [Demo Architecture](#1-demo-architecture)
2. [Prerequisites](#2-prerequisites)
3. [Configure Environment](#3-configure-environment)
4. [Start the Application](#4-start-the-application)
5. [Verify API Health](#5-verify-api-health)
6. [Open the Frontend](#6-open-the-frontend)
7. [Demo Data](#7-demo-data)

**Demo Queries**

8. [Query 1 — Historical Incident Search](#8-demo-query-1--historical-incident-search)
9. [Query 2 — Database Connection Pool Incident](#9-demo-query-2--database-connection-pool-incident)
10. [Query 3 — Troubleshooting Runbook](#10-demo-query-3--troubleshooting-runbook)
11. [Query 4 — Kubernetes Troubleshooting](#11-demo-query-4--kubernetes-troubleshooting)
12. [Query 5 — Payments API Incident](#12-demo-query-5--payments-api-incident)
13. [Query 6 — Incident Timeline](#13-demo-query-6--incident-timeline)
14. [Query 7 — Postmortem Draft](#14-demo-query-7--postmortem-draft)

**Direct Component Testing**

15. [Testing the Incident Tool Directly](#15-testing-the-incident-tool-directly)
16. [Testing Incident Timeline Retrieval](#16-testing-incident-timeline-retrieval)
17. [Verify Database Data](#17-verify-database-data)
18. [Verify PostgreSQL Extensions](#18-verify-postgresql-extensions)
19. [Test Retrieval Directly](#19-test-retrieval-directly)
20. [Demo Without an OpenAI API Key](#20-demo-without-an-openai-api-key)

**Reference**

21. [Full Demo Flow](#21-full-demo-flow)
22. [Recommended Short Demo](#22-recommended-short-demo)
23. [Useful Commands](#23-useful-commands)
24. [Known Demo Environment Details](#24-known-demo-environment-details)
25. [Demo Troubleshooting](#25-demo-troubleshooting)
26. [What This Demo Demonstrates](#26-what-this-demo-demonstrates)
27. [Related Documentation](#27-related-documentation)

---

## 1. Demo Architecture

The local demo runs the following services:

```text
                    Browser
                       │
                       ▼
             ┌──────────────────┐
             │   Streamlit UI   │
             │  localhost:8501  │
             └────────┬─────────┘
                      │
                      ▼
             ┌──────────────────┐
             │     FastAPI      │
             │  localhost:8002  │
             └────────┬─────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
            ▼                   ▼
     ┌─────────────┐     ┌─────────────┐
     │ PostgreSQL  │     │    Redis    │
     │ + pgvector  │     │             │
     │ localhost:  │     │ localhost:  │
     │    5434     │     │    6379     │
     └─────────────┘     └─────────────┘
```

---

## 2. Prerequisites

Install:

- Docker
- Docker Compose
- Git

For local Python development/testing:

- Python 3.11+

Clone the repository:

```bash
git clone https://github.com/Upshivam786/on-call-copilot.git
cd on-call-copilot
```

---

## 3. Configure Environment

Create the environment file:

```bash
cp .env.example .env
```

For a full LLM-powered demo, configure:

```bash
OPENAI_API_KEY=your-api-key
```

The project also contains a mock LLM mode for demonstration when an OpenAI API key is not configured.

---

## 4. Start the Application

Build the Docker images:

```bash
docker compose build
```

Start the complete stack:

```bash
docker compose up -d
```

Check the running services:

```bash
docker compose ps
```

Expected services:

- `oncall-postgres`
- `oncall-redis`
- `oncall-api`
- `oncall-ui`

---

## 5. Verify API Health

The API is exposed on host port `8002` in the current development configuration.

```bash
curl http://localhost:8002/api/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0",
  "components": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

This verifies that FastAPI is running and that PostgreSQL and Redis are both reachable.

---

## 6. Open the Frontend

Open the Streamlit UI at <http://localhost:8501>.

The interface provides:

```text
┌────────────────────────────────────────────┐
│              On-Call Copilot               │
├────────────────────────────────────────────┤
│                                            │
│  Sessions             Chat                 │
│                                            │
│  New Chat             User Query           │
│                       ─────────────        │
│  Previous sessions    Agent Response       │
│                                            │
└────────────────────────────────────────────┘
```

The frontend communicates with FastAPI rather than accessing the database directly.

---

## 7. Demo Data

The repository includes demo operational data under `demo_docs/`.

The dataset contains example runbooks and postmortems covering incidents such as:

- `HighErrorRate_payments-api`
- `PostgreSQLConnectionPoolExhausted`
- `PodCrashLoopBackOff`
- `OOMKilled_payments-api`

The demo database currently contains five incidents.

**Example incident:**

| Field | Value |
| --- | --- |
| Alert | `HighErrorRate_payments-api` |
| Severity | critical |
| Status | resolved |
| Services | `payments-api`, `payments-db` |
| Root cause | Database connection pool exhaustion from a deployment increasing connections per request without PgBouncer scaling |
| Resolution | Rolled back deployment; deployed PgBouncer; increased `max_connections` temporarily |

---

## 8. Demo Query 1 — Historical Incident Search

Open the UI and ask:

> What happened in the previous `HighErrorRate_payments-api` incidents?

The agent can use `search_incidents`, which searches historical incident records stored in PostgreSQL. The current demo data contains two matching incidents.

The results include:

- Incident
- Severity
- Status
- Services
- Start time
- Resolution time
- Root cause
- Resolution steps

---

## 9. Demo Query 2 — Database Connection Pool Incident

Ask:

> How was the database connection pool exhaustion incident resolved?

The agent can retrieve relevant historical incident information. The important incident contains:

**Root cause:** Database connection pool exhaustion from a deployment increasing connections per request without PgBouncer scaling.

**Resolution:** Rolled back deployment; deployed PgBouncer; increased `max_connections` temporarily.

This demonstrates how incident history can be used as operational context.

---

## 10. Demo Query 3 — Troubleshooting Runbook

Ask:

> How do I troubleshoot database connection pool exhaustion?

This query demonstrates the RAG pipeline. The expected retrieval flow is:

```text
User Query
    │
    ▼
Embedding
    │
    ├───────────────┐
    ▼               ▼
Vector Search   BM25 Search
    │               │
    └───────┬───────┘
            ▼
      Hybrid Ranking
            │
            ▼
       Reranking
            │
            ▼
     Relevant Chunks
            │
            ▼
      Agent Response
```

The knowledge base contains a runbook titled **Database Connection Pool Exhaustion**.

---

## 11. Demo Query 4 — Kubernetes Troubleshooting

Ask:

> Pod is in CrashLoopBackOff state, how do I debug it?

The agent can route this request toward `query_k8s` and/or `search_knowledge`.

The knowledge base contains the runbook **Kubernetes Pod CrashLoopBackOff**, which covers the operational troubleshooting context.

> **Note:** The Kubernetes tool is designed for read-only investigation.

---

## 12. Demo Query 5 — Payments API Incident

Ask:

> Why did the payments API have high error rates?

The historical incidents include multiple causes for the same alert. `HighErrorRate_payments-api` occurred because of:

1. Stripe gateway timeout during a provider outage
2. Database connection pool exhaustion during a deployment

This demonstrates an important incident-response use case: **the same alert does not necessarily imply the same root cause.**

An on-call engineer can therefore search previous incidents without assuming that the previous mitigation is automatically correct.

---

## 13. Demo Query 6 — Incident Timeline

After identifying an incident, the agent can use `get_incident_timeline`, which retrieves:

- Incident metadata
- Start time
- Resolution time
- Severity
- Services
- Root cause
- Resolution steps
- Tags
- Raw alert payload
- Linked postmortem

Example incident ID from the current demo data:

```text
efbd485b-e835-4b61-a84b-fbe32a36c709
```

This is the critical `HighErrorRate_payments-api` incident caused by database connection pool exhaustion.

---

## 14. Demo Query 7 — Postmortem Draft

Ask the agent to create a postmortem draft for an incident. The postmortem tool can produce a summary, timeline, root cause, impact, resolution, action items, lessons learned, and citations.

Example structure:

```markdown
# Postmortem: HighErrorRate_payments-api

## Summary
...

## Timeline
...

## Root Cause
...

## Impact
...

## Resolution
...

## Action Items

- [ ] Review connection handling
- [ ] Deploy PgBouncer with appropriate capacity
- [ ] Add connection pool monitoring
```

> **Note:** The output is intentionally a draft. An engineer should review the generated content before publishing it as an official postmortem.

---

## 15. Testing the Incident Tool Directly

The agent tools can also be tested independently from the UI:

```bash
python3 -c "
import asyncio
from app.agent.tools.search_incidents import SearchIncidentsTool

async def main():
    tool = SearchIncidentsTool()

    result = await tool.execute(
        alert_name='HighErrorRate_payments-api',
        limit=10,
    )

    print(result)

asyncio.run(main())
"
```

This isolates the incident-search functionality from Streamlit, agent selection, the LLM, and streaming — useful when debugging.

---

## 16. Testing Incident Timeline Retrieval

```bash
python3 -c "
import asyncio
from app.agent.tools.get_timeline import GetIncidentTimelineTool

async def main():
    tool = GetIncidentTimelineTool()

    result = await tool.execute(
        incident_id='efbd485b-e835-4b61-a84b-fbe32a36c709'
    )

    print(result)

asyncio.run(main())
"
```

This verifies the database lookup and incident-to-postmortem relationship handling.

---

## 17. Verify Database Data

Check the incidents:

```bash
docker compose exec postgres \
  psql -U oncall -d oncall_copilot \
  -c "SELECT alert_name, severity, status, root_cause FROM incidents;"
```

Check documents:

```bash
docker compose exec postgres \
  psql -U oncall -d oncall_copilot \
  -c "SELECT source_type, source_id, title FROM documents;"
```

Check chunks:

```bash
docker compose exec postgres \
  psql -U oncall -d oncall_copilot \
  -c "SELECT COUNT(*) AS total_chunks FROM chunks;"
```

The current demo database contains:

| Entity | Count |
| --- | --- |
| Documents | 5 |
| Chunks | 9 |
| Incidents | 5 |

All nine chunks in the demo dataset have stored embeddings.

---

## 18. Verify PostgreSQL Extensions

```bash
docker compose exec postgres \
  psql -U oncall -d oncall_copilot \
  -c "SELECT extname, extversion FROM pg_extension;"
```

Expected extensions include `plpgsql`, `vector`, and `pg_trgm`. The `vector` extension confirms pgvector support.

---

## 19. Test Retrieval Directly

The retrieval service can be tested independently:

```bash
python3 -c "
import asyncio
from app.retrieval.service import RetrievalService

async def main():
    service = RetrievalService(top_k=5)

    results = await service.search(
        'How do I troubleshoot database connection pool exhaustion?',
        use_query_expansion=False,
        use_reranking=False,
    )

    print(f'Found {len(results)} results')

    for i, r in enumerate(results, 1):
        print('=' * 80)
        print(f'RANK: {i}')
        print(f'TITLE: {r.title}')
        print(f'SOURCE: {r.source_type}')
        print(f'SCORE: {r.score:.4f}')
        print(f'CHUNK: {r.chunk_id}')
        print(f'CONTENT:\\n{r.content[:1000]}')

asyncio.run(main())
"
```

> **Note:** This test requires a configured embedding provider. If `OPENAI_API_KEY` is empty, the OpenAI-based `BatchEmbedder` cannot generate a query embedding through this path. The project contains a local embedding implementation, but provider switching requires compatible embedding dimensions and configuration.

---

## 20. Demo Without an OpenAI API Key

The agent includes a mock LLM mode. When `OPENAI_API_KEY` is empty, the agent initializes `MockLLMClient` instead of the OpenAI client.

The UI can therefore demonstrate the agent interaction flow without requiring a live LLM API. The response explicitly indicates that it is operating in mock mode:

```text
Based on my search, here's what I found about your query.
[This is a mock response since no OpenAI API key is configured]
```

> **Important:** Mock LLM mode should be considered a demonstration/testing mode rather than a production inference implementation.

---

## 21. Full Demo Flow

A recommended demonstration sequence:

**Step 1 — Start the stack**

```bash
docker compose up -d
```

**Step 2 — Verify services**

```bash
docker compose ps
```

**Step 3 — Verify API**

```bash
curl http://localhost:8002/api/v1/health
```

**Step 4 — Open UI**

<http://localhost:8501>

**Step 5 — Ask an incident question**

> What happened in the previous `HighErrorRate_payments-api` incidents?

**Step 6 — Ask a troubleshooting question**

> How do I troubleshoot database connection pool exhaustion?

**Step 7 — Ask a Kubernetes question**

> Pod is in CrashLoopBackOff state, how do I debug it?

**Step 8 — Generate a postmortem**

Ask for a structured postmortem based on the incident context.

---

## 22. Recommended Short Demo

For a short technical demonstration, use this sequence:

1. Show the architecture
2. Show Docker Compose services
3. Show PostgreSQL + pgvector
4. Show the Streamlit UI
5. Ask: *"What happened in the previous `HighErrorRate_payments-api` incidents?"*
6. Explain that the agent searches historical incident data
7. Ask: *"How do I troubleshoot database connection pool exhaustion?"*
8. Explain: Vector Search + BM25 + Hybrid Ranking + Reranking
9. Show the incident timeline tool
10. Show postmortem generation
11. Show [TESTING.md](./TESTING.md) and [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) to demonstrate engineering/debugging work

This covers DevOps/SRE knowledge, AI/RAG engineering, backend engineering, Docker, PostgreSQL, and agentic workflows.

---

## 23. Useful Commands

| Purpose | Command |
| --- | --- |
| View all services | `docker compose ps` |
| View API logs | `docker compose logs -f api` |
| View UI logs | `docker compose logs -f ui` |
| View PostgreSQL logs | `docker compose logs -f postgres` |
| Restart API | `docker compose restart api` |
| Restart UI | `docker compose restart ui` |
| Rebuild | `docker compose build` |
| Rebuild and restart | `docker compose up -d --build` |
| Stop everything | `docker compose down` |

---

## 24. Known Demo Environment Details

The current development environment uses:

| Component | Host Port | Container Port |
| --- | --- | --- |
| Streamlit | 8501 | 8501 |
| FastAPI | 8002 | 8000 |
| PostgreSQL | 5434 | 5432 |
| Redis | 6379 | 6379 |

The API uses port `8002` on the host because port `8000` was already occupied by another Docker container during development.

Inside Docker Compose, the UI communicates with `http://api:8000` rather than `http://localhost:8002`. This distinction is important when debugging container networking.

---

## 25. Demo Troubleshooting

**If the UI cannot create a session:**

```bash
docker compose exec ui \
  python -c "import requests; print(requests.get('http://api:8000/api/v1/health').text)"
```

If this returns a healthy response, Docker networking between UI and API is working.

**If port 8000 is already allocated:**

```bash
sudo lsof -i :8000
```

Find the container using the port:

```bash
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}"
```

Then either stop the conflicting container or keep the On-Call Copilot API exposed on host port `8002`.

For additional troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

---

## 26. What This Demo Demonstrates

The project demonstrates a complete AI-assisted DevOps workflow:

```text
Operational Documentation
          │
          ▼
       Ingestion
          │
          ▼
      Embeddings
          │
          ▼
 PostgreSQL + pgvector
          │
          ▼
     Hybrid Search
          │
          ▼
       Reranking
          │
          ▼
      Agent Tools
          │
          ▼
  Incident Investigation
          │
          ▼
      AI Synthesis
          │
          ▼
   Streaming Response
          │
          ▼
       Engineer
```

The goal is not to replace the on-call engineer. The goal is to reduce the time required to:

- Find relevant operational knowledge
- Understand previous incidents
- Investigate common failure patterns
- Retrieve troubleshooting procedures
- Assemble incident context
- Produce a structured postmortem draft

---

## 27. Related Documentation

| Document | Purpose |
| --- | --- |
| [README.md](./README.md) | Project overview, installation, configuration, and project structure |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Detailed technical architecture and component interactions |
| [TESTING.md](./TESTING.md) | Testing strategy and validation commands |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | Issues encountered during development and their resolutions |
