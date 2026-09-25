import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiMonitor } from "../components/ApiMonitor";
import { LoaderDots } from "../components/LoaderDots";
import { VibeChips } from "../components/VibeChips";
import { copyText } from "../lib/clipboard";
import { formatDuration, formatScore, formatSourceRange } from "../lib/format";
import { clipVibes } from "../lib/vibes";
import { shortJobLabel } from "../lib/job";
import { api } from "../services/api";
import type { Clip, Job, Project, SourceVideo, UsageReport } from "../types/api";

const CLIP_COUNTS = [3, 5, 10, 15, 20, 30];
const CAPTION_STYLES = [
  { id: "classic", label: "Classic" },
  { id: "bold", label: "Bold" },
  { id: "boxed", label: "Boxed" },
] as const;
const SOCIALS = [
  { id: "youtube", label: "YouTube" },
  { id: "tiktok", label: "TikTok" },
  { id: "instagram", label: "Instagram" },
] as const;

type SocialState = Record<string, { on: boolean; name: string }>;

function emptySocials(): SocialState {
  return {
    youtube: { on: false, name: "" },
    tiktok: { on: false, name: "" },
    instagram: { on: false, name: "" },
  };
}

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileName(path: string): string {
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] || "Video";
}

function ClipPlayer({
  clip,
  selected,
  onToggle,
}: {
  clip: Clip;
  selected: boolean;
  onToggle: (clip: Clip, checked: boolean) => void;
}) {
  const [copied, setCopied] = useState(false);
  const label = clip.title || `Clip ${clip.id}`;
  const numbered = clip.clip_index != null ? `${clip.clip_index}. ${label}` : label;
  const length =
    clip.duration ??
    (clip.start_time != null && clip.end_time != null ? clip.end_time - clip.start_time : null);
  async function copyHook() {
    const ok = await copyText(clip.title || clip.filename || "");
    if (!ok) return;
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }
  const vibes = clipVibes(clip);
  return (
    <li className={selected ? "clip-tile selected" : "clip-tile"}>
      <input
        className="clip-check"
        type="checkbox"
        checked={selected}
        onChange={(event) => onToggle(clip, event.target.checked)}
        aria-label={`Select ${numbered}`}
      />
      <div className="clip-tile-frame">
        {clip.has_file ? (
          <video controls preload="metadata" playsInline src={`/api/clips/${clip.id}/file?v=${clip.id}`} aria-label={numbered}>
            Your browser cannot play this clip.
          </video>
        ) : (
          <div className="clip-tile-empty">Not ready</div>
        )}
      </div>
      <div className="clip-tile-meta">
        <p className="clip-hook" title={numbered}>
          {numbered}
        </p>
        <p className="clip-tile-facts">
          <span className="clip-score">
            {formatScore(clip.quality_score)}
            <span>/100</span>
          </span>
          <span className="meta">
            {formatSourceRange(clip.start_time, clip.end_time) ?? "—"}
            {length != null ? ` · ${formatDuration(length)}` : ""}
          </span>
        </p>
        {vibes.length > 0 ? (
          <div className="clip-tile-tags">
            {vibes.map((name) => (
              <span key={name} className="tag-chip on" aria-label={`Vibe ${name}`}>
                {name}
              </span>
            ))}
          </div>
        ) : null}
        <button type="button" className="btn-quiet copy-hook" onClick={() => void copyHook()}>
          {copied ? "Copied" : "Copy hook"}
        </button>
      </div>
    </li>
  );
}

