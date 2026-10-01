# Mindloom — Software Requirements Specification (SRS)

Project: Visual Research & Browser Tab Manager (CSI TSEC 4.0, PS 2)
Status: Draft v0.1 — for team review before any implementation
Sources: problem statement, PS2 research doc, work plan, AGENTS.md, Weft README (reference only)

---

## 1. Problem

Researching a topic on the web leaves users with dozens of tabs, links and half-remembered threads. A tab bar or bookmark list stores *links* but not *relationships*:

- Users forget **why** a tab was opened.
- Related pages are scattered; themes and source → topic relationships are invisible.
- Returning to earlier research means re-opening and re-reading everything.
- Different projects (e.g. "AI in healthcare" vs "climate") get mixed in one window.

Core question the product answers: **"How is my research connected?"**

## 2. Current behaviour (as-is)

| Area | Today |
|---|---|
| Organisation | Linear tab strip, folders of bookmarks, manual tab groups |
| Relationships | None stored; user keeps them in their head |
| Context | No notes/tags attached to a tab; no summary |
| Recall | Browser history is chronological, not topical |
| Projects | Single browser session, no per-project workspace |
| Sharing | Copy-paste URLs manually; no structure preserved |
| Tools like Weft | Local-first graph of tabs, but single-user, no workspaces, no collaboration, no manual-override model |

## 3. Expected solution (to-be)

A **Chrome extension + web dashboard + backend**:

1. User opens the dashboard, selects/creates a **workspace**, clicks **Start Tracking**.
2. The extension (with user-granted permission) lists open tabs, extracts readable content from eligible pages and sends it to the backend — the user can stay on the dashboard.
3. The backend cleans, deduplicates, stores, summarises and compares pages, then **suggests** clusters and relationships with evidence.
4. The dashboard shows pages as nodes in an interactive graph (or list/grid), updating live.
5. The user can always **override**: move, connect, regroup, reject suggestions, add notes/tags.
6. Workspaces persist and resume; they can be shared and exported.

## 4. Scope

### In scope (mapped to the 6 problem-statement requirements)

| Req | Name | Functional requirements |
|---|---|---|
| R1 | Visual workspace & node management | FR-1.1 Nodes with title, URL, preview, metadata. FR-1.2 Drag/move nodes; persisted positions. FR-1.3 Manually create edges. FR-1.4 Group nodes. FR-1.5 Remove node from workspace. |
| R2 | Automatic organisation (challenging) | FR-2.1 Cluster related pages into suggested groups. FR-2.2 Suggest typed edges (source→topic, question→answer, related…). FR-2.3 Each suggestion carries confidence + evidence. FR-2.4 User can accept / edit / reject any suggestion. FR-2.5 Manual changes survive recomputation. FR-2.6 Duplicate detection (canonical URL + near-duplicate). |
| R3 | Notes, tags, groups | FR-3.1 Notes/highlights/comments on node or group. FR-3.2 Tags on nodes/groups. FR-3.3 Custom categories (groups with colour, by topic/source/importance). |
| R4 | Search, navigation, view modes | FR-4.1 Search across title, URL, summary, text, notes, tags, groups. FR-4.2 Selecting a result jumps to and highlights the node. FR-4.3 Views: full graph, focused topic (group/neighbourhood), list/grid. |
| R5 | Workspaces & sessions | FR-5.1 Multiple isolated workspaces. FR-5.2 Save/resume exactly (layout, view, filters). |
| R6 | Sharing, collaboration, export | FR-6.1 Export JSON (full) and Markdown (readable). FR-6.2 Share link (view-only at minimum). FR-6.3 Collaborative contribution (see §8 open decisions). |

### Browser-side requirements (from PS2 doc)

- FR-7.1 Discover open tabs; detect create/update/activate/remove events.
- FR-7.2 Extract title, URL, main text (Readability) and metadata from eligible pages.
- FR-7.3 Start/Stop controls; collection begins only after explicit user action.
- FR-7.4 Restricted pages (chrome://, web store, blocked injection) fail visibly with a reason.
- FR-7.5 Durable retry queue that survives MV3 service-worker restarts.
- FR-7.6 Excluded-site list; "Add to research" selection mode.

### Out of scope for first demo

Dynamic-page MutationObserver, PDF extraction, semantic Q&A over research, research-gap suggestions, timeline, real-time collaborative cursors, cloud deployment hardening. (Planned later per PS2 phase 7.)

## 5. Users and personas

- **Researcher/student** — 20–80 tabs, wants structure without manual filing.
- **Team member** — needs to view or add to a teammate's workspace.
- **Reviewer/judge** — needs a repeatable demo with known pages.

## 6. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 Privacy | Collection only after user action; no passwords/form fields; clear Start/Stop; deletion removes stored text; data collected is documented in the UI. |
| NFR-2 Reliability | Ingested pages survive backend restart; ingest is idempotent (retry-safe). |
| NFR-3 Performance | Ingest responds < 500 ms (processing async); graph of 200 nodes renders smoothly; recompute of 100 pages < 30 s on a laptop. |
| NFR-4 Explainability | No generated relationship shown without evidence (shared keywords/snippets). |
| NFR-5 Editability | Every generated structure is editable; manual edits always win. |
| NFR-6 Accessibility | Keyboard-operable list view and controls; responsive layout. |
| NFR-7 Isolation | Workspace data never leaks across workspaces. |
| NFR-8 Maintainability | Documented contract (`api.md`); each member owns tests for their area. |

## 7. Constraints and assumptions

- Chrome Manifest V3 only. Service workers may be terminated at any time.
- Hackathon time budget: backend vertical slice is ~3–4 hours of work, so scope is tiered (P0/P1/P2 in `task.md`).
- Repository currently contains only a README; Weft is a reference, not a dependency.
- Four members: Noushad (frontend), Member 2 (extension), Member 3 (backend), Member 4 (research intelligence & QA).

## 8. Open decisions (must be settled before/at kickoff)

| # | Decision | Proposed default |
|---|---|---|
| D1 | Does "Start Tracking" collect **all eligible tabs** or **selected tabs**? | Show tab picker; default = all eligible tabs checked, user can untick. |
| D2 | Database | **Decided:** Supabase-hosted PostgreSQL (via SQLAlchemy/asyncpg) for relational data. |
| D3 | Graph library | React Flow (easy drag/connect/edit). Cytoscape.js is fine if the team prefers layout algorithms. |
| D4 | Collaboration depth | Share link with `view` or `edit` token; edits propagate via WebSocket; last-write-wins. No accounts. |
| D5 | Dashboard ↔ extension channel | Dashboard `window.postMessage` ↔ extension content script on dashboard origin ↔ service worker. |
| D6 | Vectors | **Decided:** pgvector on Supabase Postgres (384-d cosine) with Sentence-Transformers MiniLM embeddings. |
| D7 | Summaries | Extractive by default; LLM (API/Ollama) optional flag. |
| D8 | Reuse of Weft code | No copying unless licence (MIT) and fit are checked; reuse ideas (canonical URL, SimHash, Louvain). |

## 9. Acceptance (demo-level)

1. Start tracking → a real page appears in the dashboard and persists after reload.
2. A blocked page reports a useful error.
3. Two workspaces stay independent; each resumes as left.
4. Related pages get suggested edges/groups with evidence; user rejects one and it stays rejected after recompute.
5. Search jumps to a node; export opens outside the app.
