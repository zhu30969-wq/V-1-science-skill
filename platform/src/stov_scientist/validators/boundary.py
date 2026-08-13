"""Initial/boundary condition validation (spec §13, §22)."""

from __future__ import annotations

from stov_scientist.schemas import (
    ScientificModelSpec,
    SimulationSpec,
    ValidationLevel,
    ValidationResult,
)

_FFT_BASED_KINDS = ("FFT", "ANGULAR_SPECTRUM", "FRESNEL_TF", "SPLIT_STEP")


def validate_boundary_conditions(
    model: ScientificModelSpec,
    spec: SimulationSpec | None = None,
    check_id: str = "boundary-model",
) -> ValidationResult:
    """Every dependent variable needs an initial condition expression, and
    boundary conditions must be declared for the model domain.

    FFT-based solvers require periodic BCs on transverse grids — anything
    else produces a warning (not a failure: absorbing BCs may be valid for
    non-FFT solvers).
    """
    problems: list[str] = []
    warnings: list[str] = []

    ic_vars = {ic.variable for ic in model.initial_conditions}
    missing_ic = [v for v in model.dependent_variables if v not in ic_vars]
    if missing_ic:
        problems.append(f"dependent variables without initial condition: {missing_ic}")

    if not model.boundary_conditions and model.dependent_variables:
        warnings.append("no explicit boundary conditions declared on the model")

    if spec is not None:
        for solver_kind in _FFT_BASED_KINDS:
            if solver_kind in (spec.solver_id or "").upper() or solver_kind in spec.grid.kind.upper():
                for bc in model.boundary_conditions:
                    if bc.kind.upper() not in ("PERIODIC",):
                        warnings.append(
                            f"BC {bc.bc_id!r} kind={bc.kind!r}: FFT-based solvers "
                            "implicitly assume periodic boundary conditions"
                        )

    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.BOUNDARY,
        name="initial/boundary condition completeness",
        passed=not problems,
        message="; ".join(problems) if problems else "ICs/BCs complete",
        warnings=warnings,
        details={"missing_initial_conditions": missing_ic},
    )
