import type { TrackingState, SavedPage, CollectionEvent } from "../../types";
import styles from "./TrackingHeader.module.css";

interface TrackingHeaderProps {
  workspaceName: string;
  trackingState: TrackingState;
  onStartTracking: () => void;
  onStopTracking: () => void;
  onRetry: () => void;
  savedPages: SavedPage[];
  collectionEvents: CollectionEvent[];
}

const DOT_CLASS: Record<TrackingState, string> = {
  paused: styles.dotPaused,
  starting: styles.dotStarting,
  active: styles.dotActive,
  stopping: styles.dotStopping,
  unavailable: styles.dotUnavailable,
};

const STATUS_LABEL: Record<TrackingState, string> = {
  paused: "Tracking Paused",
  starting: "Starting\u2026",
  active: "Tracking Active",
  stopping: "Stopping\u2026",
  unavailable: "Extension Unavailable",
};

export function TrackingHeader({
  workspaceName,
  trackingState,
  onStartTracking,
  onStopTracking,
  onRetry,
  savedPages,
  collectionEvents,
}: TrackingHeaderProps) {
  const capturedCount = savedPages.filter((p) => ["captured", "extracted", "ready"].includes(p.status)).length;
  const processingCount = savedPages.filter((p) => p.status === "processing").length;
  const errorCount = collectionEvents.filter((e) => e.status === "failed").length;
  const isTransitioning = trackingState === "starting" || trackingState === "stopping";

  return (
    <div>
      <div className={styles.header}>
        <h1 className={styles.workspaceName}>{workspaceName}</h1>

        <div>
          <div className={styles.trackingControl}>
            <div className={styles.trackingStatus}>
              <span className={`${styles.dot} ${DOT_CLASS[trackingState]}`} />
              <span className={styles.statusLabel}>
                {STATUS_LABEL[trackingState]}
              </span>
            </div>

            {trackingState === "paused" && (
              <button className={styles.trackingBtn} onClick={onStartTracking}>
                Start Tracking
              </button>
            )}
            {trackingState === "active" && (
              <button className={styles.trackingBtn} onClick={onStopTracking}>
                Stop Tracking
              </button>
            )}
            {trackingState === "unavailable" && (
              <button
                className={`${styles.trackingBtn} ${styles.trackingBtnRetry}`}
                onClick={onRetry}
              >
                Retry
              </button>
            )}
            {isTransitioning && (
              <button className={styles.trackingBtn} disabled>
                {trackingState === "starting" ? "Starting\u2026" : "Stopping\u2026"}
              </button>
            )}
          </div>

          {trackingState === "unavailable" && (
            <p className={styles.unavailableHelper}>
              Install or enable the Mindloom extension to start collecting.
            </p>
          )}
        </div>
      </div>

      {/* Status strip — only show when there's data */}
      {(savedPages.length > 0 || collectionEvents.length > 0) && (
        <div className={styles.statusStrip}>
          <span>
            {savedPages.length} page{savedPages.length !== 1 ? "s" : ""} saved
          </span>
          {processingCount > 0 && (
            <>
              <span className={styles.statusDot} />
              <span>{processingCount} processing</span>
            </>
          )}
          {capturedCount > 0 && (
            <>
              <span className={styles.statusDot} />
              <span>{capturedCount} captured</span>
            </>
          )}
          {errorCount > 0 && (
            <>
              <span className={styles.statusDot} />
              <span style={{ color: "var(--status-error-text)" }}>
                {errorCount} error{errorCount !== 1 ? "s" : ""}
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
