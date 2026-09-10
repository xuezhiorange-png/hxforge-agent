"""TASK-169 Golden validation and HXForge v0.6 release acceptance."""

from __future__ import annotations

from dataclasses import replace

from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    CandidateRecord,
    CandidateStatus,
)
from hexagent.exchangers.shell_tube.selection_release.models import (
    SelectionStatus,
    Task169Result,
)
from hexagent.exchangers.shell_tube.selection_release.service import (
    validate_request as validate_selection_request,
)

from .canonical import blocked_hash, blocked_id, request_hash, result_hash, result_id
from .models import (
    AcceptanceGateRecord,
    AcceptanceStatus,
    GoldenAcceptanceRecord,
    GoldenCaseId,
    TASK169_RELEASE_RESULT_SCHEMA_VERSION,
    TASK169_RELEASE_SCHEMA_VERSION,
    TASK169_RELEASE_SOFTWARE_VERSION,
    TASK169_RELEASE_SOURCE_DEFINITION_ID,
    TASK169_RELEASE_VERSION,
    Task169GoldenCase,
    Task169ReleaseBlockedResult,
    Task169ReleaseRequest,
    Task169ReleaseResult,
    Task169ReleaseValidationResult,
)

FROZEN_TOLERANCE_LEDGER = (
    ("ENERGY_BALANCE_RELATIVE_ERROR_MAX", "0.001"),
    ("THERMAL_DUTY_CLOSURE_RELATIVE_ERROR_MAX", "0.001"),
    ("DIRECT_PUBLISHED_EQUATION_REPRODUCTION_RELATIVE_ERROR_MAX", "0.005"),
    ("PUBLISHED_REFERENCE_SHELL_H_RELATIVE_ERROR_MAX", "0.02"),
    ("PUBLISHED_REFERENCE_SHELL_DP_RELATIVE_ERROR_MAX", "0.02"),
    ("MANUFACTURABLE_CATALOG_MEMBERSHIP", "EXACT"),
    ("HARD_CONSTRAINT_STATUS", "EXACT"),
    ("RANKING_ORDER", "EXACT"),
    ("CANONICAL_IDENTITY_REPLAY", "EXACT"),
    ("PY311_PY312_CANONICAL_PARITY", "EXACT"),
)

_GOLDEN_ORDER = (
    GoldenCaseId.V06_G01,
    GoldenCaseId.V06_G02,
    GoldenCaseId.V06_G03,
    GoldenCaseId.V06_G04,
    GoldenCaseId.V06_G05,
)

_GATE_ORDER = (
    "SHELL_TUBE_FIXED_GEOMETRY_RATING",
    "BELL_DELAWARE_HEAT_TRANSFER",
    "BELL_DELAWARE_PRESSURE_DROP",
    "BELL_DELAWARE_PROVENANCE_COMPLETE",
    "SHELL_TUBE_ENGINEERING_SCREENING",
    "THERMAL_EXPANSION_SCREENING",
    "VIBRATION_SCREENING",
    "SHELL_TUBE_CANDIDATE_GENERATION",
    "SHELL_TUBE_SIZING",
    "SHELL_TUBE_MULTI_CANDIDATE_RANKING",
    "TUBE_DP_CONSTRAINT_CLOSURE",
    "SHELL_DP_CONSTRAINT_CLOSURE",
    "THERMAL_DUTY_CLOSURE",
    "DETERMINISTIC_REPLAY",
    "PROVENANCE_COMPLETE",
    "PY311_PY312_PARITY",
    "GOLDEN_V06_G01",
    "GOLDEN_V06_G02",
    "GOLDEN_V06_G03",
    "GOLDEN_V06_G04",
    "GOLDEN_V06_G05",
    "END_TO_END_RELEASE_DEMO",
)


def _blocked(request_hash_value: str, codes: tuple[str, ...]) -> Task169ReleaseValidationResult:
    provisional = Task169ReleaseBlockedResult(
        schema_version=TASK169_RELEASE_RESULT_SCHEMA_VERSION,
        release_version=TASK169_RELEASE_VERSION,
        implementation_software_version=TASK169_RELEASE_SOFTWARE_VERSION,
        request_hash=request_hash_value,
        blocker_codes=tuple(dict.fromkeys(codes)),
        result_hash="",
        result_id="",
    )
    digest = blocked_hash(provisional)
    result = replace(provisional, result_hash=digest, result_id=blocked_id(digest))
    return Task169ReleaseValidationResult(blocked=result)


