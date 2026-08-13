"""SimulationRunner (spec §28): the SimulationPlan workflow.

    Schema Validation -> Solver Selection -> Validity Check ->
    Sampling Validation -> Resource Check -> Execution -> Convergence ->
    Uncertainty -> Observable Extraction -> Artifact Registry

Failures are classified (spec PHASE 11): SAMPLING_FAILURE and
NUMERICAL_FAILURE are reported as SimulationRun statuses — never as
physical contradictions. Hard contract violations raise ValidationError /
NoValidSolverError for the control plane to route.
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass

import numpy as np

from stov_scientist.artifacts.registry import ArtifactRegistry
from stov_scientist.errors import (
    NoValidSolverError,
    SchemaError,
    SimulationError,
    ValidationError,
)
from stov_scientist.physics.field_builders import build_initial_field
from stov_scientist.physics.observables import Observables, extract
from stov_scientist.schemas import (
    AcceptancePolicy,
    ConvergenceResult,
    RuntimeMetadata,
    ScientificModelSpec,
    SimulationRun,
    SimulationSpec,
    SimulationStatus,
    UncertaintyResult,
    ValidationLevel,
    utcnow,
)
from stov_scientist.simulation.executor import execute_solver
from stov_scientist.simulation.registry import SolverRegistry
from stov_scientist.simulation.selector import SolverSelection, select_solver
from stov_scientist.validators import ValidatorContext, run_validators
from stov_scientist.validators.convergence import check_refinement_sequence
from stov_scientist.validators.sampling import validate_sampling


@dataclass
class SimulationOutcome:
    run: SimulationRun
    solver_selection: SolverSelection
    final_field: object | None = None
    observables: Observables | None = None
    sampling_report_id: str | None = None
    classification: str = "OK"  # OK / SAMPLING_FAILURE / NUMERICAL_FAILURE / RESOURCE_LIMIT


class SimulationRunner:
    def __init__(
        self,
        registry: SolverRegistry,
        artifacts: ArtifactRegistry,
    ) -> None:
        self.registry = registry
        self.artifacts = artifacts

    # ------------------------------------------------------------------ API
    def run(
        self,
        model: ScientificModelSpec,
        spec: SimulationSpec,
        policy: AcceptancePolicy | None = None,
        campaign_id: str = "unnamed",
    ) -> SimulationOutcome:
        started = time.monotonic()

        # 1. Schema validation
        context = ValidatorContext(models={model.model_id: model})
        report = run_validators(spec, context)
        failing = [r for r in report.failed if r.level is ValidationLevel.SAMPLING]
        if report.failed and not failing:
            raise ValidationError(
                f"simulation spec {spec.simulation_id} failed validation: "
                + "; ".join(r.message for r in report.failed)
            )
        if failing:
            return self._outcome_failure(
                spec, model, SimulationStatus.SAMPLING_FAILURE, "SAMPLING_FAILURE",
                "; ".join(r.message for r in failing), None,
            )

        # 2-3. Solver selection + validity
        selection = select_solver(model, spec, self.registry)
        if not selection.is_valid:
            raise NoValidSolverError(
                f"NO_VALID_SOLVER for {spec.simulation_id}: {selection.selection_reason}"
            )
        entry = self.registry.get(selection.solver_id)
        solver = entry.build(spec)

        # 4. Sampling validation (propagation-specific)
        params = dict(spec.parameters)
        z_raw = params.get("propagation_distance")
        wl_raw = params.get("wavelength")
        z = float(z_raw) if z_raw is not None else None
        wavelength = float(wl_raw) if wl_raw is not None else None
        sampling_result, sampling_report = validate_sampling(
            spec, propagation_distance=z, wavelength=wavelength
        )
        if not sampling_result.passed:
            return self._outcome_failure(
                spec, model, SimulationStatus.SAMPLING_FAILURE, "SAMPLING_FAILURE",
                sampling_result.message, selection,
            )

        # 5. Resource check
        if spec.resource_limits.max_artifacts and spec.resource_limits.max_artifacts < 1:
            return self._outcome_failure(
                spec, model, SimulationStatus.RESOURCE_LIMIT, "RESOURCE_LIMIT",
                "max_artifacts < 1", selection,
            )

        # 6. Execution
        try:
            base_field = self._build_field(spec)
            propagation = execute_solver(selection.solver_id, solver, base_field, spec)
        except (SimulationError, SchemaError, ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
            return self._outcome_failure(
                spec, model, SimulationStatus.NUMERICAL_FAILURE, "NUMERICAL_FAILURE",
                f"{type(exc).__name__}: {exc}", selection,
            )

        # 7. Convergence
        convergence: ConvergenceResult | None = None
        if policy is not None:
            try:
                convergence = self._convergence(
                    spec, selection.solver_id, solver, policy
                )
            except (SimulationError, SchemaError) as exc:
                return self._outcome_failure(
                    spec, model, SimulationStatus.NUMERICAL_FAILURE, "NUMERICAL_FAILURE",
                    str(exc), selection,
                )

        # 8. Uncertainty
        uncertainty = self._uncertainty(spec, selection.solver_id, solver, policy)

        # 9. Observable extraction + 10. artifacts
        observables = extract(propagation.field)
        self._register_artifacts(campaign_id, spec, selection, propagation.field, observables, uncertainty)

        duration = time.monotonic() - started
        now = utcnow()
        run = SimulationRun(
            run_id=f"run-{spec.simulation_id}",
            simulation_spec_id=spec.simulation_id,
            status=SimulationStatus.COMPLETED,
            runtime_metadata=RuntimeMetadata(
                started_at=now,
                finished_at=now,
                duration_seconds=round(duration, 4),
            ),
            solver_version=entry.metadata.version,
            python_version=_python_version(),
            random_seed=spec.random_seed,
            convergence_result=convergence,
            uncertainty_result=uncertainty,
            warnings=list(propagation.warnings) + selection.warnings,
        )
        return SimulationOutcome(
            run=run,
            solver_selection=selection,
            final_field=propagation.field,
            observables=observables,
            sampling_report_id=sampling_report.sampling_report_id,
            classification="OK",
        )

    # ------------------------------------------------------------ internals
    def _outcome_failure(
        self,
        spec: SimulationSpec,
        model: ScientificModelSpec,
        status: SimulationStatus,
        classification: str,
        message: str,
        selection: SolverSelection | None,
    ) -> SimulationOutcome:
        run = SimulationRun(
            run_id=f"run-{spec.simulation_id}",
            simulation_spec_id=spec.simulation_id,
            status=status,
            errors=[message],
            solver_version=selection.solver_id if selection else "",
            python_version=_python_version(),
            random_seed=spec.random_seed,
        )
        return SimulationOutcome(run=run, solver_selection=selection or SolverSelection("NO_VALID_SOLVER"), classification=classification)

    def _build_field(self, spec: SimulationSpec):
        grid = spec.grid
        return build_initial_field(
            field_kind=str(spec.parameters["field_kind"]),
            spec_axes=tuple(grid.axes),
            spec_shape=tuple(grid.shape),
            spacing=dict(grid.spacing),
            extent=dict(grid.domain_extent),
            params=dict(spec.parameters),
        )

    def _convergence(
        self,
        spec: SimulationSpec,
        solver_id: str,
        solver: object,
        policy: AcceptancePolicy,
    ) -> ConvergenceResult:
        plan = spec.convergence_plan
        rule = _find_rule(policy, plan.acceptance_rule)
        levels = plan.refinement_levels or [0, 1]
        values: dict[int, float] = {}
        for level in levels:
            level_spec = _refined_spec(spec, level, strategy=str(plan.strategy))
            field = self._build_field(level_spec)
            result = execute_solver(solver_id, solver, field, level_spec)
            values[level] = _target_observable(result.field, plan.target_observable)
        _, convergence = check_refinement_sequence(values, rule)
        return convergence

    def _uncertainty(
        self,
        spec: SimulationSpec,
        solver_id: str,
        solver: object,
        policy: AcceptancePolicy | None,
    ) -> UncertaintyResult:
        plan = spec.uncertainty_plan
        result = UncertaintyResult()
        if plan.stochastic_uncertainty and spec.ensemble_size > 1:
            target = spec.convergence_plan.target_observable
            samples: list[float] = []
            for i in range(spec.ensemble_size):
                seed = (spec.random_seed or 0) + i
                ens_spec = spec.model_copy(update={"random_seed": seed})
                field = self._build_field(ens_spec)
                res = execute_solver(solver_id, solver, field, ens_spec)
                samples.append(_target_observable(res.field, target))
            result.stochastic_uncertainty = {
                "std": float(np.std(samples)),
                "mean": float(np.mean(samples)),
                "n": len(samples),
            }
        if plan.numerical_uncertainty:
            result.numerical_uncertainty = {
                "method": plan.numerical_method or "grid_refinement_deviation",
                "note": "deviation computed in convergence step (spec §30)",
            }
        return result

    def _register_artifacts(
        self,
        campaign_id: str,
        spec: SimulationSpec,
        selection: SolverSelection,
        field: object,
        observables: Observables,
        uncertainty: UncertaintyResult,
    ) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import orjson

        field_values = field.values  # type: ignore[attr-defined]
        npy_buffer = io.BytesIO()
        np.save(npy_buffer, field_values, allow_pickle=False)
        self.artifacts.register_artifact(
            campaign_id=campaign_id,
            artifact_type="FIELD_NPY",
            artifact_id=f"field-{spec.simulation_id}",
            payload=npy_buffer.getvalue(),
            random_seed=spec.random_seed,
            parameters=dict(spec.parameters),
        )
        obs_payload = orjson.dumps(observables.as_dict(), option=orjson.OPT_INDENT_2)
        self.artifacts.register_artifact(
            campaign_id=campaign_id,
            artifact_type="OBSERVABLES_JSON",
            artifact_id=f"observables-{spec.simulation_id}",
            payload=obs_payload,
            random_seed=spec.random_seed,
            parameters=dict(spec.parameters),
        )
        fig, ax = plt.subplots(figsize=(6, 4))
        im = ax.imshow(field.intensity(), origin="lower", cmap="inferno")  # type: ignore[attr-defined]
        fig.colorbar(im, ax=ax, label="|E|^2 (a.u.)")
        ax.set_title(f"{spec.simulation_id} ({selection.solver_id})")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110)
        plt.close(fig)
        self.artifacts.register_artifact(
            campaign_id=campaign_id,
            artifact_type="FIGURE_PNG",
            artifact_id=f"figure-{spec.simulation_id}",
            payload=buf.getvalue(),
            random_seed=spec.random_seed,
            parameters=dict(spec.parameters),
        )


def _python_version() -> str:
    import sys

    return sys.version.split()[0]


def _find_rule(policy: AcceptancePolicy, rule_id: str):
    from stov_scientist.errors import SchemaError

    for rule in policy.convergence_rules:
        if rule.rule_id == rule_id:
            return rule
    if len(policy.convergence_rules) == 1:
        return policy.convergence_rules[0]
    raise SchemaError(
        f"no convergence rule {rule_id!r} in AcceptancePolicy {policy.policy_id!r}"
    )


def _refined_spec(spec: SimulationSpec, level: int, strategy: str) -> SimulationSpec:
    """Refine a SimulationSpec copy for convergence level ``level``."""
    updated = spec.model_copy(deep=True)
    if level == 0:
        return updated
    if strategy in ("GRID_REFINEMENT",):
        factor = 2**level
        updated.grid.shape = [n * factor for n in spec.grid.shape]
        updated.grid.spacing = {
            a: sp / factor for a, sp in spec.grid.spacing.items()
        }
    elif strategy in ("STEP_REFINEMENT",):
        updated.parameters = dict(spec.parameters)
        updated.parameters["n_steps"] = int(spec.parameters.get("n_steps", 10)) * 2**level
    elif strategy in ("DOMAIN_SENSITIVITY",):
        factor = 1.0 + 0.5 * level
        updated.grid.domain_extent = {
            a: ext * factor for a, ext in spec.grid.domain_extent.items()
        }
    return updated


def _target_observable(field, target: str) -> float:
    from stov_scientist.errors import SimulationError

    obs = extract(field)
    if target == "energy":
        return obs.energy
    if target == "peak_intensity":
        return obs.peak_intensity
    if target == "topological_charge":
        if obs.topological_charge is None:
            raise SimulationError("field has no topological charge observable")
        return obs.topological_charge
    if target.startswith("centroid:"):
        axis = target.split(":", 1)[1]
        if axis not in obs.centroid:
            raise SimulationError(f"unknown centroid axis {axis!r}")
        return obs.centroid[axis]
    raise SimulationError(f"unknown convergence target observable {target!r}")
