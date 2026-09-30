# Mindloom — Testing Strategy

Each member owns tests for their area (per work plan). Member 4 coordinates end-to-end verification; defects go back to the owner of the affected component. **Do not claim a feature works end to end unless an E2E test or manual run exercised every component involved.**

## 1. Test pyramid and tooling

| Level | Scope | Tools | Owner |
|---|---|---|---|
| Unit | Pure functions and single modules | pytest · Vitest · extension logic via Vitest | Each member |
| Integration | API + DB, WS, extension ↔ backend, intelligence ↔ backend | pytest + httpx `AsyncClient`, a disposable Postgres with pgvector (local `pgvector/pgvector` Docker image or a Supabase branch); Vitest + MSW; WS test client | BE, FE, EXT, RI |
| E2E (user journeys) | Real Chrome + extension + backend + dashboard | Playwright (persistent context loading the unpacked extension) | RI |
| Manual/demo | Checklist before demo | Demo script in `task.md` | RI |

CI (GitHub Actions): lint + unit + integration on every PR; E2E on `main` or manually (needs Chrome).

---

## 2. Unit tests

### Backend (Member 3)
| ID | Target | Cases |
|---|---|---|
| U-BE-1 | `canonical_url` | strips `utm_*`, `fbclid`, `gclid`; lowercases host; removes `www.`, fragment, trailing slash, default port; sorts params; keeps meaningful params (`?id=5`); handles unicode/IDN; rejects non-http(s) |
| U-BE-2 | Ingest schema validation | missing url/title; text too long (truncate); bad extraction status; empty text with `status=ok` → `empty_content` |
| U-BE-3 | Page upsert logic | new page; same canonical URL → reuse; changed `content_hash` → reprocess flag; same `client_event_id` → idempotent |
| U-BE-4 | Status machine | valid transitions only (`discovered→extracted→processing→ready`, failures); illegal transition rejected |
| U-BE-5 | Edge rules | self-edge rejected; undirected pair ordering; duplicate pair+type → conflict; delete suggested → tombstone; delete manual → row removed |
| U-BE-6 | Override merge (`merge_recompute`) | manual edges untouched; rejected pairs not recreated; accepted kept; stale suggested replaced; promoted group frozen |
| U-BE-7 | Share role guard | `view` blocks writes; `edit` blocks workspace delete; expired/revoked token rejected |
| U-BE-8 | Export serializer | schema_version; includes evidence/origin; excludes text by default; import round-trip equals export |
| U-BE-9 | Search query parser | `#tag`, `@domain`, quoted phrases, empty query |
| U-BE-10 | Event seq | monotonic per workspace; independent across workspaces |

### Research intelligence (Member 4)
| ID | Target | Cases |
|---|---|---|
| U-RI-1 | `clean` | removes cookie/nav lines; preserves paragraphs; caps length |
| U-RI-2 | `keywords` | top terms stable; stopwords removed; empty text → `[]` |
| U-RI-3 | `summarize` | ≤ 400 chars; sentences come from the source; short text returned whole |
| U-RI-4 | `simhash` / `dedupe` | identical text → distance 0; minor edits ≤ 3; unrelated > 20 |
| U-RI-5 | `similarity` | scores in [0,1]; symmetric; same-domain bonus clamp |
| U-RI-6 | `cluster` | two obvious topics → 2 clusters; singletons ungrouped; deterministic with fixed seed |
| U-RI-7 | `evidence` | ≥ 2 shared keywords or edge dropped; snippets ≤ 200 chars and present in source text |
| U-RI-8 | Edge type heuristic | question-title → `answers`; near-dup → `duplicate_of`; default `related_to` |
| U-RI-9 | `rejected_pairs` | never appear in candidates |

