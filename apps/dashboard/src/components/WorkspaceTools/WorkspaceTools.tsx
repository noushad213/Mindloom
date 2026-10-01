import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import type { Workspace } from "../../types";
import styles from "./WorkspaceTools.module.css";

type NoteKind = "Highlight" | "Thought" | "Question";

interface ResearchNote {
  id: string;
  title: string;
  body: string;
  kind: NoteKind;
  source: string;
  domain: string;
  date: string;
  tags: string[];
}

const initialNotes: ResearchNote[] = [
  {
    id: "note-1",
    title: "Attention makes the sequence parallel",
    body: "The useful shift is not just a different layer: attention lets us compare every token directly, so training no longer has to wait for a recurrent pass. That is the architectural idea to carry into the systems notes.",
    kind: "Highlight",
    source: "Attention Is All You Need",
    domain: "arxiv.org",
    date: "Today · 10:42 AM",
    tags: ["transformers", "architecture"],
  },
  {
    id: "note-2",
    title: "What counts as a reliable structure?",
    body: "The confidence story is as important as the predicted structure. Look for where the paper separates local confidence from uncertainty between domains before comparing it with later benchmarks.",
    kind: "Question",
    source: "Highly accurate protein structure prediction with AlphaFold",
    domain: "nature.com",
    date: "Today · 9:18 AM",
    tags: ["evaluation", "follow-up"],
  },
  {
    id: "note-3",
    title: "Keep the capture boundary explicit",
    body: "A browser workspace should make the moment of collection visible. The saved page is durable research; an open tab is only a temporary browser state.",
    kind: "Thought",
    source: "Weft — Visual Browser Tab Manager",
    domain: "github.com",
    date: "Yesterday · 4:06 PM",
    tags: ["product principle", "local-first"],
  },
  {
    id: "note-4",
    title: "Separate the model from the mental model",
    body: "A generated connection is a prompt for inspection, not a fact. Keep the supporting evidence close to the suggestion and make manual corrections survive future runs.",
    kind: "Thought",
    source: "Sensemaking in the Age of AI",
    domain: "dl.acm.org",
    date: "Yesterday · 2:31 PM",
    tags: ["trust", "research workflow"],
  },
];

const filters = ["All notes", "Highlights", "Thoughts", "Questions"] as const;

interface LibrarySource {
  id: string;
  title: string;
  domain: string;
  date: string;
  kind: "Paper" | "Repository";
  status: "Ready" | "Processing";
  tags: string[];
  summary: string;
}

const librarySources: LibrarySource[] = [
  { id: "source-1", title: "Attention Is All You Need", domain: "arxiv.org", date: "Today · 10:41 AM", kind: "Paper", status: "Ready", tags: ["transformers", "architecture"], summary: "Introduces the Transformer, an architecture based entirely on attention mechanisms that replaces recurrence and enables more parallel training." },
  { id: "source-2", title: "Highly accurate protein structure prediction with AlphaFold", domain: "nature.com", date: "Today · 9:26 AM", kind: "Paper", status: "Processing", tags: ["protein folding", "evaluation"], summary: "Describes a deep-learning system for predicting protein structures, with confidence estimates that help distinguish reliable regions." },
  { id: "source-3", title: "Weft — Visual Browser Tab Manager", domain: "github.com", date: "Yesterday · 4:02 PM", kind: "Repository", status: "Ready", tags: ["local-first", "knowledge graph"], summary: "A reference project exploring browser-tab capture, local-first organization, and connected research browsing." },
  { id: "source-4", title: "Sensemaking in the Age of AI", domain: "dl.acm.org", date: "Yesterday · 2:28 PM", kind: "Paper", status: "Ready", tags: ["human-AI interaction", "sensemaking"], summary: "Examines how people form mental models while working with AI systems and where interface explanations help or hinder understanding." },
];

interface SearchResult {
  id: string;
  type: "Source" | "Note";
  title: string;
  location: string;
  body: string;
  tags: string[];
}

