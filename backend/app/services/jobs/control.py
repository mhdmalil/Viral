from __future__ import annotations

import threading
import time

_events: dict[int, threading.Event] = {}
_lock = threading.Lock()
_active_job_id: int | None = None


class JobCancelled(Exception):
    """Generate was stopped from the UI."""


def live_job_id() -> int | None:
    with _lock:
        return _active_job_id


def begin_job(job_id: int) -> None:
    global _active_job_id
    with _lock:
        _active_job_id = job_id
        _events.setdefault(job_id, threading.Event()).clear()


def end_job(job_id: int) -> None:
    global _active_job_id
    with _lock:
        if _active_job_id == job_id:
            _active_job_id = None
        _events.pop(job_id, None)


def request_cancel(job_id: int) -> None:
    with _lock:
        _events.setdefault(job_id, threading.Event()).set()


def is_cancelled(job_id: int | None = None) -> bool:
    with _lock:
        jid = job_id if job_id is not None else _active_job_id
        if jid is None:
            return False
        event = _events.get(jid)
        return bool(event and event.is_set())


def raise_if_cancelled(job_id: int | None = None) -> None:
    if is_cancelled(job_id):
        raise JobCancelled()


def sleep_or_cancel(seconds: float, job_id: int | None = None) -> None:
    deadline = time.monotonic() + max(0.0, seconds)
    while True:
        raise_if_cancelled(job_id)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(0.25, remaining))
