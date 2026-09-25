from app.services.ai.routing import iter_chat_targets, openrouter_free_ids


def test_openrouter_free_ids_skips_primary() -> None:
    catalog = {
        "data": [
            {"id": "z-ai/glm-5.2:free"},
            {"id": "acme/other:free"},
            {"id": "paid/model"},
        ]
    }
    assert openrouter_free_ids(catalog, skip={"z-ai/glm-5.2:free"}) == ["acme/other:free"]


def test_iter_chat_targets_order(monkeypatch: object) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "ai_api_key", "or-key")
    monkeypatch.setattr(config.settings, "ai_model", "z-ai/glm-5.2:free")
    monkeypatch.setattr(config.settings, "ai_fallback_models", "openrouter/free")
    monkeypatch.setattr(config.settings, "ai_api_base_url", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(config.settings, "gemini_api_key", "gem-key")
    monkeypatch.setattr(config.settings, "gemini_model", "gemini-flash-latest")
    monkeypatch.setattr(config.settings, "gemini_api_base_url", "https://generativelanguage.googleapis.com/v1beta/openai")
    monkeypatch.setattr(config.settings, "groq_api_key", "groq-key")
    monkeypatch.setattr(config.settings, "groq_model", "openai/gpt-oss-120b")
    monkeypatch.setattr(config.settings, "groq_api_base_url", "https://api.groq.com/openai/v1")

    rows = list(iter_chat_targets(catalog_ids=["acme/other:free"], rotate=0))
    chain = [(row.provider, row.model) for row in rows]
    groq = [model for provider, model in chain if provider == "groq"]
    gemini = [model for provider, model in chain if provider == "gemini"]
    assert groq == ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
    assert gemini[0] == "gemini-flash-latest"
    assert "gemini-2.5-flash" not in gemini
    groq_at = next(i for i, row in enumerate(chain) if row[0] == "groq")
    last_groq = max(i for i, row in enumerate(chain) if row[0] == "groq")
    gem_at = next(i for i, row in enumerate(chain) if row[0] == "gemini")
    glm_at = chain.index(("openrouter", "z-ai/glm-5.2:free"))
    extra_at = chain.index(("openrouter", "openrouter/free"))
    assert groq_at < last_groq < gem_at < glm_at < extra_at


def test_iter_chat_targets_rotates_models_inside_provider(monkeypatch: object) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "ai_api_key", "or-key")
    monkeypatch.setattr(config.settings, "ai_model", "z-ai/glm-5.2:free")
    monkeypatch.setattr(config.settings, "ai_fallback_models", "")
    monkeypatch.setattr(config.settings, "ai_api_base_url", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(config.settings, "gemini_api_key", "gem-key")
    monkeypatch.setattr(config.settings, "gemini_model", "gemini-flash-latest")
    monkeypatch.setattr(config.settings, "gemini_api_base_url", "https://generativelanguage.googleapis.com/v1beta/openai")
    monkeypatch.setattr(config.settings, "groq_api_key", "groq-key")
    monkeypatch.setattr(config.settings, "groq_model", "openai/gpt-oss-120b")
    monkeypatch.setattr(config.settings, "groq_api_base_url", "https://api.groq.com/openai/v1")

    first = [row.model for row in iter_chat_targets(rotate=0) if row.provider == "groq"]
    second = [row.model for row in iter_chat_targets(rotate=1) if row.provider == "groq"]
    assert first[0] == "openai/gpt-oss-120b"
    assert second[0] == "openai/gpt-oss-20b"
    assert set(first) == set(second)


def test_openrouter_free_ids_skips_vl() -> None:
    catalog = {
        "data": [
            {"id": "acme/chat:free"},
            {"id": "acme/vision-vl:free"},
            {"id": "acme/whisper:free"},
        ]
    }
    assert openrouter_free_ids(catalog, skip=set()) == ["acme/chat:free"]


def test_dead_env_model_is_skipped(monkeypatch: object) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "ai_api_key", "")
    monkeypatch.setattr(config.settings, "gemini_api_key", "gem-key")
    monkeypatch.setattr(config.settings, "gemini_model", "gemini-2.5-flash")
    monkeypatch.setattr(config.settings, "gemini_api_base_url", "https://generativelanguage.googleapis.com/v1beta/openai")
    monkeypatch.setattr(config.settings, "groq_api_key", "")
    gemini = [row.model for row in iter_chat_targets(rotate=0) if row.provider == "gemini"]
    assert "gemini-2.5-flash" not in gemini
    assert gemini[0] == "gemini-flash-latest"


def test_prefer_reuses_working_model_first(monkeypatch: object) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "ai_api_key", "")
    monkeypatch.setattr(config.settings, "gemini_api_key", "")
    monkeypatch.setattr(config.settings, "groq_api_key", "groq-key")
    monkeypatch.setattr(config.settings, "groq_model", "openai/gpt-oss-120b")
    monkeypatch.setattr(config.settings, "groq_api_base_url", "https://api.groq.com/openai/v1")
    rows = list(iter_chat_targets(rotate=1, prefer=("groq", "qwen/qwen3.8-27b")))
    groq = [row.model for row in rows if row.provider == "groq"]
    assert groq[0] == "qwen/qwen3.8-27b"
    assert "openai/gpt-oss-20b" in groq
