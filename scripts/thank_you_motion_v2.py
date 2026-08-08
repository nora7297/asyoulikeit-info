#!/usr/bin/env python3
"""
As You Like IT — Thank You motion collage, v2 ("punchy" edition).

A beat-driven, kinetic "chat replay": thank-you bubbles pop in on the beat and
the feed scrolls up like a live WhatsApp conversation, with an animated intro
title and outro card. 1080x1920 story format.

What's new vs v1 (thank_you_motion.py)
--------------------------------------
- Chat-replay motion: newest message pops in near the bottom and pushes the
  stack up, instead of a single slow credits roll.
- Beat-synced entrances (set BPM) with an ease-out-back "pop" (scale + fade).
- Snappier: ~25-32s depending on BPM.
- Optional festival photo backdrop (drop images in assets/bg/) with a slow
  Ken Burns drift + dark scrim so text stays legible.
- Optional avatars: drop <label>.png|jpg in assets/avatars/ (label = the
  sender name) and they render as circular badges beside each bubble.
- Optional music: drop a track in assets/audio/ and it is muxed + trimmed to
  the video length (needs ffmpeg, which imageio-ffmpeg provides).

These asset folders are all optional — with none present it renders a
self-contained, silent, gradient-backed version so the pacing can be reviewed
before the real screenshots / photos / track arrive.

Run:
    python3 scripts/thank_you_motion_v2.py
"""

from __future__ import annotations

import glob
import os
import subprocess

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import thank_you_motion as v1  # shared bubbles / emoji / fonts / data

# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #

W, H, FPS = v1.W, v1.H, v1.FPS

BPM = 112                       # tempo the entrances snap to
INTRO_SEC = 2.0                 # animated title hold
OUTRO_SEC = 3.0                 # animated outro hold
TAIL_SEC = 0.8                  # settle time after last message enters

D_POP = 0.34                    # per-bubble pop-in duration (s)
D_SCROLL = 0.42                 # feed scroll-settle duration (s)

Y_TARGET = int(H * 0.80)        # where a new bubble's bottom lands
Y_TOP_MIN = 210                 # keep tall bubbles' tops below the header

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(ROOT, "assets")
BG_DIR = os.path.join(ASSET_DIR, "bg")
AVATAR_DIR = os.path.join(ASSET_DIR, "avatars")
AUDIO_DIR = os.path.join(ASSET_DIR, "audio")

OUT_MP4 = os.path.join(ASSET_DIR, "thank-you-motion-v2.mp4")
OUT_POSTER = os.path.join(ASSET_DIR, "thank-you-motion-v2-poster.png")

BEAT = 60.0 / BPM

# --------------------------------------------------------------------------- #
# Easing                                                                       #
# --------------------------------------------------------------------------- #

