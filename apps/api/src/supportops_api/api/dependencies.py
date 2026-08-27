from __future__ import annotations

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
from supportops_api.infrastructure.embeddings import DeterministicEmbeddingGenerator
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
    BasicResponseSuggestionGenerator,
    BasicTicketKnowledgeRetriever,
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
    return DeterministicEmbeddingGenerator()


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
) -> TicketKnowledgeRetriever:
    return BasicTicketKnowledgeRetriever(repository)


def get_response_suggestion_generator(
    knowledge_retriever: TicketKnowledgeRetriever = Depends(get_ticket_knowledge_retriever),
) -> ResponseSuggestionGenerator:
    return BasicResponseSuggestionGenerator(knowledge_retriever)
