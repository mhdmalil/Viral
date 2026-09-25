import os
from pathlib import Path

os.environ["TRANSCRIPTION_BACKEND"] = "test"
os.environ["WHISPER_MODEL"] = "tiny"
os.environ["WHISPER_DEVICE"] = "cpu"
os.environ["AI_PROVIDER"] = "test"

_TEST_DIR = Path(__file__).resolve().parent / ".tmp"
_TEST_DIR.mkdir(parents=True, exist_ok=True)
_TEST_DB = _TEST_DIR / "pytest.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["PROJECTS_DIR"] = str((_TEST_DIR / "projects").as_posix())
