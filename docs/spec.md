# Mindloom — Functional Specification

Each module lists: purpose, behaviour, workflow, rules/edge cases. IDs reference `SRS.md`.

---

## M1. Workspace management (Backend + Frontend)

**Purpose:** independent research projects (R5).

**Behaviour**
- Create, rename, list, archive/delete workspaces. Each has its own pages, tab sessions, edges, groups, notes, tags, view state.
- `view_state` (JSON) stores: active view mode, zoom/pan, node positions (also on page rows), filters, selected node, search text. Saved on change (debounced 1 s) and on tab close.
- Opening a workspace loads `GET /workspaces/{id}/graph` and restores `view_state`.

**Workflow:** Select workspace → graph loads → user works → state autosaves → reload resumes at same place.

**Rules:** no cross-workspace reads; deleting a workspace cascades all children; same URL may exist in two workspaces independently.

---

## M2. Browser extension (Member 2)

**Purpose:** collect user-approved tabs without the user visiting each tab (FR-7.x).

**Behaviour**
1. **Bridge** — content script on dashboard origin relays `window.postMessage` ⇄ `chrome.runtime` messages. Messages (all carry `source:"mindloom"`, `id`):
   - Dashboard → ext: `PING`, `START {workspaceId, apiBase, excludedDomains[], tabIds?}`, `STOP`, `COLLECT_NOW {tabIds?}`, `GET_STATUS`, `LIST_TABS`.
   - Ext → dashboard: `PONG {version}`, `STATUS {tracking, queued, lastError}`, `TABS {tabs:[{tabId,url,title,eligible,reason?}]}`, `TAB_RESULT {tabId,url,status,error?}`.
2. **Eligibility** — only `http(s)` URLs; reject `chrome://`, `chrome-extension://`, `about:`, `file:` (unless enabled), Chrome Web Store, `view-source:`, excluded domains. Reason codes: `restricted_url`, `excluded_domain`, `no_permission`, `injection_blocked`, `empty_content`, `pdf_unsupported`.
3. **Extraction** — inject extractor: Readability → fallback `document.body.innerText`; strip input/password/textarea values; also collect `meta` (description, og:image, favicon, lang, site name, byline). Truncate text to 100k chars client-side.
4. **Live tracking** (while tracking = true) — `onCreated` → lightweight discovered event; `onUpdated(status=complete)` → extract; `onActivated` → update `active` only (no re-extraction); `onRemoved` → close tab session. Re-extract only if URL changed.
5. **Queue** — each payload stored in `chrome.storage.local` with `attempts`, `nextAttemptAt`; uploader drains with exponential backoff (1, 2, 4… max 60 s); on service-worker start it resumes. Duplicate-suppression key = `tabId + url + contentHash`.
6. **Stop** — halts listeners, clears no data already sent, keeps queue unless user clears.

**Workflow:** Install → open dashboard → `PING/PONG` (shows "Extension connected") → Start Tracking → tab picker → `START` → results stream back as `TAB_RESULT`.

**Failure rules:** restricted pages surface in UI with reason; upload `5xx/network` retries; `4xx` does not retry (marks failed with message).

---

## M3. Ingestion & persistence (Backend)

**Purpose:** reliably store pages and tab sessions (FR-1.1, R5).

**Behaviour**
- `POST /workspaces/{id}/pages` validates payload, rejects excluded domains (`422 excluded_domain`), canonicalises URL, upserts Page by `(workspace_id, canonical_url)`, upserts TabSession by `(workspace_id, browser_tab_id, page_id)`.
- Canonical URL: lowercase scheme/host, drop `www.`, drop fragment, remove tracking params (`utm_*`, `fbclid`, `gclid`, `mc_*`, `ref`), sort remaining params, strip trailing slash, drop default ports.
- If same canonical URL exists: reuse Page, update `last_seen_at`; if `content_hash` changed → reprocess.
- Extraction failure reports create/update a Page with `status=extraction_failed` and `error_code`, so the dashboard can show them.
- Closing a tab (`PATCH /tab-sessions/{id}` or `POST /tab-sessions/close`) sets `state=closed`; **never deletes the Page**.
- Processing statuses: `discovered → extracting → extracted → processing → ready` | `extraction_failed` | `processing_failed`.

