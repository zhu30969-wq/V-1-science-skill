---
name: stov-topology-analysis
description: Phase topology analysis for STOV fields — winding numbers, singularity detection, topological charge estimation. Deterministic NumPy algorithms only.
---

# STOV Topology Analysis

## When to use

- Measuring the topological charge of a simulated or measured (x, t) phase.
- Counterexample search (charge instability checks).
- Benchmark B01/B02/B03 topology checks.

## Algorithms (platform: `physics/topology.py`)

| Function | Purpose |
|---|---|
| `analyze_phase_winding(phase, contour)` | branch-aware winding number q = (1/2π)Σ wrapped phase increments along a closed contour |
| `detect_candidate_singularity(phase)` | 2×2-cell branch-point detection; +1/−1 candidates |
| `estimate_topological_charge(phase, contour=None)` | total charge inside a contour (default: field boundary) |

## Rules

- Winding is a *topological* observable: robust to moderate phase noise;
  metric observables are not.
- The contour must be closed and inside the field.
- Charge measurements from undersampled grids are meaningless — run the
  sampling validator first (see `stov-optical-sampling`).
- A measured charge that differs from the declared charge is a
  *counterexample candidate*, not a falsification until tested per the
  AcceptancePolicy.

## Workflow

1. Extract the phase: `field.phase()`.
2. Run singularity detection (cell level).
3. Integrate winding over a boundary contour.
4. Compare with the declared charge and the convergence tolerance.

## Script

- `scripts/estimate_charge.py` — CLI: estimate the charge of a synthetic
  STOV vortex field.
- `tests/test_estimate_charge.py` — charge +1 / −1 / 0 cases.

## References

- `references/topology-notes.md`
