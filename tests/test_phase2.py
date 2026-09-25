from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.models.entities import AnalysisRun

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "tiny.mp4"


def _tiny_video() -> Path:
    assert FIXTURE.is_file(), "tiny.mp4 fixture missing"
    return FIXTURE


def test_import_and_duplicate_hash() -> None:
    account = client.post("/api/accounts", json={"name": "Import Acc", "platform": "tiktok"}).json()
    project = client.post(
        "/api/projects",
        json={"account_id": account["id"], "name": "Import Project"},
    ).json()
    video = _tiny_video()
    with video.open("rb") as handle:
        first = client.post(
            f"/api/projects/{project['id']}/source",
            files={"file": ("tiny.mp4", handle, "video/mp4")},
        )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["file_hash"]
    assert body["width"] == 320
    assert body["height"] == 240
    assert body["thumbnail_url"]

    with video.open("rb") as handle:
        second = client.post(
            f"/api/projects/{project['id']}/source",
            files={"file": ("tiny.mp4", handle, "video/mp4")},
        )
    assert second.status_code == 200, second.text
    assert second.json()["id"] == body["id"]
    assert second.json()["reused"] is True

    listed = client.get(f"/api/projects/{project['id']}/source")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_delete_source_then_reimport() -> None:
    project = client.post("/api/projects", json={"name": "Replace Source"}).json()
    video = _tiny_video()
    with video.open("rb") as handle:
        first = client.post(
            f"/api/projects/{project['id']}/source",
            files={"file": ("tiny.mp4", handle, "video/mp4")},
        )
    assert first.status_code == 200, first.text
    source_id = first.json()["id"]
    removed = client.delete(f"/api/projects/{project['id']}/source/{source_id}")
    assert removed.status_code == 204
    listed = client.get(f"/api/projects/{project['id']}/source")
    assert listed.json() == []
    with video.open("rb") as handle:
        again = client.post(
            f"/api/projects/{project['id']}/source",
            files={"file": ("tiny.mp4", handle, "video/mp4")},
        )
    assert again.status_code == 200, again.text


def test_new_upload_replaces_previous_source(tmp_path: Path) -> None:
    project = client.post("/api/projects", json={"name": "Swap Source"}).json()
    video = _tiny_video()
    with video.open("rb") as handle:
        first = client.post(
            f"/api/projects/{project['id']}/source",
            files={"file": ("tiny.mp4", handle, "video/mp4")},
        )
    assert first.status_code == 200, first.text
    other = tmp_path / "other.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=0.5",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(other),
        ],
        check=True,
        capture_output=True,
    )
    with other.open("rb") as handle:
        second = client.post(
            f"/api/projects/{project['id']}/source",
            files={"file": ("other.mp4", handle, "video/mp4")},
        )
    assert second.status_code == 200, second.text
    listed = client.get(f"/api/projects/{project['id']}/source")
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["file_hash"] == second.json()["file_hash"]
    assert rows[0]["file_hash"] != first.json()["file_hash"]


def test_generate_needs_video_then_scores_without_padding() -> None:
    project = client.post("/api/projects", json={"name": "Generate Flow"}).json()
    empty = client.get(f"/api/projects/{project['id']}/job")
    assert empty.status_code == 204

    blocked = client.post(f"/api/projects/{project['id']}/generate")
    assert blocked.status_code == 400

    patched = client.patch(
        f"/api/projects/{project['id']}",
        json={"clip_count": 5, "strategy": "funny"},
    )
    assert patched.status_code == 200

    video = _tiny_video()
    with video.open("rb") as handle:
        imported = client.post(
            f"/api/projects/{project['id']}/source",
            files={"file": ("tiny.mp4", handle, "video/mp4")},
        )
    assert imported.status_code == 200

    started = client.post(f"/api/projects/{project['id']}/generate")
    assert started.status_code == 200
    job = client.get(f"/api/projects/{project['id']}/job")
    assert job.status_code == 200
    body = job.json()
    assert body["status"] == "COMPLETED"
    assert body["progress"] == 100
    clips = client.get(f"/api/clips?project_id={project['id']}")
    assert clips.status_code == 200
    assert clips.json() == []
    db = SessionLocal()
    try:
        run = db.scalar(select(AnalysisRun).where(AnalysisRun.project_id == project["id"]))
        assert run is not None
        assert run.result_path
        assert Path(run.result_path).is_file()
    finally:
        db.close()


def test_reject_non_video() -> None:
    account = client.post("/api/accounts", json={"name": "Bad Acc"}).json()
    project = client.post("/api/projects", json={"account_id": account["id"], "name": "Bad"}).json()
    rejected = client.post(
        f"/api/projects/{project['id']}/source",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert rejected.status_code == 400


def test_stop_generate_without_active_job() -> None:
    project = client.post("/api/projects", json={"name": "Stop Idle"}).json()
    stopped = client.post(f"/api/projects/{project['id']}/generate/stop")
    assert stopped.status_code == 409
