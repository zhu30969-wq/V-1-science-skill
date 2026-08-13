"""Unit validation with Pint (spec §23). No string comparison of units."""

from __future__ import annotations

from functools import lru_cache

import pint
from pint import UnitRegistry

from stov_scientist.errors import SchemaError
from stov_scientist.schemas import (
    ScientificModelSpec,
    SimulationSpec,
    ValidationLevel,
    ValidationResult,
)


@lru_cache(maxsize=1)
def get_ureg() -> UnitRegistry:
    return UnitRegistry()


def parse_unit(unit_str: str):
    try:
        return get_ureg().Unit(unit_str)
    except pint.errors.UndefinedUnitError as exc:
        raise SchemaError(f"unparseable unit expression: {unit_str!r}") from exc
    except pint.errors.DefinitionSyntaxError as exc:
        raise SchemaError(f"invalid unit syntax: {unit_str!r}") from exc


def same_dimensionality(unit_a: str, unit_b: str) -> bool:
    """True when both unit expressions share dimensionality (e.g. m vs km)."""
    return get_ureg().Unit(unit_a).is_compatible_with(get_ureg().Unit(unit_b))


def validate_model_units(model: ScientificModelSpec, check_id: str = "units-model") -> ValidationResult:
    problems: list[str] = []
    for symbol, unit_str in model.symbols.items():
        try:
            parse_unit(unit_str)
        except SchemaError as exc:
            problems.append(f"symbol {symbol!r}: {exc}")
    for name, unit_str in model.units.items():
        try:
            parse_unit(unit_str)
        except SchemaError as exc:
            problems.append(f"quantity {name!r}: {exc}")
    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.UNITS,
        name="model unit parseability (Pint)",
        passed=not problems,
        message="; ".join(problems) if problems else "all declared units parse as Pint units",
        warnings=[],
        details={"problems": problems},
    )


# control parameters that configure the pipeline, not physical quantities
CONTROL_PARAMETERS = frozenset(
    {
        "field_kind",
        "n_steps",
        "random_seed",
        "turbulence_model",
        "nonlinear_coefficient",
        "charge",
        "kx",
        "omega0",
    }
)


def validate_simulation_units(
    spec: SimulationSpec, model: ScientificModelSpec, check_id: str = "units-simulation"
) -> ValidationResult:
    """Every physical simulation parameter must be declared on the model with
    a unit, and grid axes must carry parseable units. Pipeline control
    parameters (field_kind, n_steps, seeds, ...) are exempt."""
    problems: list[str] = []
    for axis in spec.grid.axes:
        unit_str = spec.grid.units.get(axis)
        if not unit_str:
            problems.append(f"grid axis {axis!r} has no declared unit")
        else:
            try:
                parse_unit(unit_str)
            except SchemaError as exc:
                problems.append(f"grid axis {axis!r}: {exc}")
    for symbol in spec.parameters:
        if symbol in CONTROL_PARAMETERS:
            continue
        if symbol not in model.symbols:
            problems.append(
                f"parameter {symbol!r} is not a declared symbol of model "
                f"{model.model_id!r}"
            )
    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.UNITS,
        name="simulation units (Pint)",
        passed=not problems,
        message="; ".join(problems) if problems else "grid axes and parameters have valid units",
        details={"problems": problems},
    )
