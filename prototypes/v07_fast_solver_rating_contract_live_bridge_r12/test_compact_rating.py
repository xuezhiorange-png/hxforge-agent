"""Compact rating linkage to frozen R11 full artifact."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
)
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
    CANDIDATE_B_ID,
    R11_RATING_JSON_REL,
    R11_RATING_JSON_SHA256,
    R11_RESULT_HASH,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.compact_rating import (
    build_compact_from_full,
    compact_rating_hash,
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)

ROOT = Path(__file__).resolve().parents[2]


def _candidate_b_request() -> CandidateRatingRequest:
    runner = (
        ROOT
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _c, req_raw = mod._build_candidate_requests()[CANDIDATE_B_ID]
    if type(req_raw) is not CandidateRatingRequest:
        req_raw = CandidateRatingRequest.model_validate_json(
            json.dumps(req_raw, separators=(",", ":"), ensure_ascii=False),
            strict=True,
        )
    return req_raw


def test_compact_links_to_r11_full_hash() -> None:
    full = ExperimentalCandidateRatingResult.model_validate_json(
        (ROOT / R11_RATING_JSON_REL).read_text(encoding="utf-8"),
        strict=True,
    )
    geom = geometry_summary_from_request(_candidate_b_request())
    compact = build_compact_from_full(
        full,
        trajectory_artifact_path=R11_RATING_JSON_REL,
        trajectory_file_sha256=R11_RATING_JSON_SHA256,
        geometry_summary=geom,
    )
    assert compact.full_result_hash == R11_RESULT_HASH
    assert compact.compact_result_hash == compact_rating_hash(compact)
    assert compact.geometry_summary.task171_topology_id == geom.task171_topology_id
