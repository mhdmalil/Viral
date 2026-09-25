from fastapi import APIRouter

from app.core.config import settings
from app.schemas.api import AppSettingsOut

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettingsOut)
def get_settings() -> AppSettingsOut:
    return AppSettingsOut(
        host=settings.host,
        bind_is_loopback=settings.host in {"127.0.0.1", "localhost", "::1"},
        quality_threshold=settings.quality_threshold,
        ai_provider_configured=bool(
            (settings.ai_api_key or "").strip()
            or (settings.gemini_api_key or "").strip()
            or (settings.groq_api_key or "").strip()
        ),
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model,
        openrouter_configured=bool((settings.ai_api_key or "").strip()),
        gemini_configured=bool((settings.gemini_api_key or "").strip()),
        groq_configured=bool((settings.groq_api_key or "").strip()),
        whisper_model=settings.whisper_model,
        whisper_device=settings.whisper_device,
        transcription_backend=settings.transcription_backend,
    )
