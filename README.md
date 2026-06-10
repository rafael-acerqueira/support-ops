# SupportOps

SupportOps is a customer support operations platform for B2B SaaS teams.

It helps support agents triage tickets, retrieve trusted internal knowledge, generate policy-aware response drafts, review AI-assisted suggestions, and measure response quality through evaluation datasets and observability.

## 🎯 Overview

**Problem**: Support teams spend time searching for answers across multiple sources and risk inconsistent, unreliable responses.

**Solution**: A RAG (Retrieval-Augmented Generation) platform that:

- Ingests versioned documents (PDFs, Markdown, CSVs, HTML)
- Chunks and indexes with embeddings
- Retrieves relevant context for each support ticket
- Generates cited responses (no hallucinations)
- Requires human approval before sending
- Tracks feedback for continuous improvement

## 🏗️ Architecture

**Hexagonal architecture** with three layers:

- **Domain** (pure business logic) - independent of frameworks
- **Application** (use-cases) - orchestrates domain services and ports
- **Infrastructure** (adapters) - Postgres, S3, LLM APIs, Redis, etc.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design.

## 🛠️ Tech Stack

### Frontend

- Next.js 14 (App Router)
- Tailwind CSS + Shadcn/ui
- Theme: Dark-first, Roxo/Cyan/Laranja
- Deployed to Vercel (optional)

### Backend

- FastAPI (REST API)
- PostgreSQL + pgvector (vector storage)
- Redis (task queue)
- MinIO/S3 (document storage)

### Async Workers

- Celery + Redis (task processing)
- Document parsing, chunking, embeddings

### Monorepo

- Turbo (build orchestration)
- pnpm (Node dependencies)
- UV (Python dependencies)

## 📁 Project Structure

```
supportops/
├── apps/
│   ├── web/              # Next.js frontend
│   ├── api/              # FastAPI backend
│   └── workers/          # Celery workers
├── packages/             # Shared code (future)
├── infra/                # Docker, K8s configs
├── scripts/              # Dev scripts
├── docs/                 # Documentation
├── docker-compose.yml    # Local dev environment
├── turbo.json           # Monorepo config
└── package.json         # Root scripts
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose plugin (`docker compose`)
- pnpm (install: `npm i -g pnpm`)
- UV (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Setup

1. **Clone and enter directory**

```bash
cd supportops
```

2. **Create .env file**

```bash
cp .env.example .env
```

3. **Start infrastructure** (Postgres + pgvector, Redis, MinIO, pgAdmin)

```bash
npm run docker:up
```

Verify services:

- Postgres: `localhost:${DB_PORT}` (default in `.env.example`: `5432`)
- Redis: `localhost:${REDIS_PORT}` (default in `.env.example`: `6379`)
- pgAdmin: `http://localhost:5050` (admin@example.com / admin)
- MinIO: `http://localhost:9001` (minioadmin / minioadmin)

4. **Install Node dependencies** (monorepo root)

```bash
pnpm install
```

5. **Install Python dependencies** (each app)

```bash
cd apps/api && uv sync
cd ../workers && uv sync
```

6. **Start the local scaffold**

```bash
npm run dev
```

This runs the frontend, API, and workers in parallel. No database tables or migrations are required for the current scaffold.

### Optional: Start services individually

Frontend:

```bash
npm run dev:web
```

→ http://localhost:3000

Backend API:

```bash
npm run dev:api
```

→ http://localhost:8000 (docs at /docs)

Workers:

```bash
npm run dev:workers
```

Monitor (optional):

```bash
cd apps/workers && uv run celery -A src.celery_app flower --port=5555
```

→ http://localhost:5555

## 🔌 API Endpoints (MVP)

### Documents

- `POST /api/documents` - Upload document
- `GET /api/documents` - List documents
- `GET /api/documents/{id}` - Get document
- `GET /api/documents/{id}/versions` - Version history
- `POST /api/documents/{id}/reindex` - Reindex embeddings