**Workflow:** payload → validate → upsert → enqueue job → 201 → WS `page.discovered` → job → WS `page.processing_completed`.

---

## M4. Graph editing: nodes, edges, groups (Backend + Frontend)

**Purpose:** R1, R2 override, R3 categories.

**Behaviour**
- Node: drag to move (saves `pos_x,pos_y` via `PATCH /pages/{id}`); delete removes from workspace (hard delete text, keep tombstone of canonical URL optionally to prevent re-adding — configurable).
- Edge: create by dragging handle → `POST /edges` with `origin=manual`, chosen `type`. Edit type/label. Delete manual edge → row deleted. Delete a **suggested** edge → marked `status=rejected` (tombstone). "Accept" a suggested edge → `origin` remains `suggested`, `status=accepted` (survives recompute and stops being styled as tentative).
- Edge types: `related_to`, `source_of` (source → topic), `answers` (question → answer), `supports`, `references`, `navigated_to`, `duplicate_of`, `custom` (label).
- Groups: create/rename/colour/category (`topic|source|importance|custom`); add/remove members; dragging a node into a group sets membership `origin=manual`. Suggested groups appear with dashed style until accepted or edited.
- Visual distinction: suggested = dashed line + confidence badge; manual = solid; accepted = solid lighter; rejected hidden (restorable from "Rejected" panel).

**Override rules (contract for recompute)**
1. Never modify or delete `origin=manual` edges/memberships.
2. Never recreate a pair in `status=rejected`.
3. Suggested groups may be regenerated; if a suggested group has ≥1 manual edit (rename, member change) it is promoted to `origin=manual` and frozen.
4. Recompute replaces only `origin=suggested, status=suggested` rows.

---

## M5. Notes, tags, highlights (Backend + Frontend)

- Note belongs to a page or group: `kind = note | highlight | comment`; highlight stores `quote` (selected text) and optional `source_offset`.
- Tags: workspace-scoped unique names with colour; attach to pages and groups. Deleting a tag detaches it everywhere.
- Notes editable inline; markdown rendering (sanitised).
- Search indexes notes and tags (M7).

---

## M6. Research intelligence (Member 4)

**Purpose:** R2 — automatic organisation with evidence.

**Pipeline per page (`process_page`)**
1. Clean: collapse whitespace, drop boilerplate lines (cookie banners, nav-like short lines), cap 50k chars.
2. Keywords: TF-IDF top 10–15 terms (workspace-level IDF when ≥5 pages; otherwise per-document).
3. Summary: extractive (top 3 sentences by centrality) ≤ 400 chars; optional LLM summary if flag on. Always keep `source_url`.
4. Fingerprint: 64-bit SimHash for near-duplicate detection.
5. Embedding: MiniLM 384-d vector, stored in pgvector by the backend (intelligence code only returns the vector).

