from __future__ import annotations

import os

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.application.documents import (
    DocumentProcessingQueue,
    DocumentProcessor,
    DocumentRepository,
    DocumentStorage,
    EmbeddingGenerator,
)
from supportops_api.application.response_suggestions import (
    KnowledgeSourceRepository,
    ResponseSuggestionGenerator,
    ResponseSuggestionRepository,
    TicketKnowledgeRetriever,
)
from supportops_api.application.tickets import TicketRepository
from supportops_api.infrastructure.database import get_session
from supportops_api.infrastructure.embeddings import get_embedding_generator_from_env
from supportops_api.infrastructure.persistence import (
    PostgresDocumentChunkRepository,
    PostgresDocumentRepository,
    PostgresResponseSuggestionRepository,
    PostgresTicketRepository,
)
from supportops_api.infrastructure.processing import BasicDocumentProcessor
from supportops_api.infrastructure.queues import CeleryDocumentProcessingQueue
from supportops_api.infrastructure.storage import get_local_document_storage
from supportops_api.infrastructure.suggestions import (
    BasicTicketKnowledgeRetriever,
    get_response_suggestion_generator_from_env,
)


def get_document_repository(
    session: AsyncSession = Depends(get_session),
) -> DocumentRepository:
    return PostgresDocumentRepository(session)


def get_document_storage() -> DocumentStorage:
    return get_local_document_storage()


def get_document_processor(
    storage: DocumentStorage = Depends(get_document_storage),
) -> DocumentProcessor:
    return BasicDocumentProcessor(storage)


def get_embedding_generator() -> EmbeddingGenerator:
    return get_embedding_generator_from_env()


def get_document_processing_queue(
    repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentProcessingQueue:
    return CeleryDocumentProcessingQueue(repository)


def get_ticket_repository(
    session: AsyncSession = Depends(get_session),
) -> TicketRepository:
    return PostgresTicketRepository(session)


def get_response_suggestion_repository(
    session: AsyncSession = Depends(get_session),
) -> ResponseSuggestionRepository:
    return PostgresResponseSuggestionRepository(session)


def get_knowledge_source_repository(
    session: AsyncSession = Depends(get_session),
) -> KnowledgeSourceRepository:
    return PostgresDocumentChunkRepository(session)


def get_ticket_knowledge_retriever(
    repository: KnowledgeSourceRepository = Depends(get_knowledge_source_repository),
    embedding_generator: EmbeddingGenerator = Depends(get_embedding_generator),
) -> TicketKnowledgeRetriever:
    return BasicTicketKnowledgeRetriever(
        repository,
        embedding_generator,
        min_relevance_score=_get_float_env("KNOWLEDGE_MIN_RELEVANCE_SCORE", 0.45),
    )


def get_response_suggestion_generator(
    knowledge_retriever: TicketKnowledgeRetriever = Depends(get_ticket_knowledge_retriever),
) -> ResponseSuggestionGenerator:
    return get_response_suggestion_generator_from_env(knowledge_retriever)


def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid number") from exc
