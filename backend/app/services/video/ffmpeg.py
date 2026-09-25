from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


class VideoProcessingError(Exception):
    pass


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise VideoProcessingError("FFmpeg/ffprobe is not on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise VideoProcessingError(exc.stderr.strip() or "FFmpeg command failed.") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoProcessingError("FFmpeg timed out.") from exc


def validate_suffix(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise VideoProcessingError(f"Unsupported video type '{suffix or 'unknown'}'.")
    return suffix


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def probe_video(path: Path) -> dict[str, Any]:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video_stream is None:
        raise VideoProcessingError("No video stream found.")
    duration_values: list[float] = []
    for raw in ((payload.get("format") or {}).get("duration"), video_stream.get("duration")):
        try:
            if raw is not None:
                duration_values.append(float(raw))
        except (TypeError, ValueError):
            continue
    duration = max(duration_values) if duration_values else None
    width = video_stream.get("width")
    height = video_stream.get("height")
    return {
        "duration_seconds": duration,
        "width": int(width) if width else None,
        "height": int(height) if height else None,
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def has_audio_stream(path: Path) -> bool:
    return bool(probe_video(path).get("has_audio"))


def write_thumbnail(source: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        _run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                "1",
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-q:v",
                "4",
                str(dest),
            ]
        )
    except VideoProcessingError:
        logger.info("Thumbnail at 1s failed, retrying at 0s for %s", source)
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-q:v",
                "4",
                str(dest),
            ]
        )
    if not dest.exists() or dest.stat().st_size == 0:
        raise VideoProcessingError("Thumbnail was not created.")
    return dest


def extract_wav(source: Path, dest: Path, timeout: int = 3600) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(dest),
        ],
        timeout=timeout,
    )
    if not dest.exists() or dest.stat().st_size == 0:
        raise VideoProcessingError("Could not extract audio for transcription.")
    return dest


def extract_wav_range(
    source: Path,
    dest: Path,
    *,
    start: float,
    duration: float,
    timeout: int = 600,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    start = max(0.0, float(start))
    duration = max(0.05, float(duration))
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(dest),
        ],
        timeout=timeout,
    )
    if not dest.exists() or dest.stat().st_size == 0:
        raise VideoProcessingError("Could not extract audio for transcription.")
    return dest


def copy_if_needed(source: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.resolve() == source.resolve():
        return dest
    shutil.copy2(source, dest)
    return dest


def _subtitles_filter_path(srt: Path) -> str:
    posix = srt.resolve().as_posix()
    escaped = posix.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return escaped


def _filter_path(path: Path) -> str:
    posix = path.resolve().as_posix()
    return posix.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _subs_chain(path: Path | None) -> str:
    if path is None or not path.is_file() or path.stat().st_size <= 0:
        return ""
    return f",subtitles='{_subtitles_filter_path(path)}'"


def _hook_chain(
    hook_line: str | None,
    *,
    hook_file: Path | None,
    hook_font: Path | None,
    content_top: int,
    hook_until: float | None,
) -> str:
    if not hook_line:
        return ""
    from app.services.video.layout import hook_draw_y, hook_layout

    del content_top
    lines, size = hook_layout(hook_line)
    font_bit = f":fontfile='{_filter_path(hook_font)}'" if hook_font is not None else ""
    y0 = hook_draw_y(font_size=size)
    shown = lines or [hook_line]
    if hook_file is not None:
        hook_file.write_text(" ".join(shown), encoding="utf-8")
    enable = ""
    if hook_until is not None and hook_until > 0:
        enable = f":enable=lte(t\\,{float(hook_until):.3f})"
    parts: list[str] = []
    for index, line in enumerate(shown):
        safe = line.replace("\\", "\\\\").replace(":", r"\:").replace("'", "")
        y = y0 + index * (size + 10)
        parts.append(
            f",drawtext=text='{safe}'{font_bit}"
            f":fontsize={size}:fontcolor=white"
            f":borderw=6:bordercolor=black"
            f":expansion=none"
            f":x=(w-text_w)/2:y={y}{enable}"
        )
    return "".join(parts)


def _overlay_parts(
    overlay_rows: list[dict[str, Any]],
    start_label: str,
    *,
    content_bottom: int,
    handle_font: Path | None,
) -> tuple[list[str], str]:
    parts: list[str] = []
    last = start_label
    del content_bottom
    for index, row in enumerate(overlay_rows, start=1):
        x = int(row.get("x") or 40)
        y = int(row.get("y") or 200)
        w = int(row.get("w") or 44)
        h = int(row.get("h") or w)
        fit = str(row.get("fit") or "icon")
        label = f"o{index}"
        nxt = f"v{index}"
        if fit == "banner":
            parts.append(
                f"[{index}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black[{label}]"
            )
        else:
            parts.append(f"[{index}:v]scale={w}:{w}[{label}]")
        parts.append(f"[{last}][{label}]overlay={x}:{y}:eof_action=pass[{nxt}]")
        last = nxt
        text = str(row.get("label") or "").strip()
        if text:
            font_bit = f":fontfile='{_filter_path(handle_font)}'" if handle_font is not None else ""
            safe = text.replace("\\", "\\\\").replace(":", r"\:").replace("'", "")
            labeled = f"t{index}"
            parts.append(
                f"[{last}]drawtext=text='{safe}'{font_bit}:fontsize=22:fontcolor=white:"
                f"borderw=2:bordercolor=black:expansion=none:x={x + w + 10}:y={y}+({w}-text_h)/2[{labeled}]"
            )
            last = labeled
    return parts, last


def _slice_letterbox(
    source: Path,
    dest: Path,
    *,
    start: float,
    end: float,
    has_audio: bool,
    crop: tuple[int, int, int, int] | None,
    timeout: int,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.05, float(end) - float(start))
    from app.services.video.reframe import vertical_vf

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-vf",
        vertical_vf(crop),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-vsync",
        "cfr",
    ]
    if has_audio:
        cmd.extend(["-c:a", "aac", "-ac", "2", "-b:a", "128k", "-ar", "48000"])
    else:
        cmd.append("-an")
    cmd.append(str(dest))
    _run(cmd, timeout=timeout)
    if not dest.exists() or dest.stat().st_size == 0:
        raise VideoProcessingError("Clip slice was not created.")
    return dest


