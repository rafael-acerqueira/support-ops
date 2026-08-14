FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy local Python packages required by the worker
COPY apps/api /app/apps/api
COPY apps/workers /app/apps/workers

WORKDIR /app/apps/workers

# Install dependencies
RUN uv sync --frozen

CMD ["celery", "-A", "src.celery_app", "worker", "--loglevel=info"]
