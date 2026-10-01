import { useState } from "react";
import type { CollectionEvent, SavedPage, TrackingState } from "../../types";
import { ERROR_MESSAGES } from "../../fixtures";
import styles from "./CollectionLog.module.css";

export interface CollectionLogProps {
  events: CollectionEvent[];
  pages?: SavedPage[];
  readyCount?: number;
  processingCount?: number;
  trackingState?: TrackingState;
  onDismiss: (eventId: string) => void;
  onRetry: (eventId: string) => void;
  onClearAll: () => void;
  onStartTracking?: () => void;
  onSelectPage?: (page: SavedPage) => void;
}

function formatTimeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function CollectionLog({
  events,
  pages = [],
  readyCount = 0,
  processingCount = 0,
  onDismiss,
  onRetry,
  onClearAll,
  onStartTracking,
  onSelectPage,
}: CollectionLogProps) {
  const failedEvents = events.filter((e) => e.status === "failed");
  const [filter, setFilter] = useState<"all" | "issues" | "captured">("all");

  const totalCount = failedEvents.length + pages.length;

  const showIssues = filter === "all" || filter === "issues";
  const showCaptured = filter === "all" || filter === "captured";

  return (
    <div className={styles.container}>
      {/* ── Header ── */}
      <div className={styles.header}>
        <div>
          <span className={styles.eyebrow}>Live Intake</span>
          <h2 className={styles.title}>Collection log</h2>
        </div>
        <div className={styles.headerActions}>
          {failedEvents.length > 0 && (
            <button
              className={styles.clearBtn}
              onClick={onClearAll}
              title="Clear all failed events"
            >
              Clear issues
            </button>
          )}
        </div>
      </div>

      {/* ── Quick Stat Bar ── */}
      <div className={styles.statBar} role="status" aria-label="Collection intake status">
        <div className={styles.statItem}>
          <span className={`${styles.statDot} ${styles.readyDot}`} />
          <strong>{readyCount ?? pages.filter((p) => ["captured", "ready", "extracted"].includes(p.status)).length}</strong>
          <span>ready</span>
        </div>
        <div className={styles.statItem}>
          <span className={`${styles.statDot} ${styles.processingDot}`} />
          <strong>{processingCount ?? pages.filter((p) => ["processing", "queued", "extracting"].includes(p.status)).length}</strong>
          <span>processing</span>
        </div>
        <div className={`${styles.statItem} ${failedEvents.length > 0 ? styles.statItemError : ""}`}>
          <span
            className={`${styles.statDot} ${
              failedEvents.length > 0 ? styles.errorDot : styles.idleDot
            }`}
          />
          <strong>{failedEvents.length}</strong>
          <span>{failedEvents.length === 1 ? "issue" : "issues"}</span>
        </div>
      </div>

      {/* ── Filter Pills ── */}
      <div className={styles.filterPills} role="tablist" aria-label="Filter collection entries">
        <button
          role="tab"
          aria-selected={filter === "all"}
          className={`${styles.filterPill} ${filter === "all" ? styles.activePill : ""}`}
          onClick={() => setFilter("all")}
        >
          All <span className={styles.countBadge}>{totalCount}</span>
        </button>
        <button
          role="tab"
          aria-selected={filter === "issues"}
          className={`${styles.filterPill} ${filter === "issues" ? styles.activePill : ""}`}
          onClick={() => setFilter("issues")}
        >
          Issues{" "}
          {failedEvents.length > 0 ? (
            <span className={`${styles.countBadge} ${styles.errorBadge}`}>
              {failedEvents.length}
            </span>
          ) : (
            <span className={styles.countBadge}>0</span>
          )}
        </button>
        <button
          role="tab"
          aria-selected={filter === "captured"}
          className={`${styles.filterPill} ${filter === "captured" ? styles.activePill : ""}`}
          onClick={() => setFilter("captured")}
        >
          Captured <span className={styles.countBadge}>{pages.length}</span>
        </button>
      </div>

      {/* ── Log List ── */}
      <div className={styles.logList} role="feed" aria-label="Collection log stream">
        {/* Failed events */}
        {showIssues &&
          failedEvents.map((event) => {
            const errorInfo = event.errorCode
              ? ERROR_MESSAGES[event.errorCode]
              : { text: event.errorDetail ?? "The page could not be collected.", action: "dismiss" as const };

            return (
              <div key={event.eventId} className={styles.issueRow} role="article">
                <div className={styles.issueIconWrapper}>
                  <svg className={styles.warningIcon} viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className={styles.rowContent}>
                  <div className={styles.rowTitle} title={event.title || event.url}>
                    {event.title || event.url}
                  </div>
                  <div className={styles.errorText}>{errorInfo.text}</div>
                  <div className={styles.metaRow}>
                    <span className={styles.timestamp}>{formatTimeAgo(event.timestamp)}</span>
                    <span className={styles.metaDot}>•</span>
                    <span className={styles.codePill}>{event.errorCode || "failed"}</span>
                  </div>
                </div>
                <div className={styles.rowActions}>
                  {errorInfo.action === "retry" && (
                    <button
                      className={`${styles.actionBtn} ${styles.retryBtn}`}
                      onClick={() => onRetry(event.eventId)}
                      title="Retry capture"
                    >
                      Retry
                    </button>
                  )}
                  <button
                    className={`${styles.actionBtn} ${styles.dismissBtn}`}
                    onClick={() => onDismiss(event.eventId)}
                    aria-label={`Dismiss error for ${event.title || event.url}`}
                    title="Dismiss"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            );
          })}

        {/* Captured items */}
        {showCaptured &&
          pages.map((page) => (
            <div
              key={page.id}
              className={styles.capturedRow}
              onClick={() => onSelectPage?.(page)}
              role={onSelectPage ? "button" : undefined}
              tabIndex={onSelectPage ? 0 : undefined}
              onKeyDown={(e) => {
                if (onSelectPage && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  onSelectPage(page);
                }
              }}
            >
              <div className={styles.capturedIconWrapper}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.1 1.1" />
                  <path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.1-1.1" />
                </svg>
              </div>
              <div className={styles.rowContent}>
                <div className={styles.rowTitle} title={page.title}>
                  {page.title}
                </div>
                <div className={styles.metaRow}>
                  <span className={styles.domainText}>{page.sourceDomain}</span>
                  <span className={styles.metaDot}>•</span>
                  <span className={styles.timestamp}>{formatTimeAgo(page.capturedAt)}</span>
                </div>
              </div>
              <div className={styles.capturedStatusWrapper}>
                <span className={`${styles.statusChip} ${styles[`status_${page.status}`] || ""}`}>
                  {page.status === "captured" ? "Ready" : page.status}
                </span>
              </div>
            </div>
          ))}

        {/* Empty state for issues */}
        {filter === "issues" && failedEvents.length === 0 && (
          <div className={styles.emptyState}>
            <div className={styles.emptyIconSuccess}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
            <strong>All capture streams healthy</strong>
            <p>No permission issues or failed page extractions in this workspace.</p>
          </div>
        )}

        {/* Empty state when completely empty */}
        {totalCount === 0 && (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <strong>No collection activity yet</strong>
            <p>Start collecting tabs to stream research pages into this loom in real time.</p>
            {onStartTracking && (
              <button className={styles.emptyActionBtn} onClick={onStartTracking}>
                Collect open tabs
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
