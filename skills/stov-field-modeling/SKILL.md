---
name: stov-field-modeling
description: STOV field modeling — vortex ansatz, Gaussian envelopes, plane waves, normalization. Build OpticalField objects with declared conventions and provenance.
---

# STOV Field Modeling

## When to use

- Building initial fields for STOV simulations.
- Drafting ScientificModelSpec equations for vortex fields.

## Field forms (platform: `physics/fields.py`)

| Builder | Form | Status |
|---|---|---|
| `stov_vortex(x, t, wx, wt, charge)` | E = (x + i·sgn(l)·c₀·t)^|l| · exp(−x²/wx² − t²/wt²) | VALIDATED (Chong 2020 form, spatiotemporal coordinate x + i·c₀·t; limiting cases unit-tested) |
| `spatial_vortex(x, y, wx, wy, charge)` | E = (x + i·sgn(l)·y)^|l| · Gaussian | VALIDATED (standard OAM vortex) |
| `gaussian_envelope(axes, widths)` | exp(−Σ a²/w_a²) | VALIDATED |
| `plane_wave_xt(x, t, kx, omega0)` | exp(i·kx·x − i·ω₀·t) | VALIDATED |

## Rules

- Every field carries `convention_ids` and `source_ids`; check them before use.
- The STOV ansatz is the *linear* model: valid only inside its stated validity
  domain (paraxial, vacuum, alias-free distances).
- Any new field form without a completed source chain must be marked
  CANDIDATE_MODEL and must never feed production conclusions.
- Limiting cases that must hold for the STOV ansatz:
  - t=0 → real envelope;  x=0 → purely imaginary (charge +1)
  - charge 0 → Gaussian envelope
  - charge −1 → complex conjugate of charge +1
- The c₀·t scaling is NOT cosmetic: with bare seconds the vortex core is
  sub-resolution on realistic ps-pulse SI grids and the winding is
  numerically unmeasurable (see `stov-optical-sampling`).

## Workflow

1. Select the builder.
2. State the convention IDs (default: STOV canonical set).
3. Build + verify the limiting cases numerically.
4. Attach provenance (`source_ids`).

## References

- `references/stov-field-forms.md`
