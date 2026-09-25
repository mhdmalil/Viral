from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.branding.icons import write_platform_icon
from app.services.branding.normalize import parse_branding
from app.services.video.layout import extract_hook_line, vertical_canvas_vf

client = TestClient(app)


def test_extract_hook_line_uses_opening_words() -> None:
    words = [
        {"start": 1.0, "end": 1.2, "word": "Wait"},
        {"start": 1.2, "end": 1.5, "word": "until"},
        {"start": 1.5, "end": 1.8, "word": "you"},
        {"start": 1.8, "end": 2.1, "word": "hear"},
        {"start": 2.1, "end": 2.5, "word": "this"},
    ]
    line = extract_hook_line(words, 1.0, 12.0, hook_at=1.0)
    assert "Wait" in line
    assert len(line.split()) <= 8
    assert "," not in extract_hook_line([], 0, 8, preferred="Wait, until you hear this.")
    assert "/" not in extract_hook_line([], 0, 8, preferred="wait/until you hear")
    assert extract_hook_line([], 0, 8, preferred="He is going to what?") == "He is going to what?"
    long = extract_hook_line([], 0, 8, preferred="Who are we going to last through all of this extra clause")
    assert not long.endswith("thro")
    assert "last" in long or long.endswith("to")


def test_vertical_canvas_has_black_bars() -> None:
    vf = vertical_canvas_vf(None)
    assert "force_original_aspect_ratio=decrease" in vf
    assert "pad=1080:1808:(ow-iw)/2:(oh-ih)/2:black" in vf
    assert "pad=1080:1920:0:112:black" in vf
    assert "crop=" not in vf


def test_hook_and_picture_sit_on_the_real_frame() -> None:
    from app.services.video.layout import TOP_BAR_H, fit_source, hook_draw_y, social_placement

    video = fit_source(1920, 1080)
    assert video.y >= TOP_BAR_H
    y = hook_draw_y(video.y)
    assert y >= TOP_BAR_H
    pos = social_placement(video, 0)
    assert pos is not None
    assert pos[0] >= 52
    pos2 = social_placement(video, 1)
    if pos2 is not None:
        assert pos2[0] == pos[0]
        assert pos2[1] > pos[1]


def test_project_branding_roundtrip() -> None:
    project = client.post("/api/projects", json={"name": "Branding"}).json()
    assert project["branding"]["handles"] == []
    updated = client.patch(
        f"/api/projects/{project['id']}",
        json={
            "branding": {
                "handles": [
                    {"platform": "tiktok", "name": "@clipper"},
                    {"platform": "youtube", "name": "Clip Channel"},
                    {"platform": "myspace", "name": "nope"},
                ],
                "custom_name": "Studio",
            }
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    platforms = {row["platform"] for row in body["branding"]["handles"]}
    assert platforms == {"tiktok", "youtube"}
    assert body["branding"]["custom_name"] == "Studio"
    pictured = client.patch(
        f"/api/projects/{project['id']}",
        json={"branding": {"handles": [{"platform": "tiktok", "name": "@clipper"}], "footer": "picture"}},
    )
    assert pictured.status_code == 200, pictured.text
    assert pictured.json()["branding"]["footer"] == "picture"
    vibed = client.patch(
        f"/api/projects/{project['id']}",
        json={"branding": {"vibes": ["funny", "financial", "nope", "money"]}},
    )
    assert vibed.status_code == 200, vibed.text
    assert vibed.json()["branding"]["vibes"] == ["funny", "financial"]


def test_branding_items_picture_replaces_socials(tmp_path: Path) -> None:
    from app.services.branding.normalize import branding_items

    pic = tmp_path / "banner.png"
    pic.write_bytes(b"x" * 32)
    picture = branding_items(
        {
            "footer": "picture",
            "custom_logo_path": str(pic),
            "handles": [{"platform": "tiktok", "name": "x"}],
        }
    )
    assert picture == [{"platform": "banner", "name": "", "logo": str(pic), "fit": "banner"}]
    socials = branding_items(
        {
            "footer": "socials",
            "custom_logo_path": str(pic),
            "handles": [{"platform": "tiktok", "name": "x"}],
        }
    )
    assert [row["platform"] for row in socials] == ["tiktok"]
    assert branding_items({"footer": "picture", "handles": [{"platform": "tiktok", "name": "x"}]}) == [
        {"platform": "tiktok", "name": "x", "fit": "icon"}
    ]


def test_logo_upload_and_parse(tmp_path: Path) -> None:
    icon = tmp_path / "yt.png"
    write_platform_icon("youtube", icon)
    assert icon.stat().st_size > 1000
    parsed = parse_branding('{"handles":[{"platform":"instagram","name":"  shop  "}],"footer":"picture"}')
    assert parsed["handles"] == [{"platform": "instagram", "name": "shop"}]
    assert parsed["footer"] == "picture"


def test_clip_file_stem_is_hook_text(tmp_path: Path) -> None:
    from app.services.storage.paths import clip_file_stem, unique_clip_path

    assert clip_file_stem("Wait until you hear this", 9) == "Wait until you hear this"
    assert clip_file_stem("Wait until you hear this", 9, 3) == "03 - Wait until you hear this"
    assert ":" not in clip_file_stem('Bad:name?/file', 3)
    first = unique_clip_path(tmp_path, "Wait until you hear this", 1)
    first.write_bytes(b"x")
    second = unique_clip_path(tmp_path, "Wait until you hear this", 2)
    assert first.name == "Wait until you hear this_1.mp4"
    assert second.name == "Wait until you hear this_2.mp4"
