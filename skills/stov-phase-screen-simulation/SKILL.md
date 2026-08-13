---
name: stov-phase-screen-simulation
description: Phase screen simulation for STOV turbulence studies — FFT method with subharmonics (Lane 1992), deterministic seeds, ensemble generation and variance normalization.
---

# STOV Phase Screen Simulation

## When to use

- Generating Kolmogorov/other-turbulence phase screens.
- Ensemble turbulence studies for STOV propagation.

## Method (platform: `physics/turbulence.py`)

1. Compute the spectrum on the FFT frequency grid.
2. Multiply by complex unit-variance Gaussian noise (deterministic RNG).
3. Inverse FFT → real phase screen.
4. Normalize to the target variance (thin-layer scaling with Δz when given).

Subharmonic low-frequency correction follows Lane et al. (1992); the v1
implementation uses the base FFT method with variance normalization —
low-frequency subharmonic augmentation is tracked as a known limitation.

## Rules

- Always record: model id, Cn², l0, L0, grid, pitch, seed, Δz.
- Never reuse the same seed for different "independent" ensemble members.
- A screen is only meaningful inside the model's parameter validity.
- Turbulent screens alone never falsify a hypothesis — they are stochastic
  uncertainty (see `stov-atmospheric-turbulence`).

## Script

- `scripts/make_phase_screen.py` — CLI: one screen or an ensemble.
- `tests/test_make_phase_screen.py` — determinism, variance, validation.

## References

- `references/phase-screen-method.md`
