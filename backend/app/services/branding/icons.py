from __future__ import annotations

import shutil
import struct
import zlib
from pathlib import Path


ASSETS = Path(__file__).resolve().parent / "assets"

_COLORS = {
    "youtube": (255, 0, 0),
    "tiktok": (10, 241, 223),
    "instagram": (225, 48, 108),
}


def _png(width: int, height: int, rgba: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b""
    row = width * 4
    for y in range(height):
        raw += b"\x00" + rgba[y * row : (y + 1) * row]
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def _platform_png(kind: str) -> bytes:
    width = height = 64
    red, green, blue = _COLORS.get(kind, (220, 220, 220))
    pixels = bytearray()
    cx, cy, rad = 31.5, 31.5, 30
    for y in range(height):
        for x in range(width):
            dx, dy = x - cx, y - cy
            inside = dx * dx + dy * dy <= rad * rad
            shade = 18 if ((x // 3) + (y // 3)) % 2 else 0
            if inside:
                pixels.extend(
                    (
                        max(0, min(255, red - shade)),
                        max(0, min(255, green - shade)),
                        max(0, min(255, blue - shade)),
                        255,
                    )
                )
            else:
                pixels.extend((0, 0, 0, 0))
    return _png(width, height, bytes(pixels))


def write_platform_icon(platform: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    kind = (platform or "").strip().lower()
    src = ASSETS / f"{kind}.png"
    if src.is_file() and src.stat().st_size > 800:
        shutil.copy2(src, dest)
        return dest
    dest.write_bytes(_platform_png(kind))
    return dest
