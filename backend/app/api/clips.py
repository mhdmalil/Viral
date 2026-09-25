from io import BytesIO
from pathlib import Path
from time import sleep
import json
import logging
import os
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import Clip, ClipTag, Project, SourceVideo, Tag
from app.schemas.api import ClipIdsIn, ClipOut, ClipTagIn, DownloadOut
from app.services.activity import log_activity
from app.services.ai.editorial.vibes import normalize_vibes, parse_row_vibes
from app.services.storage.paths import clip_file_stem, ensure_project_folder, project_downloads_dir
from app.services.storage.purge import unlink_clip_disk
from app.services.storage.workspace import is_library_vault

router = APIRouter(prefix="/clips", tags=["clips"])
tags_router = APIRouter(prefix="/tags", tags=["tags"])
logger = logging.getLogger(__name__)


def _normalize_tags(raw: list[str]) -> list[str]:
    seen: list[str] = []
    for item in raw:
        name = " ".join(item.strip().lower().split())
        if not name or len(name) > 40:
            continue
        if name not in seen:
            seen.append(name)
        if len(seen) >= 12:
            break
    return seen


def _tags_for(db: Session, clip_ids: list[int]) -> dict[int, list[str]]:
    if not clip_ids:
        return {}
    rows = db.execute(
        select(ClipTag.clip_id, Tag.name)
        .join(Tag, Tag.id == ClipTag.tag_id)
        .where(ClipTag.clip_id.in_(clip_ids))
        .order_by(Tag.name.asc())
    ).all()
    mapped: dict[int, list[str]] = {clip_id: [] for clip_id in clip_ids}
    for clip_id, name in rows:
        mapped.setdefault(int(clip_id), []).append(str(name))
    return mapped


def _set_tags(db: Session, clip: Clip, names: list[str]) -> list[str]:
    wanted = _normalize_tags(names)
    clip.tag_links.clear()
    db.flush()
    for name in wanted:
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        clip.tag_links.append(ClipTag(tag=tag))
    return wanted


def _signals(clip: Clip) -> dict:
    raw = clip.viral_signals
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _clip_index(clip: Clip) -> int | None:
    try:
        value = _signals(clip).get("clip_index")
        if value is None:
            return None
        index = int(value)
        return index if index > 0 else None
    except (TypeError, ValueError):
        return None


def _download_name(clip: Clip, fallback: int) -> str:
    path = Path(clip.file_path or "clip.mp4")
    index = _clip_index(clip) or fallback
    return f"{clip_file_stem(clip.title, clip.id, index)}{path.suffix or '.mp4'}"


def _hook_at(clip: Clip) -> float | None:
    try:
        value = _signals(clip).get("hook_at")
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _vibes(clip: Clip) -> list[str]:
    return parse_row_vibes(_signals(clip))


def _vibe(clip: Clip) -> str | None:
    labels = _vibes(clip)
    return labels[0] if labels else None


def workbench_allows_clip(clip: Clip, source_hash: str | None) -> bool:
    """Workbench only shows cuts from the video currently on the project."""
    if not source_hash:
        return False
    clip_hash = str(_signals(clip).get("source_hash") or "")
    return bool(clip_hash) and clip_hash == source_hash


def _to_out(clip: Clip, *, project: Project | None = None, project_name: str = "", tags: list[str] | None = None) -> ClipOut:
    has_file = bool(clip.file_path and Path(clip.file_path).is_file())
    vault = is_library_vault(project)
    label = clip.origin_project_name or project_name
    return ClipOut(
        id=clip.id,
        account_id=clip.account_id,
        project_id=None if vault else clip.project_id,
        project_name=label or "",
        title=clip.title,
        duration=clip.duration,
        start_time=clip.start_time,
        end_time=clip.end_time,
        quality_score=clip.quality_score,
        status=clip.status,
        favorite=clip.favorite,
        has_file=has_file,
        tags=tags or [],
        hook_at=_hook_at(clip),
        vibe=_vibe(clip),
        vibes=_vibes(clip),
        clip_index=_clip_index(clip),
        filename=Path(clip.file_path).name if has_file else None,
        created_at=clip.created_at,
    )


