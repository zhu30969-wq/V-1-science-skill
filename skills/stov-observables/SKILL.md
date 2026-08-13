---
name: stov-observables
description: STOV observable extraction — intensity, phase, centroid, local frequencies, spectral density, topological charge proxy and (CANDIDATE_MODEL) transverse OAM moments.
---

# STOV Observables

## When to use

- Extracting quantitative observables from simulated fields.
- Building convergence targets for SimulationSpec.
- Evaluating declared predictions.

## Observables (platform: `physics/observables.py`)

| Observable | Function | Status |
|---|---|---|
| intensity | `intensity(field)` = |E|² | VALIDATED |
| phase | `phase(field)` = arg(E) | VALIDATED |
| centroid | `centroid(field)` | VALIDATED |
| local frequency | `local_frequency(field, axis)` | VALIDATED (finite differences) |
| spectral density | `on_axis_spectral_density(field, axis)` | VALIDATED |
| topological charge | `transverse_oam_proxy(field)` (winding-based) | VALIDATED (topological observable) |
| transverse OAM moment | `transverse_oam_moment_xt(field)` | **CANDIDATE_MODEL** (Bliokh & Nori 2012; normalization not validated) |

## Rules

- The charge proxy is a *topological* observable — it is not an OAM moment.
- OAM moment integrals carry convention-dependent prefactors; in this
  platform they are CANDIDATE_MODEL and never used as primary judge evidence.
- Observables are extracted from artifacts (never from graph state).
- Every observable used in a claim must trace back to a SimulationRun ID.

## Workflow

1. `extract(field)` → Observables bundle.
2. Persist as OBSERVABLES_JSON artifact with SHA256.
3. Use only in convergence/uncertainty/judgement contexts, with the run ID.

## References

- `references/observable-definitions.md`
