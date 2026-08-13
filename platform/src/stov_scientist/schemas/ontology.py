"""ScientificOntology (spec §8).

An ontology is not just a concept map: it carries the Convention Registry,
Symbol Registry, Assumption Registry and Observable Registry used by every
downstream ModelSpec and SimulationSpec.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord, SourceRef


class Concept(BaseRecord):
    concept_id: ID
    name: str
    definition: str
    source_ids: list[ID] = Field(default_factory=list)


class Relation(BaseRecord):
    relation_id: ID
    subject: ID  # concept_id
    predicate: str
    object: ID  # concept_id
    source_ids: list[ID] = Field(default_factory=list)


class SymbolSpec(BaseRecord):
    """Symbol Registry entry: one symbol = one meaning = one unit."""

    symbol_id: ID
    symbol: str = Field(description="e.g. 'E', 'kx', 'omega'")
    name: str
    definition: str
    units: str = Field(description="Pint-parsable unit expression, e.g. 'V/m'")
    source_ids: list[ID] = Field(default_factory=list)


class CoordinateSystemSpec(BaseRecord):
    system_id: ID
    name: str
    axes: list[str] = Field(description="ordered axis names, e.g. ['x','y','t']")
    origin: str = ""
    handedness: Literal["right", "left", "unspecified"] = "unspecified"
    source_ids: list[ID] = Field(default_factory=list)


class ConventionSpec(BaseRecord):
    """Convention Registry entry (referenced by convention_ids)."""

    convention_id: ID
    category: Literal[
        "coordinate",
        "propagation_direction",
        "fourier_transform",
        "temporal_frequency",
        "phase_sign",
        "normalization",
        "unit_system",
    ]
    name: str
    definition: str
    source_ids: list[ID] = Field(default_factory=list)


class ObservableSpec(BaseRecord):
    observable_id: ID
    symbol: str
    name: str
    definition: str
    units: str
    measurement_procedure: str = ""
    source_ids: list[ID] = Field(default_factory=list)


class ParameterSpec(BaseRecord):
    parameter_id: ID
    symbol: str
    name: str
    units: str
    default_value: float | None = None
    uncertainty: float | None = None
    source_ids: list[ID] = Field(default_factory=list)


class PhysicalAssumption(BaseRecord):
    assumption_id: ID
    statement: str
    justification: str = ""
    source_ids: list[ID] = Field(default_factory=list)


class NumericalAssumption(BaseRecord):
    assumption_id: ID
    statement: str
    justification: str = ""
    source_ids: list[ID] = Field(default_factory=list)


class ModelFamily(BaseRecord):
    family_id: ID
    name: str
    description: str
    applicable_regimes: list[str] = Field(default_factory=list)
    source_ids: list[ID] = Field(default_factory=list)


class ScientificOntology(BaseRecord):
    ontology_id: ID
    concepts: list[Concept] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    symbols: list[SymbolSpec] = Field(default_factory=list)
    coordinate_systems: list[CoordinateSystemSpec] = Field(default_factory=list)
    conventions: list[ConventionSpec] = Field(default_factory=list)
    observables: list[ObservableSpec] = Field(default_factory=list)
    parameters: list[ParameterSpec] = Field(default_factory=list)
    physical_assumptions: list[PhysicalAssumption] = Field(default_factory=list)
    numerical_assumptions: list[NumericalAssumption] = Field(default_factory=list)
    model_families: list[ModelFamily] = Field(default_factory=list)
    known_constraints: list[str] = Field(default_factory=list)
    source_ids: list[ID] = Field(default_factory=list)

    def concept_map(self) -> dict[ID, Concept]:
        return {c.concept_id: c for c in self.concepts}

    def symbol_map(self) -> dict[str, SymbolSpec]:
        return {s.symbol: s for s in self.symbols}

    def convention_map(self) -> dict[ID, ConventionSpec]:
        return {c.convention_id: c for c in self.conventions}

    def parameter_map(self) -> dict[str, ParameterSpec]:
        return {p.symbol: p for p in self.parameters}

    def observable_map(self) -> dict[str, ObservableSpec]:
        return {o.symbol: o for o in self.observables}

    def source_refs(self) -> list[SourceRef]:
        """Flatten ontology entries into provenance source refs."""
        from typing import Any, cast

        out: list[SourceRef] = []
        entries: list[Any] = [
            *self.concepts,
            *self.symbols,
            *self.parameters,
            *self.observables,
            *self.conventions,
            *self.coordinate_systems,
            *self.physical_assumptions,
            *self.numerical_assumptions,
            *self.model_families,
        ]
        for entry in entries:
            for sid in cast(Any, entry).source_ids:
                if all(r.source_id != sid for r in out):
                    out.append(SourceRef(source_id=sid))
        return out
