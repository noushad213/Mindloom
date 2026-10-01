# Mindloom

> **A real-time visual research workspace and browser tab manager.**  
> Transform messy browser tab sessions into structured, persistent, and interactive knowledge graphs.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Prerequisites & Requirements](#prerequisites--requirements)
- [Quick Start Guide](#quick-start-guide)
  - [1. Database Setup](#1-database-setup)
  - [2. Backend API Setup](#2-backend-api-setup)
  - [3. Frontend Dashboard Setup](#3-frontend-dashboard-setup)
  - [4. Chrome Extension Setup](#4-chrome-extension-setup)
- [How to Use Mindloom](#how-to-use-mindloom)
- [Configuration & Environment Variables](#configuration--environment-variables)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Team Roles & Ownership](#team-roles--ownership)
- [Privacy & Principles](#privacy--principles)

---

## Overview

During deep research, users typically open dozens of browser tabs across documentation, articles, and repositories. Traditional bookmarking is static and manual, while browser tab managers merely group URLs into lists without semantic understanding or relationship mapping.

**Mindloom** bridges the gap between web browsing and knowledge management:
1. **User-Approved Tab Capture**: Captures open browser tabs via a lightweight Manifest V3 Chrome Extension only upon explicit user request.
2. **Decoupled Page Identity**: Saved research pages are decoupled from transient browser tab sessions. Closing a tab in your browser **never** deletes your saved research.
3. **Interactive Knowledge Canvas**: Visualizes research articles, repositories, and documentation as nodes in an interactive graph with auto-suggested or manually edited relationship edges.
4. **Durable & Searchable**: Stores research permanently in PostgreSQL with full-text search and `pgvector` semantic embeddings.

---

## Key Features

Mindloom delivers six core capabilities designed around an uninterrupted research workflow:

| Feature | Description |
| :--- | :--- |
| 🕸️ **Visual Research Graph** | Interactive node-link canvas powered by React Flow. Drag, group, connect, and inspect web pages as research nodes. |
| 🤖 **Automatic Organization with Manual Overrides** | Intelligent topic clustering and relationship suggestions. User-created edges and manual overrides are strictly preserved over automated updates. |
| 🏷️ **Notes, Tags & Groups** | Attach rich notes, assign taxonomical tags, and assemble pages into thematic clusters across workspaces. |
| 🔍 **Full-Text & Vector Search** | Unified search combining PostgreSQL full-text search with pgvector (384-dimensional) semantic vector similarity. |
| 🗂️ **Isolated Workspaces** | Create independent workspaces per project or topic. Switch seamlessly with persistent state across reloads. |
| 📤 **Export & Role-Based Sharing** | Export workspaces to structured JSON or clean Markdown notes. Share research canvases with view-only or editor access tokens. |

---

## System Architecture

```text
┌────────────────────────────────────────────────────────┐
│                     Google Chrome                      │
│                                                        │
│  [Tab 1]   [Tab 2]   [Tab 3]   ...   [Tab N]          │
│     │         │         │                               │
│     └─────────┴────┬────┴──────────────────────────────┘
│                    ▼
│         Chrome Extension (MV3)                          
│         (Background Service Worker)                     
│                    │                                    
│                    │  Chrome External Messaging Port    
│                    ▼                                    
│         React 19 Dashboard (Vite)                       
│         • Workspace selection & controls                
│         • Graph canvas & list views                     
│         • Real-time collection log                      
│                    │                                    
│                    │  REST API (Ingestion / CRUD)       
│                    │  WebSocket (Live Workspace Events) 
│                    ▼                                    
│         FastAPI Backend (Python 3.11+)                  
│         • In-process durable job queue (2 workers)      
│         • Canonical URL deduplication                   
│         • Full-text & pgvector search                   
│                    │                                    
│                    ▼                                    
│         PostgreSQL Database + pgvector                  
│         • Workspaces, Pages, Tab Sessions               
│         • Graph Edges, Groups, Notes, Tags              
│         • Processing Jobs & Event Logs                  
└────────────────────────────────────────────────────────┘
```

---

## Project Structure

Mindloom is organized as a monorepo using **pnpm workspaces**:

```text
mindloom/
├── apps/
│   ├── dashboard/              # React 19 + TypeScript + Vite frontend
│   │   ├── src/
│   │   │   ├── components/     # UI components (Sidebar, PageCard, Header, Log)
│   │   │   ├── api.ts          # REST client for Mindloom FastAPI backend
│   │   │   ├── extension.ts    # Chrome runtime message bridge
│   │   │   ├── integration.ts  # Contract mapping & payload normalization
│   │   │   └── types.ts        # Frontend TypeScript definitions
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   └── extension/              # Chrome Extension (Manifest V3)
│       ├── background.js       # Service worker: tab tracking & text extraction
│       ├── manifest.json       # MV3 permissions & externally_connectable config
│       └── test/test.html      # Standalone extension verification harness
│
├── backend/                    # FastAPI backend service
│   ├── app/
│   │   ├── api/                # API route controllers (pages, graph, workspaces, etc.)
│   │   ├── db/                 # SQLAlchemy 2 models, session, and Alembic migrations
│   │   ├── intelligence/       # Content extraction, NLP, clustering & embeddings
│   │   ├── jobs/               # In-process asynchronous job queue and workers
│   │   ├── schemas/            # Pydantic v2 schemas and validation contracts
│   │   ├── services/           # Business logic, auth & share tokens
│   │   ├── ws/                 # WebSocket connection manager & event dispatcher
│   │   ├── config.py           # Pydantic settings & environment configuration
│   │   └── main.py             # FastAPI application factory & lifecycle
│   ├── tests/                  # Unit and integration test suite (pytest)
│   ├── alembic.ini             # Database migration configuration
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Backend environment template
│
├── packages/
│   ├── api-client/             # Generated TypeScript client from FastAPI OpenAPI
│   └── shared/                 # Browser-safe dashboard/extension utilities only
│
├── e2e/                        # Cross-component Playwright browser journeys
│
├── scripts/
│   ├── e2e_journey.py          # Live end-to-end API and WebSocket test journey
│   └── run_e2e_isolated.py     # Automated disposable schema integration runner
│
├── sources/                    # Project source documents & research specifications
├── AGENTS.md                   # AI agent collaboration guidelines
├── work.md                     # Engineering work plan, milestones & handoffs
├── package.json                # Root package configuration with convenience scripts
├── pnpm-workspace.yaml         # Monorepo workspace configuration
└── docker-compose.yml          # Local PostgreSQL + pgvector service
```

---

## Prerequisites & Requirements

Before starting, ensure your system has the following installed:

1. **Node.js**: `v20.x` or higher (LTS recommended)
2. **pnpm**: `v9.x` or `v11.x` (`npm install -g pnpm`)
3. **Python**: `3.11` or higher (tested with Python 3.11, 3.12, 3.13)
4. **PostgreSQL**: `v15` or `v16` with the **`pgvector`** extension enabled:
   - *Option A (Docker)*: `docker run -d --name mindloom-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 pgvector/pgvector:pg16`
   - *Option B (Cloud/Supabase)*: A Supabase or managed PostgreSQL instance with `vector` extension support.
5. **Google Chrome / Chromium**: Any modern Chromium browser (Brave, Edge, Chrome) for running the extension.

---

## Quick Start Guide

Follow these steps to run the complete Mindloom stack locally.

### 1. Database Setup

Ensure PostgreSQL is running and has the `vector` extension available.

If using Docker, start the repository's PostgreSQL service from the project root:
```bash
pnpm db:up
```

The local Compose connection URL is
`postgresql+psycopg://mindloom:mindloom@localhost:5432/mindloom`.

### 2. Backend API Setup

1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your environment file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set your PostgreSQL connection strings:
   ```env
   # Application connection (supports pooler or direct connection)
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/postgres

   # Direct connection for Alembic migrations
   DATABASE_URL_DIRECT=postgresql+psycopg://postgres:postgres@localhost:5432/postgres

   # Allowed CORS origins (Dashboard URL and Chrome Extension)
   CORS_ORIGINS=http://localhost:5173,chrome-extension://REPLACE_WITH_EXTENSION_ID
   MAX_TEXT_CHARS=100000
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   The backend API will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).  
   Interactive API documentation (Swagger) is accessible at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).  
   Health check: `GET http://127.0.0.1:8000/api/v1/health`.

---

### 3. Frontend Dashboard Setup

1. In a new terminal, navigate to the repository root:
   ```bash
   # Install all monorepo dependencies
   pnpm install
   ```

2. (Optional) Set up dashboard environment variables in `apps/dashboard/.env.local`:
   ```env
   VITE_API_URL=http://127.0.0.1:8000
   VITE_EXTENSION_ID=your_chrome_extension_id_here
   ```
   *(You can obtain the Extension ID in step 4 below)*.

3. Start the dashboard dev server:
   ```bash
   # From the repository root:
   pnpm dev

   # Or directly inside apps/dashboard:
   cd apps/dashboard
   pnpm dev
   ```
   The dashboard runs at [http://localhost:5173](http://localhost:5173).

---

### 4. Chrome Extension Setup

1. Open Google Chrome (or Edge/Brave) and navigate to:
   ```text
   chrome://extensions
   ```
2. Enable **Developer mode** using the toggle in the upper-right corner.
3. Click the **Load unpacked** button.
4. Select the directory:
   ```text
   <path_to_mindloom>/apps/extension
   ```
5. Note the generated **Extension ID** (e.g. `kpkogffeknhgflomfgpbbkcbemdfpknm`).
6. Update your configuration:
   - In `apps/dashboard/.env.local`, set:
     ```env
     VITE_EXTENSION_ID=your_chrome_extension_id_here
     ```
   - In `backend/.env`, append your extension origin to `CORS_ORIGINS`:
     ```env
     CORS_ORIGINS=http://localhost:5173,chrome-extension://your_chrome_extension_id_here
     ```
   - Verify `apps/extension/manifest.json` allows your dashboard under `externally_connectable.matches` (default includes `http://localhost:5173/*`).
7. Restart the dashboard dev server (`pnpm dev`) if you created/updated `.env.local`.

---

## How to Use Mindloom

### End-to-End Research Workflow

```text
1. Open Research Tabs ──> 2. Open Mindloom Dashboard ──> 3. Click "Start Tracking"
                                                                   │
                                                                   ▼
6. Export or Share <─── 5. Annotate & Connect <─── 4. Inspect Ingested Pages
```

1. **Start Researching**:
   - Open regular tabs in Chrome containing articles, documentation, academic papers, or GitHub repositories.
   - Restricted internal pages (`chrome://`, `about:blank`), incognito tabs, and communication apps (e.g. WhatsApp, Teams) are automatically excluded.

2. **Launch Dashboard**:
   - Open [http://localhost:5173](http://localhost:5173).
   - If this is your first run, a default workspace (`My Research`) is automatically created for you. You can create additional workspaces from the sidebar.

3. **Collect Tabs**:
   - Click the **Start Tracking** button in the header.
   - The dashboard connects to the extension service worker via Chrome runtime messaging.
   - Eligible tabs are discovered and their visible text content is extracted cleanly (up to 30,000 characters per tab).
   - The extracted data is transmitted to the dashboard and ingested into the backend via `POST /api/v1/workspaces/{id}/pages`.

4. **Review & Monitor**:
   - View newly collected pages under **Saved Pages** with their titles, source domains, canonical URLs, and word counts.
   - Check the **Collection Log** for live event statuses or any extraction notices (e.g. restricted sites).

5. **Organize Knowledge**:
   - Add notes and tags to highlight key findings.
   - Group related pages together into research themes.
   - Create manual relationship edges between pages or inspect AI-suggested edges with supporting evidence.

6. **Search & Export**:
   - Use search to locate concepts across full text and vector embeddings.
   - Export your completed workspace to structured JSON or formatted Markdown for external note-taking tools (Obsidian, Notion, Logseq).
   - Generate shareable links to collaborate with peers in view-only or edit mode.

---

## Configuration & Environment Variables

### Backend Configuration (`backend/.env`)

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | **Yes** | — | SQLAlchemy connection URI for application queries (pooling supported). |
| `DATABASE_URL_DIRECT` | **Yes** | — | Direct connection URI used by Alembic for schema migrations. |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated list of allowed origins (Dashboard & Extension URI). |
| `MAX_TEXT_CHARS` | No | `100000` | Upper limit on extracted text characters saved per page. |

### Dashboard Configuration (`apps/dashboard/.env.local`)

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `VITE_API_URL` | No | `http://127.0.0.1:8000` | Base URL of the running FastAPI backend. |
| `VITE_EXTENSION_ID` | Recommended | `""` | The unique ID of your unpacked Chrome Extension. |

---

## Testing & Quality Assurance

Mindloom includes comprehensive testing suites across every tier of the application:

### Frontend Unit & Integration Tests
Runs Vitest over React components, API contracts, and message adapters:
```bash
# From repository root
pnpm test

# Or linting
pnpm lint
```

### Backend Unit & Database Tests
Runs pytest testing validation, database schemas, and API routes:
```bash
# From backend directory with active virtualenv
pytest
```
*Note: Database tests automatically create a disposable schema via Alembic and drop it upon test completion.*

### Live API & WebSocket Journey
Streams requests and real-time WebSocket events across workspace creation, page ingestion, notes, graph edges, and export:
```bash
# In one terminal: running backend server (uvicorn app.main:app)
# In another terminal:
python -u scripts/e2e_journey.py
```

### Fully Isolated End-to-End Runner
Migrates a disposable database schema, launches a temporary FastAPI server, exercises the full test journey, and tears down cleanly:
```bash
python -u scripts/run_e2e_isolated.py
```

### Standalone Extension Testing
To test the Chrome extension independently before using the React dashboard:
1. Load the extension in Chrome.
2. Open `apps/extension/test/test.html` in Chrome via a local HTTP server (e.g. `npx serve apps/extension/test` or VS Code Live Server at port 5500).
3. Paste your Extension ID and verify live tab detection, removal, and text extraction.

---

## Team Roles & Ownership

Mindloom is built as a coordinated modular system with clear member ownership:

- **Frontend Lead (Noushad)**: React dashboard UX, workspace management, tracking controls, collection event log, graph visualization, notes/tags UI, accessibility.
- **Browser Extension**: Manifest V3 extension, tab discovery, permission handling, text extraction, extension-to-dashboard messaging bridge.
- **Backend & Persistence**: FastAPI service, PostgreSQL models, Alembic migrations, deduplication, durable job queue, WebSocket events, export, and search.
- **Research Intelligence & Quality**: Text cleanup, NLP summary, pgvector embeddings, candidate edge generation, clustering, and end-to-end evaluation.

---

## Privacy & Principles

Mindloom is built with strict user-privacy and data-integrity guarantees:

1. **Explicit Collection**: Tabs are scanned and extracted **only** when the user clicks to start collection. Mindloom does not silently record browsing history.
2. **Exclusion by Default**: Incognito windows and sensitive communication platforms (e.g. WhatsApp, Microsoft Teams) are excluded automatically.
3. **No Credential Harvesting**: Scripting extractors strictly target rendered text content and ignore input fields, password forms, and credit card inputs.
4. **Decoupled Identity**: Closing a browser tab does not remove saved research. Workspaces persist until the user explicitly deletes them.
5. **Preservation of Manual Intent**: Any user edits to graph nodes, categories, or relationships take absolute precedence over automated algorithms.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
