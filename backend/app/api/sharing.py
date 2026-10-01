import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.workspaces import require_workspace
from app.db.session import get_db
from app.models import ShareLink
from app.services.auth import valid_share


router = APIRouter(prefix="/api/v1", tags=["sharing"])


class ShareCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["view", "edit"]
    expires_in_days: int | None = Field(None, ge=1, le=365)


def share_body(link: ShareLink, include_token: bool = False) -> dict:
    body = {"id": str(link.id), "role": link.role,
            "expires_at": link.expires_at.isoformat() if link.expires_at else None}
    if include_token:
        body["token"] = link.token
        body["url"] = f"http://localhost:5173/s/{link.token}"
    return body


@router.post("/workspaces/{workspace_id}/share", status_code=201)
def create_share(workspace_id: UUID, payload: ShareCreate, db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days) if payload.expires_in_days else None
    link = ShareLink(workspace_id=workspace_id, token=secrets.token_urlsafe(32), role=payload.role, expires_at=expires_at)
    db.add(link)
    db.commit()
    db.refresh(link)
    return share_body(link, include_token=True)


@router.get("/workspaces/{workspace_id}/shares")
def list_shares(workspace_id: UUID, db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    links = db.scalars(select(ShareLink).where(ShareLink.workspace_id == workspace_id, ShareLink.revoked_at.is_(None))).all()
    return {"items": [share_body(link) for link in links]}


@router.delete("/shares/{share_id}", status_code=204)
def revoke_share(share_id: UUID, db: Session = Depends(get_db)) -> Response:
    link = db.get(ShareLink, share_id)
    if link is None:
        raise HTTPException(404, "Share link not found")
    link.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)


@router.get("/shared/{token}")
def resolve_share(token: str, db: Session = Depends(get_db)) -> dict:
    link = valid_share(db, token)
    if link is None:
        raise HTTPException(404, "Share link not found")
    return {"workspace_id": str(link.workspace_id), "role": link.role}
