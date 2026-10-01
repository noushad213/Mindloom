import type { CollectionEvent } from "../../types";
import { ERROR_MESSAGES } from "../../fixtures";
import styles from "./CollectionLog.module.css";

interface CollectionLogProps {
  events: CollectionEvent[];
  onDismiss: (eventId: string) => void;
  onRetry: (eventId: string) => void;
  onClearAll: () => void;
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
  onDismiss,
  onRetry,
  onClearAll,
}: CollectionLogProps) {
  // Only show failed events (successful ones are promoted to saved pages)
  const failedEvents = events.filter((e) => e.status === "failed");
  if (failedEvents.length === 0) return null;

  return (
    <section>
      <div className={styles.sectionHeader}>
        <h2 className={styles.sectionTitle}>Collection Log</h2>
        <button className={styles.clearBtn} onClick={onClearAll}>
          Clear all
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
        {failedEvents.map((event) => {
          const errorInfo = event.errorCode
            ? ERROR_MESSAGES[event.errorCode]
            : { text: event.errorDetail ?? "Unknown error", action: "dismiss" as const };

          return (
            <div key={event.eventId} className={styles.row}>
              {/* Warning icon */}
              <svg
                className={styles.icon}
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                  clipRule="evenodd"
                />
              </svg>

              {/* Content */}
              <div className={styles.content}>
                <div className={styles.urlLine}>
                  {event.title || event.url}
                </div>
                <div className={styles.errorText}>{errorInfo.text}</div>
              </div>

              {/* Actions */}
              <div className={styles.actions}>
                <span className={styles.timestamp}>
                  {formatTimeAgo(event.timestamp)}
                </span>
                {errorInfo.action === "retry" && (
                  <button
                    className={`${styles.actionBtn} ${styles.retryBtn}`}
                    onClick={() => onRetry(event.eventId)}
                  >
                    Retry
                  </button>
                )}
                <button
                  className={`${styles.actionBtn} ${styles.dismissBtn}`}
                  onClick={() => onDismiss(event.eventId)}
                  aria-label={`Dismiss error for ${event.url}`}
                >
                  Dismiss
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
