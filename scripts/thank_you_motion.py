#!/usr/bin/env python3
"""
As You Like IT — Thank You motion collage.

Renders the crew's WhatsApp thank-you messages as an animated, vertically
scrolling "credits roll" in 1080x1920 story format (WhatsApp / Instagram /
TikTok friendly) and exports an MP4 plus a poster still.

Highlights
----------
- Proper text wrapping (no more clipped one-liners).
- Real colour emoji via Noto Color Emoji, including skin-tone modifiers,
  ZWJ sequences and the Scotland flag (needs Pillow built with libraqm).
- WhatsApp-style chat bubbles with per-sender accent colours.
- Smooth auto-scroll with soft top/bottom fades so cards drift in and out.
- Intro title card and outro "thank you" card baked into the roll.

Dependencies: Pillow, numpy, imageio, imageio-ffmpeg.
    pip install Pillow numpy imageio imageio-ffmpeg

Run:
    python3 scripts/thank_you_motion.py
"""

from __future__ import annotations

import os

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

# --------------------------------------------------------------------------- #
# Data                                                                        #
# --------------------------------------------------------------------------- #

# First names only; group participants not saved as contacts (the "~" names in
# WhatsApp) — saved contacts and phone numbers are intentionally left out.
MESSAGES = [
    ("Al", "Thanks all for a great time. An experience ill never forget 🙌🏿"),
    ("Emma", "Thanks Chris and Ben, you were wonderful hosts!\nGreat to meet everyone, safe travels ✈️"),
    ("Declan", "Thank you Chris and Ben for an unforgettable weekend, same time next week then 🤣 it was a pleasure meeting everyone and sharing a drink, hope youse all have safe travels home 🍺"),
    ("Char", "Thanks for an amazing weekend everyone hope the journey home isn’t to rough was so nice to meet everyone safe trip home ❤️🌈"),
    ("Stephen", "I’ve made it home folks. Thanks for such a fab weekend, and thanks to Chris and Ben for organising a great trip 🎉🔥"),
    ("Craig", "Massive thanks to Chris and Ben for being awesome hosts again and it was great meeting everyone 🎵🎉 Countdowns back on only 360 days to go 😂"),
    ("Kris", "Thanks for a great weekend everyone !! Thanks Chris and Ben for the opportunity and experience was amazing hopefully can come along again next year 💙💜💖🎵"),
    ("Kyle", "Thanks for a great weekend folks. hopefully see use again next year"),
    ("Lindsey", "Thank you so much Chris and Ben! Firstly for giving us the opportunity to be there and secondly for being fantastic hosts! Glad we never got tickets through the sales now and got to share it with so many incredible people! .. sad it's all over 🫶🏼🏴󠁧󠁢󠁣󠁴󠁿 XXX"),
    ("Chris A", "Thanks for a class weekend everyone! Chris and Ben, yous smashed the hosting! 🥂🫶"),
    ("Hannah", "Brilliant few days - thank you so much Chris and Ben for looking after us ❤️"),
    ("Liam", "Had an amazing time! Thanks Chris and Ben for the excellent hosting. Looking forward to next year 👀"),
    ("Jen", "Thanks Chris & Ben another amazing year 🙌🙌"),
    ("Pamela", "Thank you so much guys!!!! Incredible experience 🫶🏼 our first time in TML and it was incredibly perfect from minute one! beautiful gifts from the hosts ❤️❤️ hope you all get home safe!! X"),
    ("Steph", "Thanks so much Chris & Ben for an unforgettable weekend 🦋 sharing a great experience with the most awesome people. Rest up everyone, safe travels and lucky buggers being home already 😩🙏🏻 it’s been a pleasure everyone thank you xxxx"),
    ("Andrea", "Thankyou ben and chris for the best experience enjoyed every second of it, and really enjoyed meeting everyone, safe home everyone ❤️"),
    ("Oli", "Nice one for such a mad weekend, appreciate you boys! 💙 And it was great meeting everyone in this group finally! Get home safe everyone and hopefully we’ll have a reunion this time next year 😉 Peace! ✌️"),
    ("Grant", "Safe travels to everyone! I’m in Brussels rn tysm for everything I had such a lovely weekend you guys were all great! 🫶🏼"),
    ("Kayla", "Thank you all so much ❤️"),
    ("Fiona", "Thanks everyone for a phenomenal weekend, what an amazing group we had this year it really does make all the difference, hope to see lots of your faces again next year! ❤️🦋"),
    ("Jessica", "Thank you Ben and Chris for another amazing weekend at Tomorrowland and for taking care of us ❤️❤️ See you soon and I hope everyone is recovering nicely, see you again soon 🍻"),
    ("Gary", "Thanks As You Like It for another awesome weekend. Finally home and showered after a long day of travel. 360 days to go until TML 2027 🙌🥰"),
    ("Marly", "Just got home - Thankyou so so much 💙🤍"),
    ("Michael", "Best time 🫶🦋"),
    ("Soph", "We have just started our 7 hour drive back to Scotland from England 🤢 thanks so much for the best weekend! Hope to see yous all next year xx"),
    ("Shannon", "Still not home 😂 thanks for the best weekend and see yous again next year 🫶🏻"),
    ("Cathy", "Finally home - thanks everyone for a fantastic weekend! See you next year! ❤️🤗"),
    ("’arry", "Thanks everyone for an amazing weekend! 🙌 As You Like It Festivals smashed it 👏"),
    ("Anu", "We’ve just landed in Stockholm. Thank you for an amazing weekend! We really had the best time. A special thank you to Chris and Pete for everything — you made it even more memorable. I hope we get to see each other again next year at Tomorrowland! ❤️"),
    ("Alannah", "We’ve just landed at Heathrow! Thanks for such a great first Tomorrowland - we loved every second! 💃🎶 Thanks Chris and Pete for all your help and organisation! xx"),
    # Saved contacts, kept but shown by first name only.
    ("Dean", "Thanks Ben and Chris see you next year not long to go 🙌"),
    ("Craig", "❤️ As You Like It ❤️ Thanks for an awesome weekend, a fantastic group and ran extremely smoothly as always!!! Thanks again, see you all next year 🔥"),
    ("James", "Thanks so much Ben and Chris for looking after us again this year! Another amazing experience with you guys. Nice to meet you all and good to see some of you regulars again 💪💪 roll on next year."),
]

# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #

W, H = 1080, 1920           # story canvas
FPS = 30

# Motion timing (seconds)
HOLD_START = 2.0            # dwell on the title before the roll begins
HOLD_END = 2.6             # dwell on the outro card at the end
SCROLL_PXPS = 225          # scroll speed in pixels / second

# Layout
SIDE_MARGIN = 60
BUBBLE_MAX_W = 880
BUBBLE_PAD_X = 34
BUBBLE_PAD_Y = 28
BUBBLE_GAP = 34
BUBBLE_RADIUS = 34

# Type
NAME_SIZE = 34
BODY_SIZE = 37
EMOJI_RATIO = 1.15         # emoji height relative to body font size

# Colours (WhatsApp-ish)
BG_TOP = (7, 47, 43)
BG_MID = (7, 94, 84)       # #075E54
BG_BOTTOM = (10, 61, 56)
BUBBLE_BG = (255, 255, 255)
BODY_COLOR = (26, 30, 32)
META_COLOR = (140, 150, 150)
TICK_COLOR = (83, 189, 235)

# Per-sender accent palette (cycled), echoing WhatsApp group-chat name colours.
ACCENTS = [
    (0, 137, 123), (233, 30, 99), (63, 81, 181), (255, 111, 0),
    (2, 136, 209), (123, 31, 162), (56, 142, 60), (211, 47, 47),
    (0, 151, 167), (175, 82, 20),
]

