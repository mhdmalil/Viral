"""One-shot: wipe dummy projects, clips, leftover accounts. Keep app settings."""

from pathlib import Path
from shutil import rmtree

from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from app.core.config import MEDIA_DIR, settings
from app.database.session import SessionLocal
from app.models.entities import Account, ApiUsageEvent, Clip, ClipTag, ProcessingJob, Project, SourceVideo, Tag
from app.services.storage.purge import purge_project
from app.services.storage.workspace import ensure_workspace_account


def main() -> None:
    db = SessionLocal()
    try:
        for project in list(db.scalars(select(Project))):
            purge_project(db, project, keep_clips=False)
        db.execute(sa_delete(ClipTag))
        db.execute(sa_delete(Clip))
        db.execute(sa_delete(SourceVideo))
        db.execute(sa_delete(ProcessingJob))
        db.execute(sa_delete(ApiUsageEvent))
        db.execute(sa_delete(Tag))
        db.execute(sa_delete(Account))
        db.commit()
        ensure_workspace_account(db)
    finally:
        db.close()
    projects = Path(settings.projects_dir)
    if projects.is_dir():
        for child in projects.iterdir():
            if child.is_dir():
                rmtree(child, ignore_errors=True)
    media = MEDIA_DIR / "accounts"
    if media.is_dir():
        rmtree(media, ignore_errors=True)
    print("workspace reset")


if __name__ == "__main__":
    main()
