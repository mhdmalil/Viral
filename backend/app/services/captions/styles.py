from __future__ import annotations

STYLES = frozenset({"classic", "bold", "boxed"})
POSITIONS = frozenset({"lower", "center", "upper"})


def normalize_style(value: str | None) -> str:
    raw = str(value or "classic").strip().lower()
    return raw if raw in STYLES else "classic"


def normalize_position(value: str | None) -> str:
    raw = str(value or "lower").strip().lower()
    return raw if raw in POSITIONS else "lower"
