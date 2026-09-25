from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from app.core.config import ROOT_DIR, settings
from app.services.transcription.provider import TranscriptionError, TranscriptionProvider

logger = logging.getLogger(__name__)

WHISPER_PY = ROOT_DIR / "backend" / ".venv-whisper" / "Scripts" / "python.exe"
SCRIPT = ROOT_DIR / "backend" / "scripts" / "transcribe_wav.py"


class FasterWhisperTranscription(TranscriptionProvider):
    def transcribe(self, media_path: Path) -> dict[str, Any]:
        if not media_path.is_file():
            raise TranscriptionError("Video file is missing on disk.")
        if not WHISPER_PY.is_file():
            raise TranscriptionError(
                "Whisper sidecar is missing. From the repo root run: "
                "py -3.12 -m venv backend\\.venv-whisper ; "
                "backend\\.venv-whisper\\Scripts\\pip install -r backend\\requirements-whisper.txt"
            )
        if not SCRIPT.is_file():
            raise TranscriptionError("Whisper script is missing.")
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            completed = subprocess.run(
                [
                    str(WHISPER_PY),
                    str(SCRIPT),
                    str(media_path),
                    settings.whisper_model,
                    settings.whisper_device if settings.whisper_device in {"cpu", "cuda"} else "cpu",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3600,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise TranscriptionError("Whisper timed out.") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "no sidecar output").strip()
            logger.error("Whisper sidecar failed (exit %s): %s", completed.returncode, detail[:2000])
            if "No module named" in detail:
                raise TranscriptionError(
                    "Whisper helper is missing a package. From the repo run: "
                    "backend\\.venv-whisper\\Scripts\\pip install -r backend\\requirements-whisper.txt"
                )
            hint = detail.splitlines()[0] if detail else f"exit {completed.returncode}"
            raise TranscriptionError(f"Whisper failed to transcribe this video. {hint}")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise TranscriptionError("Whisper returned invalid output.") from exc
