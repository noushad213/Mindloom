from uuid import uuid4

import pytest

from app.schemas.pages import IngestPayload
from app.services.ingest import ingest_page
from app.models import Page, TabSession
from sqlalchemy import func, select


def test_page_upsert_and_event_receipt(postgres_session_factory, ingest_payload):
    from app.models import Workspace

    with postgres_session_factory.begin() as db:
        workspace = Workspace(name="Unit test")
        db.add(workspace)
        db.flush()
        workspace_id = workspace.id

    def submit(data):
        with postgres_session_factory.begin() as db:
            status_code, body, _accepted = ingest_page(db, workspace_id, IngestPayload.model_validate(data))
            return status_code, body

    from datetime import datetime, timezone

    ingest_payload["captured_at"] = datetime.now(timezone.utc)
    ingest_payload["client_event_id"] = uuid4()
    first_status, first = submit(ingest_payload)
    assert first_status == 201 and first["created"] is True
    with postgres_session_factory() as db:
        first_hash = db.scalar(select(Page.content_hash))
    same_status, same = submit(ingest_payload)
    assert same_status == 200 and same == first

    ingest_payload["client_event_id"] = uuid4()
    ingest_payload["url"] = "https://example.com/article?id=5&fbclid=other"
    second_status, second = submit(ingest_payload)
    assert second_status == 200 and second["page"]["id"] == first["page"]["id"]

    ingest_payload["client_event_id"] = uuid4()
    ingest_payload["text"] = "Changed article text"
    _, changed = submit(ingest_payload)
    assert changed["page"]["id"] == first["page"]["id"]
    with postgres_session_factory() as db:
        assert db.scalar(select(func.count(Page.id))) == 1
        assert db.scalar(select(func.count(TabSession.id))) == 1
        page = db.scalar(select(Page))
        assert page.text == "Changed article text"
        assert page.content_hash != first_hash
