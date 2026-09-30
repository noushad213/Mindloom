from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.workspaces import require_workspace
from app.db.session import get_db
from app.models import Edge, Group, GroupMember, Page
from app.services.graph import changed, delete_annotations, require_group, require_page
from app.services.serialization import edge_body, group_body, page_body


router = APIRouter(prefix="/api/v1", tags=["graph"])


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EdgeCreate(Strict):
    source: UUID
    target: UUID
    type: Literal["related_to", "source_of", "answers", "supports", "references", "navigated_to", "duplicate_of", "custom"]
    label: str | None = None


class EdgeUpdate(Strict):
    type: Literal["related_to", "source_of", "answers", "supports", "references", "navigated_to", "duplicate_of", "custom"] | None = None
    label: str | None = None
    swap_direction: bool = False


class GroupCreate(Strict):
    name: str = Field(min_length=1)
    category: Literal["topic", "source", "importance", "custom"]
    color: str
    page_ids: list[UUID] = Field(default_factory=list)


class GroupUpdate(Strict):
    name: str | None = Field(None, min_length=1)
    category: Literal["topic", "source", "importance", "custom"] | None = None
    color: str | None = None
    collapsed: bool | None = None


class GroupMembers(Strict):
    page_ids: list[UUID]


class PositionItem(Strict):
    id: UUID
    x: float
    y: float


class Positions(Strict):
    positions: list[PositionItem]


class Point(Strict):
    x: float
    y: float


class PageUpdate(Strict):
    pos: Point | None = None
    title: str | None = None
    importance: int | None = Field(None, ge=1, le=5)


def get_edge(db: Session, edge_id: UUID) -> Edge:
    edge = db.get(Edge, edge_id)
    if edge is None:
        raise HTTPException(404, "Edge not found")
    return edge


def normalize_pair(source: UUID, target: UUID, edge_type: str) -> tuple[UUID, UUID]:
    if edge_type in {"related_to", "duplicate_of"} and str(source) > str(target):
        return target, source
    return source, target


