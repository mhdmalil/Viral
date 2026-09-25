from __future__ import annotations

import logging
from typing import Any, Callable

from app.core.config import settings
from app.services.ai.editorial.bounds import PLATFORM_MAX_SECONDS, refine_bounds
from app.services.ai.editorial.pool import assign_clusters, select_strongest
from app.services.ai.editorial.prompts import PASS1_SYSTEM, PASS2_SYSTEM, PASS4_SYSTEM, PASS5_SYSTEM
from app.services.ai.editorial.vibes import filter_wanted_vibes, normalize_vibes, parse_row_vibes
from app.services.ai.chat import AIProviderError
from app.services.ai.provider import AIProvider
from app.services.ai.windows import build_windows
from app.services.jobs.control import raise_if_cancelled, sleep_or_cancel
from app.services.video.timeline import resolve_hook_at

logger = logging.getLogger(__name__)

ProgressFn = Callable[[str, str, int], None]

SAFETY_CAP = 50
DISCOVERY_BAR = 0.4
BATCH = 5
CONTEXT_PAD = 75.0
SPARSE_CHARS = 400
DISCOVERY_CONTEXT_SECONDS = 90.0


def _chunks(rows: list[Any], size: int) -> list[list[Any]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _span(row: dict[str, Any], video_duration: float | None) -> dict[str, Any] | None:
    start = _float(row.get("start"))
    end = _float(row.get("end"))
    if start is None or end is None or end <= start or start < 0:
        return None
    if video_duration is not None and start >= video_duration:
        return None
    if video_duration is not None:
        end = min(end, video_duration)
        if end <= start:
            return None
    return {"start": round(start, 3), "end": round(end, 3)}


def compact_segments(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in transcript.get("segments") or []:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text") or "").strip()
        try:
            start = float(raw.get("start"))
            end = float(raw.get("end"))
        except (TypeError, ValueError):
            continue
        if not text or end <= start:
            continue
        out.append({"start": start, "end": end, "text": text})
    return out


def context_pack(segments: list[dict[str, Any]], start: float, end: float, pad: float = CONTEXT_PAD) -> list[dict[str, Any]]:
    lo = max(0.0, start - pad)
    hi = end + pad
    return [s for s in segments if s["end"] > lo and s["start"] < hi]


def _overlaps_window(span: dict[str, Any], window_start: float, window_end: float) -> bool:
    return float(span["start"]) < window_end and float(span["end"]) > window_start


def discovery_pack(
    segments: list[dict[str, Any]],
    window: dict[str, Any],
    *,
    sparse_chars: int = SPARSE_CHARS,
    pad_seconds: float = DISCOVERY_CONTEXT_SECONDS,
) -> dict[str, Any]:
    window_start = float(window.get("window_start") or 0.0)
    window_end = float(window.get("window_end") or window_start)
    local_segments = list(window.get("segments") or [])
    local_text = str(window.get("text") or "").strip()
    local_chars = len(local_text)
    has_speech = bool(local_segments) or bool(local_text)
    sparse = has_speech and local_chars < sparse_chars
    if sparse:
        lo = window_start - pad_seconds
        hi = window_end + pad_seconds
        context_segments = [row for row in segments if row["end"] > lo and row["start"] < hi]
        context_text = " ".join(row["text"] for row in context_segments)
    else:
        context_segments = local_segments
        context_text = local_text
    return {
        "window_start": window_start,
        "window_end": window_end,
        "transcript": local_text,
        "segments": local_segments,
        "has_speech": has_speech,
        "sparse": sparse,
        "context_expanded": sparse,
        "local_chars": local_chars,
        "local_segments": len(local_segments),
        "context_transcript": context_text,
        "context_segments": context_segments,
    }


def _max_fields(user_max: int | None) -> dict[str, Any]:
    if user_max is None or user_max <= 0:
        return {}
    return {"clip_count_max": int(user_max)}


def _funnel(
    *,
    windows: list[Any],
    seeds: list[dict[str, Any]],
    expanded: list[dict[str, Any]],
    pooled: list[dict[str, Any]],
    validated: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    finals: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "pass1_discovery": len(seeds),
        "pass1_windows": len(windows),
        "pass1_windows_seeded": len({int(row.get("window_index") or 0) for row in seeds}),
        "pass2_expanded": len(expanded),
        "pass3_pool": len(pooled),
        "pass3_clusters": len({int(row.get("cluster_id") or 0) for row in pooled}),
        "pass4_kept": len(validated),
        "pass4_rejected": len(rejected),
        "pass5_selected": len(selected),
        "pass6_final": len(finals),
    }


def run_editorial(
    transcript: dict[str, Any],
    *,
    provider: AIProvider,
    video_duration: float | None,
    user_max: int | None,
    wanted_vibes: list[str] | None = None,
    on_progress: ProgressFn | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    def progress(status: str, message: str, value: int) -> None:
        if on_progress:
            on_progress(status, message, value)

    segments = compact_segments(transcript)
    windows = build_windows(transcript)
    artifacts: dict[str, Any] = {
        "windows": len(windows),
        "seeds": [],
        "expanded": [],
        "validated": [],
        "selected": [],
        "pass4_rejected": [],
        "pass1_windows": [],
        "funnel": {},
    }
    if not windows:
        return [], artifacts

    count_max = _max_fields(user_max)
    wanted = normalize_vibes(wanted_vibes)

    seeds: list[dict[str, Any]] = []
    pass1_windows: list[dict[str, Any]] = []
    progress("DISCOVERING", "Scanning the full transcript", 52)
    for index, window in enumerate(windows):
        raise_if_cancelled()
        if index:
            sleep_or_cancel(0.25)
        progress(
            "DISCOVERING",
            f"Discovery {index + 1}/{len(windows)}",
            min(62, 52 + int(10 * (index + 1) / max(1, len(windows)))),
        )
        packed = discovery_pack(segments, window)
        before = len(seeds)
        try:
            data = provider.editor_json(
                PASS1_SYSTEM,
                {
                    "pass": "discovery",
                    "window_index": index + 1,
                    "window_count": len(windows),
                    "window_start": packed["window_start"],
                    "window_end": packed["window_end"],
                    "transcript": packed["transcript"],
                    "segments": packed["segments"],
                    "sparse": packed["sparse"],
                    "context_expanded": packed["context_expanded"],
                    "context_transcript": packed["context_transcript"],
                    "context_segments": packed["context_segments"],
                    "has_speech": packed["has_speech"],
                    "wanted_vibes": wanted,
                },
            )
        except AIProviderError:
            logger.info("Discovery window %s skipped; trying later windows", index)
            data = {}
        except NotImplementedError:
            raise
        for j, raw in enumerate(data.get("candidates") or []):
            if not isinstance(raw, dict):
                continue
            span = _span(raw, video_duration)
            if span is None:
                continue
            if not _overlaps_window(span, packed["window_start"], packed["window_end"]):
                continue
            score = _float(raw.get("score")) or 0.0
            hook_score = _float(raw.get("hook_score"))
            if hook_score is not None:
                score = round(0.55 * score + 0.45 * hook_score, 4)
            if score < DISCOVERY_BAR:
                continue
            labels = parse_row_vibes(raw)
            seeds.append(
                {
                    "id": f"d{index}_{j}",
                    "start": span["start"],
                    "end": span["end"],
                    "seed_start": span["start"],
                    "seed_end": span["end"],
                    "score": round(score, 4),
                    "hook_score": round(hook_score if hook_score is not None else score, 4),
                    "hook_at": resolve_hook_at(
                        _float(raw.get("hook_at")),
                        span["start"],
                        span["end"],
                        packed["window_start"],
                    ),
                    "hook_line": str(raw.get("hook_line") or "").strip()[:80],
                    "reason": str(raw.get("reason") or "").strip()[:500],
                    "topic": str(raw.get("topic") or "").strip()[:80],
                    "vibe": labels[0] if labels else "",
                    "vibes": labels,
                    "window_index": index,
                }
            )
        seed_count = len(seeds) - before
        row = {
            "window": index + 1,
            "start": packed["window_start"],
            "end": packed["window_end"],
            "chars": packed["local_chars"],
            "segments": packed["local_segments"],
            "context_expanded": packed["context_expanded"],
            "seeds": seed_count,
        }
        pass1_windows.append(row)
        logger.info(
            "Discovery window %s/%s %.1f-%.1fs chars=%s segments=%s context_expanded=%s seeds=%s",
            index + 1,
            len(windows),
            packed["window_start"],
            packed["window_end"],
            packed["local_chars"],
            packed["local_segments"],
            packed["context_expanded"],
            seed_count,
        )
    artifacts["pass1_windows"] = pass1_windows
    artifacts["seeds"] = seeds
    if not seeds:
        artifacts["funnel"] = _funnel(
            windows=windows, seeds=seeds, expanded=[], pooled=[], validated=[], rejected=[], selected=[], finals=[]
        )
        return [], artifacts

    expanded: list[dict[str, Any]] = []
    progress("EXPANDING", "Expanding candidate context", 64)
    for batch_i, batch in enumerate(_chunks(seeds, BATCH)):
        raise_if_cancelled()
        if batch_i:
            sleep_or_cancel(0.25)
        items = []
        for seed in batch:
            items.append(
                {
                    "id": seed["id"],
                    "start": seed["start"],
                    "end": seed["end"],
                    "reason": seed["reason"],
                    "vibe": seed.get("vibe"),
                    "vibes": seed.get("vibes") or [],
                    "context": context_pack(segments, seed["start"], seed["end"]),
                }
            )
        try:
            data = provider.editor_json(PASS2_SYSTEM, {"pass": "expand", "wanted_vibes": wanted, "items": items})
        except AIProviderError:
            logger.info("Expand batch %s skipped; keeping seed bounds", batch_i)
            data = {}
        by_id = {str(r.get("id")): r for r in data.get("results") or [] if isinstance(r, dict)}
        for seed in batch:
            row = by_id.get(seed["id"]) or {"action": "keep", **seed}
            if str(row.get("action") or "keep").lower() == "drop":
                continue
            span = _span(row, video_duration) or {"start": seed["start"], "end": seed["end"]}
            item = dict(seed)
            item.update(span)
            item["setup_start"] = _float(row.get("setup_start"))
            item["hook_at"] = resolve_hook_at(_float(row.get("hook_at")), item["start"], item["end"])
            if item["hook_at"] is None:
                item["hook_at"] = resolve_hook_at(seed.get("hook_at"), item["start"], item["end"])
            item["hook_line"] = str(row.get("hook_line") or seed.get("hook_line") or "").strip()[:80]
            hook_score = _float(row.get("hook_score"))
            if hook_score is None:
                hook_score = _float(seed.get("hook_score"))
            item["hook_score"] = round(hook_score if hook_score is not None else float(item.get("score") or 0), 4)
            item["payoff_end"] = _float(row.get("payoff_end"))
            item["standalone"] = bool(row.get("standalone", True))
            item["reason"] = str(row.get("reason") or seed["reason"])[:500]
            labels = parse_row_vibes(row) or list(seed.get("vibes") or [])
            if not labels and seed.get("vibe"):
                labels = parse_row_vibes({"vibe": seed.get("vibe")})
            item["vibes"] = labels
            item["vibe"] = labels[0] if labels else str(seed.get("vibe") or "")
            item["seed_start"] = seed.get("seed_start", seed["start"])
            item["seed_end"] = seed.get("seed_end", seed["end"])
            expanded.append(item)
    pooled = assign_clusters(expanded)
    artifacts["expanded"] = pooled
    if not pooled:
        artifacts["funnel"] = _funnel(
            windows=windows,
            seeds=seeds,
            expanded=expanded,
            pooled=pooled,
            validated=[],
            rejected=[],
            selected=[],
            finals=[],
        )
        return [], artifacts

    validated: list[dict[str, Any]] = []
    pass4_rejected: list[dict[str, Any]] = []
    progress("VALIDATING", "Editorial validation", 72)
    for batch_i, batch in enumerate(_chunks(pooled, BATCH)):
        raise_if_cancelled()
        if batch_i:
            sleep_or_cancel(0.25)
        items = [
            {
                "id": row["id"],
                "start": row["start"],
                "end": row["end"],
                "reason": row["reason"],
                "topic": row.get("topic"),
                "vibe": row.get("vibe"),
                "vibes": row.get("vibes") or [],
                "context": context_pack(segments, row["start"], row["end"]),
                "siblings": [{"id": o["id"], "reason": o["reason"]} for o in batch if o["id"] != row["id"]],
            }
            for row in batch
        ]
        try:
            data = provider.editor_json(PASS4_SYSTEM, {"pass": "validate", "wanted_vibes": wanted, "items": items})
        except AIProviderError:
            logger.info("Validate batch %s skipped; using discovery scores", batch_i)
            data = {}
        by_id = {str(r.get("id")): r for r in data.get("results") or [] if isinstance(r, dict)}
        if not by_id:
            for row in batch:
                span = _span(row, video_duration)
                if span is None:
                    pass4_rejected.append(
                        {
                            "id": row["id"],
                            "quality": round(float(row.get("score") or 0), 4),
                            "reason": "invalid time range",
                        }
                    )
                    continue
                kept = dict(row)
                kept["quality"] = round(float(row.get("score") or 0), 4)
                validated.append(kept)
            continue
        for row in batch:
            verdict = by_id.get(row["id"]) or {}
            quality = _float(verdict.get("quality"))
            if quality is None:
                quality = float(row.get("score") or 0)
            span = _span(row, video_duration)
            if span is None:
                pass4_rejected.append(
                    {
                        "id": row["id"],
                        "quality": round(quality, 4),
                        "reason": str(verdict.get("reason") or "invalid time range")[:500],
                    }
                )
                continue
            if str(verdict.get("verdict") or "keep").lower() == "reject":
                pass4_rejected.append(
                    {
                        "id": row["id"],
                        "quality": round(quality, 4),
                        "reason": str(verdict.get("reason") or "rejected")[:500],
                    }
                )
                continue
            kept = dict(row)
            kept["quality"] = round(quality, 4)
            kept["reason"] = str(verdict.get("reason") or row["reason"])[:500]
            labels = parse_row_vibes(verdict) or parse_row_vibes(row)
            kept["vibes"] = labels
            kept["vibe"] = labels[0] if labels else str(row.get("vibe") or "")
            validated.append(kept)
    artifacts["validated"] = validated
    artifacts["pass4_rejected"] = pass4_rejected
    validated = filter_wanted_vibes(validated, wanted)
    if not validated:
        artifacts["funnel"] = _funnel(
            windows=windows,
            seeds=seeds,
            expanded=expanded,
            pooled=pooled,
            validated=validated,
            rejected=pass4_rejected,
            selected=[],
            finals=[],
        )
        return [], artifacts

    progress("SELECTING", "Selecting strongest distinct clips", 80)
    sleep_or_cancel(0.25)
    ranked_cards = sorted(validated, key=lambda row: float(row.get("quality") or 0), reverse=True)
    card_rows = ranked_cards[: min(len(ranked_cards), SAFETY_CAP)]
    cards = [
        {
            "id": row["id"],
            "start": row["start"],
            "end": row["end"],
            "quality": row["quality"],
            "hook_score": row.get("hook_score"),
            "hook_line": row.get("hook_line"),
            "topic": row.get("topic"),
            "vibe": row.get("vibe"),
            "vibes": row.get("vibes") or [],
            "reason": row["reason"],
            "cluster_id": row.get("cluster_id"),
        }
        for row in card_rows
    ]
    keep_ids: set[str] | None = None
    try:
        data = provider.editor_json(PASS5_SYSTEM, {"pass": "select", **count_max, "cards": cards, "wanted_vibes": wanted})
        raw_ids = data.get("keep_ids")
        if isinstance(raw_ids, list):
            keep_ids = {str(i) for i in raw_ids}
    except AIProviderError:
        logger.info("Select pass skipped; ranking validated clips by quality")
        keep_ids = None
    cap = SAFETY_CAP
    if user_max is not None and user_max > 0:
        cap = min(cap, int(user_max))
    selected = select_strongest(validated, cap, preferred_ids=keep_ids)
    artifacts["selected"] = selected

    progress("REFINING", "Snapping clip boundaries to speech", 86)
    finals: list[dict[str, Any]] = []
    for row in selected:
        raise_if_cancelled()
        bounds = refine_bounds(
            float(row["start"]),
            float(row["end"]),
            transcript,
            setup_start=row.get("setup_start"),
            payoff_end=row.get("payoff_end"),
            hook_at=row.get("hook_at"),
            video_duration=video_duration,
            platform_max=float(getattr(settings, "platform_max_seconds", PLATFORM_MAX_SECONDS)),
        )
        if bounds is None:
            continue
        finals.append(
            {
                "start": bounds["start"],
                "end": bounds["end"],
                "score": float(row.get("quality") or row.get("score") or 0),
                "reason": row.get("reason") or "",
                "signals": {
                    "topic": row.get("topic"),
                    "vibe": (parse_row_vibes(row) or [None])[0],
                    "vibes": parse_row_vibes(row),
                    "cluster_id": row.get("cluster_id"),
                    "hook_at": resolve_hook_at(row.get("hook_at"), bounds["start"], bounds["end"]),
                    "hook_line": row.get("hook_line") or "",
                    "hook_score": row.get("hook_score"),
                },
                "id": row["id"],
            }
        )
    finals.sort(key=lambda r: r["start"])
    artifacts["funnel"] = _funnel(
        windows=windows,
        seeds=seeds,
        expanded=expanded,
        pooled=pooled,
        validated=validated,
        rejected=pass4_rejected,
        selected=selected,
        finals=finals,
    )
    return finals, artifacts
