#!/usr/bin/env python3
"""Generate a turbulence phase screen (or ensemble) deterministically.

Usage (from platform/, with stov-scientist installed):
    python ../skills/stov-phase-screen-simulation/scripts/make_phase_screen.py \
        --seed 7 --n 128 --pitch 5e-3 --cn2 1e-14 --l0 1e-3 --L0 10
"""

from __future__ import annotations

import argparse

import numpy as np

from stov_scientist.physics.turbulence import PhaseScreenGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--n", type=int, default=128)
    parser.add_argument("--pitch", type=float, default=5e-3)
    parser.add_argument("--cn2", type=float, default=1e-14)
    parser.add_argument("--l0", type=float, default=1e-3)
    parser.add_argument("--L0", type=float, default=10.0)
    parser.add_argument("--model", default="kolmogorov_vk")
    parser.add_argument("--ensemble", type=int, default=1)
    args = parser.parse_args()

    params = {"cn2": args.cn2, "l0": args.l0, "L0": args.L0}
    generator = PhaseScreenGenerator(model_id=args.model, seed=args.seed)
    screens = generator.generate_ensemble(
        (args.n, args.n), args.pitch, params, n_screens=args.ensemble
    )
    for i, screen in enumerate(screens):
        print(
            f"screen {i}: mean={screen.mean():+.4f} rad "
            f"std={screen.std():.4f} rad peak={np.abs(screen).max():.4f} rad"
        )


if __name__ == "__main__":
    main()
