"""Solver implementations registered against the SolverRegistry."""

from stov_scientist.simulation.registry import SolverRegistry
from stov_scientist.simulation.solvers.angular_spectrum import register_angular_spectrum_solvers
from stov_scientist.simulation.solvers.fresnel import register_fresnel_solvers
from stov_scientist.simulation.solvers.split_step import register_split_step_solvers


def default_solver_registry() -> SolverRegistry:
    """Registry with all built-in solvers registered."""
    registry = SolverRegistry()
    register_angular_spectrum_solvers(registry)
    register_fresnel_solvers(registry)
    register_split_step_solvers(registry)
    return registry
