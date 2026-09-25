from app.core.config import settings
from app.services.transcription.faster_whisper import FasterWhisperTranscription
from app.services.transcription.provider import TranscriptionProvider
from app.services.transcription.test_backend import TestTranscriptionProvider


def get_transcription_provider() -> TranscriptionProvider:
    backend = (settings.transcription_backend or "faster-whisper").strip().lower()
    if backend == "test":
        return TestTranscriptionProvider()
    return FasterWhisperTranscription()
