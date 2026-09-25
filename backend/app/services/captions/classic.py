from __future__ import annotations

from typing import Any

from app.services.video.timeline import Piece, hook_until as open_until


def build_cues(words_or_segments: list[dict[str, Any]], clip_start: float, clip_end: float) -> list[dict[str, Any]]:
    """Classic lower-third cues, times relative to the clip (0 = first frame)."""
    cues: list[dict[str, Any]] = []
    buf: list[str] = []
    cue_start: float | None = None
    cue_end = 0.0
    for item in words_or_segments:
        try:
            abs_start = float(item.get("start"))
            abs_end = float(item.get("end"))
        except (TypeError, ValueError):
            continue
        text = str(item.get("word") or item.get("text") or "").strip()
        if not text or abs_end <= clip_start or abs_start >= clip_end:
            continue
        rel_s = max(0.0, abs_start - clip_start)
        rel_e = max(rel_s + 0.05, min(abs_end, clip_end) - clip_start)
        if cue_start is None:
            cue_start = rel_s
        buf.append(text)
        cue_end = rel_e
        if len(buf) >= 4 or sum(len(part) for part in buf) >= 20 or (cue_end - cue_start) >= 1.4:
            cues.append({"start": cue_start, "end": cue_end, "text": " ".join(buf)})
            buf = []
            cue_start = None
    if buf and cue_start is not None:
        cues.append({"start": cue_start, "end": max(cue_end, cue_start + 0.4), "text": " ".join(buf)})
    return cues


def build_cues_on_timeline(
    words_or_segments: list[dict[str, Any]],
    pieces: list[Piece],
    *,
    skip_open: bool = False,
) -> list[dict[str, Any]]:
    """Cues in output time. Spoken words stay in captions for the whole cut."""
    windows = pieces[1:] if skip_open and len(pieces) > 1 else pieces
    if not windows:
        return []
    cues: list[dict[str, Any]] = []
    for piece in windows:
        for cue in build_cues(words_or_segments, piece.src_start, piece.src_end):
            cues.append(
                {
                    "start": piece.out_start + float(cue["start"]),
                    "end": piece.out_start + float(cue["end"]),
                    "text": cue["text"],
                }
            )
    cues.sort(key=lambda row: row["start"])
    if skip_open and len(pieces) == 1:
        t0 = open_until(pieces)
        kept: list[dict[str, Any]] = []
        for cue in cues:
            if float(cue["end"]) <= t0:
                continue
            kept.append({**cue, "start": max(float(cue["start"]), t0)})
        return kept
    return cues


def _punch_last_word(text: str) -> str:
    parts = str(text).replace("\n", " ").strip().split()
    if not parts:
        return ""
    safe = [part.replace("\\", r"\\") for part in parts]
    if len(safe) < 2:
        return safe[0]
    return " ".join(safe[:-1]) + r" {\c&H0000FFFF&\3c&H00000000&\bord3}" + safe[-1]


def cues_to_ass(
    cues: list[dict[str, Any]],
    *,
    margin_v: int,
    style: str | None = "classic",
    punch: bool = True,
) -> str:
    from app.services.captions.styles import normalize_style

    from app.services.video.layout import BOTTOM_UI_SAFE, CANVAS_H, CANVAS_W, CAPTION_MARGIN_LR, CAPTION_PX

    kind = normalize_style(style)
    _ = kind
    mv = max(8, min(800, int(margin_v if margin_v is not None else BOTTOM_UI_SAFE)))
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {CANVAS_W}\n"
        f"PlayResY: {CANVAS_H}\n"
        "WrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,Arial,{CAPTION_PX},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,"
        f"100,100,0,0,1,3,0,2,{CAPTION_MARGIN_LR},{CAPTION_MARGIN_LR},{mv},1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = [header.rstrip("\n")]
    for cue in cues:
        raw = str(cue["text"]).replace("\n", " ").strip()
        if punch:
            text = _punch_last_word(raw)
        else:
            text = raw.replace("\\", r"\\")
        lines.append(
            f"Dialogue: 0,{_ass_ts(cue['start'])},{_ass_ts(cue['end'])},Default,,0,0,0,,{text}"
        )
    return "\n".join(lines) + "\n"


def _ass_ts(seconds: float) -> str:
    total = max(0.0, float(seconds))
    h = int(total // 3600)
    m = int((total % 3600) // 60)
    s = total % 60
    return f"{h}:{m:02d}:{s:05.2f}"
