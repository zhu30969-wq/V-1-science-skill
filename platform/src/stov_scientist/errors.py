"""STOV AI Scientist error taxonomy (spec PHASE 21 §74).

Every domain failure raises one of these — never a bare ``Exception`` and
never a silent ``except Exception: pass``.
"""

from __future__ import annotations


class StovError(Exception):
    """Base class for all STOV Scientist errors."""


class ConfigurationError(StovError):
    """Missing or invalid runtime configuration (e.g. no DeepSeek API key)."""


class SchemaError(StovError):
    """A scientific contract (Pydantic schema) is invalid or inconsistent."""


class ProviderError(StovError):
    """LLM provider failure (DeepSeek) after retries."""


class LiteratureRetrievalError(StovError):
    """Literature database retrieval failed.

    Note: a retrieval failure is NEVER interpreted as "no literature exists".
    Partial results are recorded with PARTIAL_RETRIEVAL status.
    """


class ValidationError(StovError):
    """Deterministic validation failed (units, dimensions, symbols, limits...)."""


class SamplingError(StovError):
    """Grid/sampling requirements violated. No scientific conclusion may proceed."""


class SolverError(StovError):
    """No solver available, or solver execution failed."""


class NoValidSolverError(SolverError):
    """Solver selection found no solver whose validity conditions hold."""


class SimulationError(StovError):
    """Simulation harness failure (NOT a scientific contradiction)."""


class ArtifactError(StovError):
    """Artifact registry/store failure (write, hash, verify)."""


class EvidenceError(StovError):
    """Evidence ledger failure or invalid provenance."""


class HumanApprovalRequired(StovError):
    """A human gate is pending — the graph must be interrupted, not errored."""


class IterationLimitReached(StovError):
    """A bounded loop hit its limit from AcceptancePolicy; HUMAN_REVIEW_REQUIRED."""


class StructuredOutputFailure(StovError):
    """A worker's structured output failed even after the single retry."""
