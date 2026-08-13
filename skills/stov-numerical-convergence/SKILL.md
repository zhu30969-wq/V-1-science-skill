---
name: stov-numerical-convergence
description: Numerical convergence for STOV simulations — grid/step/domain/ensemble refinement against campaign AcceptancePolicy rules. No universal magic thresholds.
---

# STOV Numerical Convergence

## When to use

- Running SimulationSpec convergence plans.
- Interpreting `ConvergenceResult` in the Scientific Judge.

## Framework (platform: `validators/convergence.py`)

- `check_refinement_sequence(values_by_level, rule)` — compares consecutive
  refinement levels against the campaign's ConvergenceRule.
- Strategies: GRID_REFINEMENT, STEP_REFINEMENT, DOMAIN_SENSITIVITY,
  ENSEMBLE_REFINEMENT.

## Rules

- **No universal thresholds** (spec §29): 0.90 / 95% / 1e-6 style constants
  are forbidden. Tolerances come from the campaign AcceptancePolicy
  (`convergence_rules[].target`, `min_refinements`).
- At least `min_refinements` refinement steps must actually run.
- A NOT_CONVERGED result makes the Judge verdict at most INCONCLUSIVE —
  it is not a physical contradiction.
- Refinement levels must be consecutive integers starting at 0.

## Workflow

1. Pick the observable to converge (from `predicted_observables`).
2. Set the campaign rule (metric, target, min_refinements).
3. Run the sequence; record values per level in the SimulationRun.
4. Report `deviation` + verdict; store in the audit bundle.

## References

- `references/convergence-notes.md`
