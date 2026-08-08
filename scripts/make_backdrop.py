#!/usr/bin/env python3
"""
Generate an original "festival night" backdrop for the Thank You motion video.

Evokes a main-stage-at-night look (stage glow, fanned light beams, lasers,
bokeh, crowd silhouette) with pure procedural art — no copyrighted photos —
so it works offline and carries no image-rights baggage.

Output: assets/bg/festival-night.png  (picked up automatically by
thank_you_motion_v2.py's find_backdrop()).

To use a real trip photo instead, just drop a .jpg/.png in assets/bg/ and it
takes precedence by filename order — or delete this one.
"""

from __future__ import annotations

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BW, BH = 1300, 2300  # oversized so the video's Ken Burns pan has headroom
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "bg", "festival-night.png")

PALETTE = [
    (0, 190, 210), (215, 45, 165), (245, 185, 55),
    (70, 205, 150), (150, 85, 225), (60, 140, 235),
]


def vgradient() -> np.ndarray:
    top = np.array([10, 9, 34], float)
    mid = np.array([30, 20, 62], float)
    glow = np.array([70, 40, 92], float)     # warm horizon behind the stage
    foot = np.array([5, 5, 14], float)
    col = np.zeros((BH, 3), float)
    for y in range(BH):
        t = y / BH
        if t < 0.55:
            k = t / 0.55
            col[y] = top * (1 - k) + mid * k
        elif t < 0.72:
            k = (t - 0.55) / 0.17
            col[y] = mid * (1 - k) + glow * k
        else:
            k = (t - 0.72) / 0.28
            col[y] = glow * (1 - k) + foot * k
    return np.repeat(col[:, None, :], BW, axis=1)


def draw_beams() -> np.ndarray:
    img = Image.new("RGB", (BW, BH), (0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, oy = BW // 2, int(BH * 0.66)
    length = BH * 0.9
    for i, k in enumerate(range(-5, 6)):
        ang = math.radians(k * 10)
        far = (cx + length * math.sin(ang), oy - length * math.cos(ang))
        half = 30
        perp = (math.cos(ang), math.sin(ang))
        poly = [
            (cx - 5 * perp[0], oy - 5 * perp[1]),
            (cx + 5 * perp[0], oy + 5 * perp[1]),
            (far[0] + half * perp[0], far[1] + half * perp[1]),
            (far[0] - half * perp[0], far[1] - half * perp[1]),
        ]
        c = PALETTE[i % len(PALETTE)]
        d.polygon(poly, fill=tuple(int(v * 0.5) for v in c))
    img = img.filter(ImageFilter.GaussianBlur(9))
    return np.asarray(img, float)


def draw_glow() -> np.ndarray:
    img = Image.new("RGB", (BW, BH), (0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = BW // 2, int(BH * 0.66)
    for r, col in ((360, (90, 45, 70)), (230, (150, 80, 90)), (130, (210, 150, 90))):
        d.ellipse([cx - r, cy - r * 0.7, cx + r, cy + r * 0.7], fill=col)
    # stage arch silhouette
    d.rounded_rectangle([cx - 300, cy - 60, cx + 300, cy + 220], radius=140,
                        outline=(20, 14, 30), width=70)
    img = img.filter(ImageFilter.GaussianBlur(40))
    return np.asarray(img, float)


def draw_bokeh() -> np.ndarray:
    img = Image.new("RGB", (BW, BH), (0, 0, 0))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(11)
    for _ in range(160):
        x = float(rng.integers(0, BW))
        y = float(rng.integers(int(BH * 0.15), int(BH * 0.9)))
        r = float(rng.integers(3, 14))
        c = PALETTE[int(rng.integers(0, len(PALETTE)))]
        f = float(rng.uniform(0.25, 0.75))
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(v * f) for v in c))
    img = img.filter(ImageFilter.GaussianBlur(3))
    return np.asarray(img, float)


def draw_lasers() -> np.ndarray:
    img = Image.new("RGB", (BW, BH), (0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, oy = BW // 2, int(BH * 0.64)
    rng = np.random.default_rng(5)
    for i in range(14):
        ang = math.radians(rng.uniform(-80, 80))
        far = (cx + BH * math.sin(ang), oy - BH * math.cos(ang))
        c = PALETTE[i % len(PALETTE)]
        d.line([(cx, oy), far], fill=tuple(int(v * 0.55) for v in c), width=2)
    img = img.filter(ImageFilter.GaussianBlur(1.5))
    return np.asarray(img, float)


def crowd(arr: np.ndarray) -> np.ndarray:
    img = Image.new("L", (BW, BH), 0)
    d = ImageDraw.Draw(img)
    base = int(BH * 0.9)
    rng = np.random.default_rng(3)
    d.rectangle([0, base, BW, BH], fill=255)
    for x in range(0, BW, 9):
        h = int(rng.integers(10, 70))
        d.rectangle([x, base - h, x + 7, base], fill=255)
    # a few raised arms
    for _ in range(60):
        x = int(rng.integers(0, BW))
        h = int(rng.integers(30, 90))
        d.line([(x, base), (x, base - h)], fill=255, width=3)
    mask = (np.asarray(img, float) / 255.0)[:, :, None]
    dark = np.array([4, 4, 10], float)
    return arr * (1 - mask) + dark * mask


def vignette(arr: np.ndarray) -> np.ndarray:
    yy, xx = np.mgrid[0:BH, 0:BW]
    cx, cy = BW / 2, BH * 0.55
    d = np.sqrt(((xx - cx) / (BW * 0.75)) ** 2 + ((yy - cy) / (BH * 0.7)) ** 2)
    v = np.clip(1.0 - 0.55 * np.clip(d - 0.2, 0, 1), 0.45, 1.0)
    return arr * v[:, :, None]


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    base = vgradient()
    base = base + draw_glow() + draw_beams() * 0.9 + draw_lasers() * 0.8 \
        + draw_bokeh() * 0.85
    base = crowd(base)
    base = vignette(base)
    out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    out.save(OUT)
    print(f"Saved backdrop -> {OUT}  ({out.size[0]}x{out.size[1]})")


if __name__ == "__main__":
    main()
