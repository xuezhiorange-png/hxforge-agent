"""Deep validators for design C: outlet property chain and fixed nozzle override."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    build_r27b_assumption_based_hydraulic_path_input_v1,
    nozzle_flow_area_m2,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    _verify_full_path,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    AutonomousNozzleFullPathReport,
    _fluid_density_kg_m3,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import CandidateRatingBindings
from prototypes.v08_thermal_rating.candidate_c_identity_v08 import (
    CANDIDATE_C_SHELL_NOZZLE_ID_M,
    CANDIDATE_C_TUBE_NOZZLE_ID_M,
)
from prototypes.v08_thermal_rating.full_path_fixed_nozzle_evaluator_v08 import (
    _decimal_velocity_m_s,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import ThermalPrescreenResult
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    build_engineering_case_v2_from_v08,
    candidate_selection_record_from_bindings,
    task174_hydraulic_postpass_from_bindings,
)

ValidatorStatus = Literal["PASS", "BLOCKED", "NOT_EVALUATED"]
_FAIL_DETAIL = tuple[str, ...]


def _component_dp(row: dict[str, Any]) -> Decimal | None:
    if row.get("status") == "BLOCKED":
        return None
    raw = row.get("dp_pa", row.get("pressure_drop_pa"))
    if raw is None:
        return Decimal("0")
    return Decimal(str(raw))


def validate_outlet_property_consistency(
    *,
    bindings: CandidateRatingBindings,
    clean: ThermalPrescreenResult,
    hydraulic: AutonomousNozzleFullPathReport,
    provider: CoolPropProvider,
) -> tuple[ValidatorStatus, _FAIL_DETAIL]:
    failures: list[str] = []
    if clean.predicted_tube_outlet_k is None or clean.predicted_shell_outlet_k is None:
        failures.append("CLEAN_MISSING_PREDICTED_OUTLET_K")
    tube_out_k = Decimal(clean.predicted_tube_outlet_k or "0")
    shell_out_k = Decimal(clean.predicted_shell_outlet_k or "0")
    case = build_engineering_case_v2_from_v08(bindings.normalized)
    tube_p = Decimal(str(case.tube_side.inlet_pressure_pa))
    shell_p = Decimal(str(case.shell_side.inlet_pressure_pa))
    rho_t_out_expected = _fluid_density_kg_m3(
        provider, temperature_k=tube_out_k, pressure_pa=tube_p
    )
    rho_s_out_expected = _fluid_density_kg_m3(
        provider, temperature_k=shell_out_k, pressure_pa=shell_p
    )
    ports = {p.port_id: p for p in hydraulic.ports}
    for port_id, expected_rho in (
        ("TUBE_OUTLET", rho_t_out_expected),
        ("SHELL_OUTLET", rho_s_out_expected),
    ):
        port = ports.get(port_id)
        if port is None:
            failures.append(f"MISSING_PORT:{port_id}")
            continue
        if port.velocity_basis != "INDICATIVE_THERMAL_PRESCREEN_OUTLET":
            failures.append(f"OUTLET_BASIS_NOT_PRESCREEN:{port_id}={port.velocity_basis}")
        delta = abs(port.density_kg_m3 - expected_rho)
        if delta > Decimal("0.01"):
            failures.append(
                f"DENSITY_MISMATCH:{port_id}:port={port.density_kg_m3}:coolprop={expected_rho}"
            )
        area = nozzle_flow_area_m2(port.inside_diameter_m)
        v_replay = _decimal_velocity_m_s(
            mass_flow_kg_s=port.mass_flow_kg_s, rho=port.density_kg_m3, diameter_m=port.inside_diameter_m
        )
        if abs(v_replay - port.velocity_m_s) > Decimal("1e-9"):
            failures.append(f"VELOCITY_REPLAY:{port_id}:decl={port.velocity_m_s}:replay={v_replay}")
        if abs(area - port.effective_area_m2) > Decimal("1e-12"):
            failures.append(f"AREA_MISMATCH:{port_id}")

    record = candidate_selection_record_from_bindings(bindings)
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
    tube_out_state = (tube_out_k, tube_p)
    shell_out_state = (shell_out_k, shell_p)
    path = build_r27b_assumption_based_hydraulic_path_input_v1(
        case=case,
        record=record,
        loss_scenario_key="mid_band",
        tube_nozzle_inside_diameter_m=CANDIDATE_C_TUBE_NOZZLE_ID_M,
        shell_nozzle_inside_diameter_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
        tube_outlet_state_k_pa=tube_out_state,
        shell_outlet_state_k_pa=shell_out_state,
    )
    outlet_tp_ids = (
        "R27B-ASSUMP-TUBE-OUTLET-NOZZLE",
        "R27B-ASSUMP-TUBE-BUNDLE-EXIT",
        "R27B-ASSUMP-SHELL-OUTLET-NOZZLE",
        "R27B-ASSUMP-SHELL-OUTLET-TRANSITION",
    )
    for component in path.tube_side_components + path.shell_external_components:
        if (
            component.component_id in outlet_tp_ids
            and component.fluid_density_source.kind != "COOLPROP_TP"
        ):
            failures.append(
                f"PATH_NOT_COOLPROP_TP:{component.component_id}:{component.fluid_density_source.kind}"
            )

    for key in ("mid_band", "low_loss_sensitivity", "high_loss_sensitivity"):
        fp = _verify_full_path(
            case=case,
            record=record,
            postpass=postpass,
            loss_scenario_key=key,
            tube_nozzle_d_m=CANDIDATE_C_TUBE_NOZZLE_ID_M,
            shell_nozzle_d_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
            tube_outlet_state_k_pa=tube_out_state,
            shell_outlet_state_k_pa=shell_out_state,
        )
        if fp.get("status") != "COMPUTED":
            failures.append(f"FULL_PATH_NOT_COMPUTED:{key}:{fp.get('status')}")
            continue
        tube_total = Decimal(str(fp["TUBE_FULL_PATH_TOTAL_DP_PA"]))
        recon = fp.get("reconciliation") or {}
        if recon.get("tube_full_equals_friction_plus_local") is False:
            failures.append(f"TUBE_RECONCILIATION_FAIL:{key}")
        tube_local = fp.get("TUBE_LOCAL_DP_PA")
        tube_friction = fp.get("TUBE_INTERNAL_FRICTION_DP_PA")
        if tube_local is not None and tube_friction is not None:
            rebuilt = Decimal(str(tube_friction)) + Decimal(str(tube_local))
            if abs(rebuilt - tube_total) > Decimal("0.05"):
                failures.append(
                    f"TUBE_SUM_MISMATCH:{key}:total={tube_total}:friction+local={rebuilt}"
                )
        else:
            tube_parts = Decimal("0")
            for row in fp.get("TUBE_DP_COMPONENTS") or []:
                if isinstance(row, dict):
                    part = _component_dp(row)
                    if part is None:
                        failures.append(f"TUBE_COMPONENT_BLOCKED:{key}:{row.get('component_id')}")
                        tube_parts = Decimal("-1")
                        break
                    tube_parts += part
            if tube_parts >= 0 and tube_friction is not None:
                rebuilt = Decimal(str(tube_friction)) + tube_parts
                if abs(rebuilt - tube_total) > Decimal("0.05"):
                    failures.append(
                        f"TUBE_SUM_MISMATCH:{key}:total={tube_total}:parts={rebuilt}"
                    )
        shell_total = Decimal(str(fp["SHELL_FULL_PATH_TOTAL_DP_PA"]))
        if recon.get("shell_full_equals_bd_plus_external") is False:
            failures.append(f"SHELL_RECONCILIATION_FAIL:{key}")
        shell_bd = Decimal(str(fp["SHELL_BELL_DELAWARE_INTERNAL_DP_PA"] or "0"))
        shell_ext = Decimal(str(fp["SHELL_EXTERNAL_LOCAL_DP_PA"] or "0"))
        if abs(shell_bd + shell_ext - shell_total) > Decimal("0.05"):
            failures.append(
                f"SHELL_SUM_MISMATCH:{key}:total={shell_total}:bd+ext={shell_bd + shell_ext}"
            )
    for port_id in ("TUBE_INLET", "SHELL_INLET"):
        diameters = {
            str(p.inside_diameter_m)
            for p in hydraulic.ports
            if p.port_id == port_id
        }
        if len(diameters) > 1:
            failures.append(f"NOZZLE_DIAMETER_VARIES:{port_id}")
    if not hydraulic.nozzle_same_geometry_all_scenarios:
        failures.append("NOZZLE_GEOMETRY_NOT_SHARED_ACROSS_SCENARIOS")
    for port_id, expected in (
        ("TUBE_INLET", CANDIDATE_C_TUBE_NOZZLE_ID_M),
        ("SHELL_INLET", CANDIDATE_C_SHELL_NOZZLE_ID_M),
    ):
        port = ports.get(port_id)
        if port is None or port.inside_diameter_m != expected:
            failures.append(f"DESIGN_C_NOZZLE_MISMATCH:{port_id}")
    mid_fp = _verify_full_path(
        case=case,
        record=record,
        postpass=postpass,
        loss_scenario_key="mid_band",
        tube_nozzle_d_m=CANDIDATE_C_TUBE_NOZZLE_ID_M,
        shell_nozzle_d_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
        tube_outlet_state_k_pa=tube_out_state,
        shell_outlet_state_k_pa=shell_out_state,
    )
    mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
    if mid.tube_full_path_dp_pa and mid_fp.get("TUBE_FULL_PATH_TOTAL_DP_PA"):
        tube_h = Decimal(mid.tube_full_path_dp_pa)
        tube_fp = Decimal(str(mid_fp["TUBE_FULL_PATH_TOTAL_DP_PA"]))
        if abs(tube_h - tube_fp) > Decimal("0.1"):
            failures.append(f"MID_TUBE_REPORT_VS_FP:{tube_h}:{tube_fp}")

    return ("PASS" if not failures else "BLOCKED"), tuple(failures)


def validate_fixed_nozzle_override_check(
    *,
    bindings: CandidateRatingBindings,
    hydraulic: AutonomousNozzleFullPathReport,
) -> tuple[ValidatorStatus, _FAIL_DETAIL]:
    failures: list[str] = []
    if bindings is None:
        return "BLOCKED", ("BINDINGS_MISSING",)
    for port_id, expected in (
        ("TUBE_INLET", CANDIDATE_C_TUBE_NOZZLE_ID_M),
        ("SHELL_INLET", CANDIDATE_C_SHELL_NOZZLE_ID_M),
    ):
        port = next((p for p in hydraulic.ports if p.port_id == port_id), None)
        if port is None or port.inside_diameter_m != expected:
            actual = port.inside_diameter_m if port else "none"
            failures.append(f"DIAMETER_OVERRIDDEN:{port_id}:expected={expected}:actual={actual}")
    for blocker in hydraulic.remaining_blockers:
        if blocker.startswith("TUBE_NOZZLE_BISECT:") or blocker.startswith("SHELL_NOZZLE_BISECT:"):
            failures.append(f"FALSE_BISECT_BLOCKER:{blocker}")
    for p in hydraulic.ports:
        if p.velocity_m_s < Decimal("1") or p.velocity_m_s > Decimal("3"):
            failures.append(
                f"STRICT_VELOCITY_FAIL:{p.port_id}:v={p.velocity_m_s}"
            )
    for scenario in hydraulic.scenarios:
        if scenario.tube_full_path_dp_pa is None or scenario.shell_full_path_dp_pa is None:
            failures.append(f"INCOMPLETE_SCENARIO:{scenario.scenario_key}")
    if hydraulic.installation.preliminary_geometry_fit not in ("PASS", "BLOCKED"):
        failures.append("INSTALLATION_STATUS_INVALID")
    if hydraulic.installation.nozzle_reinforcement != "UNRESOLVED":
        failures.append("REINFORCEMENT_NOT_UNRESOLVED")
    return ("PASS" if not failures else "BLOCKED"), tuple(failures)


def evaluate_nozzle_only_high_k_feasibility(
    *,
    bindings: CandidateRatingBindings,
    tube_d_max_m: Decimal,
    shell_d_m: Decimal,
    tube_out_k: Decimal,
    shell_out_k: Decimal,
) -> tuple[str, str | None, str | None]:
    """Return INFEASIBLE or FEASIBLE_UNDER_ASSUMED_K with min high tube dp at max tube ID."""
    case = build_engineering_case_v2_from_v08(bindings.normalized)
    record = candidate_selection_record_from_bindings(bindings)
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
    tube_p = Decimal(str(case.tube_side.inlet_pressure_pa))
    shell_p = Decimal(str(case.shell_side.inlet_pressure_pa))
    fp = _verify_full_path(
        case=case,
        record=record,
        postpass=postpass,
        loss_scenario_key="high_loss_sensitivity",
        tube_nozzle_d_m=tube_d_max_m,
        shell_nozzle_d_m=shell_d_m,
        tube_outlet_state_k_pa=(tube_out_k, tube_p),
        shell_outlet_state_k_pa=(shell_out_k, shell_p),
    )
    limit = bindings.normalized.max_tube_side_pressure_drop_pa
    if limit is None:
        return "NOT_EVALUATED", None, None
    high_dp = fp.get("TUBE_FULL_PATH_TOTAL_DP_PA")
    if high_dp is None:
        return "NOT_EVALUATED", None, str(fp.get("status"))
    high_val = Decimal(str(high_dp))
    note = None
    if high_val > limit:
        note = "NOZZLE_ONLY_HIGH_K_FEASIBILITY=INFEASIBLE_UNDER_ASSUMED_K"
        return "INFEASIBLE_UNDER_ASSUMED_K", str(high_val), note
    return "FEASIBLE_UNDER_ASSUMED_K", str(high_val), note


__all__ = [
    "ValidatorStatus",
    "evaluate_nozzle_only_high_k_feasibility",
    "validate_fixed_nozzle_override_check",
    "validate_outlet_property_consistency",
]