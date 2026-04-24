"""
synth.py  —  Minimal additive synthesiser (numpy + stdlib `wave` only).

Renders a generator output (melody + bass event lists) to a 44.1 kHz
16-bit mono WAV. The timbre is a simple harpsichord-like pluck: a sum
of the first seven harmonics with descending amplitudes and a fast
attack / exponential decay envelope. It is not meant to be beautiful;
it is meant to let a reader audition the output without installing
fluidsynth or a SoundFont.

Usage:
    python synth.py --in  out.mid          --out out.wav   # re-parses a MIDI file
    python synth.py --from-generator triangular --seed 42 --out out.wav
"""

from __future__ import annotations
import argparse
import math
import struct
import wave
from pathlib import Path

import numpy as np
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generator import generate, TEMPO_MICROSEC_PER_QUARTER

SAMPLE_RATE = 44100
BPM = 60_000_000 / TEMPO_MICROSEC_PER_QUARTER   # quarters per minute
SEC_PER_BEAT = 60.0 / BPM


# --------------------------------------------------------------------------
# Voice: harpsichord-ish pluck
# --------------------------------------------------------------------------
HARMONIC_WEIGHTS = np.array([1.00, 0.50, 0.33, 0.22, 0.14, 0.09, 0.06])

def render_note(pitch_midi: int, dur_sec: float, velocity: int = 80) -> np.ndarray:
    """Return mono float32 samples for one note."""
    f0 = 440.0 * 2 ** ((pitch_midi - 69) / 12.0)
    n_samples = int(dur_sec * SAMPLE_RATE)
    # overall envelope: 5 ms attack, exponential decay
    t = np.arange(n_samples) / SAMPLE_RATE
    attack_samples = min(int(0.005 * SAMPLE_RATE), n_samples)
    env = np.ones(n_samples, dtype=np.float32)
    if attack_samples > 0:
        env[:attack_samples] = np.linspace(0, 1, attack_samples, dtype=np.float32)
    # exponential decay: half-life 0.6 s
    env *= np.exp(-t / 0.6).astype(np.float32)
    # sum harmonics
    sig = np.zeros(n_samples, dtype=np.float32)
    for i, w in enumerate(HARMONIC_WEIGHTS, start=1):
        phase = 2 * math.pi * f0 * i * t
        sig += (w * np.sin(phase)).astype(np.float32)
    sig *= env
    # scale by velocity
    sig *= (velocity / 127.0)
    return sig


def render_events(events, total_duration_sec: float) -> np.ndarray:
    """events: iterable of (start_beat, pitch, dur_beats)."""
    n = int(total_duration_sec * SAMPLE_RATE) + SAMPLE_RATE  # +1 s tail
    buf = np.zeros(n, dtype=np.float32)
    for start_beat, pitch, dur_beats in events:
        start_sec = start_beat * SEC_PER_BEAT
        dur_sec = dur_beats * SEC_PER_BEAT + 0.15  # small release tail
        start_idx = int(start_sec * SAMPLE_RATE)
        note = render_note(pitch, dur_sec)
        end_idx = start_idx + len(note)
        if end_idx > n:
            note = note[: n - start_idx]
            end_idx = n
        buf[start_idx:end_idx] += note
    return buf


def write_wav(samples: np.ndarray, out_path: Path):
    # normalise and convert to int16
    peak = float(np.max(np.abs(samples))) or 1.0
    normed = samples / peak * 0.88
    int16 = (normed * 32767).astype(np.int16)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(int16.tobytes())


def render_from_generator(dist: str, seed: int, out_path: Path):
    indices, mel, bass = generate(dist, seed)
    total_beats = 16 * 3  # 16 bars of 3/4
    total_sec = total_beats * SEC_PER_BEAT + 1.0
    mel_buf = render_events(mel, total_sec)
    bass_buf = render_events(bass, total_sec)
    mix = mel_buf * 0.7 + bass_buf * 0.55
    write_wav(mix, out_path)
    return indices


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dist", choices=["uniform", "triangular"],
                   default="triangular")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    indices = render_from_generator(args.dist, args.seed, Path(args.out))
    print(f"seed={args.seed} dist={args.dist}")
    print(f"chosen bar indices: {[i + 1 for i in indices]}")
    print(f"written: {args.out}")


if __name__ == "__main__":
    main()
