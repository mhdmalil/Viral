from pathlib import Path
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import Account, Clip, Project
from app.schemas.api import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.branding.normalize import dump_branding, parse_branding
from app.services.captions.styles import normalize_position, normalize_style
from app.services.storage.paths import ensure_project_folder, media_url, project_branding_dir
from app.services.storage.purge import purge_project
from app.services.storage.workspace import LIBRARY_VAULT_STATUS, ensure_workspace_account

router = APIRouter(prefix="/projects", tags=["projects"])


def _ready_counts(db: Session, project_ids: list[int]) -> dict[int, int]:
    if not project_ids:
        return {}
    counts: dict[int, int] = {}
    for clip in db.scalars(select(Clip).where(Clip.project_id.in_(project_ids), Clip.removed_from_project == 0)):
        if clip.file_path and Path(clip.file_path).is_file():
            counts[clip.project_id] = counts.get(clip.project_id, 0) + 1
    return counts


def to_project_out(project: Project, ready_clips: int = 0) -> ProjectOut:
    branding = parse_branding(getattr(project, "branding_json", None))
    logo = branding.get("custom_logo_path")
    return ProjectOut.model_validate(project).model_copy(
        update={
            "ready_clips": ready_clips,
            "branding": branding,
            "custom_logo_url": media_url(logo) if logo else None,
        }
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(account_id: int | None = None, db: Session = Depends(get_db)) -> list[ProjectOut]:
    stmt = select(Project).where(Project.status != LIBRARY_VAULT_STATUS).order_by(Project.created_at.desc())
    if account_id is not None:
        stmt = stmt.where(Project.account_id == account_id)
    projects = list(db.scalars(stmt))
    counts = _ready_counts(db, [row.id for row in projects])
    return [to_project_out(row, counts.get(row.id, 0)) for row in projects]


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectOut:
    if payload.account_id is None:
        account = ensure_workspace_account(db)
    else:
        account = db.get(Account, payload.account_id)
        if account is None:
            raise HTTPException(status_code=400, detail="Account not found")
    clip_count = payload.clip_count
    strategy = payload.strategy if payload.strategy is not None else account.content_strategy
    project = Project(
        account_id=account.id,
        name=payload.name,
        clip_count=clip_count,
        duration_min=8,
        duration_max=20,
        strategy=strategy,
        captions_enabled=1 if payload.captions_enabled else 0,
        caption_style=normalize_style(payload.caption_style or account.default_caption_style),
        caption_position=normalize_position(payload.caption_position or account.default_caption_position),
        reframe_enabled=0,
        branding_json=dump_branding(payload.branding),
        status="draft",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    ensure_project_folder(project)
    db.commit()
    db.refresh(project)
    return to_project_out(project, 0)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)) -> ProjectOut:
    project = db.get(Project, project_id)
    if project is None or project.status == LIBRARY_VAULT_STATUS:
        raise HTTPException(status_code=404, detail="Project not found")
    data = payload.model_dump(exclude_unset=True)
    if "captions_enabled" in data and data["captions_enabled"] is not None:
        data["captions_enabled"] = 1 if data["captions_enabled"] else 0
    if "reframe_enabled" in data:
        data["reframe_enabled"] = 0
    if "caption_style" in data:
        data["caption_style"] = normalize_style(data["caption_style"])
    if "caption_position" in data:
        data["caption_position"] = normalize_position(data["caption_position"])
    if "branding" in data:
        incoming = data.pop("branding")
        current = parse_branding(project.branding_json)
        parsed = parse_branding(json.dumps(incoming or {}))
        if not parsed.get("custom_logo_path"):
            parsed["custom_logo_path"] = current.get("custom_logo_path")
        if "vibes" not in (incoming or {}):
            parsed["vibes"] = current.get("vibes") or []
        project.branding_json = dump_branding(parsed)
    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    counts = _ready_counts(db, [project.id])
    return to_project_out(project, counts.get(project.id, 0))


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)) -> ProjectOut:
    project = db.get(Project, project_id)
    if project is None or project.status == LIBRARY_VAULT_STATUS:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.folder_path:
        ensure_project_folder(project)
        db.commit()
        db.refresh(project)
    counts = _ready_counts(db, [project.id])
    return to_project_out(project, counts.get(project.id, 0))


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)) -> None:
    project = db.get(Project, project_id)
    if project is None or project.status == LIBRARY_VAULT_STATUS:
        raise HTTPException(status_code=404, detail="Project not found")
    purge_project(db, project)


_LOGO_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@router.post("/{project_id}/logo", response_model=ProjectOut)
def upload_logo(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)) -> ProjectOut:
    project = db.get(Project, project_id)
    if project is None or project.status == LIBRARY_VAULT_STATUS:
        raise HTTPException(status_code=404, detail="Project not found")
    suffix = Path(file.filename or "logo.png").suffix.lower()
    if suffix not in _LOGO_SUFFIXES:
        raise HTTPException(status_code=400, detail="Logo must be png, jpg, or webp.")
    if not project.folder_path:
        ensure_project_folder(project)
        db.commit()
        db.refresh(project)
    dest = project_branding_dir(project) / f"custom_logo{suffix}"
    with dest.open("wb") as handle:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    if dest.stat().st_size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty file.")
    branding = parse_branding(project.branding_json)
    branding["custom_logo_path"] = str(dest)
    branding["footer"] = "picture"
    project.branding_json = dump_branding(branding)
    db.commit()
    db.refresh(project)
    counts = _ready_counts(db, [project.id])
    return to_project_out(project, counts.get(project.id, 0))


@router.delete("/{project_id}/logo", response_model=ProjectOut)
def delete_logo(project_id: int, db: Session = Depends(get_db)) -> ProjectOut:
    project = db.get(Project, project_id)
    if project is None or project.status == LIBRARY_VAULT_STATUS:
        raise HTTPException(status_code=404, detail="Project not found")
    branding = parse_branding(project.branding_json)
    path = branding.get("custom_logo_path")
    if path:
        Path(path).unlink(missing_ok=True)
    branding["custom_logo_path"] = None
    project.branding_json = dump_branding(branding)
    db.commit()
    db.refresh(project)
    counts = _ready_counts(db, [project.id])
    return to_project_out(project, counts.get(project.id, 0))

