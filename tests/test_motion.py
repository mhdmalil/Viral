from app.services.video.ffmpeg import _hook_chain
from app.services.video.motion import (
    JOIN_FADE_S,
    JOIN_ZOOM_S,
    hook_title_motion,
    join_into,
    punch_in_chain,
    xfade_offsets,
)
from app.services.video.timeline import Piece, apply_piece_joins, output_duration


def test_ordinary_join_is_a_short_fade() -> None:
    name, held = join_into(False)
    assert name == "fade"
    assert 0.15 <= held <= 0.3


def test_join_into_the_hook_is_a_stronger_zoom() -> None:
    name, held = join_into(True)
    assert name == "zoomin"
    assert held > JOIN_FADE_S
    assert held == JOIN_ZOOM_S


def test_piece_joins_shift_output_time_for_xfade() -> None:
    raw = [
        Piece(0.0, 4.0, 0.0),
        Piece(5.0, 9.0, 4.0),
    ]
    pieces = apply_piece_joins(raw)
    assert pieces[0].join is None
    assert pieces[1].join == "fade"
    assert pieces[1].join_seconds == JOIN_FADE_S
    assert abs(pieces[1].out_start - (4.0 - JOIN_FADE_S)) < 0.001
    assert abs(output_duration(pieces) - (8.0 - JOIN_FADE_S)) < 0.001
    steps = xfade_offsets(pieces)
    assert steps == [("fade", JOIN_FADE_S, 4.0 - JOIN_FADE_S)]


def test_hook_destination_uses_zoomin() -> None:
    raw = [
        Piece(0.0, 3.0, 0.0),
        Piece(10.0, 14.0, 3.0),
    ]
    pieces = apply_piece_joins(raw, hook_index=1)
    assert pieces[1].join == "zoomin"
    assert pieces[1].join_seconds == JOIN_ZOOM_S


def test_short_pieces_skip_a_join() -> None:
    raw = [
        Piece(0.0, 0.2, 0.0),
        Piece(1.0, 1.2, 0.2),
    ]
    pieces = apply_piece_joins(raw)
    assert pieces[1].join is None
    assert pieces[1].join_seconds == 0.0
    assert xfade_offsets(pieces) == []


def test_punch_in_and_hook_title_are_animated() -> None:
    punch = punch_in_chain()
    assert "crop=" in punch
    assert "min(1\\,t/2.0)" in punch or "min(1\\,t/2)" in punch
    assert "scale=1080:1920" in punch
    y_expr, alpha = hook_title_motion(360)
    assert "if(lt(t" in y_expr
    assert "if(lt(t" in alpha
    chain = _hook_chain("Wait for this", hook_file=None, hook_font=None, content_top=112, hook_until=1.6)
    assert "drawtext=" in chain
    assert "alpha=" in chain
    assert "y='" in chain


def test_word_by_word_hides_future_words() -> None:
    from app.services.captions.classic import cues_to_ass

    cues = [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "hello there now",
            "words": [
                {"text": "hello", "start": 0.0, "end": 0.3},
                {"text": "there", "start": 0.3, "end": 0.6},
                {"text": "now", "start": 0.6, "end": 1.0},
            ],
        }
    ]
    ass = cues_to_ass(cues, margin_v=420, style="classic")
    dialogues = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogues) == 3
    assert "there" not in dialogues[0]
    assert "now" not in dialogues[0]
    assert "hello" in dialogues[1] and "there" in dialogues[1] and "now" not in dialogues[1]
    assert "hello" in dialogues[2] and "there" in dialogues[2] and "now" in dialogues[2]
    assert r"\fscx108" in dialogues[0]
