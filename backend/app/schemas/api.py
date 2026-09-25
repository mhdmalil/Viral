from datetime import datetime

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    platform: str = "tiktok"
    handle: str = ""
    description: str = ""
    content_strategy: str = "mixed"
    default_clip_count: int = Field(default=10, ge=1, le=100)
    default_duration_min: int = Field(default=10, ge=5, le=180)
    default_duration_max: int = Field(default=20, ge=5, le=180)
    default_format: str = "9:16"
    default_resolution: str = "1080x1920"
    default_caption_style: str = "classic"
    default_caption_position: str = "lower"
    default_hashtags: str = ""


class AccountUpdate(BaseModel):
    name: str | None = None
    platform: str | None = None
    handle: str | None = None
    description: str | None = None
    content_strategy: str | None = None
    default_clip_count: int | None = Field(default=None, ge=1, le=100)
    default_duration_min: int | None = None
    default_duration_max: int | None = None
    default_format: str | None = None
    default_resolution: str | None = None
    default_caption_style: str | None = None
    default_caption_position: str | None = None
    default_hashtags: str | None = None


class AccountOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    platform: str
    handle: str
    description: str
    content_strategy: str
    default_clip_count: int
    default_duration_min: int
    default_duration_max: int
    default_format: str
    default_resolution: str
    default_caption_style: str
    default_caption_position: str
    default_hashtags: str
    created_at: datetime


class ProjectCreate(BaseModel):
    account_id: int | None = None
    name: str = Field(min_length=1, max_length=200)
    clip_count: int | None = Field(default=None, ge=1, le=100)
    strategy: str | None = None
    captions_enabled: bool = True
    caption_style: str | None = None
    caption_position: str | None = None
    reframe_enabled: bool = False
    branding: dict | None = None


class ProjectUpdate(BaseModel):
    clip_count: int | None = Field(default=None, ge=1, le=100)
    strategy: str | None = None
    captions_enabled: bool | None = None
    caption_style: str | None = None
    caption_position: str | None = None
    reframe_enabled: bool | None = None
    branding: dict | None = None


class ProjectOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    account_id: int
    name: str
    status: str
    clip_count: int | None
    strategy: str | None
    captions_enabled: int
    caption_style: str
    caption_position: str
    folder_path: str | None = None
    ready_clips: int = 0
    reframe_enabled: int = 0
    branding: dict = Field(default_factory=dict)
    custom_logo_url: str | None = None
    created_at: datetime


class ClipIdsIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=50)
    open_folder: bool = True


class DownloadOut(BaseModel):
    folder: str
    files: list[str]
    zip_name: str
    count: int
    opened: bool = False


class ClipTagIn(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=12)


class ClipOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    account_id: int
    project_id: int | None = None
    project_name: str = ""
    title: str
    duration: float | None
    start_time: float | None = None
    end_time: float | None = None
    quality_score: float | None
    status: str
    favorite: int
    has_file: bool = False
    tags: list[str] = Field(default_factory=list)
    hook_at: float | None = None
    vibe: str | None = None
    vibes: list[str] = Field(default_factory=list)
    filename: str | None = None
    clip_index: int | None = None
    created_at: datetime


class DashboardProject(BaseModel):
    id: int
    name: str
    status: str
    ready_clips: int
    created_at: datetime


class DashboardActivity(BaseModel):
    id: str
    project_id: int
    project_name: str
    status: str
    stage_message: str
    created_at: datetime


class DashboardOut(BaseModel):
    project_count: int
    clip_count: int
    download_count: int
    recent_projects: list[DashboardProject]
    recent_activity: list[DashboardActivity]


class JobOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    project_id: int
    status: str
    stage_message: str
    progress: int
    error_message: str | None
    created_at: datetime
    source_id: int | None = None


class SourceVideoOut(BaseModel):
    id: int
    project_id: int
    file_path: str
    file_hash: str
    duration_seconds: float | None
    width: int | None
    height: int | None
    size_bytes: int | None = None
    thumbnail_url: str | None
    reused: bool = False
    created_at: datetime


class AppSettingsOut(BaseModel):
    host: str
    bind_is_loopback: bool
    quality_threshold: float
    ai_provider_configured: bool
    ai_provider: str
    ai_model: str
    openrouter_configured: bool
    gemini_configured: bool
    groq_configured: bool
    whisper_model: str
    whisper_device: str
    transcription_backend: str
