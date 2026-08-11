from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.application.documents import DocumentRepository
from supportops_api.infrastructure.database import get_session
from supportops_api.infrastructure.persistence import PostgresDocumentRepository


def get_document_repository(
    session: AsyncSession = Depends(get_session),
) -> DocumentRepository:
    return PostgresDocumentRepository(session)
