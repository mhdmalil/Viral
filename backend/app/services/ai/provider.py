from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Remote HTTP API for viral-moment understanding. Not a local LLM."""

    @abstractmethod
    def editor_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class StubAIProvider(AIProvider):
    def editor_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("AIProvider stub is disabled. Set AI_PROVIDER=openrouter.")
