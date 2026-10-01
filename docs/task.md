# Mindloom — Phase-wise Implementation Plan

Follows the 7 phases in the PS2 research document, organised into the work plan's three milestones. Owners: **FE** = Noushad (frontend), **EXT** = Member 2, **BE** = Member 3 (backend), **RI** = Member 4 (research intelligence & QA).

Priority tags: **P0** = needed for the first demo · **P1** = needed for full requirement coverage · **P2** = if time permits.

Rule of the plan: **prove browser → backend → dashboard first; add AI after.**

---

## Phase 0 — Kickoff (everyone, ~30–45 min)

- [ ] Review `SRS.md`, `api.md`, `Data-model.md` together; settle open decisions D1–D8 (SRS §8). **P0**
- [ ] Create monorepo skeleton (`extension/ frontend/ backend/ docs/ e2e/`), copy `AGENTS.md`, `work.md`, `sources/`. **P0**
- [ ] BE publishes `docs/fixtures/` (sample Page, graph.json, ingest payload, WS events). **P0**
- [ ] Create Supabase project, enable `vector` extension; share `.env.example` (no secrets) **P0**
- [ ] Agree branch/PR rules (small PRs; API-changing PRs reviewed by BE + FE + EXT). **P0**

**Exit:** everyone can run their own skeleton; fixtures committed.

---

## Phase 1 — Extension foundation & vertical slice start (Milestone 1)

| Owner | Task | Pri |
|---|---|---|
| EXT | MV3 manifest (`tabs`, `scripting`, `storage`), service worker, dashboard bridge content script, `PING/PONG`, `LIST_TABS` | P0 |
| EXT | `eligibility.js` (restricted URL rules + reason codes) | P0 |
| FE | Vite/React app shell, workspace selector, tracking bar, extension-connected indicator (mock bridge first) | P0 |
| BE | FastAPI skeleton, config, DB session, Alembic, `/health`, CORS | P0 |
| BE | Workspaces CRUD + `GET /graph` (empty) | P0 |
| RI | Collect 15–20 real sample pages (related / unrelated / duplicate / blocked) as fixtures; write the evaluation set | P0 |

**Exit:** dashboard lists permitted open tabs via the extension.

### Backend time-box for Phase 1 (≈ 45 min)
1. Project scaffold + `requirements.txt` + `.env` (10 min)
2. SQLAlchemy models for `workspaces, pages, tab_sessions` + initial migration (20 min)
3. Workspaces CRUD + health + CORS (15 min)

---

## Phase 2 — Content extraction

| Owner | Task | Pri |
|---|---|---|
| EXT | Extractor injection (Readability → innerText fallback), metadata, strip form values, truncation | P0 |
| EXT | Per-tab result reporting (`TAB_RESULT`), errors for blocked pages | P0 |
| FE | Tab picker + per-tab result list (success / failed + reason) | P0 |
| RI | Verify extractor output on sample pages; note bad sites | P1 |
| BE | Finalise ingest payload schema (Pydantic) and validation | P0 |

**Exit:** with the dashboard open, eligible tabs are extracted without visiting each; blocked pages report a reason.

---

## Phase 3 — Backend integration (completes Milestone 1 vertical slice)

| Owner | Task | Pri |
|---|---|---|
| BE | `POST /workspaces/{id}/pages` (+ batch): validation, canonical URL, upsert page + tab_session, `client_event_id` idempotency, exclusion check, size limit | P0 |
| BE | `GET /workspaces/{id}/pages`, `GET /pages/{id}`, `DELETE /pages/{id}`, tab-events, close tab session | P0 |
| BE | Page status transitions; `GET /graph` returns pages | P0 |
| EXT | Uploader with retry + durable queue (`chrome.storage.local`) | P0 |
| FE | Page list wired to API; status chips; error display; reload persistence | P0 |
| RI | Run full browser → extension → backend → dashboard path; log defects to owners | P0 |

### Backend time-box for Phase 3 (≈ 60–75 min)
1. `canonical_url` util + unit tests (15 min)
2. Ingest endpoint + upsert logic + idempotency (25 min)
3. Pages/tab-sessions read/delete endpoints (15 min)
4. Seed script + publish example responses into `docs/fixtures` (10 min)

**Exit check (Milestone 1):** a page appears in the dashboard and is still there after a browser/dashboard reload; blocked page shows a useful error.

---

## Phase 4 — Live tracking & real-time updates (Milestone 2, part 1)

| Owner | Task | Pri |
|---|---|---|
| BE | WebSocket hub, event publisher, `seq`, `event_log`, `hello`/`ping` | P0 |
| BE | In-process job queue (asyncio) with concurrency limit; job states | P0 |
| EXT | Tab event listeners (created/updated/activated/removed), Start/Stop, re-extract only on URL change, duplicate-event suppression | P0 |
| FE | WS client with reconnect + refetch; live status chips; Start/Stop UX | P0 |
| RI | Test restart of service worker mid-queue; many-tab stress (30+) | P1 |

