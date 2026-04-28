"""
bars.py  —  Σ alphabet and Φ feasibility constraints for K.516f.

Encodes the 11 × 16 schematic bar table of the Musikalisches Würfelspiel
(K.516f / K. Anh. 294d, Simrock, Bonn 1792).

Each cell is a *schematic* idiomatic-Mozart bar: a 3/4 measure with a
melodic top voice (4–6 events) and a bass voice (2–3 events), in C major
or G major (V), staying inside the 8 + 8 minuet form (16 bars total).

This is **not** a transcription of the historical print: the goal is to
illustrate the combinatorial structure |Σ| = 11¹⁴ × 2 × 1 and the
specification entropy H ≈ 46.842 bits, not to reproduce the 1792 score
note-for-note (which is in the public domain and freely available — see
the `figures/Figure1_K516f_Table.jpg` plate).

Pitches are MIDI numbers (C4 = 60). Times are in beats inside the bar
(0–3 for 3/4 metre).

Bar position semantics follow the historical table:
  - bars 1–7  and 9–15  : 11 alternatives each (dice sums 2..12)  →  pos_alts = 11
  - bar 8                : 2 alternatives  (cadential half-cadence)
  - bar 16               : 1 alternative   (final tonic cadence)
  → |Σ| = 11¹⁴ × 2 × 1 = 759,499,667,166,482

The 22 + 1 hand-written archetypes below are mixed into the 11 × 16 grid
by a deterministic schematic mapping; this is enough to hear the
combinatorial mechanism. Replacing this stub with a transcription of the
1792 plate is left as an exercise for the reader.
"""

from __future__ import annotations

KEY_C = 0       # C major
KEY_G = 7       # G major (V)


# --- 23 melodic archetypes (top voice, 3/4 bar) ------------------------------
# Each archetype is a list of (start_beat, midi_pitch, dur_beats)

_MEL_ARCH = [
    # 0: tonic arpeggio up
    [(0.0, 72, 1.0), (1.0, 76, 0.5), (1.5, 79, 0.5), (2.0, 84, 1.0)],
    # 1: dominant scalar descent
    [(0.0, 79, 0.5), (0.5, 77, 0.5), (1.0, 76, 1.0), (2.0, 74, 0.5), (2.5, 72, 0.5)],
    # 2: turn figure on tonic
    [(0.0, 76, 0.5), (0.5, 77, 0.5), (1.0, 76, 0.5), (1.5, 74, 0.5), (2.0, 76, 1.0)],
    # 3: leap up + step down
    [(0.0, 72, 0.5), (0.5, 79, 0.5), (1.0, 77, 0.5), (1.5, 76, 0.5), (2.0, 74, 1.0)],
    # 4: alberti-like top
    [(0.0, 72, 0.5), (0.5, 76, 0.5), (1.0, 79, 0.5), (1.5, 76, 0.5), (2.0, 84, 1.0)],
    # 5: dotted figure
    [(0.0, 76, 0.75), (0.75, 77, 0.25), (1.0, 79, 1.0), (2.0, 76, 1.0)],
    # 6: passing-tone descent
    [(0.0, 79, 1.0), (1.0, 77, 0.5), (1.5, 76, 0.5), (2.0, 74, 0.5), (2.5, 72, 0.5)],
    # 7: half-step neighbor
    [(0.0, 76, 0.5), (0.5, 77, 0.5), (1.0, 76, 1.0), (2.0, 79, 1.0)],
    # 8: triplet sweep
    [(0.0, 72, 1.0), (1.0, 76, 0.333), (1.333, 79, 0.333), (1.667, 84, 0.333), (2.0, 79, 1.0)],
    # 9: V chord arpeggio
    [(0.0, 67, 1.0), (1.0, 71, 0.5), (1.5, 74, 0.5), (2.0, 79, 1.0)],
    # 10: V7 leading
    [(0.0, 74, 0.5), (0.5, 77, 0.5), (1.0, 79, 1.0), (2.0, 77, 1.0)],
    # 11: I64 figure
    [(0.0, 72, 0.5), (0.5, 76, 0.5), (1.0, 79, 1.0), (2.0, 76, 1.0)],
    # 12: two-voice imitation start
    [(0.0, 79, 0.5), (0.5, 76, 0.5), (1.0, 79, 0.5), (1.5, 76, 0.5), (2.0, 72, 1.0)],
    # 13: cantabile leap
    [(0.0, 84, 1.0), (1.0, 79, 0.5), (1.5, 76, 0.5), (2.0, 72, 1.0)],
    # 14: stepwise rise
    [(0.0, 72, 0.5), (0.5, 74, 0.5), (1.0, 76, 0.5), (1.5, 77, 0.5), (2.0, 79, 1.0)],
    # 15: stepwise fall
    [(0.0, 79, 0.5), (0.5, 77, 0.5), (1.0, 76, 0.5), (1.5, 74, 0.5), (2.0, 72, 1.0)],
    # 16: held + flourish
    [(0.0, 76, 1.5), (1.5, 79, 0.5), (2.0, 76, 0.5), (2.5, 72, 0.5)],
    # 17: appoggiatura
    [(0.0, 77, 0.25), (0.25, 76, 0.75), (1.0, 79, 1.0), (2.0, 72, 1.0)],
    # 18: motif repetition
    [(0.0, 76, 0.5), (0.5, 79, 0.5), (1.0, 76, 0.5), (1.5, 79, 0.5), (2.0, 72, 1.0)],
    # 19: sequence step
    [(0.0, 74, 0.5), (0.5, 76, 0.5), (1.0, 77, 0.5), (1.5, 79, 0.5), (2.0, 81, 1.0)],
    # 20: half-cadence approach    (used at bar 8)
    [(0.0, 76, 0.5), (0.5, 74, 0.5), (1.0, 71, 1.0), (2.0, 67, 1.0)],
    # 21: half-cadence approach v2 (alt for bar 8)
    [(0.0, 79, 0.5), (0.5, 77, 0.5), (1.0, 74, 1.0), (2.0, 67, 1.0)],
    # 22: final cadence I (used at bar 16)
    [(0.0, 76, 0.5), (0.5, 74, 0.5), (1.0, 72, 1.0), (2.0, 72, 1.0)],
]

