import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.intelligence.interface import compute_relationships, process_page
from app.models import Edge, Group, GroupMember, Page, PageAnalysis, ProcessingJob, Workspace
from app.services.events import record_event
from app.services.serialization import page_body
from app.ws.manager import ConnectionManager


logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(self, session_factory: sessionmaker[Session], manager: ConnectionManager, concurrency: int = 2) -> None:
        self.session_factory = session_factory
        self.manager = manager
        self.concurrency = concurrency
        self.queue: asyncio.Queue[UUID] = asyncio.Queue(maxsize=1000)
        self.workers: list[asyncio.Task[None]] = []
        self.recompute_params: dict[UUID, dict] = {}

    async def start(self) -> None:
        pending_ids = await asyncio.to_thread(self._recover_pending)
        self.workers = [asyncio.create_task(self._worker(), name=f"mindloom-job-{index}") for index in range(self.concurrency)]
        for job_id in pending_ids:
            await self.queue.put(job_id)

    async def stop(self) -> None:
        try:
            await asyncio.wait_for(self.queue.join(), timeout=5)
        except asyncio.TimeoutError:
            logger.warning("Processing queue stopped with unfinished jobs; startup will recover them")
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    async def enqueue(self, job_id: UUID, params: dict | None = None) -> None:
        if params is not None:
            self.recompute_params[job_id] = params
        await self.queue.put(job_id)

    def _recover_pending(self) -> list[UUID]:
        with self.session_factory.begin() as db:
            jobs = db.scalars(select(ProcessingJob).where(ProcessingJob.state.in_(["queued", "running"])).order_by(ProcessingJob.created_at)).all()
            for job in jobs:
                if job.state == "running":
                    job.state = "queued"
            return [job.id for job in jobs]

    async def _worker(self) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                event = await asyncio.to_thread(self._execute, job_id)
                if event is not None:
                    await self.manager.broadcast(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Processing job %s failed", job_id)
                try:
                    event = await asyncio.to_thread(self._record_failure, job_id, str(exc))
                    if event is not None:
                        await self.manager.broadcast(event)
                except Exception:
                    logger.exception("Could not record failure for processing job %s", job_id)
            finally:
                self.queue.task_done()

    def _execute(self, job_id: UUID) -> dict | None:
        with self.session_factory() as db:
            kind = db.scalar(select(ProcessingJob.kind).where(ProcessingJob.id == job_id))
        if kind == "recompute_graph":
            return self._recompute(job_id, self.recompute_params.pop(job_id, None))
        with self.session_factory.begin() as db:
            job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update(skip_locked=True))
            if job is None or job.state != "queued":
                return None
            page = db.get(Page, job.page_id)
            if page is None:
                job.state = "done"
                job.finished_at = datetime.now(timezone.utc)
                return None
            job.state = "running"
            job.attempts += 1
            job.started_at = datetime.now(timezone.utc)
            page.status = "processing"
            text, title, url, content_hash = page.text or "", page.title or "", page.url, page.content_hash

        result = process_page(text=text, title=title, url=url)

        with self.session_factory.begin() as db:
            job = db.get(ProcessingJob, job_id)
            if job is None:
                return None
            page = db.get(Page, job.page_id)
            job.state = "done"
            job.finished_at = datetime.now(timezone.utc)
            if page is None or page.content_hash != content_hash:
                return None
            analysis = db.get(PageAnalysis, page.id)
            if analysis is None:
                analysis = PageAnalysis(page_id=page.id)
                db.add(analysis)
            analysis.summary = result.summary
            analysis.summary_method = result.summary_method
            analysis.keywords = result.keywords
            analysis.simhash = result.simhash
            analysis.embedding = result.embedding
            analysis.embedding_model = result.embedding_model
            analysis.analyzed_at = datetime.now(timezone.utc)
            page.status = "ready"
            page.error_code = None
            page.error_message = None
            db.flush()
            return record_event(db, job.workspace_id, "page.processing_completed", {"page": page_body(db, page)})

    def _recompute(self, job_id: UUID, params: dict | None = None) -> dict | None:
        with self.session_factory.begin() as db:
            job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update(skip_locked=True))
            if job is None or job.state != "queued":
                return None
            job.state = "running"
            job.attempts += 1
            job.started_at = datetime.now(timezone.utc)
            workspace_id = job.workspace_id
            workspace = db.get(Workspace, workspace_id)
            effective_params = dict(workspace.settings or {}) if workspace else {}
            effective_params.update(params or {})
            analyzed_pages = db.execute(
                select(Page, PageAnalysis)
                .join(PageAnalysis, PageAnalysis.page_id == Page.id)
                .where(Page.workspace_id == workspace_id, PageAnalysis.embedding.is_not(None))
            ).all()
            page_data = [
                {
                    "id": str(page.id),
                    "title": page.title,
                    "url": page.url,
                    "text": page.text,
                    "embedding": analysis.embedding,
                    "keywords": analysis.keywords,
                    "simhash": analysis.simhash,
                }
                for page, analysis in analyzed_pages
            ]
            rejected_pairs = {(str(e.source_page_id), str(e.target_page_id)) for e in db.scalars(
                select(Edge).where(Edge.workspace_id == workspace_id, Edge.status == "rejected")).all()}
        result = compute_relationships(page_data, rejected_pairs, effective_params)
        with self.session_factory.begin() as db:
            job = db.get(ProcessingJob, job_id)
            if job is None:
                return None
            old_edges = db.scalars(select(Edge).where(Edge.workspace_id == workspace_id, Edge.origin == "suggested", Edge.status == "suggested")).all()
            old_groups = db.scalars(select(Group).where(Group.workspace_id == workspace_id, Group.origin == "suggested", Group.status == "suggested")).all()
            changed_edge_ids = [e.id for e in old_edges]
            changed_group_ids = [g.id for g in old_groups]
            for edge in old_edges:
                db.delete(edge)
            for group in old_groups:
                db.delete(group)
            db.flush()
            protected = {(e.source_page_id, e.target_page_id) for e in db.scalars(select(Edge).where(
                Edge.workspace_id == workspace_id, (Edge.status.in_(["accepted", "rejected"])) | (Edge.origin == "manual"))).all()}
            valid_pages = set(db.scalars(select(Page.id).where(Page.workspace_id == workspace_id)).all())
            for candidate in result.candidate_edges:
                source = UUID(str(candidate.get("source", candidate.get("source_page_id"))))
                target = UUID(str(candidate.get("target", candidate.get("target_page_id"))))
                edge_type = candidate.get("type", "related_to")
                if edge_type in {"related_to", "duplicate_of"} and str(source) > str(target):
                    source, target = target, source
                if source == target or source not in valid_pages or target not in valid_pages:
                    continue
                if (source, target) in protected or (target, source) in protected:
                    continue
                protected.add((source, target))
                edge = Edge(workspace_id=workspace_id, source_page_id=source, target_page_id=target,
                            type=edge_type, label=candidate.get("label"), origin="suggested", status="suggested",
                            confidence=candidate.get("confidence"), evidence=candidate.get("evidence"))
                db.add(edge)
                db.flush()
                changed_edge_ids.append(edge.id)
            for cluster in result.clusters:
                group = Group(workspace_id=workspace_id, name=cluster.get("name", "Suggested group"),
                              category=cluster.get("category", "topic"), color=cluster.get("color", "#6366f1"),
                              origin="suggested", status="suggested", keywords=cluster.get("keywords", []))
                db.add(group)
                db.flush()
                changed_group_ids.append(group.id)
                for page_id in cluster.get("page_ids", []):
                    if UUID(str(page_id)) in valid_pages:
                        db.add(GroupMember(group_id=group.id, page_id=UUID(str(page_id)), origin="suggested"))
            job.state = "done"
            job.finished_at = datetime.now(timezone.utc)
            return record_event(db, workspace_id, "graph.changed", {"changed": {"pages": [],
                "edges": [str(eid) for eid in changed_edge_ids], "groups": [str(gid) for gid in changed_group_ids]},
                "reason": "recompute"})

    def _record_failure(self, job_id: UUID, message: str) -> dict | None:
        with self.session_factory.begin() as db:
            job = db.get(ProcessingJob, job_id)
            if job is None or job.state == "done":
                return None
            job.state = "failed"
            job.error = message[:500]
            job.finished_at = datetime.now(timezone.utc)
            if job.kind == "recompute_graph":
                return None
            page = db.get(Page, job.page_id)
            if page is None:
                return None
            page.status = "processing_failed"
            page.error_message = message[:500]
            db.flush()
            return record_event(db, job.workspace_id, "page.processing_failed", {"page_id": str(page.id), "error_message": page.error_message})
