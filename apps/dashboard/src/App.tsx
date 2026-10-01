import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ingestExtraction, isFixtureMode, listPages, listWorkspaces, loadOrCreateWorkspace } from "./api";
import { FIXTURE_COLLECTION_EVENTS } from "./fixtures";
import { connectToExtension, type ExtensionConnection } from "./extension";
import type { ExtensionExtractionResult } from "./integration";
import type { CollectionEvent, GraphPage, SavedPage, TrackingState, Workspace } from "./types";
import { Sidebar, type AppView } from "./components/Sidebar/Sidebar";
import { CollectionLog } from "./components/CollectionLog/CollectionLog";
import { GraphView } from "./components/GraphView/GraphView";
import { PageDrawer } from "./components/PageDrawer/PageDrawer";
import { LibraryView, NotesView, SearchView, ShareExportView } from "./components/WorkspaceTools/WorkspaceTools";
import "./App.css";

const EXTENSION_ID = import.meta.env.VITE_EXTENSION_ID || "";

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    play: <polygon points="7 4 19 12 7 20 7 4" />,
    pause: (
      <>
        <rect x="6" y="5" width="4" height="14" rx="1" />
        <rect x="14" y="5" width="4" height="14" rx="1" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
    arrow: <path d="M5 12h14M14 7l5 5-5 5" />,
    link: (
      <>
        <path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.1 1.1" />
        <path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.1-1.1" />
      </>
    ),
    file: (
      <>
        <path d="M6 3h8l4 4v14H6z" />
        <path d="M14 3v5h5" />
      </>
    ),
    more: (
      <>
        <circle cx="5" cy="12" r="1" fill="currentColor" />
        <circle cx="12" cy="12" r="1" fill="currentColor" />
        <circle cx="19" cy="12" r="1" fill="currentColor" />
      </>
    ),
  };
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

function failureEvent(result: ExtensionExtractionResult, detail?: string): CollectionEvent {
  return {
    eventId: crypto.randomUUID(),
    tabId: result.tabId,
    url: result.url || "Restricted tab",
    title: result.title || null,
    timestamp: new Date().toISOString(),
    status: "failed",
    errorCode: "extraction_failed",
    errorDetail: detail || result.error || "The page could not be collected.",
  };
}

function timeAgo(date: string) {
  const m = Math.max(0, Math.floor((Date.now() - new Date(date).getTime()) / 60000));
  return m < 1 ? "now" : m < 60 ? `${m}m` : m < 1440 ? `${Math.floor(m / 60)}h` : `${Math.floor(m / 1440)}d`;
}