**Pipeline per workspace (`compute_relationships`)**
1. Similarity: backend supplies pgvector top-k neighbours + scores (cosine); Jaccard on keywords as a secondary signal; +0.10 same-domain bonus, clamp 0–1.
2. Candidate edges where score ≥ `edge_threshold` (default 0.35), top-k=5 per node.
3. Edge type heuristics:
   - `duplicate_of`: SimHash Hamming ≤ 3 on same domain, or same canonical content hash.
   - `question_to_answer` → `answers`: source title/first heading is a question (`?`, `how/what/why…`) and target has higher centrality and mentions the question's keywords.
   - `source_of`: target is a hub (high PageRank) and source is primary/original (domain is docs/paper/gov/etc. or cited by the target's outbound links when available).
   - default `related_to`.
4. Clusters: Louvain (resolution default 1.0) on the thresholded graph; singleton clusters are left ungrouped; label = PageRank-weighted top keywords.
5. Evidence per edge: shared top keywords (≥2) and the best matching sentence from each page (≤200 chars). **Edges with no evidence are dropped.**
6. Skip pairs in `rejected_pairs`.

**Output:** `candidate_edges[]`, `clusters[]` (see `api.md` Edge.evidence schema).

**Quality bar:** evaluation set of ≥ 12 known related and ≥ 6 known unrelated pages; precision of suggested edges ≥ 0.7 on the set before demo.

---

## M7. Search & views (Backend + Frontend)

**Search**
- `GET /workspaces/{id}/search?q=&scope=all|pages|notes|tags|groups`.
- Matches title, URL, domain, summary, extracted text, notes, tags, group names. Ranking: title/tag exact > keyword > text > notes. Returns `{type, id, page_id, snippet, score}`; frontend centres/zooms to `page_id` and pulses the node (FR-4.2).
- Fuzzy/prefix support; `#tag` and `@domain` filters (Weft-inspired).
- Implementation: Postgres full-text (`tsvector`). Semantic search: embed the query and run a pgvector nearest-neighbour query scoped to the workspace, merge with text hits (P1).

**Views (frontend)**
- **Graph** — full knowledge graph, group hulls coloured, edge styles per M4.
- **Focus** — selecting a group or node shows only it + N-hop neighbours (N=1 default, slider 1–3), "Back to full graph".
- **List/Grid** — sortable (recent, domain, group, status), grouped by group, keyboard navigable (`j/k/Enter/o`, `/` search).
- View mode persisted in `view_state`.

---

## M8. Live updates (Backend + Frontend)

- WS endpoint `/ws/workspaces/{id}?token=`. Envelope `{type, workspace_id, seq, ts, data}`.
- Events: `page.discovered`, `page.extraction_completed`, `page.extraction_failed`, `page.processing_completed`, `page.processing_failed`, `graph.changed` (`{changed:{pages,edges,groups}}`), `workspace.updated`, `ping`.
- Client behaviour: apply event to store; if `seq` gap or reconnect → refetch `GET /graph`. Reconnect with backoff (1→30 s).
- Edits made by any client emit `graph.changed` so collaborators see them.

---

## M9. Sharing, collaboration & export (Backend + Frontend)

**Export**
- JSON (`schema_version: 1`): workspace, pages (url, title, domain, summary, status), groups, edges (type, origin, evidence), notes, tags, view_state. Importable (`POST /workspaces/import`).
- Markdown: one section per group, each page as a link with summary, notes, tags, relationships list ("A → answers → B").
- Text of pages excluded from export by default (`include_text=true` to add).

**Sharing**
- `POST /workspaces/{id}/share {role: view|edit}` → token + URL `/s/{token}`.
- View role: read-only graph. Edit role: can add/edit notes, edges, groups, tags; cannot delete workspace or manage shares.
- Revoke via `DELETE /shares/{id}`. Last-write-wins on concurrent edits; `updated_at` returned on every object.
- Clearly documented: a shared export file is **not** live collaboration.

---

## M10. Privacy & controls (All)

- Explicit Start; visible tracking indicator; Stop at any time.
- Exclusion list (domains, regex-free) stored per workspace, enforced in extension and backend.
- "What we collect" panel: URL, title, extracted text, metadata; sent only to configured backend.
- Delete page / delete workspace removes stored text, summaries, embeddings.
- Never collect form values, passwords, cookies, or storage.

---

## M11. Dashboard UI (Noushad)

Screens: Workspace selector · Tracking bar (extension status, Start/Stop, tab picker, per-tab results) · Graph view · List/Grid view · Node detail drawer (title, URL, preview, summary, status, tags, notes, edges with evidence, open original) · Group panel · Search palette (`/` or Ctrl+K) · Export/Share dialog · Rejected suggestions panel.

UX rules: loading and error states for every async action; extraction errors shown in plain language with the reason code; suggested items always visually distinct; every edge click shows evidence or "manual".

---

## Cross-module workflow: end-to-end journey

1. Create workspace "AI in healthcare".
2. Start tracking → pick tabs → results stream; blocked tab shows "Restricted page".
3. Pages appear as nodes (status chips → ready).
4. Suggested edges/groups appear (dashed). User reads evidence, rejects one, drags a node into another group, adds a note and tag.
5. Recompute → user's changes persist.
6. Search "diagnosis" → jumps to node.
7. Reload → identical state. Create second workspace → empty and independent.
8. Export Markdown/JSON; share view-only link → collaborator opens it.
