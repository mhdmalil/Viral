from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

OPEN_SECONDS = 1.65
MIN_SPAN = 0.05


@dataclass(frozen=True)
class Piece:
    src_start: float
    src_end: float
    out_start: float

    @property
    def duration(self) -> float:
        return self.src_end - self.src_start

    def as_tuple(self) -> tuple[float, float]:
        return (self.src_start, self.src_end)


def resolve_hook_at(
    hook_at: Any,
    start: float,
    end: float,
    window_start: float | None = None,
) -> float | None:
    """Map hook_at onto the same absolute source timeline as start/end.

    Returns None when the value is missing, non-finite, or outside [start, end).
    If the model used window-local seconds, add window_start when that lands in range.
    """
    if hook_at is None or hook_at == "":
        return None
    try:
        hook = float(hook_at)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(hook):
        return None
    start = float(start)
    end = float(end)
    if start <= hook < end:
        return hook
    if window_start is not None:
        shifted = float(window_start) + hook
        if start <= shifted < end:
            return shifted
    return None


def hook_first_pieces(start: float, end: float, hook_at: float | None) -> list[Piece]:
    """One linear take. Playback starts on hook_at when it sits inside the thought."""
    try:
        start = float(start)
        end = float(end)
    except (TypeError, ValueError):
        return []
    if not math.isfinite(start) or not math.isfinite(end) or end <= start:
        return []

    hook = resolve_hook_at(hook_at, start, end)
    if hook is None:
        logger.info(
            "CLIP linear start=%.3f end=%.3f hook_at=%s",
            start,
            end,
            hook_at,
        )
        return _pack([(start, end)])

    logger.info(
        "CLIP starts on hook source %.3f → %.3f hook_at=%.3f",
        hook,
        end,
        hook,
    )
    return _pack([(hook, end)])


def output_duration(pieces: list[Piece]) -> float:
    return sum(piece.duration for piece in pieces)


def hook_until(pieces: list[Piece]) -> float:
    if not pieces:
        return OPEN_SECONDS
    if len(pieces) == 1:
        return min(OPEN_SECONDS, pieces[0].duration)
    return pieces[0].duration


def _pack(spans: list[tuple[float, float]]) -> list[Piece]:
    out: list[Piece] = []
    t = 0.0
    for src_start, src_end in spans:
        if src_end - src_start < MIN_SPAN:
            continue
        if src_end <= src_start:
            continue
        out.append(Piece(round(src_start, 3), round(src_end, 3), round(t, 3)))
        t += src_end - src_start
    return out
