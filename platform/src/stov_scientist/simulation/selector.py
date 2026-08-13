"""SolverSelector (spec §27).

Inputs: ScientificModelSpec + SimulationSpec (+ optional explicit solver_id).
Output: SolverSelection {solver_id, selection_reason, validity_check, warnings}.

When the spec names a solver explicitly, it is validated — not trusted.
When no solver is valid, solver_id = NO_VALID_SOLVER (spec §27) and the
selection is marked invalid.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from stov_scientist.schemas import ScientificModelSpec, SimulationSpec
from stov_scientist.simulation.registry import SolverRegistry


@dataclass
class ValidityCheck:
    passed: bool
    message: str
    problems: list[str] = field(default_factory=list)


@dataclass
class SolverSelection:
    solver_id: str
    selection_reason: str = ""
    validity_check: ValidityCheck = field(default_factory=lambda: ValidityCheck(False, ""))
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.solver_id != "NO_VALID_SOLVER" and self.validity_check.passed


def _check_required_inputs(
    spec: SimulationSpec, required: tuple[str, ...]
) -> tuple[bool, list[str]]:
    problems: list[str] = []
    for req in required:
        if req == "wavelength":
            if "wavelength" not in spec.parameters:
                problems.append("missing parameter 'wavelength'")
        elif req == "field_kind":
            if "field_kind" not in spec.parameters:
                problems.append("missing parameter 'field_kind'")
        elif req == "grid_xt":
            if tuple(spec.grid.axes) != ("x", "t"):
                problems.append(f"requires (x, t) grid axes, got {tuple(spec.grid.axes)}")
        elif req == "grid_xy":
            if tuple(spec.grid.axes) != ("x", "y"):
                problems.append(f"requires (x, y) grid axes, got {tuple(spec.grid.axes)}")
        elif req == "propagation_distance":
            if "propagation_distance" not in spec.parameters:
                problems.append("missing parameter 'propagation_distance'")
        elif req == "no_nonlinearity":
            if spec.parameters.get("nonlinear_coefficient", 0.0) != 0.0:
                problems.append("solver is linear; nonlinear_coefficient must be 0")
        else:
            if req not in spec.parameters:
                problems.append(f"missing parameter {req!r}")
    return (not problems), problems


def select_solver(
    model: ScientificModelSpec,
    spec: SimulationSpec,
    registry: SolverRegistry,
) -> SolverSelection:
    explicit = spec.solver_id
    if explicit:
        if not registry.has(explicit):
            return SolverSelection(
                solver_id="NO_VALID_SOLVER",
                selection_reason=f"spec names unknown solver {explicit!r}",
                validity_check=ValidityCheck(False, "unknown solver", [explicit]),
            )
        return _validate_candidate(model, spec, registry, explicit)

    candidates = registry.list_for_model_type(model.model_type.value)
    for meta in candidates:
        ok, _ = _check_required_inputs(spec, meta.required_inputs)
        if ok:
            return _validate_candidate(model, spec, registry, meta.solver_id)

    return SolverSelection(
        solver_id="NO_VALID_SOLVER",
        selection_reason=(
            f"no solver supports model_type={model.model_type.value} with "
            f"required inputs for grid axes {tuple(spec.grid.axes)}"
        ),
        validity_check=ValidityCheck(False, "no candidate matched", []),
    )


def _validate_candidate(
    model: ScientificModelSpec,
    spec: SimulationSpec,
    registry: SolverRegistry,
    solver_id: str,
) -> SolverSelection:
    meta = registry.get_metadata(solver_id)
    ok, problems = _check_required_inputs(spec, meta.required_inputs)
    warnings: list[str] = []

    # model-level validity conditions
    for condition in meta.validity_conditions:
        if condition == "paraxial_only" and model.model_type.value == "NUMERICAL":
            # full-wave numerical models are allowed; paraxial solvers warn
            warnings.append(
                f"solver {solver_id} is paraxial; ensure validity domain "
                "covers the paraxial regime"
            )
        if (
            condition == "linear_only"
            and spec.parameters.get("nonlinear_coefficient", 0.0) != 0.0
        ):
            problems.append("solver is linear-only but nonlinear_coefficient != 0")

    if not ok:
        return SolverSelection(
            solver_id="NO_VALID_SOLVER",
            selection_reason=f"candidate {solver_id!r} missing required inputs",
            validity_check=ValidityCheck(False, "; ".join(problems), problems),
            warnings=warnings,
        )
    return SolverSelection(
        solver_id=solver_id,
        selection_reason=(
            f"{solver_id} supports {model.model_type.value} models on "
            f"grid {tuple(spec.grid.axes)}"
        ),
        validity_check=ValidityCheck(True, "solver validity conditions satisfied"),
        warnings=warnings,
    )
