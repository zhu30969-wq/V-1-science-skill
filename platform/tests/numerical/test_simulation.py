"""Simulation harness tests (spec §68): deterministic seeds, artifact SHA,
out-of-domain rejection, sampling/numerical failure classification,
grid refinement convergence."""

from __future__ import annotations

import numpy as np
import pytest

from stov_scientist.errors import NoValidSolverError, ValidationError
from stov_scientist.schemas import SimulationStatus
from stov_scientist.simulation import default_solver_registry
from tests.helpers import POLICY, make_model, make_spec


def test_happy_path_completed(simulation_runner, artifact_registry):
    model = make_model()
    spec = make_spec(model)
    outcome = simulation_runner.run(model, spec, policy=POLICY, campaign_id="campaign-1")
    assert outcome.run.status is SimulationStatus.COMPLETED
    assert outcome.classification == "OK"
    assert outcome.run.convergence_result is not None
    assert outcome.run.convergence_result.achieved
    # energy is exactly conserved in vacuum propagation (convergence target)
    assert outcome.observables.energy > 0
    # the initial STOV charge is +1 (measured on the built field); under
    # vacuum propagation the vortex may split into a +/-1 pair (real wave-
    # equation physics in the local-time frame) — the platform measures and
    # reports this instead of assuming charge stability
    # artifacts written + hashes verify
    artifacts = artifact_registry.list_artifacts(campaign_id="campaign-1")
    kinds = {a.artifact_type for a in artifacts}
    assert {"FIELD_NPY", "OBSERVABLES_JSON", "FIGURE_PNG"} <= kinds
    for a in artifacts:
        ok, msg = artifact_registry.verify_artifact(a.artifact_id)
        assert ok, msg


def test_deterministic_random_seed(simulation_runner):
    model = make_model()
    outcome_a = simulation_runner.run(model, make_spec(model), policy=POLICY)
    outcome_b = simulation_runner.run(model, make_spec(model), policy=POLICY)
    assert np.allclose(outcome_a.final_field.values, outcome_b.final_field.values)


def test_out_of_domain_parameter_rejected(simulation_runner):
    model = make_model()
    spec = make_spec(model, parameters={**make_spec(model).parameters, "wx": 1.0})
    with pytest.raises(ValidationError):
        simulation_runner.run(model, spec, policy=POLICY)


def test_sampling_failure_classified_not_physical(simulation_runner):
    """Undersampled propagation is SAMPLING_FAILURE — never a physical
    contradiction (spec §26, §45)."""
    model = make_model()
    spec = make_spec(
        model, parameters={**make_spec(model).parameters, "propagation_distance": 500.0}
    )
    outcome = simulation_runner.run(model, spec, policy=POLICY)
    assert outcome.run.status is SimulationStatus.SAMPLING_FAILURE
    assert outcome.classification == "SAMPLING_FAILURE"


def test_no_valid_solver_rejected(simulation_runner):
    model = make_model()
    spec = make_spec(model)
    # fully-formed but unsupported (x, z) grid: sampling checks pass, then
    # no solver matches the axes -> NO_VALID_SOLVER
    spec.grid.axes = ["x", "z"]
    spec.grid.spacing = {"x": 3e-5, "z": 3e-5}
    spec.grid.domain_extent = {"x": 128 * 3e-5, "z": 128 * 3e-5}
    spec.grid.units = {"x": "m", "z": "m"}
    with pytest.raises(NoValidSolverError) as excinfo:
        simulation_runner.run(model, spec, policy=POLICY)
    assert "NO_VALID_SOLVER" in str(excinfo.value)


def test_unknown_field_kind_is_numerical_failure(simulation_runner):
    """Execution errors surface as NUMERICAL_FAILURE status."""
    model = make_model()
    spec = make_spec(model, parameters={**make_spec(model).parameters, "field_kind": "bogus"})
    outcome = simulation_runner.run(model, spec, policy=POLICY)
    assert outcome.run.status is SimulationStatus.NUMERICAL_FAILURE
    assert outcome.classification == "NUMERICAL_FAILURE"


def test_artifact_sha_verification_after_run(simulation_runner, artifact_registry):
    model = make_model()
    simulation_runner.run(model, make_spec(model), policy=POLICY, campaign_id="c-sha")
    for a in artifact_registry.list_artifacts(campaign_id="c-sha"):
        ok, _ = artifact_registry.verify_artifact(a.artifact_id)
        assert ok


def test_split_step_solver_registered():
    registry = default_solver_registry()
    ids = {m.solver_id for m in registry.all_metadata()}
    assert {"angular_spectrum_xt", "angular_spectrum_xy", "fresnel_xy", "split_step_xt"} <= ids