def _metadata_failures(case: Task169GoldenCase) -> tuple[str, ...]:
    failures: list[str] = []
    if not case.source_id or not case.source_location:
        failures.append("GOLDEN_SOURCE_IDENTITY_REQUIRED")
    if not case.redistribution_status:
        failures.append("GOLDEN_REDISTRIBUTION_STATUS_REQUIRED")
    if not case.normalized_input_identity:
        failures.append("GOLDEN_NORMALIZED_INPUT_IDENTITY_REQUIRED")
    if not case.tolerance_class:
        failures.append("GOLDEN_TOLERANCE_CLASS_REQUIRED")
    if not case.reviewer_evidence_refs:
        failures.append("GOLDEN_REVIEW_EVIDENCE_REQUIRED")
    if not case.provenance_source_hash:
        failures.append("GOLDEN_PROVENANCE_SOURCE_HASH_REQUIRED")
    return tuple(failures)


def _selection(case: Task169GoldenCase) -> Task169Result | None:
    outcome = validate_selection_request(case.selection_request)
    return outcome.valid


def _candidate_for_result(case: Task169GoldenCase, result: Task169Result) -> CandidateRecord | None:
    if result.recommended_candidate is None:
        return None
    candidate_id = result.recommended_candidate.candidate_id
    for record in case.selection_request.task168_result.candidate_records:
        if record.candidate_id == candidate_id:
            return record
    return None


def _full_chain_evidence(record: CandidateRecord | None) -> bool:
    if record is None:
        return False
    groups = (
        record.geometry_evidence,
        record.tube_layout_evidence,
        record.tube_side_evidence,
        record.bell_evidence,
        record.overall_u_ua_evidence,
        record.thermal_closure_evidence,
        record.tube_dp_evidence,
        record.shell_dp_evidence,
        record.screening_evidence,
    )
    return all(groups)


def _constraint(record: CandidateRecord | None, key: str) -> str | None:
    if record is None:
        return None
    return dict(record.constraint_evaluations).get(key)


def _golden_record(
    case: Task169GoldenCase,
    result: Task169Result | None,
) -> GoldenAcceptanceRecord:
    reasons = list(_metadata_failures(case))
    selected = result is not None and result.selection_status is SelectionStatus.SELECTED
    candidate = _candidate_for_result(case, result) if result is not None else None

    if case.golden_id is GoldenCaseId.V06_G01:
        if not selected or candidate is None:
            reasons.append("G01_RECOMMENDATION_REQUIRED")
        elif candidate.candidate.construction_family.value != "FIXED_TUBESHEET":
            reasons.append("G01_FIXED_TUBESHEET_REQUIRED")
        if not _full_chain_evidence(candidate):
            reasons.append("G01_FULL_CHAIN_EVIDENCE_REQUIRED")
    elif case.golden_id is GoldenCaseId.V06_G02:
        if not selected or candidate is None:
            reasons.append("G02_RECOMMENDATION_REQUIRED")
        elif candidate.candidate.construction_family.value != "U_TUBE":
            reasons.append("G02_U_TUBE_REQUIRED")
        if candidate is None or not candidate.screening_evidence:
            reasons.append("G02_SCREENING_EVIDENCE_REQUIRED")
    elif case.golden_id is GoldenCaseId.V06_G03:
        if not selected or candidate is None:
            reasons.append("G03_RECOMMENDATION_REQUIRED")
        elif candidate.candidate.construction_family.value != "FLOATING_HEAD":
            reasons.append("G03_FLOATING_HEAD_REQUIRED")
        if candidate is None or not candidate.screening_evidence:
            reasons.append("G03_SCREENING_EVIDENCE_REQUIRED")
    elif case.golden_id is GoldenCaseId.V06_G04:
        source_records = case.selection_request.task168_result.candidate_records
        hard_dp_rejection = any(
            record.status is CandidateStatus.BLOCKED
            and any(
                blocker.code == "HARD_CONSTRAINT_UNSATISFIED"
                and blocker.field_path in {"max_tube_dp_pa", "max_shell_dp_pa"}
                for blocker in record.blockers
            )
            for record in source_records
        )
        if not selected:
            reasons.append("G04_FEASIBLE_RECOMMENDATION_REQUIRED")
        if len(source_records) < 2:
            reasons.append("G04_MULTI_CANDIDATE_REQUIRED")
        if not hard_dp_rejection:
            reasons.append("G04_DP_CONSTRAINED_REJECTION_REQUIRED")
    else:
        if result is None:
            reasons.append("G05_SELECTION_RESULT_REQUIRED")
        elif result.selection_status is not SelectionStatus.NO_RECOMMENDABLE_CANDIDATE:
            reasons.append("G05_NO_RECOMMENDATION_REQUIRED")
        if not any(
            record.status is CandidateStatus.BLOCKED
            for record in case.selection_request.task168_result.candidate_records
        ):
            reasons.append("G05_FAIL_CLOSED_BLOCKER_REQUIRED")

    return GoldenAcceptanceRecord(
        golden_id=case.golden_id,
        status=AcceptanceStatus.PASS if not reasons else AcceptanceStatus.BLOCKED,
        selection_result_hash=result.result_hash if result is not None else None,
        selection_result_id=result.result_id if result is not None else None,
        recommended_candidate_id=(
            result.recommended_candidate.candidate_id
            if result is not None and result.recommended_candidate is not None
            else None
        ),
        reason_codes=tuple(dict.fromkeys(reasons)),
    )