FONT_DIR = "/usr/share/fonts/truetype"
NOTO_EMOJI_PATH = f"{FONT_DIR}/noto/NotoColorEmoji.ttf"
DEJAVU = f"{FONT_DIR}/dejavu/DejaVuSans.ttf"
DEJAVU_BOLD = f"{FONT_DIR}/dejavu/DejaVuSans-Bold.ttf"

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
OUT_MP4 = os.path.join(OUT_DIR, "thank-you-motion.mp4")
OUT_POSTER = os.path.join(OUT_DIR, "thank-you-motion-poster.png")

# --------------------------------------------------------------------------- #
# Fonts                                                                       #
# --------------------------------------------------------------------------- #

font_name = ImageFont.truetype(DEJAVU_BOLD, NAME_SIZE)
font_body = ImageFont.truetype(DEJAVU, BODY_SIZE)
font_meta = ImageFont.truetype(DEJAVU, 22)
font_title = ImageFont.truetype(DEJAVU_BOLD, 92)
font_sub = ImageFont.truetype(DEJAVU, 34)
font_kicker = ImageFont.truetype(DEJAVU_BOLD, 28)

# Noto Color Emoji is a bitmap-strike font: it must be opened at its native
# size (109) and the rendered glyph scaled to the size we actually want.
NOTO_STRIKE = 109
font_emoji = ImageFont.truetype(NOTO_EMOJI_PATH, NOTO_STRIKE)

_emoji_cache: dict[tuple[str, int], Image.Image] = {}


