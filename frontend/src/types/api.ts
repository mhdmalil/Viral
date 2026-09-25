export type Health = { status: string; service: string };

export type Account = {
  id: number;
  name: string;
  platform: string;
  handle: string;
  description: string;
  content_strategy: string;
  default_clip_count: number;
  created_at: string;
};

export type Project = {
  id: number;
  account_id: number;
  name: string;
  status: string;
  clip_count: number | null;
  strategy: string | null;
  captions_enabled: number;
  caption_style: string;
  caption_position: string;
  folder_path: string | null;
  ready_clips: number;
  reframe_enabled: number;
  branding?: {
    handles?: { platform: string; name: string }[];
    custom_name?: string;
    custom_logo_path?: string | null;
    footer?: "socials" | "picture";
    vibes?: string[];
  };
  custom_logo_url?: string | null;
  created_at: string;
};

export type Clip = {
  id: number;
  account_id: number;
  project_id: number | null;
  project_name?: string;
  title: string;
  duration: number | null;
  start_time: number | null;
  end_time: number | null;
  quality_score: number | null;
  status: string;
  favorite: number;
  has_file: boolean;
  tags?: string[];
  hook_at?: number | null;
  vibe?: string | null;
  vibes?: string[];
  filename?: string | null;
  clip_index?: number | null;
  created_at: string;
};

export type SourceVideo = {
  id: number;
  project_id: number;
  file_path: string;
  file_hash: string;
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  size_bytes: number | null;
  thumbnail_url: string | null;
  reused: boolean;
  created_at: string;
};

export type Job = {
  id: number;
  project_id: number;
  status: string;
  stage_message: string;
  progress: number;
  error_message: string | null;
  created_at: string;
};

export type Dashboard = {
  project_count: number;
  clip_count: number;
  download_count: number;
  recent_projects: { id: number; name: string; status: string; ready_clips: number; created_at: string }[];
  recent_activity: {
    id: string;
    project_id: number;
    project_name: string;
    status: string;
    stage_message: string;
    created_at: string;
  }[];
};

export type UsageLive = {
  provider: string | null;
  model: string | null;
  job_id: number | null;
  project_id: number | null;
  project_name: string | null;
  outcome: string | null;
};

export type UsageLog = {
  id: number;
  created_at: string;
  provider: string;
  model: string;
  outcome: string;
  http_status: number;
  latency_ms: number;
  remaining: number | null;
  limit: number | null;
  job_id: number | null;
  project_id: number | null;
};

export type UsageReport = {
  live: UsageLive;
  totals: { requests: number; ok: number; limited: number; errors: number; avg_ms: number };
  providers: {
    provider: string;
    requests: number;
    ok: number;
    limited: number;
    errors: number;
    remaining: number | null;
    limit: number | null;
    last_model: string;
  }[];
  models: { provider: string; model: string; requests: number; ok: number; limited: number; avg_ms: number }[];
  series: { at?: string; label: string; requests: number; ok: number; limited: number }[];
  logs: UsageLog[];
};

export type AppSettings = {
  host: string;
  bind_is_loopback: boolean;
  quality_threshold: number;
  ai_provider_configured: boolean;
  ai_provider: string;
  ai_model: string;
  openrouter_configured: boolean;
  gemini_configured: boolean;
  groq_configured: boolean;
  whisper_model: string;
  whisper_device: string;
  transcription_backend: string;
};
