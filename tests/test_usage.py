from fastapi.testclient import TestClient

from app.main import app
from app.services.ai.usage import begin_usage, end_usage, record, set_live

client = TestClient(app)


def test_usage_report_from_recorded_calls() -> None:
    begin_usage(job_id=1, project_id=1)
    set_live("groq", "openai/gpt-oss-120b")
    record(provider="groq", model="openai/gpt-oss-120b", outcome="ok", http_status=200, latency_ms=40, remaining=19, limit=20)
    record(provider="gemini", model="gemini-flash-latest", outcome="429", http_status=429, latency_ms=12)
    end_usage(1)

    payload = client.get("/api/usage").json()
    assert payload["totals"]["requests"] >= 2
    names = {row["provider"] for row in payload["providers"]}
    assert "groq" in names
    assert "gemini" in names
    models = {row["model"] for row in payload["models"]}
    assert "openai/gpt-oss-120b" in models
    assert payload["logs"][0]["provider"] in names
    assert len(payload["series"]) == 60
    assert "at" in payload["series"][0]

    groq = client.get("/api/usage", params={"provider": "groq"}).json()
    assert groq["totals"]["ok"] >= 1
    assert all(row["provider"] == "groq" for row in groq["models"])
    assert {row["provider"] for row in groq["providers"]} == names


def test_reset_usage_clears_history() -> None:
    record(provider="groq", model="reset-probe", outcome="ok", http_status=200, latency_ms=5)
    before = client.get("/api/usage").json()
    assert before["totals"]["requests"] >= 1
    cleared = client.delete("/api/usage")
    assert cleared.status_code == 204
    after = client.get("/api/usage").json()
    assert after["totals"]["requests"] == 0
    assert after["logs"] == []
