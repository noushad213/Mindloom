import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.models import Edge, Group, PageAnalysis


async def workspace(client, name="Workspace"):
    response = await client.post("/api/v1/workspaces", json={"name": name, "description": "", "excluded_domains": []})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def page(client, workspace_id, payload, url, tab_id):
    body = {**payload, "client_event_id": str(uuid4()), "url": url, "tab": {**payload["tab"], "browser_tab_id": tab_id}}
    response = await client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=body)
    assert response.status_code in (200, 201), response.text
    return response.json()["page"]["id"]


@pytest.mark.asyncio
async def test_edges_groups_positions_and_override_tombstone(api_client, postgres_session_factory, ingest_payload, monkeypatch):
    from app.intelligence.interface import RelationshipResult
    from app.jobs import queue as queue_module

    client = api_client
    wid = await workspace(client)
    first = await page(client, wid, ingest_payload, "https://example.com/first", 1)
    second = await page(client, wid, ingest_payload, "https://example.com/second", 2)
    third = await page(client, wid, ingest_payload, "https://example.com/third", 3)
    group = await client.post(f"/api/v1/workspaces/{wid}/groups", json={"name": "Sources", "category": "source",
                              "color": "#10b981", "page_ids": [first]})
    assert group.status_code == 201, group.text
    assert group.json()["page_ids"] == [first]
    moved = await client.patch(f"/api/v1/workspaces/{wid}/pages/positions", json={"positions": [{"id": first, "x": 1, "y": 2}]})
    assert moved.json() == {"updated": 1}
    edge = await client.post(f"/api/v1/workspaces/{wid}/edges", json={"source": first, "target": second,
                             "type": "supports", "label": None})
    assert edge.status_code == 201, edge.text
    assert edge.json()["origin"] == "manual"
    with postgres_session_factory.begin() as db:
        suggested = Edge(workspace_id=UUID(wid), source_page_id=UUID(first), target_page_id=UUID(third),
                         type="related_to", origin="suggested", status="suggested", confidence=0.7,
                         evidence={"method": "test", "shared_keywords": [], "snippets": []})
        db.add(suggested)
        accepted = Edge(workspace_id=UUID(wid), source_page_id=UUID(second), target_page_id=UUID(third),
                        type="related_to", origin="suggested", status="suggested", confidence=0.8,
                        evidence={"method": "test", "shared_keywords": [], "snippets": []})
        db.add(accepted)
        suggested_group = Group(workspace_id=UUID(wid), name="Draft", category="topic", color="#6366f1",
                                origin="suggested", status="suggested", keywords=[])
        db.add(suggested_group)
        db.flush()
        suggested_id = str(suggested.id)
        accepted_id = str(accepted.id)
        suggested_group_id = str(suggested_group.id)
    edited_group = await client.patch(f"/api/v1/groups/{suggested_group_id}", json={"name": "My topic"})
    assert edited_group.status_code == 200 and edited_group.json()["origin"] == "manual"
    assert (await client.delete(f"/api/v1/edges/{suggested_id}")).status_code == 204
    assert (await client.post(f"/api/v1/edges/{accepted_id}/accept")).json()["status"] == "accepted"
    rejected = (await client.get(f"/api/v1/workspaces/{wid}/edges?status=rejected")).json()["items"]
    assert [item["id"] for item in rejected] == [suggested_id]
    monkeypatch.setattr(queue_module, "compute_relationships", lambda *_args: RelationshipResult(candidate_edges=[
        {"source": first, "target": third, "type": "related_to", "confidence": 0.9, "evidence": {"method": "test"}},
        {"source": second, "target": third, "type": "related_to", "confidence": 0.9, "evidence": {"method": "test"}},
        {"source": first, "target": second, "type": "supports", "confidence": 0.9, "evidence": {"method": "test"}},
    ], clusters=[]))
    recompute = await client.post(f"/api/v1/workspaces/{wid}/process", json={})
    assert recompute.status_code == 202, recompute.text
    for _ in range(50):
        status = (await client.get(f"/api/v1/jobs/{recompute.json()['job_id']}")).json()["state"]
        if status in ("done", "failed"):
            break
        await asyncio.sleep(0.05)
    assert status == "done"
    assert (await client.get(f"/api/v1/workspaces/{wid}/edges?status=rejected")).json()["items"][0]["id"] == suggested_id
    remaining = {item["id"] for item in (await client.get(f"/api/v1/workspaces/{wid}/edges")).json()["items"]}
    assert remaining == {edge.json()["id"], accepted_id}
    groups = {item["id"]: item for item in (await client.get(f"/api/v1/workspaces/{wid}/groups")).json()["items"]}
    assert groups[suggested_group_id]["name"] == "My topic"
    assert (await client.post(f"/api/v1/edges/{suggested_id}/restore")).status_code == 204
    assert (await client.get(f"/api/v1/workspaces/{wid}/edges?status=rejected")).json()["items"] == []


