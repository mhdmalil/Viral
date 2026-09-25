from pathlib import Path

from app.core.config import _dotenv_value, _hydrate_env_key


def test_dotenv_value_reads_quoted_and_skips_comments(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("# GROQ_API_KEY=commented\nGROQ_API_KEY=\"gsk_new\"\n", encoding="utf-8")
    assert _dotenv_value("GROQ_API_KEY", env) == "gsk_new"


def test_hydrate_env_key_prefers_dotenv_over_process(monkeypatch: object, tmp_path: Path) -> None:
    from app.core import config

    env = tmp_path / ".env"
    env.write_text("GROQ_API_KEY=gsk_from_file\n", encoding="utf-8")
    monkeypatch.setattr(config, "ROOT_DIR", tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_from_process")
    _hydrate_env_key("GROQ_API_KEY", "groq.token")
    assert config.os.environ["GROQ_API_KEY"] == "gsk_from_file"
