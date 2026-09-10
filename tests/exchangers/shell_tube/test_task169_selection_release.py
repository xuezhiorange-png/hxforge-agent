"""TASK-169 selection, replay, and release-boundary contract tests."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import replace
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pytest

from hexagent.exchangers.shell_tube.manufacturable_candidates import (
    validate_request as validate_task168_request,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    batch_result_hash,
    provenance_graph_hash,
    requirement_authority_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    request_hash as task168_request_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    result_id as task168_result_id,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK168_RESULT_SCHEMA_VERSION,
    TASK168_SOURCE_DEFINITION_ID,
    TASK168_VERSION,
    ApplicabilityStatus,
    CandidateDisposition,
    CandidateRecord,
    CandidateSpec,
    CandidateStage,
    CandidateStatus,
    CompletenessStatus,
    DiscreteDimensionRole,
    ProvenanceGraph,
    Task168Applicability,
    Task168BatchResult,
    Task168Blocker,
    Task168Completeness,
    Task168Request,
    Task168Warning,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    ValidationStatus as Task168ValidationStatus,
)
from hexagent.exchangers.shell_tube.models import ConstructionFamily
from hexagent.exchangers.shell_tube.selection_release.canonical import (
    ranking_policy_hash,
)
from hexagent.exchangers.shell_tube.selection_release.canonical import (
    result_hash as task169_result_hash,
)
from hexagent.exchangers.shell_tube.selection_release.canonical import (
    result_id as task169_result_id,
)
from hexagent.exchangers.shell_tube.selection_release.models import (
    TASK169_SCHEMA_VERSION,
    TASK169_SOURCE_DEFINITION_ID,
    TASK169_VERSION,
    RankingDirection,
    RankingObjective,
    SelectionStatus,
    Task169RankingPolicy,
    Task169Request,
    ValidationStatus,
)
from hexagent.exchangers.shell_tube.selection_release.service import (
    validate_request as validate_selection_request,
)
from hexagent.release_demo.task169_integration_release_acceptance import service as release_service
from hexagent.release_demo.task169_integration_release_acceptance import (
    validate_request as validate_release_request,
)
from hexagent.release_demo.task169_integration_release_acceptance.canonical import (
    request_hash as release_request_hash,
)
from hexagent.release_demo.task169_integration_release_acceptance.models import (
    TASK169_GOLDEN_TOLERANCE_CLASS,
    TASK169_RELEASE_SCHEMA_VERSION,
    TASK169_RELEASE_SOURCE_DEFINITION_ID,
    TASK169_RELEASE_VERSION,
    AcceptanceStatus,
    GoldenCaseId,
    Task169GoldenCase,
    Task169ReleaseRequest,
)
from hexagent.release_demo.task169_integration_release_acceptance.trusted_evidence import (
    Task169ParityInput,
    observe_dual_runtime,
    repository_identity,
)


def _candidate(
    candidate_id: str,
    candidate_hash: str,
    *,
    status: CandidateStatus = CandidateStatus.PASS,
    shell_dp: str = "100",
    tube_dp: str = "50",
    ua: str = "1000",
    warnings: tuple[Task168Warning, ...] = (),
    blocked: bool = False,
    family: ConstructionFamily = ConstructionFamily.FIXED_TUBESHEET,
    full_chain_evidence: bool = False,
    blocked_field: str = "max_shell_dp_pa",
) -> CandidateRecord:
    spec = CandidateSpec(
        candidate_id=candidate_id,
        candidate_hash=candidate_hash,
        case_authority_id="case-v06",
        construction_family=family,
        shell_geometry_id="shell-1",
        shell_record_hash="shell-hash",
        shell_inside_diameter_m=Decimal("0.5"),
        tube_outer_diameter_m=Decimal("0.01905"),
        tube_wall_thickness_m=Decimal("0.00165"),
        tube_length_m=Decimal("4.0"),
        tube_pitch_m=Decimal("0.0254"),
        tube_layout="TRIANGULAR",
        tube_pass_count=2,
        baffle_type="SINGLE_SEGMENTAL",
        baffle_cut_fraction=Decimal("0.25"),
        baffle_spacing_m=Decimal("0.2"),
        baffle_count=19,
        authority_bindings=(),
        dimension_authority_bindings=(),
    )
    blockers = (
        (
            Task168Blocker(
                code="HARD_CONSTRAINT_UNSATISFIED",
                stage=CandidateStage.CONSTRAINT_EVALUATION,
                field_path=blocked_field,
            ),
        )
        if blocked
        else ()
    )
    evidence = (("result_hash", candidate_hash),) if full_chain_evidence else ()
    constraints = (
        ("required_duty_w", "PASS"),
        (
            "max_tube_dp_pa",
            "PASS" if not blocked or blocked_field != "max_tube_dp_pa" else "BLOCKED",
        ),
        (
            "max_shell_dp_pa",
            "PASS" if not blocked or blocked_field != "max_shell_dp_pa" else "BLOCKED",
        ),
    )
    return CandidateRecord(
        candidate_id=candidate_id,
        candidate_hash=candidate_hash,
        candidate=spec,
        disposition=CandidateDisposition.BLOCKED if blocked else CandidateDisposition.EVALUATED,
        status=CandidateStatus.BLOCKED if blocked else status,
        stage=CandidateStage.CONSTRAINT_EVALUATION if blocked else CandidateStage.COMPLETE,
        last_successful_stage=(
            CandidateStage.ENGINEERING_SCREENING if blocked else CandidateStage.COMPLETE
        ),
        configuration_evidence=evidence,
        geometry_evidence=evidence,
        tube_layout_evidence=evidence,
        tube_side_evidence=evidence,
        bell_evidence=evidence,
        overall_u_ua_evidence=evidence,
        thermal_closure_evidence=evidence,
        tube_dp_evidence=evidence,
        shell_dp_evidence=evidence,
        screening_evidence=evidence,
        constraint_evaluations=constraints,
        metrics=(
            ("modeled_ua_w_k", ua),
            ("q_method_w", "100000"),
            ("shell_dp_pa", shell_dp),
            ("tube_dp_pa", tube_dp),
            ("physical_tube_count", "100"),
            ("tube_hole_count", "104"),
        ),
        warnings=warnings,
        blockers=blockers,
    )


def _batch(records: tuple[CandidateRecord, ...]) -> Task168BatchResult:
    records = tuple(sorted(records, key=lambda record: record.candidate_hash.encode("utf-8")))
    graph0 = ProvenanceGraph(nodes=(), edges=(), graph_hash="", self_edge_count=0, cycle_count=0)
    graph = replace(graph0, graph_hash=provenance_graph_hash(graph0))
    provisional = Task168BatchResult(
        schema_version=TASK168_RESULT_SCHEMA_VERSION,
        task168_version=TASK168_VERSION,
        implementation_software_version=TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
        source_definition_id=TASK168_SOURCE_DEFINITION_ID,
        request_hash="1" * 64,
        candidate_space_id="candidate-space",
        candidate_space_hash="2" * 64,
        total_theoretical_combinations=len(records),
        total_enumerated_candidates=len(records),
        pass_count=sum(record.status is CandidateStatus.PASS for record in records),
        warn_count=sum(record.status is CandidateStatus.WARN for record in records),
        blocked_count=sum(record.status is CandidateStatus.BLOCKED for record in records),
        candidate_records=records,
        warnings=(),
        blockers=(),
        applicability=Task168Applicability(
            status=ApplicabilityStatus.APPLICABLE,
            checks=(("task169_fixture", "PASS"),),
        ),
        completeness=Task168Completeness(
            required_fields=("candidate_records",),
            present_fields=("candidate_records",),
            status=CompletenessStatus.COMPLETE,
        ),
        provenance_semantic_inputs=(),
        provenance=graph,
        result_hash="",
        result_id="",
    )
    digest = batch_result_hash(provisional)
    return replace(provisional, result_hash=digest, result_id=task168_result_id(digest))


def _policy(
    *,
    objectives: tuple[RankingObjective, ...] | None = None,
    top_n: int = 3,
    warning_penalty: Decimal = Decimal("10"),
) -> Task169RankingPolicy:
    provisional = Task169RankingPolicy(
        policy_id="V06-RANKING-POLICY-TEST",
        policy_version="v1",
        source_id="TASK169-TEST-AUTHORITY",
        approval_status="APPROVED",
        top_n=top_n,
        warning_penalty=warning_penalty,
        objectives=objectives
        or (
            RankingObjective(
                metric="shell_dp_pa",
                direction=RankingDirection.MINIMIZE,
                weight=Decimal("1"),
                scale=Decimal("100"),
            ),
        ),
        evidence_refs=("TASK169_TEST",),
        provenance_refs=("TASK169_TEST",),
        canonical_hash="",
    )
    return replace(provisional, canonical_hash=ranking_policy_hash(provisional))


def _request(
    batch: Task168BatchResult,
    policy: Task169RankingPolicy | None = None,
) -> Task169Request:
    return Task169Request(
        schema_version=TASK169_SCHEMA_VERSION,
        task169_version=TASK169_VERSION,
        source_definition_id=TASK169_SOURCE_DEFINITION_ID,
        task168_result=batch,
        ranking_policy=policy or _policy(),
    )


def test_selection_excludes_hard_blockers_and_selects_lowest_score() -> None:
    blocked = _candidate("blocked", "0" * 64, shell_dp="1", blocked=True)
    high = _candidate("high", "b" * 64, shell_dp="200")
    low = _candidate("low", "a" * 64, shell_dp="100")
    result = validate_selection_request(_request(_batch((blocked, high, low))))
    assert result.status is ValidationStatus.VALID
    assert result.valid is not None
    assert result.valid.selection_status is SelectionStatus.SELECTED
    assert result.valid.recommended_candidate is not None
    assert result.valid.recommended_candidate.candidate_id == "low"
    assert [item.candidate_id for item in result.valid.ranked_candidates] == ["low", "high"]
    assert result.valid.excluded_candidates[0].candidate_id == "blocked"


def test_selection_maximize_objective_is_supported() -> None:
    policy = _policy(
        objectives=(
            RankingObjective(
                metric="modeled_ua_w_k",
                direction=RankingDirection.MAXIMIZE,
                weight=Decimal("1"),
                scale=Decimal("1000"),
            ),
        )
    )
    result = validate_selection_request(
        _request(
            _batch(
                (
                    _candidate("low-ua", "a" * 64, ua="900"),
                    _candidate("high-ua", "b" * 64, ua="1200"),
                )
            ),
            policy,
        )
    )
    assert result.valid is not None
    assert result.valid.recommended_candidate is not None
    assert result.valid.recommended_candidate.candidate_id == "high-ua"


def test_selection_warn_penalty_and_reason_trace_are_explicit() -> None:
    warn = _candidate(
        "warn",
        "a" * 64,
        shell_dp="10",
        status=CandidateStatus.WARN,
        warnings=(Task168Warning(code="SCREENING_WARN"),),
    )
    passed = _candidate("pass", "b" * 64, shell_dp="100")
    result = validate_selection_request(
        _request(_batch((warn, passed)), _policy(warning_penalty=Decimal("2")))
    )
    assert result.valid is not None
    assert result.valid.recommended_candidate is not None
    assert result.valid.recommended_candidate.candidate_id == "pass"
    assert "WARN_PENALTY_APPLIED" in result.valid.ranked_candidates[1].reason_codes
    assert result.valid.alternative_reason_codes


def test_selection_tie_breaks_by_candidate_hash_and_is_order_invariant() -> None:
    a = _candidate("a", "a" * 64, shell_dp="100")
    b = _candidate("b", "b" * 64, shell_dp="100")
    first = validate_selection_request(_request(_batch((b, a))))
    second = validate_selection_request(_request(_batch((a, b))))
    assert first.valid is not None and second.valid is not None
    assert [item.candidate_id for item in first.valid.ranked_candidates] == ["a", "b"]
    assert first.valid.result_hash == second.valid.result_hash
    assert first.valid.result_id == second.valid.result_id
    assert "CANONICAL_CANDIDATE_HASH_TIE_BREAK" in first.valid.recommendation_reason_codes


def test_selection_missing_metric_excludes_candidate() -> None:
    record = replace(_candidate("missing", "a" * 64), metrics=(("tube_dp_pa", "50"),))
    result = validate_selection_request(_request(_batch((record,))))
    assert result.valid is not None
    assert result.valid.selection_status is SelectionStatus.NO_RECOMMENDABLE_CANDIDATE
    assert result.valid.recommended_candidate is None
    assert result.valid.excluded_candidates[0].reason_code == "RANKING_METRIC_MISSING_OR_INVALID"


def test_selection_top_n_is_exact_prefix() -> None:
    records = tuple(
        _candidate(str(index), f"{index:064x}", shell_dp=str(100 + index)) for index in range(5)
    )
    result = validate_selection_request(_request(_batch(records), _policy(top_n=2)))
    assert result.valid is not None
    assert result.valid.recommended_candidate is not None
    assert len(result.valid.alternatives) == 1
    assert result.valid.recommended_candidate.rank == 1
    assert result.valid.alternatives[0].rank == 2


def test_selection_rejects_tampered_task168_result() -> None:
    batch = _batch((_candidate("a", "a" * 64),))
    result = validate_selection_request(_request(replace(batch, result_hash="0" * 64)))
    assert result.status is ValidationStatus.TYPED_BLOCKED
    assert result.typed_blocked is not None
    assert "TASK168_RESULT_HASH_MISMATCH" in result.typed_blocked.blocker_codes


def test_selection_rejects_tampered_ranking_policy_identity() -> None:
    policy = replace(_policy(), canonical_hash="0" * 64)
    result = validate_selection_request(_request(_batch((_candidate("a", "a" * 64),)), policy))
    assert result.status is ValidationStatus.TYPED_BLOCKED
    assert result.typed_blocked is not None
    assert "RANKING_POLICY_HASH_MISMATCH" in result.typed_blocked.blocker_codes


def test_selection_result_identity_replays_with_reason_trace() -> None:
    result = validate_selection_request(
        _request(_batch((_candidate("a", "a" * 64), _candidate("b", "b" * 64))))
    )
    assert result.valid is not None
    assert task169_result_hash(result.valid) == result.valid.result_hash
    assert task169_result_id(result.valid.result_hash) == result.valid.result_id
    assert result.valid.recommendation_reason_codes
    assert result.valid.alternative_reason_codes


def test_selection_invalid_type_fails_closed() -> None:
    result = validate_selection_request(object())
    assert result.status is ValidationStatus.TYPED_BLOCKED
    assert result.typed_blocked is not None
    assert result.typed_blocked.blocker_codes == ("INVALID_REQUEST_TYPE",)


@lru_cache(maxsize=1)
def _real_request() -> Task168Request:
    from tests.exchangers.shell_tube.test_task168_manufacturable_candidates import (
        _real_request as build_real_request,
    )

    return build_real_request()


def _real_task168_request() -> Task168Request:
    return _real_request()


def _family_request(family: ConstructionFamily) -> Task168Request:
    from dataclasses import replace as dataclass_replace

    from tests.exchangers.shell_tube.test_task168_manufacturable_candidates import (
        _with_authority_values,
    )

    request = _real_task168_request()
    requirement = dataclass_replace(
        request.requirement_authority,
        allowed_construction_families=(family,),
        canonical_hash="",
    )
    requirement = dataclass_replace(
        requirement,
        canonical_hash=requirement_authority_hash(requirement),
    )
    return _with_authority_values(
        dataclass_replace(request, requirement_authority=requirement),
        DiscreteDimensionRole.CONSTRUCTION_FAMILY,
        (family,),
    )


def _g04_request() -> Task168Request:
    from dataclasses import replace as dataclass_replace

    from tests.exchangers.shell_tube.test_task168_manufacturable_candidates import (
        _with_authority_values,
    )

    request = _real_task168_request()
    requirement = dataclass_replace(
        request.requirement_authority,
        max_shell_dp_pa=Decimal("20000"),
        canonical_hash="",
    )
    requirement = dataclass_replace(
        requirement,
        canonical_hash=requirement_authority_hash(requirement),
    )
    return _with_authority_values(
        dataclass_replace(request, requirement_authority=requirement),
        DiscreteDimensionRole.TUBE_OUTER_DIAMETER,
        (Decimal("0.018"), Decimal("0.02")),
    )


def _g05_request() -> Task168Request:
    from tests.exchangers.shell_tube.test_task168_manufacturable_candidates import (
        _real_request as build_real_request,
    )

    return build_real_request(shell_diameter="0.20")


def _proposal_case(golden_id: GoldenCaseId, request: Task168Request) -> Task169GoldenCase:
    outcome = validate_task168_request(request)
    assert outcome.status is Task168ValidationStatus.VALID
    assert outcome.valid is not None
    request_digest = task168_request_hash(request)
    return Task169GoldenCase(
        golden_id=golden_id,
        source_id=f"TASK169-PROPOSAL-{golden_id.value}",
        source_location="tests/exchangers/shell_tube/test_task169_selection_release.py",
        source_class="PROPOSAL_ONLY_INTEGRATION_EVIDENCE",
        redistribution_status="METADATA_ONLY_NO_PROTECTED_PAYLOAD",
        normalized_input_identity=request_digest,
        task168_request=request,
        task168_request_hash=request_digest,
        expected_task168_result_hash=outcome.valid.result_hash,
        expected_task168_result_id=outcome.valid.result_id,
        expected_task168_result_status=Task168ValidationStatus.VALID.value,
        ranking_policy=_policy(),
        expected_task169_result_hash=None,
        expected_task169_result_id=None,
        approved_numeric_expectations=(("EXPECTED_IDENTITY_STATUS", "PROPOSED_FOR_REVIEW"),),
        tolerance_class=TASK169_GOLDEN_TOLERANCE_CLASS,
        provenance_source_hash="f" * 64,
        reviewer_evidence_refs=("INDEPENDENT_REVIEW_PENDING",),
    )


@lru_cache(maxsize=1)
def _release_request() -> Task169ReleaseRequest:
    cases = (
        _proposal_case(GoldenCaseId.V06_G01, _real_task168_request()),
        _proposal_case(GoldenCaseId.V06_G02, _family_request(ConstructionFamily.U_TUBE)),
        _proposal_case(GoldenCaseId.V06_G03, _family_request(ConstructionFamily.FLOATING_HEAD)),
        _proposal_case(GoldenCaseId.V06_G04, _g04_request()),
        _proposal_case(GoldenCaseId.V06_G05, _g05_request()),
    )
    return Task169ReleaseRequest(
        schema_version=TASK169_RELEASE_SCHEMA_VERSION,
        release_version=TASK169_RELEASE_VERSION,
        source_definition_id=TASK169_RELEASE_SOURCE_DEFINITION_ID,
        golden_cases=cases,
    )


def test_task168_real_request_replays_before_release_validation() -> None:
    outcome = validate_task168_request(_real_task168_request())
    assert outcome.valid is not None
    assert outcome.valid.candidate_records[0].stage is CandidateStage.COMPLETE
    assert outcome.valid.result_hash


def test_release_replays_task168_public_validator_for_each_golden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    original = release_service.validate_task168_request

    def counted(request: object) -> object:
        nonlocal calls
        calls += 1
        return original(request)

    monkeypatch.setattr(release_service, "validate_task168_request", counted)
    outcome = validate_release_request(_release_request())
    assert calls == 5
    assert outcome.valid is not None
    g01 = outcome.valid.golden_records[0]
    assert (
        g01.task168_result_hash == _release_request().golden_cases[0].expected_task168_result_hash
    )
    assert g01.selection_result_hash
    if (
        os.environ.get("TASK169_PY311_EXECUTABLE") and os.environ.get("TASK169_PY312_EXECUTABLE")
    ) or (
        os.environ.get("TASK164_PY311_EXECUTABLE") and os.environ.get("TASK164_PY312_EXECUTABLE")
    ):
        assert outcome.valid.trusted_runtime_status is AcceptanceStatus.PASS


def test_release_does_not_have_caller_supplied_task168_result_surface() -> None:
    case = _release_request().golden_cases[0]
    assert not hasattr(case, "task168_result")
    assert hasattr(case, "task168_request")


def test_release_golden_proposals_cannot_self_approve() -> None:
    outcome = validate_release_request(_release_request())
    assert outcome.valid is not None
    assert outcome.valid.overall_status is AcceptanceStatus.BLOCKED
    assert all(record.status is AcceptanceStatus.BLOCKED for record in outcome.valid.golden_records)
    assert "V06_GOLDEN_FIXTURE_REVIEW_APPROVAL_PENDING" in outcome.valid.blocker_codes


def test_release_g04_replays_real_multi_candidate_dp_constraint() -> None:
    outcome = validate_release_request(_release_request())
    assert outcome.valid is not None
    g04 = outcome.valid.golden_records[3]
    assert g04.task168_result_hash
    assert g04.recommended_candidate_id
    assert not any(code == "G04_MULTI_CANDIDATE_REQUIRED" for code in g04.reason_codes)
    assert not any(code == "G04_DP_CONSTRAINED_REJECTION_REQUIRED" for code in g04.reason_codes)


def test_release_g05_is_real_no_recommendation_path() -> None:
    outcome = validate_release_request(_release_request())
    assert outcome.valid is not None
    g05 = outcome.valid.golden_records[4]
    assert g05.recommended_candidate_id is None
    assert "G05_NO_RECOMMENDATION_REQUIRED" not in g05.reason_codes


def test_release_negative_batch_keeps_provenance_gate_replayable() -> None:
    outcome = validate_release_request(_release_request())
    assert outcome.valid is not None
    gates = {gate.gate_id: gate.status for gate in outcome.valid.acceptance_gates}
    assert gates["PROVENANCE_COMPLETE"] is AcceptanceStatus.PASS


def test_release_task168_request_binding_tampering_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _release_request().golden_cases[0]
    original = release_service.validate_task168_request

    def tampered(request: object) -> object:
        outcome = original(request)
        if request is not case.task168_request or outcome.valid is None:
            return outcome
        changed = replace(outcome.valid, request_hash="0" * 64, result_hash="", result_id="")
        digest = batch_result_hash(changed)
        changed = replace(changed, result_hash=digest, result_id=task168_result_id(digest))
        return replace(outcome, valid=changed)

    monkeypatch.setattr(release_service, "validate_task168_request", tampered)
    outcome = validate_release_request(_release_request())
    assert outcome.valid is not None
    assert "TASK168_REQUEST_BINDING_MISMATCH" in outcome.valid.golden_records[0].reason_codes


def test_release_task168_expected_identity_tampering_is_fail_closed() -> None:
    case = _release_request().golden_cases[0]
    tampered = replace(case, expected_task168_result_hash="0" * 64)
    request = replace(
        _release_request(), golden_cases=(tampered, *_release_request().golden_cases[1:])
    )
    outcome = validate_release_request(request)
    assert outcome.valid is not None
    assert "TASK168_EXPECTED_RESULT_HASH_MISMATCH" in outcome.valid.golden_records[0].reason_codes


def test_release_task168_request_hash_tampering_is_fail_closed() -> None:
    case = _release_request().golden_cases[0]
    tampered = replace(case, task168_request_hash="0" * 64)
    request = replace(
        _release_request(), golden_cases=(tampered, *_release_request().golden_cases[1:])
    )
    outcome = validate_release_request(request)
    assert outcome.valid is not None
    assert "TASK168_REQUEST_HASH_MISMATCH" in outcome.valid.golden_records[0].reason_codes


def test_release_frozen_tolerance_cannot_be_overridden() -> None:
    request = replace(
        _release_request(),
        frozen_tolerance_ledger=(("ENERGY_BALANCE_RELATIVE_ERROR_MAX", "9"),),
    )
    outcome = validate_release_request(request)
    assert outcome.blocked is not None
    assert "FROZEN_TOLERANCE_AUTHORITY_MISMATCH" in outcome.blocked.blocker_codes


def test_release_request_identity_includes_all_golden_request_bindings() -> None:
    request = _release_request()
    first = release_request_hash(request)
    altered = replace(
        request.golden_cases[0],
        source_location="different-authority-location",
    )
    second = release_request_hash(
        replace(request, golden_cases=(altered, *request.golden_cases[1:]))
    )
    assert first != second


def _parity_input_for_test() -> Task169ParityInput:
    identity = repository_identity()
    assert identity is not None
    head, tree = identity
    return Task169ParityInput(
        release_request_hash="a" * 64,
        task168_request_hashes=(("V06-G01", "b" * 64),),
        task168_result_hashes=(("V06-G01", "c" * 64),),
        task169_result_hashes=(("V06-G01", "d" * 64),),
        task169_result_ids=(("V06-G01", "task169-result"),),
        head_sha=head,
        head_tree=tree,
        software_version="task169.release-acceptance-impl-v2",
    )


def test_trusted_runtime_rejects_duplicate_executable_assignment() -> None:
    executable = shutil.which("python3")
    if executable is None:
        pytest.skip("python executable unavailable")
    observed = observe_dual_runtime(
        input_value=_parity_input_for_test(),
        py311=executable,
        py312=executable,
    )
    assert observed.status == "BLOCKED"
    assert observed.python311.status == "BLOCKED"
    assert observed.python312.status == "BLOCKED"


def test_trusted_runtime_missing_observation_is_fail_closed() -> None:
    observed = observe_dual_runtime(
        input_value=_parity_input_for_test(),
        py311="/definitely/missing/python311",
        py312="/definitely/missing/python312",
    )
    assert observed.status == "BLOCKED"


def test_trusted_runtime_executes_provisioned_py311_and_py312() -> None:
    py311 = os.environ.get("TASK169_PY311_EXECUTABLE") or os.environ.get("TASK164_PY311_EXECUTABLE")
    py312 = os.environ.get("TASK169_PY312_EXECUTABLE") or os.environ.get("TASK164_PY312_EXECUTABLE")
    if not py311 or not py312:
        pytest.skip("trusted dual-runtime executables are not provisioned")
    observed = observe_dual_runtime(
        input_value=_parity_input_for_test(),
        py311=py311,
        py312=py312,
    )
    assert observed.status == "PASS"
    assert observed.python311.status == "PASS"
    assert observed.python312.status == "PASS"
    assert observed.python311.actual_python_major_minor == "3.11"
    assert observed.python312.actual_python_major_minor == "3.12"


def test_trusted_runtime_input_pair_order_is_canonical() -> None:
    first = _parity_input_for_test()
    second = replace(
        first,
        task168_request_hashes=tuple(reversed(first.task168_request_hashes)),
        task168_result_hashes=tuple(reversed(first.task168_result_hashes)),
    )
    from hexagent.release_demo.task169_integration_release_acceptance.trusted_evidence import (
        expected_digests,
    )

    assert expected_digests(first) == expected_digests(second)


def test_release_result_identity_replays_even_when_acceptance_is_blocked() -> None:
    from hexagent.release_demo.task169_integration_release_acceptance.canonical import (
        result_hash as release_result_hash,
    )
    from hexagent.release_demo.task169_integration_release_acceptance.canonical import (
        result_id as release_result_id,
    )

    outcome = validate_release_request(_release_request())
    assert outcome.valid is not None
    assert release_result_hash(outcome.valid) == outcome.valid.result_hash
    assert release_result_id(outcome.valid.result_hash) == outcome.valid.result_id


def test_real_g04_request_has_one_feasible_and_one_dp_blocked_candidate() -> None:
    outcome = validate_task168_request(_g04_request())
    assert outcome.valid is not None
    assert len(outcome.valid.candidate_records) == 2
    assert (
        sum(record.stage is CandidateStage.COMPLETE for record in outcome.valid.candidate_records)
        == 1
    )
    blocked = [
        record
        for record in outcome.valid.candidate_records
        if record.status is CandidateStatus.BLOCKED
    ]
    assert blocked
    assert any(
        blocker.code == "HARD_CONSTRAINT_UNSATISFIED" and blocker.field_path == "max_shell_dp_pa"
        for record in blocked
        for blocker in record.blockers
    )


def test_real_family_materialization_attempts_u_tube_and_floating_head() -> None:
    for family in (ConstructionFamily.U_TUBE, ConstructionFamily.FLOATING_HEAD):
        outcome = validate_task168_request(_family_request(family))
        assert outcome.valid is not None
        assert outcome.valid.candidate_records[0].candidate.construction_family is family
        assert (
            dict(outcome.valid.candidate_records[0].configuration_evidence)["construction_family"]
            == family.value
        )


def test_task169_release_schema_is_v2_and_proposal_status_is_frozen() -> None:
    request = _release_request()
    assert request.schema_version == TASK169_RELEASE_SCHEMA_VERSION
    assert all(case.review_status == "PROPOSED" for case in request.golden_cases)
    assert all(
        case.expected_identity_status == "PROPOSED_FOR_REVIEW" for case in request.golden_cases
    )


def test_golden_authority_payload_is_proposal_only() -> None:
    payload_path = (
        Path(__file__).parents[3] / "docs" / "tasks" / "TASK-169-v06-golden-authority-proposal.json"
    )
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["authority_status"] == "PROPOSED"
    assert payload["golden_self_approval"] is False
    assert [item["golden_id"] for item in payload["goldens"]] == [
        "V06-G01",
        "V06-G02",
        "V06-G03",
        "V06-G04",
        "V06-G05",
    ]
    assert all(
        item["review_status"] == "PROPOSED"
        and item["expected_identity_status"] == "PROPOSED_FOR_REVIEW"
        and item["approved_by"] == ""
        and item["approval_evidence"] == []
        and item["expected_task169_result_hash"] is None
        and item["expected_task169_result_id"] is None
        for item in payload["goldens"]
    )
