# Architecture - SupportOps

## Overview

This project uses **Hexagonal Architecture** (Ports & Adapters) to separate business logic from infrastructure concerns.

## Core Principles

1. **Domain Independence** - Business rules live in pure Python/domain layer, no framework dependencies
2. **Testability** - Each layer can be tested independently with clear contracts
3. **Flexibility** - Swap implementations (Postgres → MongoDB, OpenAI → Anthropic) without touching domain
4. **Traceability** - Every decision (document version, embedding model, retrieval score) is explicit

## Layers

### 1. Domain Layer (Pure Business Logic)

```
packages/domain/
├── entities/           # Document, DocumentVersion, Chunk, Ticket, AIResponse
├── value_objects/      # VersionLabel, ConfidenceScore, Citation
├── services/           # ChunkingService, VersioningPolicy, ConfidenceScorer
└── events/             # DocumentVersionCreated, ResponseReviewed
```

**Characteristics:**

- Zero external dependencies (no FastAPI, SQLAlchemy, etc.)
- Testable without mocks or infrastructure
- Slow to change (should be stable)

### 2. Application Layer (Use-Cases)

```
packages/application/
├── use_cases/
│   ├── ingest_document.py      # Orchestrate document upload
│   ├── generate_response.py    # Generate AI response for ticket
│   ├── review_response.py      # Store human feedback
│   └── ...
├── dtos/                       # Input/output data transfer objects
└── orchestrators/              # Complex workflows
```

**Characteristics:**

- Calls Domain Services for business logic
- Calls Ports (interfaces) to interact with external systems
- Never directly calls Adapters
- Coordinates transactions

### 3. Ports (Interfaces/Contracts)

```
packages/ports/
├── repositories/
│   ├── DocumentRepository       # get, list, create, update
│   ├── TicketRepository
│   ├── ChunkRepository
│   └── ReviewRepository
├── storage/
│   └── DocumentStoragePort      # save, retrieve files
├── vector/
│   ├── VectorSearchPort         # search vectors
│   └── EmbeddingStorePort       # index embeddings
├── llm/
│   └── LLMClientPort            # call LLM
└── queue/
    └── QueuePort                # enqueue tasks
```

**Characteristics:**

- Define contracts (interfaces/protocols)
- Specify method signatures and behaviors
- No implementation
- Language-agnostic contracts

### 4. Adapters (Implementations)

```
packages/adapters/
├── postgres/
│   ├── document_repository.py       # Implements DocumentRepository
│   ├── ticket_repository.py
│   └── models.py                     # SQLAlchemy ORM models
├── pgvector/
│   └── vector_search_adapter.py     # Implements VectorSearchPort
├── s3/
│   └── document_storage_adapter.py  # Implements DocumentStoragePort
├── llm/
│   ├── openai_adapter.py            # Implements LLMClientPort
│   └── anthropic_adapter.py         # Alternative implementation
└── redis/
    └── queue_adapter.py             # Implements QueuePort
```

**Characteristics:**

- Framework-specific code lives here
- Each port has one or more implementations
- Easily replaceable
- Can be mocked for testing

### 5. Apps (Entry Points)

```
apps/
├── api/                 # FastAPI app (adapter in)
│   ├── main.py         # Create app
│   ├── controllers/     # HTTP handlers (adapters)
│   ├── routes/         # Endpoint definitions
│   ├── serializers/    # HTTP DTOs (Pydantic)
│   └── wiring.py       # Dependency injection
│
├── web/                 # Next.js app (adapter in)
│   ├── app/            # Pages
│   ├── components/
│   └── lib/api/        # HTTP client wrapper
│
└── workers/            # Celery app (adapter in/out)
    ├── celery_app.py   # Setup
    ├── tasks/          # Task definitions
    └── processors/     # Processing logic
```

**Characteristics:**

- Minimal business logic
- Mainly orchestration and translation
- Thin layers that call Application use-cases
- Can be deployed independently

## Data Flow: Document Upload Example

```
1. ADMIN UPLOADS DOCUMENT (HTTP)
   ┌─────────────────────────────────────────┐
   │ Browser: POST /documents                │
   │ Body: { file, type, tags }              │
   └─────────────────────────────────────────┘
                    ↓

2. ADAPTER IN (Controller)
   ┌─────────────────────────────────────────┐
   │ apps/api/controllers/document_controller│
   │ - Validate HTTP request                 │
   │ - Parse form data                       │
   │ - Create DTO                            │
   └─────────────────────────────────────────┘
                    ↓

3. APPLICATION (Use-Case)
   ┌─────────────────────────────────────────┐
   │ packages/application/ingest_document    │
   │ - Call VersioningPolicy (domain service)│
   │ - Call DocumentStoragePort (save file)  │
   │ - Call DocumentRepository (create DB)   │
   │ - Call QueuePort (enqueue processing)   │
   └─────────────────────────────────────────┘
                    ├─────────────────────────────────────┐
                    ↓                                       ↓

4. ADAPTERS OUT
   ┌─────────────────────────────────────────┐  ┌────────────────────┐
   │ S3DocumentStorageAdapter                │  │ PostgresRepository │
   │ - Upload to MinIO/S3                    │  │ - Create Document  │
   │ - Return URI                            │  │ - Create Version   │
   └─────────────────────────────────────────┘  └────────────────────┘
                                                        ↓
                                            ┌──────────────────────────┐
                                            │ RedisQueueAdapter        │
                                            │ - Enqueue task           │
                                            │ Return job_id            │
                                            └──────────────────────────┘
                    ↑                                       ↑
                    └─────────────────────────────────────┘

5. RESPONSE
   ┌─────────────────────────────────────────┐
   │ Controller receives results             │
   │ - Map to DTO                            │
   │ - Convert to JSON                       │
   │ - Return HTTP 200                       │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ Browser receives:                       │
   │ { document_id, version, status, ... }   │
   └─────────────────────────────────────────┘

6. ASYNC WORKER (Adapter In + Out)
   ┌─────────────────────────────────────────┐
   │ apps/workers/tasks                      │
   │ - Dequeue job from Redis                │
   │ - Call DocumentStorageAdapter (download)│
   │ - Process (chunking, parsing)           │
   │ - Call EmbeddingStorePort (index)       │
   │ - Update status in DB                   │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ Frontend polls GET /documents           │
   │ Status now: "Indexed ✓"                 │
   └─────────────────────────────────────────┘
```

