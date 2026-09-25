from pathlib import Path
import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
MEDIA_DIR = ROOT_DIR / "media"
LOG_DIR = ROOT_DIR / "logs"


def _dotenv_value(name: str, env_path: Path) -> str:
    if not env_path.is_file():
        return ""
    prefix = f"{name}="
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped.startswith(prefix):
            continue
        return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _hydrate_env_key(name: str, token_file: str | None = None) -> None:
    """Project .env wins so a new Groq/Gemini/OpenRouter key is used after restart."""
    file_value = _dotenv_value(name, ROOT_DIR / ".env")
    if file_value:
        os.environ[name] = file_value
        return
    if (os.environ.get(name) or "").strip():
        return
    if token_file:
        token = DATA_DIR / token_file
        if token.is_file():
            value = token.read_text(encoding="utf-8").strip()
            if value:
                os.environ[name] = value


load_dotenv(ROOT_DIR / ".env", override=False)
_hydrate_env_key("AI_API_KEY", "ai.token")
_hydrate_env_key("GEMINI_API_KEY", "gemini.token")
_hydrate_env_key("GROQ_API_KEY", "groq.token")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = f"sqlite:///{(DATA_DIR / 'database.db').as_posix()}"
    quality_threshold: float = 0.5
    ai_provider: str = "openrouter"
    ai_api_base_url: str = "https://openrouter.ai/api/v1"
    ai_api_key: str = ""
    ai_model: str = "z-ai/glm-5.2:free"
    ai_fallback_models: str = "openrouter/free"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    gemini_api_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_api_base_url: str = "https://api.groq.com/openai/v1"
    transcription_backend: str = "faster-whisper"
    whisper_model: str = "tiny"
    whisper_device: str = "cpu"
    projects_dir: str = str(ROOT_DIR / "projects")

    def ensure_dirs(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        Path(self.projects_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
