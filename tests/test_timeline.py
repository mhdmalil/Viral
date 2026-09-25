from app.services.captions.classic import build_cues_on_timeline, cues_to_ass
from app.services.video.timeline import (
    OPEN_SECONDS,
    hook_first_pieces,
    hook_until,
    output_duration,
    resolve_hook_at,
)


def _src(pieces) -> list[tuple[float, float]]:
    return [piece.as_tuple() for piece in pieces]


def test_clip_starts_on_the_hook_and_plays_forward() -> None:
    pieces = hook_first_pieces(8.0, 20.0, 12.0)
    assert _src(pieces) == [(12.0, 20.0)]
    assert abs(output_duration(pieces) - 8.0) < 0.02
    assert pieces[0].src_start == 12.0
    assert pieces[0].src_end == 20.0
    assert hook_until(pieces) <= OPEN_SECONDS


def test_missing_hook_keeps_the_thought() -> None:
    assert _src(hook_first_pieces(8.0, 20.0, None)) == [(8.0, 20.0)]
    assert _src(hook_first_pieces(8.0, 20.0, 25.0)) == [(8.0, 20.0)]
    assert _src(hook_first_pieces(8.0, 20.0, 5.0)) == [(8.0, 20.0)]


def test_hook_already_at_start_is_linear() -> None:
    assert _src(hook_first_pieces(8.0, 20.0, 8.0)) == [(8.0, 20.0)]
    assert _src(hook_first_pieces(8.0, 20.0, 8.2)) == [(8.2, 20.0)]


def test_no_jump_back_to_setup() -> None:
    pieces = hook_first_pieces(8.0, 20.0, 12.0)
    starts = [p.src_start for p in pieces]
    assert starts == sorted(starts)
    assert len(pieces) == 1


def test_resolve_hook_at_window_local() -> None:
    assert resolve_hook_at(12.0, 8.0, 20.0) == 12.0
    assert resolve_hook_at(12.0, 120.0, 140.0, window_start=120.0) == 132.0
    assert resolve_hook_at(130.0, 120.0, 140.0, window_start=120.0) == 130.0
    assert resolve_hook_at(5.0, 8.0, 20.0) is None
    assert resolve_hook_at(0.0, 0.0, 12.0) == 0.0


def test_captions_cover_speech_and_punch_the_last_word() -> None:
    pieces = hook_first_pieces(8.0, 20.0, 12.0)
    words = [
        {"start": 8.0, "end": 8.4, "text": "hello"},
        {"start": 8.4, "end": 8.9, "text": "there"},
        {"start": 12.0, "end": 12.4, "text": "wait"},
        {"start": 12.4, "end": 13.0, "text": "what"},
        {"start": 14.0, "end": 14.4, "text": "payoff"},
        {"start": 14.4, "end": 15.0, "text": "now"},
    ]
    cues = build_cues_on_timeline(words, pieces)
    joined = " ".join(c["text"] for c in cues)
    assert "wait" in joined
    assert "hello" not in joined
    assert "payoff" in joined
    ass = cues_to_ass(cues, margin_v=420, style="classic")
    assert "[V4+ Styles]" in ass
    assert "PlayResX: 1080" in ass
    assert "PlayResY: 1920" in ass
    assert "Arial,52," in ass
    assert r"{\c&H0000FFFF&" in ass
    assert r"\bord3" in ass