def ease_out_cubic(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3


def ease_out_back(p: float) -> float:
    p = min(1.0, max(0.0, p))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2


# --------------------------------------------------------------------------- #
# Optional assets                                                              #
# --------------------------------------------------------------------------- #

def find_backdrop() -> Image.Image | None:
    files = sorted(
        glob.glob(os.path.join(BG_DIR, "*.jp*g"))
        + glob.glob(os.path.join(BG_DIR, "*.png")))
    if not files:
        return None
    im = Image.open(files[0]).convert("RGB")
    # Cover-fit to a slightly oversized canvas so we can Ken Burns pan it.
    scale = max((W * 1.12) / im.width, (H * 1.12) / im.height)
    im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    return im


def find_audio() -> str | None:
    files = sorted(
        glob.glob(os.path.join(AUDIO_DIR, "*.mp3"))
        + glob.glob(os.path.join(AUDIO_DIR, "*.m4a"))
        + glob.glob(os.path.join(AUDIO_DIR, "*.wav"))
        + glob.glob(os.path.join(AUDIO_DIR, "*.aac")))
    return files[0] if files else None


def load_avatar(label: str, size: int) -> Image.Image | None:
    if not os.path.isdir(AVATAR_DIR):
        return None
    key = label.lstrip("~").strip().lower()
    for f in glob.glob(os.path.join(AVATAR_DIR, "*")):
        stem = os.path.splitext(os.path.basename(f))[0].lower()
        if stem == key or stem in key or key in stem:
            try:
                im = Image.open(f).convert("RGB")
            except Exception:
                return None
            s = min(im.size)
            im = im.crop(((im.width - s) // 2, (im.height - s) // 2,
                          (im.width - s) // 2 + s, (im.height - s) // 2 + s))
            im = im.resize((size, size), Image.LANCZOS).convert("RGBA")
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
            im.putalpha(mask)
            return im
    return None


# --------------------------------------------------------------------------- #
# Cards                                                                        #
# --------------------------------------------------------------------------- #

def build_cards():
    """Return list of (rgba_card, entry_beat, hold_beats) plus title/outro."""
    cards = []
    beat_cursor = 0
    for i, (name, text) in enumerate(v1.MESSAGES):
        card = v1.make_bubble(name, text, v1.ACCENTS[i % len(v1.ACCENTS)])
        avatar = load_avatar(name, 84)
        if avatar is not None:
            card = attach_avatar(card, avatar)
        L = len(text)
        hold = 1 if L < 45 else (2 if L < 135 else 3)
        cards.append({"img": card, "entry_beat": beat_cursor, "hold": hold})
        beat_cursor += hold
    return cards, beat_cursor


def attach_avatar(card: Image.Image, avatar: Image.Image) -> Image.Image:
    """Widen the card canvas and place a circular avatar to the left tail."""
    gap = 14
    extra = avatar.width + gap
    out = Image.new("RGBA", (card.width + extra, card.height), (0, 0, 0, 0))
    out.paste(card, (extra, 0), card)
    ring = Image.new("RGBA", (avatar.width + 6, avatar.height + 6), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([0, 0, avatar.width + 5, avatar.height + 5],
                                 fill=(255, 255, 255, 235))
    out.paste(ring, (0, 30), ring)
    out.paste(avatar, (3, 33), avatar)
    return out


# --------------------------------------------------------------------------- #
# Image transforms                                                             #
# --------------------------------------------------------------------------- #

def scaled(card: Image.Image, s: float) -> Image.Image:
    if abs(s - 1.0) < 1e-3:
        return card
    return card.resize((max(1, round(card.width * s)),
                        max(1, round(card.height * s))), Image.LANCZOS)


def with_alpha(card: Image.Image, a: float) -> Image.Image:
    if a >= 0.999:
        return card
    r = card.copy()
    r.putalpha(r.getchannel("A").point(lambda p: int(p * a)))
    return r


# --------------------------------------------------------------------------- #
# Backgrounds / overlays                                                       #
# --------------------------------------------------------------------------- #

GRADIENT_BG = None
BACKDROP = None
SCRIM = None
CHROME = None
EDGE = None


def bg_frame(t: float, total: float) -> Image.Image:
    if BACKDROP is None:
        return GRADIENT_BG.copy()
    # Slow Ken Burns: pan diagonally across the oversized backdrop.
    prog = t / max(1e-6, total)
    max_dx = BACKDROP.width - W
    max_dy = BACKDROP.height - H
    dx = int(max_dx * (0.15 + 0.7 * prog))
    dy = int(max_dy * (0.10 + 0.5 * prog))
    frame = BACKDROP.crop((dx, dy, dx + W, dy + H)).copy()
    frame.paste(SCRIM, (0, 0), SCRIM)
    return frame


def make_scrim() -> Image.Image:
    """Dark vertical scrim so bubbles stay legible over a photo."""
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    for y in range(H):
        a = int(150 + 60 * (y / H))          # 150 -> 210 top to bottom
        arr[y, :, 3] = a
    scrim = Image.fromarray(arr, "RGBA")
    tealed = Image.new("RGBA", (W, H), (7, 40, 37, 0))
    tealed.putalpha(scrim.getchannel("A"))
    return tealed


# --------------------------------------------------------------------------- #
# Intro / outro                                                                #
# --------------------------------------------------------------------------- #

def draw_intro(base: Image.Image, p: float) -> Image.Image:
    frame = base.copy()
    title = v1.make_title_card()
    e = ease_out_back(min(1.0, p / 0.6))
    a = min(1.0, p / 0.4)
    card = with_alpha(scaled(title, 0.8 + 0.2 * e), a)
    x = (W - card.width) // 2
    y = (H - card.height) // 2 - 40 + int((1 - ease_out_cubic(min(1, p / 0.6))) * 40)
    frame.paste(card, (x, y), card)
    return frame


def draw_outro(base: Image.Image, p: float) -> Image.Image:
    frame = base.copy()
    outro = v1.make_outro_card()
    e = ease_out_back(min(1.0, p / 0.6))
    a = min(1.0, p / 0.4)
    card = with_alpha(scaled(outro, 0.82 + 0.18 * e), a)
    x = (W - card.width) // 2
    y = (H - card.height) // 2 - 20
    frame.paste(card, (x, y), card)
    return frame


# --------------------------------------------------------------------------- #
# Chat-replay geometry                                                         #
# --------------------------------------------------------------------------- #

def main():
    global GRADIENT_BG, BACKDROP, SCRIM, CHROME, EDGE
    GRADIENT_BG = v1.make_background().convert("RGB")
    BACKDROP = find_backdrop()
    SCRIM = make_scrim() if BACKDROP is not None else None
    CHROME = v1.make_chrome()
    EDGE = v1.make_edge_mask()

    cards, total_beats = build_cards()
    gap = v1.BUBBLE_GAP
    x_left = v1.SIDE_MARGIN - 18

    # Absolute stacked positions of each bubble on a virtual strip.
    tops, bottoms = [], []
    y = 0
    for c in cards:
        tops.append(y)
        y += c["img"].height
        bottoms.append(y)
        y += gap

    # Scroll value once bubble i has settled: its bottom sits at Y_TARGET,
    # but a tall bubble instead pins its top to Y_TOP_MIN so it stays visible.
    scroll_at = []
    for i, c in enumerate(cards):
        s = bottoms[i] - Y_TARGET
        if tops[i] - s < Y_TOP_MIN:
            s = tops[i] - Y_TOP_MIN
        scroll_at.append(max(0, s))

    # Timeline (seconds).
    t0 = INTRO_SEC
    entry_time = [t0 + c["entry_beat"] * BEAT for c in cards]
    chat_end = entry_time[-1] + cards[-1]["hold"] * BEAT + TAIL_SEC
    total = chat_end + OUTRO_SEC
    total_frames = int(total * FPS)

    print(f"BPM {BPM} | {len(cards)} messages over {total_beats} beats "
          f"| backdrop={'yes' if BACKDROP else 'no'} "
          f"| avatars={'some' if os.path.isdir(AVATAR_DIR) else 'none'}")
    print(f"Duration ~{total:.1f}s ({total_frames} frames)")

    def scroll(t: float) -> float:
        # Before the first entry, hold so bubble 0 slides up from below.
        if t <= entry_time[0]:
            return scroll_at[0] - (cards[0]["img"].height + gap)
        s = scroll_at[0]
        for i in range(len(cards)):
            if t >= entry_time[i]:
                prev = scroll_at[i - 1] if i > 0 else \
                    scroll_at[0] - (cards[0]["img"].height + gap)
                p = ease_out_cubic((t - entry_time[i]) / D_SCROLL)
                s = prev + (scroll_at[i] - prev) * p
            else:
                break
        return s

    def compose(t: float) -> Image.Image:
        # Intro / outro phases.
        if t < INTRO_SEC:
            return draw_intro(bg_frame(0, total), t / INTRO_SEC).convert("RGB")
        if t >= chat_end:
            return draw_outro(bg_frame(t, total),
                              (t - chat_end) / OUTRO_SEC).convert("RGB")

        frame = bg_frame(t, total)
        sc = scroll(t)
        # Composite the strip region with soft top/bottom edge fades.
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        n_entered = sum(1 for et in entry_time if t >= et)
        for i in range(n_entered):
            base_y = int(tops[i] - sc)
            if base_y > H or base_y + cards[i]["img"].height < 0:
                continue
            img = cards[i]["img"]
            # Pop only the most-recent entrant.
            if i == n_entered - 1:
                pp = (t - entry_time[i]) / D_POP
                if pp < 1.0:
                    s = 0.82 + 0.18 * ease_out_back(pp)
                    img = with_alpha(scaled(img, s), min(1.0, pp * 1.6))
                    dx = (img.width - cards[i]["img"].width) // 2
                    dy = (img.height - cards[i]["img"].height) // 2
                    layer.paste(img, (x_left - dx, base_y - dy), img)
                    continue
            layer.paste(img, (x_left, base_y), img)

        alpha = ImageChops.multiply(layer.getchannel("A"), EDGE)
        layer.putalpha(alpha)
        frame.paste(layer, (0, 0), layer)
        frame.paste(CHROME, (0, 0), CHROME)
        return frame.convert("RGB")

    # Poster: a lively mid-chat frame.
    compose(entry_time[min(3, len(cards) - 1)] + 0.2).save(OUT_POSTER)
    print(f"Saved poster -> {OUT_POSTER}")

    tmp_mp4 = OUT_MP4 if find_audio() is None else OUT_MP4.replace(".mp4", ".silent.mp4")
    writer = imageio.get_writer(
        tmp_mp4, fps=FPS, codec="libx264", macro_block_size=8,
        ffmpeg_params=["-crf", "20", "-preset", "medium",
                       "-pix_fmt", "yuv420p", "-movflags", "+faststart"])
    try:
        for f in range(total_frames):
            writer.append_data(np.asarray(compose(f / FPS)))
            if f % 60 == 0:
                print(f"  frame {f}/{total_frames}")
    finally:
        writer.close()

    audio = find_audio()
    if audio:
        mux_audio(tmp_mp4, audio, OUT_MP4, total)
        os.remove(tmp_mp4)
        print(f"Muxed audio from {os.path.basename(audio)}")
    size_mb = os.path.getsize(OUT_MP4) / 1e6
    print(f"Saved video -> {OUT_MP4} ({size_mb:.1f} MB)")


def mux_audio(video: str, audio: str, out: str, dur: float):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([
        ff, "-y", "-loglevel", "error",
        "-i", video, "-i", audio,
        "-map", "0:v:0", "-map", "1:a:0",
        "-t", f"{dur:.3f}",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-af", "afade=t=out:st=%.2f:d=1.2" % max(0, dur - 1.2),
        "-shortest", "-movflags", "+faststart", out,
    ], check=True)


if __name__ == "__main__":
    main()
