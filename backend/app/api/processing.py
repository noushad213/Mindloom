from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.workspaces import require_workspace
from app.db.session import get_db
from app.models import Page, ProcessingJob


router = APIRouter(prefix="/api/v1", tags=["processing"])


class RecomputeOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    edge_threshold: float = Field(0.35, ge=0, le=1)
    louvain_resolution: float = Field(1.0, gt=0)


@router.post("/workspaces/{workspace_id}/process", status_code=202)
def recompute(workspace_id: UUID, request: Request, background: BackgroundTasks,
              payload: RecomputeOptions | None = None, db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    job = ProcessingJob(workspace_id=workspace_id, kind="recompute_graph", state="queued")
    db.add(job)
    db.commit()
    background.add_task(request.app.state.job_queue.enqueue, job.id, payload.model_dump() if payload else None)
    return {"job_id": str(job.id)}


@router.get("/jobs/{job_id}")
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> dict:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"id": str(job.id), "kind": job.kind, "state": job.state, "error": job.error}


@router.get("/workspaces/{workspace_id}/processing")
def processing_summary(workspace_id: UUID, db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    counts = dict(db.execute(select(ProcessingJob.state, func.count(ProcessingJob.id)).where(ProcessingJob.workspace_id == workspace_id).group_by(ProcessingJob.state)).all())
    ready = db.scalar(select(func.count(Page.id)).where(Page.workspace_id == workspace_id, Page.status == "ready")) or 0
    last_recompute_at = db.scalar(select(func.max(ProcessingJob.finished_at)).where(
        ProcessingJob.workspace_id == workspace_id, ProcessingJob.kind == "recompute_graph", ProcessingJob.state == "done"))
    return {"queued": counts.get("queued", 0), "running": counts.get("running", 0), "failed": counts.get("failed", 0),
            "ready": ready, "last_recompute_at": last_recompute_at.isoformat() if last_recompute_at else None}