@router.get("/workspaces/{workspace_id}/edges")
def list_edges(workspace_id: UUID, origin: Literal["suggested", "manual"] | None = None,
               status: Literal["suggested", "accepted", "rejected"] | None = None,
               page_id: UUID | None = None, db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    query = select(Edge).where(Edge.workspace_id == workspace_id)
    if origin:
        query = query.where(Edge.origin == origin)
    if status:
        query = query.where(Edge.status == status)
    else:
        query = query.where(Edge.status != "rejected")
    if page_id:
        query = query.where((Edge.source_page_id == page_id) | (Edge.target_page_id == page_id))
    return {"items": [edge_body(e) for e in db.scalars(query.order_by(Edge.created_at)).all()]}


@router.post("/workspaces/{workspace_id}/edges", status_code=201)
def create_edge(workspace_id: UUID, payload: EdgeCreate, request: Request, background: BackgroundTasks,
                db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    require_page(db, workspace_id, payload.source)
    require_page(db, workspace_id, payload.target)
    if payload.source == payload.target:
        raise HTTPException(422, "An edge needs two different pages")
    source, target = normalize_pair(payload.source, payload.target, payload.type)
    existing = db.scalar(select(Edge).where(Edge.workspace_id == workspace_id, Edge.source_page_id == source,
                                           Edge.target_page_id == target, Edge.type == payload.type))
    if existing:
        raise HTTPException(409, "Edge already exists")
    edge = Edge(workspace_id=workspace_id, source_page_id=source, target_page_id=target,
                type=payload.type, label=payload.label, origin="manual", status="accepted")
    db.add(edge)
    db.flush()
    changed(db, request, background, workspace_id, edges=[edge.id])
    db.refresh(edge)
    return edge_body(edge)


@router.patch("/edges/{edge_id}")
def update_edge(edge_id: UUID, payload: EdgeUpdate, request: Request, background: BackgroundTasks,
                db: Session = Depends(get_db)) -> dict:
    edge = get_edge(db, edge_id)
    if edge.status == "rejected":
        raise HTTPException(409, "Restore the rejected edge first")
    if payload.swap_direction:
        edge.source_page_id, edge.target_page_id = edge.target_page_id, edge.source_page_id
    if "type" in payload.model_fields_set:
        if payload.type is None:
            raise HTTPException(422, "type cannot be null")
        edge.type = payload.type
    if "label" in payload.model_fields_set:
        edge.label = payload.label
    edge.source_page_id, edge.target_page_id = normalize_pair(edge.source_page_id, edge.target_page_id, edge.type)
    existing = db.scalar(select(Edge.id).where(Edge.workspace_id == edge.workspace_id,
        Edge.source_page_id == edge.source_page_id, Edge.target_page_id == edge.target_page_id,
        Edge.type == edge.type, Edge.id != edge.id))
    if existing is not None:
        raise HTTPException(409, "Edge already exists")
    edge.status = "accepted"
    db.flush()
    changed(db, request, background, edge.workspace_id, edges=[edge.id])
    db.refresh(edge)
    return edge_body(edge)


@router.post("/edges/{edge_id}/accept")
def accept_edge(edge_id: UUID, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    edge = get_edge(db, edge_id)
    if edge.status == "rejected":
        raise HTTPException(409, "Restore the rejected edge first")
    edge.status = "accepted"
    db.flush()
    changed(db, request, background, edge.workspace_id, edges=[edge.id])
    db.refresh(edge)
    return edge_body(edge)


@router.delete("/edges/{edge_id}", status_code=204)
def delete_edge(edge_id: UUID, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)) -> Response:
    edge = get_edge(db, edge_id)
    workspace_id = edge.workspace_id
    if edge.origin == "suggested":
        edge.status = "rejected"
    else:
        db.delete(edge)
    changed(db, request, background, workspace_id, edges=[edge_id])
    return Response(status_code=204)


@router.post("/edges/{edge_id}/restore", status_code=204)
def restore_edge(edge_id: UUID, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)) -> Response:
    edge = get_edge(db, edge_id)
    if edge.status != "rejected":
        raise HTTPException(409, "Edge is not rejected")
    workspace_id = edge.workspace_id
    db.delete(edge)
    changed(db, request, background, workspace_id, edges=[edge_id])
    return Response(status_code=204)


@router.get("/workspaces/{workspace_id}/groups")
def list_groups(workspace_id: UUID, db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    return {"items": [group_body(db, g) for g in db.scalars(select(Group).where(Group.workspace_id == workspace_id).order_by(Group.created_at)).all()]}


@router.post("/workspaces/{workspace_id}/groups", status_code=201)
def create_group(workspace_id: UUID, payload: GroupCreate, request: Request, background: BackgroundTasks,
                 db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    for page_id in set(payload.page_ids):
        require_page(db, workspace_id, page_id)
    group = Group(workspace_id=workspace_id, name=payload.name, category=payload.category, color=payload.color,
                  origin="manual", status="accepted", keywords=[])
    db.add(group)
    db.flush()
    for page_id in set(payload.page_ids):
        db.add(GroupMember(group_id=group.id, page_id=page_id, origin="manual"))
    db.flush()
    changed(db, request, background, workspace_id, groups=[group.id], pages=list(set(payload.page_ids)))
    return group_body(db, group)


@router.patch("/groups/{group_id}")
def update_group(group_id: UUID, payload: GroupUpdate, request: Request, background: BackgroundTasks,
                 db: Session = Depends(get_db)) -> dict:
    group = require_group(db, group_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None:
            raise HTTPException(422, f"{key} cannot be null")
        setattr(group, key, value)
    group.origin = "manual"
    group.status = "accepted"
    db.flush()
    changed(db, request, background, group.workspace_id, groups=[group.id])
    return group_body(db, group)


@router.post("/groups/{group_id}/members")
def add_members(group_id: UUID, payload: GroupMembers, request: Request, background: BackgroundTasks,
                db: Session = Depends(get_db)) -> dict:
    group = require_group(db, group_id)
    for page_id in set(payload.page_ids):
        require_page(db, group.workspace_id, page_id)
    existing = set(db.scalars(select(GroupMember.page_id).where(GroupMember.group_id == group_id)).all())
    for page_id in set(payload.page_ids) - existing:
        db.add(GroupMember(group_id=group_id, page_id=page_id, origin="manual"))
    group.origin = "manual"
    group.status = "accepted"
    db.flush()
    changed(db, request, background, group.workspace_id, groups=[group.id], pages=list(set(payload.page_ids)))
    return group_body(db, group)


@router.delete("/groups/{group_id}/members/{page_id}")
def remove_member(group_id: UUID, page_id: UUID, request: Request, background: BackgroundTasks,
                  db: Session = Depends(get_db)) -> dict:
    group = require_group(db, group_id)
    member = db.get(GroupMember, (group_id, page_id))
    if member is None:
        raise HTTPException(404, "Group member not found")
    db.delete(member)
    group.origin = "manual"
    group.status = "accepted"
    db.flush()
    changed(db, request, background, group.workspace_id, groups=[group.id], pages=[page_id])
    return group_body(db, group)


@router.post("/groups/{group_id}/accept")
def accept_group(group_id: UUID, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    group = require_group(db, group_id)
    group.status = "accepted"
    db.flush()
    changed(db, request, background, group.workspace_id, groups=[group.id])
    return group_body(db, group)


@router.delete("/groups/{group_id}", status_code=204)
def delete_group(group_id: UUID, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)) -> Response:
    group = require_group(db, group_id)
    workspace_id = group.workspace_id
    delete_annotations(db, "group", group_id)
    db.delete(group)
    changed(db, request, background, workspace_id, groups=[group_id])
    return Response(status_code=204)


@router.patch("/pages/{page_id}")
def update_page(page_id: UUID, payload: PageUpdate, request: Request, background: BackgroundTasks,
                db: Session = Depends(get_db)) -> dict:
    page = db.get(Page, page_id)
    if page is None:
        raise HTTPException(404, "Page not found")
    if "pos" in payload.model_fields_set:
        page.pos_x = payload.pos.x if payload.pos else None
        page.pos_y = payload.pos.y if payload.pos else None
    for key in ("title", "importance"):
        if key in payload.model_fields_set:
            setattr(page, key, getattr(payload, key))
    db.flush()
    changed(db, request, background, page.workspace_id, pages=[page.id])
    return page_body(db, page)


@router.patch("/workspaces/{workspace_id}/pages/positions")
def update_positions(workspace_id: UUID, payload: Positions, request: Request, background: BackgroundTasks,
                     db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    if len({p.id for p in payload.positions}) != len(payload.positions):
        raise HTTPException(422, "Duplicate page id")
    pages = {item.id: require_page(db, workspace_id, item.id) for item in payload.positions}
    for item in payload.positions:
        pages[item.id].pos_x = item.x
        pages[item.id].pos_y = item.y
    db.flush()
    changed(db, request, background, workspace_id, pages=list(pages))
    return {"updated": len(pages)}
