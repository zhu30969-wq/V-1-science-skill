"""Campaign system (spec §13) + audit bundle (spec §48) + reproducibility
(spec §49). Campaigns live in campaigns/<campaign_id>/ with an audit/ dir."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import orjson

from stov_scientist.artifacts.hashing import git_commit, git_dirty
from stov_scientist.errors import EvidenceError
from stov_scientist.evidence.provenance import capture_environment
from stov_scientist.schemas import ResearchCampaign, utcnow

AUDIT_FILES = (
    "research_problem.json",
    "ontology.json",
    "search_boundary.json",
    "evidence_ledger.jsonl",
    "hypotheses.json",
    "mechanisms.json",
    "model_spec.json",
    "validation_report.json",
    "simulation_specs.json",
    "simulation_runs.json",
    "counterexamples.json",
    "claims.json",
    "scientific_judgement.json",
    "human_decisions.json",
    "artifact_manifest.json",
    "environment.json",
    "git_status.json",
    "audit_report.md",
)


class CampaignManager:
    def __init__(self, campaigns_root: Path, workdir: Path | None = None) -> None:
        self.root = Path(campaigns_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.workdir = workdir or self.root

    # -- campaign files ------------------------------------------------------
    def campaign_dir(self, campaign_id: str) -> Path:
        path = self.root / campaign_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def audit_dir(self, campaign_id: str) -> Path:
        path = self.campaign_dir(campaign_id) / "audit"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_campaign(self, campaign: ResearchCampaign) -> Path:
        path = self.campaign_dir(campaign.campaign_id) / "campaign.json"
        path.write_bytes(
            orjson.dumps(campaign.model_dump(mode="json"), option=orjson.OPT_INDENT_2)
        )
        return path

    def load_campaign(self, campaign_id: str) -> ResearchCampaign | None:
        path = self.campaign_dir(campaign_id) / "campaign.json"
        if not path.exists():
            return None
        return ResearchCampaign.model_validate_json(path.read_text(encoding="utf-8"))

    def list_campaigns(self) -> list[str]:
        return sorted(
            p.name for p in self.root.iterdir() if (p / "campaign.json").exists()
        )

    # -- audit bundle ---------------------------------------------------------
    def write_audit_file(self, campaign_id: str, filename: str, content: str) -> Path:
        if filename not in AUDIT_FILES:
            raise EvidenceError(f"{filename!r} is not a known audit file")
        path = self.audit_dir(campaign_id) / filename
        path.write_text(content, encoding="utf-8")
        return path

    def write_audit_json(self, campaign_id: str, filename: str, payload: Any) -> Path:
        return self.write_audit_file(
            campaign_id, filename, orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode()
        )

    # -- durable object store (survives interrupts/resume; keeps State light)
    def state_dir(self, campaign_id: str) -> Path:
        path = self.campaign_dir(campaign_id) / "state"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_object(self, campaign_id: str, kind: str, obj: Any) -> Path:
        path = self.state_dir(campaign_id) / f"{kind}.json"
        if hasattr(obj, "model_dump_json"):
            payload = obj.model_dump_json()
        elif hasattr(obj, "model_dump"):
            payload = orjson.dumps(obj.model_dump(mode="json")).decode()
        elif isinstance(obj, list) and all(hasattr(x, "model_dump") for x in obj):
            payload = orjson.dumps([x.model_dump(mode="json") for x in obj]).decode()
        else:
            payload = orjson.dumps(obj).decode()
        path.write_text(payload, encoding="utf-8")
        return path

    def load_object(self, campaign_id: str, kind: str, schema: type | None = None) -> Any | None:
        path = self.state_dir(campaign_id) / f"{kind}.json"
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        if schema is not None and hasattr(schema, "model_validate_json"):
            return schema.model_validate_json(text)
        return orjson.loads(text)

    def write_audit_bundle(
        self,
        campaign_id: str,
        *,
        campaign: ResearchCampaign,
        problem: Any = None,
        ontology: Any = None,
        boundary: Any = None,
        evidence_records: list | None = None,
        hypotheses: list | None = None,
        mechanisms: list | None = None,
        model_spec: Any = None,
        validation_report: Any = None,
        simulation_specs: list | None = None,
        simulation_runs: list | None = None,
        counterexamples: list | None = None,
        claims: list | None = None,
        judgements: list | None = None,
        artifact_manifest: list | None = None,
        pipeline_status: dict | None = None,
        warnings: list | None = None,
    ) -> Path:
        """Write the complete audit bundle (spec §48)."""
        audit = self.audit_dir(campaign_id)

        def _dump(obj: Any) -> Any:
            if obj is None:
                return None
            if hasattr(obj, "model_dump"):
                return obj.model_dump(mode="json")
            if isinstance(obj, list):
                return [_dump(x) for x in obj]
            return obj

        files: dict[str, str] = {
            "research_problem.json": _json(_dump(problem) if problem else None),
            "ontology.json": _json(_dump(ontology) if ontology else None),
            "search_boundary.json": _json(_dump(boundary) if boundary else None),
            "evidence_ledger.jsonl": "".join(
                (r.model_dump_json() if hasattr(r, "model_dump_json") else json.dumps(_dump(r))) + "\n"
                for r in (evidence_records or [])
            ),
            "hypotheses.json": _json(_dump(hypotheses) if hypotheses else None),
            "mechanisms.json": _json(_dump(mechanisms) if mechanisms else None),
            "model_spec.json": _json(_dump(model_spec) if model_spec else None),
            "validation_report.json": _json(_dump(validation_report) if validation_report else None),
            "simulation_specs.json": _json(_dump(simulation_specs) if simulation_specs else None),
            "simulation_runs.json": _json(_dump(simulation_runs) if simulation_runs else None),
            "counterexamples.json": _json(_dump(counterexamples) if counterexamples else None),
            "claims.json": _json(_dump(claims) if claims else None),
            "scientific_judgement.json": _json(_dump(judgements) if judgements else None),
            "human_decisions.json": _json(
                _dump(campaign.human_decisions) if campaign else None
            ),
            "artifact_manifest.json": _json(_dump(artifact_manifest) if artifact_manifest else None),
            "environment.json": _json(capture_environment(self.workdir)),
            "git_status.json": _json(
                {
                    "git_commit": git_commit(self.workdir),
                    "working_tree_dirty": git_dirty(self.workdir),
                }
            ),
        }
        for filename, content in files.items():
            (audit / filename).write_text(content, encoding="utf-8")

        report_path = audit / "audit_report.md"
        report_path.write_text(
            _audit_report_md(campaign, pipeline_status or {}, warnings or []),
            encoding="utf-8",
        )
        return audit


def _json(payload: Any) -> str:
    return orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode()


def _audit_report_md(
    campaign: ResearchCampaign,
    pipeline_status: dict[str, str],
    warnings: list[str],
) -> str:
    lines = [
        f"# Audit Report — {campaign.campaign_id}",
        "",
        f"- Title: {campaign.title}",
        f"- Status: {campaign.status.value}",
        f"- Generated at: {utcnow().isoformat()}",
        "",
        "## Pipeline status",
        "",
    ]
    for stage, status in pipeline_status.items():
        lines.append(f"- {stage}: {status}")
    lines.append("")
    lines.append("## Human decisions")
    for d in campaign.human_decisions:
        lines.append(f"- {d.gate}: {d.decision.value} ({d.rationale[:200]})")
    lines.append("")
    lines.append("## Warnings")
    if warnings:
        lines.extend(f"- {w}" for w in warnings)
    else:
        lines.append("- none")
    lines.append("")
    lines.append(
        "## Scientific integrity note\n\n"
        "This report is a record of the research pipeline state. Statuses follow "
        "the STOV AI Scientist vocabulary: SUPPORTED_WITHIN_SCOPE, "
        "PARTIALLY_SUPPORTED, INCONCLUSIVE, CONTRADICTED, INSUFFICIENT_EVIDENCE. "
        "INCONCLUSIVE is a valid scientific outcome."
    )
    return "\n".join(lines) + "\n"
