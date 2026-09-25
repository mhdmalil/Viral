from __future__ import annotations

from typing import Any

VIBE_ORDER = (
    "funny",
    "sad",
    "viral",
    "shocking",
    "awkward",
    "wholesome",
    "angry",
    "debate",
    "cringe",
    "informative",
    "financial",
    "lifestyle",
)
VIBES = frozenset(VIBE_ORDER)
VIBE_ALIASES = {
    "information": "informative",
    "info": "informative",
    "educational": "informative",
    "finance": "financial",
    "money": "financial",
    "life": "lifestyle",
}


def normalize_vibe(raw: Any) -> str | None:
    value = str(raw or "").strip().lower()
    value = VIBE_ALIASES.get(value, value)
    return value if value in VIBES else None


def normalize_vibes(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = raw.replace("|", ",").split(",")
    elif isinstance(raw, (list, tuple, set)):
        parts = list(raw)
    else:
        return []
    seen: list[str] = []
    for item in parts:
        vibe = normalize_vibe(item)
        if vibe and vibe not in seen:
            seen.append(vibe)
    return seen


def parse_row_vibes(row: dict[str, Any] | None) -> list[str]:
    if not isinstance(row, dict):
        return []
    raw = row.get("vibes")
    if raw is None or raw == "" or raw == []:
        raw = row.get("vibe")
    signals = row.get("signals")
    if (raw is None or raw == "" or raw == []) and isinstance(signals, dict):
        raw = signals.get("vibes") if signals.get("vibes") not in (None, "", []) else signals.get("vibe")
    return normalize_vibes(raw)[:3]


def row_vibe(row: dict[str, Any]) -> str | None:
    labels = parse_row_vibes(row)
    return labels[0] if labels else None


def filter_wanted_vibes(rows: list[dict[str, Any]], wanted: list[str] | None) -> list[dict[str, Any]]:
    allowed = set(normalize_vibes(wanted))
    if not allowed:
        return rows
    kept: list[dict[str, Any]] = []
    for row in rows:
        labels = parse_row_vibes(row)
        if labels and allowed.intersection(labels):
            kept.append(row)
    return kept
