from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.workspaces import require_workspace
from app.db.session import get_db
from app.models import Group, Note, Tag, Tagging
from app.services.graph import changed, require_target
from app.services.serialization import note_body, tag_body


router = APIRouter(prefix="/api/v1", tags=["annotations"])


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoteCreate(Strict):
    target_type: Literal["page", "group"]
    target_id: UUID
    kind: Literal["note", "highlight", "comment"]
    body: str = Field(min_length=1)
    quote: str | None = None
    author: str | None = None


class NoteUpdate(Strict):
    body: str = Field(min_length=1)


class TagCreate(Strict):
    name: str = Field(min_length=1, max_length=100)
    color: str


class TagUpdate(Strict):
    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = None


class TagTarget(Strict):
    target_type: Literal["page", "group"]
    target_id: UUID


def get_note(db: Session, note_id: UUID) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(404, "Note not found")
    return note


def get_tag(db: Session, tag_id: UUID) -> Tag:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(404, "Tag not found")
    return tag


def check_tag_name(db: Session, workspace_id: UUID, name: str, except_id: UUID | None = None) -> None:
    if not name.strip():
        raise HTTPException(422, "Tag name cannot be blank")
    duplicate = db.scalar(select(Tag.id).where(Tag.workspace_id == workspace_id, func.lower(Tag.name) == name.strip().lower()))
    if duplicate is not None and duplicate != except_id:
        raise HTTPException(409, "Tag name already exists")


def publish_annotation(db: Session, request: Request, background: BackgroundTasks, workspace_id: UUID,
                       target_type: str | None = None, target_id: UUID | None = None) -> None:
    changed(db, request, background, workspace_id,
            pages=[target_id] if target_type == "page" and target_id else [],
            groups=[target_id] if target_type == "group" and target_id else [])


@router.get("/workspaces/{workspace_id}/notes")
def list_notes(workspace_id: UUID, target_type: Literal["page", "group"] | None = None,
               target_id: UUID | None = None, db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    query = select(Note).where(Note.workspace_id == workspace_id)
    if target_type:
        query = query.where(Note.target_type == target_type)
    if target_id:
        query = query.where(Note.target_id == target_id)
    return {"items": [note_body(n) for n in db.scalars(query.order_by(Note.created_at)).all()]}


@router.post("/workspaces/{workspace_id}/notes", status_code=201)
def create_note(workspace_id: UUID, payload: NoteCreate, request: Request, background: BackgroundTasks,
                db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    require_target(db, workspace_id, payload.target_type, payload.target_id)
    note = Note(workspace_id=workspace_id, **payload.model_dump())
    db.add(note)
    if payload.target_type == "group":
        group = db.get(Group, payload.target_id)
        group.origin = "manual"
        group.status = "accepted"
    db.flush()
    publish_annotation(db, request, background, workspace_id, payload.target_type, payload.target_id)
    db.refresh(note)
    return note_body(note)


@router.patch("/notes/{note_id}")
def update_note(note_id: UUID, payload: NoteUpdate, request: Request, background: BackgroundTasks,
                db: Session = Depends(get_db)) -> dict:
    note = get_note(db, note_id)
    note.body = payload.body
    db.flush()
    publish_annotation(db, request, background, note.workspace_id, note.target_type, note.target_id)
    db.refresh(note)
    return note_body(note)


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: UUID, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)) -> Response:
    note = get_note(db, note_id)
    db.delete(note)
    publish_annotation(db, request, background, note.workspace_id, note.target_type, note.target_id)
    return Response(status_code=204)


@router.get("/workspaces/{workspace_id}/tags")
def list_tags(workspace_id: UUID, db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    tags = db.scalars(select(Tag).where(Tag.workspace_id == workspace_id).order_by(Tag.name)).all()
    return {"items": [tag_body(tag, db.scalar(select(func.count()).where(Tagging.tag_id == tag.id)) or 0) for tag in tags]}


@router.post("/workspaces/{workspace_id}/tags", status_code=201)
def create_tag(workspace_id: UUID, payload: TagCreate, request: Request, background: BackgroundTasks,
               db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    check_tag_name(db, workspace_id, payload.name)
    tag = Tag(workspace_id=workspace_id, name=payload.name.strip(), color=payload.color)
    db.add(tag)
    db.flush()
    publish_annotation(db, request, background, workspace_id)
    db.refresh(tag)
    return tag_body(tag, 0)


@router.patch("/tags/{tag_id}")
def update_tag(tag_id: UUID, payload: TagUpdate, request: Request, background: BackgroundTasks,
               db: Session = Depends(get_db)) -> dict:
    tag = get_tag(db, tag_id)
    if payload.name is not None:
        check_tag_name(db, tag.workspace_id, payload.name, tag_id)
        tag.name = payload.name.strip()
    if payload.color is not None:
        tag.color = payload.color
    db.flush()
    publish_annotation(db, request, background, tag.workspace_id)
    db.refresh(tag)
    return tag_body(tag, db.scalar(select(func.count()).where(Tagging.tag_id == tag.id)) or 0)


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(tag_id: UUID, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)) -> Response:
    tag = get_tag(db, tag_id)
    db.delete(tag)
    publish_annotation(db, request, background, tag.workspace_id)
    return Response(status_code=204)


@router.post("/tags/{tag_id}/attach", status_code=204)
def attach_tag(tag_id: UUID, payload: TagTarget, request: Request, background: BackgroundTasks,
               db: Session = Depends(get_db)) -> Response:
    tag = get_tag(db, tag_id)
    require_target(db, tag.workspace_id, payload.target_type, payload.target_id)
    if db.get(Tagging, (tag_id, payload.target_type, payload.target_id)) is None:
        db.add(Tagging(tag_id=tag_id, target_type=payload.target_type, target_id=payload.target_id))
        if payload.target_type == "group":
            group = db.get(Group, payload.target_id)
            group.origin = "manual"
            group.status = "accepted"
        publish_annotation(db, request, background, tag.workspace_id, payload.target_type, payload.target_id)
    return Response(status_code=204)


@router.post("/tags/{tag_id}/detach", status_code=204)
def detach_tag(tag_id: UUID, payload: TagTarget, request: Request, background: BackgroundTasks,
               db: Session = Depends(get_db)) -> Response:
    tag = get_tag(db, tag_id)
    link = db.get(Tagging, (tag_id, payload.target_type, payload.target_id))
    if link:
        db.delete(link)
        publish_annotation(db, request, background, tag.workspace_id, payload.target_type, payload.target_id)
    return Response(status_code=204)