### Extension (Member 2)
| ID | Target | Cases |
|---|---|---|
| U-EXT-1 | `eligibility` | `chrome://`, `chrome-extension://`, `about:`, Web Store, `view-source:`, `file:` blocked with correct reason; http/https allowed; excluded domain blocked |
| U-EXT-2 | `queue` | enqueue persists to storage mock; backoff schedule; 4xx not retried; 5xx retried; resume after "restart" (re-instantiate) |
| U-EXT-3 | Duplicate suppression | same `tabId+url+hash` within window dropped; changed content allowed |
| U-EXT-4 | Extractor (jsdom) | Readability picks article; fallback to innerText; password/input values never included; truncation |
| U-EXT-5 | Bridge message validation | rejects messages from wrong origin/source; unknown types ignored |
| U-EXT-6 | Tab event handler | `onActivated` does not trigger extraction; `onUpdated` URL change does |

### Frontend (Noushad)
| ID | Target | Cases |
|---|---|---|
| U-FE-1 | Store reducers | apply WS events; `seq` gap triggers refetch; optimistic edit rollback on failure |
| U-FE-2 | Graph mapper | API graph → nodes/edges; styles by origin/status; hides rejected |
| U-FE-3 | Search palette | debounce; result selection dispatches focus-node; keyboard nav |
| U-FE-4 | Components | status chip states; error message for each reason code; evidence popover with/without evidence; accessible names/roles |
| U-FE-5 | View-state | serialises/restores mode, zoom, filters |

---

## 3. Integration tests

| ID | Scenario | Components | Assertion |
|---|---|---|---|
| I-1 | Ingest → persist → read | BE + DB | POST payload → `GET /pages` returns it; restart app (new engine on same DB file) → still present |
| I-2 | Same URL via two tabs | BE | two tab_sessions, one page |
| I-3 | Close tab | BE | tab_session `closed`; page remains |
| I-4 | Excluded domain | BE | 422 `excluded_domain`; nothing stored |
| I-5 | Idempotent retry | BE | same `client_event_id` twice → one page, same response |
| I-6 | Extraction failure report | BE | page `extraction_failed` with `error_code` |
| I-7 | Workspace isolation | BE | ids from workspace A not readable/writable through B's routes (404); same URL in both workspaces independent |
| I-8 | WS flow | BE | connect → `hello`; ingest → `page.discovered`; job → `page.processing_completed`; events ordered by `seq` |
| I-9 | Processing pipeline | BE + RI | pages with known related set → suggested edges with evidence persisted; status `ready` |
| I-10 | Override survival | BE + RI | reject edge, add manual edge, rename suggested group → `POST /process` → rejected absent, manual present, renamed group intact |
| I-11 | Search | BE | title / note / tag / group-name hits; `#tag`, `@domain`; jump payload has `page_id` |
| I-12 | Export/import | BE | export JSON → import → structurally equal (ids remapped); Markdown contains links, notes, relationships |
| I-13 | Share roles | BE | view token can GET, cannot POST; edit token can add note; revoked token 403 |
| I-14 | Extension → backend | EXT + BE | real extension code against running test server: payload accepted, retry after server down/up |
| I-15 | Dashboard ↔ extension bridge | FE + EXT | `PING` → `PONG`; `START` → `STATUS tracking=true`; `LIST_TABS` returns eligibility reasons |
| I-16 | Frontend vs API contract | FE + BE | FE typed client checked against `docs/fixtures` and OpenAPI schema (contract test in CI) |
| I-17 | Large payload | BE | 2.1 MB → 413; 100k-char text accepted/truncated |
| I-18 | Concurrency | BE | 30 parallel ingests → no duplicates, no lost pages, job queue honours concurrency limit |

---

## 4. End-to-end user journeys

Each journey runs against real Chrome (Playwright persistent context with the unpacked extension), a live backend (fresh DB) and the dashboard. Test pages are served from a local static server (`e2e/site/`) so results are repeatable, plus a small set of real sites for the manual demo.

### E2E-1 — First capture (vertical slice, **P0**)
1. Open dashboard, create workspace "AI in healthcare".
2. Dashboard shows "Extension connected".
3. Open 3 article tabs; click **Start Tracking**; accept default tab selection.
4. **Expect:** 3 page rows with status progressing to `ready`, titles/domains shown.
5. Reload dashboard → same 3 pages present.

