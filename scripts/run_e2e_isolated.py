"""Run the E2E journey against a temporary migrated PostgreSQL schema.

This helper starts its own API server, streams both server and journey logs to
the current terminal, and drops only the schema it created afterward.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def main() -> int:
    schema = f"mindloom_e2e_{uuid4().hex}"
    if not re.fullmatch(r"mindloom_e2e_[a-f0-9]{32}", schema):
        raise RuntimeError("Unsafe temporary schema name")
    direct_url = get_settings().database_url_direct
    admin = create_engine(direct_url, pool_pre_ping=True)
    server: subprocess.Popen | None = None
    schema_created = False
    try:
        with admin.begin() as connection:
            vector_schema = connection.scalar(text(
                "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'"
            ))
            if vector_schema is not None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", vector_schema):
                raise RuntimeError("Unsupported pgvector schema name")
            connection.execute(text(f"CREATE SCHEMA {schema}"))
        schema_created = True
        print(f"E2E SETUP created disposable schema {schema}", flush=True)
        search_path = ",".join(dict.fromkeys([schema, vector_schema or schema, "public"]))
        isolated_url = make_url(direct_url).update_query_dict({"options": f"-csearch_path={search_path}"})
        engine = create_engine(isolated_url, pool_pre_ping=True)
        try:
            alembic = Config(str(BACKEND / "alembic.ini"))
            with engine.begin() as connection:
                alembic.attributes["connection"] = connection
                command.upgrade(alembic, "head")
                head = connection.scalar(text("SELECT version_num FROM alembic_version"))
            print(f"E2E SETUP migrated {schema} to {head}", flush=True)
        finally:
            engine.dispose()

        port = free_port()
        base_url = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        rendered_url = isolated_url.render_as_string(hide_password=False)
        env["DATABASE_URL"] = rendered_url
        env["DATABASE_URL_DIRECT"] = rendered_url
        env["MINDLOOM_E2E_DATABASE_URL"] = rendered_url
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port),
             "--no-access-log"],
            cwd=BACKEND,
            env=env,
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f"Temporary API server exited with code {server.returncode}")
            try:
                print("E2E SETUP -> GET /api/v1/health", flush=True)
                response = httpx.get(f"{base_url}/api/v1/health", timeout=2)
                print(f"E2E SETUP <- GET /api/v1/health: {response.status_code}", flush=True)
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                print("E2E SETUP <- GET /api/v1/health: connection pending", flush=True)
            time.sleep(0.25)
        else:
            raise RuntimeError("Temporary API server did not become healthy")
        print(f"E2E SETUP API ready at {base_url}", flush=True)
        return subprocess.call([sys.executable, str(ROOT / "scripts" / "e2e_journey.py"),
                                "--base-url", base_url], cwd=ROOT, env=env)
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        if schema_created:
            with admin.begin() as connection:
                connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
            print(f"E2E CLEANUP dropped disposable schema {schema}", flush=True)
        admin.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
