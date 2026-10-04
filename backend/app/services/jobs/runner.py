import json
import logging
from pathlib import Path
from time import sleep

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.entities import AnalysisRun, Clip, ProcessingJob, Project, SourceVideo
from app.services.ai.editorial import run_editorial
from app.services.ai.factory import get_ai_provider
from app.services.ai.chat import AIProviderError
from app.services.branding.icons import write_platform_icon
from app.services.branding.normalize import branding_items, parse_branding
from app.services.captions.classic import build_cues_on_timeline, cues_to_ass
from app.services.ai.usage import begin_usage, end_usage
from app.services.jobs.control import JobCancelled, begin_job, end_job, raise_if_cancelled
from app.services.storage.import_video import _drop_other_sources, hide_current_project_clips
from app.services.storage.purge import erase_project_cuts
from app.services.video.ffmpeg import (
    VideoProcessingError,
    extract_wav_range,
    has_audio_stream,
    overlay_cutaway,
    probe_video,
    render_vertical_clip,
    scene_times,
    sha256_file,
)
from app.services.storage.paths import (
    ensure_project_folder,
    project_analysis_dir,
    project_branding_dir,
    project_clips_dir,
    clip_file_stem,
    unique_clip_path,
)
from app.services.transcription.factory import get_transcription_provider
from app.services.transcription.provider import TranscriptionError
from app.services.transcription.shift import CHUNK_SECONDS, merge_transcript, shift_transcript, transcript_complete
from app.services.ai.editorial.bounds import CLIP_MIN_SECONDS, PLATFORM_MAX_SECONDS, _ensure_min_length
from app.services.video.layout import (
    FittedVideo,
    caption_margin_v,
    clean_hook_line,
    extract_hook_line,
    fit_source,
    social_placement,
)
from app.services.video.timeline import (
    apply_piece_joins,
    hook_first_pieces,
    hook_until,
    output_duration,
    pick_cutaway,
    resolve_hook_at,
    tighten_pieces,
)

logger = logging.getLogger(__name__)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _transcript_words(payload: dict) -> list[dict]:
    words: list[dict] = []
    for seg in payload.get("segments") or []:
        inner = seg.get("words") or []
        if inner:
            words.extend(inner)
        else:
            words.append({"start": seg.get("start"), "end": seg.get("end"), "text": seg.get("text")})
    return words


def _clip_title(row: dict, index: int, hook_line: str = "") -> str:
    line = str(hook_line or "").strip()
    if line:
        return line[:80]
    reason = str(row.get("reason") or "").strip()
    if reason:
        return reason[:80]
    start = int(row["start"])
    return f"Clip {index} · {start}s"


def _branding_overlays(project: Project, work_dir: Path, video: FittedVideo) -> list[dict]:
    items = branding_items(parse_branding(getattr(project, "branding_json", None)))
    if not items:
        return []
    work_dir.mkdir(parents=True, exist_ok=True)
    icon = 44
    overlays: list[dict] = []
    if items and items[0].get("fit") == "banner":
        path = Path(str(items[0].get("logo") or ""))
        pos = social_placement(video, 0, 96)
        if path.is_file() and pos is not None:
            overlays.append(
                {
                    "path": str(path),
                    "x": pos[0],
                    "y": pos[1],
                    "w": 96,
                    "h": 96,
                    "fit": "banner",
                    "label": "",
                }
            )
        return overlays
    for index, item in enumerate(items):
        pos = social_placement(video, index, icon)
        if pos is None:
            break
        path = work_dir / f"{item['platform']}.png"
        write_platform_icon(item["platform"], path)
        overlays.append(
            {
                "path": str(path),
                "x": pos[0],
                "y": pos[1],
                "w": icon,
                "fit": "icon",
                "label": item.get("name") or "",
            }
        )
    return overlays


