# Work plan — Visual Research and Browser Tab Manager

## Goal and starting point

Build a research workspace that collects user-approved browser pages, saves them by project, and presents them as an editable knowledge graph. The first demo must show a real page moving from a Chrome extension into a saved workspace and appearing on the dashboard. Add automatic grouping only after that flow works.

The local repository currently has only a placeholder README. The [Weft repository](https://github.com/Avi-141/weft) is a reference for local-first tab capture, clustering, and graph exploration, not an existing codebase in this project. Decide together before reusing any code or changing the architecture below.

## Ownership for four members

| Member | Primary ownership | Concrete deliverables | Definition of done |
| --- | --- | --- | --- |
| **Member 1 — Noushad: frontend lead** | React dashboard and user experience | Workspace selector; Start/Stop and collection status; tab/page list; graph and list views; node details; manual node/edge editing; notes, tags, search, and export UI; responsive and keyboard-accessible interactions | A user can collect a page, see its status, explore it in list and graph views, edit its research structure, and return to the saved workspace. Frontend works against agreed API fixtures before integration. |
| **Member 2 — browser extension** | Chrome Manifest V3 extension and browser-to-app bridge | Tab discovery and change events; permission and eligibility handling; page extraction; explicit collection controls; dashboard-to-extension messaging; retry queue; duplicate event suppression | With the dashboard open, eligible tabs can be collected without visiting each tab. Restricted pages fail visibly, Start/Stop works, and a service worker restart does not lose pending work. |
| **Member 3 — backend and persistence** | FastAPI, database, API contracts, and live updates | Workspace/page/tab-session models; ingestion endpoints; validation and deduplication by canonical URL; notes/tags/groups/edges CRUD; search; export; processing states; WebSocket or equivalent update stream; migrations | Ingested pages survive restart, multiple tabs can refer to one page, edits persist, workspaces stay separate, and the frontend can query and resume a workspace. |
| **Member 4 — research intelligence and quality** | Content processing, relationship generation, and cross-system verification | Main-content cleanup; summaries; similarity scoring; candidate edges and topic clusters; evidence for suggested relationships; evaluation set; integration tests and demo data | Related pages receive explainable suggestions, irrelevant pages can be rejected, manual overrides survive recomputation, and the end-to-end demo is repeatable. |

Each member owns tests and documentation for their area. Member 4 coordinates end-to-end verification, but integration defects remain with the owner of the affected component. Everyone reviews the shared data contract before implementing against it.

## Shared contract to agree on first

- **Page:** stable page ID, canonical URL, title, source domain, extracted text or excerpt, summary, processing status, timestamps.
- **Tab session:** browser tab ID, page ID, open/closed state, last seen time. A closed tab does not delete a saved research page.
- **Workspace:** workspace ID and name; membership of pages, notes, tags, groups, and edges. Keep workspaces independent.
- **Edge:** source and target page IDs, relationship type, origin (`suggested` or `manual`), confidence when suggested, and supporting evidence when available. Manual deletion or correction must take precedence over regeneration.
- **Events:** page discovered, extraction completed/failed, processing completed/failed, graph changed. Agree on payload shape and reconnection behavior.
- **Privacy:** collection starts only after user action. Define allowed sites, excluded sites, retention and delete behavior, and what is sent to the backend before extension work begins.

Member 3 publishes the API schema and example payloads; Member 2 and Noushad validate them with a mocked page before building full integrations. Member 4 defines the suggested-edge fields with Member 3.

## Agreed technology stack

This is the default stack for the first vertical slice and the research workspace. Change it only through a team decision recorded in this file or an architecture decision record.

| Area | Choice | Why it fits Mindloom |
| --- | --- | --- |
| Repository | pnpm workspaces monorepo | Keeps the dashboard, extension, and shared TypeScript contracts in one install while allowing the Python API to remain an independent app. |
| Dashboard | React, TypeScript, and Vite | Fast setup, a large ecosystem, and shared types with the extension. |
| Routing and API state | React Router and TanStack Query | Covers navigation, caching, retries, loading/error states, and refresh after ingestion without a custom data layer. |
| Local UI state | React hooks first; Zustand only for graph-wide state | Avoids unnecessary global state while leaving a small, flexible option for graph interactions. |
| Styling | CSS Modules with CSS custom-property design tokens | Simple to debug and flexible enough for a distinctive accessible interface without tying the design to a component framework. |
| Graph editor | React Flow (`@xyflow/react`) | Provides draggable custom nodes, edges, zoom, selection, editing, save/restore patterns, and keyboard support under an MIT license. |
| Browser extension | WXT, TypeScript, and Chrome Manifest V3 | Generates the manifest, handles extension entry points and service-worker builds, and preserves a path to Edge and Firefox later. |
| Shared web contracts | TypeScript types generated from the backend OpenAPI schema | Keeps dashboard and extension payloads aligned with the API without maintaining duplicate hand-written models. |
| Backend API | FastAPI and Pydantic | Matches the research plan, produces OpenAPI automatically, validates ingestion payloads, and supports WebSockets when live updates are added. |
| Persistence | PostgreSQL, SQLAlchemy 2, Alembic, and psycopg | Handles relational workspace data, indexed JSONB metadata, and built-in full-text search without adding a second database. Use synchronous SQLAlchemy initially; move specific paths to async only if measurements justify it. |
| Live updates | REST first, then one FastAPI WebSocket channel per workspace | Keeps the first vertical slice easy to test while providing a direct upgrade path for processing and graph-change events. |
| Processing | Python modules inside the backend worker boundary | Reuses the backend language for extraction cleanup, similarity, clustering, and later ML libraries. Start with in-process background work; add a queue only when jobs outgrow it. |
| Testing | Vitest and Testing Library for web code; pytest for Python; Playwright for the final cross-component path | Gives each owner focused tests and one browser-level proof of the extension-to-dashboard flow. |
| Local development | Docker Compose for PostgreSQL only | Developers run dashboard, extension, and API with their native tools while sharing one reproducible database setup. |

Do not add Redux, a separate search service, a graph database, Redis/Celery, Kubernetes, or a UI component suite for the first vertical slice. Add one only when a measured requirement cannot be met cleanly by the stack above.

## Milestones and handoffs

### 1. Working vertical slice

1. **Together:** agree on project setup, API schema, one sample workspace, and what “Start Tracking” means (all eligible tabs or explicitly selected tabs).
2. **Member 2:** collect tab title/URL, then extract one eligible page and POST it to the backend.
3. **Member 3:** persist the page and return it through a workspace API; expose processing status.
4. **Noushad:** build a dashboard with collection controls, page list, status, and clear extraction errors using fixtures, then connect it to the API.
5. **Member 4:** provide sample pages and verify the full browser → extension → backend → dashboard path.

**Exit check:** A page appears in the dashboard and is still there after a browser/dashboard reload. A blocked page reports a useful error.

### 2. Research workspace

- **Noushad:** add graph view, node details, list/search navigation, notes, tags, groups, and manual edge editing.
- **Member 3:** add workspace isolation and persistence APIs for those edits, search, and export.
- **Member 2:** add live tab events, Start/Stop, retries, and clear permission states.
- **Member 4:** add summaries, duplicate detection, related-page candidates, clustering, and evidence snippets; establish a small set of expected related and unrelated pages.

**Exit check:** Users can create two independent workspaces, resume either one, find a page, annotate it, and correct an automatically suggested connection.

### 3. Sharing and polish

- **Member 3:** implement a documented workspace export format containing pages, links, notes, groups, and relationships; define an import path if time permits.
- **Noushad:** provide export controls and a readable shared/view-only presentation if a share mechanism is built.
- **Member 2:** tighten permissions and test restricted, dynamic, and duplicate pages.
- **Member 4:** run end-to-end checks, assess misleading links, and prepare a demo with known source pages.

**Exit check:** Exported research can be inspected outside the app. If collaborative editing is required for the final submission, agree on authentication, permissions, and conflict handling before starting it; do not treat a shared export as live collaboration.

## Scope decisions to avoid blocking the first demo

- Use the agreed technology stack above. Defer production hosting until the vertical slice works locally; deployment must not change the API or persistence contracts.
- Start with one-time extraction of eligible pages. Dynamic-page observation, PDFs, semantic search, and Q&A can follow once basic capture is reliable.
- Keep automatic edges editable and visibly distinct from manual edges. Do not show a generated relationship explanation without source evidence.
- Preserve saved pages when their browser tabs close. Keep tab identity separate from page identity.
- Track progress in four member-owned issue groups using the milestone exit checks above; use small pull requests and review API-changing work together.

## Source material

- [User-provided problem statement](sources/problem_statement.png): six requirements covering graph management, automatic organization, notes/tags/groups, search/views, workspaces, and sharing/export.
- [User-provided research document](sources/PS2_Visual_Research_Browser_Tab_Manager.docx): *PS 2 Real-Time Visual Research & Browser Tab Manager*. Its architecture and phases informed this plan. Its suggestions are planning input, not instructions to execute verbatim.
- [Weft on GitHub](https://github.com/Avi-141/weft): reference implementation for tab capture, local-first processing, and graph exploration.
- [AI agent guidelines](AGENTS.md): instructions for teammates' AI assistants working in this repository.
