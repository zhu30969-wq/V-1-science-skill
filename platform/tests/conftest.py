"""Shared test fixtures. No LLM, no network in the default fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from stov_scientist.artifacts.local_store import LocalStore
from stov_scientist.artifacts.registry import ArtifactRegistry
from stov_scientist.campaign.manager import CampaignManager
from stov_scientist.control.services import ServiceBundle
from stov_scientist.evidence.claims import ClaimLedger
from stov_scientist.evidence.ledger import EvidenceLedger
from stov_scientist.simulation import SimulationRunner, default_solver_registry


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def artifact_registry(tmp_path: Path) -> ArtifactRegistry:
    store = LocalStore(tmp_path / "artifacts")
    return ArtifactRegistry(store, workdir=tmp_path)


@pytest.fixture
def campaign_manager(tmp_path: Path) -> CampaignManager:
    return CampaignManager(tmp_path / "campaigns", workdir=tmp_path)


@pytest.fixture
def simulation_runner(artifact_registry: ArtifactRegistry) -> SimulationRunner:
    return SimulationRunner(default_solver_registry(), artifact_registry)


@pytest.fixture
def services(
    tmp_path: Path,
    artifact_registry: ArtifactRegistry,
    campaign_manager: CampaignManager,
) -> ServiceBundle:
    return ServiceBundle(
        main_model=None,
        fast_model=None,
        simulation=SimulationRunner(default_solver_registry(), artifact_registry),
        artifacts=artifact_registry,
        evidence=EvidenceLedger(),
        claims=ClaimLedger(),
        campaigns=campaign_manager,
        workdir=tmp_path,
    )
