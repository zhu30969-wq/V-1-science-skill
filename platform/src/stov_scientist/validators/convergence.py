"""Numerical convergence framework (spec §29).

No global magic thresholds (no hard-coded 0.90 / 1e-6): every tolerance
comes from a campaign AcceptancePolicy convergence rule.
"""

from __future__ import annotations

from itertools import pairwise

from stov_scientist.errors import SchemaError
from stov_scientist.schemas import (
    ConvergenceResult,
    ConvergenceRule,
    ValidationLevel,
    ValidationResult,
)


def relative_change(a: float, b: float) -> float | None:
    """Relative change between two refinement levels; None when undefinable."""
    denom = max(abs(a), abs(b))
    if denom == 0:
        return 0.0 if a == b else None
    return abs(a - b) / denom


def check_refinement_sequence(
    values_by_level: dict[int, float],
    rule: ConvergenceRule,
    check_id: str = "convergence-grid",
) -> tuple[ValidationResult, ConvergenceResult]:
    """Compare consecutive refinement levels against the campaign rule.

    ``values_by_level``: refinement level (0 = coarsest) -> observable value.
    Levels must be consecutive integers starting at 0.
    """
    levels = sorted(values_by_level)
    if not levels:
        raise SchemaError("values_by_level is empty")
    if levels[0] != 0 or levels != list(range(len(levels))):
        raise SchemaError(f"refinement levels must be 0..N consecutive, got {levels}")
    if len(levels) - 1 < rule.min_refinements:
        message = (
            f"only {len(levels) - 1} refinement step(s) performed; "
            f"rule {rule.rule_id!r} requires >= {rule.min_refinements}"
        )
        convergence = ConvergenceResult(
            achieved=False,
            metric_name=rule.metric,
            refinement_levels=levels,
            values=dict(values_by_level),
            verdict="INSUFFICIENT_REFINEMENTS",
        )
        return (
            ValidationResult(
                check_id=check_id,
                level=ValidationLevel.SAMPLING,
                name="refinement convergence vs AcceptancePolicy",
                passed=False,
                message=message,
                details={"rule": rule.model_dump()},
            ),
            convergence,
        )

    worst = 0.0
    for a, b in pairwise(levels):
        rc = relative_change(values_by_level[b], values_by_level[a])
        if rc is None:
            worst = float("inf")
            break
        worst = max(worst, rc)
    achieved = bool(np_isfinite(worst) and worst <= rule.target)
    convergence = ConvergenceResult(
        achieved=achieved,
        metric_name=rule.metric,
        refinement_levels=levels,
        values=dict(values_by_level),
        deviation=worst if np_isfinite(worst) else None,
        verdict="CONVERGED" if achieved else "NOT_CONVERGED",
    )
    return (
        ValidationResult(
            check_id=check_id,
            level=ValidationLevel.SAMPLING,
            name="refinement convergence vs AcceptancePolicy",
            passed=achieved,
            message=(
                f"worst relative change {worst:.3g} vs rule target {rule.target:.3g} "
                f"(metric: {rule.metric})"
            ),
            details={"rule": rule.model_dump(), "values": values_by_level},
        ),
        convergence,
    )


def np_isfinite(x: float) -> bool:
    import math

    return math.isfinite(x)
