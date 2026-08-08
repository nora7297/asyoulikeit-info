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

BPM = 124                       # tempo the entrances snap to (matches the track)
INTRO_BEATS = 8                 # 2-bar intro so the first bubble hits the drop
OUTRO_SEC = 3.4                 # animated outro hold
TAIL_SEC = 1.0                  # settle time after last message enters

D_POP = 0.34                    # per-bubble pop-in duration (s)
D_SCROLL = 0.42                 # feed scroll-settle duration (s)

Y_TARGET = 1760                 # newest bubble's bottom sits just above input bar
Y_TOP_MIN = 200                 # keep tall bubbles' tops below the chat header

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(ROOT, "assets")
BG_DIR = os.path.join(ASSET_DIR, "bg")
AVATAR_DIR = os.path.join(ASSET_DIR, "avatars")
AUDIO_DIR = os.path.join(ASSET_DIR, "audio")

OUT_MP4 = os.path.join(ASSET_DIR, "thank-you-motion-v2.mp4")
OUT_POSTER = os.path.join(ASSET_DIR, "thank-you-motion-v2-poster.png")

BEAT = 60.0 / BPM
INTRO_SEC = INTRO_BEATS * BEAT   # keep the title hold an exact number of beats

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

def build_cards(messages):
    """Return list of card dicts (image, entry_beat, hold_beats)."""
    cards = []
    beat_cursor = 0
    for i, (name, text) in enumerate(messages):
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

# WhatsApp-group scene: beige doodle wallpaper, green header bar with the
# group's details, and a message input bar along the bottom.

WA_HEADER_H = 158
WA_INPUT_H = 122
WA_GREEN = (7, 94, 84)               # #075E54 header
GROUP_NAME = "As You Like It · TML 2026"
HOST_QUESTION = "How did everyone find Tomorrowland this year?? 🙌💚"

LOGO_PATH = os.path.join(ASSET_DIR, "logo-white.png")
_font_hdr = ImageFont.truetype(v1.DEJAVU_BOLD, 33)
_font_sub = ImageFont.truetype(v1.DEJAVU, 23)
_font_input = ImageFont.truetype(v1.DEJAVU, 30)

WALLPAPER = None
HEADER = None
INPUTBAR = None

DOODLES = ["🎵", "❤️", "🎉", "✈️", "☕", "🎈", "🦋", "🌈", "🎧", "⭐", "🍺", "🙌"]


