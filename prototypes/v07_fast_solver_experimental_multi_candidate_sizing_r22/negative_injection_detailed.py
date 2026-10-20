"""Execute negative injection cases and record deterministic BLOCKED codes."""

# ruff: noqa: E501

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    recompute_task174_result_hash,
)
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
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    admit_candidate_b_live_rating,
    admit_second_candidate_live_rating,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    live_rating_result_hash,
)

REQ = experimental_multi_candidate_sizing_requirement()


@dataclass(frozen=True)
class InjectionCase:
    test_id: str
    tamper_type: str
    expected_blocked_codes: tuple[str, ...]
    runner: Callable[[Path], Any]


def _pair(root: Path):
    return (admit_candidate_b_live_rating(root), admit_second_candidate_live_rating(root))


def _record(result: Any, expected: tuple[str, ...]) -> dict[str, str]:
    actual = getattr(result, "blocked_code", None) or "NOT_BLOCKED"
    status = result.status if hasattr(result, "status") else str(result)
    passed = status == "BLOCKED" and actual in expected
    return {
        "EXPECTED_BLOCKED_CODE": "|".join(expected),
        "ACTUAL_BLOCKED_CODE": str(actual),
        "RESULT": "PASS" if passed else "FAIL",
        "STATUS": str(status),
    }


