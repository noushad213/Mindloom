# Mindloom backend

Requires Python 3.11+, PostgreSQL with permission to enable `vector`, and the dependencies in `requirements.txt`.

Install dependencies, copy `.env.example` to `.env`, and replace both placeholder connection strings. `DATABASE_URL` uses the application pooler; `DATABASE_URL_DIRECT` uses the direct/session connection for migrations. Set `CORS_ORIGINS` to the dashboard origin and the exact extension origin once the extension ID is known.

```powershell
python -m pip install -r requirements.txt
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Alembic resolves the backend package independently of the current working directory, so the migration command is safe to run from the repository root in local scripts and CI. PostgreSQL must have pgvector installed and the migration role must be allowed to run `CREATE EXTENSION IF NOT EXISTS vector`.
`GET /api/v1/health` checks the database and returns `{"status":"ok","version":"0.1.0","db":"ok"}`. The migrations enable pgvector, create the ingestion tables, and add `page_analysis`, graph storage, `processing_jobs`, and the workspace event log.

Implemented routes cover workspace CRUD, graph snapshots, single-page ingest and listing, page read/delete, tab-session listing/close, edge and group editing, notes and tags, search, JSON/Markdown export, share links, job status, processing summary, health, and `/ws/workspaces/{id}`. Ingest creates a durable job and broadcasts workspace events. The in-process queue has two workers and recovers queued/running jobs on startup. Run a single API worker until a distributed job claim/recovery policy is added.

`app/intelligence/interface.py` is deliberately a stub: it stores a visibly marked summary (`[Stub] ...`) and empty keywords, with no embedding or relationship suggestions. The `vector(384)` column and HNSW index are ready for Member 4's implementation. Search uses PostgreSQL full-text search now and adds vector neighbors when `embed_query` returns a 384-dimensional vector. Share links support `view` and `edit` roles on HTTP and WebSocket routes; owner connections without a token work.

For database tests, run `python -m pytest` from the repository root. Tests use `MINDLOOM_TEST_DATABASE_URL` when set, otherwise `DATABASE_URL_DIRECT` from `backend/.env`. The database user must be able to create schemas and enable `vector`. Each database test migrates a randomly named schema through Alembic head and drops that schema afterward. A missing or unreachable database fails the suite instead of silently skipping it.

## Live API journey

With a migrated API server running in another terminal, run `python -u scripts/e2e_journey.py` from the repository root. Set `MINDLOOM_API_BASE_URL` to override `http://127.0.0.1:8000`; set `MINDLOOM_E2E_DATABASE_URL` if the server uses a database other than `DATABASE_URL_DIRECT`. The script streams every HTTP request/status and incoming WebSocket message to stdout. It seeds one suggested edge directly because the public edge API creates manual edges only, then removes its two temporary workspaces. Use `--keep-data` to inspect them afterward.

To validate against a fresh database schema without changing the default schema or starting a server manually, run `python -u scripts/run_e2e_isolated.py`. This helper migrates a disposable schema, starts a temporary API server, streams the journey, and drops the schema afterward.
