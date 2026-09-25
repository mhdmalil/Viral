from pathlib import Path

from app.database.session import SessionLocal
from app.main import app
from app.models.entities import Account, Clip, Project
from app.services.storage.purge import purge_project, wipe_clips_matching_hash, wipe_project_clips

_ = app


def test_wipe_project_clips_deletes_mp4_and_hook(tmp_path: Path) -> None:
    db = SessionLocal()
    try:
        account = Account(name="Wipe", platform="tiktok", handle="wipe-src")
        db.add(account)
        db.flush()
        folder = tmp_path / "proj"
        clips_dir = folder / "clips"
        clips_dir.mkdir(parents=True)
        project = Project(account_id=account.id, name="Wipe Me", folder_path=str(folder), status="ready")
        db.add(project)
        db.flush()
        mp4 = clips_dir / "01 - old.mp4"
        hook = clips_dir / "clip_1_hook.txt"
        mp4.write_bytes(b"old")
        hook.write_text("old hook", encoding="utf-8")
        clip = Clip(
            account_id=account.id,
            project_id=project.id,
            title="old",
            status="ready",
            file_path=str(mp4),
            viral_signals='{"source_hash":"abc","hook_line":"old hook"}',
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)
        hook = clips_dir / f"clip_{clip.id}_hook.txt"
        hook.write_text("old hook", encoding="utf-8")
        assert wipe_project_clips(db, project) == 1
        db.commit()
        assert db.get(Clip, clip.id) is None
        assert not mp4.exists()
        assert not hook.exists()
        leftover = list(clips_dir.iterdir())
        assert leftover == []
    finally:
        db.close()


def test_wipe_matching_hash_clears_library_copies(tmp_path: Path) -> None:
    db = SessionLocal()
    try:
        account = Account(name="Hash", platform="tiktok", handle="wipe-hash")
        db.add(account)
        db.flush()
        a = Project(account_id=account.id, name="A", folder_path=str(tmp_path / "a"), status="ready")
        b = Project(account_id=account.id, name="B", folder_path=str(tmp_path / "b"), status="ready")
        db.add_all([a, b])
        db.flush()
        (tmp_path / "a" / "clips").mkdir(parents=True)
        (tmp_path / "b" / "clips").mkdir(parents=True)
        path = tmp_path / "a" / "clips" / "gone.mp4"
        path.write_bytes(b"x")
        clip = Clip(
            account_id=account.id,
            project_id=b.id,
            title="moved",
            status="ready",
            file_path=str(path),
            viral_signals='{"source_hash":"deadbeef"}',
        )
        db.add(clip)
        db.commit()
        assert wipe_clips_matching_hash(db, "deadbeef") == 1
        db.commit()
        assert db.get(Clip, clip.id) is None
        assert not path.exists()
    finally:
        db.close()


def test_purge_project_deletes_clips_not_library() -> None:
    db = SessionLocal()
    try:
        account = Account(name="Purge", platform="tiktok", handle="wipe-purge")
        db.add(account)
        db.flush()
        from app.core.config import settings

        folder = Path(settings.projects_dir) / "9999_purge_test"
        clips_dir = folder / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        project = Project(account_id=account.id, name="Purge Me", folder_path=str(folder), status="ready")
        db.add(project)
        db.flush()
        path = clips_dir / "keep-not.mp4"
        path.write_bytes(b"mp4")
        clip = Clip(
            account_id=account.id,
            project_id=project.id,
            title="gone",
            status="ready",
            file_path=str(path),
        )
        db.add(clip)
        db.commit()
        clip_id = clip.id
        purge_project(db, project)
        db2 = SessionLocal()
        try:
            assert db2.get(Clip, clip_id) is None
            assert db2.get(Project, project.id) is None
        finally:
            db2.close()
        assert not path.exists()
    finally:
        db.close()


def test_abandon_stale_rendering_job() -> None:
    from app.api.jobs import abandon_orphan_jobs
    from app.models.entities import ProcessingJob

    db = SessionLocal()
    try:
        account = Account(name="Orphan", platform="tiktok", handle="wipe-orphan")
        db.add(account)
        db.flush()
        project = Project(account_id=account.id, name="Stuck", status="processing")
        db.add(project)
        db.flush()
        job = ProcessingJob(project_id=project.id, status="RENDERING", stage_message="Clipping 1/3", progress=92)
        db.add(job)
        db.commit()
        job_id = job.id
    finally:
        db.close()
    abandon_orphan_jobs()
    db = SessionLocal()
    try:
        row = db.get(ProcessingJob, job_id)
        assert row is not None
        assert row.status == "CANCELLED"
    finally:
        db.close()


def test_workbench_hides_old_clips_without_source_hash() -> None:
    from app.api.clips import workbench_allows_clip

    clip = Clip(title="old", status="ready", viral_signals='{"source_hash":"abc"}')
    assert workbench_allows_clip(clip, None) is False
    assert workbench_allows_clip(clip, "abc") is True
    assert workbench_allows_clip(clip, "other") is False
    bare = Clip(title="bare", status="ready", viral_signals="{}")
    assert workbench_allows_clip(bare, "abc") is False


def test_erase_project_cuts_deletes_transcripts_and_clips(tmp_path: Path) -> None:
    from app.services.storage.purge import erase_project_cuts

    folder = tmp_path / "proj"
    analysis = folder / "analysis"
    clips = folder / "clips"
    analysis.mkdir(parents=True)
    clips.mkdir(parents=True)
    (analysis / "transcript_old.json").write_text("old", encoding="utf-8")
    (analysis / "audio_old_0.wav").write_bytes(b"wav")
    (clips / "01 - old.mp4").write_bytes(b"mp4")
    project = Project(account_id=999999, name="Erase", folder_path=str(folder), status="draft")
    project.id = 999999
    erase_project_cuts(project)
    assert not analysis.exists()
    assert not clips.exists()
