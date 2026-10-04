from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.video.timeline import Piece

JOIN_FADE_S = 0.22
JOIN_ZOOM_S = 0.36
JOIN_MIN_S = 0.08
PUNCH_SECONDS = 2.0
PUNCH_ZOOM = 1.10
HOOK_TITLE_IN = 0.40
CANVAS_W = 1080
CANVAS_H = 1920


def join_into(into_hook: bool) -> tuple[str, float]:
    """Ordinary joins fade. Only a join that lands on the hook uses a stronger zoom."""
    if into_hook:
        return ("zoomin", JOIN_ZOOM_S)
    return ("fade", JOIN_FADE_S)


def clamp_join(duration: float, left: float, right: float) -> float:
    held = min(float(duration), max(0.0, float(left)) * 0.35, max(0.0, float(right)) * 0.35)
    if held < JOIN_MIN_S:
        return 0.0
    return round(held, 3)


def punch_in_chain(*, width: int = CANVAS_W, height: int = CANVAS_H) -> str:
    """Slow zoom-in over the first couple of seconds, then hold.

    crop w/h cannot use t (they are evaluated once). Scale the canvas per frame, then crop back.
    """
    grow = round(PUNCH_ZOOM - 1.0, 2)
    seconds = PUNCH_SECONDS
    w = int(width)
    h = int(height)
    return (
        f",scale=w='trunc({w}*(1+{grow}*min(1\\,t/{seconds}))/2)*2'"
        f":h='trunc({h}*(1+{grow}*min(1\\,t/{seconds}))/2)*2'"
        f":eval=frame"
        f",crop={w}:{h}:(in_w-{w})/2:(in_h-{h})/2"
    )


def hook_title_motion(y: int) -> tuple[str, str]:
    """Slide/fade the hook title in instead of drawing it fully formed."""
    fade = HOOK_TITLE_IN
    y_expr = f"{int(y)}+if(lt(t\\,{fade})\\,({fade}-t)/{fade}*40\\,0)"
    alpha = f"if(lt(t\\,{fade})\\,t/{fade}\\,1)"
    return y_expr, alpha


def xfade_offsets(pieces: list[Piece]) -> list[tuple[str, float, float]]:
    """(transition, duration, offset) for each join after the first piece."""
    steps: list[tuple[str, float, float]] = []
    if len(pieces) < 2:
        return steps
    cursor = pieces[0].duration
    for piece in pieces[1:]:
        held = float(piece.join_seconds or 0.0)
        name = piece.join or "fade"
        if held >= JOIN_MIN_S:
            steps.append((name, held, max(0.0, cursor - held)))
            cursor = cursor + piece.duration - held
        else:
            cursor = cursor + piece.duration
    return steps
