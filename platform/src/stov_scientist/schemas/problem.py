"""ResearchProblem — the formalized research question (spec §7)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord, utcnow


class ResearchProblem(BaseRecord):
    problem_id: ID
    title: str = Field(min_length=3, max_length=500)
    research_question: str = Field(min_length=3)
    system_under_study: str = Field(
        description="e.g. 'space-time optical vortex pulse in free space'"
    )
    scope: str = Field(description="What IS included in this study")
    excluded_scope: str = Field(description="What is explicitly NOT included")
    target_observables: list[str] = Field(default_factory=list)
    known_constraints: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    owner: str = "unknown"
    created_at: datetime = Field(default_factory=utcnow)
    source_ids: list[ID] = Field(default_factory=list)

    # research problem kind — used by the router
    kind: Literal["THEORY", "SIMULATION", "MIXED_THEORY_SIMULATION", "LITERATURE"] = (
        "MIXED_THEORY_SIMULATION"
    )
