from app.core.config import settings
from app.services.ai.chat import ChatAIProvider
from app.services.ai.provider import AIProvider, StubAIProvider
from app.services.ai.test_backend import TestAIProvider


def get_ai_provider() -> AIProvider:
    name = (settings.ai_provider or "openrouter").strip().lower()
    if name == "test":
        return TestAIProvider()
    if name in {"openrouter", "hermes", "openai", "chat", ""}:
        return ChatAIProvider()
    if name == "stub":
        return StubAIProvider()
    return ChatAIProvider()