## Dependency Rules

```
  ┌─────────────────────────────────────┐
  │         Apps                         │  (Outer ring)
  │  (FastAPI, Next.js, Celery)         │
  └──────────┬──────────────────────────┘
             │ depends on
             ↓
  ┌─────────────────────────────────────┐
  │      Adapters                        │  (Infrastructure)
  │  (Postgres, S3, OpenAI, Redis)      │
  └──────────┬──────────────────────────┘
             │ implement
             ↓
  ┌─────────────────────────────────────┐
  │      Ports                           │  (Interfaces)
  │  (Repository, Storage, LLM, Queue)  │
  └──────────┬──────────────────────────┘
             │ used by
             ↓
  ┌─────────────────────────────────────┐
  │    Application                       │  (Use-Cases)
  │  (IngestDocument, GenerateResponse) │
  └──────────┬──────────────────────────┘
             │ calls
             ↓
  ┌─────────────────────────────────────┐
  │      Domain                          │  (Core Business)
  │  (Entities, Services, Events)       │  (Inner ring - pure)
  └─────────────────────────────────────┘

Key Rules:
- Domain ← depends on nothing
- Application ← depends on Domain & Ports only
- Adapters ← implement Ports
- Apps ← depend on Application
- Adapters cannot depend on each other (go through Application)
```

## Key Benefits

### 1. Testability

```python
# Test domain service without infrastructure
from domain.services import VersioningPolicy

policy = VersioningPolicy()
assert policy.decide_version("old_hash", "new_hash") == "v2"  # Easy!
```

### 2. Flexibility

Change from OpenAI to Anthropic:

```python
# Before
class OpenAIEmbeddingsAdapter(EmbeddingStorePort):
    def embed(self, text): ...

# After
class AnthropicEmbeddingsAdapter(EmbeddingStorePort):
    def embed(self, text): ...

# In wiring.py, swap one line. Use-cases unchanged!
```

### 3. Traceability

Document processing includes version tracking:

```python
Chunk {
    id: "chunk-123",
    document_version_id: "doc-v3",  # Which version?
    embedding_model: "text-embedding-3-small",  # Which model?
    retrieval_score: 0.89,
    created_at: ...
}
```

### 4. Scalability

Worker processes independently:

```
API creates DocumentVersion, enqueues job
Worker dequeues, processes, updates status
Frontend polls and sees progress
```

## Wiring (Dependency Injection)

Each app has a `wiring.py` that connects everything:

```python
# apps/api/wiring.py
from packages.adapters.postgres import PostgresDocumentRepository
from packages.adapters.s3 import S3DocumentStorageAdapter
from packages.application import IngestDocumentUseCase

# Create adapters
document_repo = PostgresDocumentRepository(session)
storage = S3DocumentStorageAdapter(client)

# Create use-case with dependencies
ingest_use_case = IngestDocumentUseCase(
    repository=document_repo,
    storage=storage,
    versioning_policy=VersioningPolicy(),
)

# Use in controller
app.ingest_use_case = ingest_use_case
```

## Contracts (Port Specifications)

Each port has a contract document:

```markdown
# DocumentRepository Contract

## Methods

- `create(document: Document) → DocumentVersion`
- `get(id: str) → Document | None`
- `list(filters: Dict) → List[Document]`
- `update_status(id: str, status: str) → None`

## Invariants

- DocumentVersion is immutable (insert-only)
- All versions reference same Document
- Version labels are unique per Document
```

See [packages/ports/contracts/](../packages/ports/contracts/) for full specs.

## Evolution Strategy

### MVP Phase

1. Extract domain entities and services
2. Write application use-cases
3. Define ports (interfaces)
4. Implement basic adapters (Postgres, S3, local LLM)
5. Wire everything in apps

### Production Phase

1. Add contract tests (adapter vs port)
2. Implement alternative adapters (vector DB, LLM providers)
3. Add observability (tracing, metrics)
4. Optimize adapters based on learnings

## Files to Read

1. Start: `apps/api/README.md` - How API app uses hexagonal
2. Then: `packages/domain/README.md` - Business logic
3. Then: `packages/adapters/README.md` - Infrastructure
4. Advanced: `docs/PATTERNS.md` - Common patterns
