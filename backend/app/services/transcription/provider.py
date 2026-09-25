from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class TranscriptionError(Exception):
    pass


class TranscriptionProvider(ABC):
    @abstractmethod
    def transcribe(self, media_path: Path) -> dict[str, Any]:
        raise NotImplementedError
