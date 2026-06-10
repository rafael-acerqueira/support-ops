#!/bin/bash

# SupportOps - Development Setup Script

set -e

echo "🚀 SupportOps - Setup"
echo "===================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install from https://docker.com"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Install from https://nodejs.org"
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    echo "pnpm not found. Attempting to enable via corepack..."
    if command -v corepack &> /dev/null; then
        corepack enable || true
        corepack prepare pnpm@latest --activate || true
    else
        echo "corepack not available. Trying to install pnpm globally via npm..."
        npm install -g pnpm || true
    fi
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install from https://python.org"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "❌ UV not found. Install from https://astral.sh/uv"
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Create .env if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ .env created. Review it before proceeding."
fi

echo ""
echo "🐳 Starting Docker services..."
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo "❌ 'docker compose' not found. Install Docker Compose plugin."
    exit 1
fi

$DOCKER_COMPOSE_CMD up -d

# Wait for Postgres
echo "⏳ Waiting for Postgres to be ready..."
until docker exec supportops-postgres pg_isready -U "${DB_USER:-supportops}" > /dev/null 2>&1; do
    sleep 1
done
echo "✅ Postgres ready"

echo ""
echo "📦 Installing Node dependencies..."
pnpm install

echo ""
echo "🐍 Installing Python API dependencies..."
cd apps/api
uv sync
cd ../..  

echo ""
echo "🐍 Installing Python Workers dependencies..."
cd apps/workers
uv sync
cd ../..  

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo ""
echo "1. Start frontend, API, and workers:"
echo "   npm run dev"
echo ""
echo "2. View services:"
echo "   - Frontend: http://localhost:3000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - pgAdmin: http://localhost:5050"
echo "   - MinIO: http://localhost:9001"
echo "   - Flower (Workers): uv run celery -A src.celery_app flower --port=5555"
echo ""
echo "3. Stop infrastructure:"
echo "   npm run docker:down"
echo ""
