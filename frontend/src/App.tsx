import { useEffect, useMemo, useState } from "react";
import { demoFindings, demoHistoryByFinding, demoNotesByFinding, demoSummary } from "./demoData";
import type { Finding, FindingSeverity, FindingStatus } from "./types";
import "./styles.css";

type FilterValue<T extends string> = T | "all";

const statusLabels: Record<FindingStatus, string> = {
  new: "New",
  investigating: "Investigating",
  resolved: "Resolved",
  dismissed: "Dismissed",
};

const severityLabels: Record<FindingSeverity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  informational: "Info",
};

const dateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
  timeZoneName: "short",
});

function formatDate(value: string) {
  return dateFormatter.format(new Date(value));
}

function Icon({ name }: { name: "overview" | "findings" | "chevron" | "close" }) {
  const paths = {
    overview: (
      <>
        <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
        <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
        <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
        <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
      </>
    ),
    findings: (
      <>
        <path d="M12 3 20 6v5.2c0 5-3.4 8.5-8 10.3-4.6-1.8-8-5.3-8-10.3V6l8-3Z" />
        <path d="m8.5 12 2.2 2.2 4.8-5" />
      </>
    ),
    chevron: <path d="m9 18 6-6-6-6" />,
    close: <path d="m6 6 12 12M18 6 6 18" />,
  };

  return (
    <svg
      aria-hidden="true"
      className="icon"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
      viewBox="0 0 24 24"
    >
      {paths[name]}
    </svg>
  );
}

function FindingRow({ finding, onOpen }: { finding: Finding; onOpen: (finding: Finding) => void }) {
  return (
    <tr>
      <td className="finding-cell">
        <button
          aria-label={`View ${finding.title}`}
          className="finding-link"
          onClick={() => onOpen(finding)}
          type="button"
        >
          {finding.title}
        </button>
        <span className="finding-meta">Observed {formatDate(finding.observed_at)}</span>
      </td>
      <td>
        <span className={`severity severity-${finding.severity}`}>
          <span className="severity-dot" />
          {severityLabels[finding.severity]}
        </span>
      </td>
      <td>
        <span className={`status status-${finding.status}`}>{statusLabels[finding.status]}</span>
      </td>
      <td className="source-cell">{finding.source}</td>
      <td className="date-cell">{formatDate(finding.updated_at)}</td>
      <td className="action-cell">
        <button
          aria-label={`Open details for ${finding.title}`}
          className="icon-button row-action"
          onClick={() => onOpen(finding)}
          type="button"
        >
          <Icon name="chevron" />
        </button>
      </td>
    </tr>
  );
}

