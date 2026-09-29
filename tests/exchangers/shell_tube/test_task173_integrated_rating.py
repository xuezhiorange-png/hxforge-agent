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
    Task172LocalRequest,
    build_local_support,
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
