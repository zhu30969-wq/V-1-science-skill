"""Deterministic SimulationSpec builder (research graph: simulation_planning).

Grid/parameters come from the model's numerical assumptions and the problem
constraints — never invented by an agent.
"""

from __future__ import annotations

import numpy as np

from stov_scientist.schemas import (
    AcceptancePolicy,
    ConvergencePlan,
    GridSpec,
    ResearchProblem,
    ResourceLimits,
    ScientificModelSpec,
    SimulationSpec,
    UncertaintyPlan,
)


def build_simulation_spec(
    model: ScientificModelSpec,
    problem: ResearchProblem,
    *,
    simulation_id: str,
    policy: AcceptancePolicy | None = None,
    parameters: dict[str, float | str] | None = None,
    random_seed: int = 0,
    ensemble_size: int = 1,
) -> SimulationSpec:
    params = dict(parameters or {})
    params.setdefault("wavelength", 800e-9)
    # 0.05 m keeps N=128 grids inside the alias-free bound for mm-scale
    # envelope widths (z_max ~ 36 wx^2 / (N lambda), Voelz 2011)
    params.setdefault("propagation_distance", 0.05)
    params.setdefault("field_kind", "stov_vortex_xt")
    # envelope-representation carrier: without it the envelope is baseband
    # and all spatial structure is evanescent (near-field, not propagation)
    from stov_scientist.physics.constants import SPEED_OF_LIGHT

    params.setdefault("carrier_omega", 2 * np.pi * SPEED_OF_LIGHT / float(params["wavelength"]))
    params.setdefault("wt", 1e-3 / SPEED_OF_LIGHT)

    # grid from validity domain / defaults
    wx = float(params.get("wx", 1e-3))
    # isotropic spatiotemporal envelope (c0*wt = wx): the linear STOV
    # vortex only propagates stably when the envelope is isotropic in the
    # (x, c0*t) plane (see model template validity domain)
    wt = float(params.get("wt", 1e-3 / SPEED_OF_LIGHT))
    nx = int(params.get("nx", 128))
    nt = int(params.get("nt", 128))
    x_half = 3 * wx
    t_half = 3 * wt
    grid = GridSpec(
        grid_id=f"grid-{simulation_id}",
        kind="x-t",
        axes=["x", "t"],
        shape=[nx, nt],
        spacing={"x": 2 * x_half / nx, "t": 2 * t_half / nt},
        domain_extent={"x": 2 * x_half, "t": 2 * t_half},
        units={"x": "m", "t": "s"},
    )

    params["wx"] = wx
    params["wt"] = wt
    params["n_steps"] = int(params.get("n_steps", 10))

    # Energy is the convergence target: it is exactly conserved in vacuum
    # propagation. (Topological charge of the propagated STOV is NOT a
    # stable observable — the vacuum wave equation in the local-time frame
    # splits the vortex into a +1/-1 pair; the platform measures and
    # reports this real effect rather than asserting charge stability.)
    convergence_plan = ConvergencePlan(
        strategy="GRID_REFINEMENT",
        refinement_levels=[0, 1],
        target_observable="energy",
        acceptance_rule=(
            policy.convergence_rules[0].rule_id
            if policy and policy.convergence_rules
            else "default-convergence"
        ),
    )
    uncertainty_plan = UncertaintyPlan(
        numerical_uncertainty=True,
        numerical_method="grid_refinement_deviation",
        stochastic_uncertainty=ensemble_size > 1,
        ensemble_sizes=[ensemble_size] if ensemble_size > 1 else [],
    )

    return SimulationSpec(
        simulation_id=simulation_id,
        model_id=model.model_id,
        domain="free space vacuum propagation",
        grid=grid,
        parameters=params,
        random_seed=random_seed,
        ensemble_size=ensemble_size,
        convergence_plan=convergence_plan,
        uncertainty_plan=uncertainty_plan,
        expected_observables=list(model.predicted_observables),
        resource_limits=ResourceLimits(max_artifacts=10),
    )
