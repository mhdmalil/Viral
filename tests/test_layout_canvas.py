from __future__ import annotations

import subprocess
from pathlib import Path

from app.services.video.layout import (
    BOTTOM_UI_SAFE,
    CANVAS_H,
    CANVAS_W,
    TOP_BAR_H,
    TOP_SAFE_Y,
    VIDEO_AREA_H,
    VIDEO_AREA_Y,
    caption_margin_v,
    fit_source,
    hook_draw_y,
    social_placement,
    vertical_canvas_vf,
)

RATIOS = (
    (1920, 1080),
    (1280, 720),
    (1080, 1920),
    (720, 1280),
    (1080, 1080),
    (1440, 1080),
    (1080, 1440),
)


def test_fit_does_not_stretch_or_crop() -> None:
    for src_w, src_h in RATIOS:
        video = fit_source(src_w, src_h)
        assert video.w <= CANVAS_W
        assert video.h <= VIDEO_AREA_H
        assert video.y >= VIDEO_AREA_Y
        assert video.bottom <= CANVAS_H
        assert abs(video.w / video.h - src_w / src_h) < 0.02
        assert video.x == (CANVAS_W - video.w) // 2
        assert video.y == VIDEO_AREA_Y + (VIDEO_AREA_H - video.h) // 2


def test_landscape_and_portrait_sizes() -> None:
    wide = fit_source(1920, 1080)
    assert wide.w == 1080
    assert abs(wide.h - 608) <= 2
    tall = fit_source(1080, 1920)
    assert tall.h == VIDEO_AREA_H
    assert abs(tall.w - 1017) <= 2


def test_hook_and_captions_ignore_source_ratio() -> None:
    from app.services.video.layout import HOOK_Y

    ys = [hook_draw_y(fit_source(*size).y, font_size=88) for size in RATIOS]
    assert len(set(ys)) == 1
    assert ys[0] == HOOK_Y
    assert ys[0] >= TOP_SAFE_Y
    margins = {caption_margin_v() for _ in RATIOS}
    assert margins == {BOTTOM_UI_SAFE}


def test_socials_stay_on_picture_and_above_bottom_ui() -> None:
    for src_w, src_h in RATIOS:
        video = fit_source(src_w, src_h)
        last = None
        for index in range(8):
            pos = social_placement(video, index)
            if pos is None:
                break
            x, y = pos
            assert x >= 52
            assert x < CANVAS_W / 2
            assert y >= TOP_SAFE_Y
            assert y >= hook_draw_y() + 88
            assert y + 44 < video.bottom - BOTTOM_UI_SAFE
            assert y + 44 <= CANVAS_H - BOTTOM_UI_SAFE
            last = pos
        assert last is not None


def test_canvas_filter_fits_then_pads() -> None:
    vf = vertical_canvas_vf(None)
    assert "crop=" not in vf
    assert "force_original_aspect_ratio=decrease" in vf
    assert f"scale={CANVAS_W}:{VIDEO_AREA_H}" in vf
    assert f"pad={CANVAS_W}:{CANVAS_H}:0:{TOP_BAR_H}:black" in vf


def test_render_all_ratios_are_1080x1920(tmp_path: Path) -> None:
    from app.services.video.ffmpeg import probe_video, render_vertical_clip

    ffmpeg_ok = True
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=20)
    except Exception:
        ffmpeg_ok = False
    if not ffmpeg_ok:
        return

    from app.services.branding.icons import write_platform_icon

    icon = tmp_path / "tiktok.png"
    write_platform_icon("tiktok", icon)
    for src_w, src_h in RATIOS:
        src = tmp_path / f"src_{src_w}x{src_h}.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=red:s={src_w}x{src_h}:d=0.4",
                "-pix_fmt",
                "yuv420p",
                str(src),
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        video = fit_source(src_w, src_h)
        pos = social_placement(video, 0)
        dest = tmp_path / f"out_{src_w}x{src_h}.mp4"
        overlays = []
        if pos is not None:
            overlays = [{"path": str(icon), "x": pos[0], "y": pos[1], "w": 44, "label": "@clip"}]
        render_vertical_clip(
            src,
            dest,
            start=0.0,
            end=0.4,
            has_audio=False,
            hook_line="Wait until you hear this",
            hook_file=tmp_path / f"hook_{src_w}.txt",
            overlays=overlays,
            pad_min=False,
        )
        out = probe_video(dest)
        assert out["width"] == CANVAS_W
        assert out["height"] == CANVAS_H
        assert dest.stat().st_size > 0