def scene_times(source: Path, *, limit: int = 24) -> list[float]:
    """Timestamps where the picture changes. Empty if ffmpeg cannot scan."""
    cmd = [
        "ffmpeg",
        "-i",
        str(source),
        "-vf",
        "select='gt(scene,0.35)',showinfo",
        "-an",
        "-f",
        "null",
        "-",
    ]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired):
        return []
    found: list[float] = []
    for match in re.finditer(r"pts_time:([0-9.]+)", proc.stderr or ""):
        try:
            found.append(float(match.group(1)))
        except ValueError:
            continue
        if len(found) >= limit:
            break
    return found


def overlay_cutaway(canvas: Path, source: Path, span: tuple[float, float], fitted: Any) -> None:
    """Cover the picture for ~1s with another shot from the same file. Hook and captions stay."""
    start, end = float(span[0]), float(span[1])
    if end - start < 0.5 or not canvas.is_file():
        return
    info = probe_video(canvas)
    duration = float(info.get("duration_seconds") or 0)
    if duration < 10:
        return
    show = min(1.2, end - start, duration - 2.0)
    t0 = duration * 0.42
    t1 = t0 + show
    from app.services.video.layout import vertical_canvas_vf

    tmp = canvas.with_name(canvas.stem + "_cutaway.mp4")
    vf = vertical_canvas_vf(None)
    crop = f"crop={int(fitted.w)}:{int(fitted.h)}:{int(fitted.x)}:{int(fitted.y)}"
    graph = (
        f"[1:v]{vf},{crop}[cut];"
        f"[0:v][cut]overlay={int(fitted.x)}:{int(fitted.y)}:enable='between(t,{t0:.3f},{t1:.3f})'[v]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(canvas),
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{show:.3f}",
        "-i",
        str(source),
        "-filter_complex",
        graph,
        "-map",
        "[v]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "copy",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(tmp),
    ]
    _run(cmd, timeout=600)
    if not tmp.is_file() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise VideoProcessingError("Cutaway was not created.")
    tmp.replace(canvas)


def _concat_copies(parts: list[Path], dest: Path, timeout: int) -> Path:
    list_path = dest.with_name(dest.stem + "_list.txt")
    lines = []
    for part in parts:
        posix = part.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{posix}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        _run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(dest)],
            timeout=timeout,
        )
    finally:
        list_path.unlink(missing_ok=True)
    if not dest.exists() or dest.stat().st_size == 0:
        raise VideoProcessingError("Could not join hook and body.")
    return dest


