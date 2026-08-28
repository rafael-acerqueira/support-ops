from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.celery_app import celery_app
from supportops_api.application.documents import ProcessDocument
from supportops_api.infrastructure.database import get_database_url
from supportops_api.infrastructure.embeddings import DeterministicEmbeddingGenerator
from supportops_api.infrastructure.persistence import PostgresDocumentRepository
from supportops_api.infrastructure.processing import BasicDocumentProcessor
from supportops_api.infrastructure.storage import get_local_document_storage


@celery_app.task(name="supportops.documents.process")
def process_document_task(document_id: str) -> dict[str, str]:
    return asyncio.run(_process_document(UUID(document_id)))


async def _process_document(document_id: UUID) -> dict[str, str]:
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            repository = PostgresDocumentRepository(session)
            processor = BasicDocumentProcessor(get_local_document_storage())
            embedding_generator = DeterministicEmbeddingGenerator()
            document = await ProcessDocument(
                repository,
                processor,
                embedding_generator,
            ).execute(document_id)
            await session.commit()

            return {
                "document_id": str(document.id),
                "status": document.status.value,
                "chunk_count": str(document.chunk_count),
            }
    finally:
        await engine.dispose()
