from fastapi.testclient import TestClient


def test_spa_served_when_dist_exists(tmp_path, monkeypatch) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><html><body>desktop</body></html>", encoding="utf-8")
    (dist / "favicon.ico").write_bytes(b"ico")
    monkeypatch.setattr("app.main.FRONTEND_DIST", dist)
    from app.main import create_app

    client = TestClient(create_app())
    home = client.get("/")
    assert home.status_code == 200
    assert b"desktop" in home.content
    nested = client.get("/library")
    assert nested.status_code == 200
    assert b"desktop" in nested.content
    asset = client.get("/favicon.ico")
    assert asset.status_code == 200
    assert asset.content == b"ico"
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
