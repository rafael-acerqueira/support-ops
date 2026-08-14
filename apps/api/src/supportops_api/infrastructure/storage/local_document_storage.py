from __future__ import annotations

import os
import re
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from supportops_api.application.documents import StoredDocumentFile
from supportops_api.application.documents import DocumentStorage


class LocalDocumentStorage(DocumentStorage):
    def __init__(self, root_path: Path | str) -> None:
        self._root_path = Path(root_path)

    async def save(
        self,
        *,
        file_name: str,
        content_type: str,
        content: BinaryIO,
    ) -> StoredDocumentFile:
        safe_file_name = _safe_file_name(file_name)
        storage_key = f"{uuid4()}-{safe_file_name}"
        destination = self._path_for(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        size_bytes = 0
        with destination.open("wb") as output:
            while chunk := content.read(1024 * 1024):
                size_bytes += len(chunk)
                output.write(chunk)

        if size_bytes <= 0:
            destination.unlink(missing_ok=True)
            raise ValueError("Document file cannot be empty")

        return StoredDocumentFile(
            storage_key=storage_key,
            file_name=safe_file_name,
            content_type=content_type,
            size_bytes=size_bytes,
        )

    async def open(self, storage_key: str) -> BinaryIO:
        return self._path_for(storage_key).open("rb")

    def _path_for(self, storage_key: str) -> Path:
        path = (self._root_path / storage_key).resolve()
        root = self._root_path.resolve()

        if root != path and root not in path.parents:
            raise ValueError("Invalid storage key")

        return path


def _safe_file_name(file_name: str) -> str:
    name = Path(file_name.strip()).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")

    if not name:
        raise ValueError("File name is required")

    return name


def get_local_document_storage() -> LocalDocumentStorage:
    root_path = os.getenv("DOCUMENT_STORAGE_PATH", ".var/documents")
    return LocalDocumentStorage(root_path)
