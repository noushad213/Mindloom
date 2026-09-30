import asyncio
from uuid import uuid4

import pytest


async def create_workspace(client, name="Research", excluded_domains=None):
    response = await client.post("/api/v1/workspaces", json={"name": name, "description": "", "excluded_domains": excluded_domains or []})
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_i1_ingest_then_read(api_client, ingest_payload):
    workspace_id = await create_workspace(api_client)
    response = await api_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
    assert response.status_code == 201, response.text
    page = response.json()["page"]
    assert page["canonical_url"] == "https://example.com/article?id=5"
    listing = await api_client.get(f"/api/v1/workspaces/{workspace_id}/pages")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["id"] == page["id"]


@pytest.mark.asyncio
async def test_i2_two_tabs_one_page(api_client, ingest_payload):
    workspace_id = await create_workspace(api_client)
    first = await api_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
    ingest_payload["client_event_id"] = str(uuid4())
    ingest_payload["tab"]["browser_tab_id"] = 11
    second = await api_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["page"]["id"] == second.json()["page"]["id"]
    assert len((await api_client.get(f"/api/v1/workspaces/{workspace_id}/tab-sessions")).json()["items"]) == 2


@pytest.mark.asyncio
async def test_i3_close_tab_preserves_page(api_client, ingest_payload):
    workspace_id = await create_workspace(api_client)
    created = (await api_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)).json()
    session_id = created["tab_session"]["id"]
    response = await api_client.patch(f"/api/v1/tab-sessions/{session_id}", json={"state": "closed"})
    assert response.status_code == 200
    assert response.json()["state"] == "closed"
    assert response.json()["closed_at"] is not None
    page_response = await api_client.get(f"/api/v1/pages/{created['page']['id']}")
    assert page_response.status_code == 200
    assert page_response.json()["tab_open"] is False


@pytest.mark.asyncio
async def test_i4_excluded_domain_stores_nothing(api_client, ingest_payload):
    workspace_id = await create_workspace(api_client, excluded_domains=["example.com"])
    response = await api_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "excluded_domain"
    assert (await api_client.get(f"/api/v1/workspaces/{workspace_id}/pages")).json()["total"] == 0
    assert (await api_client.get(f"/api/v1/workspaces/{workspace_id}/tab-sessions")).json()["items"] == []


@pytest.mark.asyncio
async def test_i5_identical_event_response(api_client, ingest_payload):
    workspace_id = await create_workspace(api_client)
    first = await api_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
    second = await api_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert (await api_client.get(f"/api/v1/workspaces/{workspace_id}/pages")).json()["total"] == 1


@pytest.mark.asyncio
async def test_i6_extraction_failure_is_visible(api_client, ingest_payload):
    workspace_id = await create_workspace(api_client)
    ingest_payload["text"] = ""
    ingest_payload["extraction"] = {"status": "failed", "method": "readability", "error_code": "no_permission", "error_message": "Access denied"}
    response = await api_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=ingest_payload)
    assert response.status_code == 201, response.text
    page = response.json()["page"]
    assert page["status"] == "extraction_failed"
    assert page["error_code"] == "no_permission"
    assert (await api_client.get(f"/api/v1/workspaces/{workspace_id}/pages")).json()["items"][0]["id"] == page["id"]


@pytest.mark.asyncio
async def test_i7_workspace_isolation(api_client, ingest_payload):
    first_id = await create_workspace(api_client, "First")
    second_id = await create_workspace(api_client, "Second")
    first_page = (await api_client.post(f"/api/v1/workspaces/{first_id}/pages", json=ingest_payload)).json()["page"]
    second_listing = (await api_client.get(f"/api/v1/workspaces/{second_id}/pages")).json()
    assert second_listing["items"] == []
    assert first_page["id"] not in {item["id"] for item in second_listing["items"]}
    wrong_scope = await api_client.get(f"/api/v1/workspaces/{second_id}/pages/{first_page['id']}")
    assert wrong_scope.status_code == 404
    assert wrong_scope.json()["error"]["code"] == "not_found"
    ingest_payload["client_event_id"] = str(uuid4())
    second_page = (await api_client.post(f"/api/v1/workspaces/{second_id}/pages", json=ingest_payload)).json()["page"]
    assert first_page["id"] != second_page["id"]
    assert (await api_client.get(f"/api/v1/workspaces/{first_id}/pages/{second_page['id']}")).status_code == 404
    assert (await api_client.delete(f"/api/v1/workspaces/{first_id}")).status_code == 204
    assert (await api_client.get(f"/api/v1/pages/{first_page['id']}")).status_code == 404
    assert (await api_client.get(f"/api/v1/workspaces/{second_id}/pages/{second_page['id']}")).status_code == 200


@pytest.mark.asyncio
async def test_concurrent_ingests_share_one_page(api_client, ingest_payload):
    workspace_id = await create_workspace(api_client)
    payloads = []
    for index in range(5):
        payload = {**ingest_payload, "client_event_id": str(uuid4()), "tab": {**ingest_payload["tab"], "browser_tab_id": 100 + index}}
        payloads.append(payload)
    responses = await asyncio.gather(*(api_client.post(f"/api/v1/workspaces/{workspace_id}/pages", json=payload) for payload in payloads))
    assert sorted(response.status_code for response in responses) == [200, 200, 200, 200, 201]
    assert len({response.json()["page"]["id"] for response in responses}) == 1
    assert (await api_client.get(f"/api/v1/workspaces/{workspace_id}/pages")).json()["total"] == 1
    assert len((await api_client.get(f"/api/v1/workspaces/{workspace_id}/tab-sessions")).json()["items"]) == 5
