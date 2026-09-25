from pathlib import Path
from shutil import rmtree
from stat import S_IWRITE
from time import sleep

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import MEDIA_DIR, settings
from app.models.entities import ActivityEvent, AnalysisRun, ApiUsageEvent, Clip, ClipTag, ProcessingJob, Project, SourceVideo
from app.services.storage.paths import library_clips_dir, project_analysis_dir, project_clips_dir
from app.services.storage.workspace import LIBRARY_VAULT_STATUS


def _force_rmtree(folder: Path) -> None:
    if not folder.exists():
        return

    def _onexc(_func, path: str, _exc: BaseException) -> None:
        target = Path(path)
        try:
            target.chmod(S_IWRITE)
            if target.is_file() or target.is_symlink():
                target.unlink(missing_ok=True)
            elif target.is_dir():
                rmtree(target, ignore_errors=True)
        except OSError:
            return

    rmtree(folder, onexc=_onexc)
    if folder.exists():
        rmtree(folder, ignore_errors=True)


def _unlink(path: str | Path | None) -> None:
    if not path:
        return
    file_path = Path(path)
    for target in (file_path, file_path.with_suffix(".srt"), file_path.with_suffix(".ass")):
        for _ in range(6):
            try:
                target.unlink(missing_ok=True)
                break
            except PermissionError:
                sleep(0.25)


def unlink_clip_disk(clip: Clip) -> None:
    """Delete the MP4 plus hook/caption sidecars. Delete means delete."""
    _unlink(clip.file_path)
    _unlink(clip.thumbnail_path)
    parents: list[Path] = []
    if clip.file_path:
        parents.append(Path(clip.file_path).parent)
    for folder in parents:
        _unlink(folder / f"clip_{clip.id}.ass")
        _unlink(folder / f"clip_{clip.id}_hook.txt")


def _delete_clip_rows(db: Session, clips: list[Clip]) -> int:
    ids = [clip.id for clip in clips]
    if ids:
        db.execute(sa_delete(ClipTag).where(ClipTag.clip_id.in_(ids)))
    for clip in clips:
        unlink_clip_disk(clip)
        db.delete(clip)
    return len(clips)


def wipe_project_clips(db: Session, project: Project) -> int:
    """Erase every clip row and file for this project, including leftover sidecars."""
    clips = list(db.scalars(select(Clip).where(Clip.project_id == project.id)))
    count = _delete_clip_rows(db, clips)
    folder = project_clips_dir(project)
    if folder.is_dir():
        for path in folder.iterdir():
            if path.is_file():
                path.unlink(missing_ok=True)
    return count


def wipe_clips_matching_hash(db: Session, file_hash: str) -> int:
    needle = (file_hash or "").strip()
    if not needle:
        return 0
    clips = list(db.scalars(select(Clip).where(Clip.viral_signals.contains(needle))))
    return _delete_clip_rows(db, clips)


def clear_analysis(project: Project, *, keep_hash: str | None = None) -> None:
    folder = project_analysis_dir(project)
    if not folder.is_dir():
        return
    keep = (keep_hash or "").strip()
    for path in folder.iterdir():
        if not path.is_file():
            continue
        if keep and keep in path.name:
            continue
        path.unlink(missing_ok=True)


def clear_uploaded_media(db: Session) -> dict[str, int]:
    """Delete every clip, source video, and analysis file. Keep accounts, projects, and settings."""
    clips = list(db.scalars(select(Clip)))
    n_clips = _delete_clip_rows(db, clips)
    sources = list(db.scalars(select(SourceVideo)))
    for source in sources:
        _unlink(source.file_path)
        _unlink(source.thumbnail_path)
        db.delete(source)
    jobs = list(db.scalars(select(ProcessingJob)))
    for job in jobs:
        db.delete(job)
    db.execute(sa_delete(AnalysisRun))
    projects = list(db.scalars(select(Project)))
    for project in projects:
        if project.status != LIBRARY_VAULT_STATUS:
            project.status = "draft"
        folder = Path(project.folder_path) if project.folder_path else None
        if folder is not None and folder.is_dir():
            for sub in ("clips", "original", "thumbnails", "analysis", "downloads"):
                _force_rmtree(folder / sub)
            clear_analysis(project)
    db.commit()
    _force_rmtree(library_clips_dir())
    leftover = Path(settings.projects_dir)
    if leftover.is_dir():
        for child in leftover.iterdir():
            if child.is_dir() and child.name.isdigit():
                for sub in ("clips", "original", "thumbnails", "analysis", "downloads"):
                    _force_rmtree(child / sub)
    accounts_media = MEDIA_DIR / "accounts"
    if accounts_media.is_dir():
        for account_dir in accounts_media.iterdir():
            projects_dir = account_dir / "projects"
            if not projects_dir.is_dir():
                continue
            for project_dir in projects_dir.iterdir():
                for sub in ("clips", "original", "thumbnails", "analysis", "downloads"):
                    _force_rmtree(project_dir / sub)
    return {"clips": n_clips, "sources": len(sources), "jobs": len(jobs), "projects": len(projects)}


def purge_project(db: Session, project: Project, *, keep_clips: bool = False) -> None:
    """Delete the project, its source video, clips, hooks, and folders. keep_clips is ignored."""
    del keep_clips
    project_id = project.id
    account_id = project.account_id
    folder = Path(project.folder_path) if project.folder_path else None
    is_vault = project.status == LIBRARY_VAULT_STATUS
    hashes = [
        row.file_hash
        for row in db.scalars(select(SourceVideo).where(SourceVideo.project_id == project_id))
        if row.file_hash
    ]
    wipe_project_clips(db, project)
    for file_hash in hashes:
        wipe_clips_matching_hash(db, file_hash)
    db.execute(sa_delete(ProcessingJob).where(ProcessingJob.project_id == project_id))
    db.execute(sa_delete(AnalysisRun).where(AnalysisRun.project_id == project_id))
    db.execute(sa_delete(ApiUsageEvent).where(ApiUsageEvent.project_id == project_id))
    db.execute(sa_delete(ActivityEvent).where(ActivityEvent.project_id == project_id))
    for source in list(db.scalars(select(SourceVideo).where(SourceVideo.project_id == project_id))):
        _unlink(source.file_path)
        _unlink(source.thumbnail_path)
        db.delete(source)
    db.delete(project)
    db.commit()
    if folder is not None and folder.resolve() != library_clips_dir().parent.resolve():
        _force_rmtree(folder)
    media = MEDIA_DIR / "accounts" / str(account_id) / "projects" / str(project_id)
    _force_rmtree(media)
    leftover_root = Path(settings.projects_dir)
    if leftover_root.is_dir() and not is_vault:
        for leftover in leftover_root.glob(f"{project_id:04d}_*"):
            _force_rmtree(leftover)
