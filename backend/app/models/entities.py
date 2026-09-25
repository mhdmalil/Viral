from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    platform: Mapped[str] = mapped_column(String(50), default="tiktok")
    handle: Mapped[str] = mapped_column(String(200), default="")
    profile_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    content_strategy: Mapped[str] = mapped_column(String(80), default="mixed")
    default_clip_count: Mapped[int] = mapped_column(Integer, default=10)
    default_duration_min: Mapped[int] = mapped_column(Integer, default=10)
    default_duration_max: Mapped[int] = mapped_column(Integer, default=20)
    default_format: Mapped[str] = mapped_column(String(20), default="9:16")
    default_resolution: Mapped[str] = mapped_column(String(20), default="1080x1920")
    default_caption_style: Mapped[str] = mapped_column(String(40), default="classic")
    default_caption_position: Mapped[str] = mapped_column(String(40), default="lower")
    default_hashtags: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="account")
    clips: Mapped[list["Clip"]] = relationship(back_populates="account")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="draft")
    clip_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strategy: Mapped[str | None] = mapped_column(String(80), nullable=True)
    output_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    captions_enabled: Mapped[int] = mapped_column(Integer, default=1)
    caption_style: Mapped[str] = mapped_column(String(40), default="classic")
    caption_position: Mapped[str] = mapped_column(String(40), default="lower")
    folder_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reframe_enabled: Mapped[int] = mapped_column(Integer, default=0)
    branding_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    account: Mapped[Account] = relationship(back_populates="projects")
    source_videos: Mapped[list["SourceVideo"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    clips: Mapped[list["Clip"]] = relationship(back_populates="project", passive_deletes=True)
    jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class SourceVideo(Base):
    __tablename__ = "source_videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(1000))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="source_videos")


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    viral_signals: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    favorite: Mapped[int] = mapped_column(Integer, default=0)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    removed_from_project: Mapped[int] = mapped_column(Integer, default=0)
    origin_project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped[Account] = relationship(back_populates="clips")
    project: Mapped[Project] = relationship(back_populates="clips")
    tag_links: Mapped[list["ClipTag"]] = relationship(back_populates="clip", cascade="all, delete-orphan")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class ClipTag(Base):
    __tablename__ = "clip_tags"
    __table_args__ = (UniqueConstraint("clip_id", "tag_id"),)

    clip_id: Mapped[int] = mapped_column(ForeignKey("clips.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)

    clip: Mapped[Clip] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship()


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    result_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="analysis_runs")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="QUEUED")
    stage_message: Mapped[str] = mapped_column(String(300), default="")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    project: Mapped[Project] = relationship(back_populates="jobs")


class ApiUsageEvent(Base):
    __tablename__ = "api_usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(200), index=True)
    outcome: Mapped[str] = mapped_column(String(40), default="error")
    http_status: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    message: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(40), default="INFO")


class AppSetting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
