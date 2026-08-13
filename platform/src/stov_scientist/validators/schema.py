"""Cross-object schema/reference validation (spec PHASE 6 §22).

Checks relationships BETWEEN scientific contracts: simulation spec refers to
a known model; hypotheses reference known evidence; model conventions are
registered; model symbols are covered by the ontology.
"""

from __future__ import annotations

from stov_scientist.physics.conventions import validate_convention_ids
from stov_scientist.schemas import (
    EvidenceSet,
    HypothesisCandidate,
    ScientificModelSpec,
    ScientificOntology,
    SimulationSpec,
    ValidationLevel,
    ValidationResult,
)


def validate_model_schema(
    model: ScientificModelSpec,
    ontology: ScientificOntology | None = None,
    check_id: str = "schema-model",
) -> ValidationResult:
    problems: list[str] = []
    warnings: list[str] = []

    unknown = validate_convention_ids(model.convention_ids)
    if unknown:
        problems.append(f"unknown convention_ids: {unknown}")

    if not model.validity_domain:
        problems.append("model has no validity domain (mandatory, spec §13)")

    if ontology is not None:
        onto_symbols = set(ontology.symbol_map())
        missing = [s for s in model.symbols if s not in onto_symbols]
        if missing:
            warnings.append(f"model symbols not declared in ontology: {missing}")
        coord_ids = {c.system_id for c in ontology.coordinate_systems}
        if model.coordinate_system not in coord_ids:
            problems.append(
                f"coordinate_system {model.coordinate_system!r} not in ontology"
            )

    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.SCHEMA,
        name="model schema cross-references",
        passed=not problems,
        message="; ".join(problems) if problems else "model schema references consistent",
        warnings=warnings,
        details={"problems": problems},
    )


def validate_simulation_schema(
    spec: SimulationSpec,
    models: dict[str, ScientificModelSpec] | None = None,
    check_id: str = "schema-simulation",
) -> ValidationResult:
    problems: list[str] = []
    if models is not None and spec.model_id not in models:
        problems.append(f"simulation refers to unknown model_id {spec.model_id!r}")
    if spec.ensemble_size < 1:
        problems.append("ensemble_size must be >= 1")
    if not spec.convergence_plan.target_observable:
        problems.append("convergence plan has no target observable")
    if not spec.grid.axes:
        problems.append("grid has no axes")
    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.SCHEMA,
        name="simulation schema cross-references",
        passed=not problems,
        message="; ".join(problems) if problems else "simulation schema references consistent",
        details={"problems": problems},
    )


def validate_hypothesis_schema(
    hypothesis: HypothesisCandidate,
    evidence: EvidenceSet | None = None,
    check_id: str = "schema-hypothesis",
) -> ValidationResult:
    problems: list[str] = []
    if evidence is not None:
        known = {r.evidence_id for r in evidence.records}
        missing_support = [e for e in hypothesis.supporting_evidence_ids if e not in known]
        missing_contra = [e for e in hypothesis.contradicting_evidence_ids if e not in known]
        if missing_support:
            problems.append(f"unknown supporting evidence ids: {missing_support}")
        if missing_contra:
            problems.append(f"unknown contradicting evidence ids: {missing_contra}")
    if not hypothesis.falsification_conditions:
        problems.append("hypothesis has no falsification conditions (untestable)")
    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.SCHEMA,
        name="hypothesis schema cross-references",
        passed=not problems,
        message="; ".join(problems) if problems else "hypothesis schema references consistent",
        details={"problems": problems},
    )
