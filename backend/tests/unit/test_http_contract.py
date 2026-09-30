import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_validation_and_not_found_use_error_envelope():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing = await client.post("/api/v1/workspaces", json={})
        assert missing.status_code == 422
        assert missing.json()["error"]["code"] == "validation_error"
        absent = await client.get("/no-such-route")
        assert absent.status_code == 404
        assert absent.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_ingest_size_limit_has_cors_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/workspaces/00000000-0000-0000-0000-000000000000/pages",
            content=b"x" * (2 * 1024 * 1024 + 1),
            headers={"Origin": "http://localhost:5173", "Content-Type": "application/json"},
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "payload_too_large"
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
