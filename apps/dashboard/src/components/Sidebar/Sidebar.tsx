import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Workspace } from "../../types";
import styles from "./Sidebar.module.css";

export type AppView = "overview" | "graph" | "library" | "search" | "notes" | "export";
interface Props { workspaces: Workspace[]; activeWorkspace: Workspace; onWorkspaceChange: (workspace: Workspace) => void; activeView: AppView; onViewChange: (view: AppView) => void; }
const items: { view: AppView; label: string; icon: ReactNode }[] = [
  { view: "overview", label: "Overview", icon: <><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></> },
  { view: "graph", label: "Knowledge graph", icon: <><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="17" r="2.5"/><path d="m8 8 8 7M18 6l-5 4"/><circle cx="18" cy="5" r="2"/></> },
  { view: "library", label: "Source library", icon: <><path d="M5 4h14v16H5z"/><path d="M9 4v16M12 8h4M12 12h4"/></> },
  { view: "search", label: "Search", icon: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></> },
  { view: "notes", label: "Notes", icon: <><path d="M5 3h14v18H5z"/><path d="M9 8h6M9 12h6M9 16h4"/></> },
  { view: "export", label: "Share & export", icon: <><path d="M12 15V3M8 7l4-4 4 4"/><path d="M5 12v8h14v-8"/></> },
];
export function Sidebar({ workspaces, activeWorkspace, onWorkspaceChange, activeView, onViewChange }: Props) {
  const [open, setOpen] = useState(false); const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); }; document.addEventListener("mousedown", close); return () => document.removeEventListener("mousedown", close); }, []);
  return <aside className={styles.sidebar}>
    <div className={styles.brand}><span className={styles.logo}><i/><i/><i/></span><span>Mindloom</span></div>
    <div className={styles.workspace} ref={ref}><span className={styles.sectionLabel}>Current workspace</span><button className={styles.workspaceButton} onClick={() => setOpen(!open)} aria-expanded={open}><span className={styles.workspaceGlyph}>ML</span><span><strong>{activeWorkspace.name}</strong><small>{workspaces.length} workspaces</small></span><svg viewBox="0 0 16 16"><path d="m4 6 4 4 4-4"/></svg></button>{open && <div className={styles.menu}>{workspaces.map((ws) => <button key={ws.id} onClick={() => { onWorkspaceChange(ws); setOpen(false); }} aria-current={ws.id === activeWorkspace.id}>{ws.name}</button>)}</div>}</div>
    <nav className={styles.nav} aria-label="Workspace navigation"><span className={styles.sectionLabel}>Explore</span>{items.slice(0,4).map((item) => <button key={item.view} className={activeView === item.view ? styles.active : ""} onClick={() => onViewChange(item.view)} aria-current={activeView === item.view ? "page" : undefined}><svg viewBox="0 0 24 24">{item.icon}</svg>{item.label}{item.view === "graph" && <span className={styles.badge}>8</span>}</button>)}<span className={styles.sectionLabel}>Work with</span>{items.slice(4).map((item) => <button key={item.view} className={activeView === item.view ? styles.active : ""} onClick={() => onViewChange(item.view)} aria-current={activeView === item.view ? "page" : undefined}><svg viewBox="0 0 24 24">{item.icon}</svg>{item.label}</button>)}</nav>
    <div className={styles.captureCard}><span>Browser collector</span><strong>Ready when you are</strong><p>Capture eligible tabs into this workspace.</p><div><i/> Extension connected</div></div>
    <footer><span className={styles.avatar}>N</span><span><strong>Noushad</strong><small>Frontend lead</small></span><button aria-label="Open settings">•••</button></footer>
  </aside>;
}
