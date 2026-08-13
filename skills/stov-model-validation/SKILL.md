---
name: stov-model-validation
description: STOV model validation methodology — the mandatory source chain for any STOV equation: primary source → reference record → convention → transcription → unit/dim check → limiting case → unit test → production.
---

# STOV Model Validation

## When to use

- Before ANY STOV-specific equation enters production physics code.
- Counterexample worker runs (this skill is in its skill set).
- Auditing a ScientificModelSpec.

## The source chain (spec §20)

1. **Primary/authoritative source** located and recorded (Reference Record).
2. **Convention identified** — mapped into the Convention Registry.
3. **Equation transcribed** in the registry frame.
4. **Unit/dimension check** — Pint + SymPy deterministic validation.
5. **Known limiting case** — at least one analytic limit evaluated.
6. **Unit test** — the limiting case encoded as a test.
7. **Production physics module** — only then VALIDATED.

No source → **CANDIDATE_MODEL**. A CANDIDATE_MODEL equation must never be
treated as a validated model and cannot support a SUPPORTED_WITHIN_SCOPE
claim on physics content alone.

## Validation vocabulary

- LLM output ≠ evidence. Model ≠ hypothesis. Simulation ≠ experiment.
- Numerical failure ≠ physical contradiction.
- INCONCLUSIVE is a valid outcome.

## Workflow

1. Check the equation's `status` field (VALIDATED / CANDIDATE_MODEL).
2. Run `run_validators(model, context)` (schema → units → dimensions →
   symbols → limits → boundary).
3. Run the model through the counterexample worker (boundary cases +
   numerical stress).
4. Only validated + converged + uncontradicted content may reach the
   Scientific Judge with positive claims.

## References

- `references/validation-methodology.md`
