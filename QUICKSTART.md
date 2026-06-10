# 🚀 Quick Start Guide

## Local Scaffold Setup

### Requirements

- Docker & Docker Compose plugin (`docker compose`)
- Node.js 18+
- Python 3.11+
- pnpm
- uv

### Go

```bash
# Clone/enter directory
cd supportops

# Copy env config
cp .env.example .env

# Auto setup
chmod +x scripts/setup.sh
bash scripts/setup.sh
```

Done! ✅

## Running Services

```bash
npm run docker:up
npm run dev
```

This starts the local infrastructure first, then runs frontend, API, and workers in parallel.

Local URLs:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- pgAdmin: http://localhost:5050
- MinIO console: http://localhost:9001

### Optional: Run Services Separately

```bash
npm run dev:web      # Frontend only
npm run dev:api      # Backend API only
npm run dev:workers  # Workers only
```

## Common Tasks

```bash
# Stop everything
npm run docker:down

# View logs
npm run docker:logs

# Run tests
npm run test

# Format code
npm run format

# Using Make (easier)
make help              # See all commands
make docker-up         # Start infra
make dev               # Start all services
make lint              # Check code
make test              # Run tests
```

## Current Scaffold Endpoints

```
GET / - Health/status endpoint
```

Planned MVP endpoints are documented in `README.md` and will be added with the business/domain implementation.

## Project Structure

```
supportops/
├── apps/
│   ├── web/          (Next.js frontend)
│   ├── api/          (FastAPI backend)
│   └── workers/      (Celery tasks)
├── packages/         (Shared code - future)
├── infra/            (Docker configs)
├── scripts/          (Dev scripts)
└── docs/             (Documentation)
```

## Key Files

- **README.md** - Full documentation
- **docs/ARCHITECTURE.md** - Hexagonal design explained
- **docs/DESIGN.md** - Visual design system
- **ROADMAP.md** - Implementation phases

## Troubleshooting

**Docker won't start?**

```bash
npm run docker:down
npm run docker:up
```

**Postgres connection error?**

```bash
docker ps              # Check containers running
docker logs supportops-postgres  # See Postgres logs
```

**uv lock issues?**

```bash
cd apps/api
uv lock --upgrade
```

**Need a fresh local database volume?**

```bash
docker compose down -v
npm run docker:up
```

## What's Next?

1. Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) to understand hexagonal design
2. Check [DESIGN.md](docs/DESIGN.md) for visual guidelines
3. Explore [ROADMAP.md](ROADMAP.md) for implementation phases
4. Start building! The current repo intentionally runs as a scaffold before database tables and business rules exist

Good luck! 🎉
