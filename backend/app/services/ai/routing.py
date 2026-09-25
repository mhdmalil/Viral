from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODELS = (
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
)
GROQ_MODELS = (
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
)
DEAD_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen/qwen3.6-27b",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite",
}
CATALOG_LIMIT = 8
_rotation = 0


@dataclass(frozen=True)
class ChatTarget:
    provider: str
    model: str
    base_url: str
    api_key: str


def _csv(raw: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for part in (raw or "").split(","):
        name = part.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def openrouter_free_ids(catalog: dict[str, Any], *, skip: set[str]) -> list[str]:
    ids: list[str] = []
    for row in catalog.get("data") or []:
        if not isinstance(row, dict):
            continue
        model_id = str(row.get("id") or "").strip()
        if not model_id.endswith(":free") or model_id in skip:
            continue
        lowered = model_id.lower()
        if any(tag in lowered for tag in ("-vl", "whisper", "tts", "image", "audio")):
            continue
        ids.append(model_id)
        if len(ids) >= CATALOG_LIMIT:
            break
    return ids


def fetch_openrouter_free_ids(skip: set[str]) -> list[str]:
    key = (settings.ai_api_key or "").strip()
    if not key:
        return []
    url = (settings.ai_api_base_url or "https://openrouter.ai/api/v1").rstrip("/") + "/models"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {key}"},
            timeout=20.0,
        )
    except httpx.HTTPError:
        logger.info("Could not list OpenRouter models; using pinned fallbacks only")
        return []
    if response.status_code >= 400:
        logger.info("OpenRouter model list HTTP %s", response.status_code)
        return []
    try:
        payload = response.json()
    except ValueError:
        return []
    if not isinstance(payload, dict):
        return []
    return openrouter_free_ids(payload, skip=skip)


def _unique_models(*groups: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for name in group:
            name = (name or "").strip()
            if not name or name in seen or name in DEAD_MODELS:
                continue
            seen.add(name)
            out.append(name)
    return out


def _rotate(names: list[str], offset: int) -> list[str]:
    if not names:
        return []
    start = offset % len(names)
    return names[start:] + names[:start]


def next_rotation() -> int:
    global _rotation
    value = _rotation
    _rotation += 1
    return value


def _prefer(names: list[str], preferred: str | None) -> list[str]:
    if not preferred or preferred not in names:
        return names
    return [preferred] + [n for n in names if n != preferred]


def iter_chat_targets(
    *,
    catalog_ids: list[str] | None = None,
    rotate: int = 0,
    prefer: tuple[str, str] | None = None,
) -> Iterator[ChatTarget]:
    """All Groq models, then all Gemini models, then OpenRouter.

    `prefer` (provider, model) is tried first inside its provider so a working
    model is reused until it 429s. `rotate` still shuffles the rest.
    """
    seen: set[tuple[str, str]] = set()

    def emit(provider: str, model: str, base: str, key: str) -> ChatTarget | None:
        model = (model or "").strip()
        key = (key or "").strip()
        base = (base or "").strip()
        if not model or not key or not base:
            return None
        stamp = (provider, model)
        if stamp in seen:
            return None
        seen.add(stamp)
        return ChatTarget(provider=provider, model=model, base_url=base, api_key=key)

    or_key = (settings.ai_api_key or "").strip()
    or_base = settings.ai_api_base_url
    gem_key = (settings.gemini_api_key or "").strip()
    gem_base = settings.gemini_api_base_url
    groq_key = (settings.groq_api_key or "").strip()
    groq_base = settings.groq_api_base_url

    groq_models = _prefer(
        _rotate(
            _unique_models([(settings.groq_model or "").strip()], GROQ_MODELS),
            rotate,
        ),
        prefer[1] if prefer and prefer[0] == "groq" else None,
    )
    for name in groq_models:
        target = emit("groq", name, groq_base, groq_key)
        if target:
            yield target

    gem_models = _prefer(
        _rotate(
            _unique_models([(settings.gemini_model or "").strip()], GEMINI_MODELS),
            rotate,
        ),
        prefer[1] if prefer and prefer[0] == "gemini" else None,
    )
    for name in gem_models:
        target = emit("gemini", name, gem_base, gem_key)
        if target:
            yield target

    glm = emit("openrouter", settings.ai_model, or_base, or_key)
    if glm:
        yield glm

    skip = {(settings.ai_model or "").strip()}
    for name in _csv(settings.ai_fallback_models):
        target = emit("openrouter", name, or_base, or_key)
        if target:
            yield target
            skip.add(name)
    extras = catalog_ids if catalog_ids is not None else []
    for name in extras:
        target = emit("openrouter", name, or_base, or_key)
        if target:
            yield target


def any_chat_key() -> bool:
    return bool(
        (settings.ai_api_key or "").strip()
        or (settings.gemini_api_key or "").strip()
        or (settings.groq_api_key or "").strip()
    )
