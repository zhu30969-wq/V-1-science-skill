"""MechanismCandidate (spec §12)."""

from __future__ import annotations

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord


class PhysicalProcess(BaseRecord):
    process_id: ID
    name: str
    description: str
    source_ids: list[ID] = Field(default_factory=list)


class MechanisticLink(BaseRecord):
    link_id: ID
    from_step: ID
    to_step: ID
    description: str


class MechanismCandidate(BaseRecord):
    mechanism_id: ID
    hypothesis_id: ID
    description: str
    physical_processes: list[PhysicalProcess] = Field(default_factory=list)
    mechanistic_links: list[MechanisticLink] = Field(default_factory=list)
    governing_principles: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    boundary_conditions: list[str] = Field(default_factory=list)
    predicted_observables: list[str] = Field(default_factory=list)
    alternative_mechanisms: list[ID] = Field(default_factory=list)
    evidence_ids: list[ID] = Field(default_factory=list)
    model_requirements: list[str] = Field(default_factory=list)
