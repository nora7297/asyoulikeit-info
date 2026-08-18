#!/usr/bin/env python3
"""
Render the full deliverable set:
  - thank-you-mix-1.mp4 / mix-2.mp4  (the two 9:16 story mixes)
  - thank-you-combined.mp4           (everyone, 9:16)
  - thank-you-combined-square.mp4    (1:1, phone on a blurred festival backdrop)
  - thank-you-combined-wide.mp4      (16:9, same treatment)

All carry sound effects (no music). Run:
    python3 scripts/render_all.py
"""

from __future__ import annotations

import os
import subprocess

import imageio_ffmpeg
from PIL import Image, ImageEnhance, ImageFilter

import thank_you_motion as v1
import thank_you_motion_split as split
import thank_you_motion_v2 as v2

ASSET = v2.ASSET_DIR
PHOTO = os.path.join(ASSET, "bg", "tomorrowland-mainstage.jpg")


def blurred_bg(w, h, out):
    im = Image.open(PHOTO).convert("RGB")
    scale = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    im = im.crop((x, y, x + w, y + h)).filter(ImageFilter.GaussianBlur(45))
    ImageEnhance.Brightness(im).enhance(0.45).save(out)
    return out


def reformat(src, out, w, h):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    bg = blurred_bg(w, h, src.replace(".mp4", f".bg{w}x{h}.png"))
    subprocess.run([
        ff, "-y", "-loglevel", "error", "-loop", "1", "-i", bg, "-i", src,
        "-filter_complex",
        f"[1:v]scale=-2:{h}[fg];[0:v][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,"
        f"format=yuv420p[v]",
        "-map", "[v]", "-map", "1:a:0",
        "-c:v", "libx264", "-crf", "20", "-preset", "medium",
        "-c:a", "copy", "-shortest", "-movflags", "+faststart", out,
    ], check=True)
    os.remove(bg)
    print(f"Reformatted -> {out} ({os.path.getsize(out) / 1e6:.1f} MB)")


def main():
    split.main()                                   # mix-1, mix-2 (9:16)

    combined = os.path.join(ASSET, "thank-you-combined.mp4")
    print("\n=== Combined (everyone) ===")
    v2.render(v1.MESSAGES, combined, combined.replace(".mp4", "-poster.png"))
    reformat(combined, os.path.join(ASSET, "thank-you-combined-square.mp4"), 1080, 1080)
    reformat(combined, os.path.join(ASSET, "thank-you-combined-wide.mp4"), 1920, 1080)


if __name__ == "__main__":
    main()
