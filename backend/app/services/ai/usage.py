from __future__ import annotations

import logging
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.entities import ApiUsageEvent, ProcessingJob, Project

logger = logging.getLogger(__name__)

_job_id: ContextVar[int | None] = ContextVar("usage_job_id", default=None)
_project_id: ContextVar[int | None] = ContextVar("usage_project_id", default=None)
_live: dict[str, Any] = {
    "provider": None,
    "model": None,
    "job_id": None,
    "project_id": None,
    "outcome": None,
}


def begin_usage(*, job_id: int, project_id: int | None) -> None:
    _job_id.set(job_id)
    _project_id.set(project_id)
    _live.update(provider=None, model=None, job_id=job_id, project_id=project_id, outcome="calling")


def end_usage(job_id: int | None = None) -> None:
    if job_id is not None and _live.get("job_id") not in (None, job_id):
        return
    _job_id.set(None)
    _project_id.set(None)
    _live.update(provider=None, model=None, job_id=None, project_id=None, outcome=None)


def set_live(provider: str, model: str) -> None:
    _live.update(provider=provider, model=model, job_id=_job_id.get(), project_id=_project_id.get(), outcome="calling")


def live_snapshot() -> dict[str, Any]:
    return dict(_live)


def _header_int(headers: Any, *names: str) -> int | None:
    if headers is None:
        return None
    lookup = {str(key).lower(): value for key, value in headers.items()}
    for name in names:
        raw = lookup.get(name)
        if raw is None:
            continue
        try:
            return int(str(raw).split(";")[0].strip().split(",")[0])
        except ValueError:
            continue
    return None


def limits_from_headers(headers: Any) -> tuple[int | None, int | None]:
    remaining = _header_int(
        headers,
        "x-ratelimit-remaining-requests",
        "x-ratelimit-remaining",
        "ratelimit-remaining",
    )
    limit = _header_int(
        headers,
        "x-ratelimit-limit-requests",
        "x-ratelimit-limit",
        "ratelimit-limit",
    )
    return remaining, limit


def record(
    *,
    provider: str,
    model: str,
    outcome: str,
    http_status: int = 0,
    latency_ms: int = 0,
    remaining: int | None = None,
    limit: int | None = None,
) -> None:
    _live.update(
        provider=provider,
        model=model,
        job_id=_job_id.get(),
        project_id=_project_id.get(),
        outcome=outcome,
    )
    db = SessionLocal()
    try:
        db.add(
            ApiUsageEvent(
                provider=provider,
                model=model,
                outcome=outcome,
                http_status=int(http_status or 0),
                latency_ms=max(0, int(latency_ms)),
                remaining=remaining,
                limit=limit,
                job_id=_job_id.get(),
                project_id=_project_id.get(),
            )
        )
        db.commit()
    except Exception:
        logger.debug("Could not persist API usage", exc_info=True)
        db.rollback()
    finally:
        db.close()


def clear_usage(*, project_id: int | None = None) -> None:
    db = SessionLocal()
    try:
        stmt = sa_delete(ApiUsageEvent)
        if project_id is not None:
            stmt = stmt.where(ApiUsageEvent.project_id == project_id)
        db.execute(stmt)
        db.commit()
    finally:
        db.close()


def _minute_key(stamp: datetime) -> datetime:
    aware = stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).replace(second=0, microsecond=0)


def usage_report(*, provider: str | None = None, project_id: int | None = None, hours: int = 1) -> dict[str, Any]:
    window_hours = max(1, min(hours, 168))
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    db = SessionLocal()
    try:
        base = [ApiUsageEvent.created_at >= since]
        if project_id is not None:
            base.append(ApiUsageEvent.project_id == project_id)
        all_rows = list(db.scalars(select(ApiUsageEvent).where(*base).order_by(ApiUsageEvent.id.desc()).limit(4000)))
        rows = [row for row in all_rows if not provider or row.provider == provider]
        logs = rows[:40]
        ok = sum(1 for row in rows if row.outcome == "ok")
        limited = sum(1 for row in rows if row.outcome == "429")
        errors = len(rows) - ok
        latency = [row.latency_ms for row in rows if row.latency_ms]
        by_provider: dict[str, dict[str, Any]] = {}
        by_model: dict[tuple[str, str], dict[str, Any]] = {}
        for row in all_rows:
            bucket = by_provider.setdefault(
                row.provider,
                {"provider": row.provider, "requests": 0, "ok": 0, "limited": 0, "errors": 0, "remaining": None, "limit": None, "last_model": row.model},
            )
            if bucket["requests"] == 0:
                bucket["last_model"] = row.model
                bucket["remaining"] = row.remaining
                bucket["limit"] = row.limit
            bucket["requests"] += 1
            if row.outcome == "ok":
                bucket["ok"] += 1
            elif row.outcome == "429":
                bucket["limited"] += 1
            else:
                bucket["errors"] += 1
        for row in rows:
            model_key = (row.provider, row.model)
            model = by_model.setdefault(
                model_key,
                {"provider": row.provider, "model": row.model, "requests": 0, "ok": 0, "limited": 0, "avg_ms": 0, "_lat": []},
            )
            model["requests"] += 1
            if row.outcome == "ok":
                model["ok"] += 1
            if row.outcome == "429":
                model["limited"] += 1
            model["_lat"].append(row.latency_ms)
        models = []
        for item in by_model.values():
            times = item.pop("_lat")
            item["avg_ms"] = int(sum(times) / len(times)) if times else 0
            models.append(item)
        models.sort(key=lambda row: row["requests"], reverse=True)
        minutes_map: dict[datetime, dict[str, int]] = {}
        now_minute = _minute_key(datetime.now(timezone.utc))
        steps = window_hours * 60
        for offset in range(steps - 1, -1, -1):
            stamp = now_minute - timedelta(minutes=offset)
            minutes_map[stamp] = {"requests": 0, "ok": 0, "limited": 0}
        for row in rows:
            key = _minute_key(row.created_at)
            if key not in minutes_map:
                continue
            minutes_map[key]["requests"] += 1
            if row.outcome == "ok":
                minutes_map[key]["ok"] += 1
            if row.outcome == "429":
                minutes_map[key]["limited"] += 1
        live = live_snapshot()
        project_name = None
        job_id = live.get("job_id")
        if job_id:
            job = db.get(ProcessingJob, int(job_id))
            if job is not None:
                project = db.get(Project, job.project_id)
                project_name = project.name if project else None
                live["project_id"] = job.project_id
        return {
            "live": {**live, "project_name": project_name},
            "totals": {
                "requests": len(rows),
                "ok": ok,
                "limited": limited,
                "errors": errors,
                "avg_ms": int(sum(latency) / len(latency)) if latency else 0,
            },
            "providers": sorted(by_provider.values(), key=lambda row: row["requests"], reverse=True),
            "models": models,
            "series": [
                {
                    "at": stamp.isoformat(),
                    "label": stamp.strftime("%H:%M"),
                    "requests": counts["requests"],
                    "ok": counts["ok"],
                    "limited": counts["limited"],
                }
                for stamp, counts in minutes_map.items()
            ],
            "logs": [
                {
                    "id": row.id,
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                    "provider": row.provider,
                    "model": row.model,
                    "outcome": row.outcome,
                    "http_status": row.http_status,
                    "latency_ms": row.latency_ms,
                    "remaining": row.remaining,
                    "limit": row.limit,
                    "job_id": row.job_id,
                    "project_id": row.project_id,
                }
                for row in logs
            ],
        }
    finally:
        db.close()