@pytest.mark.asyncio
async def test_notes_tags_search_and_export(api_client, postgres_session_factory, ingest_payload):
    client = api_client
    wid = await workspace(client, "Clinical Research")
    pid = await page(client, wid, {**ingest_payload, "title": "Clinical triage", "text": "Clinical triage research"},
                     "https://nature.com/triage", 3)
    tag = await client.post(f"/api/v1/workspaces/{wid}/tags", json={"name": "Important", "color": "#f59e0b"})
    assert tag.status_code == 201, tag.text
    tid = tag.json()["id"]
    assert (await client.post(f"/api/v1/tags/{tid}/attach", json={"target_type": "page", "target_id": pid})).status_code == 204
    note = await client.post(f"/api/v1/workspaces/{wid}/notes", json={"target_type": "page", "target_id": pid,
                             "kind": "note", "body": "Triage finding", "quote": None, "author": "Asha"})
    assert note.status_code == 201, note.text
    assert (await client.get(f"/api/v1/workspaces/{wid}/pages/{pid}")).json()["tags"][0]["name"] == "Important"
    snapshot = (await client.get(f"/api/v1/workspaces/{wid}/graph")).json()
    assert snapshot["notes"][0]["id"] == note.json()["id"]
    assert snapshot["tags"][0]["count"] == 1
    result = await client.get(f"/api/v1/workspaces/{wid}/search", params={"q": "triage #important @nature.com"})
    assert result.status_code == 200, result.text
    assert any(item["id"] == pid for item in result.json()["results"])
    tag_results = (await client.get(f"/api/v1/workspaces/{wid}/search", params={"q": "Important"})).json()["results"]
    assert any(item["type"] == "page" and item["id"] == pid for item in tag_results)
    from app.main import app
    await app.state.job_queue.queue.join()
    with postgres_session_factory.begin() as db:
        db.get(PageAnalysis, UUID(pid)).summary = "Distinctive oncology insight"
    summary_results = (await client.get(f"/api/v1/workspaces/{wid}/search", params={"q": "oncology"})).json()["results"]
    assert any(item["id"] == pid for item in summary_results)
    export = await client.get(f"/api/v1/workspaces/{wid}/export?format=json")
    assert export.status_code == 200, export.text
    assert export.json()["pages"][0]["tags"] == ["Important"]
    assert "text" not in export.json()["pages"][0]
    markdown = await client.get(f"/api/v1/workspaces/{wid}/export?format=md")
    assert markdown.status_code == 200 and "Triage finding" in markdown.text
    assert (await client.delete(f"/api/v1/pages/{pid}")).status_code == 204
    assert (await client.get(f"/api/v1/workspaces/{wid}/notes")).json()["items"] == []
    assert (await client.get(f"/api/v1/workspaces/{wid}/tags")).json()["items"][0]["count"] == 0


