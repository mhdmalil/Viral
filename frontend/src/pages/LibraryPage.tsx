import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { VibeChips } from "../components/VibeChips";
import { copyText } from "../lib/clipboard";
import { formatDuration, formatScore, formatSourceRange } from "../lib/format";
import { clipVibes } from "../lib/vibes";
import { api } from "../services/api";
import type { Clip, Project } from "../types/api";

function hasHookTag(clip: Clip): boolean {
  return (clip.tags || []).includes("hook");
}

export function LibraryPage() {
  const [clips, setClips] = useState<Clip[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [tagNames, setTagNames] = useState<string[]>([]);
  const [q, setQ] = useState("");
  const [projectId, setProjectId] = useState<number | "">("");
  const [tag, setTag] = useState("");
  const [wantedVibes, setWantedVibes] = useState<string[]>([]);
  const [ready, setReady] = useState<"all" | "ready" | "missing">("all");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copiedId, setCopiedId] = useState<number | "all" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const rows = await api.clips({
      q: q.trim() || undefined,
      projectId: projectId === "" ? undefined : projectId,
      tag: tag || undefined,
      vibes: wantedVibes.length ? wantedVibes : undefined,
      ready: ready === "all" ? undefined : ready === "ready",
    });
    setClips(rows);
    setSelected((current) => new Set([...current].filter((id) => rows.some((clip) => clip.id === id))));
  }, [q, projectId, tag, ready, wantedVibes]);

  useEffect(() => {
    api.projects().then(setProjects).catch((err: Error) => setError(err.message));
    api.tags().then(setTagNames).catch(() => undefined);
  }, []);

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, [load]);

  const chosen = clips.filter((clip) => selected.has(clip.id));
  const allSelected = clips.length > 0 && clips.every((clip) => selected.has(clip.id));
  const extraTags = tagNames.filter((name) => name !== "hook");

  function toggle(clip: Clip, checked: boolean) {
    setSelected((current) => {
      const next = new Set(current);
      if (checked) next.add(clip.id);
      else next.delete(clip.id);
      return next;
    });
  }

  async function copyHooks(rows: Clip[], id: number | "all") {
    const text = rows.map((clip) => clip.title || clip.filename || "").filter(Boolean).join("\n");
    const ok = await copyText(text);
    if (!ok) return;
    setCopiedId(id);
    window.setTimeout(() => setCopiedId(null), 1500);
  }

  async function bulkDownload() {
    const ids = chosen.filter((clip) => clip.has_file).map((clip) => clip.id);
    if (ids.length === 0) return;
    setError(null);
    setNotice(null);
    try {
      const saved = await api.downloadClips(ids);
      setNotice(`Saved ${saved.count} clip${saved.count === 1 ? "" : "s"} to the downloads folder: ${saved.folder}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    }
  }

  async function bulkDelete() {
    const ids = [...selected];
    if (ids.length === 0) return;
    if (!window.confirm(`Delete ${ids.length} clip${ids.length === 1 ? "" : "s"} from ViralClipper? This removes the files.`)) return;
    setError(null);
    try {
      await api.deleteClips(ids);
      setSelected(new Set());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete clips");
    }
  }

  async function markHook() {
    if (chosen.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      await Promise.all(
        chosen.map((clip) => api.updateClipTags(clip.id, Array.from(new Set([...(clip.tags || []), "hook"])))),
      );
      setTagNames(await api.tags());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not tag clips");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="library-page">
      <div className="page-head">
        <h1>Library</h1>
      </div>
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p className="notice" role="status">
          {notice}
        </p>
      ) : null}

      <div className="library-bar panel">
        <label>
          Search
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Title or project" />
        </label>
        <label>
          Project
          <select value={projectId === "" ? "" : String(projectId)} onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">All</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Files
          <select value={ready} onChange={(e) => setReady(e.target.value as "all" | "ready" | "missing")}>
            <option value="all">All</option>
            <option value="ready">Ready</option>
            <option value="missing">No file</option>
          </select>
        </label>
        <label>
          Tag
          <select value={tag} onChange={(e) => setTag(e.target.value)}>
            <option value="">All</option>
            <option value="hook">Hook</option>
            {extraTags.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <VibeChips
        value={wantedVibes}
        onChange={setWantedVibes}
        label="Show kinds"
        hint="Tick kinds to show. Several is fine. Mixed clips show if they match any tick. None ticked means all."
      />

      <div className="library-actions">
        <label className="select-all">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={(e) => setSelected(e.target.checked ? new Set(clips.map((clip) => clip.id)) : new Set())}
            disabled={clips.length === 0}
          />
          {chosen.length} selected
        </label>
        <div className="library-actions-end">
          <button type="button" className="btn-quiet" disabled={chosen.length === 0} onClick={() => void copyHooks(chosen, "all")}>
            {copiedId === "all" ? "Copied" : "Copy hooks"}
          </button>
          <button type="button" className="btn-quiet" disabled={chosen.length === 0 || busy} onClick={() => void markHook()}>
            Hook
          </button>
          <button type="button" className="btn-quiet" disabled={chosen.every((clip) => !clip.has_file)} onClick={() => void bulkDownload()}>
            Download
          </button>
          <button type="button" className="btn-danger" disabled={chosen.length === 0} onClick={() => void bulkDelete()}>
            Delete
          </button>
        </div>
      </div>

      {clips.length === 0 ? (
        <p className="empty library-empty">{q || tag || projectId || ready !== "all" ? "No clips match these filters." : "No clips yet. Generate from a project."}</p>
      ) : (
        <ul className="library-list">
          {clips.map((clip) => {
            const label = clip.title || `Clip ${clip.id}`;
            const numbered = clip.clip_index != null ? `${clip.clip_index}. ${label}` : label;
            const hooked = hasHookTag(clip);
            return (
              <li key={clip.id} className={selected.has(clip.id) ? "library-row selected" : "library-row"}>
                <input
                  type="checkbox"
                  checked={selected.has(clip.id)}
                  onChange={(event) => toggle(clip, event.target.checked)}
                  aria-label={`Select ${numbered}`}
                />
                {clip.has_file ? (
                  <video muted preload="metadata" playsInline src={`/api/clips/${clip.id}/file`} aria-label={numbered} />
                ) : (
                  <div className="library-thumb-empty" aria-hidden="true" />
                )}
                <div className="library-row-body">
                  <div className="library-row-head">
                    <p className="library-row-title">{numbered}</p>
                    <button
                      type="button"
                      className="btn-quiet copy-hook"
                      onClick={() => void copyHooks([clip], clip.id)}
                    >
                      {copiedId === clip.id ? "Copied" : "Copy"}
                    </button>
                  </div>
                  <p className="library-row-meta">
                    {clip.project_id ? (
                      <Link to={`/projects/${clip.project_id}`}>{clip.project_name || "Project"}</Link>
                    ) : (
                      <span>{clip.project_name || "Library"}</span>
                    )}
                    <span>
                      {formatSourceRange(clip.start_time, clip.end_time) ?? (clip.duration ? formatDuration(clip.duration) : "—")}
                    </span>
                    <span>
                      {formatScore(clip.quality_score)}
                      <span className="meta">/100</span>
                    </span>
                    {clip.hook_at != null ? <span>Hook {formatDuration(clip.hook_at)}</span> : null}
                    {clipVibes(clip).map((name) => (
                      <span key={name} className="tag-chip on" aria-label={`Vibe ${name}`}>
                        {name}
                      </span>
                    ))}
                  </p>
                  {hooked ? (
                    <div className="library-row-tags">
                      <button type="button" className="tag-chip on" onClick={() => setTag("hook")}>
                        Hook
                      </button>
                    </div>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
