"""
entropy_validation.py  —  Empirical cross-check against §3 theoretical values.

Two complementary checks, both run on the actual generator:

  (1) Exhaustive combinatorial count of the modular alphabet Σ:
      11^14 × 2 × 1 should equal 7.594996671664820 × 10^14
      log2 of that is ≈ 49.43 bits.

  (2) Monte-Carlo estimate of the *specification entropy* under each P:
      sample N = 1,000,000 realisations; compute the per-bar empirical
      distribution of chosen options; sum the per-bar entropies.

  Expected (from §3, exact):
      uniform:    H_uniform    = 14 × log2(11) + log2(2) + log2(1)
                                = 14 × 3.4594316 + 1 + 0
                                ≈ 49.432 bits
      triangular (per-bar triangular of sums 2..12 folded into 11 slots):
                  H_bar_triangular
                   = − Σ p log2 p over {1/36, 2/36, 3/36, 4/36, 5/36,
                                        6/36, 5/36, 4/36, 3/36, 2/36, 1/36}
                   ≈ 3.2744 bits
                   × 14 + 1 + 0  ≈ 46.842 bits.

This is the 46.84-bit figure reported in §3 and used as the paper's
"specification entropy of a K.516f realisation". Matching it within
Monte-Carlo noise confirms that the generator implements the claimed P.

Output: JSON file and a human-readable summary.
"""

from __future__ import annotations
import json
import math
import random
from collections import Counter
from fractions import Fraction
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bars import N_BARS, OPTIONS_PER_BAR
from generator import choose_bar_index


# --------------------------------------------------------------------------
# Theoretical values
# --------------------------------------------------------------------------
def theoretical_combinatorial_space():
    total = 1
    for k in OPTIONS_PER_BAR:
        total *= k
    return total

def entropy_uniform_bar(k):
    return math.log2(k) if k > 1 else 0.0

def entropy_triangular_bar(k):
    """Triangular (two-dice sum) with modulo-k folding into k slots."""
    # base probabilities over sums 2..12
    probs = {s: Fraction(6 - abs(s - 7), 36) for s in range(2, 13)}  # 11 values
    # map sum s to slot s-2, folded modulo k
    slot_prob = Counter()
    for s, p in probs.items():
        slot_prob[(s - 2) % k] += p
    H = 0.0
    for _, p in slot_prob.items():
        p_f = float(p)
        if p_f > 0:
            H -= p_f * math.log2(p_f)
    return H

def theoretical_spec_entropy_uniform():
    return sum(entropy_uniform_bar(k) for k in OPTIONS_PER_BAR)

def theoretical_spec_entropy_triangular():
    return sum(entropy_triangular_bar(k) for k in OPTIONS_PER_BAR)


# --------------------------------------------------------------------------
# Monte Carlo empirical entropy
# --------------------------------------------------------------------------
def monte_carlo_entropy(dist: str, n_samples: int, seed: int = 2026):
    """Sample the generator and return the sum of per-bar empirical entropies."""
    rng = random.Random(seed)
    per_bar_counters = [Counter() for _ in range(N_BARS)]
    for _ in range(n_samples):
        for bar_pos in range(1, N_BARS + 1):
            idx = choose_bar_index(bar_pos, dist, rng)
            per_bar_counters[bar_pos - 1][idx] += 1

    per_bar_entropies = []
    for cnt in per_bar_counters:
        total = sum(cnt.values())
        H = 0.0
        for v in cnt.values():
            p = v / total
            if p > 0:
                H -= p * math.log2(p)
        per_bar_entropies.append(H)
    return per_bar_entropies


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main(n_samples: int = 1_000_000):
    report = {}

    # combinatorial space
    space = theoretical_combinatorial_space()
    report["combinatorial_space"] = {
        "value": space,
        "scientific": f"{space:.4e}",
        "log2": math.log2(space),
    }

    # theoretical uniform
    H_u_th = theoretical_spec_entropy_uniform()
    H_t_th = theoretical_spec_entropy_triangular()

    report["theoretical"] = {
        "uniform_bits":    round(H_u_th, 4),
        "triangular_bits": round(H_t_th, 4),
    }

    # Monte Carlo
    H_u_mc = sum(monte_carlo_entropy("uniform",    n_samples))
    H_t_mc = sum(monte_carlo_entropy("triangular", n_samples))

    report["monte_carlo"] = {
        "n_samples": n_samples,
        "uniform_bits":    round(H_u_mc, 4),
        "triangular_bits": round(H_t_mc, 4),
        "absolute_error_uniform":    round(abs(H_u_mc - H_u_th), 4),
        "absolute_error_triangular": round(abs(H_t_mc - H_t_th), 4),
    }

    # section-3 cross-check: paper reports 46.842 bits
    report["section3_cross_check"] = {
        "paper_reported_bits": 46.842,
        "generator_triangular_bits": round(H_t_mc, 4),
        "within_mc_noise_of_paper": abs(H_t_mc - 46.842) < 0.01,
    }

    out_dir = Path(__file__).resolve().parents[1] / "outputs"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "entropy_validation.json").write_text(
        json.dumps(report, indent=2))

    # human-readable summary
    lines = [
        "K.516f specification-entropy validation",
        "=" * 48,
        f"Combinatorial space |Σ|    : {space:,}",
        f"                    |Σ|    ≈ {space:.4e}",
        f"                    log2   : {math.log2(space):.4f} bits",
        "",
        "Theoretical per-bar distributions summed over 16 bars:",
        f"  uniform    H = {H_u_th:.4f} bits",
        f"  triangular H = {H_t_th:.4f} bits",
        "",
        f"Monte Carlo ({n_samples:,} samples, seed=2026):",
        f"  uniform    H̃ = {H_u_mc:.4f} bits  (|Δ| = {abs(H_u_mc - H_u_th):.4f})",
        f"  triangular H̃ = {H_t_mc:.4f} bits  (|Δ| = {abs(H_t_mc - H_t_th):.4f})",
        "",
        "Paper §3 reports 46.842 bits for the triangular case.",
        f"Generator yields {H_t_mc:.3f} bits; within-MC agreement: "
        f"{'YES' if abs(H_t_mc - 46.842) < 0.01 else 'NO'}",
    ]
    (out_dir / "entropy_validation.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
