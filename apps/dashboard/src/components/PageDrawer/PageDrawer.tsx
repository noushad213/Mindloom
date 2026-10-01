import { useEffect } from "react";
import type { GraphPage, SavedPage } from "../../types";
import styles from "./PageDrawer.module.css";

interface PageDrawerProps {
  page: GraphPage | SavedPage | null;
  onClose: () => void;
}

export function PageDrawer({ page, onClose }: PageDrawerProps) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!page) return null;

  const statusClass =
    page.status === "ready" || page.status === "captured"
      ? styles.statusReady
      : page.status === "processing" || page.status === "queued"
      ? styles.statusProcessing
      : styles.statusFailed;

  const summary = "summary" in page ? page.summary : null;

  return (
    <div className={styles.backdrop} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.drawer} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div>
            <div className={styles.metaRow}>
              <span className={styles.domainBadge}>{page.sourceDomain}</span>
              <span className={`${styles.statusPill} ${statusClass}`}>{page.status}</span>
            </div>
            <h2 className={styles.title}>{page.title || "Untitled Page"}</h2>
          </div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close details">
            ✕
          </button>
        </div>

        <div className={styles.body}>
          <div className={styles.section}>
            <span className={styles.sectionLabel}>Source URL</span>
            <a
              href={page.canonicalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.urlLink}
            >
              {page.canonicalUrl}
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
            </a>
          </div>

          <div className={styles.section}>
            <span className={styles.sectionLabel}>Captured At</span>
            <p style={{ fontSize: "13px", color: "var(--text-body)" }}>
              {new Date(page.capturedAt).toLocaleString()}
            </p>
          </div>

          <div className={styles.section}>
            <span className={styles.sectionLabel}>Research Summary & Excerpt</span>
            {summary ? (
              <div className={styles.summaryBox}>{summary}</div>
            ) : (
              <p className={styles.emptyHint}>
                No AI summary available yet. Content analysis is queued or pending.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
