from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "backend" / ".venv-whisper" / "Scripts" / "python.exe"
SCRIPT = ROOT / "backend" / "scripts" / "transcribe_wav.py"


def test_whisper_sidecar_reads_pcm_wav(tmp_path: Path) -> None:
    if not SIDECAR.is_file():
        return
    wav = tmp_path / "tone.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(wav),
        ],
        check=True,
        capture_output=True,
    )
    completed = subprocess.run(
        [str(SIDECAR), str(SCRIPT), str(wav), "tiny", "cpu"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["backend"] == "faster-whisper"
    assert payload["duration"]
