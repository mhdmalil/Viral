"""Sidecar script: run under CPython 3.12 (ctranslate2 has no cp313t wheel)."""

from __future__ import annotations

import json
import sys
import traceback
import wave
from typing import Any

import numpy as np
from faster_whisper import WhisperModel


def load_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if width != 2:
        raise RuntimeError(f"Expected 16-bit PCM wav, got sample width {width}.")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if rate != 16000:
        raise RuntimeError(f"Expected 16 kHz wav, got {rate}.")
    return audio


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: transcribe_wav.py <wav> <model> <device>", file=sys.stderr)
        return 2
    wav, model_name, device = sys.argv[1], sys.argv[2], sys.argv[3]
    try:
        audio = load_wav(wav)
        compute = "int8" if device == "cpu" else "float16"
        model = WhisperModel(model_name, device=device, compute_type=compute)
        segments_iter, info = model.transcribe(
            audio,
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        segments: list[dict[str, Any]] = []
        texts: list[str] = []
        for index, segment in enumerate(segments_iter):
            words = []
            for word in segment.words or []:
                words.append({"start": float(word.start), "end": float(word.end), "word": word.word})
            text = (segment.text or "").strip()
            texts.append(text)
            segments.append(
                {
                    "id": index,
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": text,
                    "words": words,
                }
            )
        duration = getattr(info, "duration", None)
        payload = {
            "language": getattr(info, "language", None),
            "duration": float(duration) if duration is not None else float(len(audio) / 16000),
            "text": " ".join(t for t in texts if t).strip(),
            "segments": segments,
            "backend": "faster-whisper",
            "model": model_name,
        }
        sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
