# Troubleshooting & Engineering Notes

This document records the main issues encountered while developing and validating On-Call Copilot, including the investigation process, root cause, and resolution.

The purpose is to document practical debugging rather than only the final working state.

---

## Table of Contents

1. [PostgreSQL Role Error](#1-postgresql-role-error)
2. [Alembic Password Authentication Failure](#2-alembic-password-authentication-failure)
3. [Incorrect Database Column Assumption](#3-incorrect-database-column-assumption)
4. [Incorrect Document Column Assumption](#4-incorrect-document-column-assumption)
5. [Docker API Port Conflict](#5-docker-api-port-conflict)
6. [Docker Image Build Failure](#6-docker-image-build-failure)
7. [Streamlit UI Could Not Reach API](#7-streamlit-ui-could-not-reach-api)
8. [API Path Duplication Bug](#8-api-path-duplication-bug)
9. [Missing OpenAI API Key During Retrieval Test](#9-missing-openai-api-key-during-retrieval-test)
10. [Missing Postmortem Relationship](#10-missing-postmortem-relationship)
11. [Postmortem Date Formatting Bug](#11-postmortem-date-formatting-bug)
12. [Direct Retrieval Testing vs End-to-End Demo Mode](#12-direct-retrieval-testing-vs-end-to-end-demo-mode)
- [Debugging Workflow Used](#debugging-workflow-used)
- [Key Engineering Lessons](#key-engineering-lessons)
- [Final Status](#final-status)

---

## 1. PostgreSQL Role Error

### Symptom

The initial PostgreSQL verification used:

```bash
docker compose exec postgres psql -U postgres -d oncall -c "SELECT extname FROM pg_extension;"
```

It failed with:

```text
FATAL: role "postgres" does not exist
```

### Investigation

The PostgreSQL configuration in `docker-compose.yml` defined:

```yaml
POSTGRES_DB: oncall_copilot
POSTGRES_USER: oncall
POSTGRES_PASSWORD: oncall_dev_password
```

Therefore, the configured database user was `oncall`, not `postgres`.

### Resolution

The correct command was:

```bash
docker compose exec postgres \
  psql -U oncall -d oncall_copilot \
  -c "SELECT extname, extversion FROM pg_extension;"
```

Verified extensions: `plpgsql`, `vector`, `pg_trgm`.

### Lesson

Always verify the actual database credentials from the Compose configuration before assuming the default PostgreSQL role exists.

---

## 2. Alembic Password Authentication Failure

### Symptom

Running `alembic current` failed with:

```text
asyncpg.exceptions.InvalidPasswordError:
password authentication failed for user "oncall"
```

### Investigation

The project had different database URLs in different locations.

`.env` contained:

```bash
DATABASE_URL=postgresql+asyncpg://oncall:oncall_dev_password@localhost:5434/oncall_copilot
```

But `alembic.ini` contained:

```ini
sqlalchemy.url = postgresql+asyncpg://oncall:oncall_dev_password@localhost:5432/oncall_copilot
```

Additionally, `echo "$DATABASE_URL"` returned nothing. The Alembic environment reads the database URL from the environment when it is available.

### Resolution

The correct host-side PostgreSQL port was `5434`. The migration command was executed with:

```bash
DATABASE_URL='postgresql+asyncpg://oncall:oncall_dev_password@localhost:5434/oncall_copilot' \
  alembic current
```

Result:

```text
0001_initial (head)
```

### Lesson

Docker internal ports and host-mapped ports are different:

| Context | Address |
| --- | --- |
| Host-side tools | `localhost:5434` |
| Application container | `postgres:5432` |

---

## 3. Incorrect Database Column Assumption

### Symptom

The following query failed:

```sql
SELECT id, title, status FROM incidents;
```

PostgreSQL returned:

```text
ERROR: column "title" does not exist
```

### Investigation

Instead of assuming the schema, the table definition was inspected:

```bash
docker compose exec postgres \
  psql -U oncall -d oncall_copilot \
  -c "\d incidents"
```

The actual schema contained fields such as `id`, `alert_name`, `severity`, `status`, `started_at`, `resolved_at`, `root_cause`, `resolution_steps`, `services`, `tags`, `raw_payload`, and `created_at`. There was no `title` column.

### Resolution

The query was changed to use the actual schema:

```sql
SELECT alert_name, severity, status, root_cause
FROM incidents
ORDER BY created_at;
```

### Lesson

When debugging a database query failure, inspect the actual schema instead of guessing column names. Useful PostgreSQL commands:

```sql
\d table_name
\dt
```

---

## 4. Incorrect Document Column Assumption

### Symptom

The following query failed:

```sql
SELECT id, filename FROM documents;
```

with:

```text
ERROR: column "filename" does not exist
```

### Investigation

The table schema was inspected:

```bash
docker compose exec postgres \
  psql -U oncall -d oncall_copilot \
  -c "\d documents"
```

The actual document model uses `source_type`, `source_id`, `title`, `content`, `metadata`, `created_at`, and `updated_at`.

### Resolution

The query was changed to:

```sql
SELECT
    source_type,
    source_id,
    title,
    length(content) AS content_length
FROM documents
ORDER BY created_at;
```

This successfully displayed the ingested runbooks and postmortems.

### Lesson

The database model is the source of truth for SQL queries.

---

## 5. Docker API Port Conflict

### Symptom

Starting the API container failed with:

```text
Bind for 0.0.0.0:8000 failed: port is already allocated
```

### Investigation

The host port was checked:

```bash
sudo lsof -i :8000
```

The result showed Docker was already using port 8000. The running containers were then inspected:

```bash
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}"
```

Another project was already exposing `0.0.0.0:8000->8000/tcp`.

### Resolution

The On-Call Copilot API was mapped to host port `8002` while keeping port `8000` inside the container:

```yaml
ports:
  - "8002:8000"
```

The API was then verified:

```bash
curl http://localhost:8002/api/v1/health
```

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

### Lesson

When running multiple Docker projects on the same development machine, host ports can conflict even though containers use isolated networking.

---

## 6. Docker Image Build Failure

### Symptom

The API image initially failed during:

```dockerfile
RUN pip install --no-cache-dir ".[dev]"
```

The build reported:

```text
error: package directory 'app' does not exist
```

### Root Cause

The package installation command was executed before the application source code had been copied into the image. The Dockerfile initially contained:

```dockerfile
COPY pyproject.toml .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[dev]"
```

Only after that did it contain:

```dockerfile
COPY app/ ./app/
```

The package metadata expected the `app` package to exist during installation.

### Resolution

The Dockerfile was changed so that the application package is available before installing the local package. The resulting build completed successfully.

### Lesson

Docker build order matters. If `pyproject.toml` defines a local package such as `packages = ["app"]`, then that package must exist in the image when running `pip install .`.

---

## 7. Streamlit UI Could Not Reach API

### Symptom

The Streamlit UI initially showed:

```text
Failed to create session:
HTTPConnectionPool(host='localhost', port=8000)
```

The API was actually running on host port `8002`.

### Investigation

The Streamlit application originally contained:

```python
API_URL = "http://localhost:8000/api/v1"
```

However, the UI itself was running inside a Docker container. Inside the UI container, `localhost` means the UI container itself — not the host, and not the API container.

### Correct Docker Networking

Docker Compose provides service-name DNS. The API service is named `api`, so the UI container should connect to `http://api:8000` — not `http://localhost:8002`.

### Verification

The connection was tested directly from inside the UI container:

```bash
docker compose exec ui python -c \
  "import requests; print(requests.get('http://api:8000/api/v1/health').text)"
```

The request successfully returned:

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

### Resolution

The Streamlit application was changed to read the API URL from the environment:

```python
API_URL = os.getenv("API_URL", "http://localhost:8000") + "/api/v1"
```

Docker Compose provides:

```yaml
environment:
  - API_URL=http://api:8000
```

The final communication path is:

```text
Browser
   │
   ▼
localhost:8501
   │
   ▼
Streamlit container
   │
   │ http://api:8000
   ▼
FastAPI container
   │
   ├──────► PostgreSQL
   │
   └──────► Redis
```

### Lesson

`localhost` means different things depending on where the request originates. This is one of the most common problems when containerizing multi-service applications.

---

## 8. API Path Duplication Bug

### Symptom

The UI initially generated requests such as:

```text
/api/v1/api/v1/chat/sessions
```

### Investigation

The application had:

```python
API_URL = "http://localhost:8000/api/v1"
```

and another change accidentally appended `/api/v1` again, resulting in `http://localhost:8000/api/v1/api/v1`.

### Resolution

The API base URL was normalized to contain `/api/v1` only once:

```python
API_URL = os.getenv("API_URL", "http://localhost:8000") + "/api/v1"
```

Individual requests then use:

```python
f"{API_URL}/chat/sessions"
```

Result: `http://api:8000/api/v1/chat/sessions`

### Lesson

Keep the API version prefix in exactly one place.

---

## 9. Missing OpenAI API Key During Retrieval Test

### Symptom

A direct retrieval test failed with:

```text
openai.OpenAIError: Missing credentials.
```

### Investigation

The environment contained an empty `OPENAI_API_KEY`. The retrieval service creates a `BatchEmbedder`, whose default path initializes:

```python
openai.AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY
)
```

Without an API key, the OpenAI client cannot create query embeddings.

### Important Observation

The project does contain a local embedding implementation:

```python
class LocalEmbedder:
    ...


def get_embedder():
    if settings.OPENAI_API_KEY:
        return BatchEmbedder()
    else:
        return LocalEmbedder()
```

However, the current `RetrievalService` directly initializes:

```python
self.embedder = embedder or BatchEmbedder()
```

Therefore the local fallback is not automatically used by this retrieval path.

### Current Status

This is a known limitation. The stored demo embeddings and the local embedding model also need to use compatible dimensions before the local fallback can be used against the existing pgvector data.

### Lesson

Having a fallback implementation in a codebase does not automatically mean every execution path uses it. Fallback logic must be wired into the actual dependency path.

---

## 10. Missing Postmortem Relationship

### Observation

The database contains postmortem documents, but the seeded incidents currently have `postmortem_id = NULL`. This was verified with:

```sql
SELECT
    alert_name,
    severity,
    postmortem_id
FROM incidents
ORDER BY started_at;
```

### Effect

The timeline tool successfully retrieves incident details, but returns `postmortem = None` when the incident has no linked postmortem.

### Current Status

This does not prevent incident investigation or postmortem generation. It simply means the current demo seed data does not establish a database relationship between those incidents and postmortem documents.

### Lesson

A document existing in the knowledge base is different from having a relational link between that document and an incident.

---

## 11. Postmortem Date Formatting Bug

### Symptom

The generated postmortem displayed the literal template expression instead of the actual date:

```text
**Date:** {datetime.now().strftime('%Y-%m-%d')}
```

### Root Cause

The postmortem template was created as an f-string, but the date expression was escaped using double braces:

```python
**Date:** {{datetime.now().strftime('%Y-%m-%d')}}
```

Double braces in an f-string produce literal braces.

### Correct Implementation

```python
**Date:** {datetime.now().strftime('%Y-%m-%d')}
```

### Lesson

When using f-strings, distinguish between `{expression}` for evaluation and `{{expression}}` for literal braces.

---

## 12. Direct Retrieval Testing vs End-to-End Demo Mode

The project has two different execution paths that should not be confused.

### Retrieval Test

A direct retrieval test executes:

```text
Query
  ↓
Embedding
  ↓
Vector Search
  +
BM25
  ↓
Hybrid Ranking
  ↓
Results
```

This requires a working query embedding provider.

### Demo Agent

The agent can operate with:

```text
No OPENAI_API_KEY
        ↓
    Mock LLM
        ↓
 Tool Selection
        ↓
   Agent Tool
        ↓
Mock Final Response
```

Therefore, a successful demo-mode UI interaction does not prove that production OpenAI-based retrieval is configured.

### Lesson

Always test individual layers independently. A working UI can hide failures in lower-level components if the application has fallback behavior.

---

## Debugging Workflow Used

The general debugging workflow for this project was:

```text
1. Reproduce the error
        ↓
2. Read the exact error message
        ↓
3. Inspect configuration
        ↓
4. Inspect Docker/container state
        ↓
5. Inspect database schema when relevant
        ↓
6. Test the smallest failing component
        ↓
7. Apply the smallest targeted fix
        ↓
8. Re-run the failing command
        ↓
9. Verify the complete path
```

Useful commands used during troubleshooting:

**Docker**

```bash
docker compose ps
docker ps
docker compose logs
docker compose exec
docker compose config
docker compose build
docker compose up -d
```

**Database inspection**

```sql
\d table_name
\dt
SELECT ...
```

**Network/port inspection**

```bash
sudo lsof -i :8000
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}"
```

**Application verification**

```bash
curl http://localhost:8002/api/v1/health
```

---

## Key Engineering Lessons

### 1. Container networking

| Direction | Address |
| --- | --- |
| Container → container | `api:8000` |
| Host → container | `localhost:8002` |

### 2. Configuration consistency

Keep database configuration consistent between Docker Compose, `.env`, Alembic, and application configuration.

### 3. Inspect before changing

Instead of guessing, `\d incidents` is better than repeatedly trying random SQL column names.

### 4. Test components independently

The project was validated at multiple levels:

```text
Infrastructure
    ↓
  Database
    ↓
    Data
    ↓
 Retrieval
    ↓
Agent Tools
    ↓
    API
    ↓
Docker Networking
    ↓
Streamlit UI
```

### 5. Fallbacks must be integrated

A local embedding implementation existing in the repository is not enough. The production retrieval path must explicitly select the correct embedder based on configuration.

---

## Final Status

The major infrastructure, database, agent-tool, API, Docker networking, and Streamlit UI paths were successfully debugged and verified.

Known improvements remain around:

- Local embedding fallback integration
- Embedding dimension compatibility
- Incident → postmortem relationships
- Postmortem date formatting
- Production LLM integration
- Evaluation harness
- Authentication and authorization

These are tracked separately from the core demo functionality.

---

## Related Documentation

| Document | Purpose |
| --- | --- |
| [README.md](./README.md) | Project overview and setup |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Detailed system architecture |
| [DEMO.md](./DEMO.md) | End-to-end application demonstration |
| [TESTING.md](./TESTING.md) | Test commands and verification results |