def run_negative_injection_detailed(root: Path) -> list[dict[str, str]]:
    cases: list[InjectionCase] = []

    def case_full_duty_rehash(r: Path):
        b, second = _pair(r)
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
        return experimental_multi_candidate_sizing_from_admitted(REQ, (b, second), evidence_root=r)

    cases.append(
        InjectionCase(
            "R24-001",
            "FULL_DUTY_MODIFY_REHASH",
            (
                "PINNED_FULL_STRUCTURAL_MISMATCH",
                "FULL_RESULT_HASH_REPLAY_MISMATCH",
                "COMPACT_FULL_ENGINEERING_PARITY_MISMATCH",
                "COMPACT_FULL_RESULT_HASH_MISMATCH",
            ),
            case_full_duty_rehash,
        )
    )

    def case_task171_embedded(r: Path):
        b, second = _pair(r)
        t171 = b.request.task171_result
        topo = t171.topology_definition
        if topo is None:
            return experimental_multi_candidate_sizing_from_admitted(
                REQ, (b, second), evidence_root=r
            )
        intervals = list(topo.intervals)
        first = intervals[0].model_copy(
            update={"start_m": str(Decimal(str(intervals[0].start_m)) + Decimal("0.01"))}
        )
        intervals[0] = first
        bad_topo = topo.model_copy(update={"intervals": tuple(intervals)})
        bad_t171 = t171.model_copy(update={"topology_definition": bad_topo})
        req = b.request.model_copy(update={"task171_result": bad_t171})
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
        return experimental_multi_candidate_sizing_from_admitted(REQ, (b, second), evidence_root=r)

    cases.append(
        InjectionCase(
            "R24-002",
            "TASK171_EMBEDDED_MODIFY",
            (
                "PINNED_REQUEST_STRUCTURAL_MISMATCH",
                "TASK174_RESULT_HASH_REPLAY_MISMATCH",
                "RATING_REQUEST_HASH_REPLAY_MISMATCH",
                "TASK171_TASK174_UPSTREAM_HASH_BINDING_MISMATCH",
            ),
            case_task171_embedded,
        )
    )

    def case_forged_sha(r: Path):
        b, second = _pair(r)
        b = b.__class__(
            label=b.label,
            full=b.full,
            compact_r19=b.compact_r19,
            compact_general=b.compact_general,
            request=b.request,
            full_audit=b.full_audit,
            full_file_sha256="0" * 64,
            snapshot_rel_path=b.snapshot_rel_path,
        )
        return experimental_multi_candidate_sizing_from_admitted(REQ, (b, second), evidence_root=r)

    cases.append(
        InjectionCase(
            "R24-003",
            "FORGED_FULL_FILE_SHA256",
            ("FORGED_FULL_FILE_SHA256_DECLARATION",),
            case_forged_sha,
        )
    )

    def case_no_root(r: Path):
        b, second = _pair(r)
        return experimental_multi_candidate_sizing_from_admitted(
            REQ, (b, second), evidence_root=None
        )

    cases.append(
        InjectionCase(
            "R24-004",
            "MISSING_EVIDENCE_ROOT",
            ("UNTRUSTED_EVIDENCE_ROOT_MISSING",),
            case_no_root,
        )
    )

    def case_forged_screening_rule(r: Path):
        b, second = _pair(r)
        expected = execute_experimental_mandatory_screening((b, second), REQ)
        records = list(expected.rule_records)
        bad = records[0].model_copy(update={"detail": "tampered"})
        records[0] = bad
        forged = expected.model_copy(update={"rule_records": tuple(records)})
        return experimental_multi_candidate_sizing_from_admitted(
            REQ, (b, second), evidence_root=r, screening=forged
        )

    cases.append(
        InjectionCase(
            "R24-005",
            "FORGED_SCREENING_RULE_RECORD",
            ("FORGED_MANDATORY_SCREENING_OUTCOME",),
            case_forged_screening_rule,
        )
    )

    def case_requirement_rehash(r: Path):
        projection = REQ.model_dump(mode="json", exclude={"canonical_hash"})
        projection["max_shell_dp_pa"] = "6000"
        tampered = REQ.model_copy(
            update={
                "max_shell_dp_pa": Decimal("6000"),
                "canonical_hash": canonical_sha256(projection),
            }
        )
        return experimental_multi_candidate_sizing(r, tampered)

    cases.append(
        InjectionCase(
            "R24-006",
            "REQUIREMENT_REHASH_UNTRUSTED",
            ("UNTRUSTED_REQUIREMENT_CANONICAL_HASH", "UNTRUSTED_REQUIREMENT_FIELD_BINDING"),
            case_requirement_rehash,
        )
    )

    def case_task174_rehash(r: Path):
        b, second = _pair(r)
        t174 = b.request.task174_result.model_copy(
            update={"modeled_total_tube_side_pressure_drop_pa": Decimal("99999")}
        )
        t174 = t174.model_copy(update={"result_hash": recompute_task174_result_hash(t174)})
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
        return experimental_multi_candidate_sizing_from_admitted(REQ, (b, second), evidence_root=r)

    cases.append(
        InjectionCase(
            "R24-007",
            "TASK174_MODIFY_REHASH",
            (
                "PINNED_REQUEST_STRUCTURAL_MISMATCH",
                "TASK174_RESULT_HASH_REPLAY_MISMATCH",
                "RATING_REQUEST_HASH_REPLAY_MISMATCH",
            ),
            case_task174_rehash,
        )
    )

    def case_frozen_request_replace(r: Path):
        b, second = _pair(r)
        b = b.__class__(
            label=b.label,
            full=b.full,
            compact_r19=b.compact_r19,
            compact_general=b.compact_general,
            request=second.request,
            full_audit=b.full_audit,
            full_file_sha256=b.full_file_sha256,
            snapshot_rel_path=b.snapshot_rel_path,
        )
        return experimental_multi_candidate_sizing_from_admitted(REQ, (b, second), evidence_root=r)

    cases.append(
        InjectionCase(
            "R24-008",
            "FROZEN_REQUEST_REPLACE",
            (
                "PINNED_REQUEST_STRUCTURAL_MISMATCH",
                "RATING_REQUEST_HASH_REPLAY_MISMATCH",
                "ADMITTED_REQUEST_CANDIDATE_ID_BINDING_MISMATCH",
            ),
            case_frozen_request_replace,
        )
    )

    def case_full_compact_joint_rehash(r: Path):
        b, second = _pair(r)
        tampered = b.full.model_copy(update={"total_duty_w": b.full.total_duty_w + Decimal("1")})
        digest = live_rating_result_hash(tampered)
        rebinding = tampered.model_copy(update={"result_hash": digest})
        assert b.compact_r19 is not None
        compact = b.compact_r19.model_copy(
            update={"compact_result_hash": live_rating_result_hash(rebinding)}
        )
        b = b.__class__(
            label=b.label,
            full=rebinding,
            compact_r19=compact,
            compact_general=b.compact_general,
            request=b.request,
            full_audit=b.full_audit,
            full_file_sha256=b.full_file_sha256,
            snapshot_rel_path=b.snapshot_rel_path,
        )
        return experimental_multi_candidate_sizing_from_admitted(REQ, (b, second), evidence_root=r)

    cases.append(
        InjectionCase(
            "R24-009",
            "FULL_COMPACT_JOINT_REHASH",
            (
                "PINNED_FULL_STRUCTURAL_MISMATCH",
                "PINNED_COMPACT_STRUCTURAL_MISMATCH",
                "FULL_RESULT_HASH_REPLAY_MISMATCH",
                "COMPACT_RESULT_HASH_REPLAY_MISMATCH",
            ),
            case_full_compact_joint_rehash,
        )
    )

    out: list[dict[str, str]] = []
    for item in cases:
        result = item.runner(root)
        row = {
            "TEST_ID": item.test_id,
            "TAMPER_TYPE": item.tamper_type,
            **_record(result, item.expected_blocked_codes),
        }
        out.append(row)
    return out
