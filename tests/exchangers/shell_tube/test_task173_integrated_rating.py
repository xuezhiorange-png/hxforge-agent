"""Stage-3 native replay, enthalpy boundary, and feasibility-root contracts."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from hexagent.exchangers.shell_tube import task173_integrated_rating as task173
from hexagent.exchangers.shell_tube.task172_local_runtime import (
    Task172BlockedResult,
    Task172LocalRequest,
    build_local_support,
    recompute_task172_blocked_result_hash,
    recompute_task172_local_roundoff_bounds,
    recompute_task172_support_id,
)
from hexagent.exchangers.shell_tube.task172_local_runtime import models as task172_models
from hexagent.exchangers.shell_tube.task172_local_runtime import (
    validate_request as task172_validate,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service
from hexagent.exchangers.shell_tube.task173_integrated_rating.replay import (
    EXPECTED_TASK031_GEOMETRY_HASH,
    EXPECTED_TASK032_RESULT_HASH,
    EXPECTED_TASK166_RESULT_HASH,
    EXPECTED_TASK174_RESULT_HASH,
    SUPERSEDED_EFFECTIVE_IDENTITIES,
    NativeReplayError,
    replay_shell_flow_authority,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

EVIDENCE_PATH = (
    Path(__file__).parents[3]
    / "docs"
    / "tasks"
    / "evidence"
    / "TASK-172-stage2-native-shell-flow-replay-correction-r1.json"
)


def _evidence() -> dict[str, Any]:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def test_corrected_native_shell_flow_chain_replays_exactly() -> None:
    authority, task174, replay = replay_shell_flow_authority(_evidence(), CoolPropProvider())
    assert replay["status"] == "PASS"
    assert replay["task031_geometry_hash"] == EXPECTED_TASK031_GEOMETRY_HASH
    assert replay["task032_result_hash"] == EXPECTED_TASK032_RESULT_HASH
    assert replay["task166_result_hash"] == EXPECTED_TASK166_RESULT_HASH
    assert replay["task174_result_hash"] == EXPECTED_TASK174_RESULT_HASH
    assert replay["task172_reference_result_payload_identity_validated"] is True
    assert replay["task172_reference_producer_reinvoked_during_shell_replay"] is False
    assert authority.task166_result.result_hash == EXPECTED_TASK166_RESULT_HASH
    assert task174.task166_result_hash == EXPECTED_TASK166_RESULT_HASH
    assert replay["test_fixture_used_as_authority"] is False
    assert SUPERSEDED_EFFECTIVE_IDENTITIES.isdisjoint(
        {
            authority.task166_result.result_hash,
            task174.result_hash,
        }
    )


def test_mutated_persisted_task172_result_payload_fails_bundle_identity() -> None:
    evidence = _evidence()
    evidence["shared_native_payload"]["TASK172_native_result"]["result_hash"] = "0" * 64
    with pytest.raises(NativeReplayError, match="evidence hash"):
        replay_shell_flow_authority(evidence, CoolPropProvider())


def test_historical_task166_identity_is_not_effective() -> None:
    assert "3b639d0523b799f92bdf59ebee415dc263dac5164ab816cb5fb7df5b3ed37cb7" in (
        SUPERSEDED_EFFECTIVE_IDENTITIES
    )
    assert "ed3c9b1d-b303-5b50-9faf-ba1a1fd927df" in SUPERSEDED_EFFECTIVE_IDENTITIES


def test_reviewed_base_support_is_exact_task171_support() -> None:
    support = build_local_support(0, 1, 0)
    assert support.support_start_m == Decimal("0.0")
    assert support.support_end_m == Decimal("1.2")
    assert support.inside_area_m2 == Decimal("15.02215359168")
    assert support.outside_area_m2 == Decimal("18.1696524394605785819779008")
    assert support.tube_cell_id == task172_models.TASK171_BASE_SUPPORT_IDS[0][1]
    assert support.shell_cell_id == task172_models.TASK171_BASE_SUPPORT_IDS[0][2]
    assert support.wall_interface_id == task172_models.TASK171_BASE_SUPPORT_IDS[0][3]


def test_refinement_conserves_parent_length_and_cylindrical_areas() -> None:
    parent = build_local_support(0, 1, 0)
    children = (build_local_support(0, 2, 0), build_local_support(0, 2, 1))
    assert tuple(child.support_start_m for child in children) == (Decimal("0.0"), Decimal("0.6"))
    assert tuple(child.support_end_m for child in children) == (Decimal("0.6"), Decimal("1.2"))
    assert sum((child.support_end_m - child.support_start_m for child in children), Decimal(0)) == (
        parent.support_end_m - parent.support_start_m
    )
    assert sum((child.inside_area_m2 for child in children), Decimal(0)) == parent.inside_area_m2
    assert sum((child.outside_area_m2 for child in children), Decimal(0)) == parent.outside_area_m2
    assert all(child.physical_segment_id == parent.physical_segment_id for child in children)
    assert len({child.tube_cell_id for child in children}) == 2
    assert len({child.shell_cell_id for child in children}) == 2
    assert len({child.wall_interface_id for child in children}) == 2


def test_property_lower_boundary_rejects_without_backend_call() -> None:
    class SpyProvider:
        calls = 0

        def state_ph(self, *_args: Any, **_kwargs: Any) -> Any:
            self.calls += 1
            raise AssertionError("out-of-domain backend call is forbidden")

    provider = SpyProvider()
    with pytest.raises(service._LowSideDomainInfeasible):
        service._state_from_enthalpy(
            provider, service.H_MIN_J_KG - Decimal("1e-20"), shell_search_state=True
        )
    assert provider.calls == 0


def test_exact_reviewed_upper_property_endpoint_uses_tp_not_clipped_ph() -> None:
    thermo = service._state_from_enthalpy(CoolPropProvider(), service.H_MAX_J_KG)
    assert thermo.native.temperature_k == 300.0
    assert thermo.native.pressure_pa == float(service.REFERENCE_PRESSURE_PA)
    assert thermo.native.phase.value == "liquid"
    assert thermo.snapshot.query_type == "TP"
    assert thermo.snapshot.enthalpy_j_kg == str(Decimal(str(thermo.native.enthalpy_j_kg)))


def test_ph_input_above_reviewed_upper_enthalpy_is_rejected_before_backend() -> None:
    class SpyProvider:
        calls = 0

        def state_ph(self, *_args: Any, **_kwargs: Any) -> Any:
            self.calls += 1
            raise AssertionError("out-of-domain PH input must not reach provider")

    provider = SpyProvider()
    with pytest.raises(service._Stage3Failure) as failure:
        service._state_from_enthalpy(provider, service.H_MAX_J_KG + Decimal("1e-6"))
    assert failure.value.code == "BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT"
    assert provider.calls == 0


def test_task172_support_identity_and_roundoff_floor_replay() -> None:
    payload = _evidence()["shared_native_payload"]
    raw = payload["TASK172_request"]
    encoded = json.dumps(raw, separators=(",", ":"), ensure_ascii=False)
    request = Task172LocalRequest.model_validate_json(encoded, strict=True)
    provider = CoolPropProvider()
    result = task172_validate(request, provider)
    assert result.status == "VALIDATED"
    assert result.physical_support_id == recompute_task172_support_id(request)
    duty_i, duty_wall, duty_o, temp_floor = recompute_task172_local_roundoff_bounds(request, result)
    assert min(duty_i, duty_wall, duty_o, temp_floor) >= 0
    assert temp_floor.is_finite()


def _historical_n2_cell_inputs() -> tuple[Any, Any, Any, Any, Any]:
    provider = CoolPropProvider()
    authority, _, _ = replay_shell_flow_authority(
        json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")), provider
    )
    support = build_local_support(4, 2, 0)
    tube = service._state_from_enthalpy(provider, Decimal("109051.37045646932"))
    shell = service._state_from_enthalpy(provider, Decimal("105416.83286221564"))
    return support, tube, shell, provider, authority


def _valid_trial(q_w: float, residual: str, label: str) -> service._CellTrial:
    return service._CellTrial(
        q_w,
        "VALID_CELL_EVALUATION",
        SimpleNamespace(task172_result=SimpleNamespace(result_hash=label)),
        Decimal(residual),
    )


def test_injected_residual_acceptance_block_is_a_signless_nonphysical_hole(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    support, tube, shell, provider, authority = _historical_n2_cell_inputs()

    def return_validly_hashed_hole(
        request: Task172LocalRequest, _provider: Any
    ) -> Task172BlockedResult:
        candidate = Task172BlockedResult(
            status="BLOCKED",
            failure_code="BLOCKED_RESIDUAL_ACCEPTANCE",
            field_path="solver.residual",
            request_hash=service.recompute_task172_request_hash(request),
            diagnostic_last_iterate=("q_internal_w=999999999", "blocked_residual_sign=forbidden"),
            blockers=("BLOCKED_RESIDUAL_ACCEPTANCE",),
            blocked_result_hash="0" * 64,
        )
        return candidate.model_copy(
            update={"blocked_result_hash": recompute_task172_blocked_result_hash(candidate)}
        )

    monkeypatch.setattr(service, "task172_validate", return_validly_hashed_hole)
    with pytest.raises(service._Task172NumericalHole):
        service._cell_evaluation(
            4436.3679921671355,
            support=support,
            tube_upstream=tube,
            shell_physical_left=shell,
            provider=provider,
            shell_authority=authority,
        )

    hole = service._CellTrial(4436.3679921671355, "TASK172_NUMERICAL_HOLE")
    assert hole.residual is None
    assert hole.evaluation is None
    left = _valid_trial(4436.0, "-0.2", "left-valid-result")
    right = _valid_trial(4437.0, "0.2", "right-valid-result")
    cache: dict[float, service._CellTrial] = {}
    probe_order: list[float] = []

    def evaluate(q_w: float) -> service._CellTrial:
        probe_order.append(q_w)
        trial = _valid_trial(q_w, "-0.1" if q_w < hole.q_w else "0.1", f"valid-{q_w}")
        cache[q_w] = trial
        return trial

    new_left, new_right, selected = service._dyadic_refine_valid_bracket(
        left,
        right,
        hole,
        evaluate=evaluate,
        all_trials=lambda: [left, hole, right, *cache.values()],
        record_hole_neighbors=lambda _trials: None,
    )
    assert (
        probe_order
        == sorted(probe_order)
        == [
            (4436.0 + hole.q_w) / 2.0,
            (hole.q_w + 4437.0) / 2.0,
        ]
    )
    assert selected is None
    assert new_left.classification == new_right.classification == "VALID_CELL_EVALUATION"
    assert new_left.residual is not None and new_left.residual <= 0
    assert new_right.residual is not None and new_right.residual >= 0
    assert hole.residual is None and hole.evaluation is None


def test_injected_hole_recovery_returns_only_a_native_task172_solution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    support, tube, shell, provider, authority = _historical_n2_cell_inputs()
    native_evaluation = service._cell_evaluation
    calls: list[float] = []

    def inject_one_caller_level_hole(q_w: float, **kwargs: Any) -> Any:
        calls.append(q_w)
        if len(calls) == 3:
            raise service._Task172NumericalHole
        return native_evaluation(q_w, **kwargs)

    monkeypatch.setattr(service, "_cell_evaluation", inject_one_caller_level_hole)
    solution = service._solve_cell(
        support=support,
        tube_upstream=tube,
        shell_physical_left=shell,
        provider=provider,
        shell_authority=authority,
    )
    assert len(calls) > 3
    assert type(solution.task172_result) is task172_models.Task172LocalResult
    assert solution.task172_result.status == "VALIDATED"
    assert abs(solution.q_w - solution.task172_result.signed_q_hot_to_cold_w) <= Decimal("1e-6")


def test_historical_n2_native_classification_is_characterization_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    support, tube, shell, provider, authority = _historical_n2_cell_inputs()
    q_trial = 4436.3679921671355
    native_results: list[Any] = []
    native_validate = service.task172_validate

    def record_native_result(*args: Any, **kwargs: Any) -> Any:
        result = native_validate(*args, **kwargs)
        native_results.append(result)
        return result

    monkeypatch.setattr(service, "task172_validate", record_native_result)
    try:
        direct = service._cell_evaluation(
            q_trial,
            support=support,
            tube_upstream=tube,
            shell_physical_left=shell,
            provider=provider,
            shell_authority=authority,
        )
    except service._Task172NumericalHole:
        assert type(native_results[-1]) is Task172BlockedResult
        assert native_results[-1].failure_code == "BLOCKED_RESIDUAL_ACCEPTANCE"
        assert native_results[-1].blocked_result_hash == recompute_task172_blocked_result_hash(
            native_results[-1]
        )
        observation = "BLOCKED_RESIDUAL_ACCEPTANCE"
        characterized = service._CellTrial(q_trial, "TASK172_NUMERICAL_HOLE")
        assert characterized.residual is None and characterized.evaluation is None
    else:
        assert type(native_results[-1]) is task172_models.Task172LocalResult
        assert native_results[-1].status == "VALIDATED"
        assert direct.task172_result.result_hash == native_results[-1].result_hash
        observation = "VALID_TASK172_RESULT"

    # The native classification is an environment observation, never an invariant.
    assert observation in {"BLOCKED_RESIDUAL_ACCEPTANCE", "VALID_TASK172_RESULT"}
    accepted = service._solve_cell(
        support=support,
        tube_upstream=tube,
        shell_physical_left=shell,
        provider=provider,
        shell_authority=authority,
    )
    assert type(accepted.task172_result) is task172_models.Task172LocalResult
    assert accepted.task172_result.status == "VALIDATED"
    assert abs(accepted.q_w - accepted.task172_result.signed_q_hot_to_cold_w) <= Decimal("1e-6")


def test_task172_non_residual_blocker_remains_hard_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    support, tube, shell, provider, authority = _historical_n2_cell_inputs()
    request = service._task172_request(support, tube, shell, authority)
    blocked = Task172BlockedResult(
        status="BLOCKED",
        failure_code="BLOCKED_NONCONVERGENCE",
        field_path="solver",
        request_hash=service.recompute_task172_request_hash(request),
        blockers=("BLOCKED_NONCONVERGENCE",),
        blocked_result_hash="0" * 64,
    )
    monkeypatch.setattr(service, "task172_validate", lambda *_args, **_kwargs: blocked)
    with pytest.raises(service._Stage3Failure) as caught:
        service._cell_evaluation(
            4436.0,
            support=support,
            tube_upstream=tube,
            shell_physical_left=shell,
            provider=provider,
            shell_authority=authority,
        )
    assert caught.value.code == "BLOCKED_TASK172_LOCAL_CONSTITUTIVE_CLOSURE"
    assert caught.value.diagnostics == ("BLOCKED_NONCONVERGENCE",)


def test_invalid_residual_blocked_identity_remains_hard_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    support, tube, shell, provider, authority = _historical_n2_cell_inputs()
    request = service._task172_request(support, tube, shell, authority)
    invalid = Task172BlockedResult(
        status="BLOCKED",
        failure_code="BLOCKED_RESIDUAL_ACCEPTANCE",
        field_path="solver.residual",
        request_hash=service.recompute_task172_request_hash(request),
        diagnostic_last_iterate=("q_internal_w=999999",),
        blockers=("BLOCKED_RESIDUAL_ACCEPTANCE",),
        blocked_result_hash="0" * 64,
    )
    monkeypatch.setattr(service, "task172_validate", lambda *_args, **_kwargs: invalid)
    with pytest.raises(service._Stage3Failure) as caught:
        service._cell_evaluation(
            4436.0,
            support=support,
            tube_upstream=tube,
            shell_physical_left=shell,
            provider=provider,
            shell_authority=authority,
        )
    assert caught.value.code == "BLOCKED_TASK172_BLOCKED_RESULT_IDENTITY_REPLAY"


def test_dyadic_probe_order_narrowest_pair_and_tie_break_are_deterministic() -> None:
    endpoint_left = service._CellTrial(
        0.0,
        "VALID_CELL_EVALUATION",
        SimpleNamespace(task172_result=SimpleNamespace(result_hash="l")),
        Decimal("-1"),
    )
    endpoint_right = service._CellTrial(
        1.0,
        "VALID_CELL_EVALUATION",
        SimpleNamespace(task172_result=SimpleNamespace(result_hash="r")),
        Decimal("1"),
    )
    hole = service._CellTrial(0.5, "TASK172_NUMERICAL_HOLE")
    cache: dict[float, service._CellTrial] = {}
    order: list[float] = []

    def evaluate(q: float) -> service._CellTrial:
        order.append(q)
        residual = Decimal("-0.1") if q < hole.q_w else Decimal("0.1")
        trial = _valid_trial(q, str(residual), f"{q}")
        cache[q] = trial
        return trial

    neighbors: list[list[service._CellTrial]] = []
    left, right, solution = service._dyadic_refine_valid_bracket(
        endpoint_left,
        endpoint_right,
        hole,
        evaluate=evaluate,
        all_trials=lambda: [endpoint_left, hole, endpoint_right, *cache.values()],
        record_hole_neighbors=neighbors.append,
    )
    assert solution is None
    assert order == [0.25, 0.75]
    assert (left.q_w, right.q_w) == (0.25, 0.75)
    assert len(neighbors) == 1


def test_local_hole_probe_sequence_is_repeatable_for_same_inputs() -> None:
    def run_once() -> tuple[float, ...]:
        left = _valid_trial(0.0, "-1", "left")
        right = _valid_trial(1.0, "1", "right")
        hole = service._CellTrial(0.5, "TASK172_NUMERICAL_HOLE")
        cache: dict[float, service._CellTrial] = {}
        probes: list[float] = []

        def evaluate(q: float) -> service._CellTrial:
            probes.append(q)
            trial = service._CellTrial(q, "TASK172_NUMERICAL_HOLE")
            cache[q] = trial
            return trial

        with pytest.raises(service._Stage3Failure):
            service._dyadic_refine_valid_bracket(
                left,
                right,
                hole,
                evaluate=evaluate,
                all_trials=lambda: [left, hole, right, *cache.values()],
                record_hole_neighbors=lambda _trials: None,
            )
        return tuple(probes)

    first = run_once()
    second = run_once()
    assert first == second
    assert len(first) == 2 * service.MAX_HOLE_DYADIC_LEVELS_PER_BRACKET


def test_narrowest_adjacent_valid_sign_pair_wins_with_lower_q_tie_break() -> None:
    samples = [
        _valid_trial(0.0, "-1", "a"),
        _valid_trial(0.1, "1", "b"),
        _valid_trial(0.2, "-1", "c"),
        _valid_trial(0.25, "1", "d"),
        _valid_trial(0.5, "-1", "e"),
        _valid_trial(0.55, "1", "f"),
    ]
    pairs = service._valid_sign_pairs(samples)
    assert [(left.q_w, right.q_w) for left, right in pairs] == [
        (0.2, 0.25),
        (0.5, 0.55),
        (0.0, 0.1),
    ]


def test_initial_upper_numerical_hole_can_yield_a_valid_only_sign_bracket() -> None:
    lower = service._CellTrial(
        0.0,
        "VALID_CELL_EVALUATION",
        SimpleNamespace(task172_result=SimpleNamespace(result_hash="lower")),
        Decimal("-1"),
    )
    upper_hole = service._CellTrial(1.0, "TASK172_NUMERICAL_HOLE")
    cache = {0.0: lower, 1.0: upper_hole}
    probes: list[float] = []

    def evaluate(q: float) -> service._CellTrial:
        probes.append(q)
        trial = _valid_trial(q, "0.5", f"{q}")
        cache[q] = trial
        return trial

    left, right, eligible = service._discover_valid_sign_bracket_from_endpoint_holes(
        0.0,
        1.0,
        (lower, upper_hole),
        evaluate=evaluate,
        all_trials=lambda: list(cache.values()),
        record_hole_neighbors=lambda _trials: None,
    )
    assert probes == [0.5]
    assert eligible is None
    assert (left.q_w, right.q_w) == (0.0, 0.5)
    assert left.classification == right.classification == "VALID_CELL_EVALUATION"
    assert left.residual is not None and left.residual < 0
    assert right.residual is not None and right.residual > 0
    assert upper_hole.evaluation is None and upper_hole.residual is None


def test_initial_lower_numerical_hole_can_yield_a_valid_only_sign_bracket() -> None:
    lower_hole = service._CellTrial(0.0, "TASK172_NUMERICAL_HOLE")
    upper = service._CellTrial(
        1.0,
        "VALID_CELL_EVALUATION",
        SimpleNamespace(task172_result=SimpleNamespace(result_hash="upper")),
        Decimal("1"),
    )
    cache = {0.0: lower_hole, 1.0: upper}
    probes: list[float] = []

    def evaluate(q: float) -> service._CellTrial:
        probes.append(q)
        residual = "-0.5" if q == 0.25 else "0.5"
        trial = _valid_trial(q, residual, f"{q}")
        cache[q] = trial
        return trial

    left, right, eligible = service._discover_valid_sign_bracket_from_endpoint_holes(
        0.0,
        1.0,
        (lower_hole, upper),
        evaluate=evaluate,
        all_trials=lambda: list(cache.values()),
        record_hole_neighbors=lambda _trials: None,
    )
    assert probes == [0.5, 0.25]
    assert eligible is None
    assert (left.q_w, right.q_w) == (0.25, 0.5)
    assert left.classification == right.classification == "VALID_CELL_EVALUATION"
    assert left.residual is not None and left.residual < 0
    assert right.residual is not None and right.residual > 0
    assert lower_hole.evaluation is None and lower_hole.residual is None


def test_local_dyadic_hole_search_is_linear_and_enforces_twelve_levels() -> None:
    left = service._CellTrial(
        0.0,
        "VALID_CELL_EVALUATION",
        SimpleNamespace(task172_result=SimpleNamespace(result_hash="l")),
        Decimal("-1"),
    )
    right = service._CellTrial(
        1.0,
        "VALID_CELL_EVALUATION",
        SimpleNamespace(task172_result=SimpleNamespace(result_hash="r")),
        Decimal("1"),
    )
    hole = service._CellTrial(0.5, "TASK172_NUMERICAL_HOLE")
    cache: dict[float, service._CellTrial] = {}

    def evaluate(q: float) -> service._CellTrial:
        trial = service._CellTrial(q, "TASK172_NUMERICAL_HOLE")
        cache[q] = trial
        return trial

    with pytest.raises(service._Stage3Failure) as caught:
        service._dyadic_refine_valid_bracket(
            left,
            right,
            hole,
            evaluate=evaluate,
            all_trials=lambda: [left, hole, right, *cache.values()],
            record_hole_neighbors=lambda _trials: None,
        )
    assert caught.value.code == "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED"
    assert "maximum_hole_dyadic_levels=12" in caught.value.diagnostics
    assert len(cache) == 2 * service.MAX_HOLE_DYADIC_LEVELS_PER_BRACKET


def test_cell_root_search_depth_and_evaluation_budget_are_compatible() -> None:
    worst_case = service.cell_root_worst_case_task172_evaluations()
    assert service.MAX_HOLE_DYADIC_LEVELS_PER_BRACKET == 12
    assert service.MAX_HOLE_RECOVERY_BRACKETS_PER_CELL == 15
    assert service.MAX_HOLE_RECOVERY_PROBES_PER_CELL == 360
    assert service.MAX_CELL_TASK172_EVALUATIONS == 512
    assert worst_case == 491
    assert worst_case <= service.MAX_CELL_TASK172_EVALUATIONS
    assert service.CELL_ROOT_SOLVER_AUTHORITY["worst_case_authorized_task172_evaluations"] == (
        worst_case
    )


def test_cell_task172_evaluation_cap_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    support = build_local_support(0, 1, 0)
    provider = CoolPropProvider()
    tube = service._state_at_inlet(provider, Decimal("300"))
    shell = service._state_at_inlet(provider, Decimal("299"))
    monkeypatch.setattr(service, "MAX_CELL_TASK172_EVALUATIONS", 3)
    fake = SimpleNamespace(
        task172_result=SimpleNamespace(signed_q_hot_to_cold_w=Decimal("1.234567"))
    )
    monkeypatch.setattr(service, "_cell_evaluation", lambda *_args, **_kwargs: fake)
    with pytest.raises(service._Stage3Failure) as caught:
        service._solve_cell(
            support=support,
            tube_upstream=tube,
            shell_physical_left=shell,
            provider=provider,
            shell_authority=object(),
            mesh_subdivisions=2,
            outer_iteration=5,
            shooting_enthalpy=Decimal("105416.83286221564"),
        )
    assert caught.value.code == "BLOCKED_CELL_ROOT_RESOURCE_EXHAUSTION"
    diagnostics = set(caught.value.diagnostics)
    for key in (
        "mesh_subdivisions=2",
        f"physical_support_id={support.physical_segment_id}",
        f"tube_cell_id={support.tube_cell_id}",
        f"shell_cell_id={support.shell_cell_id}",
        f"wall_interface_id={support.wall_interface_id}",
        "outer_iteration=5",
        "shooting_enthalpy_j_kg=105416.83286221564",
        "left_q_w=",
        "right_q_w=",
        "left_f_q_w=",
        "right_f_q_w=",
        "current_search_level=",
        "cell_evaluation_count=",
        "cell_valid_evaluation_count=",
        "cell_hole_count=",
        "hole_codes=",
        "last_valid_bracket_width_w=",
    ):
        assert any(item.startswith(key) for item in diagnostics)


def _fake_cell_evaluation_for_capture(
    q_w: float, signed_q_w: str, request: Task172LocalRequest
) -> Any:
    digest = service.canonical_sha256({"q_trial_w": repr(q_w), "signed_q_w": signed_q_w})
    return SimpleNamespace(
        task172_request=request,
        task172_result=SimpleNamespace(
            request_hash=service.recompute_task172_request_hash(request),
            result_id=f"result-{digest}",
            result_hash=digest,
            signed_q_hot_to_cold_w=Decimal(signed_q_w),
        ),
        tube_local=SimpleNamespace(native=SimpleNamespace(temperature_k=299.5)),
        shell_local=SimpleNamespace(native=SimpleNamespace(temperature_k=299.0)),
    )


def test_endpoint_hole_capture_keeps_each_valid_recovery_level_and_depth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = CoolPropProvider()
    support = build_local_support(3, 16, 0)
    tube = service._state_at_inlet(provider, Decimal("300"))
    shell = service._state_at_inlet(provider, Decimal("299"))
    stats = service._CellSearchStats()
    calls: list[float] = []
    authority, _, _ = replay_shell_flow_authority(
        json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")), provider
    )

    def endpoint_hole_then_valid_points(q_w: float, **kwargs: Any) -> Any:
        calls.append(q_w)
        if q_w == 0.0:
            raise service._Task172NumericalHole("request-hole", "blocked-hash")
        request = service._task172_request(
            kwargs["support"],
            kwargs["tube_upstream"],
            kwargs["shell_physical_left"],
            authority,
        )
        return _fake_cell_evaluation_for_capture(q_w, "0", request)

    monkeypatch.setattr(service, "_cell_evaluation", endpoint_hole_then_valid_points)
    with pytest.raises(service._Stage3Failure) as caught:
        service._solve_cell(
            support=support,
            tube_upstream=tube,
            shell_physical_left=shell,
            provider=provider,
            shell_authority=object(),
            search_stats=stats,
            capture_diagnostics=True,
            mesh_subdivisions=16,
            outer_iteration=2,
            shooting_enthalpy=Decimal("106853.814770607445"),
        )

    assert caught.value.code == "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED"
    summary = stats.endpoint_hole_summaries[-1]
    assert summary.hole_endpoint_side == "LOWER_ENDPOINT"
    assert summary.hole_endpoint_q_w == "0.0"
    assert summary.initial_valid_anchor_f_q_w == summary.physical_upper_q_w
    level_receipts = [
        receipt
        for receipt in stats.endpoint_hole_level_receipts
        if receipt.physical_support_id == support.physical_segment_id
    ]
    assert [receipt.level for receipt in level_receipts] == list(range(1, 13))
    assert len(calls) == 14
    assert len(stats.trial_receipts) == len(calls)
    assert stats.maximum_hole_recovery_depth_observed == 12
    for receipt in level_receipts:
        assert receipt.probe_classification == "VALID_CELL_EVALUATION"
        assert receipt.probe_f_q_w == receipt.probe_q_w
        assert receipt.probe_task172_result_hash is not None
        assert receipt.valid_anchor_before_task172_result_hash
        assert receipt.valid_anchor_after_task172_result_hash
        assert receipt.sign_pair_found is False
        assert receipt.eligible_root_found is False

    hole_receipt = next(
        receipt
        for receipt in stats.trial_receipts
        if receipt.classification == "TASK172_NUMERICAL_HOLE"
    )
    assert hole_receipt.task172_request_hash == "request-hole"
    assert hole_receipt.blocked_result_hash == "blocked-hash"
    assert hole_receipt.f_q_w is None
    assert hole_receipt.residual_sign is None
    assert hole_receipt.physical_result_id is None
    assert hole_receipt.physical_result_hash is None
    assert hole_receipt.diagnostic_last_iterate_used is False


def test_upper_endpoint_hole_capture_retains_all_twelve_valid_probes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = CoolPropProvider()
    support = build_local_support(3, 16, 0)
    tube = service._state_at_inlet(provider, Decimal("300"))
    shell = service._state_at_inlet(provider, Decimal("299"))
    authority, _, _ = replay_shell_flow_authority(
        json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")), provider
    )
    stats = service._CellSearchStats()
    calls: list[float] = []

    def upper_endpoint_hole(q_w: float, **kwargs: Any) -> Any:
        calls.append(q_w)
        if len(calls) == 2:
            raise service._Task172NumericalHole("upper-hole-request", "upper-hole-result")
        request = service._task172_request(
            kwargs["support"],
            kwargs["tube_upstream"],
            kwargs["shell_physical_left"],
            authority,
        )
        signed_q = str(Decimal(str(q_w)) + Decimal("1000"))
        return _fake_cell_evaluation_for_capture(q_w, signed_q, request)

    monkeypatch.setattr(service, "_cell_evaluation", upper_endpoint_hole)
    with pytest.raises(service._Stage3Failure) as caught:
        service._solve_cell(
            support=support,
            tube_upstream=tube,
            shell_physical_left=shell,
            provider=provider,
            shell_authority=authority,
            search_stats=stats,
            capture_diagnostics=True,
            mesh_subdivisions=16,
            outer_iteration=2,
            shooting_enthalpy=Decimal("106853.814770607445"),
        )

    assert caught.value.code == "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED"
    summary = stats.endpoint_hole_summaries[-1]
    assert summary.hole_endpoint_side == "UPPER_ENDPOINT"
    assert summary.hole_endpoint_q_w == repr(calls[1])
    level_receipts = stats.endpoint_hole_level_receipts
    assert [receipt.level for receipt in level_receipts] == list(range(1, 13))
    assert len(stats.trial_receipts) == len(calls) == 14
    assert all(
        receipt.probe_classification == "VALID_CELL_EVALUATION" for receipt in level_receipts
    )
    assert all(
        receipt.probe_f_q_w is not None and Decimal(receipt.probe_f_q_w) < 0
        for receipt in level_receipts
    )
    assert all(receipt.sign_pair_found is False for receipt in level_receipts)
    hole_receipt = next(
        receipt
        for receipt in stats.trial_receipts
        if receipt.classification == "TASK172_NUMERICAL_HOLE"
    )
    assert hole_receipt.q_trial_w == repr(calls[1])
    assert hole_receipt.task172_request_hash == "upper-hole-request"
    assert hole_receipt.blocked_result_hash == "upper-hole-result"
    assert hole_receipt.f_q_w is None
    assert hole_receipt.residual_sign is None
    assert hole_receipt.physical_result_hash is None
    assert hole_receipt.diagnostic_last_iterate_used is False


def test_multiple_numerical_holes_are_all_retained_without_blocked_signs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = CoolPropProvider()
    support = build_local_support(0, 1, 0)
    tube = service._state_at_inlet(provider, Decimal("300"))
    shell = service._state_at_inlet(provider, Decimal("299"))
    stats = service._CellSearchStats()
    calls: list[float] = []
    tube_capacity = service.TUBE_MASS_FLOW_KG_S * (
        Decimal(str(tube.native.enthalpy_j_kg)) - service.H_MIN_J_KG
    )
    shell_capacity = service.SHELL_MASS_FLOW_KG_S * (
        Decimal(str(shell.native.enthalpy_j_kg)) - service.H_MIN_J_KG
    )
    upper_q = float(min(tube_capacity, shell_capacity))
    authority, _, _ = replay_shell_flow_authority(
        json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")), provider
    )

    def multiple_holes(q_w: float, **kwargs: Any) -> Any:
        calls.append(q_w)
        if q_w not in (0.0, upper_q):
            raise service._Task172NumericalHole(f"request-{repr(q_w)}", f"blocked-{repr(q_w)}")
        signed_q = "1" if q_w == 0.0 else "0"
        request = service._task172_request(
            kwargs["support"],
            kwargs["tube_upstream"],
            kwargs["shell_physical_left"],
            authority,
        )
        return _fake_cell_evaluation_for_capture(q_w, signed_q, request)

    monkeypatch.setattr(service, "_cell_evaluation", multiple_holes)
    with pytest.raises(service._Stage3Failure) as caught:
        service._solve_cell(
            support=support,
            tube_upstream=tube,
            shell_physical_left=shell,
            provider=provider,
            shell_authority=object(),
            search_stats=stats,
            capture_diagnostics=True,
        )

    assert caught.value.code == "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED"
    hole_receipts = [
        receipt
        for receipt in stats.trial_receipts
        if receipt.classification == "TASK172_NUMERICAL_HOLE"
    ]
    assert len(hole_receipts) == stats.task172_numerical_hole_count == 25
    assert len(stats.task172_numerical_hole_trials) == 25
    assert len(calls) == len(stats.trial_receipts) == 27
    assert all(
        receipt.f_q_w is None
        and receipt.residual_sign is None
        and receipt.physical_result_id is None
        and receipt.physical_result_hash is None
        and receipt.diagnostic_last_iterate_used is False
        for receipt in hole_receipts
    )


def test_diagnostic_capture_does_not_change_native_trial_or_task172_call_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    support, tube, shell, provider, authority = _historical_n2_cell_inputs()
    native_validate = service.task172_validate

    def run(capture: service._CellSearchStats | None) -> tuple[Any, list[tuple[str, str]]]:
        observed: list[tuple[str, str]] = []

        def counted_validate(request: Task172LocalRequest, state_provider: Any) -> Any:
            result = native_validate(request, state_provider)
            identity = (
                result.result_hash
                if type(result) is task172_models.Task172LocalResult
                else result.blocked_result_hash
            )
            observed.append((service.recompute_task172_request_hash(request), identity))
            return result

        monkeypatch.setattr(service, "task172_validate", counted_validate)
        try:
            result = service._solve_cell(
                support=support,
                tube_upstream=tube,
                shell_physical_left=shell,
                provider=provider,
                shell_authority=authority,
                search_stats=capture,
                capture_diagnostics=capture is not None,
            )
        except service._Stage3Failure as exc:
            outcome: Any = ("BLOCKED", exc.code, exc.diagnostics)
        else:
            outcome = ("VALID", result.task172_result.result_hash)
        return outcome, observed

    without_capture = run(None)
    captured_stats = service._CellSearchStats()
    with_capture = run(captured_stats)
    assert with_capture == without_capture
    assert len(captured_stats.trial_receipts) == len(with_capture[1])
    assert captured_stats.task172_local_evaluation_count == len(with_capture[1])


def test_duty_relative_metric_is_compared_and_reported_dimensionlessly() -> None:
    def run(n: int, duty: str, floor: str) -> Any:
        return SimpleNamespace(
            subdivisions=n,
            observables=SimpleNamespace(
                interval_duty_w=(Decimal(duty),) * 5,
                total_duty_w=Decimal(duty),
                duty_roundoff_floor_w=Decimal(floor),
                wall_inner_min_k=Decimal("299"),
                wall_inner_max_k=Decimal("300"),
                wall_outer_min_k=Decimal("298.5"),
                wall_outer_max_k=Decimal("299.5"),
                wall_temperature_roundoff_floor_k=Decimal("1e-10"),
            ),
        )

    comparison = service._compare_meshes(run(1, "1000", "0.001"), run(2, "992", "0.001"))
    assert comparison.duty_difference_w == Decimal("8")
    assert comparison.duty_metric == Decimal("8") / Decimal("1000")
    assert comparison.duty_metric_units == "RELATIVE_FRACTION"
    assert comparison.duty_metric_threshold == Decimal("0.01")
    assert comparison.duty_precision_floor_metric == Decimal("0.002") / Decimal("1000")
    assert comparison.duty_status == "PASS"


def _fake_mesh_run(enthalpy: Decimal, residual_h: Decimal) -> Any:
    residual_t = residual_h / Decimal("4181.0")
    return SimpleNamespace(
        shooting_enthalpy=enthalpy,
        observables=SimpleNamespace(
            terminal_boundary_residual_j_kg=residual_h,
            terminal_boundary_residual_k=residual_t,
        ),
    )


def test_boundary_root_uses_infeasible_low_and_valid_high_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    low = Decimal("0")
    high = Decimal("100")
    root = Decimal("37.123456789")
    monkeypatch.setattr(service, "H_MIN_J_KG", low)
    monkeypatch.setattr(service, "H_MAX_J_KG", high)
    monkeypatch.setattr(
        service,
        "_terminal_tolerance_pass",
        lambda run: (
            Decimal(0)
            <= run.observables.terminal_boundary_residual_k
            <= service.TERMINAL_TOLERANCE_K
            and run.observables.terminal_boundary_residual_j_kg <= Decimal("0.00005")
        ),
    )
    observations: list[tuple[Decimal, str]] = []

    def trial(_n: int, h: Decimal, _provider: Any, _authority: Any, _iteration: int) -> Any:
        if h < root:
            observations.append((h, "LOW_SIDE_DOMAIN_INFEASIBLE"))
            return service._OuterTrial("LOW_SIDE_DOMAIN_INFEASIBLE", h)
        residual = h - root
        run = _fake_mesh_run(h, residual)
        observations.append((h, "VALID_TRAJECTORY"))
        return service._OuterTrial("VALID_TRAJECTORY", h, mesh_run=run)

    monkeypatch.setattr(service, "_outer_trial", trial)
    accepted = service._solve_outer_boundary(1, object(), object())
    assert observations[0] == (low, "LOW_SIDE_DOMAIN_INFEASIBLE")
    assert observations[1] == (high, "VALID_TRAJECTORY")
    assert accepted.shooting_enthalpy >= root
    assert accepted.observables.terminal_boundary_residual_j_kg >= 0
    assert accepted.observables.terminal_boundary_residual_k >= 0
    assert accepted.observables.terminal_boundary_residual_k <= Decimal("1e-8")
    assert all(classification != "VALID_NEGATIVE_RESIDUAL" for _, classification in observations)


def test_boundary_root_target_is_exactly_the_approved_property_lower_boundary() -> None:
    assert Decimal("104920.11980926784") == service.H_MIN_J_KG
    assert Decimal("298.15") == service.T_MIN_K


def test_boundary_bisection_is_deterministic_and_returns_valid_high_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "H_MIN_J_KG", Decimal("0"))
    monkeypatch.setattr(service, "H_MAX_J_KG", Decimal("100"))
    root = Decimal("33.333333333")
    sequences: list[tuple[Decimal, ...]] = []

    def solve_once() -> Any:
        sequence: list[Decimal] = []

        def trial(_n: int, h: Decimal, _provider: Any, _authority: Any, _iteration: int) -> Any:
            sequence.append(h)
            if h < root:
                return service._OuterTrial("LOW_SIDE_DOMAIN_INFEASIBLE", h)
            return service._OuterTrial("VALID_TRAJECTORY", h, mesh_run=_fake_mesh_run(h, h - root))

        monkeypatch.setattr(service, "_outer_trial", trial)
        monkeypatch.setattr(
            service,
            "_terminal_tolerance_pass",
            lambda run: (
                run.observables.terminal_boundary_residual_k <= Decimal("1e-8")
                and run.observables.terminal_boundary_residual_j_kg <= Decimal("0.00005")
            ),
        )
        result = service._solve_outer_boundary(1, object(), object())
        sequences.append(tuple(sequence))
        return result

    first = solve_once()
    second = solve_once()
    assert sequences[0] == sequences[1]
    assert first.shooting_enthalpy == second.shooting_enthalpy
    assert first.shooting_enthalpy >= root


@pytest.mark.parametrize(
    ("terminal_residual_k", "expected_code"),
    [
        (Decimal("2e-8"), "BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED"),
        (Decimal("1.00000000001e-8"), "PRECISION_FLOOR_UNRESOLVED"),
    ],
)
def test_outer_bisection_representability_floor_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
    terminal_residual_k: Decimal,
    expected_code: str,
) -> None:
    monkeypatch.setattr(service, "H_MIN_J_KG", Decimal("1.0000000000000000"))
    monkeypatch.setattr(service, "H_MAX_J_KG", Decimal("1.0000000000000001"))
    monkeypatch.setattr(service, "_terminal_tolerance_pass", lambda _run: False)

    def trial(_n: int, h: Decimal, _provider: Any, _authority: Any, _iteration: int) -> Any:
        if h == service.H_MIN_J_KG:
            return service._OuterTrial("LOW_SIDE_DOMAIN_INFEASIBLE", h)
        run = SimpleNamespace(
            shooting_enthalpy=h,
            observables=SimpleNamespace(
                terminal_boundary_residual_k=terminal_residual_k,
                terminal_boundary_residual_j_kg=Decimal("0.0001"),
            ),
        )
        return service._OuterTrial("VALID_TRAJECTORY", h, mesh_run=run)

    monkeypatch.setattr(service, "_outer_trial", trial)
    with pytest.raises(service._Stage3Failure) as caught:
        service._solve_outer_boundary(1, object(), object())
    assert caught.value.code == expected_code


@pytest.mark.parametrize(
    ("seen_low", "seen_valid", "value", "classification"),
    [
        ([Decimal("10")], [], Decimal("5"), "VALID_TRAJECTORY"),
        ([], [Decimal("20")], Decimal("25"), "LOW_SIDE_DOMAIN_INFEASIBLE"),
    ],
)
def test_nonmonotonic_classification_fails_closed(
    seen_low: list[Decimal],
    seen_valid: list[Decimal],
    value: Decimal,
    classification: str,
) -> None:
    with pytest.raises(service._Stage3Failure) as caught:
        service._assert_outer_classification_order(seen_low, seen_valid, value, classification)
    assert caught.value.code == "BLOCKED_OUTER_FEASIBILITY_CLASSIFICATION_NONMONOTONIC"


def test_task172_failure_is_hard_blocker_not_low_side(monkeypatch: pytest.MonkeyPatch) -> None:
    def failed(*_args: Any, **_kwargs: Any) -> Any:
        raise service._Stage3Failure(
            "BLOCKED_TASK172_LOCAL_CONSTITUTIVE_CLOSURE", "BLOCKED_RESIDUAL_ACCEPTANCE"
        )

    monkeypatch.setattr(service, "_valid_trajectory", failed)
    trial = service._outer_trial(1, Decimal("105000"), object(), object(), 1)
    assert trial.classification == "HARD_BLOCKER"
    assert trial.mesh_run is None
    assert trial.diagnostics[0] == "BLOCKED_TASK172_LOCAL_CONSTITUTIVE_CLOSURE"


def test_low_side_outer_classification_never_contains_partial_mesh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def infeasible(*_args: Any, **_kwargs: Any) -> Any:
        raise service._LowSideDomainInfeasible

    monkeypatch.setattr(service, "_valid_trajectory", infeasible)
    trial = service._outer_trial(1, service.H_MIN_J_KG, object(), object(), 0)
    assert trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE"
    assert trial.mesh_run is None


def test_negative_terminal_residual_cannot_be_a_valid_outer_trajectory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = SimpleNamespace(
        observables=SimpleNamespace(
            terminal_boundary_residual_j_kg=Decimal("-1e-9"),
            terminal_boundary_residual_k=Decimal("-1e-12"),
        )
    )
    monkeypatch.setattr(service, "_valid_trajectory", lambda *_args, **_kwargs: run)
    trial = service._outer_trial(1, Decimal("105000"), object(), object(), 1)
    assert trial.classification == "HARD_BLOCKER"
    assert trial.diagnostics == ("BLOCKED_NEGATIVE_TERMINAL_RESIDUAL",)


def test_precision_floor_unresolved_is_not_pass() -> None:
    result = service._classify_difference(
        Decimal("0.0100000000000000000000000001"),
        Decimal("1e-10"),
        Decimal("0.01"),
    )
    assert result == "PRECISION_FLOOR_UNRESOLVED"


def test_strict_request_rejects_unknown_fields_and_unreviewed_mesh_sequence() -> None:
    request = {
        "case_revision_id": "V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R2",
        "case_mode": "RATING_FIXED_GEOMETRY",
        "shell_flow_replay_bundle": {},
        "task174_result": {},
        "unexpected": "not accepted",
    }
    with pytest.raises(ValidationError):
        task173.Task173Request.model_validate(request)
    del request["unexpected"]
    request["mesh_sequence"] = (1, 3, 4)
    with pytest.raises(ValidationError):
        task173.Task173Request.model_validate(request)


def test_stage2_task172_historical_payload_is_native_not_fixture_authority() -> None:
    payload = _evidence()["shared_native_payload"]
    assert payload["TASK166_native_result"]["result_hash"] == EXPECTED_TASK166_RESULT_HASH
    assert payload["TASK032_native_result"]["result_hash"] == EXPECTED_TASK032_RESULT_HASH
    assert payload["TASK172_native_result"]["result_hash"] == (
        "14feaec9190e5e00be79f638db8e5e572adf83788a628b56b4ba1d9b20036e63"
    )
    assert (
        payload["TASK172_request"]["shell_flow_authority"]["task166_result"]["result_hash"]
        == EXPECTED_TASK166_RESULT_HASH
    )