def _runtime_parity_ok(
    request: Task169ReleaseRequest,
    golden_records: tuple[GoldenAcceptanceRecord, ...],
) -> bool:
    by_runtime = {item.runtime_id: item for item in request.runtime_parity_evidence}
    if set(by_runtime) != {"PYTHON_3_11", "PYTHON_3_12"}:
        return False
    expected = tuple(
        (record.golden_id.value, record.selection_result_hash or "")
        for record in golden_records
    )
    return (
        by_runtime["PYTHON_3_11"].golden_result_hashes == expected
        and by_runtime["PYTHON_3_12"].golden_result_hashes == expected
        and bool(by_runtime["PYTHON_3_11"].evidence_refs)
        and bool(by_runtime["PYTHON_3_12"].evidence_refs)
    )


def _gate(status: bool, gate_id: str, *refs: str) -> AcceptanceGateRecord:
    return AcceptanceGateRecord(
        gate_id=gate_id,
        status=AcceptanceStatus.PASS if status else AcceptanceStatus.BLOCKED,
        evidence_refs=tuple(refs),
    )


def validate_request(raw: object) -> Task169ReleaseValidationResult:
    """Evaluate the frozen TASK-165 v0.6 acceptance gates."""

    if type(raw) is not Task169ReleaseRequest:
        return _blocked("", ("INVALID_RELEASE_REQUEST_TYPE",))
    request = raw
    failures: list[str] = []
    if request.schema_version != TASK169_RELEASE_SCHEMA_VERSION:
        failures.append("RELEASE_SCHEMA_VERSION_MISMATCH")
    if request.release_version != TASK169_RELEASE_VERSION:
        failures.append("RELEASE_VERSION_MISMATCH")
    if request.source_definition_id != TASK169_RELEASE_SOURCE_DEFINITION_ID:
        failures.append("RELEASE_SOURCE_DEFINITION_MISMATCH")
    if tuple(case.golden_id for case in request.golden_cases) != _GOLDEN_ORDER:
        failures.append("GOLDEN_CASE_SET_OR_ORDER_MISMATCH")
    try:
        request_hash_value = request_hash(request)
    except (TypeError, ValueError, UnicodeError, ArithmeticError):
        request_hash_value = ""
        failures.append("RELEASE_REQUEST_NOT_CANONICAL")
    if failures:
        return _blocked(request_hash_value, tuple(failures))

    selections = tuple(_selection(case) for case in request.golden_cases)
    golden_records = tuple(
        _golden_record(case, result)
        for case, result in zip(request.golden_cases, selections, strict=True)
    )
    golden_ok = {
        record.golden_id: record.status is AcceptanceStatus.PASS
        for record in golden_records
    }

    positive_pairs = tuple(zip(request.golden_cases[:4], selections[:4], strict=True))
    positive_candidates = tuple(
        _candidate_for_result(case, result)
        if result is not None
        else None
        for case, result in positive_pairs
    )
    g01, g02, g03, g04 = positive_candidates
    candidate_generation_ok = all(
        case.selection_request.task168_result.total_enumerated_candidates > 0
        for case in request.golden_cases[:4]
    )
    replay_ok = all(
        result is not None
        and _selection(case) is not None
        and _selection(case).result_hash == result.result_hash
        for case, result in zip(request.golden_cases, selections, strict=True)
    )
    parity_ok = _runtime_parity_ok(request, golden_records)
    g04_source = request.golden_cases[3].selection_request.task168_result.candidate_records
    g04_dp_rejection = any(
        record.status is CandidateStatus.BLOCKED
        and any(
            blocker.code == "HARD_CONSTRAINT_UNSATISFIED"
            and blocker.field_path in {"max_tube_dp_pa", "max_shell_dp_pa"}
            for blocker in record.blockers
        )
        for record in g04_source
    )
    tube_dp_ok = _constraint(g04, "max_tube_dp_pa") == "PASS" and g04_dp_rejection
    shell_dp_ok = _constraint(g04, "max_shell_dp_pa") == "PASS" and g04_dp_rejection
    duty_ok = all(_constraint(item, "required_duty_w") == "PASS" for item in (g01, g02, g03, g04))
    full_chain_ok = all(_full_chain_evidence(item) for item in (g01, g02, g03, g04))

    gates = [
        _gate(golden_ok[GoldenCaseId.V06_G01] and _full_chain_evidence(g01), _GATE_ORDER[0]),
        _gate(full_chain_ok, _GATE_ORDER[1]),
        _gate(full_chain_ok, _GATE_ORDER[2]),
        _gate(full_chain_ok, _GATE_ORDER[3]),
        _gate(all(item is not None and item.screening_evidence for item in (g01, g02, g03, g04)), _GATE_ORDER[4]),
        _gate(golden_ok[GoldenCaseId.V06_G02] and g02 is not None and bool(g02.screening_evidence), _GATE_ORDER[5]),
        _gate(golden_ok[GoldenCaseId.V06_G02] and g02 is not None and bool(g02.screening_evidence), _GATE_ORDER[6]),
        _gate(candidate_generation_ok, _GATE_ORDER[7]),
        _gate(candidate_generation_ok and all(result is not None for result in selections[:4]), _GATE_ORDER[8]),
        _gate(golden_ok[GoldenCaseId.V06_G04], _GATE_ORDER[9]),
        _gate(tube_dp_ok, _GATE_ORDER[10]),
        _gate(shell_dp_ok, _GATE_ORDER[11]),
        _gate(duty_ok, _GATE_ORDER[12]),
        _gate(replay_ok, _GATE_ORDER[13]),
        _gate(all(result is not None and bool(result.provenance_semantic_inputs) for result in selections), _GATE_ORDER[14]),
        _gate(parity_ok, _GATE_ORDER[15]),
    ]
    gates.extend(
        _gate(golden_ok[golden_id], f"GOLDEN_{golden_id.value.replace('-', '_')}")
        for golden_id in _GOLDEN_ORDER
    )
    pre_terminal_ok = all(gate.status is AcceptanceStatus.PASS for gate in gates)
    gates.append(_gate(pre_terminal_ok, _GATE_ORDER[-1]))
    gates_tuple = tuple(gates)
    if tuple(gate.gate_id for gate in gates_tuple) != _GATE_ORDER:
        return _blocked(request_hash_value, ("RELEASE_GATE_ORDER_INTERNAL_ERROR",))

    overall = (
        AcceptanceStatus.PASS
        if all(gate.status is AcceptanceStatus.PASS for gate in gates_tuple)
        else AcceptanceStatus.BLOCKED
    )
    provisional = Task169ReleaseResult(
        schema_version=TASK169_RELEASE_RESULT_SCHEMA_VERSION,
        release_version=TASK169_RELEASE_VERSION,
        implementation_software_version=TASK169_RELEASE_SOFTWARE_VERSION,
        source_definition_id=request.source_definition_id,
        request_hash=request_hash_value,
        frozen_tolerance_ledger=FROZEN_TOLERANCE_LEDGER,
        golden_records=golden_records,
        acceptance_gates=gates_tuple,
        overall_status=overall,
        result_hash="",
        result_id="",
    )
    digest = result_hash(provisional)
    result = replace(provisional, result_hash=digest, result_id=result_id(digest))
    if result_hash(result) != result.result_hash or result_id(result.result_hash) != result.result_id:
        return _blocked(request_hash_value, ("RELEASE_IDENTITY_REPLAY_FAILED",))
    return Task169ReleaseValidationResult(valid=result)


__all__ = ["FROZEN_TOLERANCE_LEDGER", "validate_request"]
