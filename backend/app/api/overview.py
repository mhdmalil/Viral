from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import ActivityEvent, Clip, ProcessingJob, Project
from app.schemas.api import DashboardActivity, DashboardOut, DashboardProject

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _file_ready(clip: Clip) -> bool:
    return bool(clip.file_path and Path(clip.file_path).is_file())


@router.get("", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    project_count = db.scalar(select(func.count()).select_from(Project).where(Project.status != "vault")) or 0
    clips = list(db.scalars(select(Clip)))
    clip_count = sum(1 for clip in clips if _file_ready(clip))
    download_count = db.scalar(select(func.coalesce(func.sum(Clip.download_count), 0))) or 0
    projects = list(
        db.scalars(select(Project).where(Project.status != "vault").order_by(Project.created_at.desc()).limit(6))
    )
    ready_rows: dict[int, int] = {}
    for clip in clips:
        if clip.removed_from_project:
            continue
        if clip.project_id in {row.id for row in projects} and _file_ready(clip):
            ready_rows[clip.project_id] = ready_rows.get(clip.project_id, 0) + 1
    jobs = list(db.scalars(select(ProcessingJob).order_by(ProcessingJob.id.desc()).limit(8)))
    events = list(db.scalars(select(ActivityEvent).order_by(ActivityEvent.id.desc()).limit(8)))
    project_ids = {job.project_id for job in jobs} | {event.project_id for event in events} | {row.id for row in projects}
    names = {
        row.id: row.name
        for row in db.scalars(select(Project).where(Project.id.in_(project_ids)))
    } if project_ids else {}
    activity: list[DashboardActivity] = []
    for job in jobs:
        activity.append(
            DashboardActivity(
                id=f"job-{job.id}",
                project_id=job.project_id,
                project_name=names.get(job.project_id, "Project"),
                status=job.status,
                stage_message=job.stage_message or job.status,
                created_at=job.updated_at or job.created_at,
            )
        )
    for event in events:
        activity.append(
            DashboardActivity(
                id=f"event-{event.id}",
                project_id=event.project_id,
                project_name=names.get(event.project_id, "Project"),
                status=event.status,
                stage_message=event.message,
                created_at=event.created_at,
            )
        )
    activity.sort(key=lambda row: row.created_at or row.id, reverse=True)
    return DashboardOut(
        project_count=int(project_count),
        clip_count=int(clip_count),
        download_count=int(download_count),
        recent_projects=[
            DashboardProject(
                id=row.id,
                name=row.name,
                status=row.status,
                ready_clips=int(ready_rows.get(row.id, 0)),
                created_at=row.created_at,
            )
            for row in projects
        ],
        recent_activity=activity[:8],
    )