def run_generate_job(job_id: int) -> None:
    db = SessionLocal()
    begin_job(job_id)
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return
        job.status = "ANALYZING"
        job.stage_message = "Checking the imported video"
        job.progress = 12
        db.commit()
        sleep(0.1)

        source = None
        if job.source_id:
            source = db.get(SourceVideo, job.source_id)
            if source is None or source.project_id != job.project_id:
                job.status = "FAILED"
                job.stage_message = "Video was replaced"
                job.error_message = "The imported video changed. Drop it again and Generate."
                job.progress = 0
                db.commit()
                return
        else:
            source = db.scalar(
                select(SourceVideo).where(SourceVideo.project_id == job.project_id).order_by(SourceVideo.id.desc())
            )
        if source is None:
            job.status = "FAILED"
            job.stage_message = "No video imported"
            job.error_message = "Drop a video first."
            job.progress = 0
            db.commit()
            return

        project = db.get(Project, job.project_id)
        if project is None:
            job.status = "FAILED"
            job.stage_message = "Project missing"
            job.error_message = "Project was deleted."
            job.progress = 0
            db.commit()
            return

        _drop_other_sources(db, project, source.id)
        db.flush()
        source = db.get(SourceVideo, source.id)
        if source is None:
            job.status = "FAILED"
            job.stage_message = "No video imported"
            job.error_message = "Drop a video first."
            job.progress = 0
            db.commit()
            return

        media = Path(source.file_path)
        if not media.is_file():
            job.status = "FAILED"
            job.stage_message = "Source file missing"
            job.error_message = "The imported video is no longer on disk."
            job.progress = 0
            db.commit()
            return

        disk_hash = sha256_file(media)
        if disk_hash != source.file_hash:
            job.status = "FAILED"
            job.stage_message = "Wrong video on disk"
            job.error_message = "The file on disk is not the video you imported. Drop the video again."
            job.progress = 0
            db.commit()
            return

        probed = probe_video(media)
        if probed.get("duration_seconds"):
            video_duration = float(probed["duration_seconds"])
            source.duration_seconds = video_duration
            db.commit()
        else:
            video_duration = float(source.duration_seconds) if source.duration_seconds else None

        logger.info(
            "GENERATE source id=%s hash=%s path=%s duration=%s",
            source.id,
            source.file_hash,
            media,
            source.duration_seconds,
        )

        begin_usage(job_id=job_id, project_id=project.id)

        hide_current_project_clips(db, project)
        erase_project_cuts(project)
        db.commit()

        if not project.folder_path:
            ensure_project_folder(project)
            db.commit()
        analysis_dir = project_analysis_dir(project)
        transcript_path = analysis_dir / f"transcript_{source.file_hash}.json"
        user_max = int(project.clip_count) if project.clip_count else None

        def on_progress(status: str, message: str, value: int) -> None:
            job.status = status
            job.stage_message = message
            job.progress = value
            db.commit()

        job.status = "TRANSCRIBING"
        job.stage_message = "Transcribing the full video"
        job.progress = 28
        db.commit()

        try:
            if transcript_path.is_file():
                payload = json.loads(transcript_path.read_text(encoding="utf-8"))
                cached_dur = float(payload.get("duration") or 0)
                if not transcript_complete(payload, video_duration):
                    payload = None
                elif video_duration and cached_dur and abs(cached_dur - video_duration) > 8.0:
                    logger.info(
                        "Ignoring transcript cache duration %.1f vs source %.1f",
                        cached_dur,
                        video_duration,
                    )
                    payload = None
                else:
                    job.stage_message = "Using saved transcript"
                    job.progress = 45
                    db.commit()
            else:
                payload = None
            if payload is None:
                if not has_audio_stream(media):
                    payload = {
                        "language": None,
                        "duration": source.duration_seconds,
                        "text": "",
                        "segments": [],
                        "backend": "none",
                        "model": None,
                        "note": "no_audio",
                    }
                    _write_json(transcript_path, payload)
                    job.stage_message = "No speech track on this video"
                    job.progress = 45
                    db.commit()
                else:
                    duration = float(video_duration or 0)
                    merged: dict = {
                        "language": None,
                        "duration": duration,
                        "text": "",
                        "segments": [],
                        "backend": "faster-whisper",
                        "model": None,
                    }
                    lookback = 15.0
                    offset = 0.0
                    chunk_i = 0
                    while True:
                        raise_if_cancelled(job_id)
                        remaining = duration - offset if duration > 0 else CHUNK_SECONDS
                        if duration > 0 and remaining <= 0.05:
                            break
                        start = 0.0 if offset == 0 else max(0.0, offset - lookback)
                        slice_dur = CHUNK_SECONDS + (0.0 if offset == 0 else lookback)
                        if duration > 0:
                            slice_dur = min(slice_dur, duration - start)
                        wav_path = analysis_dir / f"audio_{source.file_hash}_{chunk_i}.wav"
                        extract_wav_range(media, wav_path, start=start, duration=slice_dur)
                        try:
                            piece = get_transcription_provider().transcribe(wav_path)
                        finally:
                            wav_path.unlink(missing_ok=True)
                        merged = merge_transcript(merged, shift_transcript(piece, start))
                        chunk_i += 1
                        offset += CHUNK_SECONDS
                        shown = int(min(offset, duration) if duration > 0 else offset)
                        job.stage_message = f"Transcribing {shown}s"
                        job.progress = 28 + int(17 * min(1.0, offset / max(duration, CHUNK_SECONDS)))
                        db.commit()
                        if duration <= 0:
                            break
                    payload = merged
                    _write_json(transcript_path, payload)
        except (VideoProcessingError, TranscriptionError, OSError, json.JSONDecodeError) as exc:
            logger.exception("Transcription failed for job %s", job_id)
            job.status = "FAILED"
            job.stage_message = "Transcription failed"
            job.error_message = str(exc)
            job.progress = 40
            db.commit()
            return

        run = AnalysisRun(project_id=project.id, status="transcribed", result_path=str(transcript_path))
        db.add(run)
        project.status = "transcribed"
        db.commit()

        raise_if_cancelled(job_id)
        branding = parse_branding(getattr(project, "branding_json", None))
        try:
            selected, artifacts = run_editorial(
                payload,
                provider=get_ai_provider(),
                video_duration=video_duration,
                user_max=user_max,
                wanted_vibes=branding.get("vibes") or [],
                brief=str(branding.get("brief") or ""),
                on_progress=on_progress,
            )
        except AIProviderError as exc:
            job.status = "FAILED"
            job.stage_message = "Viral AI unavailable"
            job.error_message = str(exc)
            job.progress = 60
            db.commit()
            return
        except NotImplementedError as exc:
            job.status = "FAILED"
            job.stage_message = "Viral AI not configured"
            job.error_message = str(exc)
            job.progress = 60
            db.commit()
            return

        _write_json(analysis_dir / f"candidates_{source.file_hash}.json", artifacts)

        if not selected:
            project.status = "scored"
            job.status = "COMPLETED"
            job.progress = 100
            job.stage_message = "0 strong clips found"
            job.error_message = "No moments passed editorial validation. Nothing was padded."
            db.commit()
            return

        job.status = "RENDERING"
        job.stage_message = f"Clipping 0/{len(selected)}"
        job.progress = 90
        db.commit()

        words = _transcript_words(payload)
        clips_dir = project_clips_dir(project)
        clips_dir.mkdir(parents=True, exist_ok=True)
        audio_ok = has_audio_stream(media)
        media_info = probe_video(media)
        video = fit_source(
            int(media_info.get("width") or 1080),
            int(media_info.get("height") or 1920),
        )
        caption_mv = caption_margin_v()
        overlays = _branding_overlays(project, project_branding_dir(project) / "icons", video)
        scenes = scene_times(media)
        rendered = 0
        for index, row in enumerate(selected, start=1):
            job.stage_message = f"Clipping {index}/{len(selected)}"
            job.progress = min(99, 90 + int(8 * index / len(selected)))
            db.commit()
            raise_if_cancelled(job_id)
            if db.get(SourceVideo, source.id) is None:
                raise JobCancelled()
            signals = row.get("signals") or {}
            start = float(row["start"])
            end = float(row["end"])
            hook = resolve_hook_at(signals.get("hook_at"), start, end)
            if hook is not None:
                start = hook
            grown = _ensure_min_length(
                {"start": start, "end": end},
                video_duration,
                PLATFORM_MAX_SECONDS,
                freeze_start=True,
            )
            if grown is None:
                continue
            row = {**row, "start": grown["start"], "end": grown["end"]}
            if float(row["end"]) - float(row["start"]) < CLIP_MIN_SECONDS - 0.05:
                continue
            pieces = tighten_pieces(words, float(row["start"]), float(row["end"]))
            if not pieces:
                pieces = hook_first_pieces(row["start"], row["end"], None)
            pieces = apply_piece_joins(pieces)
            spans = [piece.as_tuple() for piece in pieces]
            cutaway = pick_cutaway(scenes, float(row["start"]), float(row["end"]), float(video_duration or 0))
            hook_line = extract_hook_line(
                words,
                row["start"],
                row["end"],
                signals.get("hook_at"),
                signals.get("hook_line"),
            )
            if not hook_line:
                hook_line = clean_hook_line(str(row.get("reason") or f"Clip {index}"))
            clip = Clip(
                account_id=project.account_id,
                project_id=project.id,
                title=_clip_title(row, index, hook_line),
                description=str(row.get("reason") or ""),
                duration=output_duration(pieces) if pieces else float(row["end"]) - float(row["start"]),
                start_time=row["start"],
                end_time=row["end"],
                quality_score=row["score"],
                viral_signals=json.dumps(
                    {
                        **signals,
                        "hook_line": hook_line,
                        "hook_first": False,
                        "source_hash": source.file_hash,
                        "clip_index": index,
                    }
                ),
                strategy="mixed",
                status="pending_render",
                ai_analysis=str(row.get("reason") or ""),
            )
            db.add(clip)
            db.commit()
            db.refresh(clip)
            stem = clip_file_stem(clip.title, clip.id, index)
            ass_path = clips_dir / f"clip_{clip.id}.ass"
            cues = build_cues_on_timeline(words, pieces) if project.captions_enabled else []
            if cues:
                ass_path.write_text(
                    cues_to_ass(cues, margin_v=caption_mv, style=project.caption_style),
                    encoding="utf-8",
                )
            hook_file = clips_dir / f"clip_{clip.id}_hook.txt"
            hook_file.write_text(hook_line, encoding="utf-8")
            dest = unique_clip_path(clips_dir, stem, clip.id, ".mp4")
            try:
                render_vertical_clip(
                    media,
                    dest,
                    start=spans[0][0],
                    end=spans[-1][1] if len(spans) == 1 else spans[0][1],
                    srt_path=ass_path if cues else None,
                    has_audio=audio_ok,
                    crop=None,
                    hook_line=hook_line,
                    hook_file=hook_file,
                    overlays=overlays,
                    pieces=pieces if len(pieces) > 1 else None,
                    hook_until=hook_until(pieces),
                )
                if cutaway is not None:
                    try:
                        overlay_cutaway(dest, media, cutaway, video)
                    except VideoProcessingError:
                        logger.info("Cutaway skipped for clip %s", clip.id)
                clip.file_path = str(dest)
                clip.status = "ready"
                rendered += 1
            except VideoProcessingError:
                logger.exception("Render failed for clip %s", clip.id)
                clip.status = "render_failed"
                clip.file_path = None
            db.commit()

        project.status = "complete"
        job.status = "COMPLETED"
        job.progress = 100
        job.stage_message = f"{rendered} clip{'s' if rendered != 1 else ''} ready"
        job.error_message = None if rendered == len(selected) else f"{len(selected) - rendered} clip(s) failed to cut."
        db.commit()
    except JobCancelled:
        job = db.get(ProcessingJob, job_id)
        if job is not None:
            job.status = "CANCELLED"
            job.stage_message = "Stopped"
            job.error_message = "Generate was stopped."
            job.progress = 0
            project = db.get(Project, job.project_id)
            if project is not None and db.scalar(select(SourceVideo.id).where(SourceVideo.project_id == project.id)) is None:
                hide_current_project_clips(db, project)
                erase_project_cuts(project)
                project.status = "draft"
            elif project is not None and project.status == "processing":
                project.status = "draft"
            db.commit()
    except Exception:
        logger.exception("Generate job %s crashed", job_id)
        job = db.get(ProcessingJob, job_id)
        if job is not None:
            job.status = "FAILED"
            job.stage_message = "Job crashed"
            job.error_message = "Something went wrong while processing. Try generate again."
            db.commit()
    finally:
        end_usage(job_id)
        end_job(job_id)
        db.close()
