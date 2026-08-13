"""Artifact registry tests (spec §16, PHASE 4): register, get, verify,
list, tamper detection, SHA256."""

from __future__ import annotations

import pytest

from stov_scientist.errors import ArtifactError


def test_register_and_get(artifact_registry):
    record = artifact_registry.register_artifact(
        campaign_id="campaign-1",
        artifact_type="FIELD_NPY",
        artifact_id="field-1",
        payload=b"\x00\x01\x02payload",
        random_seed=42,
        parameters={"wx": 1e-3},
    )
    assert len(record.sha256) == 64
    stored, payload = artifact_registry.get_artifact("field-1")
    assert payload == b"\x00\x01\x02payload"
    assert stored.campaign_id == "campaign-1"
    assert stored.random_seed == 42


def test_verify_ok(artifact_registry):
    artifact_registry.register_artifact(
        campaign_id="cmp-1", artifact_type="TEST_TYPE", artifact_id="a-1", payload=b"data"
    )
    ok, message = artifact_registry.verify_artifact("a-1")
    assert ok and message == "ok"


def test_verify_tampered_payload_detected(artifact_registry):
    record = artifact_registry.register_artifact(
        campaign_id="cmp-1", artifact_type="TEST_TYPE", artifact_id="a-1", payload=b"data"
    )
    from pathlib import Path

    Path(record.path_or_uri).write_bytes(b"tampered!")
    ok, message = artifact_registry.verify_artifact("a-1")
    assert not ok
    assert "mismatch" in message


def test_unknown_artifact_raises(artifact_registry):
    with pytest.raises(ArtifactError):
        artifact_registry.get_artifact("nope-1")


def test_list_and_filter(artifact_registry):
    artifact_registry.register_artifact(
        campaign_id="cmp-1", artifact_type="FIELD_NPY", artifact_id="f-1", payload=b"1"
    )
    artifact_registry.register_artifact(
        campaign_id="cmp-1", artifact_type="FIGURE_PNG", artifact_id="p-1", payload=b"2"
    )
    artifact_registry.register_artifact(
        campaign_id="cmp-2", artifact_type="FIELD_NPY", artifact_id="f-2", payload=b"3"
    )
    assert len(artifact_registry.list_artifacts()) == 3
    assert len(artifact_registry.list_artifacts(campaign_id="cmp-1")) == 2
    assert len(artifact_registry.list_artifacts(artifact_type="FIGURE_PNG")) == 1


def test_deterministic_sha256():
    from stov_scientist.artifacts.hashing import sha256_bytes

    assert sha256_bytes(b"same") == sha256_bytes(b"same")
    assert sha256_bytes(b"a") != sha256_bytes(b"b")


def test_unsafe_path_segment_rejected(artifact_registry):
    with pytest.raises(ArtifactError):
        artifact_registry.register_artifact(
            campaign_id="../../etc",
            artifact_type="TEST_TYPE",
            artifact_id="x-1",
            payload=b"x",
        )