# --- 23 bass archetypes (bottom voice) ---------------------------------------

_BASS_ARCH = [
    [(0.0, 36, 1.0), (1.0, 43, 1.0), (2.0, 48, 1.0)],          # 0
    [(0.0, 43, 1.0), (1.0, 47, 1.0), (2.0, 50, 1.0)],          # 1
    [(0.0, 48, 1.0), (1.0, 52, 1.0), (2.0, 48, 1.0)],          # 2
    [(0.0, 36, 1.5), (1.5, 43, 1.5)],                          # 3
    [(0.0, 36, 1.0), (1.0, 48, 1.0), (2.0, 52, 1.0)],          # 4
    [(0.0, 43, 1.0), (1.0, 50, 1.0), (2.0, 47, 1.0)],          # 5
    [(0.0, 48, 1.0), (1.0, 43, 1.0), (2.0, 36, 1.0)],          # 6
    [(0.0, 41, 1.0), (1.0, 45, 1.0), (2.0, 48, 1.0)],          # 7
    [(0.0, 36, 0.5), (0.5, 43, 0.5), (1.0, 48, 1.0), (2.0, 52, 1.0)],  # 8
    [(0.0, 43, 1.5), (1.5, 50, 1.5)],                          # 9
    [(0.0, 50, 1.0), (1.0, 43, 1.0), (2.0, 47, 1.0)],          # 10
    [(0.0, 48, 1.0), (1.0, 43, 1.0), (2.0, 48, 1.0)],          # 11
    [(0.0, 43, 1.0), (1.0, 50, 1.0), (2.0, 43, 1.0)],          # 12
    [(0.0, 36, 1.0), (1.0, 40, 1.0), (2.0, 43, 1.0)],          # 13
    [(0.0, 36, 1.5), (1.5, 48, 1.5)],                          # 14
    [(0.0, 41, 1.0), (1.0, 38, 1.0), (2.0, 43, 1.0)],          # 15
    [(0.0, 48, 1.0), (1.0, 50, 1.0), (2.0, 43, 1.0)],          # 16
    [(0.0, 36, 1.0), (1.0, 43, 1.0), (2.0, 36, 1.0)],          # 17
    [(0.0, 43, 1.0), (1.0, 36, 1.0), (2.0, 43, 1.0)],          # 18
    [(0.0, 38, 1.0), (1.0, 41, 1.0), (2.0, 45, 1.0)],          # 19
    [(0.0, 43, 1.0), (1.0, 47, 1.0), (2.0, 43, 1.0)],          # 20  half-cadence on V
    [(0.0, 50, 1.0), (1.0, 43, 1.0), (2.0, 43, 1.0)],          # 21  half-cadence on V (v2)
    [(0.0, 36, 1.5), (1.5, 36, 1.5)],                          # 22  final tonic
]


def _pos_alts(bar_position: int) -> int:
    """Number of alternatives Φ allows at bar position (1..16)."""
    if bar_position == 8:
        return 2
    if bar_position == 16:
        return 1
    return 11


def alphabet_at(bar_position: int) -> list[int]:
    """Return list of feasible *archetype indices* at this bar position."""
    if bar_position == 8:
        return [20, 21]
    if bar_position == 16:
        return [22]
    # 11 alternatives drawn deterministically from the 20-archetype pool
    base = (bar_position - 1) * 7  # rotate so different bars feel different
    return [(base + i) % 20 for i in range(11)]


def get_bar(archetype_idx: int) -> tuple[list, list]:
    """Return (melody, bass) event lists for a given archetype index."""
    return _MEL_ARCH[archetype_idx], _BASS_ARCH[archetype_idx]


def sigma_size() -> int:
    """|Σ| = product of pos_alts over all 16 bar positions."""
    n = 1
    for b in range(1, 17):
        n *= _pos_alts(b)
    return n


# Public constants used by generator and entropy modules
N_BARS = 16
TIME_SIG_NUM = 3
TIME_SIG_DEN = 4
KEY_OF_PIECE = KEY_C
SIGMA_SIZE = sigma_size()  # 759,499,667,166,482


if __name__ == "__main__":
    # quick self-test
    assert SIGMA_SIZE == 11 ** 14 * 2 * 1, f"|Σ| mismatch: {SIGMA_SIZE}"
    print(f"|Σ| = {SIGMA_SIZE:,}  ({SIGMA_SIZE:.3e})")
    print(f"     = 11¹⁴ × 2 × 1 = {11**14 * 2 * 1:,}  OK")
    for b in (1, 7, 8, 9, 15, 16):
        print(f"  bar {b:>2}: {_pos_alts(b)} alternatives")
