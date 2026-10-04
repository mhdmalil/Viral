from __future__ import annotations

from typing import Any

from app.services.video.timeline import Piece, hook_until as open_until


def build_cues(words_or_segments: list[dict[str, Any]], clip_start: float, clip_end: float) -> list[dict[str, Any]]:
    """Classic lower-third cues, times relative to the clip (0 = first frame)."""
    cues: list[dict[str, Any]] = []
    buf: list[dict[str, Any]] = []
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
        buf.append({"text": text, "start": rel_s, "end": rel_e})
        cue_end = rel_e
        if len(buf) >= 4 or sum(len(part["text"]) for part in buf) >= 20 or (cue_end - cue_start) >= 1.4:
            cues.append(_cue(cue_start, cue_end, buf))
            buf = []
            cue_start = None
    if buf and cue_start is not None:
        cues.append(_cue(cue_start, max(cue_end, cue_start + 0.4), buf))
    return cues


def _cue(start: float, end: float, words: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "start": start,
        "end": end,
        "text": " ".join(str(word["text"]) for word in words),
        "words": words,
    }


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
            shifted = []
            for word in cue.get("words") or []:
                shifted.append(
                    {
                        "text": word["text"],
                        "start": piece.out_start + float(word["start"]),
                        "end": piece.out_start + float(word["end"]),
                    }
                )
            cues.append(
                {
                    "start": piece.out_start + float(cue["start"]),
                    "end": piece.out_start + float(cue["end"]),
                    "text": cue["text"],
                    "words": shifted,
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


def _ass_word(token: str) -> str:
    return str(token).replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def _spoken_line(words: list[dict[str, Any]], active: int) -> str:
    parts: list[str] = []
    for index, word in enumerate(words):
        token = _ass_word(str(word.get("text") or ""))
        if not token:
            continue
        if index > active:
            continue
        if index == active:
            parts.append(r"{\c&H0000FFFF&\fscx108\fscy108}" + token + r"{\c&H00FFFFFF&\fscx100\fscy100}")
        else:
            parts.append(token)
    return " ".join(parts)


def cues_to_ass(
    cues: list[dict[str, Any]],
    *,
    margin_v: int,
    style: str | None = "classic",
    punch: bool = True,
) -> str:
    from app.services.captions.styles import normalize_style

    from app.services.video.layout import BOTTOM_UI_SAFE, CANVAS_H, CANVAS_W

    kind = normalize_style(style)
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
        f"{_ass_style_line(kind, mv)}\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = [header.rstrip("\n")]
    for cue in cues:
        spoken = cue.get("words") if isinstance(cue.get("words"), list) else None
        if spoken:
            for index, word in enumerate(spoken):
                text = _spoken_line(spoken, index)
                if not text:
                    continue
                lines.append(
                    f"Dialogue: 0,{_ass_ts(word['start'])},{_ass_ts(word['end'])},Default,,0,0,0,,{text}"
                )
            continue
        raw = str(cue["text"]).replace("\n", " ").strip()
        text = _spoken_line([{"text": part} for part in raw.split()], max(0, len(raw.split()) - 1)) if punch and raw else raw.replace("\\", r"\\")
        if not text:
            continue
        lines.append(
            f"Dialogue: 0,{_ass_ts(cue['start'])},{_ass_ts(cue['end'])},Default,,0,0,0,,{text}"
        )
    return "\n".join(lines) + "\n"


def _ass_style_line(kind: str, mv: int) -> str:
    from app.services.video.layout import CAPTION_MARGIN_LR, CAPTION_PX

    if kind == "boxed":
        return (
            f"Style: Default,Arial,{CAPTION_PX},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,"
            f"100,100,0,0,3,4,0,2,{CAPTION_MARGIN_LR},{CAPTION_MARGIN_LR},{mv},1"
        )
    if kind == "bold":
        return (
            f"Style: Default,Arial,{CAPTION_PX},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,"
            f"100,100,0,0,1,5,1,2,{CAPTION_MARGIN_LR},{CAPTION_MARGIN_LR},{mv},1"
        )
    return (
        f"Style: Default,Arial,{CAPTION_PX},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,"
        f"100,100,0,0,1,3,0,2,{CAPTION_MARGIN_LR},{CAPTION_MARGIN_LR},{mv},1"
    )


def _ass_ts(seconds: float) -> str:
    total = max(0.0, float(seconds))
    h = int(total // 3600)
    m = int((total % 3600) // 60)
    s = total % 60
    return f"{h}:{m:02d}:{s:05.2f}"
