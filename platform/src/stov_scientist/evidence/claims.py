"""Claim registry with guarded status transitions (spec §17).

Status transitions are monotone in epistemic strength: a claim may only
move to a status consistent with accumulating evidence; it may never jump
to a "proven" state (no such status exists).
"""

from __future__ import annotations

from sqlalchemy import String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from stov_scientist.errors import EvidenceError
from stov_scientist.schemas import ClaimStatus, ScientificClaim


class Base(DeclarativeBase):
    pass


class ClaimRow(Base):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="UNASSESSED")
    statement: Mapped[str] = mapped_column(Text)
    record_json: Mapped[str] = mapped_column(Text)


_ALLOWED_TRANSITIONS: dict[ClaimStatus, frozenset[ClaimStatus]] = {
    ClaimStatus.UNASSESSED: frozenset(
        {
            ClaimStatus.SUPPORTED_WITHIN_SCOPE,
            ClaimStatus.PARTIALLY_SUPPORTED,
            ClaimStatus.INCONCLUSIVE,
            ClaimStatus.CONTRADICTED,
            ClaimStatus.INSUFFICIENT_EVIDENCE,
        }
    ),
    ClaimStatus.INSUFFICIENT_EVIDENCE: frozenset(
        {
            ClaimStatus.SUPPORTED_WITHIN_SCOPE,
            ClaimStatus.PARTIALLY_SUPPORTED,
            ClaimStatus.INCONCLUSIVE,
            ClaimStatus.CONTRADICTED,
        }
    ),
    ClaimStatus.INCONCLUSIVE: frozenset(
        {
            ClaimStatus.SUPPORTED_WITHIN_SCOPE,
            ClaimStatus.PARTIALLY_SUPPORTED,
            ClaimStatus.CONTRADICTED,
        }
    ),
    ClaimStatus.PARTIALLY_SUPPORTED: frozenset(
        {ClaimStatus.SUPPORTED_WITHIN_SCOPE, ClaimStatus.CONTRADICTED}
    ),
    ClaimStatus.SUPPORTED_WITHIN_SCOPE: frozenset(
        {ClaimStatus.PARTIALLY_SUPPORTED, ClaimStatus.CONTRADICTED}
    ),
    ClaimStatus.CONTRADICTED: frozenset({ClaimStatus.PARTIALLY_SUPPORTED}),
}


class ClaimLedger:
    def __init__(self, database_url: str = "") -> None:
        if database_url:
            self.engine: Engine = create_engine(database_url)
        else:
            self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def add_claim(self, claim: ScientificClaim) -> None:
        with Session(self.engine) as session:
            session.merge(
                ClaimRow(
                    claim_id=claim.claim_id,
                    status=claim.status.value,
                    statement=claim.statement,
                    record_json=claim.model_dump_json(),
                )
            )
            session.commit()

    def get_claim(self, claim_id: str) -> ScientificClaim | None:
        with Session(self.engine) as session:
            row = session.get(ClaimRow, claim_id)
        return ScientificClaim.model_validate_json(row.record_json) if row else None

    def list_claims(self) -> list[ScientificClaim]:
        with Session(self.engine) as session:
            rows = session.execute(select(ClaimRow)).scalars().all()
        return [ScientificClaim.model_validate_json(r.record_json) for r in rows]

    def update_status(self, claim_id: str, new_status: ClaimStatus) -> ScientificClaim:
        claim = self.get_claim(claim_id)
        if claim is None:
            raise EvidenceError(f"unknown claim_id {claim_id!r}")
        allowed = _ALLOWED_TRANSITIONS.get(claim.status, frozenset())
        if new_status not in allowed and new_status is not claim.status:
            raise EvidenceError(
                f"illegal claim status transition {claim.status.value} -> "
                f"{new_status.value} for {claim_id}"
            )
        claim = claim.model_copy(update={"status": new_status})
        self.add_claim(claim)
        return claim
