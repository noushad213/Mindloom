import { useEffect, useRef, useState, type ReactNode } from "react";
import type { TrackingState, Workspace } from "../../types";
import styles from "./Sidebar.module.css";

export type AppView = "overview" | "graph" | "library" | "search" | "notes" | "export";

interface Props {
  workspaces: Workspace[];
  activeWorkspace: Workspace;
  onWorkspaceChange: (workspace: Workspace) => void;
  activeView: AppView;
  onViewChange: (view: AppView) => void;
  trackingState: TrackingState;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

const items: { view: AppView; label: string; icon: ReactNode }[] = [
  {
    view: "overview",
    label: "Overview",
    icon: (
      <>
        <rect x="3" y="3" width="7" height="7" />
        <rect x="14" y="3" width="7" height="7" />
        <rect x="3" y="14" width="7" height="7" />
        <rect x="14" y="14" width="7" height="7" />
      </>
    ),
  },
  {
    view: "graph",
    label: "Knowledge graph",
    icon: (
      <>
        <circle cx="6" cy="6" r="2.5" />
        <circle cx="18" cy="17" r="2.5" />
        <path d="m8 8 8 7M18 6l-5 4" />
        <circle cx="18" cy="5" r="2" />
      </>
    ),
  },
  {
    view: "library",
    label: "Source library",
    icon: (
      <>
        <path d="M5 4h14v16H5z" />
        <path d="M9 4v16M12 8h4M12 12h4" />
      </>
    ),
  },
  {
    view: "search",
    label: "Search",
    icon: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </>
    ),
  },
  {
    view: "notes",
    label: "Notes",
    icon: (
      <>
        <path d="M5 3h14v18H5z" />
        <path d="M9 8h6M9 12h6M9 16h4" />
      </>
    ),
  },
  {
    view: "export",
    label: "Share & export",
    icon: (
      <>
        <path d="M12 15V3M8 7l4-4 4 4" />
        <path d="M5 12v8h14v-8" />
      </>
    ),
  },
];

export function Sidebar({
  workspaces,
  activeWorkspace,
  onWorkspaceChange,
  activeView,
  onViewChange,
  trackingState,
  collapsed = false,
  onToggleCollapse,
}: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const collectorStatus: Record<TrackingState, { title: string; description: string; connection: string }> = {
    paused: { title: "Collection paused", description: "Start collecting to save eligible tabs here.", connection: "Not connected" },
    starting: { title: "Connecting…", description: "Starting the browser collector.", connection: "Connecting" },
    active: { title: "Collecting tabs", description: "Eligible tabs are being saved to this workspace.", connection: "Connected" },
    stopping: { title: "Stopping…", description: "Finishing the current collection session.", connection: "Disconnecting" },
    unavailable: { title: "Extension unavailable", description: "Check that the Mindloom browser extension is installed.", connection: "Not connected" },
  }[trackingState];

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  return (
    <aside
      className={`${styles.sidebar} ${collapsed ? styles.collapsed : ""}`}
      aria-label="Main application sidebar"
    >
      <div className={styles.sidebarHeader}>
        <div className={styles.brand}>
          <div className={styles.brandMain}>
            <span className={styles.logo}>
              <i />
              <i />
              <i />
            </span>
            {!collapsed && <span className={styles.brandTitle}>Mindloom</span>}
          </div>
          {onToggleCollapse && (
            <button
              className={styles.collapseToggle}
              onClick={onToggleCollapse}
              title={collapsed ? "Expand sidebar" : "Collapse sidebar to icons"}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                {collapsed ? (
                  <path d="M7 4l6 6-6 6" />
                ) : (
                  <path d="M13 16l-6-6 6-6" />
                )}
              </svg>
            </button>
          )}
        </div>

        <div className={styles.workspace} ref={ref}>
          {!collapsed ? (
            <>
              <span className={styles.sectionLabel}>Current workspace</span>
              <button
                className={styles.workspaceButton}
                onClick={() => setOpen(!open)}
                aria-expanded={open}
              >
                <span className={styles.workspaceGlyph}>ML</span>
                <span>
                  <strong>{activeWorkspace.name}</strong>
                  <small>{workspaces.length} workspaces</small>
                </span>
                <svg viewBox="0 0 16 16">
                  <path d="m4 6 4 4 4-4" />
                </svg>
              </button>
            </>
          ) : (
            <button
              className={styles.collapsedWorkspaceBtn}
              onClick={() => setOpen(!open)}
              aria-expanded={open}
              title={`Workspace: ${activeWorkspace.name} (${workspaces.length} workspaces)`}
            >
              ML
            </button>
          )}

          {open && (
            <div className={styles.menu} role="menu">
              <span className={styles.menuHeader}>Workspaces</span>
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  onClick={() => {
                    onWorkspaceChange(ws);
                    setOpen(false);
                  }}
                  aria-current={ws.id === activeWorkspace.id}
                  role="menuitem"
                >
                  {ws.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <nav className={styles.nav} aria-label="Workspace navigation">
        {!collapsed ? (
          <span className={styles.sectionLabel}>Explore</span>
        ) : (
          <div className={styles.navDivider} />
        )}
        {items.slice(0, 4).map((item) => (
          <button
            key={item.view}
            className={activeView === item.view ? styles.active : ""}
            onClick={() => onViewChange(item.view)}
            aria-current={activeView === item.view ? "page" : undefined}
            title={collapsed ? item.label : undefined}
          >
            <svg viewBox="0 0 24 24">{item.icon}</svg>
            {!collapsed && <span className={styles.navLabel}>{item.label}</span>}
          </button>
        ))}

        {!collapsed ? (
          <span className={styles.sectionLabel}>Work with</span>
        ) : (
          <div className={styles.navDivider} />
        )}
        {items.slice(4).map((item) => (
          <button
            key={item.view}
            className={activeView === item.view ? styles.active : ""}
            onClick={() => onViewChange(item.view)}
            aria-current={activeView === item.view ? "page" : undefined}
            title={collapsed ? item.label : undefined}
          >
            <svg viewBox="0 0 24 24">{item.icon}</svg>
            {!collapsed && <span className={styles.navLabel}>{item.label}</span>}
          </button>
        ))}
      </nav>

      {!collapsed && (
        <div className={styles.captureCard}>
          <span>Browser collector</span>
          <strong>{collectorStatus.title}</strong>
          <p>{collectorStatus.description}</p>
          <div>
            <i /> {collectorStatus.connection}
          </div>
        </div>
      )}

      <footer>
        <span
          className={styles.avatar}
          title={collapsed ? "Noushad (Frontend lead)" : undefined}
        >
          N
        </span>
        {!collapsed && (
          <>
            <span>
              <strong>Noushad</strong>
              <small>Frontend lead</small>
            </span>
            <button aria-label="Open settings">•••</button>
          </>
        )}
      </footer>
    </aside>
  );
}
