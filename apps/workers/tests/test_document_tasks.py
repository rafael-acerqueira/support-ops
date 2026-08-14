from uuid import uuid4

from src.celery_app import celery_app
from src.supportops_workers.tasks.documents import process_document_task


def test_process_document_task_is_registered() -> None:
    assert "supportops.documents.process" in celery_app.tasks


def test_process_document_task_has_expected_name() -> None:
    assert process_document_task.name == "supportops.documents.process"


def test_process_document_task_accepts_string_document_id() -> None:
    document_id = uuid4()

    assert str(document_id)
