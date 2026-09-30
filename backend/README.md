# Mindloom backend

Requires Python 3.11+, PostgreSQL with permission to enable `vector`, and the dependencies in `requirements.txt`.

From `backend/`, install dependencies, copy `.env.example` to `.env`, and replace both placeholder connection strings. `DATABASE_URL` uses the application pooler; `DATABASE_URL_DIRECT` uses the direct/session connection for migrations. Set `CORS_ORIGINS` to the dashboard origin and the exact extension origin once the extension ID is known.

```powershell
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

`GET /api/v1/health` checks the database and returns `{"status":"ok","version":"0.1.0","db":"ok"}`. The migrations enable pgvector, create the ingestion tables, and add `page_analysis`, graph storage, `processing_jobs`, and the workspace event log.

Implemented routes cover workspace CRUD, graph snapshots, single-page ingest and listing, page read/delete, tab-session listing/close, job status, processing summary, health, and `/ws/workspaces/{id}`. Ingest now creates a durable job and broadcasts workspace events. The in-process queue has two workers and recovers queued/running jobs on startup. Run a single API worker until a distributed job claim/recovery policy is added.

`app/intelligence/interface.py` is deliberately a stub: it stores a visibly marked summary (`[Stub] ...`) and empty keywords, with no embedding or relationship suggestions. The `vector(384)` column and HNSW index are ready for Member 4's implementation. Share-token WebSocket access remains unavailable until share links are implemented; owner connections without a token work.

For database tests, run `python -m pytest` from the repository root. Tests use `MINDLOOM_TEST_DATABASE_URL` when set, otherwise `DATABASE_URL_DIRECT` from `backend/.env`. The database user must be able to create schemas and enable `vector`. Each database test migrates a randomly named schema through Alembic head and drops that schema afterward. A missing or unreachable database fails the suite instead of silently skipping it.
