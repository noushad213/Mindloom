import asyncio
from uuid import UUID, uuid4
from threading import Event

from sqlalchemy import func, insert, select

import app.jobs.queue as queue_module
from app.main import app
from app.models import EventLog, Page, PageAnalysis, ProcessingJob, Workspace
from app.services.events import record_event
from app.services.serialization import workspace_body


def create_workspace(client, name="Live"):
    response = client.post("/api/v1/workspaces", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def assert_envelope(message, kind, workspace_id, seq, keys):
    assert set(message) == {"type", "workspace_id", "seq", "ts", "data"}
    assert message["type"] == kind
    assert message["workspace_id"] == workspace_id
    assert message["seq"] == seq
    assert message["ts"].endswith("Z")
    assert set(message["data"]) == keys


def test_i8_websocket_ingest_and_processing(ws_client, postgres_session_factory, ingest_payload):
    workspace_id = create_workspace(ws_client)
    with ws_client.websocket_connect(f"/ws/workspaces/{workspace_id}") as socket:
        assert_envelope(socket.receive_json(), "hello", workspace_id, 0, {"seq"})
        ingested = ws_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
        assert ingested.status_code == 201, ingested.text
        discovered = socket.receive_json()
        extracted = socket.receive_json()
        completed = socket.receive_json()
        assert_envelope(discovered, "page.discovered", workspace_id, 1, {"page"})
        assert discovered["data"]["page"]["id"] == ingested.json()["page"]["id"]
        assert_envelope(extracted, "page.extraction_completed", workspace_id, 2, {"page_id", "status"})
        assert extracted["data"]["status"] == "extracted"
        assert_envelope(completed, "page.processing_completed", workspace_id, 3, {"page"})
        assert completed["data"]["page"]["status"] == "ready"
        assert completed["data"]["page"]["summary"] == "[Stub] Research article"
    graph = ws_client.get(f"/api/v1/workspaces/{workspace_id}/graph").json()
    assert graph["seq"] == 3
    assert graph["pages"][0]["summary"] == "[Stub] Research article"
    with postgres_session_factory() as db:
        assert db.scalar(select(func.count(EventLog.seq)).where(EventLog.workspace_id == UUID(workspace_id))) == 3
        analysis = db.get(PageAnalysis, UUID(ingested.json()["page"]["id"]))
        assert analysis.keywords == [] and analysis.embedding is None
        job = db.scalar(select(ProcessingJob).where(ProcessingJob.workspace_id == UUID(workspace_id)))
        assert job.state == "done" and job.attempts == 1


def test_failure_event_has_exact_payload(ws_client, postgres_session_factory, ingest_payload):
    workspace_id = create_workspace(ws_client)
    ingest_payload["text"] = ""
    ingest_payload["extraction"] = {"status": "failed", "method": "readability", "error_code": "no_permission", "error_message": "Denied"}
    with ws_client.websocket_connect(f"/ws/workspaces/{workspace_id}") as socket:
        socket.receive_json()
        response = ws_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
        assert response.status_code == 201
        assert_envelope(socket.receive_json(), "page.discovered", workspace_id, 1, {"page"})
        failed = socket.receive_json()
        assert_envelope(failed, "page.extraction_failed", workspace_id, 2, {"page_id", "error_code", "error_message"})
        assert failed["data"]["error_code"] == "no_permission"
    with postgres_session_factory() as db:
        assert db.scalar(select(func.count(ProcessingJob.id))) == 0


def test_job_moves_through_processing(ws_client, postgres_session_factory, ingest_payload, monkeypatch):
    started = Event()
    release = Event()
    original = queue_module.process_page

    def delayed_process(*, text, title, url):
        started.set()
        assert release.wait(10)
        return original(text=text, title=title, url=url)

    monkeypatch.setattr(queue_module, "process_page", delayed_process)
    workspace_id = create_workspace(ws_client)
    with ws_client.websocket_connect(f"/ws/workspaces/{workspace_id}") as socket:
        socket.receive_json()
        response = ws_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
        assert response.status_code == 201
        assert started.wait(5)
        page_id = response.json()["page"]["id"]
        assert ws_client.get(f"/api/v1/pages/{page_id}").json()["status"] == "processing"
        with postgres_session_factory() as db:
            job = db.scalar(select(ProcessingJob).where(ProcessingJob.page_id == UUID(page_id)))
            assert job.state == "running" and job.attempts == 1
        release.set()
        assert [socket.receive_json()["type"] for _ in range(3)] == ["page.discovered", "page.extraction_completed", "page.processing_completed"]


def test_processing_failure_is_persisted_and_published(ws_client, postgres_session_factory, ingest_payload, monkeypatch):
    def broken_process(*, text, title, url):
        raise RuntimeError("stub processing failed")

    monkeypatch.setattr(queue_module, "process_page", broken_process)
    workspace_id = create_workspace(ws_client)
    with ws_client.websocket_connect(f"/ws/workspaces/{workspace_id}") as socket:
        socket.receive_json()
        response = ws_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
        assert response.status_code == 201
        socket.receive_json()
        socket.receive_json()
        failed = socket.receive_json()
        assert_envelope(failed, "page.processing_failed", workspace_id, 3, {"page_id", "error_message"})
        assert "stub processing failed" in failed["data"]["error_message"]
        page_id = response.json()["page"]["id"]
    with postgres_session_factory() as db:
        job = db.scalar(select(ProcessingJob).where(ProcessingJob.page_id == UUID(page_id)))
        assert job.state == "failed" and "stub processing failed" in job.error
    assert ws_client.get(f"/api/v1/pages/{page_id}").json()["status"] == "processing_failed"


def test_event_sequence_isolated_and_retained(postgres_session_factory):
    with postgres_session_factory.begin() as db:
        first = Workspace(name="A")
        second = Workspace(name="B")
        db.add_all([first, second])
        db.flush()
        first_id, second_id = first.id, second.id
        db.execute(insert(EventLog).values([{"workspace_id": first_id, "seq": number, "type": "workspace.updated", "payload": {"workspace": {}}} for number in range(1, 501)]))
    with postgres_session_factory.begin() as db:
        first = db.get(Workspace, first_id)
        event = record_event(db, first_id, "workspace.updated", {"workspace": workspace_body(db, first)})
        other = record_event(db, second_id, "workspace.updated", {"workspace": workspace_body(db, db.get(Workspace, second_id))})
        assert event["seq"] == 501
        assert other["seq"] == 1
    with postgres_session_factory() as db:
        assert db.scalar(select(func.count(EventLog.seq)).where(EventLog.workspace_id == first_id)) == 500
        assert db.scalar(select(func.min(EventLog.seq)).where(EventLog.workspace_id == first_id)) == 2


async def test_queued_job_recovers_on_startup(postgres_session_factory):
    with postgres_session_factory.begin() as db:
        workspace = Workspace(name="Recovery")
        db.add(workspace)
        db.flush()
        page = Page(workspace_id=workspace.id, url="https://example.com/recovery", canonical_url="https://example.com/recovery", title="Recovery", domain="example.com", meta={}, text="Stored text", content_hash="original", status="extracted")
        db.add(page)
        db.flush()
        job = ProcessingJob(workspace_id=workspace.id, page_id=page.id, kind="analyze_page", state="queued", attempts=0)
        db.add(job)
        db.flush()
        page_id, job_id = page.id, job.id
    app.state.session_factory = postgres_session_factory
    try:
        async with app.router.lifespan_context(app):
            await asyncio.wait_for(app.state.job_queue.queue.join(), timeout=10)
    finally:
        del app.state.session_factory
    with postgres_session_factory() as db:
        assert db.get(ProcessingJob, job_id).state == "done"
        assert db.get(Page, page_id).status == "ready"
        assert db.get(PageAnalysis, page_id).summary == "[Stub] Recovery"
