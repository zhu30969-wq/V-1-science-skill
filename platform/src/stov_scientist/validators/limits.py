"""Parameter limits vs. model validity domain (spec section 13, section 24)."""

from __future__ import annotations

from stov_scientist.schemas import (
    ScientificModelSpec,
    SimulationSpec,
    ValidationLevel,
    ValidationResult,
)


def validate_parameter_limits(
    spec: SimulationSpec, model: ScientificModelSpec, check_id: str = "limits-simulation"
) -> ValidationResult:
    """Every simulation parameter must lie inside the model validity domain.

    A parameter outside the declared domain is a MODEL_DOMAIN_VIOLATION -
    never silently clamped. Non-numeric pipeline control parameters
    (field_kind, turbulence_model, ...) are skipped with a warning.
    """
    problems: list[str] = []
    warnings: list[str] = []
    ranges = model.validity_domain.parameter_ranges
    for symbol, raw_value in spec.parameters.items():
        if not isinstance(raw_value, (int, float)):
            warnings.append(
                f"parameter {symbol!r} is a control parameter ({raw_value!r}); "
                "limits check skipped"
            )
            continue
        value = float(raw_value)
        if symbol not in ranges:
            warnings.append(f"parameter {symbol!r} has no declared range in the validity domain")
            continue
        lo, hi = ranges[symbol]
        if lo is not None and value < lo:
            problems.append(f"{symbol}={value} below domain lower bound {lo}")
        if hi is not None and value > hi:
            problems.append(f"{symbol}={value} above domain upper bound {hi}")
    for symbol in ranges:
        if symbol not in spec.parameters:
            warnings.append(
                f"domain-bound parameter {symbol!r} is not set in the simulation spec"
            )
    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.LIMITS,
        name="parameter limits vs validity domain",
        passed=not problems,
        message="; ".join(problems) if problems else "all bounded parameters inside validity domain",
        warnings=warnings,
        details={"problems": problems},
    )
