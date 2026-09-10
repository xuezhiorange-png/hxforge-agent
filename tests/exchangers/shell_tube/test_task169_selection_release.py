from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    batch_result_hash,
    provenance_graph_hash,
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
    ProvenanceGraph,
    Task168Applicability,
    Task168BatchResult,
    Task168Blocker,
    Task168Completeness,
    Task168Warning,
)
from hexagent.exchangers.shell_tube.models import ConstructionFamily
from hexagent.exchangers.shell_tube.selection_release.canonical import (
    ranking_policy_hash,
    result_hash as task169_result_hash,
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
from hexagent.exchangers.shell_tube.selection_release.service import validate_request


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
) -> CandidateRecord:
    spec = CandidateSpec(
        candidate_id=candidate_id,
        candidate_hash=candidate_hash,
        case_authority_id="case-v06",
        construction_family=ConstructionFamily.FIXED_TUBESHEET,
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
        Task168Blocker(
            code="HARD_CONSTRAINT_UNSATISFIED",
            stage=CandidateStage.CONSTRAINT_EVALUATION,
        ),
    ) if blocked else ()
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


def test_task169_excludes_hard_blockers_and_selects_lowest_score() -> None:
    blocked = _candidate("blocked", "0" * 64, shell_dp="1", blocked=True)
    high = _candidate("high", "b" * 64, shell_dp="200")
    low = _candidate("low", "a" * 64, shell_dp="100")
    result = validate_request(_request(_batch((blocked, high, low))))
    assert result.status is ValidationStatus.VALID
    assert result.valid is not None
    assert result.valid.selection_status is SelectionStatus.SELECTED
    assert result.valid.recommended_candidate is not None
    assert result.valid.recommended_candidate.candidate_id == "low"
    assert [item.candidate_id for item in result.valid.ranked_candidates] == ["low", "high"]
    assert result.valid.excluded_candidates[0].candidate_id == "blocked"


def test_task169_maximize_objective_is_supported() -> None:
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
    low_ua = _candidate("low-ua", "a" * 64, ua="900")
    high_ua = _candidate("high-ua", "b" * 64, ua="1200")
    result = validate_request(_request(_batch((low_ua, high_ua)), policy))
    assert result.valid is not None
    assert result.valid.recommended_candidate is not None
    assert result.valid.recommended_candidate.candidate_id == "high-ua"


def test_task169_warn_penalty_is_explicit_and_deterministic() -> None:
    warn = _candidate(
        "warn",
        "a" * 64,
        shell_dp="10",
        status=CandidateStatus.WARN,
        warnings=(Task168Warning(code="SCREENING_WARN"),),
    )
    passed = _candidate("pass", "b" * 64, shell_dp="100")
    result = validate_request(
        _request(_batch((warn, passed)), _policy(warning_penalty=Decimal("2")))
    )
    assert result.valid is not None
    assert result.valid.recommended_candidate is not None
    assert result.valid.recommended_candidate.candidate_id == "pass"


def test_task169_tie_breaks_by_candidate_hash() -> None:
    b = _candidate("b", "b" * 64, shell_dp="100")
    a = _candidate("a", "a" * 64, shell_dp="100")
    result = validate_request(_request(_batch((b, a))))
    assert result.valid is not None
    assert [item.candidate_id for item in result.valid.ranked_candidates] == ["a", "b"]


def test_task169_missing_metric_excludes_candidate() -> None:
    record = _candidate("missing", "a" * 64)
    record = replace(record, metrics=(("tube_dp_pa", "50"),))
    result = validate_request(_request(_batch((record,))))
    assert result.valid is not None
    assert result.valid.selection_status is SelectionStatus.NO_RECOMMENDABLE_CANDIDATE
    assert result.valid.recommended_candidate is None
    assert result.valid.excluded_candidates[0].reason_code == "RANKING_METRIC_MISSING_OR_INVALID"


def test_task169_top_n_is_exact_prefix() -> None:
    records = tuple(
        _candidate(str(index), f"{index:064x}", shell_dp=str(100 + index))
        for index in range(5)
    )
    result = validate_request(_request(_batch(records), _policy(top_n=2)))
    assert result.valid is not None
    assert result.valid.recommended_candidate is not None
    assert len(result.valid.alternatives) == 1
    assert result.valid.recommended_candidate.rank == 1
    assert result.valid.alternatives[0].rank == 2


def test_task169_rejects_tampered_task168_result() -> None:
    batch = _batch((_candidate("a", "a" * 64),))
    tampered = replace(batch, result_hash="0" * 64)
    result = validate_request(_request(tampered))
    assert result.status is ValidationStatus.TYPED_BLOCKED
    assert result.typed_blocked is not None
    assert "TASK168_RESULT_HASH_MISMATCH" in result.typed_blocked.blocker_codes


def test_task169_rejects_unbound_ranking_policy_hash() -> None:
    policy = replace(_policy(), canonical_hash="0" * 64)
    result = validate_request(_request(_batch((_candidate("a", "a" * 64),)), policy))
    assert result.status is ValidationStatus.TYPED_BLOCKED
    assert result.typed_blocked is not None
    assert "RANKING_POLICY_HASH_MISMATCH" in result.typed_blocked.blocker_codes


def test_task169_result_identity_replays() -> None:
    result = validate_request(_request(_batch((_candidate("a", "a" * 64),))))
    assert result.valid is not None
    assert task169_result_hash(result.valid) == result.valid.result_hash
    assert task169_result_id(result.valid.result_hash) == result.valid.result_id


def test_task169_invalid_type_fails_closed() -> None:
    result = validate_request(object())
    assert result.status is ValidationStatus.TYPED_BLOCKED
    assert result.typed_blocked is not None
    assert result.typed_blocked.blocker_codes == ("INVALID_REQUEST_TYPE",)
