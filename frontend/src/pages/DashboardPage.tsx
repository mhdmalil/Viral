import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiMonitor } from "../components/ApiMonitor";
import { formatLogTime } from "../lib/format";
import { api } from "../services/api";
import type { Dashboard, UsageReport } from "../types/api";

export function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [usage, setUsage] = useState<UsageReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function refreshDashboard() {
      api
        .dashboard()
        .then(setData)
        .catch((err: Error) => setError(err.message));
    }
    function refreshUsage() {
      api.usage().then(setUsage).catch(() => undefined);
    }
    refreshDashboard();
    refreshUsage();
    const timer = window.setInterval(() => {
      refreshDashboard();
      refreshUsage();
    }, 3000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section>
      <div className="page-head">
        <h1>Dashboard</h1>
      </div>
      {error ? <p className="error" role="alert">{error}</p> : null}
      <div className="stats-row">
        <article className="card stat-card">
          <p>Projects</p>
          <strong>{data ? data.project_count : "—"}</strong>
        </article>
        <article className="card stat-card">
          <p>Clips</p>
          <strong>{data ? data.clip_count : "—"}</strong>
        </article>
        <article className="card stat-card">
          <p>Downloads</p>
          <strong>{data ? data.download_count : "—"}</strong>
        </article>
      </div>
      <div className="quick-actions">
        <Link className="btn-action" to="/projects">
          Open projects
        </Link>
        <Link className="btn-action btn-action-quiet" to="/projects">
          New project
        </Link>
      </div>
      <div className="dashboard-split">
        <article className="card">
          <h2>Recent projects</h2>
          {!data || data.recent_projects.length === 0 ? (
            <p className="empty">No projects yet.</p>
          ) : (
            <ul className="nested-project-grid">
              {data.recent_projects.map((project) => (
                <li key={project.id}>
                  <Link className="nested-project-card" to={`/projects/${project.id}`}>
                    <h3>{project.name}</h3>
                    <p className="meta">
                      Clips {project.ready_clips}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </article>
        <article className="card activity-card">
          <h2>Recent activity</h2>
          {!data || data.recent_activity.length === 0 ? (
            <p className="empty">Nothing generated yet.</p>
          ) : (
            <ul className="activity-log">
              {data.recent_activity.map((row) => (
                <li key={row.id}>
                  <Link className="activity-log-line" to={`/projects/${row.project_id}`} title={row.stage_message || row.status}>
                    <time dateTime={row.created_at}>{formatLogTime(row.created_at)}</time>
                    <span>{row.stage_message?.trim() || row.status}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </article>
      </div>
      <div className="dashboard-api">
        {usage ? <ApiMonitor data={usage} variant="logs" /> : null}
      </div>
    </section>
  );
}
