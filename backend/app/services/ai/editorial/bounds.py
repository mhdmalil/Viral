from __future__ import annotations

from typing import Any

from app.services.video.timeline import resolve_hook_at


RENDER_MIN_SECONDS = 8.0
CLIP_MIN_SECONDS = 8.0
CLIP_PREF_SECONDS = 15.0
PLATFORM_MAX_SECONDS = 180.0
UTTERANCE_GAP = 0.4


def flatten_words(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for seg in transcript.get("segments") or []:
        if not isinstance(seg, dict):
            continue
        inner = seg.get("words") or []
        if inner:
            for raw in inner:
                if not isinstance(raw, dict):
                    continue
                try:
                    start = float(raw.get("start"))
                    end = float(raw.get("end"))
                except (TypeError, ValueError):
                    continue
                text = str(raw.get("word") or raw.get("text") or "").strip()
                if not text or end <= start:
                    continue
                words.append({"start": start, "end": end, "text": text})
        else:
            try:
                start = float(seg.get("start"))
                end = float(seg.get("end"))
            except (TypeError, ValueError):
                continue
            text = str(seg.get("text") or "").strip()
            if text and end > start:
                words.append({"start": start, "end": end, "text": text})
    words.sort(key=lambda w: w["start"])
    return words


def refine_bounds(
    start: float,
    end: float,
    transcript: dict[str, Any],
    *,
    setup_start: float | None = None,
    payoff_end: float | None = None,
    hook_at: float | None = None,
    video_duration: float | None = None,
    platform_max: float = PLATFORM_MAX_SECONDS,
) -> dict[str, Any] | None:
    words = flatten_words(transcript)
    if not words:
        span = _clamp_span(start, end, video_duration, platform_max)
        return _pin_start_to_hook(span, hook_at, [], video_duration, platform_max)

    left = min(start, setup_start if setup_start is not None else start)
    right = max(end, payoff_end if payoff_end is not None else end)
    start_i = _index_at_or_after(words, left)
    end_i = _index_at_or_before(words, right)
    if start_i is None or end_i is None or end_i < start_i:
        span = _clamp_span(start, end, video_duration, platform_max)
        return _pin_start_to_hook(span, hook_at, words, video_duration, platform_max)
    start_i = _utterance_start(words, start_i)
    end_i = _utterance_end(words, end_i)
    new_start = float(words[start_i]["start"])
    new_end = float(words[end_i]["end"])
    new_start, new_end = _grow_to_preferred(words, new_start, new_end, video_duration, platform_max)
    span = _clamp_span(new_start, new_end, video_duration, platform_max)
    if span is None:
        return None
    if span["end"] - span["start"] > platform_max:
        span = _keep_payoff_window(words, start_i, end_i, platform_max, video_duration)
    span = _ensure_min_length(span, video_duration, platform_max, freeze_start=False)
    return _pin_start_to_hook(span, hook_at, words, video_duration, platform_max)


def _pin_start_to_hook(
    span: dict[str, Any] | None,
    hook_at: float | None,
    words: list[dict[str, Any]],
    video_duration: float | None,
    platform_max: float,
) -> dict[str, Any] | None:
    """File starts on the hook in source order. No jump back to setup."""
    if span is None:
        return None
    hook = resolve_hook_at(hook_at, span["start"], span["end"])
    if hook is None:
        return span
    end = max(float(span["end"]), hook)
    if words:
        start, end = _grow_to_preferred(words, hook, end, video_duration, platform_max)
    else:
        start = hook
    return _ensure_min_length({"start": start, "end": end}, video_duration, platform_max, freeze_start=True)


def _index_at_or_after(words: list[dict[str, Any]], t: float) -> int | None:
    for i, word in enumerate(words):
        if word["end"] > t:
            return i
    return None


def _index_at_or_before(words: list[dict[str, Any]], t: float) -> int | None:
    last = None
    for i, word in enumerate(words):
        if word["start"] < t:
            last = i
        else:
            break
    return last


def _utterance_start(words: list[dict[str, Any]], index: int) -> int:
    i = index
    while i > 0:
        gap = float(words[i]["start"]) - float(words[i - 1]["end"])
        prev = str(words[i - 1]["text"])
        if gap >= UTTERANCE_GAP or prev.endswith((".", "?", "!", "…")):
            break
        i -= 1
    return i


def _utterance_end(words: list[dict[str, Any]], index: int) -> int:
    i = index
    last = len(words) - 1
    while i < last:
        cur = str(words[i]["text"])
        if cur.endswith((".", "?", "!", "…")):
            break
        gap = float(words[i + 1]["start"]) - float(words[i]["end"])
        if gap >= UTTERANCE_GAP:
            break
        i += 1
    return i


def _grow_to_preferred(
    words: list[dict[str, Any]],
    start: float,
    end: float,
    video_duration: float | None,
    platform_max: float,
) -> tuple[float, float]:
    """8s is a floor. Keep following speech until a full beat (~15s) when it continues."""
    if end - start >= CLIP_PREF_SECONDS:
        return start, end
    index = _index_at_or_after(words, end - 0.05)
    if index is None:
        return start, end
    last = index
    limit = float(video_duration) if video_duration is not None and video_duration > 0 else None
    while last < len(words) - 1:
        nxt = last + 1
        gap = float(words[nxt]["start"]) - float(words[last]["end"])
        if gap >= 0.85:
            break
        nxt_end = float(words[nxt]["end"])
        if limit is not None and nxt_end > limit:
            break
        if nxt_end - start > platform_max:
            break
        last = nxt
        end = nxt_end
        token = str(words[last].get("text") or "")
        if end - start >= CLIP_PREF_SECONDS and token.endswith((".", "?", "!", "…")):
            break
        if end - start >= CLIP_PREF_SECONDS + 6:
            break
    return start, end


def _clamp_span(
    start: float,
    end: float,
    video_duration: float | None,
    platform_max: float,
) -> dict[str, Any] | None:
    start = max(0.0, float(start))
    end = float(end)
    if video_duration is not None and video_duration > 0:
        end = min(end, float(video_duration))
        start = min(start, end)
    if end <= start:
        return None
    if end - start > platform_max:
        start = max(0.0, end - platform_max)
    grown = _ensure_min_length({"start": start, "end": end}, video_duration, platform_max, freeze_start=False)
    if grown is None:
        return None
    return {"start": round(grown["start"], 3), "end": round(grown["end"], 3)}


def _ensure_min_length(
    span: dict[str, Any] | None,
    video_duration: float | None,
    platform_max: float,
    *,
    freeze_start: bool,
) -> dict[str, Any] | None:
    if span is None:
        return None
    start = float(span["start"])
    end = float(span["end"])
    limit = float(video_duration) if video_duration is not None and video_duration > 0 else None
    if limit is not None and limit + 0.05 < CLIP_MIN_SECONDS:
        return None
    if end - start < CLIP_MIN_SECONDS:
        end = start + CLIP_MIN_SECONDS
        if limit is not None:
            end = min(end, limit)
    if end - start < CLIP_MIN_SECONDS:
        start = max(0.0, end - CLIP_MIN_SECONDS)
    if end - start < CLIP_MIN_SECONDS - 0.05:
        return None
    if end - start > platform_max:
        end = start + platform_max
    return {"start": round(start, 3), "end": round(end, 3)}


def _keep_payoff_window(
    words: list[dict[str, Any]],
    start_i: int,
    end_i: int,
    platform_max: float,
    video_duration: float | None,
) -> dict[str, Any] | None:
    end = float(words[end_i]["end"])
    start = end - platform_max
    for i in range(end_i, start_i - 1, -1):
        if end - float(words[i]["start"]) <= platform_max:
            start = float(words[i]["start"])
            break
    return _clamp_span(start, end, video_duration, platform_max)
