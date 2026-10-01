import { useCallback, useEffect, useRef, useState } from "react";
import { ingestExtraction, listPages, listWorkspaces, loadOrCreateWorkspace } from "./api";
import { connectToExtension } from "./extension";
import type { ExtensionConnection } from "./extension";
import type { ExtensionExtractionResult } from "./integration";
import type { CollectionEvent, SavedPage, TrackingState, Workspace } from "./types";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { TrackingHeader } from "./components/TrackingHeader/TrackingHeader";
import { PageCard } from "./components/PageCard/PageCard";
import { CollectionLog } from "./components/CollectionLog/CollectionLog";
import { EmptyState } from "./components/EmptyState/EmptyState";
import "./App.css";

const EXTENSION_ID = import.meta.env.VITE_EXTENSION_ID || "";

function failureEvent(result: ExtensionExtractionResult, detail?: string): CollectionEvent {
  return {
    eventId: crypto.randomUUID(), tabId: result.tabId,
    url: result.url || "Restricted or unavailable tab", title: result.title || null,
    timestamp: new Date().toISOString(), status: "failed", errorCode: "extraction_failed",
    errorDetail: detail || result.error || "The page could not be collected.",
  };
}

export default function App() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [trackingState, setTrackingState] = useState<TrackingState>("paused");
  const [savedPages, setSavedPages] = useState<SavedPage[]>([]);
  const [collectionEvents, setCollectionEvents] = useState<CollectionEvent[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const connectionRef = useRef<ExtensionConnection | null>(null);

  const refreshWorkspace = useCallback(async (workspace: Workspace) => {
    setLoading(true); setLoadError(null);
    try { setSavedPages(await listPages(workspace.id)); }
    catch (error) { setLoadError(error instanceof Error ? error.message : "Could not load saved pages."); }
    finally { setLoading(false); }
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
    return () => { cancelled = true; connectionRef.current?.disconnect(); };
  }, [refreshWorkspace]);

  const collectResults = useCallback(async (results: ExtensionExtractionResult[]) => {
    if (!activeWorkspace) return;
    for (const result of results) {
      if (!result.success) {
        setCollectionEvents((events) => [failureEvent(result), ...events]);
        continue;
      }
      try {
        const page = await ingestExtraction(activeWorkspace.id, result);
        setSavedPages((pages) => [page, ...pages.filter((item) => item.id !== page.id)]);
      } catch (error) {
        setCollectionEvents((events) => [failureEvent(result, error instanceof Error ? error.message : "The API rejected this page."), ...events]);
      }
    }
  }, [activeWorkspace]);

  const handleStartTracking = useCallback(() => {
    if (!activeWorkspace || connectionRef.current) return;
    setTrackingState("starting");
    try {
      connectionRef.current = connectToExtension(
        EXTENSION_ID, (results) => void collectResults(results),
        () => setTrackingState("active"),
        () => {
          connectionRef.current = null;
          setTrackingState((state) => state === "stopping" ? "paused" : "unavailable");
        },
      );
    } catch { setTrackingState("unavailable"); }
  }, [activeWorkspace, collectResults]);

  const handleStopTracking = useCallback(() => {
    setTrackingState("stopping"); connectionRef.current?.disconnect();
    connectionRef.current = null; setTrackingState("paused");
  }, []);

  const selectWorkspace = useCallback((workspace: Workspace) => {
    setActiveWorkspace(workspace); void refreshWorkspace(workspace);
  }, [refreshWorkspace]);
  const dismissEvent = useCallback((eventId: string) => {
    setCollectionEvents((events) => events.filter((event) => event.eventId !== eventId));
  }, []);

  if (!activeWorkspace) {
    return <main className="startupState" aria-busy={loading}>
      <h1>Mindloom</h1>
      <p role={loadError ? "alert" : "status"}>{loadError || "Connecting to your research workspace…"}</p>
      {loadError && <button onClick={() => window.location.reload()}>Retry connection</button>}
    </main>;
  }

  const isEmpty = !loading && savedPages.length === 0 && collectionEvents.length === 0;
  return <div className="layout">
    <Sidebar workspaces={workspaces} activeWorkspace={activeWorkspace} onWorkspaceChange={selectWorkspace} />
    <main className="main">
      <TrackingHeader workspaceName={activeWorkspace.name} trackingState={trackingState}
        onStartTracking={handleStartTracking} onStopTracking={handleStopTracking} onRetry={handleStartTracking}
        savedPages={savedPages} collectionEvents={collectionEvents} />
      {loadError && <p className="integrationNotice" role="alert">{loadError}</p>}
      {loading ? <p className="integrationNotice" role="status">Loading saved research…</p> : isEmpty ?
        <EmptyState onStartTracking={handleStartTracking} /> : <>
          {savedPages.length > 0 && <section className="section">
            <h2 className="sectionHeader">Saved Pages</h2>
            <div className="pageList">{savedPages.map((page) => <PageCard key={page.id} page={page} />)}</div>
          </section>}
          <CollectionLog events={collectionEvents} onDismiss={dismissEvent} onRetry={dismissEvent}
            onClearAll={() => setCollectionEvents([])} />
        </>}
    </main>
  </div>;
}
