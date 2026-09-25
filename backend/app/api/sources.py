from uuid import uuid4

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import Project, SourceVideo
from app.schemas.api import SourceVideoOut
from app.services.storage.import_video import (
    DuplicateSourceError,
    SourceBusyError,
    delete_source_record,
    import_video_file,
    source_to_dict,
)
from app.services.storage.paths import ensure_project_folder, project_original_dir
from app.services.video.ffmpeg import VideoProcessingError, validate_suffix

router = APIRouter(prefix="/projects", tags=["source-videos"])


@router.get("/{project_id}/source", response_model=list[SourceVideoOut])
def list_sources(project_id: int, db: Session = Depends(get_db)) -> list[dict]:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    rows = list(db.scalars(select(SourceVideo).where(SourceVideo.project_id == project_id)))
    return [source_to_dict(row) for row in rows]


@router.post("/{project_id}/source", response_model=SourceVideoOut)
def upload_source(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    filename = file.filename or "video.mp4"
    try:
        suffix = validate_suffix(filename)
    except VideoProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not project.folder_path:
        ensure_project_folder(project)
        db.commit()
        db.refresh(project)
    dest_dir = project_original_dir(project)
    dest_dir.mkdir(parents=True, exist_ok=True)
    temp_path = dest_dir / f".upload_{uuid4().hex}{suffix}"
    try:
        with temp_path.open("wb") as handle:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
        if temp_path.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="Empty file.")
        record, reused = import_video_file(db, project, temp_path, filename)
    except HTTPException:
        temp_path.unlink(missing_ok=True)
        raise
    except DuplicateSourceError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SourceBusyError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except VideoProcessingError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return source_to_dict(record, reused=reused)


@router.delete("/{project_id}/source/{source_id}", status_code=204)
def delete_source(project_id: int, source_id: int, db: Session = Depends(get_db)) -> None:
    record = db.get(SourceVideo, source_id)
    if record is None or record.project_id != project_id:
        raise HTTPException(status_code=404, detail="Source video not found")
    try:
        delete_source_record(db, record)
    except SourceBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{project_id}/source/{source_id}/download")
def download_source(project_id: int, source_id: int, db: Session = Depends(get_db)) -> FileResponse:
    record = db.get(SourceVideo, source_id)
    if record is None or record.project_id != project_id:
        raise HTTPException(status_code=404, detail="Source video not found")
    path = Path(record.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File is missing on disk")
    return FileResponse(path, filename=path.name, media_type="application/octet-stream")
