from pathlib import Path

from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.models.entities import Clip

client = TestClient(app)


def test_project_remove_hides_from_workbench() -> None:
    project = client.post("/api/projects", json={"name": "Keep In Library"}).json()
    db = SessionLocal()
    try:
        folder = Path(project["folder_path"]) / "clips"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "keep.mp4"
        path.write_bytes(b"mp4")
        clip = Clip(
            account_id=project["account_id"],
            project_id=project["id"],
            title="Kept bit",
            status="ready",
            file_path=str(path),
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)
        clip_id = clip.id
    finally:
        db.close()

    on_project = client.get("/api/clips", params={"project_id": project["id"], "in_project": True}).json()
    assert any(row["id"] == clip_id for row in on_project)

    removed = client.post("/api/clips/bulk-remove", json={"ids": [clip_id]})
    assert removed.status_code == 204, removed.text
    hidden = client.get("/api/clips", params={"project_id": project["id"], "in_project": True}).json()
    assert all(row["id"] != clip_id for row in hidden)


def test_delete_project_wipes_clips() -> None:
    project = client.post("/api/projects", json={"name": "Delete Wipes Clips"}).json()
    db = SessionLocal()
    try:
        folder = Path(project["folder_path"]) / "clips"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "wipe.mp4"
        path.write_bytes(b"mp4")
        hook = folder / "clip_pending_hook.txt"
        clip = Clip(
            account_id=project["account_id"],
            project_id=project["id"],
            title="Old cut",
            status="ready",
            file_path=str(path),
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)
        clip_id = clip.id
        hook = folder / f"clip_{clip_id}_hook.txt"
        hook.write_text("hook", encoding="utf-8")
    finally:
        db.close()

    deleted = client.delete(f"/api/projects/{project['id']}")
    assert deleted.status_code == 204, deleted.text
    leftover = client.get("/api/clips").json()
    assert all(row["id"] != clip_id for row in leftover)
    assert not path.exists()
    assert not hook.exists()


def test_generate_wipe_deletes_old_cuts() -> None:
    from app.models.entities import Project
    from app.services.storage.import_video import hide_current_project_clips

    project = client.post("/api/projects", json={"name": "Clear On Generate"}).json()
    db = SessionLocal()
    try:
        folder = Path(project["folder_path"]) / "clips"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "old.mp4"
        path.write_bytes(b"mp4")
        clip = Clip(
            account_id=project["account_id"],
            project_id=project["id"],
            title="Old video cut",
            status="ready",
            file_path=str(path),
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)
        clip_id = clip.id
        project_row = db.get(Project, project["id"])
        assert project_row is not None
        hide_current_project_clips(db, project_row)
        db.commit()
        assert db.get(Clip, clip_id) is None
        assert not path.exists()
    finally:
        db.close()
