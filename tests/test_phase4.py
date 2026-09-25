from app.services.ai.chat import assistant_text, chat_completions_url, parse_response_json, retry_after_seconds
from app.services.ai.parse import parse_candidates_json, validate_candidate
from app.services.ai.windows import build_windows


def test_retry_after_seconds_reads_header() -> None:
    class Fake:
        headers = {"retry-after": "12"}

    assert retry_after_seconds(Fake(), 0) == 12.0  # type: ignore[arg-type]


def test_chat_completions_url_appends_path() -> None:
    assert (
        chat_completions_url("https://openrouter.ai/api/v1")
        == "https://openrouter.ai/api/v1/chat/completions"
    )


def test_parse_json_object_strips_fence() -> None:
    from app.services.ai.parse import parse_json_object

    data = parse_json_object('```json\n{"keep_ids":["a"]}\n```')
    assert data["keep_ids"] == ["a"]


def test_parse_accepts_fenced_json() -> None:
    raw = '```json\n{"candidates":[{"start":10,"end":40,"score":0.8,"signals":{"hook":0.9},"reason":"x"}]}\n```'
    rows = parse_candidates_json(raw)
    assert len(rows) == 1
    valid = validate_candidate(rows[0], None)
    assert valid is not None
    assert valid["start"] == 10


def test_windows_from_segments() -> None:
    transcript = {
        "segments": [
            {"start": 0, "end": 2, "text": "hello"},
            {"start": 310, "end": 312, "text": "later"},
        ]
    }
    windows = build_windows(transcript, window_seconds=300)
    assert len(windows) == 2
    assert "hello" in windows[0]["text"]
    assert "later" in windows[1]["text"]


def test_default_windows_are_two_minutes() -> None:
    from app.services.ai.windows import WINDOW_SECONDS

    assert WINDOW_SECONDS == 120.0
    transcript = {
        "segments": [
            {"start": 0, "end": 2, "text": "early"},
            {"start": 130, "end": 132, "text": "later"},
        ]
    }
    windows = build_windows(transcript)
    assert len(windows) == 2


def test_shift_and_merge_transcript() -> None:
    from app.services.transcription.shift import merge_transcript, shift_transcript, transcript_complete

    chunk = {
        "duration": 10,
        "text": "hi",
        "segments": [{"start": 0.0, "end": 1.5, "text": "hi", "words": [{"start": 0.0, "end": 1.5, "word": "hi"}]}],
    }
    shifted = shift_transcript(chunk, 120.0)
    assert shifted["segments"][0]["start"] == 120.0
    assert shifted["segments"][0]["words"][0]["start"] == 120.0
    merged = merge_transcript({"segments": [], "duration": 0}, shifted)
    assert len(merged["segments"]) == 1
    assert transcript_complete(merged, 130.0) is True
    assert transcript_complete({"segments": []}, 130.0) is False


def test_assistant_text_reads_list_content_and_reasoning() -> None:
    listed = {
        "choices": [
            {"message": {"role": "assistant", "content": [{"type": "text", "text": '{"candidates":[]}'}]}}
        ]
    }
    assert '{"candidates"' in assistant_text(listed)
    reasoned = {
        "choices": [{"message": {"role": "assistant", "content": None, "reasoning_content": '{"candidates":[]}'}}]
    }
    assert assistant_text(reasoned) == '{"candidates":[]}'
    stacked = '{"id":1}\n{"choices":[{"message":{"content":"{\\"candidates\\":[]}"}}]}'
    data = parse_response_json(stacked)
    assert assistant_text(data) == '{"candidates":[]}'