const searchItems: SearchResult[] = [
  { id: "result-1", type: "Source", title: "Attention Is All You Need", location: "arxiv.org · Research paper", body: "The Transformer relies entirely on attention mechanisms, allowing parallel computation across the input sequence.", tags: ["transformers", "architecture"] },
  { id: "result-2", type: "Note", title: "Attention makes the sequence parallel", location: "Note on Attention Is All You Need", body: "Attention lets us compare every token directly, so training no longer has to wait for a recurrent pass.", tags: ["transformers", "highlight"] },
  { id: "result-3", type: "Note", title: "Keep the capture boundary explicit", location: "Note on Weft — Visual Browser Tab Manager", body: "The saved page is durable research; an open tab is only a temporary browser state.", tags: ["product principle", "local-first"] },
  { id: "result-4", type: "Source", title: "Sensemaking in the Age of AI", location: "dl.acm.org · Research paper", body: "A study of how people build mental models and make sense of AI-supported work.", tags: ["human-AI interaction", "sensemaking"] },
];

function ToolIcon({ name, size = 16 }: { name: "plus" | "copy" | "download"; size?: number }) {
  const paths = {
    plus: <path d="M12 5v14M5 12h14" />,
    copy: <><rect x="8" y="8" width="12" height="12" rx="2" /><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" /></>,
    download: <><path d="M12 3v12m-5-5 5 5 5-5" /><path d="M5 19h14" /></>,
  };

  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  );
}

function PageHeading({ workspace, eyebrow, title, description, action }: {
  workspace: Workspace;
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className={styles.pageHeading}>
      <div>
        <div className={styles.breadcrumb}><span>{workspace.name}</span><i />{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </header>
  );
}

export function NotesView({ workspace }: { workspace: Workspace }) {
  const [notes, setNotes] = useState(initialNotes);
  const [activeId, setActiveId] = useState(initialNotes[0].id);
  const [filter, setFilter] = useState<(typeof filters)[number]>("All notes");
  const [query, setQuery] = useState("");
  const [draftOpen, setDraftOpen] = useState(false);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftBody, setDraftBody] = useState("");

  const visibleNotes = useMemo(() => notes.filter((note) => {
    const matchesFilter = filter === "All notes" || `${note.kind}s` === filter;
    const matchesQuery = `${note.title} ${note.source} ${note.tags.join(" ")}`.toLowerCase().includes(query.toLowerCase());
    return matchesFilter && matchesQuery;
  }), [filter, notes, query]);
  const activeNote = visibleNotes.find((note) => note.id === activeId) ?? visibleNotes[0];

  function saveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const note: ResearchNote = {
      id: `note-${Date.now()}`,
      title: draftTitle.trim(),
      body: draftBody.trim(),
      kind: "Thought",
      source: "Attention Is All You Need",
      domain: "arxiv.org",
      date: "Just now",
      tags: ["draft"],
    };
    setNotes((current) => [note, ...current]);
    setFilter("All notes");
    setQuery("");
    setActiveId(note.id);
    setDraftOpen(false);
    setDraftTitle("");
    setDraftBody("");
  }

  return (
    <div className={`${styles.workspaceView} ${styles.notesView}`}>
      <PageHeading
        workspace={workspace}
        eyebrow="Notes"
        title="Notes & annotations"
        description="Your thinking, kept alongside the sources that sparked it."
        action={<button className={styles.primaryAction} onClick={() => setDraftOpen(true)}><ToolIcon name="plus" />New note</button>}
      />

      <div className={styles.noteStats} aria-label="Workspace note summary">
        <div><strong>{notes.length}</strong><span>notes</span></div>
        <i />
        <div><strong>4</strong><span>linked sources</span></div>
        <i />
        <div><strong>{notes.filter((note) => note.kind === "Highlight").length}</strong><span>highlights</span></div>
        <span className={styles.sampleFlag}>Sample data</span>
      </div>

      <div className={styles.notesWorkbench}>
        <aside className={styles.noteRail} aria-label="Notes list">
          <label className={styles.noteSearch}>
            <span className={styles.srOnly}>Search notes</span>
            <svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a note…" />
          </label>
          <div className={styles.noteFilters} aria-label="Filter notes">
            {filters.map((item) => (
              <button key={item} className={filter === item ? styles.filterActive : ""} onClick={() => setFilter(item)} aria-pressed={filter === item}>
                {item}<span>{item === "All notes" ? notes.length : item === "Highlights" ? notes.filter((note) => note.kind === "Highlight").length : item === "Questions" ? notes.filter((note) => note.kind === "Question").length : notes.filter((note) => note.kind === "Thought").length}</span>
              </button>
            ))}
          </div>
          <div className={styles.noteList}>
            <span className={styles.listLabel}>RECENTLY EDITED</span>
            {visibleNotes.map((note) => (
              <button key={note.id} className={`${styles.noteListItem} ${activeNote?.id === note.id ? styles.noteSelected : ""}`} onClick={() => setActiveId(note.id)} aria-current={activeNote?.id === note.id ? "true" : undefined}>
                <span className={`${styles.noteKind} ${styles[`kind${note.kind}`]}`}>{note.kind}</span>
                <strong>{note.title}</strong>
                <span className={styles.noteListMeta}>{note.source} <i /> {note.date.split("·")[0].trim()}</span>
              </button>
            ))}
            {visibleNotes.length === 0 && <p className={styles.noResults}>No notes match this search.</p>}
          </div>
        </aside>

        <article className={styles.noteDetail}>
          {draftOpen ? (
            <form className={styles.noteComposer} onSubmit={saveDraft}>
              <span className={styles.detailKicker}>NEW THOUGHT · SAMPLE WORKSPACE</span>
              <label>Note title<input autoFocus required maxLength={90} value={draftTitle} onChange={(event) => setDraftTitle(event.target.value)} placeholder="What do you want to remember?" /></label>
              <label>Your note<textarea required rows={7} value={draftBody} onChange={(event) => setDraftBody(event.target.value)} placeholder="Write a thought connected to your research…" /></label>
              <div className={styles.composerActions}><span>Linked to Attention Is All You Need</span><button type="button" className={styles.subtleAction} onClick={() => setDraftOpen(false)}>Cancel</button><button className={styles.primaryAction} type="submit">Save note</button></div>
            </form>
          ) : activeNote ? (
            <>
              <div className={styles.detailTopline}><span className={`${styles.noteKind} ${styles[`kind${activeNote.kind}`]}`}>{activeNote.kind}</span><span>Edited {activeNote.date}</span><button className={styles.detailMore} aria-label="More note actions" title="More note actions">···</button></div>
              <h2>{activeNote.title}</h2>
              <a className={styles.sourceLink} href="#source-preview" onClick={(event) => event.preventDefault()}>
                <span className={styles.sourceGlyph}>{activeNote.domain.slice(0, 1).toUpperCase()}</span>
                <span><strong>{activeNote.source}</strong><small>{activeNote.domain}</small></span>
                <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" /></svg>
              </a>
              <div className={styles.noteBody}><p>{activeNote.body}</p></div>
              <div className={styles.noteDetailFooter}>
                <div className={styles.noteTags}>{activeNote.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
                <span className={styles.savedIndicator}><i />Saved in {workspace.name}</span>
              </div>
            </>
          ) : (
            <div className={styles.emptyNotes}><strong>No notes here yet</strong><span>Try another filter or start a new note.</span></div>
          )}
        </article>
      </div>
    </div>
  );
}

