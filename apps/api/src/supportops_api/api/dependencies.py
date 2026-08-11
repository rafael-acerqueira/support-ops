from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.application.documents import DocumentRepository, DocumentStorage
from supportops_api.infrastructure.database import get_session
from supportops_api.infrastructure.persistence import PostgresDocumentRepository
from supportops_api.infrastructure.storage import get_local_document_storage


def get_document_repository(
    session: AsyncSession = Depends(get_session),
) -> DocumentRepository:
    return PostgresDocumentRepository(session)


def get_document_storage() -> DocumentStorage:
    return get_local_document_storage()
