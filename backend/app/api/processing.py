from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.workspaces import require_workspace
from app.db.session import get_db
from app.models import Page, ProcessingJob


router = APIRouter(prefix="/api/v1", tags=["processing"])


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
    return {"queued": counts.get("queued", 0), "running": counts.get("running", 0), "failed": counts.get("failed", 0), "ready": ready, "last_recompute_at": None}
