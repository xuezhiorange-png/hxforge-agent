"""Low-cost Task168 enumeration before full Task173 rating."""

from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import ValidationStatus
from hexagent.exchangers.shell_tube.task173_integrated_sizing import Task173SizingRequest


def enumerate_task168_candidates(request: Task173SizingRequest) -> dict[str, Any]:
    outcome = task168.validate_request(request.task168_candidate_request)
    if outcome.status is not ValidationStatus.VALID or outcome.valid is None:
        blockers = []
        branch = getattr(outcome, "typed_blocked", None) or getattr(
            outcome, "raw_boundary_blocked", None
        )
        if branch is not None:
            blockers = [item.code for item in branch.blockers]
        return {
            "status": "BLOCKED",
            "blocked_codes": blockers,
            "candidate_count": 0,
            "candidates": [],
        }
    records = []
    for record in outcome.valid.candidate_records:
        candidate = record.candidate
        records.append(
            {
                "candidate_id": record.candidate_id,
                "candidate_hash": record.candidate_hash,
                "disposition": record.disposition.value,
                "status": record.status.value,
                "tube_length_m": str(candidate.tube_length_m),
                "baffle_spacing_m": str(candidate.baffle_spacing_m),
            }
        )
    distinct_geometry = len(
        {
            (
                str(r["tube_length_m"]),
                str(r["baffle_spacing_m"]),
            )
            for r in records
        }
    )
    structurally_admitted = sum(1 for r in records if r["status"] != "BLOCKED")
    return {
        "status": "VALID",
        "task168_structural_enumeration_status": "VALID",
        "task168_downstream_full_evaluation_status": "NOT_RUN_IN_PREFLIGHT_ONLY",
        "task173_rating_status": "NOT_RUN",
        "candidate_count": len(records),
        "distinct_geometry_count": distinct_geometry,
        "structurally_admitted_count": structurally_admitted,
        "candidates": records,
        "candidate_space_hash": outcome.valid.candidate_space_hash,
        "notes": (
            "Preflight VALID means Task168 request enumeration succeeded; "
            "per-candidate BLOCKED disposition is downstream evaluation, not geometry illegality."
        ),
    }
