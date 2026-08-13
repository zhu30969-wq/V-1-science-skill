"""Scientific contracts — Pydantic schemas (spec PHASE 3).

The schemas are the contract layer between agents and the deterministic
scientific core. LLM output must land in these before entering any graph edge.
"""

from stov_scientist.schemas.artifact import ScientificArtifact
from stov_scientist.schemas.campaign import (
    AcceptancePolicy,
    CampaignStatus,
    ConvergenceRule,
    GateDecision,
    HumanDecision,
    ResearchCampaign,
)
from stov_scientist.schemas.claim import ClaimStatus, ScientificClaim
from stov_scientist.schemas.common import (
    EvidenceQuality,
    EvidenceRelation,
    Identifiers,
    ProvenanceRecord,
    RetrievalStatus,
    SearchBoundary,
    SourceRef,
    SourceType,
    normalize_doi,
    utcnow,
)
from stov_scientist.schemas.contradiction import (
    ContradictionRecord,
    ContradictionStatus,
    ContradictionType,
    CounterexampleCandidate,
)
from stov_scientist.schemas.evidence import EvidenceRecord, EvidenceSet
from stov_scientist.schemas.hypothesis import (
    FalsificationCondition,
    HypothesisCandidate,
    HypothesisStatus,
    Prediction,
)
from stov_scientist.schemas.judgement import JudgementStatus, ScientificJudgement
from stov_scientist.schemas.mechanism import (
    MechanismCandidate,
    MechanisticLink,
    PhysicalProcess,
)
from stov_scientist.schemas.model import (
    BoundaryCondition,
    Equation,
    EquationStatus,
    InitialCondition,
    Invariant,
    ModelType,
    ScientificModelSpec,
    SolverRequirement,
    ValidityDomain,
)
from stov_scientist.schemas.ontology import (
    Concept,
    ConventionSpec,
    CoordinateSystemSpec,
    ModelFamily,
    NumericalAssumption,
    ObservableSpec,
    ParameterSpec,
    PhysicalAssumption,
    Relation,
    ScientificOntology,
    SymbolSpec,
)
from stov_scientist.schemas.problem import ResearchProblem
from stov_scientist.schemas.simulation import (
    ConvergencePlan,
    ConvergenceResult,
    GridSpec,
    ResourceLimits,
    RuntimeMetadata,
    SimulationRun,
    SimulationSpec,
    SimulationStatus,
    UncertaintyPlan,
    UncertaintyResult,
)
from stov_scientist.schemas.validation import (
    VALIDATION_LEVEL_ORDER,
    SamplingReport,
    ValidationLevel,
    ValidationReport,
    ValidationResult,
)

__all__ = [
    "VALIDATION_LEVEL_ORDER",
    "AcceptancePolicy",
    "BoundaryCondition",
    "CampaignStatus",
    "ClaimStatus",
    "Concept",
    "ContradictionRecord",
    "ContradictionStatus",
    "ContradictionType",
    "ConventionSpec",
    "ConvergencePlan",
    "ConvergenceResult",
    "ConvergenceRule",
    "CoordinateSystemSpec",
    "CounterexampleCandidate",
    "Equation",
    "EquationStatus",
    "EvidenceQuality",
    "EvidenceRecord",
    "EvidenceRelation",
    "EvidenceSet",
    "FalsificationCondition",
    "GateDecision",
    "GridSpec",
    "HumanDecision",
    "HypothesisCandidate",
    "HypothesisStatus",
    "Identifiers",
    "InitialCondition",
    "Invariant",
    "JudgementStatus",
    "MechanismCandidate",
    "MechanisticLink",
    "ModelFamily",
    "ModelType",
    "NumericalAssumption",
    "ObservableSpec",
    "ParameterSpec",
    "PhysicalAssumption",
    "PhysicalProcess",
    "Prediction",
    "ProvenanceRecord",
    "Relation",
    "ResearchCampaign",
    "ResearchProblem",
    "ResourceLimits",
    "RetrievalStatus",
    "RuntimeMetadata",
    "SamplingReport",
    "ScientificArtifact",
    "ScientificClaim",
    "ScientificJudgement",
    "ScientificModelSpec",
    "ScientificOntology",
    "SearchBoundary",
    "SimulationRun",
    "SimulationSpec",
    "SimulationStatus",
    "SolverRequirement",
    "SourceRef",
    "SourceType",
    "SymbolSpec",
    "UncertaintyPlan",
    "UncertaintyResult",
    "ValidationLevel",
    "ValidationReport",
    "ValidationResult",
    "ValidityDomain",
    "normalize_doi",
    "utcnow",
]
