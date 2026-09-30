import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.api.workspaces import require_workspace
from app.db.session import get_db
from app.services.export import export_markdown, export_workspace


router = APIRouter(prefix="/api/v1", tags=["export"])


@router.get("/workspaces/{workspace_id}/export")
def export(workspace_id: UUID, format: Literal["json", "md"] = "json", include_text: bool = False,
           db: Session = Depends(get_db)) -> Response:
    workspace = require_workspace(db, workspace_id)
    data = export_workspace(db, workspace, include_text)
    filename = re.sub(r"[^A-Za-z0-9_-]+", "-", workspace.name).strip("-") or "workspace"
    if format == "md":
        return Response(export_markdown(data), media_type="text/markdown; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{filename}.mindloom.md"'})
    return JSONResponse(data, headers={"Content-Disposition": f'attachment; filename="{filename}.mindloom.json"'})