const topics = [
  { name: "Language models", count: 12, width: 82, color: "teal" },
  { name: "Human–AI interaction", count: 8, width: 58, color: "amber" },
  { name: "Knowledge systems", count: 6, width: 45, color: "navy" },
  { name: "Model evaluation", count: 4, width: 31, color: "mint" },
];

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    try {
      const saved = localStorage.getItem("mindloom_theme");
      if (saved === "light" || saved === "dark") return saved;
    } catch {}
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [trackingState, setTrackingState] = useState<TrackingState>("paused");
  const [savedPages, setSavedPages] = useState<SavedPage[]>([]);
  const [collectionEvents, setCollectionEvents] = useState<CollectionEvent[]>(() =>
    isFixtureMode ? FIXTURE_COLLECTION_EVENTS.map((event) => ({ ...event })) : [],
  );
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<AppView>("overview");
  const [query, setQuery] = useState("");
  const [selectedPage, setSelectedPage] = useState<GraphPage | SavedPage | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem("mindloom_sidebar_collapsed") === "true";
    } catch {
      return false;
    }
  });

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("mindloom_sidebar_collapsed", String(next));
      } catch {}
      return next;
    });
  }, []);

  const connectionRef = useRef<ExtensionConnection | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    try {
      localStorage.setItem("mindloom_theme", theme);
    } catch {}
  }, [theme]);

  const refreshWorkspace = useCallback(async (workspace: Workspace) => {
    setLoading(true);
    setLoadError(null);
    try {
      setSavedPages(await listPages(workspace.id));
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Could not load saved pages.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function initialize() {
      try {
        const initial = await loadOrCreateWorkspace();
        if (cancelled) return;
        const available = await listWorkspaces();
        if (cancelled) return;
        setWorkspaces(available.length ? available : [initial]);
        setActiveWorkspace(initial);
        await refreshWorkspace(initial);
      } catch (error) {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : "Could not connect to the Mindloom API.");
          setLoading(false);
        }
      }
    }
    void initialize();
    return () => {
      cancelled = true;
      connectionRef.current?.disconnect();
    };
  }, [refreshWorkspace]);

  const collectResults = useCallback(
    async (results: ExtensionExtractionResult[]) => {
      if (!activeWorkspace) return;
      for (const result of results) {
        if (!result.success) {
          setCollectionEvents((events) => [
            failureEvent(result),
            ...events.filter((event) => event.tabId !== result.tabId),
          ]);
          continue;
        }
        try {
          const page = await ingestExtraction(activeWorkspace.id, result);
          setSavedPages((pages) => [page, ...pages.filter((p) => p.id !== page.id)]);
          setCollectionEvents((events) => events.filter((event) => event.tabId !== result.tabId));
        } catch (error) {
          setCollectionEvents((events) => [
            failureEvent(result, error instanceof Error ? error.message : "The API rejected this page."),
            ...events.filter((event) => event.tabId !== result.tabId),
          ]);
        }
      }
    },
    [activeWorkspace],
  );

  const handleStartTracking = useCallback(() => {
    if (!activeWorkspace || connectionRef.current) return;
    setTrackingState("starting");
    try {
      connectionRef.current = connectToExtension(
        EXTENSION_ID,
        (r) => void collectResults(r),
        () => setTrackingState("active"),
        () => {
          connectionRef.current = null;
          setTrackingState((s) => (s === "stopping" ? "paused" : "unavailable"));
        },
      );
    } catch {
      setTrackingState("unavailable");
    }
  }, [activeWorkspace, collectResults]);

  const handleStopTracking = useCallback(() => {
    setTrackingState("stopping");
    connectionRef.current?.disconnect();
    connectionRef.current = null;
    setTrackingState("paused");
  }, []);

  const handleRetryCapture = useCallback((eventId: string) => {
    const event = collectionEvents.find((item) => item.eventId === eventId);
    if (!event) return;
    if (connectionRef.current) {
      connectionRef.current.retry(event.tabId);
      return;
    }
    handleStartTracking();
  }, [collectionEvents, handleStartTracking]);

  const selectWorkspace = useCallback(
    (workspace: Workspace) => {
      setActiveWorkspace(workspace);
      void refreshWorkspace(workspace);
    },
    [refreshWorkspace],
  );

  const visiblePages = useMemo(
    () =>
      savedPages.filter((p) =>
        `${p.title} ${p.sourceDomain}`.toLowerCase().includes(query.toLowerCase()),
      ),
    [savedPages, query],
  );

  const ready = savedPages.filter((p) => ["captured", "ready", "extracted"].includes(p.status)).length;
  const processing = savedPages.filter((p) => ["processing", "queued", "extracting"].includes(p.status)).length;

  if (!activeWorkspace) {
    return (
      <main className="startupState" aria-busy={loading}>
        <span className="eyebrow">Mindloom workspace</span>
        <h1>Preparing your research desk</h1>
        <p role={loadError ? "alert" : "status"}>{loadError || "Connecting to your saved sources…"}</p>
        {loadError && <button onClick={() => window.location.reload()}>Retry connection</button>}
      </main>
    );
  }

  const viewTitle: Record<AppView, string> = {
    overview: "Research overview",
    graph: "Knowledge graph",
    library: "Source library",
    search: "Search research",
    notes: "Notes & annotations",
    export: "Share & export",
  };

  return (
    <div className={`appShell ${sidebarCollapsed ? "sidebarCollapsed" : ""}`}>
      <Sidebar
        workspaces={workspaces}
        activeWorkspace={activeWorkspace}
        onWorkspaceChange={selectWorkspace}
        activeView={activeView}
        onViewChange={setActiveView}
        trackingState={trackingState}
        collapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebar}
      />
      <main className={`main ${activeView === "graph" ? "mainGraphView" : ""}`}>
        {activeView !== "graph" && <header className="topbar">
          <div className="topbarBrand">
            <span className="topbarLogo"><i/><i/><i/></span>
            <span>MindLoom</span>
          </div>
          <label className="quickSearch">
            <Icon name="search" size={16} />
            <span className="srOnly">Search pages</span>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search this workspace…"
            />
            <kbd>⌘ K</kbd>
          </label>
          <div className="topActions">
            <button
              className="themeButton"
              onClick={() => setTheme((value) => (value === "light" ? "dark" : "light"))}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
              title={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
            >
              <svg aria-hidden="true" viewBox="0 0 24 24">
                {theme === "light" ? (
                  <><path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.8 6.8 0 0 0 9.8 9.8Z" /></>
                ) : (
                  <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>
                )}
              </svg>
            </button>
            <div className={`trackingBadge state-${trackingState}`}>
              <span />
              {trackingState === "active"
                ? "Collecting"
                : trackingState === "unavailable"
                ? "Extension offline"
                : "Paused"}
            </div>
            <button
              className="primaryButton"
              onClick={trackingState === "active" ? handleStopTracking : handleStartTracking}
              disabled={trackingState === "starting" || trackingState === "stopping"}
            >
              <Icon name={trackingState === "active" ? "pause" : "play"} size={15} />
              {trackingState === "active" ? "Stop" : "Collect tabs"}
            </button>
          </div>
        </header>}

        {loadError && (
          <div className="notice" role="alert">
            Live data is unavailable. Showing local workspace data.{" "}
            <button onClick={() => void refreshWorkspace(activeWorkspace)}>Try again</button>
          </div>
        )}

        {activeView === "graph" ? (
          <GraphView
            activeWorkspace={activeWorkspace}
            onSelectPage={(page) => setSelectedPage(page)}
            onStartTracking={handleStartTracking}
          />
        ) : activeView === "overview" ? (
          <div className="dashboardGrid">
            {/* ─── Top-left: Research graph preview ─── */}
            <section className="panel weavePanel">
              <div className="panelHeader">
                <div>
                  <span className="eyebrow">{activeWorkspace.name}</span>
                  <h2>Research graph</h2>
                </div>
                <button className="textButton" onClick={() => setActiveView("graph")}>
                  Expand <Icon name="arrow" size={15} />
                </button>
              </div>
              <div className="graphContainer">
                <GraphView
                  activeWorkspace={activeWorkspace}
                  onSelectPage={(page) => setSelectedPage(page)}
                  onStartTracking={handleStartTracking}
                  embedded
                />
              </div>
            </section>

            {/* ─── Top-right: Collection log (side-by-side with graph) ─── */}
            <section className="panel collectionLogPanel">
              <CollectionLog
                events={collectionEvents}
                pages={savedPages}
                readyCount={ready}
                processingCount={processing}
                trackingState={trackingState}
                onDismiss={(id) => setCollectionEvents((e) => e.filter((x) => x.eventId !== id))}
                onRetry={handleRetryCapture}
                onClearAll={() => setCollectionEvents([])}
                onStartTracking={handleStartTracking}
                onSelectPage={(page) => setSelectedPage(page)}
              />
            </section>

            {/* ─── Bottom-left: Recent sources ─── */}
            <section className="panel recentPanel">
              <div className="panelHeader">
                <div>
                  <span className="eyebrow">Recent</span>
                  <h2>Sources</h2>
                </div>
                <button className="textButton" onClick={() => setActiveView("library")}>
                  View all <Icon name="arrow" size={15} />
                </button>
              </div>
              <div className="sourceTableWrapper">
                <div className="sourceTable" role="table" aria-label="Recent saved sources">
                  {visiblePages.slice(0, 5).map((p, i) => (
                    <button
                      className="sourceRow"
                      role="row"
                      key={p.id}
                      onClick={() => setSelectedPage(p)}
                    >
                      <span className={`sourceMark mark${i % 4}`}>
                        <Icon name="file" size={14} />
                      </span>
                      <span className="sourceCopy">
                        <strong>{p.title}</strong>
                        <small>
                          {p.sourceDomain} · {timeAgo(p.capturedAt)} ago
                        </small>
                      </span>
                      <span className={`status status-${p.status}`}>
                        {p.status === "captured" ? "Ready" : p.status}
                      </span>
                      <Icon name="arrow" size={14} />
                    </button>
                  ))}
                </div>
              </div>
            </section>

            {/* ─── Bottom-right: Today's focus ─── */}
            <aside className="panel focusPanel">
              <div className="panelHeader">
                <div>
                  <span className="eyebrow">Today</span>
                  <h2>Focus</h2>
                </div>
              </div>
              <div className="focusStat">
                <div className="ring">
                  <span>68%</span>
                </div>
                <div>
                  <strong>Reviewed</strong>
                  <p>9 links remain</p>
                </div>
              </div>
              <div className="taskList">
                <label>
                  <input type="checkbox" defaultChecked />
                  <span>Review transformer cluster</span>
                </label>
                <label>
                  <input type="checkbox" />
                  <span>Add notes to AlphaFold paper</span>
                </label>
                <label>
                  <input type="checkbox" />
                  <span>Resolve 3 suggested links</span>
                </label>
              </div>
              <button className="quietButton">
                <Icon name="plus" size={13} /> Add task
              </button>

              <div style={{ marginTop: 12 }}>
                <div className="panelHeader">
                  <div>
                    <span className="eyebrow">Map</span>
                    <h2>Topics</h2>
                  </div>
                </div>
                <div className="topicList">
                  {topics.map((t) => (
                    <div className="topicRow" key={t.name}>
                      <div>
                        <strong>{t.name}</strong>
                        <span>{t.count} sources</span>
                      </div>
                      <div className="topicTrack">
                        <i className={t.color} style={{ width: `${t.width}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </aside>
          </div>
        ) : activeView === "notes" ? (
          <NotesView workspace={activeWorkspace} />
        ) : activeView === "export" ? (
          <ShareExportView workspace={activeWorkspace} />
        ) : activeView === "library" ? (
          <LibraryView workspace={activeWorkspace} />
        ) : activeView === "search" ? (
          <SearchView workspace={activeWorkspace} />
        ) : (
          <section className="futureView">
            <div className="futureIcon">
              <Icon name={activeView === "search" ? "search" : "file"} size={26} />
            </div>
            <span className="eyebrow">Foundation preview</span>
            <h2>{viewTitle[activeView]}</h2>
            <p>
              This shell is ready for the {activeView} workflow. Its live data contract and detailed interactions
              can be connected without redesigning the navigation or page structure.
            </p>
            <button className="primaryButton" onClick={() => setActiveView("overview")}>
              Back to overview
            </button>
          </section>
        )}

        <PageDrawer page={selectedPage} onClose={() => setSelectedPage(null)} />
      </main>
    </div>
  );
}
