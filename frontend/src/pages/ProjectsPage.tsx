import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../services/api";
import type { Project } from "../types/api";

export function ProjectsPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  function refresh() {
    api.projects().then(setProjects).catch((err: Error) => setError(err.message));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const created = await api.createProject({
        name: name.trim(),
      });
      setName("");
      navigate(`/projects/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create project");
      setSaving(false);
    }
  }

  async function onDelete(project: Project) {
    const ok = window.confirm(`Delete “${project.name}”? This cannot be undone.`);
    if (!ok) return;
    setDeletingId(project.id);
    setError(null);
    try {
      await api.deleteProject(project.id);
      setProjects((current) => current.filter((item) => item.id !== project.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete project");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Projects</h1>
        </div>
      </div>
      {error ? <p className="error" role="alert">{error}</p> : null}

      <form className="panel create-row" onSubmit={onSubmit}>
        <label>
          New project
          <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Podcast Episode 42" />
        </label>
        <button type="submit" disabled={saving || !name.trim()}>
          {saving ? "Creating…" : "Create and open"}
        </button>
      </form>

      {projects.length === 0 ? (
        <p className="empty">No projects yet. Create one to start importing a video.</p>
      ) : (
        <ul className="project-grid">
          {projects.map((project) => (
            <li key={project.id} className="project-card">
              <Link className="project-card-main" to={`/projects/${project.id}`}>
                <h2>{project.name}</h2>
                <p className="meta">Clips {project.ready_clips}</p>
              </Link>
              <button
                type="button"
                className="btn-danger"
                disabled={deletingId === project.id}
                onClick={() => onDelete(project)}
              >
                {deletingId === project.id ? "Deleting…" : "Delete"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
