# On-Call Copilot

**RAG-powered incident response assistant for on-call engineers.**

On-Call Copilot ingests your operational knowledge (runbooks, postmortems, alert definitions, Kubernetes configs) and acts as an expert copilot during incidents — retrieving relevant history, diagnosing from live context, and drafting mitigation checklists + postmortems with citations.

## Features

- **Hybrid RAG Search**: Vector + BM25 search over runbooks, postmortems, alerts, and configs
- **Incident History**: Query past incidents by alert, service, severity, date
- **Live K8s Queries**: Check pod status, logs, events, resource usage (read-only)
- **Agentic Loop**: ReAct-style agent that plans, searches, and synthesizes answers
- **Streaming Chat**: Real-time responses with citations
- **Postmortem Drafting**: Generate structured postmortems from incident context
- **Evaluation Harness**: Golden set with retrieval/generation metrics

## Architecture

```
��─────────────────────────────────────────────────────────────────��
│                        FastAPI Backend                          │
├──────────────��──────────────��──────────────��────────────────────��
│  Ingestion   │   Retrieval  │    Agent     │     Chat API       │
│  Pipeline    │   Service    │    Loop      │  (Streaming SSE)   │
��──────��───────��──────��───────��──────��───────��─────────��──────────��
       │              │              │                 │
       ��              ��              ��                 ��
��──────────────�� ��────────────�� ��─────────────�� ��──────────────��
│  Document    │ │  Vector    │ │  Tool       │ │  Session     │
│  Loader/     │ │  Store     │ │  Registry   │ │  Manager     │
│  Chunker     │ │  (pgvector)│ │  (k8s,      │ │  (Redis)     │
│              │ │            │ │   logs,     │ │              │
│              │ │            │ │   alerts)   │ │              │
��──────────────�� └────────────�� └─────────────�� └──────────────��
```

## Quickstart

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- OpenAI API key (or local embeddings via Ollama)

### 1. Clone and Configure

```bash
git clone <repo>
cd oncall-copilot
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
```

### 2. Start Infrastructure

```bash
docker compose up -d postgres redis
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Seed Demo Data

```bash
python scripts/seed_demo_data.py
```

### 5. Ingest Demo Documents

```bash
python scripts/ingest.py --source markdown --path ./demo_docs
```

### 6. Start API Server

```bash
uvicorn app.main:app --reload
# Or via Docker: docker compose up -d api
```

### 7. Start UI (separate terminal)

```bash
streamlit run ui/streamlit_app.py
# Or via Docker: docker compose up -d ui
```

### 8. Test

Open http://localhost:8501 and ask:
- "Alert: HighErrorRate on payments-api"
- "What caused the payments outage on March 15?"
- "Pod is in CrashLoopBackOff state, how do I debug?"

## Configuration

Key settings in `.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# OpenAI
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o-mini

# Retrieval
RETRIEVAL_TOP_K=20
RETRIEVAL_RERANK_TOP_K=5

# Agent
AGENT_MAX_TURNS=8
```

## Project Structure

```
oncall-copilot/
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
├── scripts/
│   ├── ingest.py              # CLI for ingestion
│   └── seed_demo_data.py      # Demo incidents
├── demo_docs/
│   ├── runbooks/              # Sample runbooks
│   └── postmortems/           # Sample postmortems
├── app/
│   ├── main.py                # FastAPI app
│   ├── config.py              # Pydantic settings
│   ├── database.py            # SQLAlchemy async
│   ├── models/                # SQLModel models
│   │   ├── documents.py
│   │   ├── chunks.py
│   │   ├── incidents.py
│   │   └── chat.py
│   ├── api/
│   │   └── routes/
│   │       ├── health.py
│   │       ├── chat.py        # Streaming SSE endpoint
│   │       └── ingest.py
│   ├── ingestion/
│   │   ├── loaders/
│   │   │   ├── markdown.py
│   │   │   ├── github.py
│   │   │   └── pagerduty.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   └── pipeline.py
│   ├── retrieval/
│   │   ├── service.py         # Hybrid search + reranking
│   │   ├── strategies.py      # Vector, BM25, Hybrid
│   │   └── reranker.py        # Cross-encoder
│   ├── agent/
│   │   ├── tools/
│   │   │   ├── search_knowledge.py
│   │   │   ├── search_incidents.py
│   │   │   ├── get_timeline.py
│   │   │   ├── query_k8s.py
│   │   │   └── draft_postmortem.py
│   │   ├── loop.py            # ReAct agent loop
│   │   ├── prompts.py
│   │   └── state.py
│   └── utils/
│       └── streaming.py       # SSE formatting
├── evals/
│   ├── golden_set.jsonl       # Evaluation queries
│   ├── run.py                 # Evaluation script
│   └── ci.yml                 # GitHub Actions
��── ui/
    └── streamlit_app.py       # Chat UI
```

## Ingestion Sources

| Source | Loader | Description |
|--------|--------|-------------|
| Markdown | `MarkdownLoader` | Local .md files with YAML frontmatter |
| GitHub | `GitHubPostmortemLoader` | Postmortems from GitHub repo |
| PagerDuty | `PagerDutyLoader` | Incidents + runbooks from PagerDuty API |

## Tools Available to Agent

| Tool | Description |
|------|-------------|
| `search_knowledge` | Hybrid RAG search over docs |
| `search_incidents` | SQL query over incidents table |
| `get_incident_timeline` | Full details for incident ID |
| `query_k8s` | K8s read-only: pods, logs, events |
| `draft_postmortem` | Generate structured postmortem |

## Evaluation

```bash
# Run all evaluations
python evals/run.py --all

# Retrieval only
python evals/run.py --retrieval

# Generation only
python evals/run.py --generation
```

Thresholds:
- Retrieval: Hit@5 >= 0.7, MRR >= 0.6, nDCG@10 >= 0.6
- Generation: Faithfulness >= 0.8, Citation Accuracy >= 0.9, Relevance >= 0.7

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
ruff format .

# Type check
mypy app/
```

## Docker Compose Services

| Service | Port | Description |
|---------|------|-------------|
| postgres | 5432 | PostgreSQL + pgvector |
| redis | 6379 | Session cache |
| api | 8000 | FastAPI backend |
| ui | 8501 | Streamlit chat UI |

## Roadmap

- [ ] Authentication/Authorization
- [ ] Slack bot integration
- [ ] PagerDuty webhook ingestion
- [ ] Advanced K8s tooling (kubectl exec, port-forward)
- [ ] Multi-tenant support
- [ ] Custom embedding models (local via Ollama)
- [ ] Langfuse/LangSmith tracing integration
- [ ] Next.js production UI

## License

MIT