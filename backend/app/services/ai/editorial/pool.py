from __future__ import annotations

from typing import Any

from app.services.ai.editorial.vibes import parse_row_vibes


def overlap_ratio(a: dict[str, Any], b: dict[str, Any]) -> float:
    start = max(float(a["start"]), float(b["start"]))
    end = min(float(a["end"]), float(b["end"]))
    overlap = max(0.0, end - start)
    shorter = min(float(a["end"]) - float(a["start"]), float(b["end"]) - float(b["start"]))
    if shorter <= 0:
        return 0.0
    return overlap / shorter


def assign_clusters(rows: list[dict[str, Any]], threshold: float = 0.5) -> list[dict[str, Any]]:
    clustered: list[dict[str, Any]] = []
    next_id = 0
    for row in rows:
        item = dict(row)
        matched: int | None = None
        for other in clustered:
            if overlap_ratio(item, other) > threshold:
                matched = int(other["cluster_id"])
                break
        if matched is None:
            matched = next_id
            next_id += 1
        item["cluster_id"] = matched
        clustered.append(item)
    return clustered


def one_per_cluster(rows: list[dict[str, Any]], score_key: str = "quality") -> list[dict[str, Any]]:
    best: dict[int, dict[str, Any]] = {}
    for row in rows:
        cid = int(row.get("cluster_id") or 0)
        current = best.get(cid)
        if current is None or float(row.get(score_key) or 0) > float(current.get(score_key) or 0):
            best[cid] = row
    return sorted(best.values(), key=lambda r: float(r.get(score_key) or 0), reverse=True)


def _quality(row: dict[str, Any], score_key: str) -> float:
    return float(row.get(score_key) or row.get("score") or 0)


def _standalone_rank(row: dict[str, Any]) -> float:
    flag = row.get("standalone")
    if flag is None:
        return 1.0
    return 1.0 if bool(flag) else 0.0


def _hook_rank(row: dict[str, Any]) -> float:
    value = row.get("hook_score")
    if value is None:
        signals = row.get("signals")
        if isinstance(signals, dict):
            value = signals.get("hook_score") or signals.get("hook")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def select_strongest(
    rows: list[dict[str, Any]],
    limit: int,
    *,
    score_key: str = "quality",
    overlap_threshold: float = 0.5,
    preferred_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Quality-first ceiling pick. Dedupes the same moment; does not fill a quota."""
    if limit <= 0 or not rows:
        return []
    preferred = preferred_ids or set()
    remaining = list(rows)
    picked: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    used_vibes: set[str] = set()
    used_topics: set[str] = set()

    def vibe_of(row: dict[str, Any]) -> str:
        labels = parse_row_vibes(row)
        return ",".join(labels) if labels else "mixed"

    def topic_of(row: dict[str, Any]) -> str:
        return (str(row.get("topic") or "").strip().lower()[:48] or "general")

    while remaining and len(picked) < limit:
        remaining.sort(
            key=lambda row: (
                _hook_rank(row),
                _quality(row, score_key),
                _standalone_rank(row),
                0.0 if vibe_of(row) in used_vibes else 1.0,
                0.0 if topic_of(row) in used_topics else 1.0,
                1.0 if str(row.get("id") or "") in preferred else 0.0,
            ),
            reverse=True,
        )
        candidate = remaining.pop(0)
        cid = str(candidate.get("id") or "")
        if cid in used_ids:
            continue
        if any(overlap_ratio(candidate, other) > overlap_threshold for other in picked):
            continue
        picked.append(candidate)
        if cid:
            used_ids.add(cid)
        used_vibes.add(vibe_of(candidate))
        used_topics.add(topic_of(candidate))
    return picked


def take_non_overlapping(
    rows: list[dict[str, Any]],
    limit: int,
    *,
    score_key: str = "quality",
    threshold: float = 0.5,
    use_seed_span: bool = False,
) -> list[dict[str, Any]]:
    del use_seed_span
    ranked = sorted(rows, key=lambda row: _quality(row, score_key), reverse=True)
    return select_strongest(ranked, limit, score_key=score_key, overlap_threshold=threshold)


def spread_select(
    rows: list[dict[str, Any]],
    limit: int,
    *,
    duration: float | None = None,
    preferred_ids: set[str] | None = None,
    score_key: str = "quality",
    overlap_threshold: float = 0.5,
    min_gap: float = 12.0,
    use_seed_span: bool = True,
) -> list[dict[str, Any]]:
    """Compatibility wrapper. Runtime spreading is not applied."""
    del duration, min_gap, use_seed_span
    return select_strongest(
        rows,
        limit,
        score_key=score_key,
        overlap_threshold=overlap_threshold,
        preferred_ids=preferred_ids,
    )
