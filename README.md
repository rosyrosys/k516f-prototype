# The Dice Within the Machine — K.516f Prototype

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19727020.svg)](https://doi.org/10.5281/zenodo.19727020)

A reference implementation of the R-C-M-R framework
⟨Σ, P, Φ, γ⟩ applied to Mozart's *Musikalisches Würfelspiel*
K.516f (Simrock, Bonn 1792).

This repository accompanies the article "The Dice Within the Machine:
A Historical-Computational Reading of Musical Combinatorics from
Mozart to Generative AI" (Park, preprint, under peer review, 2026).

It instantiates the article's formal quadruple as a runnable Python
package and produces three audible artefacts (uniform-P, triangular-P,
alternative-seed) together with an empirical cross-check of the
specification entropy reported in §3.

---

## What this archive contains

| Path | Role in ⟨Σ, P, Φ, γ⟩ | Description |
|------|---------------------|-------------|
| `src/bars.py`           | Σ (alphabet), Φ (positional constraints) | 11 × 16 schematic bar table in C major, 3/4 metre. Bar 8 has 2 options (half cadence); bar 16 has 1 option (authentic cadence). |
| `src/generator.py`      | P (distribution), γ (operator) | Chooses bar indices under `uniform` or `triangular` P; concatenates into a 16-bar minuet; writes a Standard MIDI File (format 0). |
| `src/synth.py`          | render | Pure-Python additive synthesiser (numpy + stdlib `wave`). Renders generator output to 44.1 kHz 16-bit mono WAV. |
| `src/entropy_validation.py` | cross-check | Closed-form and Monte-Carlo (1 000 000 samples) specification-entropy calculation; reproduces §3's 46.842 bits figure. |
| `outputs/` | artefacts | Three MIDI + WAV files plus `entropy_validation.{json,txt}`. |
| `docs/` | web demo | Single-page GitHub Pages site (`index.html` + `js/app.js`). Bilingual EN/KR. Pre-rendered audio samples plus a browser-side "roll your own" generator that ports `generator.py` and `synth.py` to vanilla JS + Web Audio. |
| `Makefile` | orchestration | One-command reproduction (`make all`). |
| `.github/workflows/reproducibility.yml` | CI | Verifies on every push that `|Σ| = 759,499,667,166,482` exactly and that the Monte-Carlo entropy reproduces 46.842 bits within |Δ| ≤ 0.01, across Python 3.9 / 3.11 / 3.12. |

## How to reproduce

The code has *no third-party dependencies beyond NumPy*. Any Python
3.8+ install will run it:

```bash
# from repository root
python3 src/generator.py         --dist triangular --seed 42 --out outputs/run.mid
python3 src/synth.py             --dist triangular --seed 42 --out outputs/run.wav
python3 src/entropy_validation.py
```

Cross-checking §3 of the paper:

```
$ python3 src/entropy_validation.py
...
Paper §3 reports 46.842 bits for the triangular case.
Generator yields 46.843 bits; within-MC agreement: YES
```

## Scope and limitations

The 11 × 16 bar table in `src/bars.py` is a **structural demonstration**
of the K.516f modular alphabet Σ: it preserves the historically
documented slot shape (11-option × 14 positions, 2-option × 1,
1-option × 1, yielding |Σ| = 11¹⁴ × 2 × 1 ≈ 7.60 × 10¹⁴) but the
bar content is a C-major minuet pastiche, **not** a transcription of
the Simrock 1792 plates. Swapping in the Simrock tables (available in
Zaslaw 1992 and Nierhaus 2009) requires only replacing the data
structure in `bars.py`; the generator, synthesiser, and validator are
bar-agnostic. The article is explicit about this scope.

Three distributions are *not* implemented here — a learned empirical
distribution from a minuet corpus, and any of the neural-era
distributions (MusicVAE, MusicLM, MusicGen) surveyed in §6. The
argument of the article is that those systems occupy a different
point in the same ⟨Σ, P, Φ, γ⟩ space, not the same point with a
different P; reimplementing them would be out of scope for a
framework-validation artefact.

## Cross-references into the paper

| Paper section | Claim | Evidence in this repository |
|---------------|-------|----------------------------|
| §3 (K.516f numerics) | "The corrected realisation count is 7.60 × 10¹⁴ and the specification entropy is 46.842 bits under the historical triangular P." | `src/bars.py` (OPTIONS_PER_BAR multiplication = 759 499 667 166 482 exactly); `outputs/entropy_validation.json` (Monte Carlo 46.843 bits, |Δ| ≤ 0.002 from theoretical). |
| §4.2 (Definitions 1–4) | "Any generative music system is modelled as G = ⟨Σ, P, Φ, γ⟩, where Σ is a finite modular alphabet, P a probability law over Σ, Φ a feasibility potential, and γ a composition operator." | `src/generator.py` — `TABLE` is Σ, `choose_bar_index(dist)` is P, `OPTIONS_PER_BAR` encodes Φ, `assemble()` is γ. The framework is connected to an executable system line-for-line. |

## Citation

If you use this prototype, please cite the article (this file's
`CITATION.cff` provides the BibTeX/CSL template).

## License

Code: MIT.  Data and audio outputs: Creative Commons Attribution 4.0
International (CC BY 4.0). See `LICENSE` and `LICENSE-data`.

---

**Author.**  Eun Ji Park, Seoul National University <dr.rosyrosys@gmail.com>

**Paper.**  Park, E. J. (2026). *The Dice Within the Machine: A
Historical-Computational Reading of Musical Combinatorics from Mozart
to Generative AI.* Manuscript under peer review.
