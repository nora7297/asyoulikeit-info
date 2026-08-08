#!/usr/bin/env python3
"""
Build TWO "punchy" thank-you videos from the full message pool.

Both weekends are pooled together, shuffled, and split into two videos so each
one is a random mix of Weekend 1 + Weekend 2 messages in a random order. Uses
the kinetic chat-replay engine (thank_you_motion_v2) over the real Tomorrowland
backdrop in assets/bg/.

Deterministic shuffle (fixed seed) so re-runs are stable; change SEED for a
fresh order.

Run:
    python3 scripts/thank_you_motion_split.py
"""

from __future__ import annotations

import os
import random

import thank_you_motion as v1
import thank_you_motion_v2 as v2

SEED = 20260726  # bump for a different random order
ASSET_DIR = v2.ASSET_DIR

OUTPUTS = [
    (os.path.join(ASSET_DIR, "thank-you-mix-1.mp4"),
     os.path.join(ASSET_DIR, "thank-you-mix-1-poster.png")),
    (os.path.join(ASSET_DIR, "thank-you-mix-2.mp4"),
     os.path.join(ASSET_DIR, "thank-you-mix-2-poster.png")),
]


def main():
    pool = list(v1.MESSAGES)
    random.Random(SEED).shuffle(pool)
    half = (len(pool) + 1) // 2
    parts = [pool[:half], pool[half:]]

    for idx, (msgs, (mp4, poster)) in enumerate(zip(parts, OUTPUTS), start=1):
        print(f"\n=== Mix {idx}: {len(msgs)} messages "
              f"({', '.join(n for n, _ in msgs)}) ===")
        v2.render(msgs, mp4, poster)


if __name__ == "__main__":
    main()
