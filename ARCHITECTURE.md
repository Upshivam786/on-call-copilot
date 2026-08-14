# On-Call Copilot — Architecture

## 1. Overview

On-Call Copilot is a RAG-powered incident response assistant designed around a typical DevOps/SRE incident investigation workflow.

The system combines:

- FastAPI
- Streamlit
- PostgreSQL
- pgvector
- Redis
- Hybrid retrieval
- Cross-encoder reranking
- A ReAct-style agent loop
- Specialized incident-response tools
- Server-Sent Events (SSE)
- Docker Compose

The architecture separates the system into four major application responsibilities:

```text
┌─────────────────────────────────────────────────────────────┐
│                     On-Call Copilot                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Ingestion       Retrieval       Agent        Chat API      │
│  Pipeline        Service         Loop         + SSE         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
2. High-Level Architecture
                         ┌─────────────────────┐
                         │      User           │
                         │  On-call Engineer   │
                         └──────────┬──────────┘
                                    │
                                    │ Browser
                                    ▼
                         ┌─────────────────────┐
                         │    Streamlit UI     │
                         │       :8501         │
                         └──────────┬──────────┘
                                    │
                                    │ HTTP / SSE
                                    ▼
                         ┌─────────────────────┐
                         │     FastAPI API     │
                         │       :8002         │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     Agent Loop      │
                         │   ReAct-style flow  │
                         └──────────┬──────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
       ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
       │ Knowledge      │  │ Incident       │  │ Kubernetes     │
       │ Retrieval      │  │ Tools          │  │ Tools          │
       └───────┬────────┘  └───────┬────────┘  └────────────────┘
               │                   │
               ▼                   ▼
       ┌─────────────────────────────────────┐
       │          PostgreSQL + pgvector       │
       │                                     │
       │ Documents / Chunks / Incidents      │
       │ Chat Sessions / Messages            │
       └──────────────────┬──────────────────┘
                          │
                          ▼
                     ┌─────────┐
                     │  Redis  │
                     │  :6379  │
                     └─────────┘
3. Docker Compose Architecture

The development environment is composed of four main services:

┌───────────────────────────────────────────────┐
│              Docker Compose                   │
│                                               │
│  ┌─────────────┐       ┌─────────────┐       │
│  │ PostgreSQL  │       │    Redis    │       │
│  │  + pgvector │       │             │       │
│  │    :5434    │       │    :6379    │       │
│  └──────┬──────┘       └──────┬──────┘       │
│         │                     │              │
│         └──────────┬──────────┘              │
│                    │                         │
│             ┌──────▼──────┐                  │
│             │   FastAPI   │                  │
│             │     API     │                  │
│             │    :8000    │                  │
│             └──────┬──────┘                  │
│                    │                         │
│             ┌──────▼──────┐                  │
│             │  Streamlit  │                  │
│             │     UI      │                  │
│             │    :8501    │                  │
│             └─────────────┘                  │
│                                               │
└───────────────────────────────────────────────┘

The host-side API port is currently mapped to 8002 because port 8000 was already occupied by another Docker workload on the development machine.

Host                    Container

localhost:8002   ────►  api:8000
localhost:8501   ────►  ui:8501
localhost:5434   ────►  postgres:5432
localhost:6379   ────►  redis:6379

Inside the Docker network, services communicate using Compose service names.

For example:

Streamlit → http://api:8000
API       → postgres:5432
API       → redis:6379
4. Application Layers

The application is organized into several logical layers.

┌──────────────────────────────────────────┐
│              Presentation                │
│             Streamlit UI                 │
└────────────────────┬─────────────────────┘
                     │
┌────────────────────▼─────────────────────┐
│               API Layer                  │
│              FastAPI + SSE               │
└────────────────────┬─────────────────────┘
                     │
┌────────────────────▼─────────────────────┐
│              Agent Layer                 │
│          ReAct-style Agent Loop          │
└────────────────────┬─────────────────────┘
                     │
┌────────────────────▼─────────────────────┐
│              Tool Layer                  │
│ Knowledge / Incidents / K8s / Postmortem │
└────────────────────┬─────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌─────────────────────┐ ┌──────────────────┐
│ Retrieval Layer     │ │ Database Layer   │
│ Vector + BM25       │ │ PostgreSQL       │
│ + Reranking         │ │ Redis            │
└─────────────────────┘ └──────────────────┘
5. Ingestion Pipeline

Operational knowledge first enters through the ingestion pipeline.

Current demo sources include Markdown runbooks and postmortems.

Markdown Documents
        │
        ▼
  Document Loader
        │
        ▼
  Document Model
        │
        ▼
 Semantic Chunking
        │
        ▼
   Text Chunks
        │
        ▼
    Embedding
        │
        ▼
 PostgreSQL + pgvector

The main components are located under:

app/ingestion/

including:

loaders/
chunker.py
embedder.py
pipeline.py
6. Document Model

Documents are stored separately from their chunks.

Conceptually:

Document
   │
   ├── Chunk 0
   ├── Chunk 1
   ├── Chunk 2
   └── ...

The document contains information such as:

id
source_type
source_id
title
content
metadata
created_at
updated_at

Chunks contain:

id
document_id
chunk_index
content
embedding
token_count
metadata
created_at

This separation allows the system to preserve document-level metadata while performing retrieval at chunk level.

7. Embedding Flow

During ingestion, text chunks are converted into numerical vectors.

Chunk Text
    │
    ▼
Embedding Model
    │
    ▼
Vector
    │
    ▼
PostgreSQL + pgvector

The current project supports an OpenAI embedding implementation and contains a local embedding implementation for future/local deployment scenarios.

The existing demo data was populated with embeddings and verified in PostgreSQL.

8. Retrieval Architecture

The retrieval layer is one of the core components of the project.

It combines two retrieval approaches:

                    User Query
                        │
             ┌──────────┴──────────┐
             │                     │
             ▼                     ▼
       Query Embedding         BM25/Text Search
             │                     │
             ▼                     ▼
       Vector Search           PostgreSQL
             │                     │
             └──────────┬──────────┘
                        ▼
                 Hybrid Search
                        │
                        ▼
                Score Normalization
                        │
                        ▼
                 Result Merging
                        │
                        ▼
               Cross-Encoder Reranker
                        │
                        ▼
                  Final Results

The retrieval implementation is primarily under:

app/retrieval/
9. Vector Search

Vector retrieval uses pgvector similarity search.

Conceptually:

User Query
    │
    ▼
Embedding
    │
    ▼
Query Vector
    │
    ▼
pgvector
    │
    ▼
Nearest Chunks

The similarity operation is performed against stored chunk embeddings.

This allows semantically related content to be retrieved even when the wording differs.

For example:

"database pool exhaustion"

may retrieve documentation containing:

"PostgreSQL connection saturation"

even if the exact phrase is different.

10. BM25 / Full-Text Retrieval

The second retrieval strategy uses PostgreSQL full-text search.

Query
  │
  ▼
PostgreSQL tsquery
  │
  ▼
Full-text matching
  │
  ▼
Ranked results

This is useful for exact operational terminology such as:

CrashLoopBackOff
PgBouncer
HighErrorRate_payments-api
DATABASE_URL

The combination of vector and lexical retrieval provides better coverage than either approach alone.

11. Hybrid Retrieval

Vector and BM25 results are normalized and combined using configurable weights.

The current implementation uses:

Vector weight = 0.7
BM25 weight   = 0.3

Conceptually:

Hybrid Score =
    (Vector Score × 0.7)
  + (BM25 Score × 0.3)

Results are merged using the chunk ID.

If a chunk appears in both retrieval result sets, its weighted scores are combined.

12. Cross-Encoder Reranking

After hybrid retrieval, candidate results can be reranked using a cross-encoder.

Hybrid Results
      │
      ▼
Candidate Documents
      │
      ▼
┌───────────────────────────┐
│ Cross Encoder             │
│                           │
│ Query + Candidate Chunk   │
└─────────────┬─────────────┘
              │
              ▼
        Rerank Score
              │
              ▼
       Final Ranking

This provides a second-stage ranking mechanism after the initial high-recall retrieval.

13. Query Expansion

The retrieval service also supports optional query expansion.

Original Query
      │
      ▼
Query Expansion
      │
      ├──────► Query 1
      ├──────► Query 2
      └──────► Query 3
                │
                ▼
          Hybrid Retrieval

The resulting searches are merged by chunk ID.

If query expansion is unavailable, the service can fall back to the original query.

14. Agent Architecture

The agent uses a ReAct-style loop.

Conceptually:

User Query
    │
    ▼
Agent
    │
    ▼
Select Tool
    │
    ▼
Execute Tool
    │
    ▼
Observe Result
    │
    ▼
Select Next Action
    │
    ▼
...
    │
    ▼
Final Answer

The agent implementation is located under:

app/agent/

The loop maintains agent state and tracks tool execution.

15. Agent Tools

The current agent exposes five tools.

search_knowledge

Purpose:

Search operational knowledge using hybrid RAG.

Flow:

Query
  ↓
Embedding
  ↓
Vector + BM25
  ↓
Hybrid Search
  ↓
Reranking
  ↓
Relevant Chunks
search_incidents

Purpose:

Search historical incidents.

It can filter by:

alert name
service
severity
status

Flow:

Agent
  ↓
search_incidents
  ↓
PostgreSQL
  ↓
Historical incidents
get_incident_timeline

Purpose:

Retrieve detailed information for a specific incident.

The tool returns information including:

Incident
Severity
Status
Services
Start time
Resolution time
Root cause
Resolution steps
Tags
Raw payload

It can also retrieve a linked postmortem when one is associated with the incident.

query_k8s

Purpose:

Perform read-only Kubernetes investigation.

The intended workflow is:

Agent
  ↓
Kubernetes Tool
  ↓
Pods / Logs / Events / Resources
  ↓
Observation
  ↓
Agent

Production deployment would require appropriate Kubernetes RBAC and security controls.

draft_postmortem

Purpose:

Generate a structured postmortem draft.

Input can include:

Summary
Timeline
Root Cause
Impact
Resolution
Action Items
Citations

Output:

Structured Markdown Postmortem

The generated document is a draft and should be reviewed by an engineer before publication.

16. Example Agent Workflow

Consider the query:

What happened in the previous HighErrorRate_payments-api incidents?

The conceptual agent flow is:

User
 │
 ▼
Agent
 │
 ▼
Recognizes historical incident question
 │
 ▼
search_incidents
 │
 ▼
PostgreSQL
 │
 ▼
Historical incidents
 │
 ▼
Agent observes results
 │
 ▼
Final synthesis
 │
 ▼
Streaming response

For a knowledge question:

How do I troubleshoot database connection pool exhaustion?

the flow becomes:

User
 │
 ▼
Agent
 │
 ▼
search_knowledge
 │
 ▼
RetrievalService
 │
 ├──► Vector Search
 │
 ├──► BM25
 │
 ├──► Hybrid Merge
 │
 └──► Reranking
 │
 ▼
Relevant Runbook Chunks
 │
 ▼
Agent
 │
 ▼
Final Answer
17. Chat API

The FastAPI backend exposes the chat functionality.

The main endpoint is:

POST /api/v1/chat/stream

The endpoint accepts a query and session ID.

Conceptually:

POST /chat/stream
        │
        ▼
   FastAPI Route
        │
        ▼
    Agent Loop
        │
        ├── Tool Events
        ├── Reasoning/Status Events
        └── Response Events
        │
        ▼
      SSE Stream
        │
        ▼
   Streamlit UI
18. Server-Sent Events

The system uses SSE for streaming.

Instead of waiting for the entire agent execution:

Request
   │
   ▼
Wait
   │
   ▼
Complete response

the client receives incremental events:

Request
   │
   ├── start
   │
   ├── tool_start
   │
   ├── tool_result
   │
   ├── content
   │
   └── complete

This is particularly useful for long-running agent workflows.

19. Session Management

Chat sessions and messages are persisted in PostgreSQL.

Redis is also part of the runtime architecture and is used for session/cache-related functionality.

Conceptually:

User
 │
 ▼
Chat Session
 │
 ├── Message 1
 ├── Message 2
 ├── Message 3
 └── ...

This allows conversations to maintain context rather than treating every query as completely independent.

20. Database Architecture

PostgreSQL stores the core application data.

Current tables include:

documents
chunks
incidents
chat_sessions
chat_messages
alembic_version

Conceptual relationships:

documents
    │
    └──────< chunks

incidents
    │
    └──────> documents
             (optional postmortem relationship)

chat_sessions
    │
    └──────< chat_messages
21. PostgreSQL Extensions

The database is configured with:

pgvector
pg_trgm

along with PostgreSQL's standard plpgsql extension.

pgvector provides vector similarity capabilities.

pg_trgm can support efficient text similarity operations.

22. API and Database Communication

The API uses SQLAlchemy's asynchronous database stack.

Conceptually:

FastAPI
   │
   ▼
SQLAlchemy AsyncSession
   │
   ▼
asyncpg
   │
   ▼
PostgreSQL

This allows database operations to be integrated with the asynchronous FastAPI request flow.

23. Redis

Redis runs as a separate Docker Compose service.

FastAPI
   │
   ▼
Redis
   │
   ├── Session/cache functionality
   └── Fast temporary state

Redis is intentionally separated from PostgreSQL because it serves a different role:

PostgreSQL → Persistent application data
Redis      → Fast temporary/cache/session data
24. Streamlit Frontend

The frontend is implemented using Streamlit.

Location:

ui/streamlit_app.py

The UI provides:

┌─────────────────────────────────────────┐
│          On-Call Copilot                │
├─────────────────────────────────────────┤
│ Sessions          │ Chat                │
│                   │                     │
│ New Chat          │ User Query          │
│                   │       ↓             │
│ Previous Chats    │ Agent Response      │
│                   │       ↓             │
│                   │ Tool Activity        │
│                   │ Citations            │
└─────────────────────────────────────────┘

The frontend does not directly access PostgreSQL.

Instead:

Streamlit
    ↓
FastAPI
    ↓
Application Services
    ↓
Database / Redis

This separation keeps the frontend decoupled from backend implementation details.

25. Configuration and Environment Separation

The project uses environment variables for runtime configuration.

Important configuration areas include:

DATABASE_URL
REDIS_URL
OPENAI_API_KEY
EMBEDDING_MODEL
EMBEDDING_DIMENSIONS
LLM_MODEL
RETRIEVAL_TOP_K
RETRIEVAL_RERANK_TOP_K
AGENT_MAX_TURNS

The .env file is intentionally excluded from Git.

A template is provided through:

.env.example
26. Host vs Container Networking

One important architectural detail is the difference between host networking and Docker networking.

From the host:

Browser
   ↓
localhost:8501
   ↓
Streamlit

API health from the host:

curl localhost:8002/api/v1/health

From inside Docker:

Streamlit
   ↓
http://api:8000
   ↓
FastAPI

The API container connects to PostgreSQL using:

postgres:5432

not:

localhost:5434

This distinction was important during development and is documented in TROUBLESHOOTING.md.

27. End-to-End Request Flow

A complete knowledge-based request looks like:

                 User
                  │
                  ▼
            Streamlit UI
                  │
                  │ HTTP
                  ▼
             FastAPI API
                  │
                  ▼
             Agent Loop
                  │
                  ▼
          search_knowledge
                  │
                  ▼
          Retrieval Service
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   Vector Search        BM25 Search
        │                   │
        └─────────┬─────────┘
                  ▼
           Hybrid Ranking
                  │
                  ▼
          Cross-Encoder
             Reranking
                  │
                  ▼
          Relevant Chunks
                  │
                  ▼
               Agent
                  │
                  ▼
          Final Synthesis
                  │
                  ▼
             SSE Stream
                  │
                  ▼
            Streamlit UI
28. End-to-End Incident Investigation Flow

For an incident-focused query:

User
 │
 ▼
"What happened in previous
 HighErrorRate incidents?"
 │
 ▼
Streamlit
 │
 ▼
FastAPI
 │
 ▼
Agent Loop
 │
 ▼
search_incidents
 │
 ▼
PostgreSQL
 │
 ▼
Historical Incident Records
 │
 ▼
Agent
 │
 ▼
Final Response
 │
 ▼
SSE
 │
 ▼
Streamlit

If more context is required, the agent can use additional tools such as:

search_knowledge
get_incident_timeline
query_k8s
29. Postmortem Generation Flow
Incident Context
       │
       ▼
Historical Data
       │
       +
Retrieved Knowledge
       │
       ▼
Agent
       │
       ▼
draft_postmortem
       │
       ▼
Structured Markdown
       │
       ▼
Human Review
       │
       ▼
Final Postmortem

The system intentionally keeps a human review step before a generated postmortem is treated as authoritative.

30. Error Isolation Strategy

The project was developed and tested layer-by-layer.

Infrastructure
      │
      ▼
Database
      │
      ▼
Migrations
      │
      ▼
Seed Data
      │
      ▼
Ingestion
      │
      ▼
Retrieval
      │
      ▼
Agent Tools
      │
      ▼
API
      │
      ▼
Docker Networking
      │
      ▼
Streamlit
      │
      ▼
End-to-End Flow

This approach makes it easier to determine whether a failure belongs to:

Infrastructure
Configuration
Database
Retrieval
Agent logic
API
Networking
Frontend

Detailed debugging examples are available in:

TROUBLESHOOTING.md
31. Current Architecture Limitations

The current architecture is intentionally a portfolio/demo implementation.

Known limitations include:

Embedding provider coupling

The retrieval service currently initializes the OpenAI-based embedder directly.

The local embedding implementation exists but requires additional integration for transparent fallback.

Embedding dimension compatibility

The stored demo vectors and local embedding model must use compatible dimensions before switching providers.

Authentication

Authentication and authorization are not currently implemented.

Kubernetes security

A production Kubernetes deployment would require:

RBAC
Service account controls
Network policies
Audit logging
Secret management
LLM provider

The project includes a mock LLM mode for demonstration when an OpenAI API key is unavailable.

Production deployment would require a properly configured LLM and embedding provider.

32. Production Evolution

A possible production architecture could evolve toward:

                    Load Balancer
                          │
                          ▼
                   API / Gateway
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
       Agent Services            Ingestion Workers
             │                         │
             ▼                         ▼
       Retrieval Layer          Document Pipeline
             │                         │
             ├──────────────┬──────────┤
             ▼              ▼          ▼
        PostgreSQL        Redis     Object Storage
        + pgvector
             │
             ▼
       Observability
       ├── Metrics
       ├── Logs
       └── Traces

Potential production additions include:

Authentication/RBAC
Kubernetes-native deployment
Managed PostgreSQL
Managed Redis
Object storage
Background ingestion workers
OpenTelemetry
Langfuse/LangSmith tracing
PagerDuty integration
Slack integration
CI/CD
Evaluation gates
Secret management
33. Design Principles

The architecture follows several principles.

Separation of concerns

The UI, API, agent, retrieval, and persistence layers have separate responsibilities.

Retrieval before generation

The agent should use operational knowledge and incident history rather than relying only on the LLM's pretrained knowledge.

Tool-based investigation

Specialized operations are exposed as tools instead of embedding every capability directly into the prompt.

Read-only operational access

Kubernetes investigation is designed around read-only operations.

Human-in-the-loop

Generated postmortems are drafts and require human review.

Layered testing

Each major component can be tested independently before validating the complete system.

34. Summary

The core architecture can be summarized as:

                 ┌───────────────────┐
                 │     Streamlit     │
                 │        UI         │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │      FastAPI      │
                 │    Chat + SSE     │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │    ReAct Agent    │
                 └─────────┬─────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    Knowledge          Incidents          K8s
    Retrieval           Search           Tools
          │                │                │
          └────────┬───────┴────────────────┘
                   ▼
          ┌─────────────────────┐
          │ PostgreSQL          │
          │ + pgvector          │
          └─────────┬───────────┘
                    │
                    ▼
          ┌─────────────────────┐
          │       Redis         │
          └─────────────────────┘

The key idea is to combine traditional DevOps incident data and operational documentation with modern RAG and agentic AI patterns, 
creating an assistant that can support investigation rather than simply generate generic chatbot responses.


