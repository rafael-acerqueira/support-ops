FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy pyproject.toml and uv.lock
COPY apps/workers/pyproject.toml ./
COPY apps/workers/uv.lock* ./

# Install dependencies
RUN uv sync --frozen

# Copy source code
COPY apps/workers/src ./src

CMD ["celery", "-A", "src.celery_app", "worker", "--loglevel=info"]
