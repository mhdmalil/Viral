from app.services.video.layout import (
    BOTTOM_UI_SAFE,
    CANVAS_H,
    CANVAS_W,
    HOOK_CHAR_W,
    HOOK_MAX_W,
    TOP_BAR_H,
    TOP_SAFE_Y,
    extract_hook_line,
    fit_source,
    hook_draw_y,
    hook_font_size,
    hook_layout,
    social_placement,
)


def test_overlay_masks_swears_not_other_words() -> None:
    assert extract_hook_line([], 0, 8, preferred="He said fuck that") == "He said f*ck that"
    assert "class" in extract_hook_line([], 0, 8, preferred="classic class act")


def test_overlay_is_one_line_below_the_header() -> None:
    from app.services.video.layout import HOOK_FONT, HOOK_Y

    short_lines, short_size = hook_layout("Wait for it")
    assert short_lines == ["Wait for it"]
    assert short_size >= 90
    lines, size = hook_layout("Who are we going to last through all")
    assert len(lines) == 2
    assert size >= 72
    assert size <= HOOK_FONT
    for line in lines:
        assert hook_font_size(line) * len(line) * HOOK_CHAR_W <= HOOK_MAX_W + 8
    y = hook_draw_y(font_size=size)
    assert y == HOOK_Y
    assert y >= TOP_SAFE_Y


def test_platform_icon_is_visible(tmp_path) -> None:
    from app.services.branding.icons import write_platform_icon

    dest = tmp_path / "youtube.png"
    write_platform_icon("youtube", dest)
    data = dest.read_bytes()
    assert data.startswith(b"\x89PNG")
    assert dest.stat().st_size > 400


def test_downloads_folder_is_named_downloads() -> None:
    from types import SimpleNamespace

    from app.services.storage.paths import project_downloads_dir

    project = SimpleNamespace(folder_path=r"C:\tmp\proj", account_id=1, id=1, name="Demo")
    assert project_downloads_dir(project).name == "downloads"


def test_captions_use_fixed_canvas_margin() -> None:
    from app.services.video.layout import caption_margin_v

    for size in ((1080, 1920), (1920, 1080), (1080, 1080)):
        mv = caption_margin_v()
        assert mv == BOTTOM_UI_SAFE
        caption_bottom = CANVAS_H - mv
        assert caption_bottom == CANVAS_H - 420
        assert caption_bottom > CANVAS_H * 0.7
        _ = size


def test_hook_and_socials_are_phone_safe_for_wide_and_tall() -> None:
    from app.services.video.layout import HOOK_FONT, HOOK_Y

    tall = fit_source(1080, 1920)
    assert tall.y == TOP_BAR_H
    y_hook = hook_draw_y(tall.y)
    assert y_hook == HOOK_Y
    assert y_hook >= TOP_SAFE_Y
    pos = social_placement(tall, 0)
    assert pos is not None
    assert pos[0] >= 52
    assert pos[1] >= HOOK_Y + HOOK_FONT + 16
    assert pos[1] > y_hook

    wide = fit_source(1920, 1080)
    assert wide.y > TOP_BAR_H + 200
    assert hook_draw_y(wide.y) == hook_draw_y(tall.y)
    pos_w = social_placement(wide, 0)
    assert pos_w is not None
    assert pos_w[0] >= 52
    assert pos_w[1] >= HOOK_Y + HOOK_FONT + 16
