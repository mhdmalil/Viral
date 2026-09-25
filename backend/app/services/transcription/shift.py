from __future__ import annotations

from typing import Any


CHUNK_SECONDS = 120.0


def shift_transcript(payload: dict[str, Any], offset: float) -> dict[str, Any]:
    """Move Whisper times from chunk-local 0 to absolute source seconds."""
    shift = float(offset)
    out = dict(payload)
    segments: list[dict[str, Any]] = []
    for raw in payload.get("segments") or []:
        if not isinstance(raw, dict):
            continue
        seg = dict(raw)
        try:
            seg["start"] = float(raw.get("start")) + shift
            seg["end"] = float(raw.get("end")) + shift
        except (TypeError, ValueError):
            continue
        words_out: list[dict[str, Any]] = []
        for word in raw.get("words") or []:
            if not isinstance(word, dict):
                continue
            item = dict(word)
            try:
                if "start" in item:
                    item["start"] = float(item["start"]) + shift
                if "end" in item:
                    item["end"] = float(item["end"]) + shift
            except (TypeError, ValueError):
                continue
            words_out.append(item)
        if words_out:
            seg["words"] = words_out
        segments.append(seg)
    out["segments"] = segments
    try:
        local_dur = float(payload.get("duration") or 0.0)
    except (TypeError, ValueError):
        local_dur = 0.0
    ends = [float(s["end"]) for s in segments]
    out["duration"] = max(local_dur + shift, max(ends) if ends else shift)
    if segments:
        out["text"] = " ".join(str(s.get("text") or "").strip() for s in segments if str(s.get("text") or "").strip())
    return out


def merge_transcript(base: dict[str, Any], chunk: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    segments = [dict(s) for s in (base.get("segments") or []) if isinstance(s, dict)]
    last_end = max((float(s.get("end") or 0) for s in segments), default=-1.0)
    for raw in chunk.get("segments") or []:
        if not isinstance(raw, dict):
            continue
        try:
            start = float(raw.get("start"))
        except (TypeError, ValueError):
            continue
        if start + 0.05 < last_end:
            continue
        segments.append(dict(raw))
        try:
            last_end = max(last_end, float(raw.get("end")))
        except (TypeError, ValueError):
            pass
    merged["segments"] = segments
    merged["text"] = " ".join(str(s.get("text") or "").strip() for s in segments if str(s.get("text") or "").strip())
    try:
        merged["duration"] = max(float(base.get("duration") or 0), float(chunk.get("duration") or 0), last_end)
    except (TypeError, ValueError):
        merged["duration"] = last_end if last_end > 0 else base.get("duration")
    if chunk.get("language") and not merged.get("language"):
        merged["language"] = chunk.get("language")
    if chunk.get("backend"):
        merged["backend"] = chunk.get("backend")
    if chunk.get("model"):
        merged["model"] = chunk.get("model")
    return merged


def transcript_complete(payload: dict[str, Any], video_duration: float | None) -> bool:
    segments = payload.get("segments") or []
    if not segments:
        return False
    if video_duration is None or video_duration <= 0:
        return True
    try:
        last = max(float(s.get("end") or 0) for s in segments if isinstance(s, dict))
    except ValueError:
        return False
    return last >= float(video_duration) * 0.9


def window_from_segments(
    segments: list[dict[str, Any]],
    *,
    window_start: float,
    window_end: float,
) -> dict[str, Any] | None:
    chunk: list[dict[str, Any]] = []
    for raw in segments:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text") or "").strip()
        try:
            start = float(raw.get("start"))
            end = float(raw.get("end"))
        except (TypeError, ValueError):
            continue
        if not text or end <= window_start or start >= window_end:
            continue
        chunk.append({"start": start, "end": end, "text": text})
    if not chunk:
        return None
    return {
        "window_start": chunk[0]["start"],
        "window_end": chunk[-1]["end"],
        "text": " ".join(s["text"] for s in chunk),
        "segments": chunk,
    }
