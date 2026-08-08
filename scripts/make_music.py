#!/usr/bin/env python3
"""
Synthesize an original, royalty-free festival/house backing track for the
thank-you videos — no samples, no copyright, generated from scratch with numpy.

Locked to 124 BPM to match thank_you_motion_v2 (BPM=124), with a 2-bar (8-beat)
intro build and a "drop" on beat 8 — exactly where the first message appears —
so the bubble pop-ins land on the kick.

Output: assets/audio/asyoulikeit-dance.wav  (picked up automatically by the
video renderer's find_audio(), which muxes + trims + fades it per video).

Run:
    python3 scripts/make_music.py
"""

from __future__ import annotations

import os
import wave

import numpy as np

SR = 44100
BPM = 124
BEAT = 60.0 / BPM
BAR = 4 * BEAT
DUR = 30.0                       # seconds (videos trim from the start)
DROP_BEAT = 8                    # full groove kicks in here

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "audio", "asyoulikeit-dance.wav")

N = int(DUR * SR)
t = np.arange(N) / SR


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


# A-minor uplifting progression, one chord per bar: Am – F – C – G
CHORDS = [[57, 60, 64], [53, 57, 60], [60, 64, 67], [55, 59, 62]]
BASS = [33, 29, 36, 31]          # A1, F1, C2, G1


def env(length, a=0.005, d=0.2, s=0.0, r=0.05, sus_level=0.0):
    """Simple AD/AR percussive envelope of `length` samples."""
    e = np.zeros(length)
    ai = max(1, int(a * SR))
    di = max(1, int(d * SR))
    e[:ai] = np.linspace(0, 1, ai)
    n2 = min(length, ai + di)
    e[ai:n2] = np.linspace(1, sus_level, n2 - ai)
    if length > n2:
        e[n2:] = sus_level
    return e


def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i] * gain


def saw(freq, n, detune=0.0):
    ph = (np.arange(n) / SR) * freq * (1 + detune)
    return 2.0 * (ph - np.floor(0.5 + ph))


def sine(freq, n):
    return np.sin(2 * np.pi * freq * np.arange(n) / SR)


