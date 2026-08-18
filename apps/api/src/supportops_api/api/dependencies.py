from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.application.documents import (
    DocumentProcessingQueue,
    DocumentProcessor,
    DocumentRepository,
    DocumentStorage,
)
from supportops_api.application.response_suggestions import (
    ResponseSuggestionGenerator,
    ResponseSuggestionRepository,
)
from supportops_api.application.tickets import TicketRepository
from supportops_api.infrastructure.database import get_session
from supportops_api.infrastructure.persistence import (
    PostgresDocumentRepository,
    PostgresResponseSuggestionRepository,
    PostgresTicketRepository,
)
from supportops_api.infrastructure.processing import BasicDocumentProcessor
from supportops_api.infrastructure.queues import CeleryDocumentProcessingQueue
from supportops_api.infrastructure.storage import get_local_document_storage
from supportops_api.infrastructure.suggestions import BasicResponseSuggestionGenerator


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


def get_response_suggestion_generator() -> ResponseSuggestionGenerator:
    return BasicResponseSuggestionGenerator()
