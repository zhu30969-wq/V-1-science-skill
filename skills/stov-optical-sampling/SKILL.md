---
name: stov-optical-sampling
description: Optical sampling requirements for STOV grids — Nyquist, FFT consistency, aliasing and the alias-free propagation bound. A sampling failure blocks scientific conclusions.
---

# STOV Optical Sampling

## When to use

- Designing (x, t) grids for STOV simulations.
- Diagnosing SAMPLING_FAILURE classifications from the simulation graph.

## Checks (platform: `validators/sampling.py`)

1. **FFT consistency** — uniform spacing; n·spacing = declared extent.
2. **Nyquist** — declared spectral content must sit below
   f_Nyq = 1/(2·Δ) per axis; <80% margin triggers a warning.
3. **Propagation sampling requirement** (Voelz 2011):
   z ≤ N·Δx²/λ per transverse axis for angular-spectrum/Fresnel-TF solvers.
4. **Verdict** — any failure → SamplingReport.usable_for_conclusions=False.

## Rules

- A sampling failure MUST block scientific conclusions (spec §26). The
  contradiction graph classifies it SAMPLING_FAILURE → redesign sampling →
  rerun. It is never a physical contradiction.
- Charge/topology measurements on undersampled grids are meaningless.
- Retry refinement doubles the transverse grid per retry (bounded by
  AcceptancePolicy.max_simulation_retries).

## Workflow

1. Declare grid shape/spacing/extent + spectral content.
2. Run `validate_sampling(spec, propagation_distance, wavelength)`.
3. On failure: redesign the grid — never interpret the physics as wrong.

## References

- `references/sampling-requirements.md`
