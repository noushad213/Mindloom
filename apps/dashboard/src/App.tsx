import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ingestExtraction, listPages, getInitialWorkspaces } from "./api";
import { connectToExtension, type ExtensionConnection } from "./extension";
import type { ExtensionExtractionResult } from "./integration";
import type { CollectionEvent, GraphPage, SavedPage, TrackingState, Workspace } from "./types";
import { Sidebar, type AppView } from "./components/Sidebar/Sidebar";
import { CollectionLog } from "./components/CollectionLog/CollectionLog";
import { GraphView } from "./components/GraphView/GraphView";
import { PageDrawer } from "./components/PageDrawer/PageDrawer";
import "./App.css";


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
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [trackingState, setTrackingState] = useState<TrackingState>("paused");
  const [savedPages, setSavedPages] = useState<SavedPage[]>([]);
  const [collectionEvents, setCollectionEvents] = useState<CollectionEvent[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<AppView>("overview");
  const [query, setQuery] = useState("");
  const [selectedPage, setSelectedPage] = useState<GraphPage | SavedPage | null>(null);

  const connectionRef = useRef<ExtensionConnection | null>(null);

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
        const { initial, all } = await getInitialWorkspaces();
        if (cancelled) return;
        setWorkspaces(all);
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
          setCollectionEvents((e) => [failureEvent(result), ...e]);
          continue;
        }
        try {
          const page = await ingestExtraction(activeWorkspace.id, result);
          setSavedPages((pages) => [page, ...pages.filter((p) => p.id !== page.id)]);
        } catch (error) {
          setCollectionEvents((e) => [
            failureEvent(result, error instanceof Error ? error.message : "The API rejected this page."),
            ...e,
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
        activeWorkspace.id,
        () => setTrackingState("active"),
        () => {
          connectionRef.current = null;
          setTrackingState((s) => (s === "stopping" ? "paused" : "unavailable"));
        },
      );
    } catch {
      setTrackingState("unavailable");
    }
  }, [activeWorkspace]);

  const handleStopTracking = useCallback(() => {
    setTrackingState("stopping");
    connectionRef.current?.disconnect();
    connectionRef.current = null;
    setTrackingState("paused");
  }, []);

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
  const errors = collectionEvents.filter((e) => e.status === "failed").length;

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
    <div className="appShell">
      <Sidebar
        workspaces={workspaces}
        activeWorkspace={activeWorkspace}
        onWorkspaceChange={selectWorkspace}
        activeView={activeView}
        onViewChange={setActiveView}
      />
      <main className="main">
        <header className="topbar">
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
        </header>

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
            {/* ─── Graph — full top row ─── */}
            <section className="panel weavePanel">
              <div className="panelHeader">
                <div>
                  <span className="eyebrow">Knowledge canvas</span>
                  <h2>Research graph</h2>
                </div>
                <button className="textButton" onClick={() => setActiveView("graph")}>
                  Open full graph <Icon name="arrow" size={15} />
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

            {/* ─── Bottom-left: captured logs + recent captures ─── */}
            <div className="bottomLeft">
              <section className="panel logCard" aria-label="Collection summary">
                <div className="logIcon">
                  <Icon name="link" size={18} />
                </div>
                <div className="logInfo">
                  <strong>Captured logs</strong>
                  <span>{activeWorkspace.name} workspace</span>
                </div>
                <div className="logStatRow">
                  <div className="logStat tealDot">
                    <strong>{ready || 24}</strong>
                    <span>ready</span>
                  </div>
                  <div className="logStat amberDot">
                    <strong>{processing || 2}</strong>
                    <span>processing</span>
                  </div>
                  {errors > 0 && (
                    <div className="logStat redDot">
                      <strong>{errors}</strong>
                      <span>failed</span>
                    </div>
                  )}
                </div>
              </section>

              <section className="panel recentPanel">
                <div className="panelHeader">
                  <div>
                    <span className="eyebrow">Recent captures</span>
                    <h2>Latest sources</h2>
                  </div>
                  <button className="textButton" onClick={() => setActiveView("library")}>
                    View all <Icon name="arrow" size={15} />
                  </button>
                </div>
                <div className="sourceTable" role="table" aria-label="Recent saved sources">
                  {visiblePages.slice(0, 4).map((p, i) => (
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
              </section>
            </div>

            {/* ─── Bottom-right: Today's focus ─── */}
            <aside className="panel focusPanel">
              <div className="panelHeader">
                <div>
                  <span className="eyebrow">Today's focus</span>
                  <h2>Keep the thread moving</h2>
                </div>
              </div>
              <div className="focusStat">
                <div className="ring">
                  <span>68%</span>
                </div>
                <div>
                  <strong>Workspace reviewed</strong>
                  <p>9 relationships remain before this map is tidy.</p>
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
                    <span className="eyebrow">Topic map</span>
                    <h2>Active topics</h2>
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

            {errors > 0 && (
              <section className="panel logPanel">
                <CollectionLog
                  events={collectionEvents}
                  onDismiss={(id) => setCollectionEvents((e) => e.filter((x) => x.eventId !== id))}
                  onRetry={(id) => setCollectionEvents((e) => e.filter((x) => x.eventId !== id))}
                  onClearAll={() => setCollectionEvents([])}
                />
              </section>
            )}
          </div>
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
