"""Simulation harness (spec PHASE 7)."""

from stov_scientist.simulation.registry import SolverMetadata, SolverRegistry
from stov_scientist.simulation.runner import SimulationOutcome, SimulationRunner
from stov_scientist.simulation.selector import SolverSelection, select_solver
from stov_scientist.simulation.solvers import default_solver_registry

__all__ = [
    "SimulationOutcome",
    "SimulationRunner",
    "SolverMetadata",
    "SolverRegistry",
    "SolverSelection",
    "default_solver_registry",
    "select_solver",
]
