"""Fail-closed TASK174 orchestration tests; no hydraulic total is fabricated."""

from decimal import Decimal, localcontext

from hexagent.exchangers.shell_tube.bell_delaware.decimal_math import engineering_context
from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    BellEventRegionAllocation,
    Task174BlockedResult,
    Task174CaseRequest,
    Task174NativeOutputs,
    recompute_task174_result_hash,
    validate_request,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration.service import (
    _native_bell_region_reconciliation_valid,
)


def test_task174_returns_one_consolidated_fail_closed_authority_disposition() -> None:
    result = validate_request(Task174CaseRequest(), Task174NativeOutputs(None, None, None))

    assert type(result) is Task174BlockedResult
    assert result.status == "BLOCKED"
    assert result.tube_pressure_drop_status == "BLOCKED_INCOMPLETE_MODELED_BOUNDARY"
    assert result.shell_pressure_drop_status == "BLOCKED_INCOMPLETE_PHYSICAL_EVENT_AGGREGATION"
    assert result.bell_aggregation_status == "BLOCKED_EVENT_TO_REGION_MAPPING"
    assert {item.scope for item in result.blockers} == {
        "TUBE_SIDE_TASK029_PATH",
        "SHELL_SIDE_TASK166_BELL_AGGREGATION",
        "CASE_PRESSURE_PATH",
    }
    assert result.fiv_status == "WARN_MISSING_NUMERIC_LIMIT"
    assert result.fiv_numeric_limit_not_guessed is True
    assert result.result_id == f"urn:hxforge:task174:{result.result_hash}"
    assert recompute_task174_result_hash(result) == result.result_hash


def test_task174_bell_allocation_is_role_based_not_per_event_pressure() -> None:
    from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import models
    from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration.service import (
        _BELL_ALLOCATION_BY_EVENT_ROLE,
    )

    assert len(_BELL_ALLOCATION_BY_EVENT_ROLE) == 8
    assert _BELL_ALLOCATION_BY_EVENT_ROLE["CENTRAL_CROSSFLOW"] == (
        "ADDITIVE_PRESSURE_REGION",
        "BELL_CENTRAL_CROSSFLOW_REGION",
    )
    assert _BELL_ALLOCATION_BY_EVENT_ROLE["LEAKAGE_GEOMETRY"] == (
        "CORRECTION_OR_GEOMETRY_SUPPORT",
        "RL_LEAKAGE_CORRECTION_SUPPORT",
    )
    allocation = BellEventRegionAllocation(
        physical_event_id="event-1",
        allocation_role="CORRECTION_OR_GEOMETRY_SUPPORT",
        bell_region_or_support_role="RB_BYPASS_CORRECTION_SUPPORT",
        task166_result_hash="a" * 64,
        evidence_refs=("docs/tasks/evidence/task171.json",),
    )
    assert not hasattr(allocation, "modeled_pressure_drop_pa")
    assert "BellEventPressureBinding" not in models.__all__


def test_task174_task034_is_optional_not_the_authoritative_shell_total() -> None:
    from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
        Task174SuccessResult,
    )

    assert Task174SuccessResult.model_fields["task034_screening_result_id"].is_required() is False
    assert Task174SuccessResult.model_fields["task034_screening_result_hash"].is_required() is False
    assert (
        Task174SuccessResult.model_fields["kern_screening_pressure_drop_pa"].is_required() is False
    )
    assert "bell_total_shell_pressure_drop_pa" in Task174SuccessResult.model_fields


def test_task174_blocked_replay_is_deterministic_for_same_request_and_inputs() -> None:
    request = Task174CaseRequest()
    first = validate_request(request, Task174NativeOutputs(None, None, None))
    second = validate_request(request, Task174NativeOutputs(None, None, None))

    assert type(first) is Task174BlockedResult
    assert type(second) is Task174BlockedResult
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_task174_rejects_out_of_domain_pressure_without_clamping() -> None:
    raw = Task174CaseRequest().model_dump(mode="python")
    raw["pressure_property_bindings"] = (
        {
            "location_id": "tube-cell-0",
            "side": "TUBE",
            "pressure_pa": 99999,
            "property_snapshot_hash": "0" * 64,
        },
    )
    result = validate_request(raw, Task174NativeOutputs(None, None, None))
    assert type(result) is Task174BlockedResult
    assert result.blockers[0].code == "INVALID_TASK174_REQUEST_SCHEMA"


