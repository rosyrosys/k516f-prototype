"""
bars.py  —  Schematic K.516f bar table.

This module supplies an 11 x 16 table of one-bar minuet fragments in
C major, 3/4 metre. It is a **structural demonstration** of the K.516f
modular alphabet Σ: it preserves the historically-documented slot shape
(14 positions with 11 options, position 8 with 2 options for the half
cadence, position 16 with 1 option for the authentic cadence) but the
bar content itself is *not* transcribed from the Simrock 1792 plates.
Swapping in Simrock's bars — e.g., from Zaslaw (1992) or Nierhaus
(2009) — only requires replacing the tables below; the generator and
entropy code are bar-agnostic.

Representation
--------------
Each bar is a dict with two voices:
  melody : list of (midi_pitch, duration_in_beats)
  bass   : list of (midi_pitch, duration_in_beats)

Durations are given in *quarter-note beats* (3.0 per bar for 3/4).
The sum of durations in each voice equals 3.0.
"""

# --------------------------------------------------------------------------
# Helpers for readable note names
# --------------------------------------------------------------------------
_BASE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

def n(name):
    """Parse 'C4', 'F#5', 'Bb3' → MIDI pitch (C4 = 60)."""
    if name[1] in '#b':
        step, accidental, octave = name[0], name[1], name[2:]
    else:
        step, accidental, octave = name[0], '', name[1:]
    pc = _BASE[step] + (1 if accidental == '#' else -1 if accidental == 'b' else 0)
    return 12 * (int(octave) + 1) + pc


# --------------------------------------------------------------------------
# Harmonic plan per bar position (1-indexed to match historical layout)
# --------------------------------------------------------------------------
# Typical minuet: 8-bar A phrase (half cadence on V) + 8-bar B phrase (PAC on I).
#   bar  1-3 : tonic-region
#   bar  4   : pre-dominant
#   bar  5-6 : tonic / V
#   bar  7   : pre-dominant
#   bar  8   : V (half cadence)   — 2 options
#   bar  9-11: tonic-region development
#   bar 12   : pre-dominant
#   bar 13-14: tonic / V
#   bar 15   : V (pre-final)
#   bar 16   : V → I (PAC)        — 1 option

# --------------------------------------------------------------------------
# 11 stock melodic figures per bar position, built as variations on the
# chord-tone set of that bar's harmony. Bass line is a steady I/IV/V
# outline in the low register (simulating a left-hand continuo).
# --------------------------------------------------------------------------

def _variations(chord_tones, bass_notes):
    """Generate 11 distinct one-bar (3/4) melodic variations from a set
    of chord tones. All voices sum to 3 beats. Returns list[dict]."""
    ct = chord_tones
    # Ensure we have at least 5 tones to cycle through
    while len(ct) < 5:
        ct = ct + [p + 12 for p in ct[:5 - len(ct)]]
    a, b, c, d, e = ct[0], ct[1], ct[2], ct[3 % len(ct)], ct[4 % len(ct)]

    figures = [
        # v1: three quarter notes, root-third-fifth
        [(a, 1.0), (b, 1.0), (c, 1.0)],
        # v2: quarter + two eighths + quarter
        [(a, 1.0), (b, 0.5), (c, 0.5), (b, 1.0)],
        # v3: dotted-quarter + eighth + quarter
        [(a, 1.5), (b, 0.5), (c, 1.0)],
        # v4: ascending scalar
        [(a, 1.0), (c, 1.0), (d, 1.0)],
        # v5: descending scalar
        [(e, 1.0), (c, 1.0), (a, 1.0)],
        # v6: leap + step + leap
        [(a, 1.0), (d, 1.0), (b, 1.0)],
        # v7: neighbour motion
        [(c, 1.0), (b, 0.5), (c, 0.5), (a, 1.0)],
        # v8: arpeggio figure
        [(a, 0.5), (c, 0.5), (e, 1.0), (c, 1.0)],
        # v9: long-short-short-short-long (minuet rhythm)
        [(a, 1.0), (b, 0.5), (c, 0.5), (d, 1.0)],
        # v10: suspension figure
        [(d, 1.5), (c, 0.5), (b, 1.0)],
        # v11: cadential turn
        [(c, 0.5), (d, 0.5), (c, 0.5), (b, 0.5), (a, 1.0)],
    ]

    # Bass: tonic on beat 1, chord continuation on beat 2
    bass = [(bass_notes[0], 1.0),
            (bass_notes[1 % len(bass_notes)], 1.0),
            (bass_notes[2 % len(bass_notes)], 1.0)]

    return [{"melody": fig, "bass": list(bass)} for fig in figures]


