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
COPY apps/api/pyproject.toml ./
COPY apps/api/uv.lock* ./

# Install dependencies
RUN uv sync --frozen

# Copy source code
COPY apps/api/src ./src

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
