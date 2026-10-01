# Mindloom — Architecture

## 1. System overview

```
Chrome browser
  ├─ Tabs API ............ query + observe tab events
  ├─ Content script ...... Readability extraction in eligible pages
  └─ Service worker ...... coordinate, queue (chrome.storage), send
          │  HTTPS POST (page payloads)
          ▼
FastAPI backend
  ├─ Ingest: validate → canonicalise URL → dedupe → store
  ├─ Intelligence module (Member 4): clean, summary, keywords, embedding,
  │                                   similarity, clusters, evidence
  ├─ CRUD: workspaces, pages, edges, groups, notes, tags
  ├─ Search, export/import, share links
  └─ WebSocket hub ─────────────► React dashboard (live updates)
          │
          ▼
   Supabase PostgreSQL + pgvector (relational data and embeddings)

Dashboard ──postMessage──► Extension content script (dashboard origin) ──► service worker
          (start/stop/status)
```

Principles:
- Website = dashboard. Extension = browser-side collector. Backend = source of truth.
- Page identity (canonical URL per workspace) is separate from tab-session identity (browser tab).
- Suggested structure and manual structure are stored distinctly; manual always wins.
- Processing is asynchronous; ingest returns immediately.

## 2. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Extension | Chrome MV3, vanilla JS (or TS), `@mozilla/readability` | Permissions: `tabs`, `scripting`, `storage`; host permissions narrowed later (optional host permissions) |
| Frontend | React 18 + Vite + TypeScript, React Flow, Zustand (state), TanStack Query (fetching), Tailwind | Fixtures first, API second |
| Backend | Python 3.11, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2, Alembic | WebSocket via FastAPI |
| DB | Supabase-hosted PostgreSQL | Plain Postgres only (no Supabase Auth/Realtime); JSONB for evidence/meta/view_state |
| Vector search | pgvector extension on the same Supabase Postgres | `vector(384)` column on `page_analysis`, HNSW index (cosine); semantic search + candidate-neighbour lookup in plain SQL |
| NLP | scikit-learn (TF-IDF), sentence-transformers (`all-MiniLM-L6-v2`, 384-d), numpy, NetworkX (Louvain + PageRank), simhash-style hashing | Trafilatura as server-side fallback extractor |
| LLM (optional) | Ollama or hosted API for summaries | Behind a feature flag; extractive fallback |
| Testing | pytest + httpx + pytest-asyncio; Vitest + React Testing Library; Playwright (E2E); Jest/Vitest for extension logic | See `testing.md` |
| Tooling | pnpm/npm, ruff, black, pre-commit, GitHub Actions | Small PRs; API-changing PRs reviewed together |

## 3. Project structure (monorepo)

```
mindloom/
├─ README.md
├─ AGENTS.md                 # AI agent guidelines (from Agent.md)
├─ work.md                   # work plan
├─ sources/                  # problem_statement.png, PS2 docx
├─ docs/
│  ├─ SRS.md  Architecture.md  spec.md  Data-model.md  api.md  task.md  testing.md
│  └─ fixtures/              # sample pages, graph.json, ws events (shared)
├─ extension/                # Member 2
│  ├─ manifest.json
│  ├─ src/
│  │  ├─ background/         # service worker: tabs, queue, uploader
│  │  ├─ content/            # extractor.js, dashboard-bridge.js
│  │  ├─ lib/                # eligibility.js, canonical.js, queue.js, api.js
│  │  └─ popup/              # optional status UI
│  └─ tests/
├─ frontend/                 # Noushad
│  ├─ src/
│  │  ├─ api/                # client, types (from api.md), fixtures adapter
│  │  ├─ store/              # workspace, graph, ui state
│  │  ├─ features/           # workspaces, tracking, graph, list, node-detail,
│  │  │                      # notes-tags, search, export
│  │  ├─ components/
│  │  └─ bridge/             # extension postMessage client
│  └─ tests/
├─ backend/                  # Member 3
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ db/                 # session.py, base.py, migrations/ (alembic)
│  │  ├─ models/             # SQLAlchemy models (Data-model.md)
│  │  ├─ schemas/            # Pydantic request/response models (api.md)
│  │  ├─ api/                # routers: workspaces, pages, tab_sessions, edges,
│  │  │                      # groups, notes, tags, search, export, share, process
│  │  ├─ services/           # ingest, canonical_url, search, export, share, events
│  │  ├─ ws/                 # connection manager, event publisher
│  │  ├─ jobs/               # in-process background queue (asyncio)
│  │  └─ intelligence/       # Member 4 package (pure functions, no DB access)
│  │      ├─ clean.py  summarize.py  keywords.py  embed.py
│  │      ├─ similarity.py  cluster.py  evidence.py  dedupe.py
│  │      └─ interface.py    # the contract backend calls
│  └─ tests/
│     ├─ unit/  integration/  fixtures/
└─ e2e/                      # Playwright journeys + demo data (Member 4)
```

## 4. Key components and boundaries

| Component | Owner | Talks to | Contract |
|---|---|---|---|
| Dashboard | Noushad | Backend REST + WS; extension via postMessage | `api.md`, bridge messages in `spec.md` |
| Extension | Member 2 | Backend `POST /pages`; dashboard bridge | `api.md` §Ingest |
| Backend | Member 3 | DB; calls `intelligence.interface` | `api.md`, `Data-model.md` |
| Intelligence | Member 4 | Called by backend jobs | `intelligence/interface.py` (spec.md §M6) |

### Intelligence interface (backend ↔ Member 4)

