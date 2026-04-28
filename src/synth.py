"""
synth.py  —  Improved Fortepiano (1792 era) additive synthesis.

Five elements over the v1 plain-additive voice:
  1. Hammer-attack noise burst (3 ms leather-hammer transient)
  2. String inharmonicity (B ≈ 4e-4 → high partials slightly sharp)
  3. Two-stage envelope (fast initial drop + slow sustain)
  4. Soundboard formant (mild peak ~1.8 kHz via biquad band-pass)
  5. Stereo image (alternating L/R partial spread)

Pure-Python (numpy + stdlib `wave`); zero third-party audio dependencies.

Usage:
    python synth.py --dist triangular --seed 42 --out out.wav
"""

from __future__ import annotations
import argparse
import math
import wave
from pathlib import Path

import numpy as np
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generator import generate, TEMPO_MICROSEC_PER_QUARTER

SAMPLE_RATE = 44100
BPM = 60_000_000 / TEMPO_MICROSEC_PER_QUARTER
SEC_PER_BEAT = 60.0 / BPM


# ============================================================
# Voice: Fortepiano v2 — 1792 era, stereo, with hammer thump
# ============================================================

def midi_to_hz(m): return 440.0 * 2 ** ((m - 69) / 12.0)


_RNG = np.random.default_rng(1792)
def hammer_noise(n_samples: int, peak_hz: float) -> np.ndarray:
    """Short leather-hammer transient. Cutoff scales with note pitch."""
    if n_samples <= 0:
        return np.zeros(0, dtype=np.float32)
    raw = _RNG.normal(0, 1, n_samples).astype(np.float32)
    fc = min(4 * peak_hz, 6000.0)
    alpha = 1 / (1 + SAMPLE_RATE / (2 * math.pi * fc))
    out = np.zeros(n_samples, dtype=np.float32)
    prev = 0.0
    for i in range(n_samples):
        prev = prev + alpha * (raw[i] - prev)
        out[i] = prev
    t = np.arange(n_samples) / SAMPLE_RATE
    out *= np.exp(-t / 0.004).astype(np.float32)
    return out


def soundboard_eq(sig: np.ndarray) -> np.ndarray:
    """Mild ~1.8 kHz peak via biquad band-pass (constant skirt)."""
    f0, Q = 1800.0, 1.4
    w0 = 2 * math.pi * f0 / SAMPLE_RATE
    a = math.sin(w0) / (2 * Q)
    b0, b1, b2 = a, 0.0, -a
    a0, a1, a2 = 1 + a, -2 * math.cos(w0), 1 - a
    b0, b1, b2 = b0 / a0, b1 / a0, b2 / a0
    a1, a2 = a1 / a0, a2 / a0
    y = np.zeros_like(sig)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(sig)):
        x = sig[i]
        v = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        y[i] = v
        x2, x1 = x1, x
        y2, y1 = y1, v
    return sig + 0.30 * y


def render_note(pitch: int, dur_sec: float) -> np.ndarray:
    """Render one fortepiano note as stereo (n_samples, 2) float32 array."""
    f0 = midi_to_hz(pitch)
    n = int(dur_sec * SAMPLE_RATE)
    if n <= 0:
        return np.zeros((0, 2), dtype=np.float32)
    t = np.arange(n) / SAMPLE_RATE
    # Period-instrument partial weights: weak fundamental, strong 2nd-3rd
    weights = [0.55, 0.95, 0.70, 0.45, 0.32, 0.22, 0.16, 0.11, 0.08, 0.05, 0.04, 0.03]
    B = 4e-4  # inharmonicity coefficient (fortepiano)
    # Two-stage envelope
    fast = np.exp(-t / 0.10).astype(np.float32) * 0.55
    slow = np.exp(-t / 1.4).astype(np.float32) * 0.45
    main_env = fast + slow
    attack = min(int(0.008 * SAMPLE_RATE), n)
    if attack > 0:
        ramp = np.linspace(0, 1, attack, dtype=np.float32) ** 0.6
        main_env[:attack] *= ramp
    # Build partials with stereo spread
    L = np.zeros(n, dtype=np.float32)
    R = np.zeros(n, dtype=np.float32)
    for i, w in enumerate(weights, start=1):
        f_i = i * f0 * math.sqrt(1 + B * i * i)
        h_env = np.exp(-t * (0.3 + 0.18 * i))
        phase = (i * 0.137 * 2 * math.pi) % (2 * math.pi)
        s = (w * np.sin(2 * math.pi * f_i * t + phase) * h_env).astype(np.float32)
        pan = 0.15 * ((-1) ** i)
        L += s * (1 - pan)
        R += s * (1 + pan)
    L *= main_env
    R *= main_env
    # Soundboard formant on mono mixdown then re-disperse
    mono = ((L + R) * 0.5).astype(np.float32)
    formant = soundboard_eq(mono)
    L = L * 0.85 + 0.15 * formant
    R = R * 0.85 + 0.15 * formant
    # Hammer noise burst
    nb = int(0.003 * SAMPLE_RATE)
    burst = hammer_noise(nb, f0)
    L[:nb] += burst * 0.25
    R[:nb] += burst * 0.25
    return np.stack([L, R], axis=1)


def render_events(events, total_sec, gain=0.7):
    n = int(total_sec * SAMPLE_RATE) + SAMPLE_RATE
    buf = np.zeros((n, 2), dtype=np.float32)
    for start_beat, pitch, dur_beats in events:
        si = int(start_beat * SEC_PER_BEAT * SAMPLE_RATE)
        if si >= n:
            continue
        ds = dur_beats * SEC_PER_BEAT + 0.25
        note = render_note(pitch, ds)
        ei = min(si + len(note), n)
        buf[si:ei] += note[: ei - si]
    return buf * gain


def write_wav_stereo(samples: np.ndarray, out_path: Path):
    peak = float(np.max(np.abs(samples))) or 1.0
    normed = samples / peak * 0.85
    int16 = (normed * 32767).astype(np.int16)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(int16.tobytes())


def render_from_generator(dist: str, seed: int, out_path: Path):
    indices, mel, bass = generate(dist, seed)
    total_beats = 16 * 3
    total_sec = total_beats * SEC_PER_BEAT + 1.5
    mel_buf = render_events(mel, total_sec, gain=0.65)
    bass_buf = render_events(bass, total_sec, gain=0.50)
    write_wav_stereo(mel_buf + bass_buf, out_path)
    return indices


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dist", choices=["uniform", "triangular"], default="triangular")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    indices = render_from_generator(args.dist, args.seed, Path(args.out))
    print(f"seed={args.seed} dist={args.dist}")
    print(f"chosen bar indices: {[i + 1 for i in indices]}")
    print(f"written: {args.out}  (stereo, fortepiano v2)")


if __name__ == "__main__":
    main()
