import { useState, useCallback, useRef, useEffect } from "react";
import type { TrackingState, Workspace, SavedPage, CollectionEvent } from "./types";
import {
  FIXTURE_WORKSPACES,
  FIXTURE_SAVED_PAGES,
  FIXTURE_COLLECTION_EVENTS,
} from "./fixtures";
import { Sidebar } from "./components/Sidebar/Sidebar";
import { TrackingHeader } from "./components/TrackingHeader/TrackingHeader";
import { PageCard } from "./components/PageCard/PageCard";
import { CollectionLog } from "./components/CollectionLog/CollectionLog";
import { EmptyState } from "./components/EmptyState/EmptyState";
import "./App.css";

type DemoMode = "empty" | "active" | "unavailable";

/**
 * Mock extension interaction.
 * In production this would use chrome.runtime.sendMessage or
 * a MessagePort to the extension's service worker.
 */
function useMockExtension() {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const simulateStart = useCallback(
    (
      onStarting: () => void,
      onSuccess: () => void,
      onFail: () => void,
      shouldFail = false
    ) => {
      onStarting();
      timeoutRef.current = setTimeout(
        () => {
          if (shouldFail) {
            onFail();
          } else {
            onSuccess();
          }
        },
        shouldFail ? 5000 : 1500
      );
    },
    []
  );

  const simulateStop = useCallback(
    (onStopping: () => void, onStopped: () => void) => {
      onStopping();
      timeoutRef.current = setTimeout(onStopped, 800);
    },
    []
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return { simulateStart, simulateStop };
}

export default function App() {
  // ─── State ───────────────────────────────────────────────
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace>(
    FIXTURE_WORKSPACES[0]
  );
  const [trackingState, setTrackingState] = useState<TrackingState>("paused");
  const [savedPages, setSavedPages] = useState<SavedPage[]>([]);
  const [collectionEvents, setCollectionEvents] = useState<CollectionEvent[]>([]);
  const [demoMode, setDemoMode] = useState<DemoMode>("active");

  const { simulateStart, simulateStop } = useMockExtension();

  // ─── Demo mode switching ─────────────────────────────────
  const applyDemoMode = useCallback(
    (mode: DemoMode) => {
      setDemoMode(mode);
      switch (mode) {
        case "empty":
          setSavedPages([]);
          setCollectionEvents([]);
          setTrackingState("paused");
          break;
        case "active":
          setSavedPages(FIXTURE_SAVED_PAGES);
          setCollectionEvents(FIXTURE_COLLECTION_EVENTS);
          setTrackingState("active");
          break;
        case "unavailable":
          setSavedPages(FIXTURE_SAVED_PAGES);
          setCollectionEvents(FIXTURE_COLLECTION_EVENTS);
          setTrackingState("unavailable");
          break;
      }
    },
    []
  );

  // Initialize with active demo
  useEffect(() => {
    applyDemoMode("active");
  }, [applyDemoMode]);

  // ─── Tracking handlers ───────────────────────────────────
  const handleStartTracking = useCallback(() => {
    const shouldFail = demoMode === "unavailable";
    simulateStart(
      () => setTrackingState("starting"),
      () => {
        setTrackingState("active");
        // If starting from empty, load fixture data
        if (savedPages.length === 0) {
          setSavedPages(FIXTURE_SAVED_PAGES);
          setCollectionEvents(FIXTURE_COLLECTION_EVENTS);
        }
      },
      () => setTrackingState("unavailable"),
      shouldFail
    );
  }, [simulateStart, demoMode, savedPages.length]);

  const handleStopTracking = useCallback(() => {
    simulateStop(
      () => setTrackingState("stopping"),
      () => setTrackingState("paused")
    );
  }, [simulateStop]);

  const handleRetry = useCallback(() => {
    simulateStart(
      () => setTrackingState("starting"),
      () => setTrackingState("active"),
      () => setTrackingState("unavailable"),
      false // retry succeeds
    );
  }, [simulateStart]);

  // ─── Collection log handlers ─────────────────────────────
  const handleDismissEvent = useCallback((eventId: string) => {
    setCollectionEvents((prev) => prev.filter((e) => e.eventId !== eventId));
  }, []);

  const handleRetryEvent = useCallback((eventId: string) => {
    // In production: re-attempt capture via extension messaging
    // For demo: just remove it
    setCollectionEvents((prev) => prev.filter((e) => e.eventId !== eventId));
  }, []);

  const handleClearAllEvents = useCallback(() => {
    setCollectionEvents([]);
  }, []);

  // ─── Derived state ──────────────────────────────────────
  const isEmpty = savedPages.length === 0 && collectionEvents.length === 0;

  return (
    <div className="layout">
      <Sidebar
        workspaces={FIXTURE_WORKSPACES}
        activeWorkspace={activeWorkspace}
        onWorkspaceChange={setActiveWorkspace}
      />

      <main className="main">
        <TrackingHeader
          workspaceName={activeWorkspace.name}
          trackingState={trackingState}
          onStartTracking={handleStartTracking}
          onStopTracking={handleStopTracking}
          onRetry={handleRetry}
          savedPages={savedPages}
          collectionEvents={collectionEvents}
        />

        {isEmpty ? (
          <EmptyState onStartTracking={handleStartTracking} />
        ) : (
          <>
            {/* Section A — Saved Pages */}
            {savedPages.length > 0 && (
              <section className="section">
                <h2 className="sectionHeader">Saved Pages</h2>
                <div className="pageList">
                  {savedPages.map((page) => (
                    <PageCard key={page.id} page={page} />
                  ))}
                </div>
              </section>
            )}

            {/* Section B — Collection Log */}
            <CollectionLog
              events={collectionEvents}
              onDismiss={handleDismissEvent}
              onRetry={handleRetryEvent}
              onClearAll={handleClearAllEvents}
            />
          </>
        )}
      </main>

      {/* Temporary demo toolbar — remove before integration */}
      <div className="demoBar">
        <span className="demoLabel">Demo</span>
        {(["empty", "active", "unavailable"] as DemoMode[]).map((mode) => (
          <button
            key={mode}
            className={`demoBtn ${demoMode === mode ? "demoBtnActive" : ""}`}
            onClick={() => applyDemoMode(mode)}
          >
            {mode === "empty"
              ? "Empty State"
              : mode === "active"
                ? "With Pages"
                : "Ext. Unavailable"}
          </button>
        ))}
      </div>
    </div>
  );
}
