"""Ordered validator runner (spec PHASE 6 §22).

Schema -> Units -> Dimensions -> Symbols -> Limits -> Boundary -> Topology ->
Sampling -> Physics consistency. Stops at the first failing level by
default and records ``stop_level``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from stov_scientist.schemas import (
    VALIDATION_LEVEL_ORDER,
    EvidenceRecord,
    EvidenceSet,
    HypothesisCandidate,
    SamplingReport,
    ScientificModelSpec,
    ScientificOntology,
    SimulationSpec,
    ValidationLevel,
    ValidationReport,
    ValidationResult,
    utcnow,
)

ValidatorFn = Callable[..., ValidationResult]


@dataclass
class ValidatorContext:
    """Everything a validation run may reference."""

    models: dict[str, ScientificModelSpec] = field(default_factory=dict)
    simulations: dict[str, SimulationSpec] = field(default_factory=dict)
    evidence: EvidenceSet | None = None
    ontology: ScientificOntology | None = None
    hypotheses: dict[str, HypothesisCandidate] = field(default_factory=dict)
    sampling_reports: dict[str, SamplingReport] = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


def run_validators(
    target: object,
    context: ValidatorContext,
    *,
    stop_on_failure: bool = True,
    report_id: str | None = None,
) -> ValidationReport:
    """Run the applicable validators for the target in canonical order.

    Returns a ValidationReport; results beyond the first failing level are
    absent when stop_on_failure is True (stop_level records where it stopped).
    """
    checks = _select_checks(target, context)
    results: list[ValidationResult] = []
    stop_level: ValidationLevel | None = None

    for level in VALIDATION_LEVEL_ORDER:
        for fn in checks.get(ValidationLevel(level), []):
            try:
                result = fn()
            except Exception as exc:
                result = ValidationResult(
                    check_id=f"error-{len(results)}",
                    level=ValidationLevel(level),
                    name="validator execution",
                    passed=False,
                    message=f"{type(exc).__name__}: {exc}",
                )
            results.append(result)
            if not result.passed:
                stop_level = result.level
                if stop_on_failure:
                    target_id = _target_id(target)
                    return ValidationReport(
                        report_id=report_id or f"vr-{target_id}",
                        target_id=target_id,
                        target_kind=_target_kind(target),
                        created_at=utcnow(),
                        results=results,
                        stop_level=stop_level,
                    )

    target_id = _target_id(target)
    return ValidationReport(
        report_id=report_id or f"vr-{target_id}",
        target_id=target_id,
        target_kind=_target_kind(target),
        created_at=datetime.now().astimezone(),
        results=results,
        stop_level=stop_level,
    )


def _target_id(target: object) -> str:
    for attr in ("model_id", "simulation_id", "hypothesis_id", "evidence_id", "name"):
        value = getattr(target, attr, None)
        if isinstance(value, str) and value:
            return value
    return type(target).__name__


def _target_kind(target: object) -> str:
    name = type(target).__name__
    return {
        "ScientificModelSpec": "MODEL_SPEC",
        "SimulationSpec": "SIMULATION_SPEC",
        "HypothesisCandidate": "HYPOTHESIS",
        "EvidenceRecord": "EVIDENCE",
    }.get(name, name.upper())


def _select_checks(
    target: object, context: ValidatorContext
) -> dict[ValidationLevel, list[ValidatorFn]]:
    from stov_scientist.validators.boundary import validate_boundary_conditions
    from stov_scientist.validators.dimensions import validate_dimensions
    from stov_scientist.validators.evidence import validate_evidence_record
    from stov_scientist.validators.limits import validate_parameter_limits
    from stov_scientist.validators.sampling import validate_sampling
    from stov_scientist.validators.schema import (
        validate_hypothesis_schema,
        validate_model_schema,
        validate_simulation_schema,
    )
    from stov_scientist.validators.symbolic import validate_symbol_coverage
    from stov_scientist.validators.units import validate_model_units, validate_simulation_units

    checks: dict[ValidationLevel, list[ValidatorFn]] = {}

    if isinstance(target, ScientificModelSpec):
        checks.setdefault(ValidationLevel.SCHEMA, []).append(
            lambda: validate_model_schema(target, context.ontology)
        )
        checks.setdefault(ValidationLevel.UNITS, []).append(lambda: validate_model_units(target))
        checks.setdefault(ValidationLevel.DIMENSIONS, []).append(
            lambda: validate_dimensions(target)
        )
        checks.setdefault(ValidationLevel.SYMBOLS, []).append(
            lambda: validate_symbol_coverage(target)
        )
        checks.setdefault(ValidationLevel.BOUNDARY, []).append(
            lambda: validate_boundary_conditions(target)
        )

    if isinstance(target, SimulationSpec):
        checks.setdefault(ValidationLevel.SCHEMA, []).append(
            lambda: validate_simulation_schema(target, context.models)
        )
        if target.model_id in context.models:
            model = context.models[target.model_id]
            checks.setdefault(ValidationLevel.UNITS, []).append(
                lambda: validate_simulation_units(target, model)
            )
            checks.setdefault(ValidationLevel.LIMITS, []).append(
                lambda: validate_parameter_limits(target, model)
            )
        checks.setdefault(ValidationLevel.SAMPLING, []).append(
            lambda: validate_sampling(target)[0]
        )

    if isinstance(target, HypothesisCandidate):
        checks.setdefault(ValidationLevel.SCHEMA, []).append(
            lambda: validate_hypothesis_schema(target, context.evidence)
        )

    if isinstance(target, EvidenceRecord):
        checks.setdefault(ValidationLevel.PHYSICS, []).append(
            lambda: validate_evidence_record(target)
        )

    return checks
