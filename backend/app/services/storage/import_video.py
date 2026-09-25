from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ProcessingJob, Project, SourceVideo
from app.services.storage.paths import (
    media_url,
    project_original_dir,
    project_thumb_dir,
    safe_filename,
)
from app.services.storage.purge import clear_analysis, wipe_clips_matching_hash, wipe_project_clips
from app.services.video.ffmpeg import (
    VideoProcessingError,
    copy_if_needed,
    probe_video,
    sha256_file,
    validate_suffix,
    write_thumbnail,
)

ACTIVE_JOBS = {
    "QUEUED",
    "ANALYZING",
    "TRANSCRIBING",
    "DISCOVERING",
    "EXPANDING",
    "VALIDATING",
    "SELECTING",
    "REFINING",
    "GENERATING_CANDIDATES",
    "SCORING",
    "RENDERING",
}


def hide_current_project_clips(db: Session, project: Project) -> int:
    """Hard-delete this project's clips and sidecars so Generate cannot reuse old cuts."""
    return wipe_project_clips(db, project)


def _stop_project_job(db: Session, project_id: int, message: str) -> None:
    from app.services.jobs.control import live_job_id, request_cancel

    jid = live_job_id()
    if jid is None:
        return
    job = db.get(ProcessingJob, jid)
    if job is not None and job.project_id == project_id:
        request_cancel(jid)
        job.status = "CANCELLED"
        job.stage_message = message


def _drop_other_sources(db: Session, project: Project, keep_id: int) -> None:
    others = list(
        db.scalars(
            select(SourceVideo).where(SourceVideo.project_id == project.id, SourceVideo.id != keep_id)
        )
    )
    for row in others:
        file_path = Path(row.file_path) if row.file_path else None
        thumb_path = Path(row.thumbnail_path) if row.thumbnail_path else None
        source_id = row.id
        db.delete(row)
        db.flush()
        _unlink_if_orphan(db, file_path, exclude_source_id=source_id)
        _unlink_if_orphan(db, thumb_path, exclude_source_id=source_id)


class DuplicateSourceError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class SourceBusyError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def _path_in_use(db: Session, path: Path | None, *, exclude_source_id: int | None = None) -> bool:
    if path is None:
        return False
    needle = str(path)
    rows = list(
        db.scalars(
            select(SourceVideo).where(
                (SourceVideo.file_path == needle) | (SourceVideo.thumbnail_path == needle)
            )
        )
    )
    return any(row.id != exclude_source_id for row in rows)


def _unlink_if_orphan(db: Session, path: Path | None, *, exclude_source_id: int | None = None) -> None:
    if path is None:
        return
    resolved = Path(path)
    if not resolved.is_file():
        return
    if _path_in_use(db, resolved, exclude_source_id=exclude_source_id):
        return
    resolved.unlink(missing_ok=True)


def project_has_active_job(db: Session, project_id: int) -> bool:
    from app.services.jobs.control import live_job_id

    jid = live_job_id()
    if jid is None:
        return False
    job = db.get(ProcessingJob, jid)
    return job is not None and job.project_id == project_id and job.status in ACTIVE_JOBS


def delete_source_record(db: Session, record: SourceVideo) -> None:
    _stop_project_job(db, record.project_id, "Stopped because the video was removed")
    file_path = Path(record.file_path) if record.file_path else None
    thumb_path = Path(record.thumbnail_path) if record.thumbnail_path else None
    source_id = record.id
    project_id = record.project_id
    file_hash = record.file_hash
    project = db.get(Project, project_id)
    if project is not None:
        wipe_project_clips(db, project)
        wipe_clips_matching_hash(db, file_hash)
        clear_analysis(project)
    db.delete(record)
    db.flush()
    _unlink_if_orphan(db, file_path, exclude_source_id=source_id)
    _unlink_if_orphan(db, thumb_path, exclude_source_id=source_id)
    remaining = db.scalar(select(SourceVideo.id).where(SourceVideo.project_id == project_id))
    project = db.get(Project, project_id)
    if project is not None and remaining is None:
        project.status = "draft"
    db.commit()


def import_video_file(db: Session, project: Project, source_path: Path, original_name: str) -> tuple[SourceVideo, bool]:
    suffix = validate_suffix(original_name)
    if not source_path.is_file():
        raise VideoProcessingError("Uploaded file is missing on disk.")

    file_hash = sha256_file(source_path)
    existing_on_project = db.scalar(
        select(SourceVideo).where(SourceVideo.project_id == project.id, SourceVideo.file_hash == file_hash)
    )
    if existing_on_project is not None:
        stored = Path(existing_on_project.file_path) if existing_on_project.file_path else None
        if stored is not None and stored.is_file():
            source_path.unlink(missing_ok=True)
            _stop_project_job(db, project.id, "Stopped because the video was replaced")
            _drop_other_sources(db, project, existing_on_project.id)
            wipe_project_clips(db, project)
            wipe_clips_matching_hash(db, file_hash)
            clear_analysis(project, keep_hash=file_hash)
            db.commit()
            db.refresh(existing_on_project)
            return existing_on_project, True
        db.delete(existing_on_project)
        db.flush()
    _stop_project_job(db, project.id, "Stopped because the video was replaced")

    original_dir = project_original_dir(project)
    thumb_dir = project_thumb_dir(project)
    dest = original_dir / safe_filename(original_name)
    if dest.suffix.lower() != suffix:
        dest = dest.with_suffix(suffix)

    if dest.exists() and sha256_file(dest) != file_hash:
        dest = original_dir / f"{dest.stem}_{file_hash[:8]}{suffix}"
    stored_path = copy_if_needed(source_path, dest)
    if source_path.resolve() != stored_path.resolve():
        source_path.unlink(missing_ok=True)

    probe = probe_video(stored_path)
    thumb_path = write_thumbnail(stored_path, thumb_dir / f"{file_hash[:16]}.jpg")

    record = SourceVideo(
        project_id=project.id,
        file_path=str(stored_path),
        file_hash=file_hash,
        duration_seconds=probe["duration_seconds"],
        width=probe["width"],
        height=probe["height"],
        thumbnail_path=str(thumb_path),
    )
    db.add(record)
    db.flush()
    _drop_other_sources(db, project, record.id)
    wipe_project_clips(db, project)
    wipe_clips_matching_hash(db, file_hash)
    clear_analysis(project, keep_hash=file_hash)
    project.status = "ready"
    db.commit()
    db.refresh(record)
    return record, False


def source_to_dict(record: SourceVideo, reused: bool = False) -> dict:
    path = Path(record.file_path) if record.file_path else None
    size_bytes = path.stat().st_size if path is not None and path.is_file() else None
    return {
        "id": record.id,
        "project_id": record.project_id,
        "file_path": record.file_path,
        "file_hash": record.file_hash,
        "duration_seconds": record.duration_seconds,
        "width": record.width,
        "height": record.height,
        "size_bytes": size_bytes,
        "thumbnail_url": media_url(record.thumbnail_path),
        "reused": reused,
        "created_at": record.created_at,
    }
