from pathlib import Path

from app.services.captions.classic import build_cues, cues_to_ass
from app.services.video.ffmpeg import probe_video, render_vertical_clip

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "tiny.mp4"


def test_classic_cues_are_clip_relative() -> None:
    cues = build_cues(
        [{"start": 10.0, "end": 11.0, "text": "hello"}, {"start": 11.0, "end": 12.0, "text": "world"}],
        clip_start=10.0,
        clip_end=20.0,
    )
    assert cues
    assert cues[0]["start"] == 0.0
    assert "hello" in cues[0]["text"]
    ass = cues_to_ass(cues, margin_v=420, style="classic")
    assert "PlayResX: 1080" in ass
    assert "Arial,52," in ass


def test_render_vertical_clip_writes_mp4(tmp_path: Path) -> None:
    assert FIXTURE.is_file()
    info = probe_video(FIXTURE)
    end = max(0.2, float(info["duration_seconds"] or 0.4))
    dest = tmp_path / "out.mp4"
    render_vertical_clip(
        FIXTURE,
        dest,
        start=0.0,
        end=end,
        srt_path=None,
        has_audio=bool(info.get("has_audio")),
    )
    assert dest.is_file()
    assert dest.stat().st_size > 0
    out = probe_video(dest)
    assert out["width"] == 1080
    assert out["height"] == 1920


def test_ass_styles_are_white_outline_bottom() -> None:
    cues = [{"start": 0.0, "end": 0.4, "text": "hello there"}]
    classic = cues_to_ass(cues, margin_v=420, style="classic")
    assert "Arial,52," in classic
    assert ",420,1" in classic.split("[Events]")[0]
    bold = cues_to_ass(cues, margin_v=420, style="bold")
    assert "Arial,52," in bold
    boxed = cues_to_ass(cues, margin_v=420, style="boxed")
    assert "Arial,52," in boxed
    assert ",1,3,0,2," in classic.split("[Events]")[0]
    assert ",1,5,1,2," in bold.split("[Events]")[0]
    assert ",3,4,0,2," in boxed.split("[Events]")[0]
    assert cues_to_ass(cues, margin_v=420, style="unknown") == classic


def test_render_vertical_clip_joins_pieces_with_motion(tmp_path: Path) -> None:
    info = probe_video(FIXTURE)
    end = max(0.4, float(info["duration_seconds"] or 0.4))
    mid = max(0.15, end * 0.5)
    dest = tmp_path / "joined.mp4"
    render_vertical_clip(
        FIXTURE,
        dest,
        start=0.0,
        end=end,
        has_audio=bool(info.get("has_audio")),
        hook_line="Wait for this",
        pieces=[(0.0, mid), (mid, end)],
        hook_until=min(1.6, end),
        crop=None,
        pad_min=False,
    )
    assert dest.is_file()
    out = probe_video(dest)
    assert out["width"] == 1080
    assert out["height"] == 1920


def test_render_vertical_clip_burns_ass(tmp_path: Path) -> None:
    dest = tmp_path / "captioned.mp4"
    ass = tmp_path / "cues.ass"
    ass.write_text(cues_to_ass([{"start": 0.0, "end": 0.4, "text": "hello"}], margin_v=420), encoding="utf-8")
    info = probe_video(FIXTURE)
    end = max(0.2, float(info["duration_seconds"] or 0.4))
    render_vertical_clip(
        FIXTURE,
        dest,
        start=0.0,
        end=end,
        srt_path=ass,
        has_audio=bool(info.get("has_audio")),
    )
    assert dest.is_file()
    assert dest.stat().st_size > 0


def test_nine_sixteen_window_clamps_on_wide_frame() -> None:
    from app.services.video.reframe import center_window, nine_sixteen_window, vertical_vf

    crop_w, crop_h, x, y = nine_sixteen_window(1920, 1080, 200, 540)
    assert crop_h == 1080
    assert crop_w < 1920
    assert x >= 0
    assert x + crop_w <= 1920
    assert y == 0
    center = center_window(1920, 1080)
    assert center[0] < 1920
    assert center[1] == 1080
    assert "crop=" not in vertical_vf(center)
    assert "scale=1080:1808" in vertical_vf(None)
    assert "force_original_aspect_ratio=decrease" in vertical_vf(None)
    assert "pad=1080:1920:0:112:black" in vertical_vf(None)


def test_render_vertical_clip_with_auto_crop(tmp_path: Path) -> None:
    from app.services.video.reframe import center_window, detect_reframe_crop

    info = probe_video(FIXTURE)
    end = max(0.2, float(info["duration_seconds"] or 0.4))
    crop = detect_reframe_crop(FIXTURE, 0.0, end)
    assert crop is not None
    fallback = center_window(int(info["width"]), int(info["height"]))
    assert crop[0] <= int(info["width"])
    dest = tmp_path / "reframed.mp4"
    render_vertical_clip(FIXTURE, dest, start=0.0, end=end, crop=fallback, has_audio=bool(info.get("has_audio")))
    out = probe_video(dest)
    assert out["width"] == 1080
    assert out["height"] == 1920


def test_render_letterbox_hook_and_social(tmp_path: Path) -> None:
    from app.services.branding.icons import write_platform_icon

    info = probe_video(FIXTURE)
    end = max(0.2, float(info["duration_seconds"] or 0.4))
    hook = tmp_path / "hook.txt"
    hook.write_text("Wait until you hear this", encoding="utf-8")
    icon = tmp_path / "tiktok.png"
    write_platform_icon("tiktok", icon)
    dest = tmp_path / "branded.mp4"
    render_vertical_clip(
        FIXTURE,
        dest,
        start=0.0,
        end=end,
        has_audio=bool(info.get("has_audio")),
        hook_file=hook,
        overlays=[{"path": str(icon), "x": 36, "y": 1840, "w": 44, "label": "@clipper"}],
    )
    out = probe_video(dest)
    assert dest.is_file()
    assert out["width"] == 1080
    assert out["height"] == 1920


def test_caption_style_names_normalize() -> None:
    from app.services.captions.styles import normalize_position, normalize_style

    assert normalize_style("classic") == "classic"
    assert normalize_style("bold") == "bold"
    assert normalize_style("boxed") == "boxed"
    assert normalize_style("neon") == "classic"
    assert normalize_position("center") == "center"
    assert normalize_position("nope") == "lower"
