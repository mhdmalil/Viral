from pathlib import Path
from typing import Any

from app.services.transcription.provider import TranscriptionProvider


class TestTranscriptionProvider(TranscriptionProvider):
    """Deterministic transcript for pytest. Does not download Whisper weights."""

    def transcribe(self, media_path: Path) -> dict[str, Any]:
        if not media_path.is_file():
            raise FileNotFoundError(str(media_path))
        return {
            "language": "en",
            "duration": None,
            "text": "",
            "segments": [],
            "backend": "test",
            "model": "test",
        }