# --------------------------------------------------------------------------
# Chord-tone sets per bar position (C major)
#   I   = C, E, G, C, E          root C3
#   ii  = D, F, A, D, F          root D3
#   IV  = F, A, C, F, A          root F3
#   V   = G, B, D, G, B          root G2
#   vi  = A, C, E, A, C          root A2
# --------------------------------------------------------------------------

def _ct(*names):
    return [n(x) for x in names]

HARM = {
    'I'  : dict(mel=_ct('C5', 'E5', 'G5', 'C6', 'E6'),
                bass=_ct('C3', 'E3', 'G3')),
    'IV' : dict(mel=_ct('F5', 'A5', 'C6', 'F6', 'A6'),
                bass=_ct('F3', 'A3', 'C4')),
    'V'  : dict(mel=_ct('G5', 'B5', 'D6', 'G6', 'B6'),
                bass=_ct('G2', 'B2', 'D3')),
    'V7' : dict(mel=_ct('G5', 'B5', 'D6', 'F6', 'G6'),
                bass=_ct('G2', 'B2', 'F3')),
    'ii' : dict(mel=_ct('D5', 'F5', 'A5', 'D6', 'F6'),
                bass=_ct('D3', 'F3', 'A3')),
    'vi' : dict(mel=_ct('A4', 'C5', 'E5', 'A5', 'C6'),
                bass=_ct('A2', 'C3', 'E3')),
}

# Harmonic plan: 16 bars
BAR_HARMONY = [
    'I',   # 1
    'I',   # 2
    'vi',  # 3
    'IV',  # 4  pre-dominant
    'I',   # 5
    'V',   # 6
    'ii',  # 7  pre-dominant
    'V',   # 8  HALF CADENCE — two options
    'I',   # 9
    'vi',  # 10
    'I',   # 11
    'IV',  # 12 pre-dominant
    'I',   # 13
    'V7',  # 14
    'V7',  # 15
    'I',   # 16 PAC — one option
]

# --------------------------------------------------------------------------
# Build the 11 x 16 table
# --------------------------------------------------------------------------
TABLE = []  # TABLE[bar_idx][option_idx] → bar dict

for idx, harm in enumerate(BAR_HARMONY, start=1):
    h = HARM[harm]
    variants = _variations(h['mel'], h['bass'])

    if idx == 8:
        # half-cadence bar: two options only (V and V7 flavours)
        v_variants = _variations(HARM['V']['mel'], HARM['V']['bass'])
        v7_variants = _variations(HARM['V7']['mel'], HARM['V7']['bass'])
        TABLE.append([v_variants[0], v7_variants[5]])

    elif idx == 16:
        # authentic cadence bar: one option, fixed V→I motion
        cadence = {
            "melody": [(n('D5'), 1.0), (n('E5'), 1.0), (n('C5'), 1.0)],
            "bass":   [(n('G2'), 1.0), (n('G2'), 1.0), (n('C3'), 1.0)],
        }
        TABLE.append([cadence])

    else:
        # 11 options, drawn from the bar's harmony
        TABLE.append(variants)


# --------------------------------------------------------------------------
# Public constants for the generator
# --------------------------------------------------------------------------
N_BARS = 16
OPTIONS_PER_BAR = [len(TABLE[i]) for i in range(N_BARS)]
assert OPTIONS_PER_BAR == [11] * 7 + [2] + [11] * 7 + [1], OPTIONS_PER_BAR


if __name__ == "__main__":
    # quick self-test
    print(f"{N_BARS} bars; option counts per bar: {OPTIONS_PER_BAR}")
    total = 1
    for k in OPTIONS_PER_BAR:
        total *= k
    print(f"Total realisations: {total:,}")
    # structural check: 11^14 * 2 * 1 = 7.595 × 10^14
