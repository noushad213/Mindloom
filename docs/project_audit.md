# Mindloom — Project Health Audit

> Full audit of missing files, configuration, dependencies, and integration gaps.
> Performed 2026-10-01 against the current workspace state.

---

## Quick Summary

| Area | Status | Severity |
|---|---|---|
| Dashboard (Vite + React) | ✅ Running in fixture mode | Low |
| Backend (FastAPI) | 🔴 Cannot start — missing `.env` | **Critical** |
| Database (PostgreSQL via Docker) | 🔴 Container not running | **Critical** |
| Alembic migrations | ⚠️ Exist but can't run without DB | Blocked |
| Chrome extension | ⚠️ Works standalone but not wired | Medium |
| Shared packages | ⚠️ Placeholder READMEs only | Low (planned) |
| E2E tests | ⚠️ Scripts exist, need full stack | Blocked |
| Dashboard env config | ⚠️ Incomplete | Medium |

---

## 🔴 Critical: Things That Must Be Fixed First

### 1. Missing `backend/.env` file

The backend **will crash on import** because [`config.py`](file:///d:/1.%20Projects/GitHub/Mindloom/backend/app/config.py) declares `database_url` and `database_url_direct` as **required** fields (no default). There is no `backend/.env` file — only `.env.example`.

**Fix:** Create `backend/.env` from the example:

```env
# For local Docker Compose PostgreSQL
DATABASE_URL=postgresql+psycopg://mindloom:mindloom@localhost:5432/mindloom
DATABASE_URL_DIRECT=postgresql+psycopg://mindloom:mindloom@localhost:5432/mindloom
CORS_ORIGINS=http://localhost:5173,chrome-extension://REPLACE_WITH_EXTENSION_ID
MAX_TEXT_CHARS=100000
```

> [!NOTE]
> The `.env.example` references **Supabase** (port 6543 transaction pooler). For local dev with Docker Compose, both URLs should point to `localhost:5432` directly since Docker Compose exposes the plain PostgreSQL instance.

---

### 2. PostgreSQL container is not running

```
docker ps → (no mindloom containers)
```

The [`docker-compose.yml`](file:///d:/1.%20Projects/GitHub/Mindloom/docker-compose.yml) defines a `postgres` service using `pgvector/pgvector:pg16`, but it has never been started.

**Fix:**
```bash
docker compose up -d postgres
```

Then verify: `docker compose ps` should show the container healthy.

---

### 3. Alembic migrations have never been run

There are 5 migration files in [`backend/app/db/migrations/versions/`](file:///d:/1.%20Projects/GitHub/Mindloom/backend/app/db/migrations/versions) but they've never been applied (no database exists yet).

**Fix** (after DB is running and `.env` is created):
```bash
cd backend
.venv\Scripts\activate
alembic upgrade head
```

This will create all tables: workspaces, pages, tab_sessions, edges, groups, notes, tags, share_links, processing_jobs, event_logs, ingest_events, and page_analyses, plus the `pgvector` extension.

---

## ⚠️ Medium: Dashboard Configuration Gaps

### 4. Dashboard `.env.local` is missing `VITE_API_URL` and `VITE_EXTENSION_ID`

Current [`.env.local`](file:///d:/1.%20Projects/GitHub/Mindloom/apps/dashboard/.env.local) content:
```
VITE_USE_FIXTURES=true
```

This means:
- **The dashboard never talks to the real backend** — it only shows fixture data.
- **The extension ID is empty** — the "Collect tabs" button will always fail with "Extension is not configured."

**Fix** — once backend is running, update `.env.local`:
```env
VITE_API_URL=http://127.0.0.1:8000
VITE_USE_FIXTURES=false
VITE_EXTENSION_ID=<your_chrome_extension_id>
```

To get the extension ID: load `apps/extension/` as an unpacked extension in Chrome → copy the ID from `chrome://extensions`.

---

### 5. Extension not built with WXT (deviation from plan)

[`work.md`](file:///d:/1.%20Projects/GitHub/Mindloom/work.md#L43) specifies **WXT** as the extension build tool, but the actual extension is a plain [`manifest.json`](file:///d:/1.%20Projects/GitHub/Mindloom/apps/extension/manifest.json) + [`background.js`](file:///d:/1.%20Projects/GitHub/Mindloom/apps/extension/background.js) (raw Manifest V3). There's no `package.json`, no build step, no TypeScript.

**Impact:** Works for the vertical slice, but means:
- No TypeScript type-checking on extension code
- No hot reload during development
- No shared types with the dashboard
- No path to Edge/Firefox without manual manifest rewriting

**No action required now** — this is a Member 2 decision, but worth flagging.

---

## ⚠️ Low: Structural Gaps (Not Blocking, But Notable)

### 6. `packages/shared` and `packages/api-client` are empty shells

Both contain only a README explaining their *future* purpose:
- [`packages/shared/`](file:///d:/1.%20Projects/GitHub/Mindloom/packages/shared/README.md) — reserved for shared browser-safe TypeScript
- [`packages/api-client/`](file:///d:/1.%20Projects/GitHub/Mindloom/packages/api-client/README.md) — reserved for OpenAPI-generated client

Neither has a `package.json`, meaning `pnpm-workspace.yaml` includes them but they don't actually participate in the workspace.

**Impact:** No build errors, but the dashboard duplicates type definitions in [`types.ts`](file:///d:/1.%20Projects/GitHub/Mindloom/apps/dashboard/src/types.ts) and [`integration.ts`](file:///d:/1.%20Projects/GitHub/Mindloom/apps/dashboard/src/integration.ts) that should eventually come from these packages.

---

### 7. Dashboard is missing planned dependencies

Per [`work.md`](file:///d:/1.%20Projects/GitHub/Mindloom/work.md#L39), the tech stack specifies:
- **React Router** — not installed, not used
- **TanStack Query** — not installed, not used
- **Zustand** — not installed (allowed as opt-in)

The dashboard currently manages all state with `useState` and raw `fetch` calls. This works for the vertical slice but will need these libraries for proper route-based navigation, data caching, and graph-wide state.

---

### 8. No `package.json` in the extension directory

The extension at [`apps/extension/`](file:///d:/1.%20Projects/GitHub/Mindloom/apps/extension) has no `package.json`. This means:
- `pnpm-workspace.yaml` includes `apps/*` but the extension isn't a proper workspace member
- No dependency management, no scripts, no lint

---

### 9. Backend `.env.example` has a Supabase-oriented template

The [`.env.example`](file:///d:/1.%20Projects/GitHub/Mindloom/backend/.env.example) comments reference "Supabase transaction pooler" and "direct/session connection." For local Docker dev, both URLs should simply be `localhost:5432`. The example is misleading for anyone setting up locally.

---

## 📋 End-to-End Startup Checklist

Here's the exact order to go from zero to a working local stack:

```
Step 1 ─ Start the database
   docker compose up -d postgres
   # Wait for healthy: docker compose ps

Step 2 ─ Create backend/.env
   Copy from .env.example, adjust URLs to localhost:5432

Step 3 ─ Run Alembic migrations
   cd backend
   .venv\Scripts\activate
   alembic upgrade head

Step 4 ─ Start the backend
   cd backend
   .venv\Scripts\activate
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Step 5 ─ Verify backend health
   curl http://127.0.0.1:8000/api/v1/health
   # Should return: {"status":"ok","version":"0.1.0","db":"ok"}

Step 6 ─ Switch dashboard to live mode
   Edit apps/dashboard/.env.local:
     VITE_API_URL=http://127.0.0.1:8000
     VITE_USE_FIXTURES=false
   Restart: pnpm dev

Step 7 ─ (Optional) Load the Chrome extension
   chrome://extensions → Developer mode → Load unpacked → apps/extension/
   Copy the extension ID
   Add to dashboard .env.local: VITE_EXTENSION_ID=<id>
   Add to backend .env: CORS_ORIGINS=...,chrome-extension://<id>
```

---

## ✅ What's Already Working

| Component | State |
|---|---|
| Python venv (`backend/.venv`) | All 14 required packages installed |
| Node dependencies (`apps/dashboard/node_modules`) | All 11 packages installed |
| Dashboard dev server (`pnpm dev`) | Running on localhost:5173 in fixture mode |
| Docker Engine | Available (v29.6.2) |
| pnpm workspace | Configured correctly |
| Backend code | Complete — 8 API routers, 13 models, migrations, WebSocket, job queue |
| Extension code | Complete — tab discovery, extraction, external messaging |
| Dashboard code | Complete — sidebar, graph view, collection log, page drawer |

> [!IMPORTANT]
> The project has substantial code in all three components (dashboard, backend, extension). The **only blockers** are operational: missing `.env`, database not started, and migrations not run. The code itself should work once those three steps are done.
