from __future__ import annotations

from supportops_api.application.documents import DocumentProcessor, DocumentStorage
from supportops_api.domain.documents import Document, DocumentChunk


class BasicDocumentProcessor(DocumentProcessor):
    def __init__(self, storage: DocumentStorage, *, max_chunk_chars: int = 1200) -> None:
        if max_chunk_chars <= 0:
            raise ValueError("max_chunk_chars must be greater than zero")

        self._storage = storage
        self._max_chunk_chars = max_chunk_chars

    async def process(self, document: Document) -> list[DocumentChunk]:
        if not document.storage_key:
            raise ValueError("Document has no storage key")
        if not _is_supported_content_type(document.content_type):
            raise ValueError(f"Unsupported content type: {document.content_type}")

        with await self._storage.open(document.storage_key) as file:
            content = file.read()

        text = content.decode("utf-8").strip()
        if not text:
            raise ValueError("Document content is empty")

        return [
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                metadata={"source_file_name": document.source_file_name},
            )
            for index, chunk in enumerate(_chunk_text(text, self._max_chunk_chars))
        ]


def _is_supported_content_type(content_type: str) -> bool:
    return content_type in {
        "text/plain",
        "text/markdown",
        "application/octet-stream",
    }


def _chunk_text(text: str, max_chunk_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chunk_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_text(paragraph, max_chunk_chars))
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chunk_chars:
            current = candidate
        else:
            chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def _split_long_text(text: str, max_chunk_chars: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chunk_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = word

    if current:
        chunks.append(current)

    return chunks