def test_task174_fiv_diagnostic_mode_does_not_require_a_guessed_numeric_limit() -> None:
    result = validate_request({}, Task174NativeOutputs(None, None, None))
    assert type(result) is Task174BlockedResult
    assert result.fiv_numeric_limit_authority_missing is True
    assert result.fiv_numeric_limit_not_guessed is True
    assert result.warnings == (
        "FIV is diagnostic-only; no numeric critical-velocity limit was guessed",
    )


def _h1_bell_result() -> Task166Result:
    central = Decimal("27.612207774183460206836230814703264766375478974330")
    window = Decimal("630.07134795775369108954073760345441625294093406455")
    inlet = Decimal("14.727938435732309429703959554309365007532140748327")
    outlet = Decimal("14.727938435732309429703959554309365007532140748327")
    with localcontext(engineering_context()):
        end_zone = inlet + outlet
        native_total = central + window + end_zone
        legacy_flat_total = central + window + inlet + outlet
    assert legacy_flat_total - native_total == Decimal("1E-47")
    return Task166Result(
        central_crossflow_contribution=central,
        window_contribution=window,
        entrance_zone_contribution=inlet,
        exit_zone_contribution=outlet,
        end_zone_pressure_drop=end_zone,
        total_shell_pressure_drop=native_total,
    )


def test_task174_h1_grouped_reconciliation_matches_native_task166_reduction() -> None:
    assert _native_bell_region_reconciliation_valid(_h1_bell_result()) is True


def test_task174_blocks_a_tampered_native_end_zone_split() -> None:
    result = _h1_bell_result()
    with localcontext(engineering_context()):
        tampered = Task166Result(
            central_crossflow_contribution=result.central_crossflow_contribution,
            window_contribution=result.window_contribution,
            entrance_zone_contribution=result.entrance_zone_contribution,
            exit_zone_contribution=result.exit_zone_contribution,
            end_zone_pressure_drop=result.end_zone_pressure_drop + Decimal("1E-30"),
            total_shell_pressure_drop=result.total_shell_pressure_drop,
        )
    assert _native_bell_region_reconciliation_valid(tampered) is False


def test_task174_blocks_a_tampered_native_total() -> None:
    result = _h1_bell_result()
    with localcontext(engineering_context()):
        tampered = Task166Result(
            central_crossflow_contribution=result.central_crossflow_contribution,
            window_contribution=result.window_contribution,
            entrance_zone_contribution=result.entrance_zone_contribution,
            exit_zone_contribution=result.exit_zone_contribution,
            end_zone_pressure_drop=result.end_zone_pressure_drop,
            total_shell_pressure_drop=result.total_shell_pressure_drop + Decimal("1E-30"),
        )
    assert _native_bell_region_reconciliation_valid(tampered) is False


def test_task174_grouped_reconciliation_ignores_hostile_ambient_decimal_context() -> None:
    valid = _h1_bell_result()
    split_blocked = Task166Result(
        central_crossflow_contribution=valid.central_crossflow_contribution,
        window_contribution=valid.window_contribution,
        entrance_zone_contribution=valid.entrance_zone_contribution,
        exit_zone_contribution=valid.exit_zone_contribution,
        end_zone_pressure_drop=valid.end_zone_pressure_drop + Decimal("1E-30"),
        total_shell_pressure_drop=valid.total_shell_pressure_drop,
    )
    with localcontext() as hostile:
        hostile.prec = 6
        assert _native_bell_region_reconciliation_valid(valid) is True
        assert _native_bell_region_reconciliation_valid(split_blocked) is False