def render_vertical_clip(
    source: Path,
    dest: Path,
    *,
    start: float,
    end: float,
    srt_path: Path | None = None,
    has_audio: bool = True,
    force_style: str | None = None,
    crop: tuple[int, int, int, int] | None = None,
    hook_line: str | None = None,
    hook_file: Path | None = None,
    overlays: list[dict[str, Any]] | None = None,
    pieces: list[tuple[float, float]] | None = None,
    hook_until: float | None = None,
    letterbox: bool = True,
    pad_min: bool = True,
    picture_top: int | None = None,
    timeout: int = 600,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    from app.services.ai.editorial.bounds import CLIP_MIN_SECONDS
    from app.services.video.layout import fit_source, windows_font, windows_hook_font
    from app.services.video.reframe import vertical_vf

    _ = force_style
    info = probe_video(source)
    src_w = int(info.get("width") or 1080)
    src_h = int(info.get("height") or 1920)
    fitted = fit_source(src_w, src_h)
    if picture_top is None:
        picture_top = fitted.y
    spans = [(float(a), float(b)) for a, b in (pieces or []) if float(b) - float(a) >= 0.05]
    if len(spans) >= 2:
        tmp = Path(tempfile.mkdtemp(prefix="hookfirst_", dir=str(dest.parent)))
        try:
            parts: list[Path] = []
            for index, (src_s, src_e) in enumerate(spans):
                part = tmp / f"part_{index:03d}.mp4"
                logger.info(
                    "HOOK_FIRST slice %s source %.3f → %.3f duration=%.3f",
                    part.name,
                    src_s,
                    src_e,
                    src_e - src_s,
                )
                _slice_letterbox(
                    source,
                    part,
                    start=src_s,
                    end=src_e,
                    has_audio=has_audio,
                    crop=crop,
                    timeout=timeout,
                )
                parts.append(part)
            joined = tmp / "joined.mp4"
            _concat_copies(parts, joined, timeout)
            total = max(0.05, sum(b - a for a, b in spans))
            return render_vertical_clip(
                joined,
                dest,
                start=0.0,
                end=total,
                srt_path=srt_path,
                has_audio=has_audio,
                hook_line=hook_line,
                hook_file=hook_file,
                overlays=overlays,
                pieces=None,
                letterbox=False,
                pad_min=False,
                picture_top=fitted.y,
                timeout=timeout,
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    duration = max(0.05, float(end) - float(start))
    if pad_min:
        duration = max(duration, CLIP_MIN_SECONDS)
    content_top = int(picture_top)
    content_bottom = fitted.bottom if letterbox else content_top + fitted.h
    vf = vertical_vf(crop) if letterbox else "format=yuv420p"
    hook_chain = _hook_chain(
        hook_line,
        hook_file=hook_file,
        hook_font=windows_hook_font(),
        content_top=content_top,
        hook_until=hook_until,
    )
    subs_chain = _subs_chain(srt_path)
    handle_font = windows_font(True)
    overlay_rows = [row for row in (overlays or []) if Path(str(row.get("path") or "")).is_file()]

    cmd = ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(source)]
    for row in overlay_rows:
        cmd.extend(["-loop", "1", "-t", f"{duration:.3f}", "-i", str(row["path"])])
    cmd.extend(["-t", f"{duration:.3f}"])

    if overlay_rows:
        parts = [f"[0:v]{vf}{hook_chain}[v0]"]
        extra, last = _overlay_parts(
            overlay_rows, "v0", content_bottom=content_bottom, handle_font=handle_font
        )
        parts.extend(extra)
        if subs_chain:
            parts.append(f"[{last}]{subs_chain.lstrip(',')}[vout]")
            last = "vout"
        cmd.extend(["-filter_complex", ";".join(parts), "-map", f"[{last}]"])
        if has_audio:
            cmd.extend(["-map", "0:a?", "-c:a", "aac", "-ac", "2", "-b:a", "128k"])
        else:
            cmd.append("-an")
    else:
        cmd.extend(["-vf", f"{vf}{hook_chain}{subs_chain}"])
        if has_audio:
            cmd.extend(["-c:a", "aac", "-ac", "2", "-b:a", "128k"])
        else:
            cmd.append("-an")

    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )
    _run(cmd, timeout=timeout)
    if not dest.exists() or dest.stat().st_size == 0:
        raise VideoProcessingError("Clip file was not created.")
    return dest
