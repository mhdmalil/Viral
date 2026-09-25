from __future__ import annotations

from typing import Any


WINDOW_SECONDS = 120.0
OVERLAP_SECONDS = 15.0


def build_windows(transcript: dict[str, Any], window_seconds: float = WINDOW_SECONDS) -> list[dict[str, Any]]:
    segments = transcript.get("segments") or []
    compact: list[dict[str, Any]] = []
    for raw in segments:
        text = str(raw.get("text") or "").strip()
        try:
            start = float(raw.get("start"))
            end = float(raw.get("end"))
        except (TypeError, ValueError):
            continue
        if not text or end <= start:
            continue
        compact.append({"start": start, "end": end, "text": text})
    if not compact:
        full = str(transcript.get("text") or "").strip()
        if not full:
            return []
        return [
            {
                "window_start": 0.0,
                "window_end": float(transcript.get("duration") or 0.0),
                "text": full,
                "segments": [],
            }
        ]

    windows: list[dict[str, Any]] = []
    i = 0
    while i < len(compact):
        start = compact[i]["start"]
        limit = start + window_seconds
        chunk: list[dict[str, Any]] = []
        j = i
        while j < len(compact) and compact[j]["start"] < limit:
            chunk.append(compact[j])
            j += 1
        if not chunk:
            i += 1
            continue
        windows.append(
            {
                "window_start": chunk[0]["start"],
                "window_end": chunk[-1]["end"],
                "text": " ".join(s["text"] for s in chunk),
                "segments": chunk,
            }
        )
        if j >= len(compact):
            break
        next_start = chunk[-1]["end"] - OVERLAP_SECONDS
        i += 1
        while i < len(compact) and compact[i]["start"] < next_start:
            i += 1
        if i >= j:
            i = j
    return windows
