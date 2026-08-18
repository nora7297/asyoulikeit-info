#!/usr/bin/env python3
"""
Synthesized UI sound effects for the WhatsApp-style videos — no samples, no
downloads. Builds a per-video audio track by placing a "ding" at each incoming
message and a "whoosh" on the outgoing send, then writes a WAV to mux.
"""

from __future__ import annotations

import wave

import numpy as np

SR = 44100


def _sine(f, n, sr=SR):
    return np.sin(2 * np.pi * f * np.arange(n) / sr)


def ding() -> np.ndarray:
    """Two quick marimba-ish notes — a friendly incoming-message chime."""
    out = np.zeros(int(0.42 * SR))
    for start, midi in ((0.0, 88), (0.09, 93)):     # E6 then A6
        f = 440.0 * 2 ** ((midi - 69) / 12)
        n = int(0.30 * SR)
        tt = np.arange(n) / SR
        note = (_sine(f, n) + 0.35 * _sine(2 * f, n) + 0.12 * _sine(3 * f, n))
        note *= np.exp(-tt * 16)                     # fast percussive decay
        i = int(start * SR)
        out[i:i + n] += note
    return out * 0.6


def whoosh() -> np.ndarray:
    """Short rising filtered-noise sweep — an outgoing 'sent' swish."""
    n = int(0.34 * SR)
    tt = np.arange(n) / SR
    rng = np.random.default_rng(1)
    nz = rng.standard_normal(n)
    # crude rising band-pass: high-pass (difference) with a rising envelope.
    hp = np.diff(nz, prepend=nz[0])
    env = (tt / tt[-1]) ** 1.5 * np.exp(-((tt / tt[-1] - 0.7) ** 2) * 8)
    return hp * env * 0.5


def build_track(total: float, out_path: str, send_time: float | None = None,
                ding_times=()) -> str:
    n = int((total + 0.6) * SR)
    buf = np.zeros(n)
    d = ding()
    if send_time is not None:
        w = whoosh()
        i = int(send_time * SR)
        buf[i:i + len(w)] += w[: max(0, n - i)]
    for t in ding_times:
        i = int(t * SR)
        buf[i:i + len(d)] += d[: max(0, n - i)]
    peak = np.max(np.abs(buf)) + 1e-9
    buf = buf / peak * 0.9
    stereo = np.stack([buf, buf], axis=1)
    pcm = (stereo * 32767).astype(np.int16)
    with wave.open(out_path, "wb") as wv:
        wv.setnchannels(2)
        wv.setsampwidth(2)
        wv.setframerate(SR)
        wv.writeframes(pcm.tobytes())
    return out_path
