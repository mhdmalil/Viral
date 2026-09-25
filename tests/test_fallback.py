import httpx

from app.services.ai.editorial.engine import run_editorial
from app.services.ai.chat import AIProviderError, ChatAIProvider
from app.services.ai.routing import ChatTarget
from app.services.ai.test_backend import TestAIProvider


class _FailFirstDiscovery(TestAIProvider):
    def __init__(self) -> None:
        self.discovery = 0

    def editor_json(self, system: str, payload: dict) -> dict:
        if payload.get("pass") == "discovery":
            self.discovery += 1
            if self.discovery == 1:
                raise AIProviderError("first model failed")
        return super().editor_json(system, payload)


def test_editorial_skips_failed_window_and_continues() -> None:
    transcript = {
        "duration": 400,
        "text": "first hook story. later payoff story.",
        "segments": [
            {"start": 0.0, "end": 14.0, "text": "first hook story that stands alone."},
            {"start": 240.0, "end": 255.0, "text": "later payoff story that also stands alone."},
        ],
    }
    clips, artifacts = run_editorial(
        transcript,
        provider=_FailFirstDiscovery(),
        video_duration=400.0,
        user_max=None,
    )
    assert len(artifacts["seeds"]) >= 1
    assert len(clips) >= 1
    assert max(row["start"] for row in clips) > 200


def test_complete_chat_jumps_to_next_model(monkeypatch: object) -> None:
    from app.services.ai import chat as chat_mod

    chat_mod._model_cooldown_until.clear()
    chat_mod._missing_models.clear()
    chat_mod._last_ok = None
    targets = [
        ChatTarget("groq", "openai/gpt-oss-120b", "https://groq.example/v1", "k1"),
        ChatTarget("gemini", "gemini-2.5-flash", "https://gemini.example/v1", "k2"),
    ]
    monkeypatch.setattr("app.services.ai.routing.any_chat_key", lambda: True)
    monkeypatch.setattr(
        "app.services.ai.routing.iter_chat_targets",
        lambda catalog_ids=None, rotate=0, prefer=None: iter(targets),
    )
    ChatAIProvider._or_free = []

    def post(url: str, headers=None, json=None, timeout=None):
        del headers, json, timeout
        if "groq.example" in url:
            raise httpx.ConnectError("groq down")
        response = httpx.Response(
            200,
            text='{"choices":[{"message":{"content":"ok-from-gemini"}}]}',
            request=httpx.Request("POST", url),
        )
        return response

    monkeypatch.setattr(httpx, "post", post)
    text = ChatAIProvider().complete_chat("sys", "user")
    assert text == "ok-from-gemini"


def test_complete_chat_429_skips_wait_and_jumps(monkeypatch: object) -> None:
    from app.services.ai import chat as chat_mod

    chat_mod._model_cooldown_until.clear()
    chat_mod._missing_models.clear()
    chat_mod._last_ok = None
    used: list[str] = []
    targets = [
        ChatTarget("groq", "openai/gpt-oss-120b", "https://groq.example/v1", "k1"),
        ChatTarget("groq", "openai/gpt-oss-20b", "https://groq.example/v1", "k1"),
        ChatTarget("gemini", "gemini-2.5-flash", "https://gemini.example/v1", "k2"),
    ]
    monkeypatch.setattr("app.services.ai.routing.any_chat_key", lambda: True)
    monkeypatch.setattr(
        "app.services.ai.routing.iter_chat_targets",
        lambda catalog_ids=None, rotate=0, prefer=None: iter(targets),
    )
    ChatAIProvider._or_free = []

    def post(url: str, headers=None, json=None, timeout=None):
        del headers, timeout
        model = (json or {}).get("model")
        used.append(str(model))
        if model == "openai/gpt-oss-120b":
            return httpx.Response(
                429,
                headers={"retry-after": "99"},
                request=httpx.Request("POST", url),
            )
        if model == "openai/gpt-oss-20b":
            return httpx.Response(
                200,
                text='{"choices":[{"message":{"content":"ok-from-groq-20b"}}]}',
                request=httpx.Request("POST", url),
            )
        raise AssertionError("left Groq before trying remaining Groq models")

    monkeypatch.setattr(httpx, "post", post)
    text = ChatAIProvider().complete_chat("sys", "user")
    assert text == "ok-from-groq-20b"
    assert used == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    assert chat_mod._model_cooling("groq", "openai/gpt-oss-120b")
    assert not chat_mod._model_cooling("groq", "openai/gpt-oss-20b")
