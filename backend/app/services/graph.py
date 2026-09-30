from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Group, Note, Page, Tagging
from app.services.events import record_event


def require_page(db: Session, workspace_id: UUID, page_id: UUID) -> Page:
    page = db.get(Page, page_id)
    if page is None or page.workspace_id != workspace_id:
        raise HTTPException(404, "Page not found")
    return page


def require_group(db: Session, group_id: UUID) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(404, "Group not found")
    return group


def require_target(db: Session, workspace_id: UUID, target_type: str, target_id: UUID) -> None:
    if target_type == "page":
        require_page(db, workspace_id, target_id)
    elif target_type == "group":
        group = require_group(db, target_id)
        if group.workspace_id != workspace_id:
            raise HTTPException(404, "Group not found")
    else:
        raise HTTPException(422, "Invalid target_type")


def delete_annotations(db: Session, target_type: str, target_id: UUID) -> None:
    db.execute(delete(Note).where(Note.target_type == target_type, Note.target_id == target_id))
    db.execute(delete(Tagging).where(Tagging.target_type == target_type, Tagging.target_id == target_id))


def changed(db: Session, request: Request, background: BackgroundTasks, workspace_id: UUID, *,
            pages: list[UUID] | None = None, edges: list[UUID] | None = None,
            groups: list[UUID] | None = None, reason: str = "manual_edit") -> None:
    event = record_event(db, workspace_id, "graph.changed", {"changed": {
        "pages": [str(value) for value in pages or []],
        "edges": [str(value) for value in edges or []],
        "groups": [str(value) for value in groups or []],
    }, "reason": reason})
    db.commit()
    background.add_task(request.app.state.ws_manager.broadcast, event)
