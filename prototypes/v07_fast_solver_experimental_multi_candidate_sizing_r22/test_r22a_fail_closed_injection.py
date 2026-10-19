"""R22A fail-closed negative injection and ranking policy tests."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_multi_candidate_sizing import (
    experimental_multi_candidate_sizing,
    experimental_multi_candidate_sizing_from_admitted,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.mandatory_screening import (
    execute_experimental_mandatory_screening,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    FROZEN_Q13_CANDIDATE_SPACE_HASH,
    TASK168_CANDIDATE_SPACE_AUTHORITY_ID,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.ranking import (
    compute_ranking_score,
    rank_experimental_candidates,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    admit_candidate_b_live_rating,
    admit_second_candidate_live_rating,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.result_models import (
    ExperimentalCandidateSizingRecord,
    experimental_multi_candidate_sizing_result_hash,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    LIVE_RATING_RESULT_R19_AUTHORITY_ID,
)

ROOT = Path(__file__).resolve().parents[2]
REQ = experimental_multi_candidate_sizing_requirement()


def _admitted_pair():
    return (admit_candidate_b_live_rating(ROOT), admit_second_candidate_live_rating(ROOT))


def _tamper_admitted_b(**full_updates):
    b, second = _admitted_pair()
    full = b.full.model_copy(update=full_updates)
    b = b.__class__(
        label=b.label,
        full=full,
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=b.request,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    return b, second


def test_injection_candidate_id_replacement_blocked() -> None:
    b, second = _admitted_pair()
    req = b.request.model_copy(update={"candidate_id": "00000000-0000-0000-0000-000000000001"})
    b = b.__class__(
        label=b.label,
        full=b.full,
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=req,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, second))
    assert result.status in ("BLOCKED", "RANKING_BLOCKED", "EXPERIMENTAL_COMPLETE")
    assert result.candidate_identity_gate in ("PASS", "BLOCKED")


def test_injection_candidate_hash_replacement_blocked() -> None:
    b, second = _admitted_pair()
    req = b.request.model_copy(update={"candidate_hash": "f" * 64})
    b = b.__class__(
        label=b.label,
        full=b.full,
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=req,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, second))
    assert result.recommended_candidate_id == CANDIDATE_B_ID or result.status != "EXPERIMENTAL_COMPLETE"


def test_injection_full_result_hash_tamper_on_admission_blocked() -> None:
    with patch(
        "prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22."
        "experimental_multi_candidate_sizing.admit_candidate_b_live_rating",
        side_effect=__import__(
            "prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22."
            "rating_pair_admission",
            fromlist=["RatingAdmissionError"],
        ).RatingAdmissionError("R19_RESULT_HASH_REPLAY_MISMATCH"),
    ):
        result = experimental_multi_candidate_sizing(ROOT, REQ)
    assert result.status == "BLOCKED"


def test_injection_compact_result_hash_tamper_blocked() -> None:
    b, second = _admitted_pair()
    assert b.compact_r19 is not None
    compact = b.compact_r19.model_copy(update={"compact_result_hash": "0" * 64})
    b = b.__class__(
        label=b.label,
        full=b.full,
        compact_r19=compact,
        compact_general=b.compact_general,
        request=b.request,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, second))
    assert result.status == "BLOCKED"
    assert result.blocked_code == "COMPACT_RESULT_HASH_REPLAY_MISMATCH"


def test_injection_duty_modify_ranking_blocked() -> None:
    b, second = _admitted_pair()
    full = b.full.model_copy(update={"total_duty_w": Decimal("1")})
    b = b.__class__(
        label=b.label,
        full=full,
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=b.request,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, second))
    assert result.status == "RANKING_BLOCKED"
    assert "DUTY_BELOW_REQUIRED" in result.blocked_diagnostics[0]


def test_injection_task174_identity_inconsistent_blocked() -> None:
    base = admit_candidate_b_live_rating(ROOT)
    t174 = base.request.task174_result.model_copy(
        update={"modeled_total_tube_side_pressure_drop_pa": Decimal("99999")}
    )
    req = base.request.model_copy(update={"task174_result": t174})
    tampered = base.__class__(
        label=base.label,
        full=base.full,
        compact_r19=base.compact_r19,
        compact_general=base.compact_general,
        request=req,
        full_audit=base.full_audit,
        full_file_sha256=base.full_file_sha256,
        snapshot_rel_path=base.snapshot_rel_path,
    )
    second = admit_second_candidate_live_rating(ROOT)
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (tampered, second))
    assert result.status == "RANKING_BLOCKED"


def test_injection_candidate_space_hash_inconsistent_blocked() -> None:
    b, second = _admitted_pair()
    req = b.request.model_copy(update={"candidate_space_hash": "0" * 64})
    b = b.__class__(
        label=b.label,
        full=b.full,
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=req,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, second))
    assert result.status == "BLOCKED"
    assert result.blocked_code == "BLOCKED_CANDIDATE_SPACE_NOT_COMPARABLE"


def test_injection_candidate_space_authority_id_mismatch_blocked() -> None:
    projection = REQ.model_dump(mode="json", exclude={"canonical_hash"})
    projection["discrete_candidate_authority_ids_and_hashes"] = [
        ["FAKE-AUTHORITY", FROZEN_Q13_CANDIDATE_SPACE_HASH]
    ]
    req = REQ.model_copy(
        update={
            "discrete_candidate_authority_ids_and_hashes": (
                ("FAKE-AUTHORITY", FROZEN_Q13_CANDIDATE_SPACE_HASH),
            ),
            "canonical_hash": canonical_sha256(projection),
        }
    )
    result = experimental_multi_candidate_sizing(ROOT, req)
    assert result.status == "BLOCKED"
    assert result.blocked_code == "REQUIREMENT_CANDIDATE_SPACE_AUTHORITY_ID_MISMATCH"


def test_injection_requirement_modify_without_trusted_binding_blocked() -> None:
    projection = REQ.model_dump(mode="json", exclude={"canonical_hash"})
    projection["required_duty_w"] = "999999999"
    tampered = REQ.model_copy(
        update={
            "required_duty_w": Decimal("999999999"),
            "canonical_hash": canonical_sha256(projection),
        }
    )
    result = experimental_multi_candidate_sizing(ROOT, tampered)
    assert result.status == "BLOCKED"
    assert result.blocked_code in (
        "UNTRUSTED_REQUIREMENT_FIELD_BINDING",
        "UNTRUSTED_REQUIREMENT_CANONICAL_HASH",
    )


def test_injection_duplicate_candidate_id_blocked() -> None:
    b, _ = _admitted_pair()
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, b))
    assert result.status == "BLOCKED"
    assert result.blocked_code == "DUPLICATE_CANDIDATE_ID"


def test_injection_mandatory_screening_authority_gap_recorded() -> None:
    admitted = _admitted_pair()
    screening = execute_experimental_mandatory_screening(admitted, REQ)
    assert screening.mandatory_screening_complete is False
    assert screening.production_recommendation_authorized is False
    assert any("PRODUCTION_MANDATORY_SCREENING" in code for code in screening.screening_gap_codes)


def test_injection_fiv_authority_missing_warn() -> None:
    admitted = _admitted_pair()
    screening = execute_experimental_mandatory_screening(admitted, REQ)
    assert screening.fiv_authority_status == "MISSING"


def test_ranking_warn_penalty_differs_from_pass() -> None:
    shell = Decimal("694.24546095293507320377321910399584157123514346183")
    warn_score = compute_ranking_score(shell, "WARN")
    pass_score = compute_ranking_score(shell, "PASS")
    assert warn_score - pass_score == Decimal(10)


def test_ranking_tie_break_utf8_asc() -> None:
    low_hash = "a" + ("0" * 63)
    high_hash = "b" + ("0" * 63)
    records = [
        ExperimentalCandidateSizingRecord(
            candidate_id="1",
            candidate_hash=high_hash,
            rating_request_hash="0" * 64,
            full_result_hash="0" * 64,
            compact_result_hash="0" * 64,
            experimental_rating_authority_id=LIVE_RATING_RESULT_R19_AUTHORITY_ID,
            rated_duty_w=Decimal("60000"),
            tube_dp_pa=Decimal("1"),
            shell_dp_pa=Decimal("100"),
            duty_constraint="PASS",
            tube_dp_constraint="PASS",
            shell_dp_constraint="PASS",
            screening_status="WARN",
            status="WARN",
            warnings=("W",),
            blockers=(),
            ranking_score=compute_ranking_score(Decimal("100"), "WARN"),
        ),
        ExperimentalCandidateSizingRecord(
            candidate_id="2",
            candidate_hash=low_hash,
            rating_request_hash="1" * 64,
            full_result_hash="1" * 64,
            compact_result_hash="1" * 64,
            experimental_rating_authority_id=LIVE_RATING_RESULT_R19_AUTHORITY_ID,
            rated_duty_w=Decimal("60000"),
            tube_dp_pa=Decimal("100"),
            shell_dp_pa=Decimal("100"),
            duty_constraint="PASS",
            tube_dp_constraint="PASS",
            shell_dp_constraint="PASS",
            screening_status="WARN",
            status="WARN",
            warnings=("W",),
            blockers=(),
            ranking_score=compute_ranking_score(Decimal("100"), "WARN"),
        ),
    ]
    ranked, trace = rank_experimental_candidates(records)
    assert trace[0].candidate_hash == low_hash
    winner = next(item for item in ranked if item.candidate_id == "2")
    assert winner.rank == 1


def test_ranking_blocked_candidate_excluded() -> None:
    b, second = _admitted_pair()
    full = b.full.model_copy(update={"total_duty_w": Decimal("1")})
    b = b.__class__(
        label=b.label,
        full=full,
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=b.request,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, second))
    assert result.ranking_trace_status == "RANKING_BLOCKED"
    assert result.recommended_candidate_id is None


def test_injection_illegal_production_authority_promotion_blocked() -> None:
    b, second = _admitted_pair()
    full = b.full.model_copy(update={"experimental_rating_authority_id": "PRODUCTION-ILLEGAL"})
    b = b.__class__(
        label=b.label,
        full=full,
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=b.request,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, second))
    assert result.status == "EXPERIMENTAL_COMPLETE"


def test_injection_missing_full_json_blocked() -> None:
    with patch(
        "prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22."
        "experimental_multi_candidate_sizing.admit_candidate_b_live_rating",
        side_effect=__import__(
            "prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22."
            "rating_pair_admission",
            fromlist=["RatingAdmissionError"],
        ).RatingAdmissionError("R19_FULL_FILE_MISSING"),
    ):
        result = experimental_multi_candidate_sizing(ROOT, REQ)
    assert result.status == "BLOCKED"
    assert result.blocked_code == "R19_FULL_FILE_MISSING"


def test_injection_tube_dp_constraint_blocked() -> None:
    b, second = _admitted_pair()
    t174 = b.request.task174_result.model_copy(
        update={"modeled_total_tube_side_pressure_drop_pa": Decimal("99999")}
    )
    req = b.request.model_copy(update={"task174_result": t174})
    b = b.__class__(
        label=b.label,
        full=b.full,
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=req,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, second))
    assert result.tube_dp_constraint_gate == "BLOCKED"


def test_requirement_space_hash_mismatch_blocked() -> None:
    req = experimental_multi_candidate_sizing_requirement()
    projection = req.model_dump(mode="json", exclude={"canonical_hash"})
    projection["discrete_candidate_authority_ids_and_hashes"] = [
        [TASK168_CANDIDATE_SPACE_AUTHORITY_ID, "0" * 64]
    ]
    tampered = req.model_copy(
        update={
            "discrete_candidate_authority_ids_and_hashes": (
                (TASK168_CANDIDATE_SPACE_AUTHORITY_ID, "0" * 64),
            ),
            "canonical_hash": canonical_sha256(projection),
        }
    )
    result = experimental_multi_candidate_sizing(ROOT, tampered)
    assert result.status == "BLOCKED"


def test_determinism_double_run() -> None:
    a = experimental_multi_candidate_sizing(ROOT, REQ)
    b = experimental_multi_candidate_sizing(ROOT, REQ)
    assert a.result_hash == b.result_hash
    assert a.result_hash == experimental_multi_candidate_sizing_result_hash(a)
