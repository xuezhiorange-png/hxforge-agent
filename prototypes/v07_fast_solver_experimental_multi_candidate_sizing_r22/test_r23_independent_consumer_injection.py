"""R23 independent consumer admission — strict negative injection."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_multi_candidate_sizing import (
    experimental_multi_candidate_sizing,
    experimental_multi_candidate_sizing_from_admitted,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.mandatory_screening import (
    MandatoryScreeningOutcome,
    ScreeningRuleRecord,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    admit_candidate_b_live_rating,
    admit_second_candidate_live_rating,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    live_rating_result_hash,
)

ROOT = Path(__file__).resolve().parents[2]
REQ = experimental_multi_candidate_sizing_requirement()


def _pair():
    return (admit_candidate_b_live_rating(ROOT), admit_second_candidate_live_rating(ROOT))


def test_injection_rating_request_hash_tamper_blocked() -> None:
    b, second = _pair()
    req = b.request.model_copy(update={})
    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        candidate_rating_request_hash,
    )

    forged_hash = "f" * 64
    if candidate_rating_request_hash(req) == forged_hash:
        forged_hash = "e" * 64
    req = b.request.model_copy(update={})
    b = b.__class__(
        label=b.label,
        full=b.full.model_copy(update={"rating_request_hash": forged_hash}),
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=req,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, second))
    assert result.status == "BLOCKED"
    assert result.blocked_code in (
        "RATING_REQUEST_HASH_REPLAY_MISMATCH",
        "FULL_RESULT_HASH_REPLAY_MISMATCH",
    )


def test_injection_full_duty_modify_rehash_blocked() -> None:
    b, second = _pair()
    tampered = b.full.model_copy(update={"total_duty_w": b.full.total_duty_w + Decimal("1")})
    digest = live_rating_result_hash(tampered)
    rebinding = tampered.model_copy(update={"result_hash": digest})
    b = b.__class__(
        label=b.label,
        full=rebinding,
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=b.request,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (b, second))
    assert result.status == "BLOCKED"
    assert result.status == "BLOCKED"
    assert result.blocked_code in (
        "FULL_RESULT_HASH_REPLAY_MISMATCH",
        "COMPACT_FULL_ENGINEERING_PARITY_MISMATCH",
        "COMPACT_FULL_RESULT_HASH_MISMATCH",
    )


def test_injection_task174_modify_blocked() -> None:
    b, second = _pair()
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
    assert result.status == "BLOCKED"
    assert result.blocked_code in (
        "TASK174_RESULT_HASH_REPLAY_MISMATCH",
        "RATING_REQUEST_HASH_REPLAY_MISMATCH",
    )


def test_injection_full_compact_swap_blocked() -> None:
    b, second = _pair()
    swapped = b.__class__(
        label=b.label,
        full=b.full,
        compact_r19=second.compact_general,
        compact_general=None,
        request=b.request,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (swapped, second))
    assert result.status == "BLOCKED"


def test_injection_untrusted_admitted_bundle_label_blocked() -> None:
    b, second = _pair()
    rogue = b.__class__(
        label="CALLER_FORGED_BUNDLE",
        full=b.full,
        compact_r19=b.compact_r19,
        compact_general=None,
        request=b.request,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (rogue, second))
    assert result.status == "BLOCKED"
    assert result.blocked_code == "UNTRUSTED_ADMITTED_BUNDLE_LABEL"


def test_injection_requirement_rehash_untrusted_blocked() -> None:
    projection = REQ.model_dump(mode="json", exclude={"canonical_hash"})
    projection["max_tube_dp_pa"] = "2000"
    tampered = REQ.model_copy(
        update={
            "max_tube_dp_pa": Decimal("2000"),
            "canonical_hash": canonical_sha256(projection),
        }
    )
    result = experimental_multi_candidate_sizing(ROOT, tampered)
    assert result.status == "BLOCKED"
    assert result.blocked_code in (
        "UNTRUSTED_REQUIREMENT_CANONICAL_HASH",
        "UNTRUSTED_REQUIREMENT_FIELD_BINDING",
    )


def test_injection_forged_screening_outcome_blocked() -> None:
    b, second = _pair()
    forged = MandatoryScreeningOutcome(
        mandatory_screening_gate="PRODUCTION_COMPLETE",
        mandatory_screening_complete=True,
        production_recommendation_authorized=True,
        fiv_authority_status="PRESENT",
        rule_records=(
            ScreeningRuleRecord(
                rule_id="FORGED",
                outcome="EXECUTED",
                detail="forged",
                provenance=(("forged", "true"),),
            ),
        ),
        screening_gap_codes=(),
    )
    result = experimental_multi_candidate_sizing_from_admitted(
        REQ,
        (b, second),
        screening=forged,
    )
    assert result.status == "BLOCKED"
    assert result.blocked_code == "FORGED_MANDATORY_SCREENING_OUTCOME"


def test_injection_pair_role_order_reversed_blocked() -> None:
    b, second = _pair()
    result = experimental_multi_candidate_sizing_from_admitted(REQ, (second, b))
    assert result.status == "BLOCKED"
    assert result.blocked_code == "ADMITTED_PAIR_ROLE_ORDER_MISMATCH"


def test_determinism_two_runs() -> None:
    a = experimental_multi_candidate_sizing(ROOT, REQ)
    b = experimental_multi_candidate_sizing(ROOT, REQ)
    assert a.result_hash == b.result_hash
