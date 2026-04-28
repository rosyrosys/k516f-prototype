# The Dice Within the Machine — K.516f Prototype

A reference implementation of the R-C-M-R framework
⟨Σ, P, Φ, γ⟩ applied to Mozart's *Musikalisches Würfelspiel*
K.516f / K. Anh. 294d (Simrock, Bonn 1792).

This repository accompanies the manuscript **"The Dice Within the
Machine: A Historical-Computational Reading of Musical Combinatorics
from Mozart to Generative AI"** (Park, 2026 — manuscript in
preparation).

## What this archive contains

| Path | Role | Description |
|------|------|-------------|
| `src/bars.py` | Σ alphabet, Φ constraints | 11 × 16 schematic bar table in C major, 3/4 metre |
| `src/generator.py` | P (distribution), γ (operator) | Stochastic bar selection + 3/4 concatenation; writes Standard MIDI |
| `src/synth.py` | render | Pure-Python additive synthesis with **Fortepiano (1792 era)** voice |
| `src/entropy_validation.py` | cross-check | Monte-Carlo validation reproducing 46.842-bit specification entropy |
| `outputs/` | artefacts | MIDI + WAV samples + entropy validation log |
| `docs/` | web demo | GitHub Pages site with audio samples + browser-side generator |
| `Makefile` | orchestration | `make all` regenerates every artefact |
| `.github/workflows/reproducibility.yml` | CI | Verifies on every push that |Σ| = 759,499,667,166,482 exactly and Monte-Carlo entropy reproduces 46.842 bits within |Δ| ≤ 0.01 |

## Reproduce

```bash
python3 src/generator.py --dist triangular --seed 42 --out outputs/run.mid
python3 src/synth.py     --dist triangular --seed 42 --out outputs/run.wav
python3 src/entropy_validation.py
```

Only NumPy is required. Pure Python 3.8+.

## Audio voice — Fortepiano v2

The synthesiser models a 1792-era fortepiano (the keyboard Mozart wrote for):

- 12 inharmonic partials (B = 4×10⁻⁴) with period-instrument weighting
- Two-stage decay envelope (fast initial drop + slow sustain)
- 3 ms hammer-attack noise burst (leather-hammer transient)
- Soundboard formant peak around 1.8 kHz
- Stereo image with alternating L/R partial spread

This produces a more historically appropriate timbre than a modern Steinway-style synthesiser, while remaining numpy-only with zero external audio dependencies.

## Citation

Park, E. J. (2026). *The Dice Within the Machine: A Historical-Computational Reading of Musical Combinatorics from Mozart to Generative AI.* Manuscript in preparation.

Park, E. J. (2026b). *The Dice Within the Machine — K.516f Prototype* (v1.1.0) [Software]. GitHub: <https://github.com/rosyrosys/k516f-prototype>.

## License

Code: MIT. Data and audio outputs: CC BY 4.0.

---

**Author.** Eun Ji Park, Seoul National University. <dr.rosyrosys@gmail.com>
