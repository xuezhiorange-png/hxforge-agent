"""Minimum additional numerical qualification when frozen evidence cannot replay R2A."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any


def minimum_r2a_qualification_requirements(ledger_rows: list[dict[str, Any]]) -> dict[str, Any]:
    insufficient = [
        row
        for row in ledger_rows
        if row.get("admission_status") in {"FROZEN_EVIDENCE_INSUFFICIENT", "NO_TRIGGER_PROVEN"}
        and row.get("production_r2a_certificate_replay") == "BLOCKED"
    ]
    return {
        "schema_version": "task173.r2a-minimum-qualification-requirements.v1",
        "trigger": "Frozen R19/R21E live mesh receipts lack production R2A event/certificate projections.",
        "required_inputs": [
            "Production Task173 rating replay bundle per mesh_n with transient_provider_enclosure_event projections",
            "outer_decision_certificate_projections matching service.py production schema",
            "Endpoint Task172 request/result rehydration records for Q1-Q15 replay",
            "Outer trial JSONL binding certificate trigger_support_id to recorded outer iteration",
        ],
        "budget_constraints": {
            "max_wall_seconds_per_mesh": 1800,
            "allowed_mesh_levels": [32, 64],
            "forbidden_in_this_task": [
                "Full heat exchanger re-solve beyond pinned replay",
                "Outer boundary re-execution for R19/R21E goldens",
            ],
        },
        "acceptance_criteria": [
            "verify_r2a_certificate_evidence returns CERTIFICATE_PRESENT_VERIFIED or NO_TRIGGER_PROVEN with documented acceptance path",
            "Event and certificate hash replay passes",
            "Q1 and Q15 predicates recompute from endpoint projections",
            "Candidate/request/mesh hash binding matches frozen CandidateRatingRequest",
        ],
        "expected_evidence_artifacts": [
            "R2A_CERTIFICATE_ADMISSION_RESULT.json per candidate mesh",
            "Pinned certificate projection JSON with git blob SHA256",
        ],
        "affected_meshes": [
            {
                "label": row.get("label"),
                "mesh_n": row.get("mesh_n"),
                "mesh_role": row.get("mesh_role"),
                "admission_status": row.get("admission_status"),
            }
            for row in insufficient
        ],
    }
