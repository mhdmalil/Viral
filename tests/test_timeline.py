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


def test_tighten_drops_a_long_gap_and_stays_in_order() -> None:
    from app.services.video.timeline import pick_cutaway, tighten_pieces

    words = [
        {"start": 0.0, "end": 2.0, "word": "hello"},
        {"start": 2.1, "end": 4.0, "word": "there"},
        {"start": 6.2, "end": 10.0, "word": "payoff"},
        {"start": 10.0, "end": 14.0, "word": "lands"},
    ]
    pieces = tighten_pieces(words, 0.0, 14.0)
    assert _src(pieces)[0][0] == 0.0
    assert _src(pieces)[0][1] < 5
    assert _src(pieces)[-1][0] >= 6
    assert _src(pieces)[0][0] < _src(pieces)[-1][0]


def test_tighten_keeps_a_half_second_gap() -> None:
    from app.services.video.timeline import tighten_pieces

    words = [
        {"start": 0.0, "end": 2.0, "word": "hello"},
        {"start": 2.6, "end": 10.0, "word": "world"},
    ]
    pieces = tighten_pieces(words, 0.0, 10.0)
    assert len(pieces) == 1
    assert pieces[0].src_start == 0.0
    assert pieces[0].src_end == 10.0


def test_tighten_drops_a_short_um() -> None:
    from app.services.video.timeline import tighten_pieces

    words = [
        {"start": 0.0, "end": 3.0, "word": "I"},
        {"start": 3.1, "end": 3.4, "word": "um"},
        {"start": 3.5, "end": 11.0, "word": "won"},
    ]
    pieces = tighten_pieces(words, 0.0, 11.0)
    assert len(pieces) == 2
    assert pieces[0].src_end <= 3.2
    assert pieces[1].src_start >= 3.4


def test_tighten_keeps_the_full_span_when_the_tight_cut_is_under_8s() -> None:
    from app.services.video.timeline import tighten_pieces

    words = [{"start": 0.0, "end": 1.0, "word": "hi"}, {"start": 5.0, "end": 6.0, "word": "bye"}]
    assert _src(tighten_pieces(words, 0.0, 6.0)) == [(0.0, 6.0)]


def test_pick_cutaway_uses_another_shot_in_the_same_file() -> None:
    from app.services.video.timeline import pick_cutaway

    span = pick_cutaway([1.0, 3.0, 30.0, 34.0], 0.0, 10.0, 40.0)
    assert span is not None
    assert span[0] >= 30.0


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
    assert "wait" in ass
    assert "what" in ass
    wait_line = next(line for line in ass.splitlines() if line.startswith("Dialogue:") and "wait" in line and "what" not in line)
    what_line = next(line for line in ass.splitlines() if line.startswith("Dialogue:") and "what" in line)
    assert "what" not in wait_line
    assert "wait" in what_line
    assert r"{\c&H00FFFFFF&" in ass