@pytest.mark.asyncio
async def test_share_roles_and_workspace_isolation(api_client, ingest_payload):
    client = api_client
    first = await workspace(client, "First")
    second = await workspace(client, "Second")
    updated = await client.patch(f"/api/v1/workspaces/{first}", json={"settings": {"auto_recompute": False},
                                  "view_state": {"mode": "list", "zoom": 1.2}})
    assert updated.status_code == 200, updated.text
    assert updated.json()["settings"]["auto_recompute"] is False
    assert (await client.get(f"/api/v1/workspaces/{first}")).json()["view_state"]["mode"] == "list"
    first_page = await page(client, first, ingest_payload, "https://example.com/a", 4)
    second_page = await page(client, second, ingest_payload, "https://example.com/b", 5)
    view_link = (await client.post(f"/api/v1/workspaces/{first}/share", json={"role": "view", "expires_in_days": 7})).json()
    view = view_link["token"]
    edit = (await client.post(f"/api/v1/workspaces/{first}/share", json={"role": "edit"})).json()["token"]
    view_headers = {"X-Share-Token": view}
    edit_headers = {"X-Share-Token": edit}
    assert (await client.get(f"/api/v1/workspaces/{first}", headers=view_headers)).status_code == 200
    assert (await client.get(f"/api/v1/workspaces/{second}", headers=view_headers)).status_code == 404
    assert (await client.get(f"/api/v1/pages/{second_page}", headers=view_headers)).status_code == 404
    assert len((await client.get("/api/v1/workspaces", headers=view_headers)).json()["items"]) == 1
    denied = await client.post(f"/api/v1/workspaces/{first}/notes", headers=view_headers,
                               json={"target_type": "page", "target_id": first_page, "kind": "note", "body": "No"})
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "forbidden"
    allowed = await client.post(f"/api/v1/workspaces/{first}/notes", headers=edit_headers,
                                json={"target_type": "page", "target_id": first_page, "kind": "note", "body": "Yes"})
    assert allowed.status_code == 201, allowed.text
    assert (await client.patch(f"/api/v1/workspaces/{first}/pages/positions", headers=edit_headers,
                               json={"positions": [{"id": first_page, "x": 12, "y": 34}]})).status_code == 200
    assert (await client.patch(f"/api/v1/workspaces/{first}", headers=edit_headers, json={"name": "Blocked"})).status_code == 403
    assert (await client.delete(f"/api/v1/workspaces/{first}", headers=edit_headers)).status_code == 403
    assert (await client.post(f"/api/v1/workspaces/{first}/share", headers=edit_headers, json={"role": "view"})).status_code == 403
    assert (await client.delete(f"/api/v1/shares/{view_link['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/workspaces/{first}", headers=view_headers)).status_code == 403


@pytest.mark.asyncio
async def test_semantic_search_uses_vector_and_workspace_filter(api_client, postgres_session_factory, ingest_payload, monkeypatch):
    from app.intelligence import interface

    client = api_client
    first = await workspace(client, "Vector one")
    second = await workspace(client, "Vector two")
    first_page = await page(client, first, ingest_payload, "https://example.com/vector-one", 10)
    second_page = await page(client, second, ingest_payload, "https://example.com/vector-two", 11)
    from app.main import app
    await app.state.job_queue.queue.join()
    vector = [1.0] + [0.0] * 383
    with postgres_session_factory.begin() as db:
        for pid in (first_page, second_page):
            analysis = db.get(PageAnalysis, UUID(pid))
            if analysis is None:
                analysis = PageAnalysis(page_id=UUID(pid), keywords=[])
                db.add(analysis)
            analysis.embedding = vector
    monkeypatch.setattr(interface, "embed_query", lambda _query: vector)
    response = await client.get(f"/api/v1/workspaces/{first}/search", params={"q": "unmatched-meaning"})
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["results"]] == [first_page]


def test_websocket_accepts_valid_share_and_rejects_cross_workspace(ws_client):
    from starlette.websockets import WebSocketDisconnect

    first = ws_client.post("/api/v1/workspaces", json={"name": "First", "description": "", "excluded_domains": []}).json()["id"]
    second = ws_client.post("/api/v1/workspaces", json={"name": "Second", "description": "", "excluded_domains": []}).json()["id"]
    token = ws_client.post(f"/api/v1/workspaces/{first}/share", json={"role": "view"}).json()["token"]
    with ws_client.websocket_connect(f"/ws/workspaces/{first}?share={token}") as socket:
        hello = socket.receive_json()
        assert hello["type"] == "hello" and hello["workspace_id"] == first
    with pytest.raises(WebSocketDisconnect) as exc:
        with ws_client.websocket_connect(f"/ws/workspaces/{second}?share={token}"):
            pass
    assert exc.value.code == 4403
