# API - FastAPI

Backend principal da aplicação SupportOps. Responsável por orquestrar a lógica de negócio através de use-cases, implementar os endpoints HTTP e integrar adapters.

## Stack

- **Framework**: FastAPI
- **Server**: Uvicorn
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL + pgvector
- **Cache**: Redis
- **Task Queue**: Celery/Redis (configurado em workers)
- **Storage**: S3/MinIO
- **Validation**: Pydantic 2.0

## Arquitetura (Hexagonal)

```
src/
  ├── main.py                    # App entrypoint
  ├── config.py                  # Settings (environment)
  ├── routes/                    # Definições de rotas HTTP
  │   ├── documents.py
  │   ├── tickets.py
  │   └── evaluations.py
  ├── controllers/                # Adapters (HTTP in)
  │   ├── documents_controller.py
  │   ├── tickets_controller.py
  │   └── evaluations_controller.py
  ├── serializers/               # DTOs Pydantic (input/output)
  │   ├── document_dto.py
  │   ├── ticket_dto.py
  │   └── responses.py
  ├── mappers/                   # Conversão ORM → Domain → DTO
  │   ├── document_mapper.py
  │   └── ticket_mapper.py
  ├── db/                        # Adapters (Postgres)
  │   ├── models.py              # SQLAlchemy ORM models
  │   ├── repositories/          # Implementação de ports
  │   ├── migrations/
  │   └── session.py
  ├── adapters/                  # Implementação de ports
  │   ├── storage/               # S3/MinIO adapter
  │   ├── vector_db/             # pgvector adapter
  │   ├── embeddings/            # LLM embeddings
  │   └── llm/                   # LLM calls
  ├── wiring.py                  # Dependency injection
  └── tests/
      ├── test_controllers/
      ├── test_routes/
      └── conftest.py
```

## Desenvolvimento

Estado atual: a API roda como scaffold e expõe apenas o endpoint `GET /`. As rotas, modelos e migrations descritos abaixo são planejados para o MVP.

```bash
# Instalar dependências (na pasta apps/api)
uv sync

# Rodar em desenvolvimento
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Ou via monorepo raiz
npm run dev:api

# Tests
uv run pytest
uv run pytest --cov

# Linting
uv run black .
uv run isort .
uv run flake8 .
uv run mypy .
```

Migrations com Alembic serão adicionadas quando os modelos de banco forem implementados.

## Endpoints planejados (MVP)

### Documents

- `POST /api/documents` - Upload documento
- `GET /api/documents` - Listar documentos
- `GET /api/documents/{id}` - Detalhe documento
- `GET /api/documents/{id}/versions` - Versões do documento
- `POST /api/documents/{id}/reindex` - Reindexar

### Tickets

- `GET /api/tickets` - Listar tickets
- `POST /api/tickets` - Criar ticket
- `GET /api/tickets/{id}` - Detalhe ticket
- `PATCH /api/tickets/{id}` - Atualizar ticket
- `POST /api/tickets/{id}/generate-response` - Gerar resposta via IA

### Evaluations

- `GET /api/evaluations/summary` - Resumo de métricas
- `GET /api/evaluations/experiments` - Experimentos RAG
- `GET /api/evaluations/gaps` - Knowledge gaps

## Variáveis de Ambiente

Ver `.env.example` na raiz.

Principais:

- `DB_*` - Conexão Postgres
- `REDIS_*` - Conexão Redis
- `MINIO_*` - Storage
- `OPENAI_API_KEY` - LLM provider
- `API_DEBUG` - Debug mode

## Relacionamentos (Domain → Adapters)

- **Domain Services** + **Controllers** → **Use-cases** → **Ports** → **Adapters**
- Controllers são adapters de entrada (HTTP in)
- Repositories e Storage são adapters de saída (HTTP out)
- Tudo orquestrado por wiring (dependency injection)

Ver arquivo de arquitetura na raiz: `docs/architecture.md`