type ExportFormat = "Markdown" | "JSON";

export function ShareExportView({ workspace }: { workspace: Workspace }) {
  const [access, setAccess] = useState<"private" | "link">("link");
  const [format, setFormat] = useState<ExportFormat>("Markdown");
  const [include, setInclude] = useState({ sources: true, notes: true, connections: true });
  const [feedback, setFeedback] = useState("");

  async function copyPreviewLink() {
    const url = `https://mindloom.app/share/${workspace.id}/preview`;
    let copied = false;
    try {
      await navigator.clipboard.writeText(url);
      copied = true;
    } catch {
      // The preview remains usable when clipboard access is unavailable.
    }
    setFeedback(copied ? "Preview link copied" : "Sample link ready to copy");
  }

  function downloadPreview() {
    const content = format === "JSON"
      ? JSON.stringify({ workspace: workspace.name, sources: include.sources ? initialNotes.map((note) => note.source) : [], notes: include.notes ? initialNotes : [], connections: include.connections ? 8 : 0 }, null, 2)
      : `# ${workspace.name}\n\nSample research export\n\n${include.sources ? `## Sources\n${[...new Set(initialNotes.map((note) => note.source))].map((source) => `- ${source}`).join("\n")}\n\n` : ""}${include.notes ? `## Notes\n${initialNotes.map((note) => `### ${note.title}\n${note.body}`).join("\n\n")}\n\n` : ""}${include.connections ? "## Connections\n8 relationships included in this sample.\n" : ""}`;
    const blob = new Blob([content], { type: format === "JSON" ? "application/json" : "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${workspace.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}.${format === "JSON" ? "json" : "md"}`;
    link.click();
    URL.revokeObjectURL(url);
    setFeedback(`${format} sample downloaded`);
  }

  return (
    <div className={`${styles.workspaceView} ${styles.shareView}`}>
      <PageHeading
        workspace={workspace}
        eyebrow="Share & export"
        title="Take your research with you."
        description="A clear, portable snapshot of the sources and thinking in this workspace."
      />

      <div className={styles.shareColumns}>
        <section className={styles.shareSection} aria-labelledby="sharing-title">
          <div className={styles.sectionHeading}>
            <div><span className={styles.sectionEyebrow}>01 / ACCESS</span><h2 id="sharing-title">Share this workspace</h2></div>
            <span className={styles.sampleFlag}>Preview</span>
          </div>
          <p className={styles.sectionDescription}>Choose who can open a read-only view of this research.</p>

          <div className={styles.accessOptions} role="group" aria-label="Workspace access">
            <button className={access === "link" ? styles.accessSelected : ""} onClick={() => { setAccess("link"); setFeedback(""); }} aria-pressed={access === "link"}>
              <span className={styles.accessRadio} />
              <span><strong>Anyone with the link</strong><small>View-only access · no sign-in required</small></span>
              <span className={styles.accessState}>LINK ACCESS</span>
            </button>
            <button className={access === "private" ? styles.accessSelected : ""} onClick={() => { setAccess("private"); setFeedback(""); }} aria-pressed={access === "private"}>
              <span className={styles.accessRadio} />
              <span><strong>Only me</strong><small>Keep this workspace private</small></span>
            </button>
          </div>

          {access === "link" ? (
            <div className={styles.linkPanel}>
              <div><span className={styles.linkStatus}><i />Sample link ready</span><span>Preview only; no public workspace is created.</span></div>
              <div className={styles.copyRow}><code>mindloom.app/share/{workspace.id}/preview</code><button className={styles.quietAction} onClick={() => void copyPreviewLink()}><ToolIcon name="copy" />Copy link</button></div>
            </div>
          ) : (
            <div className={`${styles.linkPanel} ${styles.privatePanel}`}><span className={styles.privateLock}>Private workspace</span><span>Link access is turned off in this preview.</span></div>
          )}

          <div className={styles.shareContents}>
            <div><span className={styles.shareCount}>04</span><span><strong>Sources</strong><small>Articles and papers</small></span></div>
            <div><span className={styles.shareCount}>04</span><span><strong>Notes</strong><small>Linked annotations</small></span></div>
            <div><span className={styles.shareCount}>08</span><span><strong>Connections</strong><small>Research relationships</small></span></div>
          </div>
        </section>

        <section className={styles.exportSection} aria-labelledby="export-title">
          <div className={styles.sectionHeading}>
            <div><span className={styles.sectionEyebrow}>02 / PORTABILITY</span><h2 id="export-title">Export a snapshot</h2></div>
            <span className={styles.fileStamp}>LOCAL FILE</span>
          </div>
          <p className={styles.sectionDescription}>Keep a copy of your research outside Mindloom.</p>

          <div className={styles.exportFormat}>
            <span className={styles.controlLabel}>FILE FORMAT</span>
            <div role="group" aria-label="Export format">
              {(["Markdown", "JSON"] as const).map((item) => <button key={item} className={format === item ? styles.formatActive : ""} onClick={() => { setFormat(item); setFeedback(""); }} aria-pressed={format === item}>{item}<small>{item === "Markdown" ? ".md" : ".json"}</small></button>)}
            </div>
          </div>

          <fieldset className={styles.includeFields}>
            <legend className={styles.controlLabel}>INCLUDE IN EXPORT</legend>
            {([ ["sources", "Saved sources", "4 pages"], ["notes", "Notes & annotations", "4 notes"], ["connections", "Graph connections", "8 links"] ] as const).map(([key, label, count]) => (
              <label key={key}><input type="checkbox" checked={include[key]} onChange={(event) => { setInclude((current) => ({ ...current, [key]: event.target.checked })); setFeedback(""); }} /><span>{label}</span><small>{count}</small></label>
            ))}
          </fieldset>

          <div className={styles.exportPreview}>
            <div className={styles.previewHeader}><span><i />{workspace.name.toLowerCase().replace(/\s+/g, "-")}.{format === "JSON" ? "json" : "md"}</span><small>MOCK CONTENT</small></div>
            <pre>{format === "Markdown" ? `# ${workspace.name}\n\n4 sources  ·  4 notes  ·  8 connections\n\n## Featured note\nAttention makes the sequence parallel` : `{"workspace": "${workspace.name}",\n "sources": 4, "notes": 4,\n "connections": 8}`}</pre>
          </div>

          <div className={styles.exportFooter}><span>{feedback || "Sample data · nothing is published or stored"}</span><button className={styles.primaryAction} onClick={downloadPreview}><ToolIcon name="download" />Download {format}</button></div>
        </section>
      </div>
      <p className={styles.previewFootnote}><span>DEMO PREVIEW</span> Sharing and export use sample workspace data. No live link is created.</p>
    </div>
  );
}

export function LibraryView({ workspace }: { workspace: Workspace }) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<"All sources" | "Papers" | "Repositories">("All sources");
  const [selectedId, setSelectedId] = useState(librarySources[0].id);
  const visibleSources = librarySources.filter((source) => {
    const matchesKind = kind === "All sources" || (kind === "Papers" ? source.kind === "Paper" : source.kind === "Repository");
    return matchesKind && `${source.title} ${source.domain} ${source.tags.join(" ")}`.toLowerCase().includes(query.toLowerCase());
  });
  const selectedSource = visibleSources.find((source) => source.id === selectedId) ?? visibleSources[0];

  return (
    <div className={`${styles.workspaceView} ${styles.libraryView}`}>
      <PageHeading workspace={workspace} eyebrow="Library" title="Source library" description="Every saved page, organized and ready to revisit." action={<span className={styles.sampleFlag}>4 sample sources</span>} />
      <div className={styles.librarySummary}><strong>04</strong><span>saved sources</span><i /><strong>03</strong><span>research papers</span><i /><strong>01</strong><span>repository</span><span className={styles.librarySummaryTail}>SORTED BY RECENT</span></div>
      <div className={styles.libraryWorkbench}>
        <section className={styles.sourceRegister} aria-label="Saved sources">
          <div className={styles.registerToolbar}>
            <label className={styles.noteSearch}><span className={styles.srOnly}>Search sources</span><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search titles, tags, domains…" /></label>
            <div className={styles.libraryFilters} aria-label="Filter sources">
              {(["All sources", "Papers", "Repositories"] as const).map((item) => <button key={item} className={kind === item ? styles.filterActive : ""} onClick={() => setKind(item)} aria-pressed={kind === item}>{item}</button>)}
            </div>
          </div>
          <div className={styles.sourceTableHead}><span>SOURCE</span><span>TYPE</span><span>STATUS</span><span>ADDED</span></div>
          <div className={styles.sourceTableRows}>
            {visibleSources.map((source) => <button key={source.id} className={`${styles.sourceTableRow} ${selectedSource?.id === source.id ? styles.sourceRowSelected : ""}`} onClick={() => setSelectedId(source.id)} aria-current={selectedSource?.id === source.id ? "true" : undefined}>
              <span className={styles.sourceTableName}><i>{source.domain.slice(0, 1).toUpperCase()}</i><span><strong>{source.title}</strong><small>{source.domain}</small></span></span>
              <span className={styles.sourceType}>{source.kind}</span>
              <span className={`${styles.sourceStatus} ${source.status === "Processing" ? styles.statusProcessing : ""}`}><i />{source.status}</span>
              <span className={styles.sourceDate}>{source.date}</span>
            </button>)}
            {visibleSources.length === 0 && <p className={styles.noResults}>No saved sources match these filters.</p>}
          </div>
          <div className={styles.registerFooter}><span>Showing {visibleSources.length} of 4 sources</span><span>Workspace · {workspace.name}</span></div>
        </section>
        <aside className={styles.sourceDetail} aria-label="Selected source details">
          {selectedSource ? <>
            <div className={styles.sourceDetailTop}><span className={styles.detailKicker}>SOURCE RECORD</span><span className={`${styles.sourceStatus} ${selectedSource.status === "Processing" ? styles.statusProcessing : ""}`}><i />{selectedSource.status}</span></div>
            <h2>{selectedSource.title}</h2>
            <span className={styles.sourceDomain}>{selectedSource.domain}</span>
            <div className={styles.sourceMeta}><span>TYPE<strong>{selectedSource.kind}</strong></span><span>ADDED<strong>{selectedSource.date}</strong></span></div>
            <div className={styles.sourceAbstract}><span className={styles.detailKicker}>WORKSPACE SUMMARY</span><p>{selectedSource.summary}</p></div>
            <div className={styles.noteTags}>{selectedSource.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
            <div className={styles.sourceDetailBottom}><span>Linked annotations<strong>{selectedSource.id === "source-1" ? "1 note" : selectedSource.id === "source-2" ? "1 note" : "1 note"}</strong></span><span className={styles.savedIndicator}><i />In {workspace.name}</span></div>
          </> : <div className={styles.emptyNotes}><strong>No source selected</strong><span>Adjust the search or filters.</span></div>}
        </aside>
      </div>
    </div>
  );
}

export function SearchView({ workspace }: { workspace: Workspace }) {
  const [query, setQuery] = useState("attention");
  const [scope, setScope] = useState<"Everything" | "Sources" | "Notes">("Everything");
  const [selectedId, setSelectedId] = useState("result-1");
  const results = searchItems.filter((item) => {
    const matchesScope = scope === "Everything" || item.type === (scope === "Sources" ? "Source" : "Note");
    const matchesQuery = `${item.title} ${item.location} ${item.body} ${item.tags.join(" ")}`.toLowerCase().includes(query.toLowerCase());
    return matchesScope && matchesQuery;
  });

  return (
    <div className={`${styles.workspaceView} ${styles.searchView}`}>
      <PageHeading workspace={workspace} eyebrow="Search" title="Find the thread." description="Search across saved sources, notes, and the ideas between them." />
      <div className={styles.searchWorkbench}>
        <label className={styles.mainSearch}>
          <span className={styles.srOnly}>Search this workspace</span>
          <svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search this workspace…" />
          {query && <button type="button" onClick={() => setQuery("")} aria-label="Clear search">×</button>}
        </label>
        <div className={styles.searchControlRow}>
          <div className={styles.searchScopes} role="group" aria-label="Search within">
            {(["Everything", "Sources", "Notes"] as const).map((item) => <button key={item} className={scope === item ? styles.scopeActive : ""} onClick={() => setScope(item)} aria-pressed={scope === item}>{item}<small>{item === "Everything" ? searchItems.length : searchItems.filter((result) => result.type === (item === "Sources" ? "Source" : "Note")).length}</small></button>)}
          </div>
          <span className={styles.searchScopeLabel}>IN {workspace.name.toUpperCase()}</span>
        </div>
        <div className={styles.searchResultsHeader}><div><span className={styles.sectionEyebrow}>RESULTS</span><h2>{results.length} {results.length === 1 ? "match" : "matches"}<span>{query ? ` for “${query}”` : " across your workspace"}</span></h2></div><span className={styles.resultSort}>Most relevant <i>⌄</i></span></div>
        <div className={styles.searchResults}>
          {results.map((result, index) => <button key={result.id} className={`${styles.searchResult} ${selectedId === result.id ? styles.searchResultSelected : ""}`} onClick={() => setSelectedId(result.id)}>
            <span className={styles.resultRank}>{String(index + 1).padStart(2, "0")}</span>
            <span className={styles.resultContent}><span className={styles.resultMeta}><i className={result.type === "Note" ? styles.noteResultMark : ""} />{result.type}<i />{result.location}</span><strong>{result.title}</strong><span className={styles.resultExcerpt}>{result.body}</span><span className={styles.resultTags}>{result.tags.map((tag) => <small key={tag}>{tag}</small>)}</span></span>
            <span className={styles.resultMatch}>{result.type === "Source" ? "SOURCE" : "ANNOTATION"}<strong>{index === 0 ? "Best match" : "Related"}</strong></span>
          </button>)}
          {results.length === 0 && <div className={styles.searchEmpty}><strong>No matches found</strong><span>Try a broader phrase or search all content types.</span></div>}
        </div>
        <div className={styles.searchFooter}><span>Search preview · 4 sources and 4 notes</span><span>Results update as you type</span></div>
      </div>
    </div>
  );
}