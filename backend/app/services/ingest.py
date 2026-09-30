import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import IngestEvent, Page, TabSession, Workspace
from app.schemas.pages import IngestPayload, IngestResponse
from app.services.canonical_url import canonical_url
from app.services.serialization import page_body, tab_body


def is_excluded(domain: str, excluded_domains: list[str]) -> bool:
    return any(domain == item.lower().lstrip(".") or domain.endswith("." + item.lower().lstrip(".")) for item in excluded_domains)


def prepare_content(payload: IngestPayload, max_chars: int) -> tuple[str, str, str | None, str | None]:
    content = payload.text.strip()[:max_chars]
    failed = payload.extraction.status == "failed" or not content
    status = "extraction_failed" if failed else "extracted"
    error_code = payload.extraction.error_code if payload.extraction.status == "failed" else "empty_content" if not content else None
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest() if content else None
    return content, status, error_code, content_hash


def ingest_page(db: Session, workspace_id: UUID, payload: IngestPayload) -> tuple[int, dict, bool]:
    """Caller owns a transaction. The event receipt and both upserts commit atomically."""
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    prior = db.get(IngestEvent, (workspace_id, payload.client_event_id))
    if prior is not None:
        return prior.status_code, prior.response_body, False

    normalized = canonical_url(payload.url)
    domain = urlsplit(normalized).hostname or ""
    if is_excluded(domain, workspace.excluded_domains):
        raise HTTPException(status_code=422, detail="excluded_domain")

    reservation = db.execute(
        insert(IngestEvent)
        .values(workspace_id=workspace_id, client_event_id=payload.client_event_id, response_body={}, status_code=0)
        .on_conflict_do_nothing(index_elements=[IngestEvent.workspace_id, IngestEvent.client_event_id])
        .returning(IngestEvent.client_event_id)
    ).scalar_one_or_none()
    if reservation is None:
        prior = db.get(IngestEvent, (workspace_id, payload.client_event_id))
        assert prior is not None
        return prior.status_code, prior.response_body, False

    content, status, error_code, content_hash = prepare_content(payload, get_settings().max_text_chars)
    extraction_failed = status == "extraction_failed"
    error_message = payload.extraction.error_message if extraction_failed else None
    now = datetime.now(timezone.utc)
    page_id = uuid4()
    page_insert = insert(Page).values(
        id=page_id,
        workspace_id=workspace_id,
        url=payload.url,
        canonical_url=normalized,
        title=payload.title,
        domain=domain,
        favicon_url=payload.meta.favicon,
        og_image_url=payload.meta.og_image,
        meta=payload.meta.model_dump(exclude_none=True),
        text=content or None,
        content_hash=content_hash,
        status=status,
        error_code=error_code,
        error_message=error_message,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    changed = Page.content_hash.is_distinct_from(content_hash)
    page_row = db.execute(
        page_insert.on_conflict_do_update(
            constraint="uq_pages_workspace_canonical_url",
            set_={
                "url": payload.url,
                "title": payload.title,
                "favicon_url": payload.meta.favicon,
                "og_image_url": payload.meta.og_image,
                "meta": payload.meta.model_dump(exclude_none=True),
                "last_seen_at": now,
                "updated_at": now,
                "text": Page.text if extraction_failed else page_insert.excluded.text,
                "content_hash": Page.content_hash if extraction_failed else page_insert.excluded.content_hash,
                "status": "extraction_failed" if extraction_failed else case((changed | (Page.status == "extraction_failed"), "extracted"), else_=Page.status),
                "error_code": error_code if extraction_failed else None,
                "error_message": error_message if extraction_failed else None,
            },
        ).returning(Page.id, Page.created_at)
    ).one()
    # A newly inserted row keeps the ID generated above; conflict updates return the old ID.
    created = page_row.id == page_id
    page = db.get(Page, page_row.id, populate_existing=True)
    assert page is not None
    tab_id = uuid4()
    tab_insert = insert(TabSession).values(
        id=tab_id,
        workspace_id=workspace_id,
        page_id=page.id,
        browser_tab_id=payload.tab.browser_tab_id,
        window_id=payload.tab.window_id,
        state="open",
        active=payload.tab.active,
        opened_at=now,
        last_seen_at=now,
        closed_at=None,
    )
    actual_tab_id = db.execute(
        tab_insert.on_conflict_do_update(
            constraint="uq_tab_sessions_workspace_tab_page",
            set_={"window_id": payload.tab.window_id, "state": "open", "active": payload.tab.active, "last_seen_at": now, "closed_at": None},
        ).returning(TabSession.id)
    ).scalar_one()
    tab = db.get(TabSession, actual_tab_id, populate_existing=True)
    assert tab is not None
    body = {
        "page": page_body(db, page),
        "tab_session": tab_body(tab),
        "created": created,
        "duplicate_of": None,
        "job": "queued",
    }
    IngestResponse.model_validate_json(json.dumps(body))
    receipt = db.get(IngestEvent, (workspace_id, payload.client_event_id))
    assert receipt is not None
    receipt.response_body = body
    receipt.status_code = 201 if created else 200
    db.flush()
    return receipt.status_code, body, True
