"""Validation results (spec PHASE 6 §22 ordering)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord, utcnow


class ValidationLevel(StrEnum):
    SCHEMA = "SCHEMA"
    UNITS = "UNITS"
    DIMENSIONS = "DIMENSIONS"
    SYMBOLS = "SYMBOLS"
    LIMITS = "LIMITS"
    BOUNDARY = "BOUNDARY"
    TOPOLOGY = "TOPOLOGY"
    SAMPLING = "SAMPLING"
    PHYSICS = "PHYSICS"


# canonical order (spec §22) — module-level, NOT an enum member
VALIDATION_LEVEL_ORDER: tuple[str, ...] = (
    "SCHEMA",
    "UNITS",
    "DIMENSIONS",
    "SYMBOLS",
    "LIMITS",
    "BOUNDARY",
    "TOPOLOGY",
    "SAMPLING",
    "PHYSICS",
)


class ValidationResult(BaseRecord):
    check_id: ID
    level: ValidationLevel
    name: str
    passed: bool
    message: str = ""
    warnings: list[str] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)


class ValidationReport(BaseRecord):
    report_id: ID
    target_id: ID
    target_kind: str = Field(description="MODEL_SPEC / SIMULATION_SPEC / FIELD / EVIDENCE")
    created_at: datetime = Field(default_factory=utcnow)
    results: list[ValidationResult] = Field(default_factory=list)
    stop_level: ValidationLevel | None = Field(
        default=None, description="first failing level (later levels not run)"
    )

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(r.passed for r in self.results)

    @property
    def failed(self) -> list[ValidationResult]:
        return [r for r in self.results if not r.passed]

    def failures_at_or_before(self, level: ValidationLevel) -> list[ValidationResult]:
        order = list(VALIDATION_LEVEL_ORDER)
        idx = order.index(level.value)
        return [r for r in self.failed if order.index(r.level.value) <= idx]


class SamplingReport(BaseRecord):
    """Outcome of the sampling validator (spec §26)."""

    sampling_report_id: ID
    grid_id: ID
    nyquist_ok: bool | None = None
    aliasing_risk: list[str] = Field(default_factory=list)
    propagation_sampling_ok: bool | None = None
    fft_consistency_ok: bool | None = None
    details: dict = Field(default_factory=dict)
    verdict: str = "NOT_RUN"

    @property
    def usable_for_conclusions(self) -> bool:
        """Sampling failure must block scientific conclusions (spec §26)."""
        return bool(self.nyquist_ok and self.propagation_sampling_ok)
