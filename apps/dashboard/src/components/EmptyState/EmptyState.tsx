import styles from "./EmptyState.module.css";

interface EmptyStateProps {
  onStartTracking: () => void;
}

export function EmptyState({ onStartTracking }: EmptyStateProps) {
  return (
    <div className={styles.emptyState}>
      {/* Simple line-art book illustration */}
      <svg
        className={styles.illustration}
        viewBox="0 0 120 120"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {/* Open book */}
        <path d="M60 30 C60 30 40 28 20 35 L20 90 C40 83 60 85 60 85 C60 85 80 83 100 90 L100 35 C80 28 60 30 60 30Z" />
        {/* Center spine */}
        <line x1="60" y1="30" x2="60" y2="85" />
        {/* Left page lines */}
        <line x1="30" y1="45" x2="52" y2="42" opacity="0.4" />
        <line x1="30" y1="53" x2="52" y2="50" opacity="0.4" />
        <line x1="30" y1="61" x2="52" y2="58" opacity="0.4" />
        <line x1="30" y1="69" x2="45" y2="67" opacity="0.4" />
        {/* Right page lines */}
        <line x1="68" y1="42" x2="90" y2="45" opacity="0.4" />
        <line x1="68" y1="50" x2="90" y2="53" opacity="0.4" />
        <line x1="68" y1="58" x2="90" y2="61" opacity="0.4" />
        <line x1="68" y1="67" x2="83" y2="69" opacity="0.4" />
      </svg>

      <h2 className={styles.heading}>No pages collected yet</h2>
      <p className={styles.subtext}>
        Start tracking to capture pages from your browser as you research.
        Pages you visit will appear here with their status.
      </p>
      <button className={styles.ctaBtn} onClick={onStartTracking}>
        Start Tracking
      </button>
    </div>
  );
}
