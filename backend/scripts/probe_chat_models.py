"""Print live model ids and probe HTTP statuses. Never prints API keys."""

from __future__ import annotations

import json

import httpx

from app.core.config import settings
from app.services.ai.chat import chat_completions_url


def _ids(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("data") or payload.get("models") or []
    out: list[str] = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                name = str(row.get("id") or row.get("name") or "").strip()
            else:
                name = str(row).strip()
            if name:
                out.append(name.removeprefix("models/"))
    return out


def list_models(base: str, key: str) -> tuple[int, list[str]]:
    url = (base or "").rstrip("/") + "/models"
    response = httpx.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=20.0)
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    return response.status_code, _ids(payload)


def probe_chat(base: str, key: str, model: str) -> int:
    url = chat_completions_url(base)
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": 8,
        "messages": [{"role": "user", "content": "Reply with ok"}],
    }
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=body,
        timeout=25.0,
    )
    return response.status_code


def main() -> None:
    groq_key = (settings.groq_api_key or "").strip()
    gem_key = (settings.gemini_api_key or "").strip()
    print("keys groq=%s gemini=%s" % (bool(groq_key), bool(gem_key)))
    if groq_key:
        for model in ["qwen/qwen3.8-27b", "allam-2-7b"]:
            print("groq chat", model, probe_chat(settings.groq_api_base_url, groq_key, model))
    if gem_key:
        for model in [
            "gemini-flash-lite-latest",
            "gemini-3.5-flash",
            "gemini-3.8-flash",
        ]:
            print("gemini chat", model, probe_chat(settings.gemini_api_base_url, gem_key, model))


if __name__ == "__main__":
    main()
