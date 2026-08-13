---
name: stov-optical-conventions
description: STOV optical convention registry — coordinate, Fourier, temporal, phase-sign, normalization and unit conventions for space-time optical vortex research. Use before transcribing or combining ANY equation from the literature.
---

# STOV Optical Conventions

## When to use

- Before writing any STOV equation into a ScientificModelSpec.
- Before combining equations from different papers (conventions must align first).
- When a validation fails with dimensional or sign anomalies.

## Conventions (canonical set)

| Convention ID | Category | Definition |
|---|---|---|
| `coord_xyt_z_prop` | coordinate | STOV transverse plane (x, t); propagation +z; y = transverse-OAM axis |
| `coord_xy_z_prop` | coordinate | spatial transverse plane (x, y); propagation +z |
| `ft_space_exp_neg` | fourier_transform | forward spatial FT with exp(-i 2π f_x x) (Goodman §3.1 sign) |
| `ft_time_exp_pos` | fourier_transform | u(t) = (1/2π)∫ U(ω) exp(-iωt) dω |
| `harmonic_exp_neg_iwt` | temporal_frequency | time-harmonic fields exp(-iωt) |
| `phase_sign_stov_xt` | phase_sign | charge +1 STOV phase φ = atan2(t, x) |
| `phase_sign_oam_xy` | phase_sign | charge +1 spatial vortex phase φ = atan2(y, x) |
| `norm_unity_l2` | normalization | optional unit-L2 normalization for comparisons |
| `units_si` | unit_system | SI via Pint; every quantity carries explicit units |

## Workflow

1. Identify the source paper and its own conventions.
2. Map them into the registry (only registered convention IDs may be cited in `ModelSpec.convention_ids`).
3. Transcribe the equation in the registry's convention frame.
4. Run the deterministic validator chain (schema → units → dimensions → symbols → limits → boundary).
5. Check at least one known limiting case with a unit test.

## Rules

- Never mix equations from different papers without convention alignment.
- Never invent a convention ID — the registry is closed (code: `physics/conventions.py`).
- If no authoritative source exists for a convention variant, mark the result CANDIDATE_MODEL.

## References

- `references/primary-sources.md`