def _file_response(clip: Clip | None, *, inline: bool) -> FileResponse:
    if clip is None or not clip.file_path:
        raise HTTPException(status_code=404, detail="Clip file not found")
    path = Path(clip.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Clip file is missing on disk")
    return FileResponse(
        path,
        filename=_download_name(clip, 1) if not inline else path.name,
        media_type="video/mp4",
        content_disposition_type="inline" if inline else "attachment",
    )


def _load_clips(db: Session, ids: list[int]) -> list[Clip]:
    rows = list(db.scalars(select(Clip).where(Clip.id.in_(ids))))
    found = {row.id for row in rows}
    missing = [clip_id for clip_id in ids if clip_id not in found]
    if missing:
        raise HTTPException(status_code=404, detail="One or more clips were not found")
    by_id = {row.id: row for row in rows}
    return [by_id[clip_id] for clip_id in ids]


def _note_download(db: Session, clips: list[Clip]) -> None:
    for position, clip in enumerate(clips, start=1):
        clip.download_count = int(clip.download_count or 0) + 1
        if not clip.file_path:
            continue
        source = Path(clip.file_path)
        if not source.is_file():
            continue
        project = db.get(Project, clip.project_id)
        if project is None:
            continue
        if not project.folder_path:
            ensure_project_folder(project)
        dest_dir = project_downloads_dir(project)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / _download_name(clip, position)
        if dest.resolve() != source.resolve():
            dest.write_bytes(source.read_bytes())
    db.commit()


def _unlink_path(path: Path) -> None:
    for _ in range(6):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            sleep(0.25)
    try:
        trash = path.with_name(path.name + ".trash")
        path.replace(trash)
    except OSError:
        logger.warning("Could not remove locked clip file %s", path)


def _unlink_clip(clip: Clip) -> None:
    unlink_clip_disk(clip)


@router.get("", response_model=list[ClipOut])
def list_clips(
    account_id: int | None = None,
    project_id: int | None = None,
    q: str | None = None,
    tag: str | None = None,
    vibes: str | None = None,
    ready: bool | None = None,
    in_project: bool | None = None,
    db: Session = Depends(get_db),
) -> list[ClipOut]:
    stmt = (
        select(Clip, Project)
        .outerjoin(Project, Project.id == Clip.project_id)
        .order_by(Clip.start_time.asc(), Clip.id.asc())
    )
    if account_id is not None:
        stmt = stmt.where(Clip.account_id == account_id)
    if project_id is not None:
        stmt = stmt.where(Clip.project_id == project_id)
    if in_project is True:
        stmt = stmt.where(Clip.removed_from_project == 0)
    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        stmt = stmt.where(
            or_(
                Clip.title.ilike(like),
                Project.name.ilike(like),
                Clip.origin_project_name.ilike(like),
                Clip.ai_analysis.ilike(like),
            )
        )
    tag_name = (tag or "").strip().lower()
    if tag_name:
        stmt = stmt.where(
            Clip.id.in_(select(ClipTag.clip_id).join(Tag, Tag.id == ClipTag.tag_id).where(Tag.name == tag_name))
        )
    rows = list(db.execute(stmt).all())
    tags_map = _tags_for(db, [clip.id for clip, _project in rows])
    wanted = normalize_vibes(vibes)
    source_hash = None
    if in_project is True and project_id is not None:
        source = db.scalar(
            select(SourceVideo).where(SourceVideo.project_id == project_id).order_by(SourceVideo.id.desc())
        )
        source_hash = source.file_hash if source is not None else None
        if not source_hash:
            return []
    out: list[ClipOut] = []
    for clip, project in rows:
        if in_project is True and not workbench_allows_clip(clip, source_hash):
            continue
        item = _to_out(
            clip,
            project=project,
            project_name=project.name if project else "",
            tags=tags_map.get(clip.id, []),
        )
        if ready is True and not item.has_file:
            continue
        if ready is False and item.has_file:
            continue
        if wanted and not set(_vibes(clip)).intersection(wanted):
            continue
        out.append(item)
    if in_project is True:
        out.sort(key=lambda item: (item.clip_index is None, item.clip_index or 0, item.id))
    return out


@tags_router.get("", response_model=list[str])
def list_tags(db: Session = Depends(get_db)) -> list[str]:
    return list(db.scalars(select(Tag.name).order_by(Tag.name.asc())))


@router.patch("/{clip_id}", response_model=ClipOut)
def update_clip(clip_id: int, payload: ClipTagIn, db: Session = Depends(get_db)) -> ClipOut:
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")
    tags = _set_tags(db, clip, payload.tags)
    db.commit()
    db.refresh(clip)
    project = db.get(Project, clip.project_id)
    return _to_out(clip, project=project, project_name=project.name if project else "", tags=tags)


@router.post("/bulk-remove", status_code=204)
def bulk_remove(payload: ClipIdsIn, db: Session = Depends(get_db)) -> None:
    clips = _load_clips(db, payload.ids)
    by_project: dict[int, int] = {}
    for clip in clips:
        by_project[clip.project_id] = by_project.get(clip.project_id, 0) + 1
        clip.removed_from_project = 1
        if not clip.origin_project_name:
            project = db.get(Project, clip.project_id)
            clip.origin_project_name = project.name if project else None
    for project_id, count in by_project.items():
        log_activity(
            db,
            project_id=project_id,
            message=f"Removed {count} clip{'s' if count != 1 else ''} from project",
            status="DELETED",
        )
    db.commit()


@router.post("/bulk-delete", status_code=204)
def bulk_delete(payload: ClipIdsIn, db: Session = Depends(get_db)) -> None:
    clips = _load_clips(db, payload.ids)
    by_project: dict[int, int] = {}
    for clip in clips:
        by_project[clip.project_id] = by_project.get(clip.project_id, 0) + 1
        _unlink_clip(clip)
        db.delete(clip)
    for project_id, count in by_project.items():
        log_activity(db, project_id=project_id, message=f"Deleted {count} clip{'s' if count != 1 else ''} from library", status="DELETED")
    db.commit()


def _open_folder(path: Path) -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    if os.name != "nt":
        return False
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
        return True
    except OSError:
        logger.warning("Could not open downloads folder %s", path)
        return False


@router.post("/bulk-download", response_model=DownloadOut)
def bulk_download(payload: ClipIdsIn, db: Session = Depends(get_db)) -> DownloadOut:
    clips = [clip for clip in _load_clips(db, payload.ids) if clip.file_path and Path(clip.file_path).is_file()]
    if not clips:
        raise HTTPException(status_code=404, detail="No clip files to download")
    project = db.get(Project, clips[0].project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.folder_path:
        ensure_project_folder(project)
        db.commit()
    dest_dir = project_downloads_dir(project)
    dest_dir.mkdir(parents=True, exist_ok=True)
    buffer = BytesIO()
    used: set[str] = set()
    names: list[str] = []
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for position, clip in enumerate(clips, start=1):
            path = Path(clip.file_path)
            name = _download_name(clip, position)
            if name in used:
                name = f"{Path(name).stem}_{clip.id}{Path(name).suffix}"
            used.add(name)
            archive.write(path, name)
            names.append(name)
    _note_download(db, clips)
    zip_name = "selected-clips.zip"
    (dest_dir / zip_name).write_bytes(buffer.getvalue())
    opened = bool(payload.open_folder) and _open_folder(dest_dir)
    return DownloadOut(folder=str(dest_dir), files=names, zip_name=zip_name, count=len(names), opened=opened)


@router.delete("/{clip_id}", status_code=204)
def delete_clip(clip_id: int, db: Session = Depends(get_db)) -> None:
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")
    project_id = clip.project_id
    _unlink_clip(clip)
    db.delete(clip)
    log_activity(db, project_id=project_id, message="Deleted 1 clip from library", status="DELETED")
    db.commit()


@router.get("/{clip_id}/file")
def stream_clip(clip_id: int, db: Session = Depends(get_db)) -> FileResponse:
    return _file_response(db.get(Clip, clip_id), inline=True)


@router.get("/{clip_id}/download")
def download_clip(clip_id: int, db: Session = Depends(get_db)) -> FileResponse:
    clip = db.get(Clip, clip_id)
    if clip is not None:
        _note_download(db, [clip])
    return _file_response(clip, inline=False)
