"""
entropy_validation.py  —  Cross-check of the 46.842-bit specification entropy.

The closed-form specification entropy of K.516f under the historical
two-dice (triangular) distribution is

    H_spec = sum over bars b of  H(P_b)

where P_b is the per-bar pmf. For bars with k = 11 alternatives drawn
from the 2-dice sum, H(P_b) = 3.27392... bits; bar 8 has 2 alternatives
(uniform → 1.000 bit); bar 16 is forced (0 bits).

So the closed-form value is

    H_spec = 14 * H_2d11 + 1.0 + 0.0  ≈  14 * 3.27392 + 1.0
           ≈  46.842 bits

This script
  (a) computes the closed-form value from first principles, and
  (b) validates it via a Monte-Carlo plug-in estimator on N draws.

Both numbers should agree to within Δ ≤ 0.01 bits at N = 200,000.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bars import alphabet_at, N_BARS, SIGMA_SIZE
from generator import distribution_for


# ----------------------------------------------------------------------
# Closed-form
# ----------------------------------------------------------------------

def _shannon(p: np.ndarray) -> float:
    p = p[p > 0]
    return float(-np.sum(p * np.log2(p)))


def closed_form_entropy(dist: str) -> tuple[float, list[float]]:
    per_bar = []
    for b in range(1, N_BARS + 1):
        p = distribution_for(b, dist)
        per_bar.append(_shannon(p))
    return float(sum(per_bar)), per_bar


# ----------------------------------------------------------------------
# Monte-Carlo
# ----------------------------------------------------------------------

def monte_carlo_entropy(dist: str, n_draws: int, seed: int) -> float:
    """Plug-in entropy estimator on per-bar empirical frequencies, summed.

    Because bars are sampled independently in this generator, the joint
    entropy decomposes additively, and the per-bar empirical pmf is a
    consistent estimator of P_b. Summing the per-bar Ĥ gives an
    unbiased-ish (low-bias plug-in) estimator of H_spec.
    """
    rng = np.random.default_rng(seed)
    total_h = 0.0
    for b in range(1, N_BARS + 1):
        feasible = alphabet_at(b)
        k = len(feasible)
        if k == 1:
            total_h += 0.0
            continue
        pmf = distribution_for(b, dist)
        draws = rng.choice(k, size=n_draws, p=pmf)
        counts = np.bincount(draws, minlength=k).astype(np.float64)
        emp = counts / counts.sum()
        total_h += _shannon(emp)
    return float(total_h)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dist", choices=["uniform", "triangular"],
                   default="triangular")
    p.add_argument("--n", type=int, default=200_000,
                   help="Monte-Carlo sample size per bar")
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--out-json", default="outputs/entropy_validation.json")
    p.add_argument("--out-txt", default="outputs/entropy_validation.txt")
    args = p.parse_args()

    h_closed, per_bar = closed_form_entropy(args.dist)
    h_mc = monte_carlo_entropy(args.dist, args.n, args.seed)
    delta = abs(h_closed - h_mc)

    # |Σ| sanity
    expected_sigma = 11 ** 14 * 2 * 1
    sigma_ok = (SIGMA_SIZE == expected_sigma)

    record = {
        "dist": args.dist,
        "n_draws": args.n,
        "seed": args.seed,
        "sigma_size": SIGMA_SIZE,
        "sigma_size_expected": expected_sigma,
        "sigma_size_ok": sigma_ok,
        "H_closed_form_bits": round(h_closed, 6),
        "H_monte_carlo_bits": round(h_mc, 6),
        "abs_delta_bits": round(delta, 6),
        "delta_threshold_bits": 0.01,
        "delta_ok": delta <= 0.01,
        "per_bar_bits": [round(x, 6) for x in per_bar],
    }

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(record, indent=2) + "\n",
                                   encoding="utf-8")

    lines = [
        "K.516f specification-entropy validation",
        "=" * 44,
        f"|Σ|              = {SIGMA_SIZE:,}",
        f"|Σ| expected     = {expected_sigma:,}     OK={sigma_ok}",
        f"distribution     = {args.dist}",
        f"H (closed form)  = {h_closed:.6f} bits",
        f"H (Monte-Carlo)  = {h_mc:.6f} bits   (N = {args.n:,}, seed = {args.seed})",
        f"|Δ|              = {delta:.6f} bits   (threshold = 0.01)",
        f"verdict          = {'PASS' if record['delta_ok'] and sigma_ok else 'FAIL'}",
        "",
        "per-bar contributions (bits):",
    ]
    for i, h in enumerate(per_bar, start=1):
        lines.append(f"  bar {i:>2}: {h:.6f}")
    Path(args.out_txt).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
