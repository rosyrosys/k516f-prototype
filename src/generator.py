"""
generator.py  —  P (probability distribution) and γ (composition operator).

For each of the 16 bar positions, a distribution P over the position's
feasible archetype set is sampled, and γ concatenates the chosen bars
into a 3/4 minuet. A Standard MIDI File (SMF) is written using a small
inline writer (no external MIDI library required).

Two distributions are supported:
    --dist uniform     : P(x) = 1/k   (modern AI-music default prior)
    --dist triangular  : the historical 2-dice sum prior  (1/36, 2/36, ...,
                          6/36, ..., 1/36)

Usage:
    python generator.py --dist triangular --seed 42 --out outputs/run.mid
"""

from __future__ import annotations
import argparse
import struct
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bars import (
    alphabet_at,
    get_bar,
    N_BARS,
    TIME_SIG_NUM,
    TIME_SIG_DEN,
    SIGMA_SIZE,
)

PPQ = 480                                     # ticks per quarter note
TEMPO_MICROSEC_PER_QUARTER = 600_000          # 100 BPM
DEFAULT_VELOCITY_MEL = 92
DEFAULT_VELOCITY_BASS = 78


# ----------------------------------------------------------------------
# P  —  distributions
# ----------------------------------------------------------------------

def _triangular_2d(k: int) -> np.ndarray:
    """Triangular distribution as in the historical 2-dice sum, restricted
    to k alternatives. For k = 11 this is exactly the (1,2,3,4,5,6,5,4,3,
    2,1)/36 pmf used by Mozart's table."""
    if k == 11:
        w = np.array([1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1], dtype=np.float64)
    elif k == 2:
        w = np.array([1, 1], dtype=np.float64)
    elif k == 1:
        w = np.array([1], dtype=np.float64)
    else:
        # generic symmetric triangular
        mid = (k - 1) / 2.0
        w = np.array([mid - abs(i - mid) + 1 for i in range(k)], dtype=np.float64)
    return w / w.sum()


def _uniform(k: int) -> np.ndarray:
    return np.full(k, 1.0 / k, dtype=np.float64)


def distribution_for(bar_position: int, dist_name: str) -> np.ndarray:
    """Return the pmf over feasible archetypes for this bar position."""
    k = len(alphabet_at(bar_position))
    if dist_name == "triangular":
        return _triangular_2d(k)
    if dist_name == "uniform":
        return _uniform(k)
    raise ValueError(f"unknown dist {dist_name!r}")


# ----------------------------------------------------------------------
# γ  —  composition operator
# ----------------------------------------------------------------------

def generate(dist: str, seed: int):
    """Sample one realisation of the dice game.

    Returns:
        chosen_indices : list[int] of archetype indices (length 16)
        melody_events  : list of (start_beat_global, midi_pitch, dur_beats)
        bass_events    : list of (start_beat_global, midi_pitch, dur_beats)
    """
    rng = np.random.default_rng(seed)
    chosen_indices = []
    mel_events, bass_events = [], []
    for bar_pos in range(1, N_BARS + 1):
        feasible = alphabet_at(bar_pos)
        pmf = distribution_for(bar_pos, dist)
        choice = int(rng.choice(len(feasible), p=pmf))
        archetype_idx = feasible[choice]
        chosen_indices.append(archetype_idx)
        mel, bass = get_bar(archetype_idx)
        bar_offset = (bar_pos - 1) * TIME_SIG_NUM   # 3 beats per bar
        for (s, p, d) in mel:
            mel_events.append((bar_offset + s, p, d))
        for (s, p, d) in bass:
            bass_events.append((bar_offset + s, p, d))
    return chosen_indices, mel_events, bass_events


# ----------------------------------------------------------------------
# Standard MIDI File writer  (Type 1, inline, no dependencies)
# ----------------------------------------------------------------------

def _vlq(n: int) -> bytes:
    """Variable-length quantity encoding."""
    if n < 0:
        raise ValueError("VLQ requires non-negative")
    if n == 0:
        return b"\x00"
    out = []
    out.append(n & 0x7F)
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def _meta(tag: int, data: bytes) -> bytes:
    return b"\xFF" + bytes([tag]) + _vlq(len(data)) + data


def _track_chunk(events_with_dt: list[bytes]) -> bytes:
    body = b"".join(events_with_dt)
    body += _vlq(0) + _meta(0x2F, b"")     # End-of-track
    return b"MTrk" + struct.pack(">I", len(body)) + body


def _conductor_track() -> bytes:
    """Tempo + time signature + key signature on a tempo track."""
    parts = []
    # tempo
    tempo_bytes = TEMPO_MICROSEC_PER_QUARTER.to_bytes(3, "big")
    parts.append(_vlq(0) + _meta(0x51, tempo_bytes))
    # time signature 3/4 with 24 MIDI clocks/beat, 8 32nd-notes/quarter
    ts = bytes([TIME_SIG_NUM, 2, 24, 8])  # 2 = log2(4)
    parts.append(_vlq(0) + _meta(0x58, ts))
    # key sig: 0 sharps/flats, major
    parts.append(_vlq(0) + _meta(0x59, bytes([0, 0])))
    return _track_chunk(parts)


def _events_to_track(events, channel: int, velocity: int, name: bytes) -> bytes:
    """events: list of (start_beat, pitch, dur_beats)."""
    # Build tick-stamped on/off list, then sort by absolute tick, then
    # emit deltas.
    abs_evs = []  # (tick, kind, pitch)  kind=1 on, 0 off
    for (sb, p, db) in events:
        on = int(round(sb * PPQ))
        off = int(round((sb + db) * PPQ))
        if off <= on:
            off = on + 1
        abs_evs.append((on, 1, p))
        abs_evs.append((off, 0, p))
    abs_evs.sort(key=lambda x: (x[0], x[1]))   # off before on at same tick

    body_parts = []
    body_parts.append(_vlq(0) + _meta(0x03, name))   # track name

    last_tick = 0
    for (tick, kind, pitch) in abs_evs:
        dt = max(0, tick - last_tick)
        last_tick = tick
        status = (0x90 if kind == 1 else 0x80) | (channel & 0x0F)
        vel = velocity if kind == 1 else 0
        body_parts.append(_vlq(dt) + bytes([status, pitch & 0x7F, vel & 0x7F]))
    return _track_chunk(body_parts)


def write_midi(out_path: Path, mel_events, bass_events):
    """Write a Type-1 SMF with conductor + melody + bass tracks."""
    header = b"MThd" + struct.pack(">IHHH", 6, 1, 3, PPQ)
    cond = _conductor_track()
    mel_trk = _events_to_track(mel_events, channel=0,
                               velocity=DEFAULT_VELOCITY_MEL, name=b"Melody")
    bass_trk = _events_to_track(bass_events, channel=1,
                                velocity=DEFAULT_VELOCITY_BASS, name=b"Bass")
    out_path.write_bytes(header + cond + mel_trk + bass_trk)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dist", choices=["uniform", "triangular"],
                   default="triangular")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", required=True, help="MIDI output path")
    args = p.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    indices, mel, bass = generate(args.dist, args.seed)
    write_midi(out, mel, bass)

    print(f"|Σ| = {SIGMA_SIZE:,}")
    print(f"dist = {args.dist}   seed = {args.seed}")
    print(f"chosen archetype indices (1-based bar pos → idx):")
    for b, idx in enumerate(indices, start=1):
        print(f"  bar {b:>2}: archetype #{idx}")
    print(f"written: {out}")


if __name__ == "__main__":
    main()