function FindingDetails({ finding, onClose }: { finding: Finding; onClose: () => void }) {
  const notes = demoNotesByFinding[finding.id] ?? [];
  const history = demoHistoryByFinding[finding.id] ?? [];

  return (
    <div className="drawer-layer">
      <button aria-label="Close finding details" className="drawer-backdrop" onClick={onClose} type="button" />
      <aside aria-labelledby="detail-title" aria-modal="true" className="detail-drawer" role="dialog">
        <div className="drawer-header">
          <div>
            <p className="eyebrow">Finding details</p>
            <h2 id="detail-title">Investigation</h2>
          </div>
          <button aria-label="Close finding details" className="icon-button" onClick={onClose} type="button">
            <Icon name="close" />
          </button>
        </div>

        <div className="drawer-content">
          <div className="detail-title-row">
            <span className={`severity severity-${finding.severity}`}>
              <span className="severity-dot" />
              {severityLabels[finding.severity]} severity
            </span>
            <span className={`status status-${finding.status}`}>{statusLabels[finding.status]}</span>
          </div>
          <h3 className="detail-finding-title">{finding.title}</h3>
          <p className="detail-description">{finding.description}</p>

          <section className="detail-section">
            <h3>Evidence summary</h3>
            <p>{finding.evidence_summary}</p>
          </section>

          <section className="detail-section">
            <h3>Source information</h3>
            <dl className="detail-grid">
              <div>
                <dt>Source</dt>
                <dd>{finding.source}</dd>
              </div>
              <div>
                <dt>Observed</dt>
                <dd>{formatDate(finding.observed_at)}</dd>
              </div>
              {Object.entries(finding.metadata).map(([key, value]) => (
                <div key={key}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>{String(value)}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="detail-section">
            <div className="section-heading-row">
              <h3>Investigation notes</h3>
              <span className="section-count">{notes.length}</span>
            </div>
            {notes.length ? (
              <div className="note-list">
                {notes.map((note) => (
                  <article className="note-card" key={note.id}>
                    <div className="note-meta">
                      <strong>{note.author}</strong>
                      <time dateTime={note.created_at}>{formatDate(note.created_at)}</time>
                    </div>
                    <p>{note.body}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="empty-copy">No notes have been added to this finding.</p>
            )}
          </section>

          <section className="detail-section">
            <div className="section-heading-row">
              <h3>Activity history</h3>
              <span className="section-count">{history.length}</span>
            </div>
            {history.length ? (
              <ol className="timeline">
                {history.map((event) => (
                  <li key={event.id}>
                    <span className="timeline-marker" />
                    <div>
                      <strong>{event.actor}</strong>
                      <p>
                        {event.event_type === "finding.status_changed"
                          ? `Changed status to ${String(event.details.to_status ?? "updated")}`
                          : "Added an investigation note"}
                      </p>
                      <time dateTime={event.occurred_at}>{formatDate(event.occurred_at)}</time>
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="empty-copy">No activity has been recorded yet.</p>
            )}
          </section>
        </div>
      </aside>
    </div>
  );
}

export function App() {
  const [statusFilter, setStatusFilter] = useState<FilterValue<FindingStatus>>("all");
  const [severityFilter, setSeverityFilter] = useState<FilterValue<FindingSeverity>>("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

  useEffect(() => {
    if (!selectedFinding) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedFinding(null);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [selectedFinding]);

  const sources = useMemo(
    () => Array.from(new Set(demoFindings.map((finding) => finding.source))).sort(),
    [],
  );

  const filteredFindings = useMemo(
    () =>
      demoFindings.filter(
        (finding) =>
          (statusFilter === "all" || finding.status === statusFilter) &&
          (severityFilter === "all" || finding.severity === severityFilter) &&
          (sourceFilter === "all" || finding.source === sourceFilter),
      ),
    [severityFilter, sourceFilter, statusFilter],
  );

  const clearFilters = () => {
    setStatusFilter("all");
    setSeverityFilter("all");
    setSourceFilter("all");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a aria-label="Cloud Security Findings Tracker home" className="brand" href="#overview">
          <span className="brand-mark">S</span>
          <span className="brand-name">
            <strong>Sentinel</strong>
            <small>SECURITY OPERATIONS</small>
          </span>
        </a>

        <div className="workspace-switcher">
          <span className="workspace-icon">D</span>
          <span>
            <strong>Demo workspace</strong>
            <small>Personal environment</small>
          </span>
          <span aria-hidden="true" className="workspace-chevron">⌄</span>
        </div>

        <p className="nav-label">WORKSPACE</p>
        <nav aria-label="Primary navigation" className="primary-nav">
          <a className="nav-item" href="#overview">
            <Icon name="overview" />
            Overview
          </a>
          <a aria-current="page" className="nav-item active" href="#findings">
            <Icon name="findings" />
            Findings
            <span className="nav-count">{demoSummary.total}</span>
          </a>
        </nav>

        <div className="sidebar-spacer" />
        <div className="sidebar-note">
          <span className="note-shield"><Icon name="findings" /></span>
          <strong>Built for safe triage</strong>
          <p>Every record in this workspace is synthetic sample data.</p>
        </div>
        <div className="sidebar-footer">
          <span className="environment-dot" />
          Local preview
          <span className="build-version">v0.2</span>
        </div>
      </aside>

      <main className="main-area" id="overview">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Security</span>
            <span className="breadcrumb-separator">/</span>
            <strong>Findings</strong>
          </div>
          <div className="topbar-right">
            <span className="sample-badge"><span /> Synthetic data</span>
            <span aria-hidden="true" className="topbar-divider" />
            <div className="user-chip">
              <span className="user-avatar">DA</span>
              <span className="user-copy">
                <strong>Demo analyst</strong>
                <small>Analyst</small>
              </span>
            </div>
          </div>
        </header>

        <div className="page-content" id="findings">
          <div className="page-heading">
            <div>
              <p className="eyebrow">SECURITY OPERATIONS / OVERVIEW</p>
              <h1>Findings overview</h1>
              <p className="page-subtitle">Review, prioritize, and investigate cloud security events.</p>
            </div>
            <div className="updated-indicator">
              <span className="pulse-dot" />
              Preview environment
            </div>
          </div>

          <section aria-label="Finding summary" className="summary-grid">
            <article className="summary-card total-card">
              <div className="summary-topline">
                <span className="summary-label">Total findings</span>
                <span className="summary-icon icon-violet"><Icon name="overview" /></span>
              </div>
              <strong className="summary-value">{demoSummary.total}</strong>
              <span className="summary-footnote">Across synthetic sources</span>
            </article>
            <article className="summary-card critical-card">
              <div className="summary-topline">
                <span className="summary-label">Critical</span>
                <span className="summary-icon icon-red"><span className="summary-alert">!</span></span>
              </div>
              <strong className="summary-value">{demoSummary.by_severity.critical}</strong>
              <span className="summary-footnote">Needs immediate review</span>
            </article>
            <article className="summary-card investigating-card">
              <div className="summary-topline">
                <span className="summary-label">Investigating</span>
                <span className="summary-icon icon-amber"><span className="summary-ring" /></span>
              </div>
              <strong className="summary-value">{demoSummary.by_status.investigating}</strong>
              <span className="summary-footnote">Active analyst reviews</span>
            </article>
            <article className="summary-card resolved-card">
              <div className="summary-topline">
                <span className="summary-label">Resolved findings</span>
                <span className="summary-icon icon-green"><span className="summary-check">✓</span></span>
              </div>
              <strong className="summary-value">{demoSummary.by_status.resolved}</strong>
              <span className="summary-footnote">Closed with a recorded reason</span>
            </article>
          </section>

          <section aria-labelledby="findings-title" className="findings-panel">
            <div className="panel-heading">
              <div>
                <div className="panel-title-row">
                  <h2 id="findings-title">Recent findings</h2>
                  <span className="result-count">{filteredFindings.length}</span>
                </div>
                <p>Prioritized events from your monitored cloud environment.</p>
              </div>
              <span className="table-context"><span className="context-dot" /> Last 24 hours</span>
            </div>

            <div className="filter-bar">
              <div className="filter-caption">
                <span className="filter-symbol">≡</span>
                <span>Filter by</span>
              </div>
              <label className="filter-select">
                <span className="sr-only">Status</span>
                <select
                  aria-label="Status"
                  onChange={(event) => setStatusFilter(event.target.value as FilterValue<FindingStatus>)}
                  value={statusFilter}
                >
                  <option value="all">All statuses</option>
                  {Object.entries(statusLabels).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </label>
              <label className="filter-select">
                <span className="sr-only">Severity</span>
                <select
                  aria-label="Severity"
                  onChange={(event) => setSeverityFilter(event.target.value as FilterValue<FindingSeverity>)}
                  value={severityFilter}
                >
                  <option value="all">All severities</option>
                  {Object.entries(severityLabels).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </label>
              <label className="filter-select">
                <span className="sr-only">Source</span>
                <select aria-label="Source" onChange={(event) => setSourceFilter(event.target.value)} value={sourceFilter}>
                  <option value="all">All sources</option>
                  {sources.map((source) => <option key={source} value={source}>{source}</option>)}
                </select>
              </label>
              <button className="clear-filters" onClick={clearFilters} type="button">Clear filters</button>
            </div>

            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Finding</th>
                    <th scope="col">Severity</th>
                    <th scope="col">Status</th>
                    <th scope="col">Source</th>
                    <th scope="col">Last updated</th>
                    <th scope="col"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFindings.map((finding) => (
                    <FindingRow finding={finding} key={finding.id} onOpen={setSelectedFinding} />
                  ))}
                </tbody>
              </table>
              {filteredFindings.length === 0 && (
                <div className="empty-table">
                  <span className="empty-table-icon">⌕</span>
                  <strong>No findings match these filters</strong>
                  <p>Try broadening your search criteria.</p>
                  <button className="text-button" onClick={clearFilters} type="button">Clear filters</button>
                </div>
              )}
            </div>
            <div className="table-footer">
              <span>Showing <strong>{filteredFindings.length}</strong> of <strong>{demoSummary.total}</strong> findings</span>
              <span>Sample records are clearly identified as synthetic.</span>
            </div>
          </section>

          <footer className="page-footer">
            <span>Cloud Security Findings Tracker</span>
            <span>Local development preview · No live cloud telemetry</span>
          </footer>
        </div>
      </main>

      {selectedFinding && <FindingDetails finding={selectedFinding} onClose={() => setSelectedFinding(null)} />}
    </div>
  );
}