def make_wallpaper() -> Image.Image:
    """WhatsApp beige doodle wallpaper (faint tinted emoji stamps)."""
    base = Image.new("RGBA", (W, H), (231, 223, 213, 255))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rng = np.random.default_rng(42)
    step = 165
    for gy in range(-1, H // step + 2):
        for gx in range(-1, W // step + 2):
            cx = gx * step + (0 if gy % 2 == 0 else step // 2) + int(rng.integers(-18, 18))
            cy = gy * step + int(rng.integers(-18, 18))
            glyph = v1.render_emoji(DOODLES[int(rng.integers(0, len(DOODLES)))], 92)
            if glyph is None:
                continue
            a = glyph.getchannel("A").point(lambda p: int(p * 0.09))
            tint = Image.new("RGBA", glyph.size, (95, 85, 70, 0))
            tint.putalpha(a)
            tint = tint.rotate(float(rng.integers(-35, 35)), expand=True,
                               resample=Image.BICUBIC)
            layer.alpha_composite(tint, (cx, cy))
    return Image.alpha_composite(base, layer).convert("RGB")


def _fit_circle(img, d, bg):
    circ = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    ImageDraw.Draw(circ).ellipse([0, 0, d - 1, d - 1], fill=bg)
    lw = int(d * 0.72)
    logo = img.copy()
    logo.thumbnail((lw, lw), Image.LANCZOS)
    circ.alpha_composite(logo, ((d - logo.width) // 2, (d - logo.height) // 2))
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d - 1, d - 1], fill=255)
    circ.putalpha(mask)
    return circ


def make_header() -> Image.Image:
    h = Image.new("RGBA", (W, WA_HEADER_H), WA_GREEN + (255,))
    d = ImageDraw.Draw(h)
    cy = WA_HEADER_H // 2 + 10
    # Back chevron.
    d.line([(56, cy - 17), (36, cy), (56, cy + 17)], fill=(255, 255, 255), width=6)
    # Group avatar (logo on a dark disc).
    av = 96
    ax, ay = 80, cy - av // 2
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        h.alpha_composite(_fit_circle(logo, av, (4, 60, 54, 255)), (ax, ay))
    except Exception:
        ImageDraw.Draw(h).ellipse([ax, ay, ax + av, ay + av], fill=(4, 60, 54))
    # Name + member subtitle.
    tx = ax + av + 22
    d.text((tx, cy - 36), GROUP_NAME, font=_font_hdr, fill=(255, 255, 255))
    names = [n for n, _ in v1.MESSAGES]
    sub = "You, " + ", ".join(names[:5]) + f", +{max(0, len(names) - 5)}"
    d.text((tx, cy + 6), sub, font=_font_sub, fill=(200, 230, 224))
    # Right icons: video camera + overflow menu.
    vx, vy = W - 150, cy
    d.rounded_rectangle([vx, vy - 15, vx + 42, vy + 15], radius=8,
                        outline=(255, 255, 255), width=5)
    d.polygon([(vx + 46, vy - 12), (vx + 64, vy - 2), (vx + 64, vy + 2),
               (vx + 46, vy + 12)], fill=(255, 255, 255))
    for k in range(3):                                    # overflow dots
        d.ellipse([W - 44, cy - 26 + k * 22, W - 34, cy - 16 + k * 22],
                  fill=(255, 255, 255))
    return h


def make_inputbar(content=None, cursor=False) -> Image.Image:
    """Bottom input bar. content=None shows the 'Message' placeholder + mic;
    an RGBA `content` image (typed text) shows it in the field + a send button."""
    b = Image.new("RGBA", (W, WA_INPUT_H), (236, 229, 221, 255))
    d = ImageDraw.Draw(b)
    cy = WA_INPUT_H // 2
    d.rounded_rectangle([24, 18, W - 140, WA_INPUT_H - 18], radius=(WA_INPUT_H - 36) // 2,
                        fill=(255, 255, 255))
    smiley = v1.render_emoji("🙂", 44)
    if smiley is not None:
        b.alpha_composite(smiley, (48, cy - 22))

    fx0, fx1 = 110, W - 156
    if content is None:
        d.text((fx0, cy - 18), "Message", font=_font_input, fill=(150, 150, 150))
        curx = fx0
    else:
        oy = cy - content.height // 2
        fw = fx1 - fx0
        if content.width <= fw:
            b.alpha_composite(content, (fx0, oy))
            curx = fx0 + content.width + 4
        else:                                   # show the tail, like a real field
            b.alpha_composite(content.crop((content.width - fw, 0,
                                            content.width, content.height)), (fx0, oy))
            curx = fx0 + fw + 4
    if cursor:
        d.line([(curx, cy - 22), (curx, cy + 22)], fill=(90, 90, 90), width=3)

    # Button: send arrow while composing, otherwise mic.
    bx = W - 74
    d.ellipse([bx - 44, cy - 44, bx + 44, cy + 44], fill=WA_GREEN)
    if content is not None:                     # paper-plane send glyph
        d.polygon([(bx - 20, cy - 16), (bx + 22, cy), (bx - 20, cy + 16),
                   (bx - 12, cy), ], fill=(255, 255, 255))
        d.polygon([(bx - 20, cy + 16), (bx - 12, cy), (bx + 4, cy)],
                  fill=(210, 240, 225))
    else:                                       # mic glyph
        d.rounded_rectangle([bx - 9, cy - 24, bx + 9, cy + 6], radius=9, fill=(255, 255, 255))
        d.arc([bx - 18, cy - 12, bx + 18, cy + 20], 20, 160, fill=(255, 255, 255), width=4)
        d.line([(bx, cy + 20), (bx, cy + 30)], fill=(255, 255, 255), width=4)
        d.line([(bx - 12, cy + 30), (bx + 12, cy + 30)], fill=(255, 255, 255), width=4)
    return b


def type_units(text):
    """Cumulative reveal states for a typewriter effect (whole emoji at once)."""
    units, cur = [], ""
    for tok in v1._tokenize(text):
        if tok[0] == "word":
            for ch in tok[1]:
                cur += ch
                units.append(cur)
        elif tok[0] == "space":
            cur += " "
            units.append(cur)
        elif tok[0] == "break":
            cur += "\n"
            units.append(cur)
        elif tok[0] == "emoji":
            cur += tok[1]
            units.append(cur)
    return units


def draw_outro(t, chat_end) -> Image.Image:
    """Fade the chat to brand teal and pop the sign-off card."""
    p = (t - chat_end) / OUTRO_SEC
    frame = WALLPAPER.convert("RGBA").copy()
    frame.alpha_composite(Image.new("RGBA", (W, H),
                                    WA_GREEN + (int(min(1.0, p / 0.35) * 255),)))
    if p > 0.12:
        e = ease_out_back(min(1.0, (p - 0.12) / 0.5))
        a = min(1.0, (p - 0.12) / 0.4)
        card = with_alpha(scaled(v1.make_outro_card(), 0.85 + 0.15 * e), a)
        frame.alpha_composite(card, ((W - card.width) // 2, (H - card.height) // 2 - 20))
    return frame.convert("RGB")


# --------------------------------------------------------------------------- #
# Chat-replay geometry                                                         #
# --------------------------------------------------------------------------- #

def render(messages, out_mp4, out_poster):
    global WALLPAPER, HEADER, INPUTBAR
    if WALLPAPER is None:
        WALLPAPER = make_wallpaper()
        HEADER = make_header()
        INPUTBAR = make_inputbar()

    gap = v1.BUBBLE_GAP
    pad = 18

    # Cards: your outgoing question first, then the incoming replies.
    cards = [{"img": v1.make_bubble("You", HOST_QUESTION, None, outgoing=True),
              "out": True, "text": HOST_QUESTION}]
    for i, (name, text) in enumerate(messages):
        cards.append({"img": v1.make_bubble(name, text, v1.ACCENTS[i % len(v1.ACCENTS)]),
                      "out": False, "text": text})

    for c in cards:                                   # horizontal placement
        w = c["img"].width
        c["x"] = (W - v1.SIDE_MARGIN + pad - w) if c["out"] else (v1.SIDE_MARGIN - pad)

    tops, bottoms = [], []                            # stacked positions
    y = 0
    for c in cards:
        tops.append(y)
        y += c["img"].height
        bottoms.append(y)
        y += gap

    # Anchor the newest bubble's bottom near the input bar (chat fills from the
    # bottom). Scroll may be negative when there are only a few messages. A
    # bubble too tall to fit pins its top under the header instead.
    scroll_at = []
    for i, c in enumerate(cards):
        s = bottoms[i] - Y_TARGET
        if tops[i] - s < Y_TOP_MIN:
            s = tops[i] - Y_TOP_MIN
        scroll_at.append(s)

    # Your question types out live in the input bar during the intro, then
    # "sends" (the bubble pops). Replies start from the drop, on the beat.
    q_units = type_units(HOST_QUESTION)
    TYPE_START, TYPE_CPS, PAUSE = 0.5, 21.0, 0.3
    send_time = min(INTRO_SEC - 0.35, TYPE_START + len(q_units) / TYPE_CPS + PAUSE)

    holds = [1 if len(c["text"]) < 45 else (2 if len(c["text"]) < 135 else 3)
             for c in cards[1:]]
    entry_time = [send_time]
    tcur = INTRO_SEC
    for h in holds:
        entry_time.append(tcur)
        tcur += h * BEAT
    chat_end = (entry_time[-1] + holds[-1] * BEAT + TAIL_SEC) if holds \
        else INTRO_SEC + TAIL_SEC
    total = chat_end + OUTRO_SEC
    total_frames = int(total * FPS)

    print(f"BPM {BPM} | {len(messages)} replies | WhatsApp theme "
          f"| duration ~{total:.1f}s ({total_frames} frames)")

    def scroll(t: float) -> float:
        first_drop = scroll_at[0] - (cards[0]["img"].height + gap)
        if t <= entry_time[0]:
            return first_drop
        s = scroll_at[0]
        for i in range(len(cards)):
            if t >= entry_time[i]:
                prev = scroll_at[i - 1] if i > 0 else first_drop
                p = ease_out_cubic((t - entry_time[i]) / D_SCROLL)
                s = prev + (scroll_at[i] - prev) * p
            else:
                break
        return s

    def compose(t: float) -> Image.Image:
        if t >= chat_end:
            return draw_outro(t, chat_end)

        frame = WALLPAPER.convert("RGBA")
        sc = scroll(t)
        n_entered = sum(1 for et in entry_time if t >= et)
        for i in range(n_entered):
            base_y = int(tops[i] - sc)
            img = cards[i]["img"]
            x = cards[i]["x"]
            if base_y > H or base_y + img.height < 0:
                continue
            if i == n_entered - 1:                    # pop the newest entrant
                pp = (t - entry_time[i]) / D_POP
                if pp < 1.0:
                    s = 0.82 + 0.18 * ease_out_back(pp)
                    im = with_alpha(scaled(img, s), min(1.0, pp * 1.6))
                    dx = (im.width - img.width) // 2
                    dy = (im.height - img.height) // 2
                    frame.alpha_composite(im, (x - dx, base_y - dy))
                    continue
            frame.alpha_composite(img, (x, base_y))

        frame.alpha_composite(HEADER, (0, 0))
        # Input bar: type the question out, then revert to the placeholder.
        if TYPE_START <= t < send_time:
            idx = max(0, min(len(q_units), int((t - TYPE_START) * TYPE_CPS)))
            typed = q_units[idx - 1] if idx > 0 else ""
            cimg = None
            if typed:
                cimg = v1.layout_rich(typed, _font_input, 4000, (70, 70, 70), 34, 40)
                bb = cimg.getbbox()                    # trim the wide empty canvas
                if bb:
                    cimg = cimg.crop((0, 0, bb[2] + 2, cimg.height))
            bar = make_inputbar(cimg, cursor=(int(t * 2) % 2 == 0))
        else:
            bar = INPUTBAR
        frame.alpha_composite(bar, (0, H - WA_INPUT_H))
        return frame.convert("RGB")

    # Poster: a lively mid-chat frame.
    compose(entry_time[min(4, len(cards) - 1)] + 0.25).save(out_poster)
    print(f"Saved poster -> {out_poster}")

    tmp_mp4 = out_mp4 if find_audio() is None else out_mp4.replace(".mp4", ".silent.mp4")
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
        mux_audio(tmp_mp4, audio, out_mp4, total)
        os.remove(tmp_mp4)
        print(f"Muxed audio from {os.path.basename(audio)}")
    size_mb = os.path.getsize(out_mp4) / 1e6
    print(f"Saved video -> {out_mp4} ({size_mb:.1f} MB)")


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
    render(v1.MESSAGES, OUT_MP4, OUT_POSTER)
