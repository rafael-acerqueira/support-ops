from io import BytesIO

import pytest

from supportops_api.infrastructure.storage import LocalDocumentStorage


@pytest.mark.asyncio
async def test_local_document_storage_saves_file(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path)

    stored_file = await storage.save(
        file_name="../Refund Policy.md",
        content_type="text/markdown",
        content=BytesIO(b"Refund policy content"),
    )

    assert stored_file.file_name == "Refund-Policy.md"
    assert stored_file.content_type == "text/markdown"
    assert stored_file.size_bytes == len(b"Refund policy content")
    assert stored_file.storage_key.endswith("-Refund-Policy.md")

    with await storage.open(stored_file.storage_key) as saved_file:
        assert saved_file.read() == b"Refund policy content"


@pytest.mark.asyncio
async def test_local_document_storage_rejects_empty_file(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path)

    with pytest.raises(ValueError, match="cannot be empty"):
        await storage.save(
            file_name="empty.md",
            content_type="text/markdown",
            content=BytesIO(b""),
        )


@pytest.mark.asyncio
async def test_local_document_storage_rejects_invalid_file_name(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path)

    with pytest.raises(ValueError, match="File name is required"):
        await storage.save(
            file_name="...",
            content_type="text/markdown",
            content=BytesIO(b"content"),
        )


@pytest.mark.asyncio
async def test_local_document_storage_rejects_path_traversal(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path)

    with pytest.raises(ValueError, match="Invalid storage key"):
        await storage.open("../secret.md")
