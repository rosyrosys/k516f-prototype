"""
generator.py  —  R-C-M-R framework, instantiated for the K.516f case.

Realises the quadruple  G = ⟨Σ, P, Φ, γ⟩  with:

  Σ  : the 11 × 16 modular bar table in bars.TABLE
  P  : a chooseable probability distribution over bar indices
       (either 'uniform' or 'triangular' — two dice summed, per 1792 rules)
  Φ  : the positional constraint (bar 8 → 2 options; bar 16 → 1 option)
  γ  : concatenation (each bar placed end-to-end in 3/4 time)

This script is pure-Python and stdlib-only (+ numpy for Monte Carlo
elsewhere). It writes a standards-compliant Standard MIDI File (SMF
format 0, one track).

Usage:
    python generator.py --dist uniform    --seed 42 --out out.mid
    python generator.py --dist triangular --seed 42 --out out.mid
"""

from __future__ import annotations
import argparse
import random
import struct
from pathlib import Path
from typing import List, Tuple

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bars import TABLE, N_BARS, OPTIONS_PER_BAR


# --------------------------------------------------------------------------
# The probability slot P
# --------------------------------------------------------------------------
def choose_bar_index(bar_position: int, dist: str, rng: random.Random) -> int:
    """Return a 0-indexed bar option for `bar_position` (1-indexed) under
    distribution `dist`. For positions with <11 options (8, 16) the choice
    is folded into the available options."""
    n_options = OPTIONS_PER_BAR[bar_position - 1]

    if dist == "uniform":
        # Each option equally likely.
        return rng.randrange(n_options)

    if dist == "triangular":
        # Historical two-dice sum: values 2..12, triangular.
        # Map to table indices 1..11 by subtracting 1.
        s = rng.randint(1, 6) + rng.randint(1, 6)  # 2..12
        idx = s - 2  # 0..10
        if idx >= n_options:
            # bars 8 and 16: truncate via modulo into the smaller option set
            idx = idx % n_options
        return idx

    raise ValueError(f"unknown distribution {dist!r}")


# --------------------------------------------------------------------------
# The composition operator γ  :  concatenation in 3/4
# --------------------------------------------------------------------------
def assemble(indices: List[int]):
    """Given a list of 16 bar option indices, return a tuple
    (melody_events, bass_events) where each event is
    (start_beat, midi_pitch, duration_beats). Beats accumulate across bars."""
    mel, bass = [], []
    t = 0.0
    for bar_pos, opt_idx in enumerate(indices, start=1):
        bar = TABLE[bar_pos - 1][opt_idx]
        # melody
        bt = t
        for pitch, dur in bar["melody"]:
            mel.append((bt, pitch, dur))
            bt += dur
        # bass
        bt = t
        for pitch, dur in bar["bass"]:
            bass.append((bt, pitch, dur))
            bt += dur
        t += 3.0  # advance one 3/4 bar
    return mel, bass


def generate(dist: str, seed: int):
    rng = random.Random(seed)
    indices = [choose_bar_index(i, dist, rng) for i in range(1, N_BARS + 1)]
    mel, bass = assemble(indices)
    return indices, mel, bass


# --------------------------------------------------------------------------
# Minimal Standard MIDI File writer  (no external deps)
# --------------------------------------------------------------------------
TICKS_PER_QUARTER = 480
TEMPO_MICROSEC_PER_QUARTER = 600_000   # 100 BPM, gentle minuet tempo

def _vlq(n: int) -> bytes:
    """Variable-length quantity encoding (used for MIDI delta times)."""
    if n == 0:
        return b"\x00"
    buf = []
    buf.append(n & 0x7F)
    n >>= 7
    while n:
        buf.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(buf))


def _meta(meta_type: int, data: bytes) -> bytes:
    return b"\xff" + bytes([meta_type]) + _vlq(len(data)) + data


def write_midi(mel, bass, out_path: Path):
    """Write melody + bass to a format-0 SMF."""
    # Consolidate all events as (tick, [status, data1, data2])
    events = []

    for start, pitch, dur in mel:
        t0 = int(round(start * TICKS_PER_QUARTER))
        t1 = int(round((start + dur) * TICKS_PER_QUARTER))
        events.append((t0, [0x90, pitch, 88]))   # note_on melody, vel 88
        events.append((t1, [0x80, pitch, 0]))    # note_off

    for start, pitch, dur in bass:
        t0 = int(round(start * TICKS_PER_QUARTER))
        t1 = int(round((start + dur) * TICKS_PER_QUARTER))
        events.append((t0, [0x91, pitch, 70]))   # note_on bass (ch 2), vel 70
        events.append((t1, [0x81, pitch, 0]))

    # Stable sort: earlier tick first; for ties, note_off before note_on
    events.sort(key=lambda e: (e[0], 0 if e[1][0] & 0xF0 == 0x80 else 1))

    # --- track bytes ---
    track = bytearray()
    # tempo meta
    tempo_data = TEMPO_MICROSEC_PER_QUARTER.to_bytes(3, "big")
    track += _vlq(0) + _meta(0x51, tempo_data)
    # time signature 3/4 (meta 0x58: numer, denom-pow2, clocks/click=24, 32nd/quarter=8)
    track += _vlq(0) + _meta(0x58, bytes([3, 2, 24, 8]))
    # key signature C major: sharps=0, major=0
    track += _vlq(0) + _meta(0x59, bytes([0, 0]))
    # programme change for both channels (ch 0 = piano, ch 1 = piano)
    track += _vlq(0) + bytes([0xC0, 0])   # ch 0 → Acoustic Grand
    track += _vlq(0) + bytes([0xC1, 0])   # ch 1 → Acoustic Grand

    # note events
    prev_tick = 0
    for tick, msg in events:
        delta = tick - prev_tick
        track += _vlq(delta) + bytes(msg)
        prev_tick = tick

    # end-of-track
    track += _vlq(0) + _meta(0x2F, b"")

    # --- header + track chunks ---
    header = b"MThd" + (6).to_bytes(4, "big") + \
             (0).to_bytes(2, "big") + \
             (1).to_bytes(2, "big") + \
             TICKS_PER_QUARTER.to_bytes(2, "big")
    chunk = b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)

    out_path.write_bytes(header + chunk)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dist", choices=["uniform", "triangular"],
                   default="triangular",
                   help="Probability distribution P over bar options")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    indices, mel, bass = generate(args.dist, args.seed)
    write_midi(mel, bass, Path(args.out))

    print(f"seed={args.seed} dist={args.dist}")
    print(f"chosen bar indices (1-indexed options):")
    print("  " + ", ".join(f"{i + 1}" for i in indices))
    print(f"melody notes: {len(mel)}  |  bass notes: {len(bass)}")
    print(f"written: {args.out}")


if __name__ == "__main__":
    main()