### E2E-2 — Restricted / failing pages
1. Include `chrome://extensions` and an excluded-domain tab.
2. **Expect:** both shown as not collected with reasons (`restricted_url`, `excluded_domain`); no backend rows; other pages unaffected.

### E2E-3 — Live tracking
1. With tracking on, open a new article tab while staying on the dashboard.
2. **Expect:** node appears without refresh; switching between tabs does **not** re-extract (upload count unchanged).
3. Close the tab → tab indicator shows closed; page remains.
4. Click **Stop**; open another tab → nothing collected.

### E2E-4 — Service-worker restart resilience
1. Take backend offline; capture 2 tabs (queued).
2. Kill/restart the extension service worker (via `chrome://serviceworker-internals` or Playwright); bring backend online.
3. **Expect:** both pages delivered exactly once.

### E2E-5 — Automatic organisation with override
1. Workspace with ≥ 8 pages (two topics + duplicates).
2. **Expect:** suggested groups/edges (dashed) with evidence on click; duplicate flagged.
3. Reject one edge; drag a node into another group; add a manual edge.
4. Click **Recompute**.
5. **Expect:** rejected edge absent; manual edge and membership intact; evidence never empty.

### E2E-6 — Notes, tags, search, views
1. Add note + highlight + tag to a node; create a custom group.
2. Search for a word present only in the note → result; select → graph centres on node and pulses.
3. Switch Graph → Focus (group) → List/Grid; sort and keyboard-navigate (`j/k/Enter`).
4. Reload → same view mode and selection.

### E2E-7 — Multiple workspaces
1. Create second workspace "Climate"; capture different pages.
2. Switch between them → each shows only its own nodes, notes, edges; each resumes at its saved view.
3. Delete "Climate" → "AI in healthcare" unaffected.

### E2E-8 — Export and share
1. Export Markdown and JSON → files contain links, notes, tags, relationships.
2. Import JSON → new workspace matches.
3. Create view-only share link; open in incognito → graph visible, edit controls disabled.
4. Create edit link → collaborator adds a note → appears live in the owner's window.

### E2E-9 — Privacy controls
1. Page contains a password field and filled textarea → extracted text excludes them.
2. Delete a page → `GET /pages/{id}` 404 and text gone from export/search.
3. Tracking indicator visible only while tracking.

---

## 5. Non-functional checks

| Check | Method | Target |
|---|---|---|
| Ingest latency | Locust/`hey` 50 req | p95 < 500 ms (processing async) |
| Recompute time | 100-page fixture | < 30 s (TF-IDF) |
| Graph rendering | 200 nodes / 400 edges manual | smooth pan/zoom |
| Accessibility | axe + keyboard pass on list view, drawer, search | no critical issues |
| Security | payload limit, CORS origins, token guard, HTML sanitising of notes (XSS test: `<script>` in note/title) | pass |

## 6. Quality evaluation (Member 4)

- **Evaluation set:** ≥ 12 known related pairs, ≥ 6 unrelated pairs, ≥ 2 near-duplicates, ≥ 2 question/answer pairs.
- **Metrics:** precision ≥ 0.7 and recall ≥ 0.5 for suggested edges at default threshold; zero edges without evidence; manual override survival = 100%.
- Report misleading links found and whether they were fixed or documented.

## 7. Test data and fixtures

- `docs/fixtures/*.json` — Page, Edge, Graph, ingest payload, WS events (BE publishes).
- `backend/tests/fixtures/pages/*.txt` — article texts (RI).
- `e2e/site/` — static pages: two topic clusters, duplicates, Q&A pair, password/form page, long page.
- Seed script: `python -m app.scripts.seed --workspace demo`.

## 8. Release / demo gate (all must pass)

- [ ] U-*, I-* green in CI
- [ ] E2E-1, 2, 3, 5, 7 green; E2E-4, 6, 8, 9 green or known limitations documented
- [ ] Evaluation metrics met
- [ ] Demo script rehearsed twice from a clean DB
- [ ] Known limitations listed in README (PDFs, dynamic pages, no real auth)
