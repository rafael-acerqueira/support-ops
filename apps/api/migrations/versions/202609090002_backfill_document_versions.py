from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "202609090002"
down_revision: str | None = "202609090001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    documents_without_versions = connection.execute(
        sa.text(
            """
            select
              d.id,
              d.version,
              d.status,
              d.is_active,
              d.source_file_name,
              d.storage_key,
              d.content_type,
              d.size_bytes,
              d.chunk_count,
              d.failure_reason,
              d.last_processed_at,
              d.created_at,
              d.updated_at
            from documents d
            where d.storage_key is not null
              and not exists (
                select 1
                from document_versions dv
                where dv.document_id = d.id
              )
            """
        )
    ).mappings()

    for document in documents_without_versions:
        version_id = uuid4()
        is_active_version = document["status"] == "indexed" and bool(document["is_active"])
        activated_at = document["updated_at"] if is_active_version else None

        connection.execute(
            sa.text(
                """
                insert into document_versions (
                  id,
                  document_id,
                  version,
                  status,
                  is_active,
                  source_file_name,
                  storage_key,
                  content_type,
                  size_bytes,
                  chunk_count,
                  failure_reason,
                  activated_at,
                  last_processed_at,
                  created_at,
                  updated_at
                )
                values (
                  :id,
                  :document_id,
                  :version,
                  :status,
                  :is_active,
                  :source_file_name,
                  :storage_key,
                  :content_type,
                  :size_bytes,
                  :chunk_count,
                  :failure_reason,
                  :activated_at,
                  :last_processed_at,
                  :created_at,
                  :updated_at
                )
                """
            ),
            {
                "id": version_id,
                "document_id": document["id"],
                "version": document["version"],
                "status": document["status"],
                "is_active": is_active_version,
                "source_file_name": document["source_file_name"],
                "storage_key": document["storage_key"],
                "content_type": document["content_type"],
                "size_bytes": document["size_bytes"],
                "chunk_count": document["chunk_count"],
                "failure_reason": document["failure_reason"],
                "activated_at": activated_at,
                "last_processed_at": document["last_processed_at"],
                "created_at": document["created_at"],
                "updated_at": document["updated_at"],
            },
        )

    connection.execute(
        sa.text(
            """
            update document_chunks dc
            set document_version_id = dv.id
            from document_versions dv
            where dv.document_id = dc.document_id
              and dv.is_active = true
              and dc.document_version_id is null
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            update document_chunks
            set document_version_id = null
            where document_version_id in (
              select dv.id
              from document_versions dv
              join documents d on d.id = dv.document_id
              join (
                select document_id, count(*) as version_count
                from document_versions
                group by document_id
              ) counts on counts.document_id = dv.document_id
              where dv.version = d.version
                and dv.storage_key = d.storage_key
                and counts.version_count = 1
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            delete from document_versions dv
            using documents d
            where d.id = dv.document_id
              and dv.version = d.version
              and dv.storage_key = d.storage_key
              and (
                select count(*)
                from document_versions existing
                where existing.document_id = dv.document_id
              ) = 1
            """
        )
    )
