from fastapi import APIRouter

from app.services.ai.usage import clear_usage, usage_report

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("")
def get_usage(provider: str | None = None, project_id: int | None = None, hours: int = 1) -> dict:
    return usage_report(provider=provider or None, project_id=project_id, hours=hours)


@router.delete("", status_code=204)
def reset_usage(project_id: int | None = None) -> None:
    clear_usage(project_id=project_id)
