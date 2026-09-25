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


_FILLER = {"um", "uh", "er", "ah", "hmm", "hm", "umm", "uhh"}
_GAP_SECONDS = 0.45


def _word_token(item: dict[str, Any]) -> str:
    raw = str(item.get("word") or item.get("text") or "").strip().lower()
    return "".join(ch for ch in raw if ch.isalpha() or ch == "'")


def tighten_pieces(
    words: list[dict[str, Any]],
    start: float,
    end: float,
    *,
    min_total: float = 8.0,
) -> list[Piece]:
    """Drop filler and long gaps. Stay in source order. Keep the full span if the tight cut is under 8s."""
    try:
        start = float(start)
        end = float(end)
    except (TypeError, ValueError):
        return []
    if not math.isfinite(start) or not math.isfinite(end) or end <= start:
        return []
    spoken: list[tuple[float, float]] = []
    for item in words:
        if not isinstance(item, dict):
            continue
        token = _word_token(item)
        if not token or token in _FILLER:
            continue
        try:
            word_start = float(item.get("start"))
            word_end = float(item.get("end"))
        except (TypeError, ValueError):
            continue
        if word_end <= start or word_start >= end:
            continue
        spoken.append((max(start, word_start), min(end, word_end)))
    if not spoken:
        return _pack([(start, end)])
    spans: list[tuple[float, float]] = []
    cur_s, cur_e = spoken[0]
    for word_start, word_end in spoken[1:]:
        if word_start - cur_e > _GAP_SECONDS:
            spans.append((cur_s, cur_e))
            cur_s, cur_e = word_start, word_end
        else:
            cur_e = max(cur_e, word_end)
    spans.append((cur_s, cur_e))
    total = sum(b - a for a, b in spans)
    if total < min_total - 0.05:
        return _pack([(start, end)])
    return _pack(spans)


def pick_cutaway(
    scene_times: list[float],
    avoid_start: float,
    avoid_end: float,
    video_duration: float,
) -> tuple[float, float] | None:
    """Another shot from this file, outside the clip, where the picture already changed."""
    try:
        avoid_start = float(avoid_start)
        avoid_end = float(avoid_end)
        video_duration = float(video_duration)
    except (TypeError, ValueError):
        return None
    times = sorted({round(float(t), 3) for t in scene_times if 0 <= float(t) < video_duration})
    if len(times) < 2:
        return None
    for index, stamp in enumerate(times[:-1]):
        nxt = times[index + 1]
        if nxt - stamp < 0.8:
            continue
        span_end = min(stamp + 1.2, nxt - 0.05)
        if span_end - stamp < 0.7:
            continue
        if span_end > avoid_start - 0.3 and stamp < avoid_end + 0.3:
            continue
        return (stamp, round(span_end, 3))
    return None


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
