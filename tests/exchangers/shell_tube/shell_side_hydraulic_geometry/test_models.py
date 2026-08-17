from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.models import (
    BLOCKER_CODES,
    DEFERRED_CAPABILITIES,
    WARNING_CODES,
    BlockerCode,
    WarningCode,
)


def test_closed_blocker_taxonomy_count() -> None:
    assert len(BlockerCode) == 36
    assert len(BLOCKER_CODES) == 36
    assert frozenset(item.value for item in BlockerCode) == BLOCKER_CODES


def test_closed_warning_taxonomy_count() -> None:
    assert len(WarningCode) == 7
    assert len(WARNING_CODES) == 7
    assert frozenset(item.value for item in WarningCode) == WARNING_CODES


def test_deferred_capabilities_count_and_order() -> None:
    assert len(DEFERRED_CAPABILITIES) == 17
    assert DEFERRED_CAPABILITIES == (
        "WINDOW_FLOW_AREA_NOT_COMPUTABLE",
        "PER_COMPARTMENT_CROSSFLOW_AREA_SET_NOT_COMPUTABLE",
        "MINIMUM_ADMITTED_FLOW_AREA_NOT_COMPUTABLE",
        "INLET_REGION_FLOW_AREA_NOT_COMPUTABLE",
        "OUTLET_REGION_FLOW_AREA_NOT_COMPUTABLE",
        "LEAKAGE_FLOW_AREA_NOT_COMPUTABLE",
        "BYPASS_FLOW_AREA_NOT_COMPUTABLE",
        "SHELL_SIDE_FLOW_STATE_NOT_COMPUTABLE",
        "SHELL_SIDE_HEAT_TRANSFER_SCREENING_NOT_COMPUTABLE",
        "SHELL_SIDE_PRESSURE_DROP_SCREENING_NOT_COMPUTABLE",
        "BELL_DELAWARE_NOT_COMPUTABLE",
        "OVERALL_U_NOT_COMPUTABLE",
        "UA_NOT_COMPUTABLE",
        "LMTD_NOT_COMPUTABLE",
        "HEAT_DUTY_NOT_COMPUTABLE",
        "OUTLET_TEMPERATURES_NOT_COMPUTABLE",
        "FULL_EXCHANGER_RATING_NOT_COMPUTABLE",
    )
