import os
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_db = os.getenv("REDIS_DB", "0")
broker_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

celery_app = Celery("supportops_workers", broker=broker_url)

# Example configuration; adjust in production
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
