---
name: stov-wave-propagation
description: STOV wave propagation — angular spectrum (spatial and spatiotemporal), Fresnel paraxial propagation, and the split-step framework with vacuum dispersion.
---

# STOV Wave Propagation

## When to use

- Propagating STOV fields in free space (simulation solvers).
- Choosing between angular spectrum / Fresnel / split-step.

## Solvers (platform: `physics/propagation.py`, `simulation/solvers/`)

| Solver ID | Domain | Notes |
|---|---|---|
| `angular_spectrum_xt` | (x, t) | k_z(ω) = √((ω/c)² − kx²) — full vacuum dispersion; evanescent components damped |
| `angular_spectrum_xy` | (x, y) | monochromatic, k_z = √(k² − kx² − ky²) |
| `fresnel_xy` | (x, y) | paraxial TF form: H = exp(ikz)·exp(−iπλz(fx²+fy²)) |
| `split_step_xt` | (x, t) | split-step framework; linear step = angular spectrum |

## Physics facts (unit-tested)

- Vacuum has NO group-velocity dispersion: the temporal envelope translates
  rigidly (plane-wave limit). Any spreading of a Gaussian *in vacuum* in the
  simulation is numerical, not physical — investigate before concluding.
- Evanescent components must be damped, never amplified.
- Split-step with `nonlinear_phase=None` must match single-shot angular
  spectrum to machine precision (consistency check).

## Rules

- Solver names come from the SolverRegistry only — agents never invent them.
- z must be non-negative for forward propagation.
- Sampling requirements (alias-free bound z ≤ N·dx²/λ) are checked before
  execution — see `stov-optical-sampling`.
- Warnings about evanescent components or alias bounds must propagate into
  the SimulationRun.warnings and the audit bundle.

## References

- `references/propagation-methods.md`
