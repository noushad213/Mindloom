from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Edge, Group, Note, Page, Tag, Tagging, Workspace
from app.services.events import latest_seq, record_event
from app.schemas.workspaces import WorkspaceCreate, WorkspaceList, WorkspaceResponse, WorkspaceUpdate
from app.services.serialization import edge_body, group_body, note_body, page_body, tag_body, workspace_body


router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


def require_workspace(db: Session, workspace_id: UUID) -> Workspace:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("", status_code=201, response_model=WorkspaceResponse)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db)) -> dict:
    workspace = Workspace(**payload.model_dump())
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace_body(db, workspace)


@router.get("", response_model=WorkspaceList)
def list_workspaces(request: Request, include_archived: bool = False, db: Session = Depends(get_db)) -> dict:
    query = select(Workspace).order_by(Workspace.created_at.desc())
    shared_workspace_id = getattr(request.state, "shared_workspace_id", None)
    if shared_workspace_id is not None:
        query = query.where(Workspace.id == shared_workspace_id)
    if not include_archived:
        query = query.where(Workspace.archived_at.is_(None))
    return {"items": [workspace_body(db, workspace) for workspace in db.scalars(query).all()]}


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: UUID, db: Session = Depends(get_db)) -> dict:
    return workspace_body(db, require_workspace(db, workspace_id))


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(workspace_id: UUID, payload: WorkspaceUpdate, request: Request,
                     background: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    workspace = require_workspace(db, workspace_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None and key in {"name", "excluded_domains", "settings", "view_state", "tracking"}:
            raise HTTPException(status_code=422, detail=f"{key} cannot be null")
        setattr(workspace, key, value)
    db.flush()
    body = workspace_body(db, workspace)
    event = record_event(db, workspace_id, "workspace.updated", {"workspace": body})
    db.commit()
    background.add_task(request.app.state.ws_manager.broadcast, event)
    return body


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(workspace_id: UUID, db: Session = Depends(get_db)) -> Response:
    workspace = require_workspace(db, workspace_id)
    db.delete(workspace)
    db.commit()
    return Response(status_code=204)


@router.get("/{workspace_id}/graph")
def graph_snapshot(workspace_id: UUID, include_rejected: bool = False, db: Session = Depends(get_db)) -> dict:
    workspace = require_workspace(db, workspace_id)
    pages = db.scalars(select(Page).where(Page.workspace_id == workspace_id).order_by(Page.created_at)).all()
    edges = select(Edge).where(Edge.workspace_id == workspace_id)
    if not include_rejected:
        edges = edges.where(Edge.status != "rejected")
    groups = db.scalars(select(Group).where(Group.workspace_id == workspace_id)).all()
    notes = db.scalars(select(Note).where(Note.workspace_id == workspace_id)).all()
    tags = db.scalars(select(Tag).where(Tag.workspace_id == workspace_id)).all()
    return {"workspace": workspace_body(db, workspace), "pages": [page_body(db, page) for page in pages],
            "edges": [edge_body(edge) for edge in db.scalars(edges).all()],
            "groups": [group_body(db, group) for group in groups], "notes": [note_body(note) for note in notes],
            "tags": [tag_body(tag, db.scalar(select(func.count()).where(Tagging.tag_id == tag.id)) or 0) for tag in tags],
            "seq": latest_seq(db, workspace_id)}
