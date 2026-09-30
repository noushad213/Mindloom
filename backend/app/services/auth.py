from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Edge, Group, Note, Page, ProcessingJob, ShareLink, TabSession, Tag


def valid_share(db: Session, token: str) -> ShareLink | None:
    link = db.scalar(select(ShareLink).where(ShareLink.token == token))
    if link is None or link.revoked_at is not None:
        return None
    if link.expires_at is not None and link.expires_at <= datetime.now(timezone.utc):
        return None
    return link


def resource_workspace(db: Session, path: str) -> UUID | None:
    parts = path.strip("/").split("/")
    if len(parts) < 3 or parts[:2] != ["api", "v1"]:
        return None
    kind = parts[2]
    if kind == "workspaces":
        if len(parts) < 4 or parts[3] == "import":
            return None
        try:
            return UUID(parts[3])
        except ValueError:
            return None
    mapping = {"pages": Page, "edges": Edge, "groups": Group, "notes": Note,
               "tags": Tag, "jobs": ProcessingJob, "tab-sessions": TabSession, "shares": ShareLink}
    model = mapping.get(kind)
    if model is None or len(parts) < 4:
        return None
    try:
        item = db.get(model, UUID(parts[3]))
    except ValueError:
        return None
    return item.workspace_id if item else None


def edit_allowed(method: str, path: str) -> bool:
    if method == "GET":
        return True
    parts = path.strip("/").split("/")
    if len(parts) < 3:
        return False
    kind = parts[2]
    if kind == "workspaces":
        return (len(parts) >= 5 and parts[4] in {"edges", "groups", "notes", "tags"}) or (
            method == "PATCH" and len(parts) == 6 and parts[4:] == ["pages", "positions"])
    return kind in {"edges", "groups", "notes", "tags"}
