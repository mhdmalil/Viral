from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from app.services.video.ffmpeg import _run, probe_video

logger = logging.getLogger(__name__)

TARGET_RATIO = 9 / 16


def _even(value: int) -> int:
    return int(value) // 2 * 2


def nine_sixteen_window(width: int, height: int, cx: float, cy: float) -> tuple[int, int, int, int]:
    """Largest 9:16 crop that fits in the frame, centered on (cx, cy)."""
    width = max(2, int(width))
    height = max(2, int(height))
    if width / height >= TARGET_RATIO:
        crop_h = _even(height)
        crop_w = _even(int(crop_h * TARGET_RATIO))
        crop_w = max(2, min(crop_w, _even(width)))
    else:
        crop_w = _even(width)
        crop_h = _even(int(crop_w / TARGET_RATIO))
        crop_h = max(2, min(crop_h, _even(height)))
    x = _even(int(round(cx - crop_w / 2)))
    y = _even(int(round(cy - crop_h / 2)))
    x = max(0, min(x, width - crop_w))
    y = max(0, min(y, height - crop_h))
    return crop_w, crop_h, x, y


def center_window(width: int, height: int) -> tuple[int, int, int, int]:
    return nine_sixteen_window(width, height, width / 2, height / 2)


def _extract_sample_frames(source: Path, start: float, end: float, dest_dir: Path) -> list[Path]:
    duration = max(0.05, float(end) - float(start))
    stamps = [start + duration * t for t in (0.15, 0.35, 0.5, 0.65, 0.85)]
    frames: list[Path] = []
    for index, stamp in enumerate(stamps):
        dest = dest_dir / f"frame_{index}.jpg"
        try:
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{max(0.0, stamp):.3f}",
                    "-i",
                    str(source),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "5",
                    str(dest),
                ],
                timeout=30,
            )
        except Exception:
            logger.debug("Reframe sample %s failed", stamp, exc_info=True)
            continue
        if dest.is_file() and dest.stat().st_size > 0:
            frames.append(dest)
    return frames


def _face_centers(frames: list[Path]) -> list[tuple[float, float, int, int]]:
    try:
        import cv2  # type: ignore  # noqa: F401
    except ImportError:
        return _face_centers_sidecar(frames)
    return _face_centers_cv2(frames)


def _face_centers_cv2(frames: list[Path]) -> list[tuple[float, float, int, int]]:
    try:
        import cv2  # type: ignore
    except ImportError:
        return []
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    if not cascade_path.is_file():
        return []
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        return []
    hits: list[tuple[float, float, int, int]] = []
    for frame_path in frames:
        image = cv2.imread(str(frame_path))
        if image is None:
            continue
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        scale = 1.0
        if width > 640:
            scale = 640 / width
            gray = cv2.resize(gray, (int(width * scale), int(height * scale)))
        faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(32, 32))
        if len(faces) == 0:
            continue
        x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
        cx = (x + w / 2) / scale
        cy = (y + h / 2) / scale
        hits.append((cx, cy, width, height))
    return hits


def _face_centers_sidecar(frames: list[Path]) -> list[tuple[float, float, int, int]]:
    import json
    import subprocess

    from app.core.config import ROOT_DIR

    python_exe = ROOT_DIR / "backend" / ".venv-whisper" / "Scripts" / "python.exe"
    script = ROOT_DIR / "backend" / "scripts" / "haar_faces.py"
    if not frames or not python_exe.is_file() or not script.is_file():
        return []
    try:
        completed = subprocess.run(
            [str(python_exe), str(script), *[str(path) for path in frames]],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except Exception:
        logger.debug("Haar sidecar failed", exc_info=True)
        return []
    if completed.returncode != 0:
        logger.info("Haar sidecar exit %s: %s", completed.returncode, (completed.stderr or "")[:300])
        return []
    try:
        raw = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return []
    hits: list[tuple[float, float, int, int]] = []
    for row in raw:
        try:
            hits.append((float(row["cx"]), float(row["cy"]), int(row["width"]), int(row["height"])))
        except (KeyError, TypeError, ValueError):
            continue
    return hits


def detect_reframe_crop(source: Path, start: float, end: float) -> tuple[int, int, int, int] | None:
    """Return crop w,h,x,y in source pixels, or None to use the default scale-then-center crop."""
    try:
        info = probe_video(source)
        width = int(info.get("width") or 0)
        height = int(info.get("height") or 0)
    except Exception:
        return None
    if width < 4 or height < 4:
        return None
    with tempfile.TemporaryDirectory(prefix="vc-reframe-") as raw:
        frames = _extract_sample_frames(source, start, end, Path(raw))
        hits = _face_centers(frames)
    if not hits:
        logger.info("Auto-reframe found no faces; using center crop")
        return center_window(width, height)
    cx = sum(hit[0] for hit in hits) / len(hits)
    cy = sum(hit[1] for hit in hits) / len(hits)
    sample_w = hits[0][2]
    sample_h = hits[0][3]
    if sample_w != width or sample_h != height:
        cx *= width / sample_w
        cy *= height / sample_h
    crop = nine_sixteen_window(width, height, cx, cy)
    logger.info("Auto-reframe crop=%sx%s+%s+%s from %sx%s", *crop, width, height)
    return crop


def vertical_vf(crop: tuple[int, int, int, int] | None) -> str:
    from app.services.video.layout import vertical_canvas_vf

    return vertical_canvas_vf(crop)
