import type { SavedPage } from "../../types";
import styles from "./PageCard.module.css";

interface PageCardProps {
  page: SavedPage;
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

const PILL_CLASS: Record<string, string> = {
  captured: styles.pillCaptured,
  ready: styles.pillCaptured,
  extracted: styles.pillCaptured,
  processing: styles.pillProcessing,
  queued: styles.pillQueued,
  discovered: styles.pillQueued,
  extracting: styles.pillQueued,
  extraction_failed: styles.pillQueued,
  processing_failed: styles.pillQueued,
};

const PILL_LABEL: Record<string, string> = {
  captured: "Captured",
  ready: "Ready",
  extracted: "Extracted",
  processing: "Processing\u2026",
  queued: "Queued",
  discovered: "Discovered",
  extracting: "Extracting\u2026",
  extraction_failed: "Extraction failed",
  processing_failed: "Processing failed",
};

export function PageCard({ page }: PageCardProps) {
  const firstLetter = page.sourceDomain.charAt(0).toUpperCase();
  const faviconUrl = `https://www.google.com/s2/favicons?domain=${page.sourceDomain}&sz=32`;

  return (
    <article className={styles.card} tabIndex={0} role="button" aria-label={`View ${page.title}`}>
      {/* Favicon */}
      <div className={styles.favicon}>
        <img
          className={styles.faviconImg}
          src={faviconUrl}
          alt=""
          loading="lazy"
          onError={(e) => {
            // Replace broken favicon with initial letter
            const target = e.currentTarget;
            target.style.display = "none";
            const fallback = target.parentElement?.querySelector(
              `.${styles.faviconFallback}`
            ) as HTMLElement | null;
            if (fallback) fallback.style.display = "flex";
          }}
        />
        <span className={styles.faviconFallback} style={{ display: "none" }}>
          {firstLetter}
        </span>
      </div>

      {/* Content */}
      <div className={styles.content}>
        <div className={styles.domain}>{page.sourceDomain}</div>
        <div className={styles.title}>{page.title}</div>
        <div className={styles.url}>{page.canonicalUrl.replace(/^https?:\/\//, "")}</div>
      </div>

      {/* Meta */}
      <div className={styles.meta}>
        <span className={`${styles.pill} ${PILL_CLASS[page.status]}`}>
          {["captured", "ready", "extracted"].includes(page.status) && (
            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
              <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
            </svg>
          )}
          {page.status === "processing" && <span className={styles.spinner} />}
          {["queued", "discovered", "extracting", "extraction_failed", "processing_failed"].includes(page.status) && (
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="8" cy="8" r="6" />
              <path d="M8 4.5V8L10.5 9.5" strokeLinecap="round" />
            </svg>
          )}
          {PILL_LABEL[page.status]}
        </span>
        <span className={styles.timestamp}>{formatTimeAgo(page.capturedAt)}</span>
      </div>
    </article>
  );
}
