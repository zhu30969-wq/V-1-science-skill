---
name: stov-atmospheric-turbulence
description: Atmospheric turbulence for STOV propagation — turbulence model registry (von Kármán, Tatarskii), parameter validation, ensemble generation. No single hard-coded spectrum.
---

# STOV Atmospheric Turbulence

## When to use

- Adding turbulent phase perturbations to STOV propagation studies.
- Comparing turbulence models (the registry exists so that NO single
  spectrum is treated as "the" turbulence model).

## Models (platform: `physics/turbulence.py`)

| Model ID | Spectrum | Parameters |
|---|---|---|
| `kolmogorov_vk` | Φn(κ) = 0.033·Cn²·exp(−κ²/κm²)/(κ²+κ₀²)^(11/6) (modified von Kármán) | Cn², l0, L0 |
| `tatarskii` | Φn(κ) = 0.033·Cn²·κ^(−11/3)·exp(−κ²/κm²) | Cn², l0 |

κm = 5.92/l0; κ₀ = 2π/L0 (Andrews & Phillips 2005 ch. 3).

## Rules

- `validate_parameters()` runs before any screen: Cn² > 0, l0 > 0, L0 > l0.
- Phase screens are deterministic for a fixed random seed — record the seed
  in the artifact metadata (reproducibility, spec §49).
- An ensemble is generated with the same RNG stream: seeds differ per member.
- Turbulence is a *stochastic* uncertainty source — report it under
  `stochastic_uncertainty`, never as a physical contradiction.

## Workflow

1. Pick the model from the registry (justify the choice).
2. Validate parameters.
3. Generate phase screen(s) with a recorded seed.
4. Apply to the field; propagate; record seeds + model id in artifacts.

## References

- `references/turbulence-models.md`
