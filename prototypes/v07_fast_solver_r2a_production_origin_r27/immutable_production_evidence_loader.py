"""Load pinned Task173 production R2A artifacts from immutable evidence JSON."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_contract import (
    R2A_CERTIFICATE_SCHEMA,
    R2A_EVENT_SCHEMA,
)

COMPLETION_MANIFEST_REL = (
    "docs/tasks/evidence/TASK-173-v0.7-full-sizing-reference-plane-serialization-completion-r1.json"
)
RATINGS_EVIDENCE_REL = (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-ratings-r1.json"
)
CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_nested(
    obj: Any, *, cert_schema: str, event_schema: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    certificates: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            schema = node.get("schema_version")
            if schema == cert_schema and isinstance(node.get("certificate_hash"), str):
                certificates.append(node)
            if schema == event_schema and isinstance(node.get("event_hash"), str):
                events.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            if cert_schema in node or event_schema in node:
                try:
                    walk(json.loads(node))
                except json.JSONDecodeError:
                    return

    walk(obj)
    return certificates, events


def load_immutable_production_bundle(root: Path) -> dict[str, Any]:
    manifest_path = root / COMPLETION_MANIFEST_REL
    ratings_path = root / RATINGS_EVIDENCE_REL
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pin = manifest["candidate_rating_execution_evidence"]
    if pin["path"] != RATINGS_EVIDENCE_REL:
        return {
            "status": "MANIFEST_RATINGS_PATH_MISMATCH",
            "certificates": [],
            "events": [],
        }
    ratings_sha = _sha256_file(ratings_path)
    if ratings_sha != pin["sha256"]:
        return {
            "status": "PINNED_RATINGS_SHA256_MISMATCH",
            "certificates": [],
            "events": [],
            "expected_sha256": pin["sha256"],
            "actual_sha256": ratings_sha,
        }
    ratings = json.loads(ratings_path.read_text(encoding="utf-8"))
    certificates, events = _extract_nested(
        ratings,
        cert_schema=R2A_CERTIFICATE_SCHEMA,
        event_schema=R2A_EVENT_SCHEMA,
    )
    candidate = ratings["candidates"][CANDIDATE_B_ID]
    provenance = candidate["mesh_ledger_projection"]["per_mesh_r2a_provenance"][0]
    return {
        "status": "LOADED",
        "completion_manifest_rel": COMPLETION_MANIFEST_REL,
        "ratings_evidence_rel": RATINGS_EVIDENCE_REL,
        "raw_evidence_sha256": ratings_sha,
        "producer_git_commit_head": ratings.get("production_runtime_head"),
        "producer_source_tree": ratings.get("production_runtime_tree"),
        "producer_symbol": "_candidate_transient_outer_boundary",
        "candidate_id": CANDIDATE_B_ID,
        "candidate_hash": candidate["candidate_hash"],
        "rating_request_hash": candidate["candidate_rating_request_hash"],
        "certificates": certificates,
        "events": events,
        "outer_trial_provenance": provenance,
        "event_projection_status": "PRESENT" if events else "MISSING",
    }
