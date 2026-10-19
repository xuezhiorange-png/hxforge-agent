"""Discover the non–Candidate-B sizing candidate with frozen upstream authority."""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_rating_authority_admission_r11.geometry_summary import (
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_task174_binding,
)

ROOT = Path(__file__).resolve().parents[2]
FROZEN_RUNNER = (
    ROOT / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
)
SECOND_CANDIDATE_ID = "adeab5b1-a339-5eb3-aa66-011ffe49bac0"
EXPECTED_SECOND_CANDIDATE_HASH = "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767"
EXPECTED_SECOND_RATING_REQUEST_HASH = (
    "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7"
)


@dataclass(frozen=True)
class SecondCandidateDiscovery:
    status: str
    candidate_id: str
    candidate_hash: str
    rating_request_hash: str
    geometry_summary: dict[str, str]
    upstream_authority_checks: tuple[tuple[str, str], ...]
    blocked_code: str | None = None
    blocked_diagnostics: tuple[str, ...] = ()


def _load_frozen_requests() -> dict[str, tuple[object, CandidateRatingRequest]]:
    spec = importlib.util.spec_from_file_location("q13", FROZEN_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("frozen candidate runner missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    found = mod._build_candidate_requests()
    out: dict[str, tuple[object, CandidateRatingRequest]] = {}
    for candidate_id, pair in found.items():
        _candidate, rating_request = pair
        if type(rating_request) is not CandidateRatingRequest:
            encoded = json.dumps(rating_request, separators=(",", ":"), ensure_ascii=False)
            rating_request = CandidateRatingRequest.model_validate_json(encoded, strict=True)
        out[candidate_id] = (_candidate, rating_request)
    return out


def discover_second_candidate() -> SecondCandidateDiscovery:
    try:
        requests = _load_frozen_requests()
    except Exception as exc:  # noqa: BLE001 — discovery must fail closed
        return SecondCandidateDiscovery(
            status="BLOCKED",
            candidate_id="",
            candidate_hash="",
            rating_request_hash="",
            geometry_summary={},
            upstream_authority_checks=(),
            blocked_code="BLOCKED_NO_VALID_SECOND_CANDIDATE",
            blocked_diagnostics=(f"frozen_runner:{exc}",),
        )

    if SECOND_CANDIDATE_ID not in requests:
        return SecondCandidateDiscovery(
            status="BLOCKED",
            candidate_id="",
            candidate_hash="",
            rating_request_hash="",
            geometry_summary={},
            upstream_authority_checks=(),
            blocked_code="BLOCKED_NO_VALID_SECOND_CANDIDATE",
            blocked_diagnostics=("missing_second_candidate_id",),
        )
    if SECOND_CANDIDATE_ID == CANDIDATE_B_ID:
        return SecondCandidateDiscovery(
            status="BLOCKED",
            candidate_id=SECOND_CANDIDATE_ID,
            candidate_hash="",
            rating_request_hash="",
            geometry_summary={},
            upstream_authority_checks=(),
            blocked_code="BLOCKED_NO_VALID_SECOND_CANDIDATE",
            blocked_diagnostics=("second_candidate_is_candidate_b",),
        )

    _candidate, request = requests[SECOND_CANDIDATE_ID]
    rating_hash = candidate_rating_request_hash(request)
    distinct = "PASS" if request.candidate_id != CANDIDATE_B_ID else "FAIL"
    hash_ok = "PASS" if request.candidate_hash == EXPECTED_SECOND_CANDIDATE_HASH else "FAIL"
    checks: list[tuple[str, str]] = [
        ("candidate_id_distinct_from_b", distinct),
        ("candidate_hash_pinned", hash_ok),
        (
            "rating_request_hash_pinned",
            "PASS" if rating_hash == EXPECTED_SECOND_RATING_REQUEST_HASH else "FAIL",
        ),
        ("task171_validated", "PASS" if request.task171_result.status == "VALIDATED" else "FAIL"),
        ("task174_binding", "PASS" if verify_task174_binding(request) else "FAIL"),
    ]
    if any(status == "FAIL" for _, status in checks):
        return SecondCandidateDiscovery(
            status="BLOCKED",
            candidate_id=request.candidate_id,
            candidate_hash=request.candidate_hash,
            rating_request_hash=rating_hash,
            geometry_summary={},
            upstream_authority_checks=tuple(checks),
            blocked_code="BLOCKED_NO_VALID_SECOND_CANDIDATE",
            blocked_diagnostics=tuple(f"{k}={v}" for k, v in checks if v == "FAIL"),
        )

    geom = geometry_summary_from_request(request)
    return SecondCandidateDiscovery(
        status="DISCOVERED",
        candidate_id=request.candidate_id,
        candidate_hash=request.candidate_hash,
        rating_request_hash=rating_hash,
        geometry_summary={
            "task171_topology_id": geom.task171_topology_id,
            "task171_mesh_identity": geom.task171_mesh_identity,
            "interval_count": str(geom.interval_count),
        },
        upstream_authority_checks=tuple(checks),
    )


def load_second_candidate_rating_request() -> CandidateRatingRequest:
    discovery = discover_second_candidate()
    if discovery.status != "DISCOVERED":
        raise ValueError(discovery.blocked_code or "second candidate not discovered")
    return _load_frozen_requests()[SECOND_CANDIDATE_ID][1]
