from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class CandidateParseError(Exception):
    pass


def parse_candidates_json(raw: str) -> list[dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        raise CandidateParseError("Empty model response.")
    match = _FENCE.search(text)
    if match:
        text = match.group(1).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise CandidateParseError("Response was not JSON.")
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise CandidateParseError("Response was not JSON.") from exc
    if not isinstance(payload, dict) or "candidates" not in payload:
        raise CandidateParseError("JSON missing candidates.")
    rows = payload["candidates"]
    if not isinstance(rows, list):
        raise CandidateParseError("candidates must be a list.")
    return rows


def parse_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise CandidateParseError("Empty model response.")
    match = _FENCE.search(text)
    if match:
        text = match.group(1).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise CandidateParseError("Response was not JSON.")
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise CandidateParseError("Response was not JSON.") from exc
    if not isinstance(payload, dict):
        raise CandidateParseError("JSON must be an object.")
    return payload


def validate_candidate(row: Any, video_duration: float | None) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    try:
        start = float(row["start"])
        end = float(row["end"])
        score = float(row["score"])
    except (KeyError, TypeError, ValueError):
        return None
    if end <= start or start < 0 or score < 0 or score > 1:
        return None
    if video_duration is not None and start >= video_duration:
        return None
    if video_duration is not None:
        end = min(end, video_duration)
        if end <= start:
            return None
    signals = row.get("signals") if isinstance(row.get("signals"), dict) else {}
    reason = str(row.get("reason") or "").strip()[:500]
    return {
        "start": round(start, 3),
        "end": round(end, 3),
        "score": round(score, 4),
        "signals": {str(k): v for k, v in signals.items()},
        "reason": reason,
    }
