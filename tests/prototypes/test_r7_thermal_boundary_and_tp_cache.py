"""R7: safe TP cache and experimental thermal boundary binding."""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.properties.base import FluidIdentifier, PropertyErrorCode, PropertyServiceError
from hexagent.properties.coolprop_provider import (
    CoolPropProvider,
    _coolprop_configuration_fingerprint,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_tp_cache import (
    install_ephemeral_tp_cache,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
    solve_positive_duty_cell_root,
)
from prototypes.v07_general_rating_sizing_mvp.property_provider_profiling import (
    run_tp_cache_ab_parity,
)

R6_CASE = (
    __import__("pathlib").Path(__file__).resolve().parents[2]
    / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_tube_hot_shell_cold_r6.json"
)
R7_CASE = (
    __import__("pathlib").Path(__file__).resolve().parents[2]
    / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_tube_hot_shell_cold_r7.json"
)
_FEASIBLE_SHELL_LEFT_TEMPERATURE_K = 298.5


def test_tp_cache_configuration_drift_fails_closed() -> None:
    provider = CoolPropProvider()
    install_ephemeral_tp_cache(provider)
    provider.state_tp(FluidIdentifier(name="Water"), 300.0, 101325.0)
    original = _coolprop_configuration_fingerprint

    def drifted_fingerprint() -> str:
        return "drifted-test-fingerprint"

    import hexagent.properties.coolprop_provider as cp_mod

    cp_mod._coolprop_configuration_fingerprint = drifted_fingerprint  # type: ignore[attr-defined]
    try:
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.state_tp(FluidIdentifier(name="Water"), 300.0, 101325.0)
        assert exc_info.value.code == PropertyErrorCode.CONFIGURATION_CHANGED
    finally:
        cp_mod._coolprop_configuration_fingerprint = original  # type: ignore[attr-defined]


def test_tp_cache_ab_parity_on_representative_cell() -> None:
    case = load_general_engineering_case_json(R6_CASE.read_text(encoding="utf-8"))
    sel = enumerate_experimental_rating_candidates(case)
    native = build_native_cell_context(case, selection=sel)
    ab = run_tp_cache_ab_parity(native)
    assert ab["numerical_parity"] is True
    assert ab["task172_request_hash_parity"] is True
    assert ab["cache_stats"]["cache_hits"] > 0


def test_live_tube_inlet_changes_task172_request_hash() -> None:
    case_a = load_general_engineering_case_json(R6_CASE.read_text(encoding="utf-8"))
    case_b = load_general_engineering_case_json(R7_CASE.read_text(encoding="utf-8"))
    sel_a = enumerate_experimental_rating_candidates(case_a)
    sel_b = enumerate_experimental_rating_candidates(case_b)
    native_a = build_native_cell_context(case_a, selection=sel_a)
    native_b = build_native_cell_context(case_b, selection=sel_b)
    root_a = solve_positive_duty_cell_root(
        native_a,
        shell_left_basis="feasible_shell_left_face",
        shell_temperature_k=_FEASIBLE_SHELL_LEFT_TEMPERATURE_K,
        case=case_a,
        enable_live_thermal_boundary=False,
    )
    root_b = solve_positive_duty_cell_root(
        native_b,
        shell_left_basis="feasible_shell_left_face",
        shell_temperature_k=_FEASIBLE_SHELL_LEFT_TEMPERATURE_K,
        case=case_b,
        enable_live_thermal_boundary=True,
    )
    assert root_a["task172_request_hash"] != root_b["task172_request_hash"]
    assert root_a["task172_result_hash"] != root_b["task172_result_hash"]
    assert root_a["q_root_w"] != root_b["q_root_w"]


def test_frozen_reference_path_unchanged_without_binding() -> None:
    assert t173.effective_tube_inlet_temperature_k() == t173.TUBE_INLET_T_K
    provider = CoolPropProvider()
    binding = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=t173.TUBE_INLET_T_K,
        shell_inlet_temperature_k=t173.SHELL_INLET_T_K,
    )
    token = bind_experimental_thermal_boundary_v1(binding)
    try:
        assert t173.effective_tube_inlet_temperature_k() == Decimal("300")
    finally:
        reset_experimental_thermal_boundary(token)
