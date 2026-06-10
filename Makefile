# Makefile for common development tasks

.PHONY: help setup dev stop logs lint format test clean docker-up docker-down

help:
	@echo "SupportOps - Development Commands"
	@echo ""
	@echo "Setup & Infrastructure:"
	@echo "  make setup          - Initialize project (one-time)"
	@echo "  make docker-up      - Start Docker services"
	@echo "  make docker-down    - Stop Docker services"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Start all services"
	@echo "  make dev-web        - Start frontend only"
	@echo "  make dev-api        - Start API only"
	@echo "  make dev-workers    - Start workers only"
	@echo ""
	@echo "Quality:"
	@echo "  make lint           - Run linters"
	@echo "  make format         - Format code"
	@echo "  make test           - Run all tests"
	@echo "  make test-watch     - Run tests in watch mode"
	@echo ""
	@echo "Utilities:"
	@echo "  make logs           - View Docker logs"
	@echo "  make clean          - Clean artifacts"
	@echo "  make db-migrate     - Placeholder for future database migrations"

setup:
	@chmod +x scripts/setup.sh
	@bash scripts/setup.sh

docker-up:
	docker compose up -d
	@echo "✅ Docker services started"

docker-down:
	docker compose down
	@echo "✅ Docker services stopped"

docker-logs:
	docker compose logs -f

dev:
	npm run dev

dev-web:
	npm run dev:web

dev-api:
	npm run dev:api

dev-workers:
	npm run dev:workers

lint:
	npm run lint

format:
	npm run format

test:
	npm run test

test-watch:
	npm run test:watch

db-migrate:
	@echo "Database migrations are not configured yet for the scaffold."

db-migrate-create:
	@echo "Alembic will be added when database models are implemented."

clean:
	npm run clean
	rm -rf apps/api/.pytest_cache
	rm -rf apps/workers/.pytest_cache

type-check:
	npm run type-check
