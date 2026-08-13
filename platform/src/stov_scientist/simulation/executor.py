"""Solver execution dispatcher: (solver object, field, spec) -> PropagationResult.

Solver ids are registry metadata; the dispatch here is the only place that
maps solver_id -> run function. Agents never generate solver names.
"""

from __future__ import annotations

from typing import Any, cast

from stov_scientist.errors import SolverError
from stov_scientist.physics.fields import OpticalField
from stov_scientist.physics.propagation import PropagationResult
from stov_scientist.simulation.solvers.angular_spectrum import run_angular_spectrum
from stov_scientist.simulation.solvers.fresnel import run_fresnel
from stov_scientist.simulation.solvers.split_step import run_split_step


def execute_solver(
    solver_id: str, solver: object, field: OpticalField, spec
) -> PropagationResult:
    s = cast(Any, solver)
    if solver_id in ("angular_spectrum_xt", "angular_spectrum_xy"):
        return run_angular_spectrum(field, spec, s)
    if solver_id == "fresnel_xy":
        return run_fresnel(field, spec, s)
    if solver_id == "split_step_xt":
        return run_split_step(field, spec, s)
    raise SolverError(f"no executor registered for solver_id {solver_id!r}")