```python
# app/intelligence/interface.py
def process_page(text: str, title: str, url: str) -> PageAnalysis:
    """-> cleaned_text, summary, keywords[list[str]], simhash(int), embedding(list[float]|None)"""

def compute_relationships(pages: list[PageAnalysisRow],
                          rejected_pairs: set[tuple[str, str]],
                          params: ProcessParams) -> RelationshipResult:
    """-> candidate_edges[{source,target,type,confidence,evidence}],
          clusters[{label, page_ids, keywords}]"""
```

Pure functions — no DB, no network (except optional LLM). Backend owns persistence and override rules.

## 5. Data flow (happy path)

1. Dashboard → extension: `MINDLOOM_START {workspaceId, apiBase, excluded[]}`.
2. Service worker `tabs.query({})` → filters ineligible URLs → reports `tabs_found` to dashboard.
3. For each eligible tab: `scripting.executeScript` runs extractor → payload.
4. Payload queued in `chrome.storage.local`, uploaded with retry → `POST /workspaces/{id}/pages`.
5. Backend validates, canonicalises URL, upserts Page + TabSession, enqueues job, returns `201` with status `extracted`/`processing`. WS event `page.discovered`.
6. Job runs `process_page` → stores summary/keywords/embedding → WS `page.processing_completed`.
7. After a debounce (or manual "Recompute"), `compute_relationships` runs → suggested edges/groups merged respecting overrides → WS `graph.changed`.
8. Dashboard applies events to local store; on reconnect it refetches `GET /graph`.

## 6. Cross-cutting decisions

- **Override model:** edges/groups/memberships carry `origin` (`suggested`|`manual`); rejected suggestions persist as tombstones (`status='rejected'`); recompute never touches manual rows or tombstoned pairs.
- **Idempotency:** unique `(workspace_id, canonical_url)`; repeated ingest updates the same Page and bumps `content_hash` only if text changed.
- **Live updates:** WebSocket per workspace, events carry a monotonically increasing `seq`. Missed events are recovered by refetching the graph snapshot.
- **Security (hackathon level):** CORS allow-list (dashboard origin + `chrome-extension://<id>`), payload size limit (2 MB text), text truncation, share tokens are random 32-byte URL-safe strings. Real auth is a post-hackathon item.
- **Privacy:** extractor never reads inputs/forms/password fields; excluded domains enforced in the extension *and* rejected by the backend; delete endpoints hard-delete text.
- **Errors:** uniform JSON error envelope (`api.md` §Conventions).
- **Config:** `.env` — `DATABASE_URL` (Supabase pooler), `DATABASE_URL_DIRECT` (migrations), `CORS_ORIGINS`, `MAX_TEXT_CHARS`, `LLM_BACKEND=none|ollama|api`.

## 7. Dependencies

**Backend (`requirements.txt`)**: fastapi, uvicorn[standard], pydantic>=2, sqlalchemy>=2, alembic, asyncpg (or psycopg[binary]), pgvector, python-multipart, httpx, scikit-learn, numpy, networkx, trafilatura (fallback), sentence-transformers, pytest, pytest-asyncio, ruff.

**Frontend**: react, react-dom, vite, typescript, reactflow, zustand, @tanstack/react-query, tailwindcss, vitest, @testing-library/react, playwright.

**Extension**: @mozilla/readability (bundled with esbuild), vitest (logic tests).

## 7a. Managed data services

**Supabase Postgres (source of truth)**
- Used only as hosted Postgres. FastAPI is the sole client; the frontend and extension never talk to Supabase directly, so the anon key is not used and is never shipped to the browser.
- Two connection strings: pooled (transaction pooler, port 6543) for the app, direct/session (port 5432) for Alembic migrations. With asyncpg behind the transaction pooler, disable the prepared-statement cache (`statement_cache_size=0`).
- Secrets only in `.env` (git-ignored). Share one project/DB between teammates for the demo, or give each a schema/branch for development.
- Full-text search uses a generated `tsvector` column + GIN index (replaces SQLite FTS5).

**pgvector (vectors, same database)**
- Enable once in Supabase (Database → Extensions → `vector`, or `CREATE EXTENSION IF NOT EXISTS vector;` in migration 0).
- `page_analysis.embedding vector(384)` (MiniLM) with an HNSW index: `CREATE INDEX ON page_analysis USING hnsw (embedding vector_cosine_ops);`
- Write path: job `analyze_page` → MiniLM embedding → stored in the same row/transaction as summary and keywords. Page or workspace delete cascades the vector; no separate sync.
- Read paths (always filtered by workspace via join on `pages.workspace_id`): (1) candidate edges — for each page, top-5 neighbours: `SELECT p.id, 1-(a.embedding <=> :vec) AS score FROM page_analysis a JOIN pages p ON p.id=a.page_id WHERE p.workspace_id=:ws AND p.id<>:pid ORDER BY a.embedding <=> :vec LIMIT 5;` then Member 4's code scores/types/clusters the pairs; (2) semantic search — embed the query, same SQL, merge with full-text hits; (3) near-duplicate hints alongside SimHash.
- Embeddings are required (no TF-IDF fallback for vectors); TF-IDF stays for keywords only. Pre-download MiniLM before the demo.

## 8. Deployment (demo)

Local: `uvicorn app.main:app --reload` (8000), `vite` (5173), extension loaded unpacked. One `docker-compose.yml` is optional after the vertical slice.

## 9. Risks (architecture-level)

| Risk | Mitigation |
|---|---|
| MV3 worker killed mid-upload | Durable queue in `chrome.storage.local`, resume on wake |
| Noisy text → poor clusters | Readability + server cleanup; users can remove pages |
| Misleading relationships | Evidence required; confidence shown; reject persists |
| Model download slow on demo machine | Pre-download MiniLM before demo |
| Dashboard↔extension handshake fragile | Fixtures + mock bridge so frontend/extension can be built independently |
