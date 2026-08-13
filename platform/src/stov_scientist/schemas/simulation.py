"""SimulationSpec / SimulationRun (spec §14, §15).

SimulationRun NEVER stores large arrays — only artifact IDs and metadata.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord, utcnow


class SimulationStatus(StrEnum):
    PLANNED = "PLANNED"
    VALIDATING = "VALIDATING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    NUMERICAL_FAILURE = "NUMERICAL_FAILURE"
    SAMPLING_FAILURE = "SAMPLING_FAILURE"
    DOMAIN_VIOLATION = "DOMAIN_VIOLATION"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"


class GridSpec(BaseRecord):
    grid_id: ID
    kind: str = Field(description="e.g. 'x-t', 'x-y', 'x-y-t', 'k-omega'")
    axes: list[str] = Field(min_length=1)
    shape: list[int] = Field(min_length=1, description="samples per axis")
    spacing: dict[str, float] = Field(description="axis -> physical spacing (base units)")
    domain_extent: dict[str, float] = Field(description="axis -> physical extent")
    units: dict[str, str] = Field(default_factory=dict, description="axis -> Pint unit")


class ConvergencePlan(BaseRecord):
    strategy: StrEnum | str = Field(
        description="GRID_REFINEMENT / STEP_REFINEMENT / DOMAIN_SENSITIVITY / ENSEMBLE_REFINEMENT"
    )
    refinement_levels: list[int] = Field(default_factory=lambda: [0, 1])
    target_observable: str
    acceptance_rule: str = Field(
        description="reference to the campaign AcceptancePolicy convergence rule id"
    )


class UncertaintyPlan(BaseRecord):
    numerical_uncertainty: bool = False
    numerical_method: str = ""
    stochastic_uncertainty: bool = False
    ensemble_sizes: list[int] = Field(default_factory=list)
    parameter_uncertainty: bool = False
    parameter_sweeps: dict[str, list[float]] = Field(default_factory=dict)
    measurement_uncertainty: bool = False
    model_uncertainty: bool = False


class ResourceLimits(BaseRecord):
    max_wall_time_seconds: float | None = None
    max_memory_mb: float | None = None
    max_artifacts: int | None = None


class SimulationSpec(BaseRecord):
    simulation_id: ID
    model_id: ID
    solver_id: ID | None = Field(default=None, description="filled by SolverSelector")
    domain: str = Field(description="physical domain description, e.g. 'free space'")
    grid: GridSpec
    parameters: dict[str, float | str] = Field(
        description="symbol -> value (base units); string values are pipeline "
        "control parameters (field_kind, turbulence_model, ...)"
    )
    initial_conditions: dict[str, str] = Field(default_factory=dict)
    boundary_conditions: dict[str, str] = Field(default_factory=dict)
    random_seed: int | None = None
    ensemble_size: int = 1
    convergence_plan: ConvergencePlan
    uncertainty_plan: UncertaintyPlan = Field(default_factory=UncertaintyPlan)
    expected_observables: list[str] = Field(default_factory=list)
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)


class RuntimeMetadata(BaseRecord):
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    cpu_count: int | None = None
    peak_memory_mb: float | None = None


class ConvergenceResult(BaseRecord):
    achieved: bool | None = None
    metric_name: str
    refinement_levels: list[int] = Field(default_factory=list)
    values: dict[int, float] = Field(default_factory=dict)
    deviation: float | None = None
    verdict: str = "NOT_RUN"


class UncertaintyResult(BaseRecord):
    numerical_uncertainty: dict[str, Any] = Field(default_factory=dict)
    stochastic_uncertainty: dict[str, float] = Field(default_factory=dict)
    parameter_uncertainty: dict[str, float] = Field(default_factory=dict)
    model_uncertainty: str = "NOT_ASSESSED"
    measurement_uncertainty: str = "NOT_ASSESSED"
    details: str = ""


class SimulationRun(BaseRecord):
    run_id: ID
    simulation_spec_id: ID
    status: SimulationStatus = SimulationStatus.PLANNED
    artifact_ids: list[ID] = Field(default_factory=list)
    runtime_metadata: RuntimeMetadata = Field(default_factory=RuntimeMetadata)
    solver_version: str = ""
    python_version: str = ""
    git_commit: str = ""
    working_tree_dirty: bool | None = None
    random_seed: int | None = None
    convergence_result: ConvergenceResult | None = None
    uncertainty_result: UncertaintyResult | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
