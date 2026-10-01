import { useState, useRef, useEffect } from "react";
import type { Workspace } from "../../types";
import styles from "./Sidebar.module.css";

interface SidebarProps {
  workspaces: Workspace[];
  activeWorkspace: Workspace;
  onWorkspaceChange: (ws: Workspace) => void;
}

export function Sidebar({
  workspaces,
  activeWorkspace,
  onWorkspaceChange,
}: SidebarProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <aside className={styles.sidebar}>
      {/* Brand */}
      <div className={styles.brand}>
        <svg
          className={styles.brandIcon}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 3c-1.2 2-3 4-5 5 1 4 2.5 8 5 13 2.5-5 4-9 5-13-2-1-3.8-3-5-5z" />
          <path d="M12 8c0 3 0 6 0 9" />
        </svg>
        <span className={styles.brandName}>Mindloom</span>
      </div>

      {/* Workspace selector */}
      <div className={styles.workspaceSelector} ref={dropdownRef}>
        <button
          className={styles.workspaceTrigger}
          onClick={() => setDropdownOpen(!dropdownOpen)}
          aria-expanded={dropdownOpen}
          aria-haspopup="listbox"
        >
          <span>{activeWorkspace.name}</span>
          <svg viewBox="0 0 16 16" fill="currentColor">
            <path d="M4.5 6L8 9.5L11.5 6" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <span className={styles.workspaceCount}>
          {workspaces.length} workspace{workspaces.length !== 1 ? "s" : ""}
        </span>
        {dropdownOpen && (
          <div className={styles.workspaceDropdown} role="listbox">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                role="option"
                aria-selected={ws.id === activeWorkspace.id}
                className={`${styles.workspaceOption} ${ws.id === activeWorkspace.id ? styles.workspaceOptionActive : ""}`}
                onClick={() => {
                  onWorkspaceChange(ws);
                  setDropdownOpen(false);
                }}
              >
                {ws.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className={styles.nav}>
        <button className={`${styles.navItem} ${styles.navItemActive}`}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          Collection
        </button>
        <button className={styles.navItem}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="6" cy="6" r="3" />
            <circle cx="18" cy="18" r="3" />
            <path d="M8.5 8.5L15.5 15.5" />
          </svg>
          Graph View
        </button>
        <button className={styles.navItem}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          Search
        </button>
        <button className={styles.navItem}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          Export
        </button>
      </nav>

      {/* Footer */}
      <div className={styles.footer}>
        <div className={styles.avatar}>N</div>
        <button className={styles.settingsBtn} aria-label="Settings">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
          </svg>
        </button>
      </div>
    </aside>
  );
}
