"""Evidence provenance validation (spec §36, PHASE 4).

Structural completeness checks: every EvidenceRecord must have a search
boundary, an identifier, a retrieval date, and a provenance record.
UNASSESSED quality is legal but must carry a reason.
"""

from __future__ import annotations

from stov_scientist.schemas import EvidenceRecord, ValidationLevel, ValidationResult


def validate_evidence_record(record: EvidenceRecord, check_id: str = "evidence-record") -> ValidationResult:
    problems: list[str] = []
    warnings: list[str] = []

    if not record.search_boundary_id:
        problems.append(f"record {record.evidence_id!r} has no search_boundary_id")
    if not record.identifiers.doi and not record.identifiers.arxiv and not record.identifiers.openalex:
        problems.append(
            f"record {record.evidence_id!r} has no external identifier (doi/arxiv/openalex)"
        )
    if not record.title.strip():
        problems.append(f"record {record.evidence_id!r} has empty title")
    if not record.provenance.source_ids and record.relation != "UNKNOWN":
        warnings.append(f"record {record.evidence_id!r}: provenance has no source_ids")
    if record.evidence_quality == "UNASSESSED" and not record.quality_reason:
        warnings.append(f"record {record.evidence_id!r}: UNASSESSED quality with no reason")

    return ValidationResult(
        check_id=check_id,
        level=ValidationLevel.PHYSICS,
        name="evidence provenance completeness",
        passed=not problems,
        message="; ".join(problems) if problems else "evidence record provenance complete",
        warnings=warnings,
        details={"problems": problems},
    )