def render_emoji(cluster: str, target_h: int) -> Image.Image | None:
    """Render a single emoji grapheme cluster to an RGBA image `target_h` tall."""
    key = (cluster, target_h)
    if key in _emoji_cache:
        return _emoji_cache[key]
    canvas = Image.new("RGBA", (NOTO_STRIKE * 3, NOTO_STRIKE + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    try:
        d.text((10, 10), cluster, font=font_emoji, embedded_color=True)
    except Exception:
        return None
    bbox = canvas.getbbox()
    if bbox is None:
        return None
    glyph = canvas.crop(bbox)
    scale = target_h / glyph.height
    out = glyph.resize((max(1, round(glyph.width * scale)), target_h), Image.LANCZOS)
    _emoji_cache[key] = out
    return out


# --------------------------------------------------------------------------- #
# Rich-text (text + emoji) layout                                             #
# --------------------------------------------------------------------------- #

_EMOJI_RANGES = (
    (0x1F300, 0x1FAFF),   # symbols, pictographs, supplemental, extended-A
    (0x1F000, 0x1F0FF),   # mahjong / dominoes / cards
    (0x1F1E6, 0x1F1FF),   # regional indicators (flags)
    (0x2600, 0x27BF),     # misc symbols + dingbats (☀ ✈ ❤ …)
    (0x2300, 0x23FF),     # technical (⌚ ⏰ ▶ …)
    (0x2B00, 0x2BFF),     # stars / arrows (⭐ ⬆ …)
    (0x2190, 0x21FF),     # arrows
)
# Individual emoji codepoints that sit among ordinary text punctuation, so we
# can't include their whole Unicode block without swallowing quotes/dashes.
_EMOJI_SINGLES = {0x203C, 0x2049, 0x2122, 0x2139, 0x3030, 0x303D, 0x00A9, 0x00AE}
_ZWJ = 0x200D
_VS = (0xFE0E, 0xFE0F)
_KEYCAP = 0x20E3


def _is_emoji_base(cp: int) -> bool:
    return cp in _EMOJI_SINGLES or any(lo <= cp <= hi for lo, hi in _EMOJI_RANGES)


def _is_emoji_extend(cp: int) -> bool:
    """Characters that continue an emoji cluster."""
    return (
        cp in _VS
        or cp == _ZWJ
        or cp == _KEYCAP
        or 0x1F3FB <= cp <= 0x1F3FF      # skin-tone modifiers
        or 0xE0020 <= cp <= 0xE007F      # tag characters (subdivision flags)
        or 0x1F1E6 <= cp <= 0x1F1FF      # regional indicators
    )


def _tokenize(text: str):
    """Split into tokens: ('word', str), ('space',), ('break',), ('emoji', str).

    Emoji clusters (skin tones, ZWJ sequences, tag/subdivision flags, keycaps)
    are detected with a self-contained scanner so we don't depend on an emoji
    dataset that may miss newer sequences (e.g. the Scotland flag).
    """
    tokens = []
    n = len(text)
    i = 0
    word = ""

    def flush_word():
        nonlocal word
        if word:
            tokens.append(("word", word))
            word = ""

    while i < n:
        ch = text[i]
        cp = ord(ch)
        if ch == "\n":
            flush_word(); tokens.append(("break",)); i += 1; continue
        if ch == " ":
            flush_word(); tokens.append(("space",)); i += 1; continue
        if _is_emoji_base(cp):
            flush_word()
            j = i + 1
            while j < n:
                njp = ord(text[j])
                if _is_emoji_extend(njp):
                    j += 1
                elif ord(text[j - 1]) == _ZWJ and _is_emoji_base(njp):
                    j += 1  # the glyph that a ZWJ joins to
                else:
                    break
            tokens.append(("emoji", text[i:j]))
            i = j
            continue
        word += ch
        i += 1
    flush_word()
    return tokens


def layout_rich(text: str, font: ImageFont.FreeTypeFont, max_w: int,
                color, emoji_h: int, line_h: int) -> Image.Image:
    """Lay out mixed text + emoji into a wrapped RGBA image `max_w` wide."""
    space_w = font.getlength(" ")
    ascent, descent = font.getmetrics()
    text_h = ascent + descent

    lines: list[list[tuple]] = [[]]
    x = 0.0

    def newline():
        nonlocal x
        lines.append([])
        x = 0.0

    for tok in _tokenize(text):
        kind = tok[0]
        if kind == "break":
            newline()
            continue
        if kind == "space":
            if x > 0:  # swallow leading spaces on a fresh line
                x += space_w
            continue
        if kind == "word":
            w = font.getlength(tok[1])
            if x + w > max_w and lines[-1]:
                newline()
            lines[-1].append(("word", tok[1], x))
            x += w
        else:  # emoji
            img = render_emoji(tok[1], emoji_h)
            if img is None:
                continue
            w = img.width + 4
            if x + w > max_w and lines[-1]:
                newline()
            lines[-1].append(("emoji", img, x))
            x += w

    total_h = max(line_h, len(lines) * line_h)
    out = Image.new("RGBA", (max_w, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)
    for row, line in enumerate(lines):
        base_y = row * line_h
        text_y = base_y + (line_h - text_h) // 2
        emoji_y = base_y + (line_h - emoji_h) // 2
        for item in line:
            if item[0] == "word":
                draw.text((item[2], text_y), item[1], font=font, fill=color)
            else:
                out.paste(item[1], (int(item[2]), emoji_y), item[1])
    # Trim trailing empty vertical space.
    bbox = out.getbbox()
    if bbox:
        out = out.crop((0, 0, max_w, min(total_h, bbox[3] + 6)))
    return out


# --------------------------------------------------------------------------- #
# Cards                                                                       #
# --------------------------------------------------------------------------- #

def make_bubble(name: str, text: str, accent) -> Image.Image:
    line_h = int(BODY_SIZE * 1.42)
    emoji_h = int(BODY_SIZE * EMOJI_RATIO)
    inner_w = BUBBLE_MAX_W - 2 * BUBBLE_PAD_X

    name_img = layout_rich(name, font_name, inner_w, accent, int(NAME_SIZE * 1.1),
                           int(NAME_SIZE * 1.35))
    body_img = layout_rich(text, font_body, inner_w, BODY_COLOR, emoji_h, line_h)

    gap_after_name = 8
    meta_h = 26
    content_h = name_img.height + gap_after_name + body_img.height + meta_h
    bubble_h = content_h + 2 * BUBBLE_PAD_Y
    bubble_w = BUBBLE_MAX_W

    # Card with a soft drop shadow.
    pad = 18
    card = Image.new("RGBA", (bubble_w + pad * 2, bubble_h + pad * 2), (0, 0, 0, 0))

    shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle(
        [pad, pad + 6, pad + bubble_w, pad + bubble_h + 6],
        radius=BUBBLE_RADIUS, fill=(0, 0, 0, 70))
    shadow = shadow.filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"]).GaussianBlur(9))
    card.alpha_composite(shadow)

    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        [pad, pad, pad + bubble_w, pad + bubble_h],
        radius=BUBBLE_RADIUS, fill=BUBBLE_BG)
    # Little chat tail on the top-left.
    draw.polygon([(pad, pad + 22), (pad - 14, pad + 6), (pad + 6, pad + 6)], fill=BUBBLE_BG)

    ox, oy = pad + BUBBLE_PAD_X, pad + BUBBLE_PAD_Y
    card.paste(name_img, (ox, oy), name_img)
    by = oy + name_img.height + gap_after_name
    card.paste(body_img, (ox, by), body_img)

    # Meta row: time + double blue tick.
    my = by + body_img.height + 4
    tick = "✓✓"
    time_txt = "22:47"
    draw.text((ox, my), time_txt, font=font_meta, fill=META_COLOR)
    tw = font_meta.getlength(time_txt)
    draw.text((ox + tw + 10, my), tick, font=font_meta, fill=TICK_COLOR)

    return card


def _center_text(draw, cx, y, text, font, fill):
    w = draw.textlength(text, font=font)
    draw.text((cx - w / 2, y), text, font=font, fill=fill)


def make_title_card() -> Image.Image:
    card = Image.new("RGBA", (W, 660), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    cx = W // 2
    _center_text(draw, cx, 120, "AS YOU LIKE IT", font_kicker, (208, 175, 94))
    _center_text(draw, cx, 190, "Thank", font_title, (255, 255, 255))
    _center_text(draw, cx, 288, "You", font_title, (255, 255, 255))
    _center_text(draw, cx, 430, "Tomorrowland 2026", font_sub, (206, 232, 226))

    heart = render_emoji("💚", 88)
    if heart:
        card.paste(heart, (cx - heart.width // 2, 500), heart)
    return card


def make_outro_card() -> Image.Image:
    card = Image.new("RGBA", (W, 230), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    cx = W // 2
    _center_text(draw, cx, 20, "Unite Forever", font_title, (255, 255, 255))
    _center_text(draw, cx, 160, "from the As You Like It Team", font_sub, (206, 232, 226))
    return card


# --------------------------------------------------------------------------- #
# Background + overlays                                                        #
# --------------------------------------------------------------------------- #

def make_background() -> Image.Image:
    # Vertical 3-stop gradient.
    top = np.array(BG_TOP, dtype=float)
    mid = np.array(BG_MID, dtype=float)
    bot = np.array(BG_BOTTOM, dtype=float)
    grad = np.zeros((H, 3), dtype=float)
    half = H // 2
    for y in range(H):
        if y < half:
            t = y / half
            grad[y] = top * (1 - t) + mid * t
        else:
            t = (y - half) / (H - half)
            grad[y] = mid * (1 - t) + bot * t
    arr = np.repeat(grad[:, None, :], W, axis=1).astype(np.uint8)
    bg = Image.fromarray(arr, "RGB").convert("RGBA")

    # Faint festival "doodle" dots for texture.
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ddraw = ImageDraw.Draw(dots)
    rng = np.random.default_rng(7)
    for _ in range(90):
        x = int(rng.integers(0, W)); y = int(rng.integers(0, H))
        r = int(rng.integers(2, 7))
        a = int(rng.integers(6, 22))
        ddraw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
    bg.alpha_composite(dots)
    return bg.convert("RGB")


def make_edge_mask() -> Image.Image:
    """L-mode alpha ramp: fade the scrolling strip near the top/bottom edges."""
    fade = 220
    col = np.full(H, 255, dtype=np.float64)
    for i in range(fade):
        v = int(255 * (i / fade))
        col[i] = min(col[i], v)
        col[H - 1 - i] = min(col[H - 1 - i], v)
    mask = np.repeat(col[:, None], W, axis=1).astype(np.uint8)
    return Image.fromarray(mask, "L")


def make_chrome() -> Image.Image:
    """Fixed top/bottom branding that sits within the faded edge zones."""
    chrome = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(chrome)
    _center_text(draw, W // 2, 40, "AS YOU LIKE IT · THANK YOU", font_kicker,
                 (255, 255, 255, 235))
    footer = "Tomorrowland 2026 · from all of us 💚"
    # emoji in footer
    fw = draw.textlength("Tomorrowland 2026 · from all of us ", font=font_meta)
    total = fw + 26
    fx = (W - total) / 2
    draw.text((fx, H - 52), "Tomorrowland 2026 · from all of us ", font=font_meta,
              fill=(210, 232, 226, 220))
    heart = render_emoji("💚", 24)
    if heart:
        chrome.paste(heart, (int(fx + fw), H - 54), heart)
    return chrome


# --------------------------------------------------------------------------- #
# Compose the scrolling strip                                                  #
# --------------------------------------------------------------------------- #

def build_strip() -> Image.Image:
    cards = []
    title = make_title_card()
    cards.append((title, "full"))
    for i, (name, text) in enumerate(MESSAGES):
        cards.append((make_bubble(name, text, ACCENTS[i % len(ACCENTS)]), "left"))
    cards.append((make_outro_card(), "full"))

    top_pad = 40
    bottom_pad = 40
    total_h = top_pad + bottom_pad + sum(c.height for c, _ in cards) \
        + BUBBLE_GAP * (len(cards) - 1)
    strip = Image.new("RGBA", (W, total_h), (0, 0, 0, 0))

    y = top_pad
    for card, align in cards:
        if align == "full":
            x = (W - card.width) // 2
        else:
            x = SIDE_MARGIN - 18  # -18 undoes the shadow pad so cards sit at margin
        strip.paste(card, (x, y), card)
        y += card.height + BUBBLE_GAP
    return strip


# --------------------------------------------------------------------------- #
# Render frames + encode                                                       #
# --------------------------------------------------------------------------- #

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Building background, chrome and strip…")
    bg = make_background()
    chrome = make_chrome()
    edge = make_edge_mask()
    strip = build_strip()

    max_scroll = max(0, strip.height - H)
    scroll_frames = int((max_scroll / SCROLL_PXPS) * FPS)
    hold_start_frames = int(HOLD_START * FPS)
    hold_end_frames = int(HOLD_END * FPS)
    total_frames = hold_start_frames + scroll_frames + hold_end_frames

    print(f"Strip height: {strip.height}px | scroll: {max_scroll}px "
          f"| {total_frames} frames (~{total_frames / FPS:.1f}s)")

    def compose(scroll_y: int) -> Image.Image:
        scroll_y = max(0, min(scroll_y, max_scroll))
        frame = bg.copy()
        view = strip.crop((0, scroll_y, W, scroll_y + H))
        # Fade the strip toward the background near the top/bottom edges.
        alpha = ImageChops.multiply(view.getchannel("A"), edge)
        view.putalpha(alpha)
        frame.paste(view, (0, 0), view)
        frame.paste(chrome, (0, 0), chrome)
        return frame.convert("RGB")

    # Poster still: the title, held.
    compose(0).save(OUT_POSTER)
    print(f"Saved poster → {OUT_POSTER}")

    writer = imageio.get_writer(
        OUT_MP4, fps=FPS, codec="libx264", macro_block_size=8,
        ffmpeg_params=["-crf", "20", "-preset", "medium",
                       "-pix_fmt", "yuv420p", "-movflags", "+faststart"])
    try:
        for f in range(total_frames):
            if f < hold_start_frames:
                y = 0
            elif f < hold_start_frames + scroll_frames:
                prog = (f - hold_start_frames) / max(1, scroll_frames)
                y = int(prog * max_scroll)
            else:
                y = max_scroll
            writer.append_data(np.asarray(compose(y)))
            if f % 60 == 0:
                print(f"  frame {f}/{total_frames}")
    finally:
        writer.close()
    size_mb = os.path.getsize(OUT_MP4) / 1e6
    print(f"Saved video → {OUT_MP4} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
