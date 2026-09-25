import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { LoaderDots } from "../components/LoaderDots";
import { api } from "../services/api";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/projects", label: "Projects" },
  { to: "/library", label: "Library" },
  { to: "/usage", label: "API" },
  { to: "/accounts", label: "Accounts" },
  { to: "/settings", label: "Settings" },
];

const STORAGE_KEY = "vc-nav-collapsed";
const DONE = new Set(["COMPLETED", "FAILED", "CANCELLED", "DELETED", "INFO"]);

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [generating, setGenerating] = useState<{ projectId: number; label: string } | null>(null);

  useEffect(() => {
    setCollapsed(window.localStorage.getItem(STORAGE_KEY) === "1");
  }, []);

  useEffect(() => {
    let alive = true;
    function refresh() {
      api
        .dashboard()
        .then((data) => {
          if (!alive) return;
          const live = data.recent_activity.find((row) => row.id.startsWith("job-") && !DONE.has(row.status));
          setGenerating(live ? { projectId: live.project_id, label: live.stage_message || live.status } : null);
        })
        .catch(() => undefined);
    }
    refresh();
    const timer = window.setInterval(refresh, 4000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  function toggle() {
    setCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      return next;
    });
  }

  return (
    <div className={collapsed ? "shell collapsed" : "shell"}>
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">
              VC
            </span>
            <span className="brand-text">ViralClipper</span>
          </div>
          <button type="button" className="sidebar-toggle" aria-expanded={!collapsed} aria-controls="app-nav" onClick={toggle}>
            {collapsed ? "Open menu" : "Hide menu"}
          </button>
        </div>
        <nav id="app-nav" aria-label="Primary">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              title={link.label}
              aria-label={link.label}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              <span className="nav-label">{link.label}</span>
            </NavLink>
          ))}
        </nav>
        {generating ? (
          <NavLink className="nav-generating" to={`/projects/${generating.projectId}`} title={generating.label}>
            <span className="nav-generating-row">
              <LoaderDots className="loader-dots-sm" />
              <span className="nav-generating-title">Generating</span>
            </span>
            <span className="nav-label">{generating.label}</span>
          </NavLink>
        ) : null}
      </aside>
      <main className="main main-full">
        <Outlet />
      </main>
    </div>
  );
}
