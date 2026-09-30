from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import EventLog, Workspace
from app.schemas.pages import PageResponse


EVENT_FIELDS: dict[str, set[str]] = {
    "page.discovered": {"page"},
    "page.extraction_completed": {"page_id", "status"},
    "page.extraction_failed": {"page_id", "error_code", "error_message"},
    "page.processing_completed": {"page"},
    "page.processing_failed": {"page_id", "error_message"},
    "graph.changed": {"changed", "reason"},
    "workspace.updated": {"workspace"},
}


def latest_seq(db: Session, workspace_id: UUID) -> int:
    return db.scalar(select(EventLog.seq).where(EventLog.workspace_id == workspace_id).order_by(EventLog.seq.desc()).limit(1)) or 0


def envelope(event_type: str, workspace_id: UUID, seq: int, data: dict, ts: datetime | None = None) -> dict:
    instant = (ts or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {"type": event_type, "workspace_id": str(workspace_id), "seq": seq, "ts": instant.isoformat().replace("+00:00", "Z"), "data": data}


def record_event(db: Session, workspace_id: UUID, event_type: str, data: dict) -> dict:
    if event_type not in EVENT_FIELDS or set(data) != EVENT_FIELDS[event_type]:
        raise ValueError(f"Invalid {event_type} event payload")
    if event_type in {"page.discovered", "page.processing_completed"}:
        PageResponse.model_validate(data["page"])
    if event_type == "page.extraction_completed" and data["status"] != "extracted":
        raise ValueError("Invalid extraction completion status")
    # NO KEY UPDATE serializes sequence allocation without conflicting with the
    # KEY SHARE lock taken by new child rows referencing this workspace.
    db.execute(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update(key_share=True)).scalar_one()
    seq = latest_seq(db, workspace_id) + 1
    now = datetime.now(timezone.utc)
    db.add(EventLog(workspace_id=workspace_id, seq=seq, type=event_type, payload=data, created_at=now))
    if seq > 500:
        db.execute(delete(EventLog).where(EventLog.workspace_id == workspace_id, EventLog.seq <= seq - 500))
    db.flush()
    return envelope(event_type, workspace_id, seq, data, now)