### Tickets

- `GET /api/tickets` - List tickets
- `POST /api/tickets` - Create ticket
- `GET /api/tickets/{id}` - Get ticket detail
- `PATCH /api/tickets/{id}` - Update ticket
- `POST /api/tickets/{id}/generate-response` - Generate AI response

### Evaluations

- `GET /api/evaluations/summary` - Metrics overview
- `GET /api/evaluations/experiments` - RAG experiments
- `GET /api/evaluations/gaps` - Knowledge gaps

## 📊 Screens (MVP)

1. **Documents** - Upload and manage knowledge base
2. **Tickets** - List and filter support requests
3. **Ticket Detail** - View customer issue and AI-suggested response
4. **Evaluations** - Dashboard with metrics and analysis

## 🎨 Design System

- **Theme**: Dark-first, professional, tech-forward
- **Primary Color**: Roxo (#7C3AED)
- **Secondary**: Cyan (#0EA5E9)
- **Accent**: Laranja (#F97316)
- **UI Library**: Shadcn/ui (Tailwind + Radix)
- **Icons**: Lucide React

See [docs/DESIGN.md](docs/DESIGN.md) for component library details.

## 📝 Development

### Common Commands

```bash
# From monorepo root
npm run docker:up        # Start local infrastructure
npm run dev              # Start all services in parallel
npm run build            # Build all apps
npm run lint             # Lint all code
npm run test             # Run all tests
npm run format           # Format code with Prettier
npm run clean            # Clean all artifacts

# Docker
npm run docker:down      # Stop infrastructure
npm run docker:logs      # View infrastructure logs
```

### Code Organization

**Each app follows hexagonal architecture:**

- Controllers (HTTP adapters)
- Routes (API definitions)
- Serializers (DTOs)
- Adapters (Infrastructure)
- Mappers (ORM → Domain → DTO)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## 🧪 Testing

```bash
# Backend tests
cd apps/api
uv run pytest                    # All tests
uv run pytest --cov             # With coverage

# Frontend tests
cd ../web
npm run test                         # Jest/Vitest

# Workers tests
cd ../workers
uv run pytest
```

## 📦 Deployment

### Docker Build

```bash
# Build all images
docker build -t supportops-web:latest apps/web -f apps/web/Dockerfile
docker build -t supportops-api:latest apps/api -f apps/api/Dockerfile
docker build -t supportops-workers:latest apps/workers -f apps/workers/Dockerfile
```

### Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Redis password set
- [ ] S3/storage configured
- [ ] LLM API keys set
- [ ] CORS origins configured
- [ ] SSL/TLS enabled
- [ ] Logging centralized
- [ ] Monitoring/alerting set up

## 🔗 Resources

- [Architecture Deep Dive](docs/ARCHITECTURE.md)
- [Design System](docs/DESIGN.md)
- [API Documentation](http://localhost:8000/docs)
- [Database Schema](docs/DATABASE.md) (coming soon)

## 📖 Phase Roadmap

### Phase 1 - MVP (Weeks 1-2)

- ✅ Scaffold monorepo
- Document upload & versioning
- Basic RAG pipeline
- Frontend for documents & tickets
- Human review workflow

### Phase 2 - Production Ready (Weeks 3-4)

- Reranking
- Confidence scoring
- Metrics & evaluation
- Langsmith integration
- Hardening & testing

### Phase 3 - Advanced (Weeks 5+)

- RAGAS evaluation
- Fine-tuning pipelines
- Multi-language support
- Integrations (Zendesk, Intercom)

## 🤝 Contributing

1. Create a feature branch
2. Make changes following hexagonal architecture principles
3. Add tests
4. Format code with `npm run format`
5. Submit PR

## 📄 License

MIT

## 👤 Author

Created as a portfolio project demonstrating:

- Full-stack AI systems design
- Hexagonal architecture
- RAG implementation
- Production-grade Python/TypeScript
- Infrastructure as code
