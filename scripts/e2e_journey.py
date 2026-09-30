"""Run Mindloom's live API, WebSocket, and persistence journey.

From the repository root, with the API server running:
    python scripts/e2e_journey.py

The script creates two temporary workspaces and removes them on exit. It uses
DATABASE_URL_DIRECT from backend/.env for the suggested-edge database seed.
Set MINDLOOM_E2E_DATABASE_URL only if the API uses a different database.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import websockets
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.models import Edge, Workspace  # noqa: E402


LOG = logging.getLogger("mindloom.e2e")
API_PREFIX = "/api/v1"
EVENT_TIMEOUT = 30.0


def configure_logging() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    LOG.info("PASS %s", message)


async def api(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    expected: int,
    **kwargs: object,
) -> httpx.Response:
    display_path = path
    if path.startswith(f"{API_PREFIX}/shared/"):
        display_path = f"{API_PREFIX}/shared/<redacted-token>"
    params = kwargs.get("params")
    LOG.info("HTTP -> %s %s%s", method, display_path, f" params={params}" if params else "")
    response = await client.request(method, path, **kwargs)
    LOG.info("HTTP <- %s %s: %s", method, display_path, response.status_code)
    if response.status_code != expected:
        raise AssertionError(
            f"{method} {display_path}: expected {expected}, got {response.status_code}: {response.text[:1000]}"
        )
    return response


def payload(url: str, title: str, text: str, browser_tab_id: int) -> dict:
    return {
        "client_event_id": str(uuid4()),
        "url": url,
        "title": title,
        "text": text,
        "meta": {"description": "E2E journey page", "og_image": None, "favicon": None,
                 "lang": "en", "site_name": None, "byline": None},
        "extraction": {"status": "ok", "method": "e2e-script", "error_code": None, "error_message": None},
        "tab": {"browser_tab_id": browser_tab_id, "window_id": 1, "active": False},
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


async def receive_messages(socket: object, messages: asyncio.Queue[dict]) -> None:
    async for raw in socket:
        LOG.info("WS <- %s", raw)
        event = json.loads(raw)
        await messages.put(event)


async def wait_for_event(messages: asyncio.Queue[dict], event_type: str, workspace_id: str,
                         page_id: str | None = None) -> dict:
    deadline = time.monotonic() + EVENT_TIMEOUT
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f"Timed out waiting for WebSocket event {event_type}")
        event = await asyncio.wait_for(messages.get(), timeout=remaining)
        check(set(event) == {"type", "workspace_id", "seq", "ts", "data"}, "WebSocket envelope has exact fields")
        check(event["workspace_id"] == workspace_id, "WebSocket event is scoped to the workspace")
        if event["type"] != event_type:
            continue
        if page_id is not None and event["data"].get("page", {}).get("id") != page_id:
            continue
        LOG.info("ASSERT WebSocket %s received (seq=%s)", event_type, event["seq"])
        return event


def seed_suggested_edge(database_url: str, workspace_id: str, first_page_id: str, second_page_id: str) -> str:
    """The public API creates manual edges only, so seed one worker-style suggestion."""
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with Session(engine) as db:
            check(db.get(Workspace, UUID(workspace_id)) is not None,
                  "Direct database connection points to the API workspace")
            source_id, target_id = sorted((UUID(first_page_id), UUID(second_page_id)), key=str)
            edge = Edge(
                workspace_id=UUID(workspace_id), source_page_id=source_id, target_page_id=target_id,
                type="related_to", label=None, origin="suggested", status="suggested",
                confidence=0.72,
                evidence={"method": "e2e-fixture", "score": 0.72,
                          "shared_keywords": ["research"], "snippets": []},
            )
            db.add(edge)
            db.commit()
            edge_id = str(edge.id)
            LOG.info("DB -> seeded suggested edge %s between %s and %s", edge_id, source_id, target_id)
            return edge_id
    finally:
        engine.dispose()


def verify_tombstone(database_url: str, edge_id: str, workspace_id: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with Session(engine) as db:
            edge = db.get(Edge, UUID(edge_id))
            check(edge is not None and edge.workspace_id == UUID(workspace_id)
                  and edge.origin == "suggested" and edge.status == "rejected",
                  "Rejected suggested edge remains as a database tombstone")
    finally:
        engine.dispose()


async def run(base_url: str, database_url: str, keep_data: bool) -> None:
    base_url = base_url.rstrip("/")
    ws_base = base_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    created_workspaces: list[str] = []
    run_id = uuid4().hex[:10]
    async with httpx.AsyncClient(base_url=base_url, timeout=20.0) as client:
        try:
            LOG.info("PHASE 0: server readiness")
            health = await api(client, "GET", f"{API_PREFIX}/health", 200)
            check(health.json()["db"] == "ok", "API and database are healthy")

            LOG.info("PHASE 1: ingestion, URL normalization, idempotency, and exclusion")
            workspace = (await api(client, "POST", f"{API_PREFIX}/workspaces", 201,
                                   json={"name": f"E2E Journey {run_id}", "description": "Temporary automated journey",
                                         "excluded_domains": ["facebook.com"]})).json()
            workspace_id = workspace["id"]
            created_workspaces.append(workspace_id)
            LOG.info("Workspace 1 ID: %s", workspace_id)

            # The ?id=5 here is inside the fragment and is intentionally removed.
            messy = payload("https://www.Example.com/article#section1?id=5", "Research article",
                            "Research content for the normalization test.", 101)
            first_response = await api(client, "POST", f"{API_PREFIX}/workspaces/{workspace_id}/pages", 201,
                                       json=messy)
            first_body = first_response.json()
            first_page_id = first_body["page"]["id"]
            check(first_body["page"]["canonical_url"] == "https://example.com/article",
                  "Host and fragment normalize to https://example.com/article")
            LOG.info("Page 1 ID: %s; canonical URL: %s", first_page_id, first_body["page"]["canonical_url"])

            retry = await api(client, "POST", f"{API_PREFIX}/workspaces/{workspace_id}/pages", 200, json=messy)
            check(retry.json() == first_body, "Same client_event_id returns the same body with HTTP 200")
            listing = (await api(client, "GET", f"{API_PREFIX}/workspaces/{workspace_id}/pages", 200)).json()
            check(listing["total"] == 1, "Idempotent retry leaves exactly one page")

            excluded = payload("https://www.facebook.com/research", "Excluded page",
                               "This content must never be stored.", 102)
            rejected = await api(client, "POST", f"{API_PREFIX}/workspaces/{workspace_id}/pages", 422,
                                 json=excluded)
            LOG.info("Excluded-domain error envelope: %s", json.dumps(rejected.json(), ensure_ascii=False))
            check(rejected.json()["error"]["code"] == "excluded_domain", "Excluded domain has the expected error code")
            listing = (await api(client, "GET", f"{API_PREFIX}/workspaces/{workspace_id}/pages", 200)).json()
            check(listing["total"] == 1, "Excluded domain stores no page")

            LOG.info("PHASE 2: WebSocket events, processing, and tab lifecycle")
            messages: asyncio.Queue[dict] = asyncio.Queue()
            ws_url = f"{ws_base}/ws/workspaces/{workspace_id}"
            LOG.info("WS -> CONNECT %s", ws_url)
            async with websockets.connect(ws_url, open_timeout=10, close_timeout=3) as socket:
                LOG.info("WS <- CONNECTED %s", ws_url)
                listener = asyncio.create_task(receive_messages(socket, messages))
                try:
                    hello = await wait_for_event(messages, "hello", workspace_id)
                    check(hello["data"]["seq"] == hello["seq"], "Hello contains the current sequence")

                    live_payload = payload(f"https://example.org/journey/{run_id}", "Live research page",
                                           "Live research content for the processing lifecycle.", 103)
                    live_response = await api(client, "POST", f"{API_PREFIX}/workspaces/{workspace_id}/pages", 201,
                                              json=live_payload)
                    live_body = live_response.json()
                    second_page_id = live_body["page"]["id"]
                    tab_session_id = live_body["tab_session"]["id"]
                    discovered = await wait_for_event(messages, "page.discovered", workspace_id, second_page_id)
                    completed = await wait_for_event(messages, "page.processing_completed", workspace_id, second_page_id)
                    check(discovered["seq"] < completed["seq"], "Discovery precedes processing completion")
                    check(completed["data"]["page"]["status"] == "ready", "Processed page reaches ready state")
                finally:
                    await socket.close()
                    await asyncio.wait_for(listener, timeout=5)
                    LOG.info("WS <- CLOSED %s", ws_url)

            closed = (await api(client, "PATCH", f"{API_PREFIX}/tab-sessions/{tab_session_id}", 200,
                                json={"state": "closed"})).json()
            check(closed["state"] == "closed", "Tab session is closed")
            saved_page = (await api(client, "GET", f"{API_PREFIX}/pages/{second_page_id}", 200)).json()
            check(saved_page["id"] == second_page_id, "Closing a tab retains the saved page")

            LOG.info("PHASE 3: rejected-edge tombstone and workspace isolation")
            edge_id = seed_suggested_edge(database_url, workspace_id, first_page_id, second_page_id)
            await api(client, "DELETE", f"{API_PREFIX}/edges/{edge_id}", 204)
            rejected_edges = (await api(client, "GET", f"{API_PREFIX}/workspaces/{workspace_id}/edges", 200,
                                        params={"status": "rejected"})).json()["items"]
            check(any(edge["id"] == edge_id and edge["status"] == "rejected" for edge in rejected_edges),
                  "Rejected edge appears through the API")
            verify_tombstone(database_url, edge_id, workspace_id)

            workspace_2 = (await api(client, "POST", f"{API_PREFIX}/workspaces", 201,
                                     json={"name": f"E2E Isolation {run_id}", "description": "Temporary isolated workspace",
                                           "excluded_domains": []})).json()["id"]
            created_workspaces.append(workspace_2)
            LOG.info("Workspace 2 ID: %s", workspace_2)
            cross_scope = await api(client, "GET", f"{API_PREFIX}/workspaces/{workspace_2}/pages/{first_page_id}", 404)
            check(cross_scope.json()["error"]["code"] == "not_found", "Cross-workspace page read returns strict 404")

            LOG.info("PHASE 4: tag search and view-token firewall")
            tag = (await api(client, "POST", f"{API_PREFIX}/workspaces/{workspace_id}/tags", 201,
                             json={"name": "journey-tag", "color": "#f59e0b"})).json()
            await api(client, "POST", f"{API_PREFIX}/tags/{tag['id']}/attach", 204,
                      json={"target_type": "page", "target_id": first_page_id})
            search = (await api(client, "GET", f"{API_PREFIX}/workspaces/{workspace_id}/search", 200,
                                params={"q": "#journey-tag"})).json()
            check(any(item["type"] == "page" and item["id"] == first_page_id for item in search["results"]),
                  "#journey-tag search returns the tagged page")

            share = (await api(client, "POST", f"{API_PREFIX}/workspaces/{workspace_id}/share", 201,
                               json={"role": "view", "expires_in_days": 1})).json()
            token = share["token"]
            resolved = (await api(client, "GET", f"{API_PREFIX}/shared/{token}", 200)).json()
            check(resolved == {"workspace_id": workspace_id, "role": "view"}, "View share token resolves correctly")
            blocked = await api(client, "DELETE", f"{API_PREFIX}/pages/{first_page_id}", 403,
                                headers={"X-Share-Token": token})
            LOG.info("Role-firewall error envelope: %s", json.dumps(blocked.json(), ensure_ascii=False))
            check(blocked.json()["error"]["code"] == "forbidden", "View token cannot delete a page")
            await api(client, "GET", f"{API_PREFIX}/pages/{first_page_id}", 200)
            LOG.info("E2E JOURNEY PASSED: all API, WebSocket, and database assertions succeeded")
        finally:
            if keep_data:
                LOG.info("Keeping journey workspaces for inspection: %s", created_workspaces)
            else:
                for workspace_id in reversed(created_workspaces):
                    try:
                        await api(client, "DELETE", f"{API_PREFIX}/workspaces/{workspace_id}", 204)
                        LOG.info("CLEANUP removed temporary workspace %s", workspace_id)
                    except Exception:
                        LOG.exception("CLEANUP failed for workspace %s", workspace_id)


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Run the live Mindloom end-to-end API journey")
    parser.add_argument("--base-url", default=os.getenv("MINDLOOM_API_BASE_URL", "http://127.0.0.1:8000"),
                        help="FastAPI server origin (default: http://127.0.0.1:8000)")
    parser.add_argument("--keep-data", action="store_true", help="Keep the temporary workspaces for inspection")
    args = parser.parse_args()
    database_url = os.getenv("MINDLOOM_E2E_DATABASE_URL") or get_settings().database_url_direct
    try:
        asyncio.run(run(args.base_url, database_url, args.keep_data))
        return 0
    except Exception:
        LOG.exception("E2E JOURNEY FAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
