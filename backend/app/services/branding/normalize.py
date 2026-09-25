from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.ai.editorial.vibes import normalize_vibes

PLATFORMS = ("youtube", "tiktok", "instagram")
HANDLE_MAX = 40


def parse_branding(raw: str | None) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    handles = []
    for row in data.get("handles") or []:
        if not isinstance(row, dict):
            continue
        platform = str(row.get("platform") or "").strip().lower()
        name = str(row.get("name") or "").strip()[:HANDLE_MAX]
        if platform in PLATFORMS:
            handles.append({"platform": platform, "name": name})
    custom_name = str(data.get("custom_name") or "").strip()[:HANDLE_MAX]
    custom_logo_path = str(data.get("custom_logo_path") or "").strip()
    footer = str(data.get("footer") or "socials").strip().lower()
    if footer not in {"socials", "picture"}:
        footer = "socials"
    return {
        "handles": handles,
        "custom_name": custom_name,
        "custom_logo_path": custom_logo_path or None,
        "footer": footer,
        "vibes": normalize_vibes(data.get("vibes")),
    }


def dump_branding(payload: dict[str, Any] | None) -> str:
    return json.dumps(parse_branding(json.dumps(payload or {})), ensure_ascii=False)


def branding_items(data: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if str(data.get("footer") or "socials") == "picture":
        logo = str(data.get("custom_logo_path") or "").strip()
        if logo and Path(logo).is_file():
            items.append({"platform": "banner", "name": "", "logo": logo, "fit": "banner"})
            return items
    for row in data.get("handles") or []:
        items.append({"platform": row["platform"], "name": row["name"], "fit": "icon"})
    return items
