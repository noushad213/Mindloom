from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.workspaces import require_workspace
from app.db.session import get_db
from app.models import Page, ProcessingJob, TabSession
from app.schemas.pages import IngestPayload, IngestResponse, PageList, TabSessionList, TabSessionResponse, TabSessionUpdate
from app.services.ingest import ingest_page
from app.services.serialization import page_body, tab_body
from app.services.events import record_event


router = APIRouter(prefix="/api/v1", tags=["pages"])


@router.post("/workspaces/{workspace_id}/pages", status_code=201, response_model=IngestResponse, responses={200: {"model": IngestResponse}})
def ingest(workspace_id: UUID, payload: IngestPayload, background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    events: list[dict] = []
    job_id: UUID | None = None
    with db.begin():
        status_code, body, accepted = ingest_page(db, workspace_id, payload)
        if accepted:
            page_id = UUID(body["page"]["id"])
            page = db.get(Page, page_id)
            assert page is not None
            events.append(record_event(db, workspace_id, "page.discovered", {"page": body["page"]}))
            if page.status == "extraction_failed":
                events.append(record_event(db, workspace_id, "page.extraction_failed", {"page_id": str(page_id), "error_code": page.error_code, "error_message": page.error_message}))
            else:
                events.append(record_event(db, workspace_id, "page.extraction_completed", {"page_id": str(page_id), "status": "extracted"}))
                if page.status == "extracted":
                    queued = db.scalar(select(ProcessingJob.id).where(ProcessingJob.page_id == page_id, ProcessingJob.kind == "analyze_page", ProcessingJob.state == "queued").limit(1))
                    if queued is None:
                        job = ProcessingJob(workspace_id=workspace_id, page_id=page_id, kind="analyze_page", state="queued", attempts=0)
                        db.add(job)
                        db.flush()
                        job_id = job.id
    if events:
        background_tasks.add_task(publish_ingest_events, request.app, events, job_id)
    return JSONResponse(status_code=status_code, content=body)


async def publish_ingest_events(app, events: list[dict], job_id: UUID | None) -> None:
    for event in events:
        await app.state.ws_manager.broadcast(event)
    queue = getattr(app.state, "job_queue", None)
    if job_id is not None and queue is not None:
        await queue.enqueue(job_id)


@router.get("/workspaces/{workspace_id}/pages", response_model=PageList)
def list_pages(
    workspace_id: UUID,
    status: str | None = None,
    domain: str | None = None,
    sort: str = "recent",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    require_workspace(db, workspace_id)
    filters = [Page.workspace_id == workspace_id]
    if status:
        filters.append(Page.status == status)
    if domain:
        filters.append(Page.domain == domain)
    if sort != "recent":
        raise HTTPException(status_code=422, detail="Unsupported sort value")
    total = db.scalar(select(func.count(Page.id)).where(*filters)) or 0
    pages = db.scalars(select(Page).where(*filters).order_by(Page.last_seen_at.desc()).limit(limit).offset(offset)).all()
    return {"items": [page_body(db, page) for page in pages], "total": total, "limit": limit, "offset": offset}


@router.get("/pages/{page_id}")
def get_page(page_id: UUID, include_text: bool = False, db: Session = Depends(get_db)) -> dict:
    page = db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    body = page_body(db, page)
    if include_text:
        body["text"] = page.text
    return body


@router.get("/workspaces/{workspace_id}/pages/{page_id}")
def get_workspace_page(workspace_id: UUID, page_id: UUID, include_text: bool = False, db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    page = db.scalar(select(Page).where(Page.id == page_id, Page.workspace_id == workspace_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    body = page_body(db, page)
    if include_text:
        body["text"] = page.text
    return body


@router.delete("/pages/{page_id}", status_code=204)
def delete_page(page_id: UUID, db: Session = Depends(get_db)) -> Response:
    page = db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    db.delete(page)
    db.commit()
    return Response(status_code=204)


@router.get("/workspaces/{workspace_id}/tab-sessions", response_model=TabSessionList)
def list_tab_sessions(workspace_id: UUID, state: str | None = None, db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    query = select(TabSession).where(TabSession.workspace_id == workspace_id)
    if state is not None:
        if state not in {"open", "closed"}:
            raise HTTPException(status_code=422, detail="Invalid tab session state")
        query = query.where(TabSession.state == state)
    return {"items": [tab_body(tab) for tab in db.scalars(query.order_by(TabSession.opened_at)).all()]}


@router.patch("/tab-sessions/{session_id}", response_model=TabSessionResponse)
def close_tab_session(session_id: UUID, payload: TabSessionUpdate, db: Session = Depends(get_db)) -> dict:
    from datetime import datetime, timezone

    tab = db.get(TabSession, session_id)
    if tab is None:
        raise HTTPException(status_code=404, detail="Tab session not found")
    if tab.state != "closed":
        tab.state = payload.state
        tab.active = False
        tab.closed_at = datetime.now(timezone.utc)
        tab.last_seen_at = tab.closed_at
        db.commit()
        db.refresh(tab)
    return tab_body(tab)
