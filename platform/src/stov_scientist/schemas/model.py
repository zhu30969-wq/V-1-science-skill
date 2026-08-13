"""ScientificModelSpec — the core schema (spec §13).

``validity_domain`` is mandatory: a model without a stated validity domain
cannot be selected by any solver.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from stov_scientist.schemas.common import (
    ID,
    BaseRecord,
    EquationStatus,
    ProvenanceRecord,
)


class ModelType(StrEnum):
    ANALYTICAL = "ANALYTICAL"
    NUMERICAL = "NUMERICAL"
    DATA_DRIVEN = "DATA_DRIVEN"  # NOT_IMPLEMENTED in v1 (spec §40)
    HYBRID = "HYBRID"  # NOT_IMPLEMENTED in v1 (spec §40)


class Equation(BaseRecord):
    equation_id: ID
    symbolic_form: str = Field(description="SymPy-parsable expression, e.g. 'E = A*exp(-(x**2 + t**2)/w**2)'")
    latex: str | None = None
    terms: dict[str, str] = Field(
        default_factory=dict, description="name -> explanation of each term"
    )
    derivation_source: str = ""
    source_ids: list[ID] = Field(default_factory=list)
    status: EquationStatus = EquationStatus.CANDIDATE_MODEL


class ValidityDomain(BaseRecord):
    domain_id: ID
    description: str
    parameter_ranges: dict[str, tuple[float | None, float | None]] = Field(
        default_factory=dict,
        description="symbol -> (min, max); None side = unbounded",
    )
    spatial_domain: str = ""
    temporal_domain: str = ""
    regime_constraints: list[str] = Field(default_factory=list)
    applicability_notes: str = ""


class InitialCondition(BaseRecord):
    ic_id: ID
    variable: str
    expression: str
    value: float | None = None
    units: str = ""


class BoundaryCondition(BaseRecord):
    bc_id: ID
    region: str
    kind: str = Field(description="DIRICHLET / NEUMANN / PERIODIC / ABSORBING / OTHER")
    expression: str
    value: float | None = None
    units: str = ""


class Invariant(BaseRecord):
    invariant_id: ID
    name: str
    expression: str
    checked_by: str = Field(description="validator id that checks this invariant")


class SolverRequirement(BaseRecord):
    requirement_id: ID
    kind: str = Field(description="e.g. FFT_GRID / PARAXIAL / ENSEMBLE / MEMORY")
    note: str = ""


class ScientificModelSpec(BaseRecord):
    model_id: ID
    name: str
    model_type: ModelType = ModelType.ANALYTICAL
    equations: list[Equation] = Field(min_length=1)
    independent_variables: list[str] = Field(min_length=1)
    dependent_variables: list[str] = Field(min_length=1)
    symbols: dict[str, str] = Field(
        default_factory=dict, description="symbol -> Pint unit expression"
    )
    units: dict[str, str] = Field(
        default_factory=dict, description="quantity name -> Pint unit expression"
    )
    coordinate_system: str = Field(description="coordinate_system id from ontology")
    convention_ids: list[ID] = Field(default_factory=list)
    physical_assumptions: list[str] = Field(default_factory=list)
    numerical_assumptions: list[str] = Field(default_factory=list)
    initial_conditions: list[InitialCondition] = Field(default_factory=list)
    boundary_conditions: list[BoundaryCondition] = Field(default_factory=list)
    validity_domain: ValidityDomain
    invariants: list[Invariant] = Field(default_factory=list)
    predicted_observables: list[str] = Field(default_factory=list)
    falsification_conditions: list[str] = Field(default_factory=list)
    solver_requirements: list[SolverRequirement] = Field(default_factory=list)
    source_ids: list[ID] = Field(default_factory=list)
    provenance: ProvenanceRecord = Field(default_factory=ProvenanceRecord)

    @model_validator(mode="after")
    def _check_symbols(self) -> ScientificModelSpec:
        # every declared symbol must carry a non-empty unit expression
        missing = [s for s, unit in self.symbols.items() if not unit.strip()]
        if missing:
            raise ValueError(f"symbols missing unit mapping: {missing}")
        return self

    @property
    def equation_by_id(self) -> dict[ID, Equation]:
        return {e.equation_id: e for e in self.equations}

    @property
    def has_validated_equations(self) -> bool:
        return all(e.status is EquationStatus.VALIDATED for e in self.equations)
