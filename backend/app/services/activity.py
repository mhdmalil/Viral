from sqlalchemy.orm import Session

from app.models.entities import ActivityEvent


def log_activity(db: Session, *, project_id: int, message: str, status: str = "INFO") -> None:
    db.add(ActivityEvent(project_id=project_id, message=message[:300], status=status))
