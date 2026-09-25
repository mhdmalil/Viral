from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.models.entities import Clip

client = TestClient(app)


def test_library_search_and_tags() -> None:
    project = client.post("/api/projects", json={"name": "Silent Hour"}).json()
    db = SessionLocal()
    try:
        clip = Clip(
            account_id=project["account_id"],
            project_id=project["id"],
            title="Silent library bit",
            status="ready",
            viral_signals='{"hook_at": 12.5}',
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)
        clip_id = clip.id
    finally:
        db.close()

    listed = client.get("/api/clips").json()
    match = next(row for row in listed if row["id"] == clip_id)
    assert match["project_name"] == "Silent Hour"
    assert match["tags"] == []
    assert match["hook_at"] == 12.5
    assert match.get("vibe") in (None, "")

    funny = client.post("/api/projects", json={"name": "Vibe Show"}).json()
    db = SessionLocal()
    try:
        tagged_clip = Clip(
            account_id=funny["account_id"],
            project_id=funny["id"],
            title="Punchline",
            status="ready",
            viral_signals='{"hook_at": 3, "vibe": "Funny"}',
        )
        db.add(tagged_clip)
        db.commit()
        vibe_id = tagged_clip.id
    finally:
        db.close()
    vibe_row = next(row for row in client.get("/api/clips").json() if row["id"] == vibe_id)
    assert vibe_row["vibe"] == "funny"

    extra = client.post("/api/projects", json={"name": "Talk Show"}).json()
    db = SessionLocal()
    try:
        info_clip = Clip(
            account_id=extra["account_id"],
            project_id=extra["id"],
            title="Rates",
            status="ready",
            viral_signals='{"vibe": "information"}',
        )
        db.add(info_clip)
        db.commit()
        info_id = info_clip.id
    finally:
        db.close()
    info_row = next(row for row in client.get("/api/clips").json() if row["id"] == info_id)
    assert info_row["vibe"] == "informative"
    assert info_row["vibes"] == ["informative"]
    mix = client.post("/api/projects", json={"name": "Mix"}).json()
    db = SessionLocal()
    try:
        mix_clip = Clip(
            account_id=mix["account_id"],
            project_id=mix["id"],
            title="Joke lesson",
            status="ready",
            viral_signals='{"vibes": ["funny", "informative"]}',
        )
        db.add(mix_clip)
        db.commit()
        mix_id = mix_clip.id
    finally:
        db.close()
    mixed = client.get("/api/clips", params={"vibes": "informative"}).json()
    assert any(row["id"] == mix_id for row in mixed)
    assert any(row["id"] == info_id for row in mixed)
    filtered = client.get("/api/clips", params={"vibes": "informative,financial"}).json()
    assert any(row["id"] == info_id for row in filtered)
    assert any(row["id"] == mix_id for row in filtered)
    assert all({"informative", "financial"}.intersection(row.get("vibes") or []) for row in filtered)

    found = client.get("/api/clips", params={"q": "silent"}).json()
    assert any(row["id"] == clip_id for row in found)
    by_project = client.get("/api/clips", params={"q": "Hour"}).json()
    assert any(row["id"] == clip_id for row in by_project)
    missing = client.get("/api/clips", params={"q": "zzzz-nope"}).json()
    assert all(row["id"] != clip_id for row in missing)

    patched = client.patch(f"/api/clips/{clip_id}", json={"tags": ["Hook", "hook", ""]})
    assert patched.status_code == 200, patched.text
    assert patched.json()["tags"] == ["hook"]
    tagged = client.get("/api/clips", params={"tag": "hook"}).json()
    assert any(row["id"] == clip_id for row in tagged)
    names = client.get("/api/tags").json()
    assert "hook" in names
    ready = client.get("/api/clips", params={"ready": True}).json()
    assert all(row["id"] != clip_id for row in ready)
