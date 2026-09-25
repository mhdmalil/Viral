from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
import threading

from app.core.config import settings
from app.database.session import get_db
from app.models.entities import ProcessingJob, Project, SourceVideo
from app.schemas.api import JobOut
from app.services.jobs.control import live_job_id, request_cancel
from app.services.jobs.runner import run_generate_job
from app.services.storage.import_video import _drop_other_sources, hide_current_project_clips
from app.services.storage.purge import wipe_clips_matching_hash

router = APIRouter(prefix="/projects", tags=["jobs"])

ACTIVE = {
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


@router.get("/{project_id}/job", response_model=None)
def latest_job(project_id: int, db: Session = Depends(get_db)) -> JobOut | Response:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    job = db.scalar(
        select(ProcessingJob).where(ProcessingJob.project_id == project_id).order_by(ProcessingJob.id.desc())
    )
    if job is None:
        return Response(status_code=204)
    return JobOut.model_validate(job)


def _cancel_dead_jobs(db: Session, project_id: int) -> None:
    """DB can still say RENDERING after uvicorn was killed. That job has no thread."""
    live = live_job_id()
    rows = list(
        db.scalars(
            select(ProcessingJob).where(ProcessingJob.project_id == project_id, ProcessingJob.status.in_(ACTIVE))
        )
    )
    for job in rows:
        if live == job.id:
            continue
        request_cancel(job.id)
        job.status = "CANCELLED"
        job.stage_message = "Stopped because the app restarted"
        job.error_message = None


def _launch_generate(job_id: int) -> None:
    if settings.transcription_backend == "test":
        run_generate_job(job_id)
        return
    threading.Thread(target=run_generate_job, args=(job_id,), name=f"generate-{job_id}", daemon=True).start()


def abandon_orphan_jobs() -> None:
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        rows = list(db.scalars(select(ProcessingJob).where(ProcessingJob.status.in_(ACTIVE))))
        for job in rows:
            job.status = "CANCELLED"
            job.stage_message = "Stopped because the app restarted"
            job.error_message = None
        db.commit()
    finally:
        db.close()


@router.post("/{project_id}/generate", response_model=JobOut)
def start_generate(project_id: int, db: Session = Depends(get_db)) -> ProcessingJob:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    source = db.scalar(
        select(SourceVideo).where(SourceVideo.project_id == project_id).order_by(SourceVideo.id.desc())
    )
    if source is None:
        raise HTTPException(status_code=400, detail="Drop a video first.")
    _drop_other_sources(db, project, source.id)
    _cancel_dead_jobs(db, project_id)
    db.flush()
    live = live_job_id()
    active = db.scalar(
        select(ProcessingJob).where(ProcessingJob.project_id == project_id, ProcessingJob.status.in_(ACTIVE))
    )
    if active is not None and live == active.id:
        return active
    if active is not None:
        request_cancel(active.id)
        active.status = "CANCELLED"
        active.stage_message = "Replaced by a new generate"
        db.flush()
    hide_current_project_clips(db, project)
    wipe_clips_matching_hash(db, source.file_hash)
    job = ProcessingJob(
        project_id=project_id,
        status="QUEUED",
        stage_message="Queued",
        progress=5,
        source_id=source.id,
    )
    project.status = "processing"
    db.add(job)
    db.commit()
    db.refresh(job)
    _launch_generate(job.id)
    return job


@router.post("/{project_id}/generate/stop", response_model=JobOut)
def stop_generate(project_id: int, db: Session = Depends(get_db)) -> ProcessingJob:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    job = db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.project_id == project_id, ProcessingJob.status.in_(ACTIVE))
        .order_by(ProcessingJob.id.desc())
    )
    if job is None:
        raise HTTPException(status_code=409, detail="Nothing is generating.")
    request_cancel(job.id)
    job.stage_message = "Stopping…"
    db.commit()
    db.refresh(job)
    return job