def onepole_lp(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def noise(n):
    return np.random.default_rng(7).standard_normal(n)


# --------------------------------------------------------------------------- #
# Drum voices                                                                  #
# --------------------------------------------------------------------------- #

def kick_hit():
    n = int(0.32 * SR)
    tt = np.arange(n) / SR
    f = 48 + (130 - 48) * np.exp(-tt * 28)          # pitch drop
    body = np.sin(2 * np.pi * np.cumsum(f) / SR)
    body *= np.exp(-tt * 7.5)
    click = noise(n)[:n] * np.exp(-tt * 120) * 0.5
    return (body + click) * 0.95


def clap_hit():
    n = int(0.25 * SR)
    tt = np.arange(n) / SR
    nz = np.random.default_rng(3).standard_normal(n)
    e = np.zeros(n)
    for off in (0.0, 0.008, 0.016):                 # three quick bursts
        s = int(off * SR)
        e[s:] += np.exp(-(tt[: n - s]) * 55)
    body = nz * e
    body = body - onepole_lp(body, 1200)            # crude high-pass
    return body * 0.6


def hat_hit(open_=False):
    n = int((0.12 if open_ else 0.05) * SR)
    tt = np.arange(n) / SR
    nz = np.random.default_rng(11).standard_normal(n)
    hp = nz - onepole_lp(nz, 6000)
    return hp * np.exp(-tt * (18 if open_ else 55)) * 0.35


def crash_hit():
    n = int(1.2 * SR)
    tt = np.arange(n) / SR
    nz = np.random.default_rng(5).standard_normal(n)
    hp = nz - onepole_lp(nz, 4000)
    return hp * np.exp(-tt * 3.0) * 0.5


# --------------------------------------------------------------------------- #
# Build the track                                                             #
# --------------------------------------------------------------------------- #

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    kick = np.zeros(N)
    perc = np.zeros(N)
    bass = np.zeros(N)
    chord = np.zeros(N)
    arp = np.zeros(N)
    fx = np.zeros(N)

    total_beats = int(DUR / BEAT)

    # Pads across the whole track (chord per bar), soft saw stack.
    for bar in range(int(DUR / BAR) + 1):
        notes = CHORDS[bar % len(CHORDS)]
        start = bar * BAR
        n = int(BAR * SR) + 1
        if start * SR >= N:
            break
        sig = np.zeros(n)
        for m in notes:
            f = midi(m)
            sig += saw(f, n, 0.003) + saw(f, n, -0.004)
        sig = onepole_lp(sig, 2200) / (len(notes) * 2)
        sig *= env(n, a=0.03, d=BAR, sus_level=0.0)
        add(chord, start, sig, 0.5)

    # Intro riser (0 .. drop): rising filtered noise + pitch sweep.
    ri_n = int(DROP_BEAT * BEAT * SR)
    tt = np.arange(ri_n) / SR
    nz = np.random.default_rng(9).standard_normal(ri_n)
    riser = (nz - onepole_lp(nz, 3000)) * (tt / tt[-1]) ** 2 * 0.35
    add(fx, 0.0, riser)
    add(fx, DROP_BEAT * BEAT, crash_hit(), 0.9)     # drop crash

    for b in range(total_beats):
        tb = b * BEAT
        bar = b // 4
        beat_in_bar = b % 4
        pre_drop = b < DROP_BEAT

        # Four-on-the-floor kick from the drop onward.
        if not pre_drop:
            add(kick, tb, kick_hit())
            # Claps on beats 2 & 4.
            if beat_in_bar in (1, 3):
                add(perc, tb, clap_hit())
            # Hats on the off-beats, open hat on the "and" of 4.
            add(perc, tb + BEAT / 2, hat_hit(open_=(beat_in_bar == 3)))
            add(perc, tb + BEAT / 4, hat_hit(), 0.6)
            add(perc, tb + 3 * BEAT / 4, hat_hit(), 0.6)

            # Bass: root note pulsed in 8ths.
            root = midi(BASS[bar % len(BASS)])
            for k in range(2):
                bn = int(0.5 * BEAT * SR)
                bsig = (np.sin(2 * np.pi * root * np.arange(bn) / SR)
                        + 0.3 * np.sin(2 * np.pi * 2 * root * np.arange(bn) / SR))
                bsig *= env(bn, a=0.004, d=0.5 * BEAT, sus_level=0.0)
                add(bass, tb + k * 0.5 * BEAT, bsig, 0.9)

            # Arp: chord tones up in 16ths, bright short pluck.
            notes = CHORDS[bar % len(CHORDS)]
            for s in range(4):
                m = notes[(beat_in_bar * 4 + s) % len(notes)] + 12
                an = int(0.25 * BEAT * SR)
                asig = saw(midi(m), an, 0.004)
                asig = onepole_lp(asig, 3500)
                asig *= env(an, a=0.002, d=0.22 * BEAT, sus_level=0.0)
                add(arp, tb + s * 0.25 * BEAT, asig, 0.5)

    # Sidechain pump on melodic elements (duck right after each beat).
    phase = (t / BEAT) % 1.0
    duck = 0.28 + 0.72 * phase ** 0.55
    bass *= duck
    chord *= duck
    arp *= duck

    mix = (kick * 1.0 + perc * 0.7 + bass * 0.8
           + chord * 0.5 + arp * 0.42 + fx * 0.6)

    # Gentle master: soft clip + normalise, short fade-in.
    mix = np.tanh(mix * 1.2)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.92
    fi = int(0.25 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)

    stereo = np.stack([mix, mix], axis=1)
    pcm = (stereo * 32767).astype(np.int16)
    with wave.open(OUT, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"Saved {DUR:.0f}s track @ {BPM} BPM -> {OUT} "
          f"({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()
