from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_account_and_project() -> None:
    created = client.post(
        "/api/accounts",
        json={"name": "Business TikTok", "platform": "tiktok", "handle": "@biz"},
    )
    assert created.status_code == 200
    account_id = created.json()["id"]

    listed = client.get("/api/accounts")
    assert listed.status_code == 200
    assert any(item["id"] == account_id for item in listed.json())

    project = client.post(
        "/api/projects",
        json={"account_id": account_id, "name": "Podcast Episode 42"},
    )
    assert project.status_code == 200
    body = project.json()
    assert body["account_id"] == account_id
    assert body["clip_count"] is None
    assert body["folder_path"]
    assert Path(body["folder_path"]).is_dir()

    missing = client.post("/api/projects", json={"account_id": 999999, "name": "Nope"})
    assert missing.status_code == 400


def test_project_without_account_and_delete() -> None:
    created = client.post("/api/projects", json={"name": "Solo Project", "clip_count": 5})
    assert created.status_code == 200
    body = created.json()
    assert body["clip_count"] == 5
    folder = body["folder_path"]
    project_id = body["id"]
    deleted = client.delete(f"/api/projects/{project_id}")
    assert deleted.status_code == 204
    missing = client.get(f"/api/projects/{project_id}")
    assert missing.status_code == 404
    assert not Path(folder).exists()


def test_dashboard_and_project_grid_fields() -> None:
    client.post("/api/projects", json={"name": "Dash Project"})
    dash = client.get("/api/dashboard")
    assert dash.status_code == 200, dash.text
    body = dash.json()
    assert body["project_count"] >= 1
    assert "clip_count" in body
    assert "download_count" in body
    assert isinstance(body["recent_projects"], list)
    assert isinstance(body["recent_activity"], list)


def test_bulk_delete_missing_clips() -> None:
    missing = client.post("/api/clips/bulk-delete", json={"ids": [999999]})
    assert missing.status_code == 404


def test_delete_project_with_imported_video() -> None:
    from pathlib import Path

    project = client.post("/api/projects", json={"name": "Delete With Source"}).json()
    video = Path(__file__).resolve().parent / "fixtures" / "tiny.mp4"
    with video.open("rb") as handle:
        imported = client.post(
            f"/api/projects/{project['id']}/source",
            files={"file": ("tiny.mp4", handle, "video/mp4")},
        )
    assert imported.status_code == 200, imported.text
    deleted = client.delete(f"/api/projects/{project['id']}")
    assert deleted.status_code == 204, deleted.text
    missing = client.get(f"/api/projects/{project['id']}")
    assert missing.status_code == 404
    fresh = client.post("/api/projects", json={"name": "Same Video Again"}).json()
    with video.open("rb") as handle:
        again = client.post(
            f"/api/projects/{fresh['id']}/source",
            files={"file": ("tiny.mp4", handle, "video/mp4")},
        )
    assert again.status_code == 200, again.text
    assert again.json()["reused"] is False
