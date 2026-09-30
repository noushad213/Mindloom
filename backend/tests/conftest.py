import os
import re
from pathlib import Path
from uuid import uuid4

import pytest_asyncio
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db.session import get_db
from app.main import app


@pytest.fixture
def postgres_session_factory():
    url = os.getenv("MINDLOOM_TEST_DATABASE_URL") or get_settings().database_url_direct
    schema = f"mindloom_test_{uuid4().hex}"
    admin = create_engine(url)
    with admin.begin() as connection:
        vector_schema = connection.scalar(text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'"))
        if vector_schema is not None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", vector_schema):
            raise RuntimeError("Unsupported pgvector extension schema name")
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    search_path = ",".join(dict.fromkeys([schema, vector_schema or schema, "public"]))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={search_path}"})
    try:
        alembic_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0004_notes_tags_shares"
            assert connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        yield factory
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


@pytest_asyncio.fixture
async def api_client(postgres_session_factory):
    def override_get_db():
        with postgres_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.session_factory = postgres_session_factory
    try:
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                yield client
    finally:
        app.dependency_overrides.clear()
        del app.state.session_factory


@pytest.fixture
def ws_client(postgres_session_factory):
    def override_get_db():
        with postgres_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.session_factory = postgres_session_factory
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        del app.state.session_factory


@pytest.fixture
def ingest_payload():
    return {
        "client_event_id": str(uuid4()),
        "url": "https://www.example.com/article?utm_source=news&id=5#section",
        "title": "Research article",
        "text": "A useful research article.",
        "meta": {"description": "A summary", "og_image": None, "favicon": None, "lang": "en", "site_name": "Example", "byline": None},
        "extraction": {"status": "ok", "method": "readability", "error_code": None, "error_message": None},
        "tab": {"browser_tab_id": 10, "window_id": 1, "active": False},
        "captured_at": "2026-10-01T10:00:00Z",
    }