export function ProjectDetailPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const id = Number(projectId);
  const [project, setProject] = useState<Project | null>(null);
  const [sources, setSources] = useState<SourceVideo[]>([]);
  const [clips, setClips] = useState<Clip[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [clipCount, setClipCount] = useState<number | null>(null);
  const [captionStyle, setCaptionStyle] = useState("classic");
  const [captionsEnabled, setCaptionsEnabled] = useState(true);
  const [socials, setSocials] = useState<SocialState>(emptySocials);
  const [customName, setCustomName] = useState("");
  const [customLogoUrl, setCustomLogoUrl] = useState<string | null>(null);
  const [footerMode, setFooterMode] = useState<"socials" | "picture">("socials");
  const [wantedVibes, setWantedVibes] = useState<string[]>([]);
  const [brief, setBrief] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [watchApi, setWatchApi] = useState(false);
  const [usage, setUsage] = useState<UsageReport | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!Number.isFinite(id)) return;
    const [p, s, c, j] = await Promise.all([api.project(id), api.sources(id), api.clips({ projectId: id, inProject: true }), api.latestJob(id)]);
    setProject(p);
    setSources(s);
    setClips(c);
    setJob(j);
    setClipCount(p.clip_count);
    setCaptionStyle(p.caption_style || "classic");
    setCaptionsEnabled(Boolean(p.captions_enabled));
    const next = emptySocials();
    for (const row of p.branding?.handles || []) {
      if (next[row.platform]) {
        next[row.platform] = { on: true, name: row.name };
      }
    }
    setSocials(next);
    setCustomName(p.branding?.custom_name || "");
    setCustomLogoUrl(p.custom_logo_url || null);
    setFooterMode(p.branding?.footer === "picture" ? "picture" : "socials");
    setWantedVibes(p.branding?.vibes || []);
    setBrief(p.branding?.brief || "");
    setLoaded(true);
  }, [id]);

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, [load]);

  useEffect(() => {
    const active = job && !["COMPLETED", "FAILED", "CANCELLED"].includes(job.status);
    if (!active) return;
    const timer = window.setInterval(() => {
      api.latestJob(id).then(setJob).catch(() => undefined);
      api.clips({ projectId: id, inProject: true }).then(setClips).catch(() => undefined);
    }, 800);
    return () => window.clearInterval(timer);
  }, [id, job]);

  useEffect(() => {
    const generatingNow = Boolean(job && !["COMPLETED", "FAILED", "CANCELLED"].includes(job.status));
    if (!watchApi && !generatingNow) return;
    function refresh() {
      api.usage({ projectId: id }).then(setUsage).catch(() => undefined);
    }
    refresh();
    const timer = window.setInterval(refresh, 1000);
    return () => window.clearInterval(timer);
  }, [id, job, watchApi]);

  async function importFile(file: File) {
    setBusy(true);
    setError(null);
    setClips([]);
    try {
      await api.uploadSource(id, file);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  async function removeSource(source: SourceVideo) {
    const ok = window.confirm("Remove this video and every clip made from it?");
    if (!ok) return;
    setBusy(true);
    setError(null);
    setClips([]);
    try {
      await api.deleteSource(id, source.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove video");
    } finally {
      setBusy(false);
    }
  }

  function onInput(event: FormEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (file) void importFile(file);
  }

  async function removeProject() {
    if (!project) return;
    const ok = window.confirm(`Delete “${project.name}”? This cannot be undone.`);
    if (!ok) return;
    setError(null);
    try {
      await api.deleteProject(project.id);
      navigate("/projects");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete project");
    }
  }

  async function resetWatchUsage() {
    if (!window.confirm("Clear this project's API usage?")) return;
    try {
      await api.resetUsage(id);
      setUsage(await api.usage({ projectId: id }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reset usage");
    }
  }

  async function saveAndGenerate() {
    setError(null);
    try {
      await api.updateProject(id, {
        clip_count: clipCount,
        captions_enabled: captionsEnabled,
        caption_style: captionStyle,
        caption_position: "lower",
        reframe_enabled: false,
        branding: {
          handles: SOCIALS.filter((row) => socials[row.id].on).map((row) => ({
            platform: row.id,
            name: socials[row.id].name.trim(),
          })),
          custom_name: customName.trim(),
          footer: footerMode,
          vibes: wantedVibes,
          brief: brief.trim(),
        },
      });
      const started = await api.generate(id);
      setClips([]);
      setSelected(new Set());
      setJob(started);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start");
    }
  }

  async function stopGenerate() {
    setError(null);
    try {
      const stoppedJob = await api.stopGenerate(id);
      setJob(stoppedJob);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not stop");
    }
  }

  function toggleClip(clip: Clip, checked: boolean) {
    setSelected((current) => {
      const next = new Set(current);
      if (checked) next.add(clip.id);
      else next.delete(clip.id);
      return next;
    });
  }

  const readyClips = clips.filter((clip) => clip.has_file);
  const allSelected = readyClips.length > 0 && readyClips.every((clip) => selected.has(clip.id));

  function toggleAll(checked: boolean) {
    setSelected(checked ? new Set(readyClips.map((clip) => clip.id)) : new Set());
  }

  async function bulkDownload() {
    const ids = readyClips.filter((clip) => selected.has(clip.id)).map((clip) => clip.id);
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
    const ok = window.confirm(`Delete ${ids.length} clip${ids.length === 1 ? "" : "s"} forever?`);
    if (!ok) return;
    document.querySelectorAll<HTMLVideoElement>(".clip-tile video").forEach((video) => {
      video.pause();
      video.removeAttribute("src");
      video.load();
    });
    setError(null);
    try {
      await api.deleteClips(ids);
      setClips((rows) => rows.filter((row) => !selected.has(row.id)));
      setSelected(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete clips");
    }
  }

  if (!Number.isFinite(id)) {
    return <p className="error">Invalid project.</p>;
  }

  const hasSource = loaded && sources.length > 0;
  const showDropzone = loaded && sources.length === 0;
  const generating = Boolean(job && !["COMPLETED", "FAILED", "CANCELLED"].includes(job.status));
  const failed = job?.status === "FAILED";
  const stopped = job?.status === "CANCELLED";
  const done = job?.status === "COMPLETED";
  const showSetup = hasSource && !generating;
  const chosen = readyClips.filter((clip) => selected.has(clip.id)).length;

  return (
    <section className={watchApi ? "workbench with-api-dock" : "workbench"}>
      <p>
        <Link to="/projects">← Projects</Link>
      </p>
      <div className="workbench-head">
        <h1>{project?.name ?? "Project"}</h1>
        {project ? (
          <div className="workbench-actions">
            {hasSource ? (
              <label className={busy || generating ? "file-button file-button-inline is-disabled" : "file-button file-button-inline"}>
                <input
                  type="file"
                  accept="video/*,.mp4,.mov,.mkv,.webm,.m4v,.avi"
                  onChange={onInput}
                  disabled={busy || generating}
                />
                {busy ? "Importing…" : "Replace"}
              </label>
            ) : null}
            <button
              type="button"
              className="btn-quiet"
              aria-pressed={watchApi}
              onClick={() => setWatchApi((open) => !open)}
            >
              {watchApi ? "Hide API" : "Watch API"}
            </button>
            <button type="button" className="btn-danger" onClick={() => void removeProject()} disabled={generating}>
              Delete project
            </button>
          </div>
        ) : null}
      </div>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {notice ? <p className="notice" role="status">{notice}</p> : null}

      {showDropzone ? (
        <div
          className={dragOver ? "dropzone active" : "dropzone"}
          onDragOver={(e) => {
            e.preventDefault();
            if (!busy && !generating) setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files[0];
            if (file && !busy && !generating) void importFile(file);
          }}
        >
          <p>{busy ? "Importing…" : "Drop a video or choose a file"}</p>
          <label className="file-button">
            <input type="file" accept="video/*,.mp4,.mov,.mkv,.webm,.m4v,.avi" onChange={onInput} disabled={busy || generating} />
            Choose file
          </label>
        </div>
      ) : null}

      {sources.map((source) => (
        <article key={source.id} className="card source-card">
          {source.thumbnail_url ? <img src={source.thumbnail_url} alt="" width={160} height={90} /> : null}
          <div>
            <p>{fileName(source.file_path)}</p>
            <p className="meta">
              {source.width}×{source.height} · {formatDuration(source.duration_seconds)}
              {source.size_bytes != null ? ` · ${formatBytes(source.size_bytes)}` : ""}
            </p>
            <button type="button" className="btn-danger" onClick={() => void removeSource(source)} disabled={busy || generating}>
              Delete
            </button>
          </div>
        </article>
      ))}

      {showSetup ? (
        <fieldset className="panel">
          <legend className="meta">Options</legend>
          <div className="options-bar">
            <label>
              Clips
              <select
                value={clipCount == null ? "all" : String(clipCount)}
                onChange={(e) => setClipCount(e.target.value === "all" ? null : Number(e.target.value))}
              >
                <option value="all">All strong clips</option>
                {CLIP_COUNTS.map((n) => (
                  <option key={n} value={n}>
                    At most {n}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Captions
              <select value={captionsEnabled ? "on" : "off"} onChange={(e) => setCaptionsEnabled(e.target.value === "on")}>
                <option value="on">Burned in</option>
                <option value="off">None</option>
              </select>
            </label>
            <label>
              Caption style
              <select value={captionStyle} onChange={(e) => setCaptionStyle(e.target.value)} disabled={!captionsEnabled}>
                {CAPTION_STYLES.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Edit note
              <input
                value={brief}
                maxLength={280}
                placeholder="fast, funny, start on the money, cut the ums"
                onChange={(e) => setBrief(e.target.value)}
              />
            </label>
            <button type="button" className="generate" onClick={() => void saveAndGenerate()}>
              Generate
            </button>
          </div>
          <VibeChips
            value={wantedVibes}
            onChange={setWantedVibes}
            label="Kinds to find"
            hint="Tick kinds to hunt. Several is fine. Mixed clips can be more than one of these. None ticked means all."
          />
          <div className="social-filters" role="group" aria-label="On-clip socials">
            <div className="footer-mode">
              <button
                type="button"
                className={footerMode === "socials" ? "usage-provider on" : "usage-provider"}
                aria-pressed={footerMode === "socials"}
                onClick={() => setFooterMode("socials")}
              >
                Socials
              </button>
              <button
                type="button"
                className={footerMode === "picture" ? "usage-provider on" : "usage-provider"}
                aria-pressed={footerMode === "picture"}
                onClick={() => setFooterMode("picture")}
              >
                Picture
              </button>
            </div>
            {footerMode === "socials"
              ? SOCIALS.map((row) => (
                  <div key={row.id} className={socials[row.id].on ? "social-filter on" : "social-filter"}>
                    <input
                      type="checkbox"
                      checked={socials[row.id].on}
                      aria-label={row.label}
                      onChange={(e) =>
                        setSocials((current) => ({
                          ...current,
                          [row.id]: { ...current[row.id], on: e.target.checked },
                        }))
                      }
                    />
                    <img src={`/socials/${row.id}.png`} alt="" width={18} height={18} />
                    <input
                      type="text"
                      value={socials[row.id].name}
                      placeholder={row.label}
                      aria-label={`${row.label} handle`}
                      disabled={!socials[row.id].on}
                      onChange={(e) =>
                        setSocials((current) => ({
                          ...current,
                          [row.id]: { ...current[row.id], name: e.target.value },
                        }))
                      }
                    />
                  </div>
                ))
              : (
              <div className="social-filter custom">
                {customLogoUrl ? <img src={customLogoUrl} alt="" width={18} height={18} /> : <span className="social-filter-mark" aria-hidden="true" />}
                <span className="social-filter-hint">Fills the gap under the caption</span>
                <label className="file-button">
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                    onChange={(event) => {
                      const file = event.currentTarget.files?.[0];
                      event.currentTarget.value = "";
                      if (!file) return;
                      void api
                        .uploadLogo(id, file)
                        .then((updated) => {
                          setCustomLogoUrl(updated.custom_logo_url || null);
                          setFooterMode("picture");
                        })
                        .catch((err: Error) => setError(err.message));
                    }}
                  />
                  Picture
                </label>
                {customLogoUrl ? (
                  <button
                    type="button"
                    className="btn-quiet"
                    onClick={() => {
                      void api
                        .deleteLogo(id)
                        .then(() => setCustomLogoUrl(null))
                        .catch((err: Error) => setError(err.message));
                    }}
                  >
                    Remove
                  </button>
                ) : null}
              </div>
            )}
          </div>
        </fieldset>
      ) : null}

      {generating ? (
        <div className="loader loader-generate" role="status" aria-live="polite">
          <LoaderDots />
          <p>{shortJobLabel(job?.status || "", job?.stage_message)}</p>
          <p className="loader-count">
            {readyClips.length} clip{readyClips.length === 1 ? "" : "s"} ready
          </p>
          <button type="button" className="btn-danger" onClick={() => void stopGenerate()}>
            Stop
          </button>
        </div>
      ) : null}

      {readyClips.length > 0 ? (
        <>
          <div className="clip-toolbar">
            <label className="select-all">
              <input type="checkbox" checked={allSelected} onChange={(e) => toggleAll(e.target.checked)} />
              Select all
            </label>
            <p className="meta">{chosen} selected</p>
            <button
              type="button"
              className="btn-quiet"
              disabled={chosen === 0}
              title="Saves into this project's downloads folder"
              onClick={() => void bulkDownload()}
            >
              Download
            </button>
            <button
              type="button"
              className="btn-quiet"
              disabled={chosen === 0}
              onClick={() => {
                const rows = readyClips.filter((clip) => selected.has(clip.id));
                void copyText(rows.map((clip) => clip.title || clip.filename || "").filter(Boolean).join("\n")).then((ok) => {
                  if (!ok) return;
                  setCopiedAll(true);
                  window.setTimeout(() => setCopiedAll(false), 1500);
                });
              }}
            >
              {copiedAll ? "Copied" : "Copy hooks"}
            </button>
            <button type="button" className="btn-danger" disabled={chosen === 0} onClick={() => void bulkDelete()}>
              Delete
            </button>
          </div>
          <ul className="clip-grid">
            {readyClips.map((clip) => (
              <ClipPlayer key={clip.id} clip={clip} selected={selected.has(clip.id)} onToggle={toggleClip} />
            ))}
          </ul>
        </>
      ) : null}

      {watchApi ? (
        usage ? (
          <ApiMonitor data={usage} variant="dock" projectId={id} onReset={() => void resetWatchUsage()} />
        ) : (
          <aside className="api-dock" aria-label="API usage">
            <div className="usage-card-head">
              <p className="usage-live idle">Waiting for API calls…</p>
              <button type="button" className="btn-quiet" onClick={() => void resetWatchUsage()}>
                Reset
              </button>
            </div>
          </aside>
        )
      ) : null}

      {failed && !generating ? (
        <p className="error" role="alert">
          {job?.error_message || job?.stage_message || "Generate failed"}
        </p>
      ) : null}

      {stopped && !generating ? <p className="meta">Generate stopped.</p> : null}

      {done && readyClips.length === 0 && !generating ? <p className="empty">No usable clip moments found.</p> : null}
    </section>
  );
}
