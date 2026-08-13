"""Service bundle for the control plane (spec §2 layering).

All external capabilities (LLMs, simulation, artifacts, evidence, campaign
store) enter the graphs through one bundle. Unit tests inject fakes; the
production bundle wires real DeepSeek models LAZILY — importing
research_graph.py must not require DEEPSEEK_API_KEY.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from stov_scientist.artifacts.local_store import LocalStore
from stov_scientist.artifacts.registry import ArtifactRegistry
from stov_scientist.campaign.manager import CampaignManager
from stov_scientist.evidence.claims import ClaimLedger
from stov_scientist.evidence.ledger import EvidenceLedger
from stov_scientist.simulation import SimulationRunner, default_solver_registry


class LazyModel:
    """Defers model construction until first use (no API key at import)."""

    def __init__(self, kind: str) -> None:
        self.kind = kind  # main | fast

    def _resolve(self) -> Any:
        from stov_scientist.config.models import get_fast_model, get_main_model

        return get_main_model() if self.kind == "main" else get_fast_model()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)

    def with_structured_output(self, schema: type) -> Any:
        return self._resolve().with_structured_output(schema)

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self._resolve().invoke(*args, **kwargs)


@dataclass
class ServiceBundle:
    main_model: Any = None
    fast_model: Any = None
    simulation: SimulationRunner | None = None
    artifacts: ArtifactRegistry | None = None
    evidence: EvidenceLedger | None = None
    claims: ClaimLedger | None = None
    campaigns: CampaignManager | None = None
    workdir: Path | None = None
    extra: dict = field(default_factory=dict)


def build_default_services(
    repo_root: Path | None = None,
    artifact_root: Path | None = None,
) -> ServiceBundle:
    """Production wiring (lazy models; local stores)."""
    from stov_scientist.config.settings import get_settings

    settings = get_settings()
    root = repo_root or _default_repo_root()
    store = LocalStore(artifact_root or settings.artifact_root, settings.database_url)
    artifacts = ArtifactRegistry(store, workdir=root)
    simulation = SimulationRunner(default_solver_registry(), artifacts)
    campaigns = CampaignManager(root / "campaigns")
    return ServiceBundle(
        main_model=LazyModel("main"),
        fast_model=LazyModel("fast"),
        simulation=simulation,
        artifacts=artifacts,
        evidence=EvidenceLedger(settings.database_url),
        claims=ClaimLedger(settings.database_url),
        campaigns=campaigns,
        workdir=root,
    )


def _default_repo_root() -> Path:
    from stov_scientist.config.settings import PLATFORM_ROOT

    return PLATFORM_ROOT.parent
