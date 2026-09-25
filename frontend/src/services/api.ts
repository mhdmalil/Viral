import type { Account, AppSettings, Clip, Dashboard, Job, Project, SourceVideo, UsageReport } from "../types/api";

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    try {
      const payload = JSON.parse(text) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        throw new Error(payload.detail);
      }
    } catch (err) {
      if (err instanceof Error && err.name !== "SyntaxError") {
        throw err;
      }
    }
    throw new Error(text || response.statusText);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  usage: (opts?: { provider?: string; projectId?: number }) => {
    const params = new URLSearchParams();
    if (opts?.provider) params.set("provider", opts.provider);
    if (opts?.projectId) params.set("project_id", String(opts.projectId));
    const query = params.toString();
    return fetch(`/api/usage${query ? `?${query}` : ""}`).then((r) => parse<UsageReport>(r));
  },
  resetUsage: (projectId?: number) => {
    const query = projectId != null ? `?project_id=${projectId}` : "";
    return fetch(`/api/usage${query}`, { method: "DELETE" }).then((r) => parse<void>(r));
  },
  dashboard: () => fetch("/api/dashboard").then((r) => parse<Dashboard>(r)),
  settings: () => fetch("/api/settings").then((r) => parse<AppSettings>(r)),
  accounts: () => fetch("/api/accounts").then((r) => parse<Account[]>(r)),
  createAccount: (body: { name: string; platform: string; handle: string; content_strategy: string; default_clip_count: number }) =>
    fetch("/api/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => parse<Account>(r)),
  projects: (accountId?: number) => {
    const q = accountId ? `?account_id=${accountId}` : "";
    return fetch(`/api/projects${q}`).then((r) => parse<Project[]>(r));
  },
  createProject: (body: { name: string; clip_count?: number; account_id?: number }) =>
    fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => parse<Project>(r)),
  deleteProject: (id: number) => fetch(`/api/projects/${id}`, { method: "DELETE" }).then((r) => parse<void>(r)),
  deleteSource: (projectId: number, sourceId: number) =>
    fetch(`/api/projects/${projectId}/source/${sourceId}`, { method: "DELETE" }).then((r) => parse<void>(r)),
  deleteClip: (clipId: number) => fetch(`/api/clips/${clipId}`, { method: "DELETE" }).then((r) => parse<void>(r)),
  deleteClips: (ids: number[]) =>
    fetch("/api/clips/bulk-delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    }).then((r) => parse<void>(r)),
  removeClipsFromProject: (ids: number[]) =>
    fetch("/api/clips/bulk-remove", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    }).then((r) => parse<void>(r)),
  downloadClips: (ids: number[]) =>
    fetch("/api/clips/bulk-download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids, open_folder: true }),
    }).then((r) => parse<{ folder: string; files: string[]; zip_name: string; count: number; opened: boolean }>(r)),
  clips: (opts?: { projectId?: number; q?: string; tag?: string; ready?: boolean; inProject?: boolean; vibes?: string[] }) => {
    const params = new URLSearchParams();
    if (opts?.projectId) params.set("project_id", String(opts.projectId));
    if (opts?.q) params.set("q", opts.q);
    if (opts?.tag) params.set("tag", opts.tag);
    if (opts?.ready != null) params.set("ready", opts.ready ? "true" : "false");
    if (opts?.inProject) params.set("in_project", "true");
    if (opts?.vibes && opts.vibes.length) params.set("vibes", opts.vibes.join(","));
    const query = params.toString();
    return fetch(`/api/clips${query ? `?${query}` : ""}`).then((r) => parse<Clip[]>(r));
  },
  tags: () => fetch("/api/tags").then((r) => parse<string[]>(r)),
  updateClipTags: (id: number, tags: string[]) =>
    fetch(`/api/clips/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tags }),
    }).then((r) => parse<Clip>(r)),
  project: (id: number) => fetch(`/api/projects/${id}`).then((r) => parse<Project>(r)),
  updateProject: (
    id: number,
    body: {
      clip_count?: number | null;
      strategy?: string;
      captions_enabled?: boolean;
      caption_style?: string;
      caption_position?: string;
      reframe_enabled?: boolean;
      branding?: {
        handles?: { platform: string; name: string }[];
        custom_name?: string;
        footer?: "socials" | "picture";
        vibes?: string[];
      };
    },
  ) =>
    fetch(`/api/projects/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => parse<Project>(r)),
  latestJob: async (projectId: number) => {
    const response = await fetch(`/api/projects/${projectId}/job`);
    if (response.status === 204) return null;
    return parse<Job>(response);
  },
  generate: (projectId: number) =>
    fetch(`/api/projects/${projectId}/generate`, { method: "POST", keepalive: true }).then((r) => parse<Job>(r)),
  stopGenerate: (projectId: number) =>
    fetch(`/api/projects/${projectId}/generate/stop`, { method: "POST" }).then((r) => parse<Job>(r)),
  sources: (projectId: number) => fetch(`/api/projects/${projectId}/source`).then((r) => parse<SourceVideo[]>(r)),
  uploadSource: async (projectId: number, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return parse<SourceVideo>(
      await fetch(`/api/projects/${projectId}/source`, {
        method: "POST",
        body,
      }),
    );
  },
  uploadLogo: async (projectId: number, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return parse<Project>(await fetch(`/api/projects/${projectId}/logo`, { method: "POST", body }));
  },
  deleteLogo: (projectId: number) =>
    fetch(`/api/projects/${projectId}/logo`, { method: "DELETE" }).then((r) => parse<Project>(r)),
};
