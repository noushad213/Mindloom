import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.intelligence.interface import process_page
from app.models import Page, PageAnalysis, ProcessingJob
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

    async def enqueue(self, job_id: UUID) -> None:
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

    def _record_failure(self, job_id: UUID, message: str) -> dict | None:
        with self.session_factory.begin() as db:
            job = db.get(ProcessingJob, job_id)
            if job is None or job.state == "done":
                return None
            job.state = "failed"
            job.error = message[:500]
            job.finished_at = datetime.now(timezone.utc)
            page = db.get(Page, job.page_id)
            if page is None:
                return None
            page.status = "processing_failed"
            page.error_message = message[:500]
            db.flush()
            return record_event(db, job.workspace_id, "page.processing_failed", {"page_id": str(page.id), "error_message": page.error_message})
