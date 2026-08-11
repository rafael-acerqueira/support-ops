from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from supportops_api.api.dependencies import get_document_repository
from supportops_api.api.schemas import CreateDocumentRequest, DocumentResponse
from supportops_api.application.documents import (
    ActivateDocument,
    CreateDocument,
    CreateDocumentInput,
    DeactivateDocument,
    DocumentNotFoundError,
    DocumentRepository,
    GetDocument,
    ListDocuments,
)
from supportops_api.infrastructure.database import get_session

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _not_found_error(error: DocumentNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"message": "Document not found", "document_id": str(error.document_id)},
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: CreateDocumentRequest,
    repository: DocumentRepository = Depends(get_document_repository),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    use_case = CreateDocument(repository)
    document = await use_case.execute(
        CreateDocumentInput(
            name=payload.name,
            document_type=payload.document_type,
            product_area=payload.product_area,
            source_file_name=payload.source_file_name,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            tags=tuple(payload.tags),
        )
    )

    await session.commit()
    return DocumentResponse.from_domain(document)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    repository: DocumentRepository = Depends(get_document_repository),
) -> list[DocumentResponse]:
    documents = await ListDocuments(repository).execute()
    return [DocumentResponse.from_domain(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentResponse:
    try:
        document = await GetDocument(repository).execute(document_id)
    except DocumentNotFoundError as error:
        raise _not_found_error(error) from error

    return DocumentResponse.from_domain(document)


@router.post("/{document_id}/activate", response_model=DocumentResponse)
async def activate_document(
    document_id: UUID,
    repository: DocumentRepository = Depends(get_document_repository),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    try:
        document = await ActivateDocument(repository).execute(document_id)
    except DocumentNotFoundError as error:
        raise _not_found_error(error) from error

    await session.commit()
    return DocumentResponse.from_domain(document)


@router.post("/{document_id}/deactivate", response_model=DocumentResponse)
async def deactivate_document(
    document_id: UUID,
    repository: DocumentRepository = Depends(get_document_repository),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    try:
        document = await DeactivateDocument(repository).execute(document_id)
    except DocumentNotFoundError as error:
        raise _not_found_error(error) from error

    await session.commit()
    return DocumentResponse.from_domain(document)
