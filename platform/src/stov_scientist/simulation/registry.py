"""SolverRegistry (spec §27, PHASE 7).

Every solver declares metadata: solver_id, name, supported model types,
required inputs, validity conditions, sampling requirements, reference ids
and version. Agents NEVER invent solver names — selection goes through
SolverSelector against this registry.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from stov_scientist.errors import SolverError


@dataclass(frozen=True)
class SolverMetadata:
    solver_id: str
    name: str
    supported_model_types: tuple[str, ...] = ("ANALYTICAL", "NUMERICAL")
    required_inputs: tuple[str, ...] = ()
    validity_conditions: tuple[str, ...] = ()
    sampling_requirements: tuple[str, ...] = ()
    reference_ids: tuple[str, ...] = ()
    version: str = "1.0.0"
    description: str = ""


@dataclass
class SolverEntry:
    metadata: SolverMetadata
    build: Callable[..., object]  # (simulation_spec) -> configured solver


class SolverRegistry:
    def __init__(self) -> None:
        self._solvers: dict[str, SolverEntry] = {}

    def register(self, metadata: SolverMetadata, build: Callable[..., object]) -> None:
        self._solvers[metadata.solver_id] = SolverEntry(metadata, build)

    def get(self, solver_id: str) -> SolverEntry:
        entry = self._solvers.get(solver_id)
        if entry is None:
            raise SolverError(f"unknown solver_id {solver_id!r}")
        return entry

    def get_metadata(self, solver_id: str) -> SolverMetadata:
        return self.get(solver_id).metadata

    def has(self, solver_id: str) -> bool:
        return solver_id in self._solvers

    def list_for_model_type(self, model_type: str) -> list[SolverMetadata]:
        return [
            e.metadata
            for e in self._solvers.values()
            if model_type in e.metadata.supported_model_types
        ]

    def all_metadata(self) -> list[SolverMetadata]:
        return [e.metadata for e in self._solvers.values()]