**Exit:** new tabs and completed processing appear without refresh; worker restart loses nothing.

### Backend time-box for Phase 4 (≈ 40 min)
WS manager (15) → event emission from ingest/edits (15) → job runner (10).

---

## Phase 5 — AI processing (Milestone 2, part 2)

| Owner | Task | Pri |
|---|---|---|
| RI | `process_page`: clean, keywords (TF-IDF), extractive summary, SimHash, embedding (MiniLM 384-d) | P0 |
| RI | `compute_relationships`: similarity, thresholded candidate edges, edge-type heuristics, Louvain clusters + labels, evidence, `rejected_pairs` skip | P0 |
| RI | Evaluate against the evaluation set; tune threshold to ≥ 0.7 precision | P0 |
| BE | `page_analysis` table, call `process_page` from job, persist; `POST /workspaces/{id}/process`; merge results respecting override rules (Data-model §4); `recompute` transaction | P0 |
| BE | Duplicate detection (canonical URL + SimHash → `duplicate_of` suggestion) | P1 |
| FE | Render suggested (dashed) vs manual vs accepted edges; confidence badge; evidence popover | P0 |

### Backend time-box for Phase 5 (≈ 45 min, after RI interface is stubbed)
Stub `intelligence.interface` returning fixed data on day one so BE/FE are unblocked → swap in RI's real implementation → persistence + merge rules + tests.

**Exit:** each page has a summary; related pages get suggested edges/groups with evidence; manual overrides survive recompute.

---

## Phase 6 — Visual graph & editing

| Owner | Task | Pri |
|---|---|---|
| FE | React Flow graph: nodes (title, favicon, domain, status), edges (styles), drag/save positions, group colours/hulls | P0 |
| FE | Node detail drawer; manual edge create/edit/delete/reject/accept; rejected panel | P0 |
| BE | Edges, groups, positions, accept/reject/restore endpoints with override semantics | P0 |
| FE | Focus view and list/grid view | P1 |
| RI | Verify override persistence across recompute (automated test) | P0 |

**Exit:** user can explore and verify relationships; corrected suggestion stays corrected after recompute.

### Backend time-box for Phase 6 (≈ 45 min)
Edges CRUD (20) → groups + members (15) → override tests (10).

---

## Phase 7 — Advanced features, workspaces, sharing, export (Milestone 3)

| Owner | Task | Pri |
|---|---|---|
| BE | Notes CRUD, tags + attach/detach | P0 |
| BE | Search (Postgres `tsvector` + pgvector semantic), `#tag`/`@domain` | P0 |
| BE | Workspace isolation checks + view_state autosave | P0 |
| BE | Export JSON + Markdown; import JSON | P1 |
| BE | Share links (`view`/`edit`), role enforcement, token on WS | P1 |
| FE | Notes/tags UI, search palette with jump-to-node, workspace resume, export/share dialogs | P0/P1 |
| EXT | Tighten permissions (optional host permissions), test restricted/dynamic/duplicate pages; MutationObserver (only if time) | P1/P2 |
| RI | End-to-end checks, misleading-link review, demo dataset + script | P0 |
| ALL | P2: Q&A with sources, timeline, research-gap hints, PDF extraction | P2 |

**Exit check (Milestone 3):** two independent workspaces resume correctly; export opens outside the app; share link works. If *live collaborative editing* is required by judges, agree auth/permissions/conflict handling first (D4) — a shared export is not collaboration.

---

## Backend priority order if time runs short (3–4 h budget)

1. Workspaces + pages ingest + list (Phases 1, 3) — **must**
2. WebSocket + job states (Phase 4)
3. Stubbed → real processing + edges (Phase 5)
4. Edges/groups override endpoints (Phase 6)
5. Notes/tags/search (Phase 7)
6. Export, share (Phase 7)

## Definition of done (every task)

- Code merged via reviewed PR; `api.md`/`Data-model.md` updated if behaviour changed.
- Unit/integration tests per `testing.md` added and passing.
- Verified across the relevant components — no "works end to end" claims otherwise.

## Demo script (RI owns)

1. Open dashboard → create workspace → Start Tracking with 6–8 prepared tabs (incl. one `chrome://` and one duplicate).
2. Show statuses, graph with suggested edges, open an evidence popover.
3. Reject one edge, add manual edge + note + tag → Recompute → show persistence.
4. Search → jump to node. Reload → resume. Switch to second workspace.
5. Export Markdown → open; share view link in incognito window.
