# On-Call Copilot

> Production-style **RAG + agentic incident response assistant** for DevOps/SRE workflows.

On-Call Copilot is an AI-powered incident response assistant that helps on-call engineers investigate alerts, search historical incidents, retrieve operational knowledge, inspect Kubernetes resources, and generate structured postmortem drafts.

The project combines RAG, hybrid retrieval, agentic tools, PostgreSQL/pgvector, Redis, FastAPI, Streamlit, Docker Compose, and automated testing into a single incident-response workflow.

---

## Table of Contents

- [Why This Project?](#why-this-project)
- [Architecture](#architecture)
- [Retrieval Flow](#retrieval-flow)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Running Locally](#running-locally)
- [Example Workflow](#example-workflow)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Known Limitations](#known-limitations)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Documentation](#documentation)
- [License](#license)

---

## Why This Project?

During a production incident, engineers often need to search across:

- Runbooks
- Previous incidents
- Postmortems
- Operational documentation
- Alert information
- Kubernetes resources
- Previous resolution procedures

On-Call Copilot provides a conversational interface for questions such as:

- *"What happened in the previous `HighErrorRate_payments-api` incidents?"*
- *"What caused the database connection pool exhaustion incident?"*
- *"How was the payments outage resolved?"*
- *"A Kubernetes pod is in CrashLoopBackOff. What should I check?"*
- *"Draft a postmortem for this incident."*

The system retrieves relevant information and uses specialized tools to support incident investigation.

---

## Architecture

```text
                     ┌──────────────────────┐
                     │     Streamlit UI     │
                     │        :8501         │
                     └──────────┬───────────┘
                                │
                          HTTP / SSE
                                │
                                ▼
                     ┌──────────────────────┐
                     │     FastAPI API      │
                     │        :8002         │
                     └──────────┬───────────┘
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ▼                  ▼                  ▼
      ┌────────────┐    ┌──────────────┐    ┌────────────┐
      │   Agent    │    │  Retrieval   │    │    Chat    │
      │    Loop    │    │   Service    │    │  Sessions  │
      └─────┬──────┘    └──────┬───────┘    └─────┬──────┘
            │                  │                  │
            ▼                  ▼                  ▼
      Agent Tools         PostgreSQL             Redis
                          + pgvector
```

For a detailed architecture explanation, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Retrieval Flow

**Ingestion**

```text
Operational Documents
        │
        ▼
   Document Loader
        │
        ▼
      Chunking
        │
        ▼
     Embeddings
        │
        ▼
 PostgreSQL + pgvector
```

**Query**

```text
User Query
    │
    ▼
Query Embedding
    │
    ├───────────────┐
    ▼               ▼
Vector Search   Full-text Search
    │               │
    └───────┬───────┘
            ▼
     Hybrid Retrieval
            │
            ▼
  Cross-Encoder Reranking
            │
            ▼
        Agent Loop
            │
            ▼
      Tool Execution
            │
            ▼
      Final Response
            │
            ▼
       SSE Streaming
            │
            ▼
       Streamlit UI
```

---

## Key Features

### Hybrid RAG Retrieval

The retrieval layer combines:

- Vector similarity search using pgvector
- PostgreSQL full-text search
- Weighted score combination
- Cross-encoder reranking
- Optional query expansion

This helps with both semantic questions and exact operational terminology.

### Historical Incident Search

Incident records contain:

- Alert name
- Severity
- Status
- Affected services
- Start / resolution timestamps
- Root cause
- Resolution steps
- Tags
- Raw alert payload

For example, asking *"What happened in previous `HighErrorRate_payments-api` incidents?"* lets the assistant retrieve previous occurrences and their root causes.

### Agentic Tool Use

The ReAct-style agent has access to specialized tools:

| Tool | Purpose |
| --- | --- |
| `search_knowledge` | Search operational documents |
| `search_incidents` | Search historical incidents |
| `get_incident_timeline` | Retrieve detailed incident information |
| `query_k8s` | Read-only Kubernetes investigation |
| `draft_postmortem` | Generate a structured postmortem draft |

### Streaming Chat

The FastAPI backend provides a streaming chat endpoint using Server-Sent Events (SSE), so the Streamlit UI receives agent and tool activity progressively instead of waiting for the entire response.

### Postmortem Drafting

The postmortem tool generates a structured draft containing:

- Summary
- Timeline
- Root cause
- Impact
- Resolution
- Action items
- Lessons learned
- Optional citations

The generated document is a **draft** and should be reviewed by an engineer before publishing.

---

## Technology Stack

| Area | Technology |
| --- | --- |
| Language | Python 3.11 |
| API | FastAPI |
| Frontend | Streamlit |
| Database | PostgreSQL 16 |
| Vector search | pgvector |
| Cache / sessions | Redis |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Retrieval | Vector + PostgreSQL full-text |
| Reranking | Cross-encoder |
| Agent | Custom ReAct-style loop |
| Streaming | Server-Sent Events |
| Containers | Docker |
| Orchestration | Docker Compose |
| Testing | pytest / pytest-asyncio / httpx |

---

## Project Structure

```text
on-call-copilot/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── api/
│   │   └── routes/
│   │       ├── health.py
│   │       ├── chat.py
│   │       └── ingest.py
│   │
│   ├── models/
│   │   ├── documents.py
│   │   ├── chunks.py
│   │   ├── incidents.py
│   │   └── chat.py
│   │
│   ├── ingestion/
│   │   ├── loaders/
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   └── pipeline.py
│   │
│   ├── retrieval/
│   │   ├── service.py
│   │   ├── strategies.py
│   │   └── reranker.py
│   │
│   ├── agent/
│   │   ├── loop.py
│   │   ├── prompts.py
│   │   ├── state.py
│   │   └── tools/
│   │       ├── search_knowledge.py
│   │       ├── search_incidents.py
│   │       ├── get_timeline.py
│   │       ├── query_k8s.py
│   │       └── draft_postmortem.py
│   │
│   └── utils/
│
├── alembic/
├── alembic.ini
├── demo_docs/
├── evals/
├── scripts/
├── tests/
├── ui/
│   └── streamlit_app.py
│
├── Dockerfile
├── Dockerfile.ui
├── docker-compose.yml
├── pyproject.toml
├── .env.example
│
├── ARCHITECTURE.md
├── DEMO.md
├── README.md
├── TESTING.md
└── TROUBLESHOOTING.md
```

---

## Running Locally

### Prerequisites

- Docker
- Docker Compose
- Python 3.11+
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Upshivam786/on-call-copilot.git
cd on-call-copilot
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in the required environment variables. **Do not commit `.env`.**

### 3. Start PostgreSQL and Redis

```bash
docker compose up -d postgres redis
docker compose ps
```

### 4. Run database migrations

For the current host development setup:

```bash
DATABASE_URL='postgresql+asyncpg://oncall:oncall_dev_password@localhost:5434/oncall_copilot' \
  alembic upgrade head
```

### 5. Seed demo data

```bash
python3 scripts/seed_demo_data.py
```

### 6. Ingest demo documents

```bash
python3 scripts/ingest.py --source markdown --path ./demo_docs
```

### 7. Start the application

```bash
docker compose up -d
```

Current Docker Compose host ports:

| Service | Host Port |
| --- | --- |
| API | 8002 |
| Streamlit | 8501 |
| PostgreSQL | 5434 |
| Redis | 6379 |

### 8. Verify the API

```bash
curl http://localhost:8002/api/v1/health
```

Expected response:

```json
{ "status": "healthy" }
```

### 9. Open the UI

<http://localhost:8501>

The Streamlit container communicates with FastAPI internally at `http://api:8000`.

---

## Example Workflow

Start the application and ask:

> What happened in the previous `HighErrorRate_payments-api` incidents?

The incident search tool retrieves previous occurrences. The current demo dataset contains examples including:

- `HighErrorRate_payments-api`
- `PostgreSQLConnectionPoolExhausted`
- `PodCrashLoopBackOff`
- `OOMKilled_payments-api`

For example, one historical `HighErrorRate_payments-api` incident has the root cause:

> Database connection pool exhaustion from a deployment increasing connections per request without PgBouncer scaling

with resolution steps including:

> Rolled back deployment; deployed PgBouncer; increased `max_connections` temporarily

The incident timeline tool can then retrieve additional incident details.

See [DEMO.md](./DEMO.md) for the complete walkthrough.

---

## Verification

The project was manually tested across multiple layers. Verified during development:

- Docker image builds
- Docker Compose startup
- PostgreSQL health
- Redis health
- Alembic migration state
- Demo incident data
- Document ingestion
- Chunk creation
- Embedding storage
- Incident search
- Incident timeline retrieval
- Postmortem generation
- FastAPI health endpoint
- Streamlit UI
- Docker UI → API networking
- Mock/demo LLM mode

Detailed commands and observed results are documented in [TESTING.md](./TESTING.md).

---

## Troubleshooting

Several real integration issues were encountered during development:

| Problem | Cause | Fix |
| --- | --- | --- |
| Docker package build failure | Application package unavailable during dependency installation | Corrected Docker build configuration |
| Alembic authentication failure | `DATABASE_URL` / PostgreSQL host-port mismatch | Used `localhost:5434` for host-side Alembic |
| API port 8000 already occupied | Another Docker application was using port 8000 | Mapped the API to host port 8002 |
| Streamlit → `localhost:8000` failed | The UI runs inside a Docker container | Changed container communication to `http://api:8000` |

Detailed troubleshooting steps and commands are available in [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

---

## Known Limitations

This is a production-style portfolio/learning project, **not** a production incident-management platform.

- **Embedding provider** — The retrieval service directly initializes the OpenAI-based embedder. A local embedding implementation exists, but transparent provider switching still requires additional integration.
- **Embedding dimensions** — Dimensions must remain consistent between the embedding model and PostgreSQL vector storage.
- **Demo data relationships** — The current demo incidents and documents do not establish every possible incident → postmortem relationship.
- **Authentication** — Authentication and authorization are not currently implemented.
- **Kubernetes** — Kubernetes functionality is intended for read-only diagnostics. A production deployment would require appropriate RBAC, authentication, auditing, and security controls.
- **Mock LLM mode** — When no OpenAI API key is configured, the agent operates in demo/mock mode. This demonstrates the application flow but does not provide real LLM-generated responses.

---

## Testing

```bash
pytest
```

Additional manual verification commands are available in [TESTING.md](./TESTING.md).

---

## Roadmap

- [ ] Clean local embedding integration
- [ ] Improved citation tracking
- [ ] Authentication and RBAC
- [ ] PagerDuty integration
- [ ] Slack integration
- [ ] Kubernetes observability integration
- [ ] LLM observability with Langfuse/LangSmith
- [ ] Production-grade frontend
- [ ] Multi-tenant support
- [ ] Helm deployment
- [ ] CI/CD evaluation pipeline

---

## What This Project Brings Together

```text
DevOps / SRE
    │
    ├── Incident Response
    ├── Docker
    ├── PostgreSQL
    ├── Redis
    └── Kubernetes tooling
    │
    ▼
AI / MLOps
    │
    ├── RAG
    ├── Vector Search
    ├── Hybrid Retrieval
    ├── Reranking
    └── Agentic Tools
    │
    ▼
Application Engineering
    │
    ├── FastAPI
    ├── Streamlit
    ├── SSE Streaming
    └── Automated Testing
```

The goal is not simply to build another chatbot, but to demonstrate how AI can be integrated into a realistic DevOps/SRE incident-response workflow.

---

## Documentation

| Document | Purpose |
| --- | --- |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Detailed system architecture and component design |
| [DEMO.md](./DEMO.md) | End-to-end application demonstration |
| [TESTING.md](./TESTING.md) | Test commands and verification results |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | Problems encountered and debugging steps |

---

## License

Released under the [MIT License](./LICENSE).
