"""CPU Haar face centers. Run with CPython 3.12 (opencv wheels; not the 3.13t app venv)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2  # type: ignore


def centers(paths: list[Path]) -> list[dict[str, float | int]]:
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        return []
    hits: list[dict[str, float | int]] = []
    for frame_path in paths:
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
        hits.append(
            {
                "cx": (x + w / 2) / scale,
                "cy": (y + h / 2) / scale,
                "width": width,
                "height": height,
            }
        )
    return hits


if __name__ == "__main__":
    print(json.dumps(centers([Path(p) for p in sys.argv[1:]])))
