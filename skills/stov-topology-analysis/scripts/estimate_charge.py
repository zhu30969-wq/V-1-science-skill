#!/usr/bin/env python3
"""Estimate the topological charge of a synthetic STOV vortex field.

Usage (from platform/, with stov-scientist installed):
    python ../skills/stov-topology-analysis/scripts/estimate_charge.py --charge -1 --n 128
"""

from __future__ import annotations

import argparse

import numpy as np

from stov_scientist.physics.fields import make_axis, stov_vortex
from stov_scientist.physics.topology import estimate_topological_charge


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--charge", type=int, default=1)
    parser.add_argument("--n", type=int, default=128)
    parser.add_argument("--wx", type=float, default=1e-3)
    parser.add_argument("--wt", type=float, default=1e-12)
    args = parser.parse_args()

    x = make_axis(0.0, 3 * args.wx, args.n)
    t = make_axis(0.0, 3 * args.wt, args.n)
    field = stov_vortex(x, t, args.wx, args.wt, charge=args.charge)
    measured = estimate_topological_charge(field.phase())
    print(
        f"declared charge: {args.charge:+d}  "
        f"measured winding: {measured:+.3f}  "
        f"grid: {args.n}x{args.n}"
    )
    if abs(measured - args.charge) > 0.5:
        print("MISMATCH: measurement outside tolerance (+-0.5)")
        raise SystemExit(1)
    print("OK: winding matches declared charge within tolerance")


if __name__ == "__main__":
    main()
