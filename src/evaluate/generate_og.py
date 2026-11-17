"""Generate the single Open Graph raster image (1200x630 PNG, <= 100 KB) using stdlib only."""

from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

WIDTH = 1200
HEIGHT = 630

# Palette (indexed PNG, 8 colors)
PALETTE = [
    (246, 240, 228),  # 0: sand (#F6F0E4)
    (237, 227, 208),  # 1: sand-2 (#EDE3D0)
    (30, 27, 22),     # 2: ink (#1E1B16)
    (227, 168, 31),   # 3: maize (#E3A81F)
    (181, 71, 31),    # 4: laterite (#B5471F)
    (47, 93, 58),     # 5: green (#2F5D3A)
    (217, 205, 184),  # 6: line (#D9CDB8)
    (111, 102, 90),   # 7: muted (#6F665A)
]


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack("!I", len(data))
        + tag
        + data
        + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _draw_rect(buf: bytearray, x0: int, y0: int, w: int, h: int, color: int) -> None:
    x1 = min(WIDTH, x0 + w)
    y1 = min(HEIGHT, y0 + h)
    x0 = max(0, x0)
    y0 = max(0, y0)
    for y in range(y0, y1):
        row = y * WIDTH
        buf[row + x0 : row + x1] = bytes([color]) * (x1 - x0)


def _draw_line(buf: bytearray, x0: int, y0: int, x1: int, y1: int, thickness: int, color: int) -> None:
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    r = thickness // 2
    for i in range(steps + 1):
        cx = int(round(x0 + (x1 - x0) * i / steps))
        cy = int(round(y0 + (y1 - y0) * i / steps))
        _draw_rect(buf, cx - r, cy - r, thickness, thickness, color)


def generate_og_image(out_path: Path) -> int:
    buf = bytearray([0] * (WIDTH * HEIGHT))

    # Outer editorial border
    _draw_rect(buf, 0, 0, WIDTH, 10, 2)
    _draw_rect(buf, 48, 48, WIDTH - 96, HEIGHT - 96, 1)
    _draw_rect(buf, 50, 50, WIDTH - 100, HEIGHT - 100, 0)

    # Three-product emblem bars (Maize, Tomato, Yam) top-left
    _draw_rect(buf, 88, 96, 20, 64, 3)
    _draw_rect(buf, 118, 96, 20, 64, 4)
    _draw_rect(buf, 148, 96, 20, 64, 5)

    # Thin horizontal divider
    _draw_rect(buf, 88, 196, WIDTH - 176, 2, 6)

    # Stylized price history + 3-month forecast band in lower panel
    chart_x0, chart_y0, chart_w, chart_h = 88, 240, WIDTH - 176, 280
    _draw_rect(buf, chart_x0, chart_y0, chart_w, chart_h, 1)
    for gy in range(chart_y0 + 56, chart_y0 + chart_h, 56):
        _draw_rect(buf, chart_x0, gy, chart_w, 1, 6)

    # Shaded forecast region (right 22%)
    fc_x = chart_x0 + int(chart_w * 0.78)
    _draw_rect(buf, fc_x, chart_y0 + 36, chart_w - int(chart_w * 0.78), chart_h - 72, 6)
    _draw_rect(buf, fc_x, chart_y0, 2, chart_h, 7)

    # Three product trajectories
    pts_maize = [(88, 440), (220, 405), (360, 425), (500, 355), (650, 375), (800, 340), (fc_x, 360)]
    pts_yam = [(88, 465), (220, 430), (360, 395), (500, 420), (650, 345), (800, 315), (fc_x, 325)]
    pts_tomato = [(88, 390), (220, 320), (360, 455), (500, 290), (650, 430), (800, 280), (fc_x, 395)]

    for pts, color in [(pts_yam, 5), (pts_tomato, 4), (pts_maize, 3)]:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            _draw_line(buf, x0, y0, x1, y1, 6, color)
        # Forecast extension
        lx, ly = pts[-1]
        _draw_line(buf, lx, ly, chart_x0 + chart_w - 18, ly - 18, 4, color)
        _draw_rect(buf, chart_x0 + chart_w - 24, ly - 24, 12, 12, color)

    # Encode indexed PNG
    raw_rows = bytearray()
    for y in range(HEIGHT):
        raw_rows.append(0)  # filter type 0
        raw_rows.extend(buf[y * WIDTH : (y + 1) * WIDTH])

    ihdr = struct.pack("!IIBBBBB", WIDTH, HEIGHT, 8, 3, 0, 0, 0)
    plte = b"".join(bytes(rgb) for rgb in PALETTE)
    idat = zlib.compress(bytes(raw_rows), level=9)

    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"PLTE", plte)
        + _chunk(b"IDAT", idat)
        + _chunk(b"IEND", b"")
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(png_bytes)
    return len(png_bytes)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out_path = repo_root / "web" / "public" / "og-image.png"
    size = generate_og_image(out_path)
    print(f"[OG Image] Wrote {out_path} ({size} bytes / {size / 1024:.2f} KiB)")
    if size > 100 * 1024:
        raise SystemExit(f"OG image exceeds 100 KB limit: {size} bytes")


if __name__ == "__main__":
    main()
