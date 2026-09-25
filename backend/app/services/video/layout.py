from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, NamedTuple

CANVAS_W = 1080
CANVAS_H = 1920
TOP_BAR_H = 112
VIDEO_AREA_Y = TOP_BAR_H
VIDEO_AREA_H = CANVAS_H - TOP_BAR_H  # 1808
TOP_SAFE_Y = 150
BOTTOM_UI_SAFE = 420

HOOK_FONT = 112
HOOK_FONT_MIN = 56
HOOK_BOX = 16
HOOK_Y = 360
HOOK_MAX_W = 1020
HOOK_CHAR_W = 0.58
CAPTION_PX = 52
CAPTION_MARGIN_LR = 158
SOCIAL_ICON = 44
SOCIAL_GAP = 18
SOCIAL_INSET = 42
SOCIAL_MIN_X = 52
SOCIAL_FROM_VIDEO_TOP = 80
# Hook is canvas-fixed at HOOK_Y; tall sources put socials at picture-top+80, which hits the line.
SOCIAL_BELOW_HOOK = 28
PICTURE_SIZE = 96
_SWEARS = frozenset(
    {
        "fuck",
        "fucking",
        "fucked",
        "fucker",
        "motherfucker",
        "motherfucking",
        "shit",
        "shitty",
        "bullshit",
        "bitch",
        "bitches",
        "asshole",
        "assholes",
        "bastard",
        "bastards",
        "dick",
        "dicks",
        "cock",
        "cocks",
        "cunt",
        "cunts",
        "piss",
        "pissing",
        "whore",
        "whores",
        "slut",
        "sluts",
        "wanker",
        "bollocks",
        "damn",
        "dammit",
        "goddamn",
    }
)


class FittedVideo(NamedTuple):
    """Source picture on the 1080×1920 canvas after fit (no crop, no stretch)."""

    x: int
    y: int
    w: int
    h: int
    scale: float

    @property
    def bottom(self) -> int:
        return self.y + self.h


def fit_source(src_w: int, src_h: int) -> FittedVideo:
    width = max(2, int(src_w or CANVAS_W))
    height = max(2, int(src_h or VIDEO_AREA_H))
    scale = min(CANVAS_W / width, VIDEO_AREA_H / height)
    video_w = max(2, round(width * scale))
    video_h = max(2, round(height * scale))
    video_x = (CANVAS_W - video_w) // 2
    video_y = VIDEO_AREA_Y + (VIDEO_AREA_H - video_h) // 2
    return FittedVideo(video_x, video_y, video_w, video_h, scale)


def fitted_content_rect(src_w: int, src_h: int) -> tuple[int, int, int, int]:
    video = fit_source(src_w, src_h)
    return video.x, video.y, video.w, video.h


def hook_draw_y(
    content_top: int | None = None,
    *,
    lines: int = 1,
    font_size: int = HOOK_FONT,
) -> int:
    """Hook sits below TikTok's For You header, on the picture — not in the cropped top strip."""
    del content_top, lines, font_size
    return HOOK_Y


def social_x(video: FittedVideo) -> int:
    return max(SOCIAL_MIN_X, int(video.x) + SOCIAL_INSET)


def social_placement(video: FittedVideo, index: int, icon: int = SOCIAL_ICON) -> tuple[int, int] | None:
    """Left stack on the fitted picture, below the hook, clamped to TikTok bottom UI."""
    size = max(32, int(icon))
    below_hook = HOOK_Y + (2 * (HOOK_FONT + 8)) + SOCIAL_BELOW_HOOK
    first_y = max(TOP_SAFE_Y, int(video.y) + SOCIAL_FROM_VIDEO_TOP, below_hook)
    y = first_y + int(index) * (size + SOCIAL_GAP)
    limit = int(video.bottom) - BOTTOM_UI_SAFE
    if y + size >= limit:
        return None
    if y + size > CANVAS_H - BOTTOM_UI_SAFE:
        return None
    return social_x(video), y


def social_stack_xy(video: FittedVideo, index: int, icon: int = SOCIAL_ICON) -> tuple[int, int] | None:
    return social_placement(video, index, icon)


def socials_row_y(icon: int = 48) -> int:
    video = FittedVideo(0, VIDEO_AREA_Y, CANVAS_W, VIDEO_AREA_H, 1.0)
    pos = social_placement(video, 0, icon)
    return pos[1] if pos else TOP_SAFE_Y


def caption_margin_v(content_bottom: int | None = None) -> int:
    """ASS MarginV in 1080×1920 PlayRes — always the canvas bottom UI safe, never the picture."""
    del content_bottom
    return BOTTOM_UI_SAFE


def picture_slot(video: FittedVideo, content_bottom: int | None = None) -> tuple[int, int, int, int] | None:
    del content_bottom
    pos = social_placement(video, 0, PICTURE_SIZE)
    if pos is None:
        return None
    return pos[0], pos[1], PICTURE_SIZE, PICTURE_SIZE


def vertical_canvas_vf(crop: tuple[int, int, int, int] | None = None) -> str:
    del crop
    return (
        f"scale={CANVAS_W}:{VIDEO_AREA_H}:force_original_aspect_ratio=decrease,"
        f"pad={CANVAS_W}:{VIDEO_AREA_H}:(ow-iw)/2:(oh-ih)/2:black,"
        f"pad={CANVAS_W}:{CANVAS_H}:0:{TOP_BAR_H}:black,"
        "eq=contrast=1.06:saturation=1.08:gamma=0.98"
    )


def extract_hook_line(
    words_or_segments: list[dict[str, Any]],
    clip_start: float,
    clip_end: float,
    hook_at: float | None = None,
    preferred: str | None = None,
) -> str:
    teased = clean_hook_line(preferred or "")
    if len(teased.split()) >= 2:
        return teased
    origin = float(hook_at) if hook_at is not None else float(clip_start)
    window_end = float(clip_end)
    bits: list[str] = []
    for item in words_or_segments:
        try:
            start = float(item.get("start"))
            end = float(item.get("end"))
        except (TypeError, ValueError):
            continue
        token = str(item.get("word") or item.get("text") or "").strip()
        if not token or end <= origin - 0.08 or start >= window_end:
            continue
        bits.append(token)
        if len(bits) >= 8:
            break
    if not bits:
        for item in words_or_segments:
            token = str(item.get("word") or item.get("text") or "").strip()
            if token:
                bits.append(token)
            if len(bits) >= 8:
                break
    return clean_hook_line(" ".join(bits))


def clean_hook_line(text: str) -> str:
    """One complete on-screen tease: no commas/slashes/periods, no mid-word cut."""
    raw = " ".join(str(text or "").replace("\n", " ").replace("\\", " ").split())
    raw = raw.replace("/", " ")
    raw = re.sub(r"[\"“”‘’`]+", "", raw)
    raw = re.sub(r"[,:;_|…]+", " ", raw)
    raw = re.sub(r"(?<!\d)\.(?!\d)", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" -–—")
    words = [_mask_swear_token(part) for part in raw.split() if part]
    if len(words) > 8:
        words = words[:8]
    line = " ".join(words)
    if len(line) > 42:
        line = line[:42].rsplit(" ", 1)[0] or line[:42]
    return line.strip(" -–—")


def _mask_swear_token(token: str) -> str:
    letters = re.sub(r"[^A-Za-z]", "", token)
    if letters.lower() not in _SWEARS:
        return token
    if len(token) <= 2:
        return f"{token[0]}*"
    return f"{token[0]}*{token[2:]}"


def hook_font_size(line: str) -> int:
    n = max(1, len(line))
    return max(HOOK_FONT_MIN, min(HOOK_FONT, int(HOOK_MAX_W / (n * HOOK_CHAR_W))))


def hook_layout(text: str) -> tuple[list[str], int]:
    """One line when it can stay large. Longer teases split in two so the type does not shrink away."""
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return [], HOOK_FONT
    one = hook_font_size(cleaned)
    if one >= 78:
        return [cleaned], one
    words = cleaned.split()
    if len(words) < 2:
        return [cleaned], one
    split_at = 1
    best = 10**9
    for index in range(1, len(words)):
        longer = max(len(" ".join(words[:index])), len(" ".join(words[index:])))
        if longer < best:
            best = longer
            split_at = index
    lines = [" ".join(words[:split_at]), " ".join(words[split_at:])]
    size = min(hook_font_size(line) for line in lines)
    return lines, max(HOOK_FONT_MIN, min(HOOK_FONT, size))


def windows_font(bold: bool = True) -> Path | None:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    fonts = windir / "Fonts"
    names = ("arialbd.ttf", "Arialbd.ttf") if bold else ("arial.ttf", "Arial.ttf")
    for name in names:
        path = fonts / name
        if path.is_file():
            return path
    fallback = fonts / "arial.ttf"
    return fallback if fallback.is_file() else None


def windows_hook_font() -> Path | None:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    fonts = windir / "Fonts"
    for name in ("impact.ttf", "Impact.ttf", "ariblk.ttf", "segoeuib.ttf", "arialbd.ttf"):
        path = fonts / name
        if path.is_file():
            return path
    return windows_font(True)
