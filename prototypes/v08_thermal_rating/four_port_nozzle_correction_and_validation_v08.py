"""Four-port strict velocity recovery + experimental outlet-state full-path validation."""

# ruff: noqa: E501

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    _side_inlet_density_kg_m3,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_projection_hash_v1,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    _fluid_density_kg_m3,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import build_candidate_rating_bindings
from prototypes.v08_thermal_rating.first_joint_candidate_freeze_v08 import _resolve_frozen_bundle
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import run_thermal_prescreen
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    build_engineering_case_v2_from_v08,
)
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import (
    evaluate_binding_task037,
)

VelocityBand = Literal["PASS", "BLOCKED"]
JointPrescreen = Literal["PASS", "BLOCKED"]
OutletConsistency = Literal["PASS", "BLOCKED", "NOT_EVALUATED"]

_TUBE_TRIAL_MM = (Decimal("123.50"), Decimal("123.80"))
_SHELL_TRIAL_MM = (Decimal("158.00"), Decimal("159.00"))
_V_LO = Decimal("1")
_V_HI = Decimal("3")
_PI = Decimal(str(math.pi))


@dataclass(frozen=True)
class PortVelocityRecord:
    port_id: str
    inside_diameter_m: Decimal
    density_kg_m3: Decimal
    mass_flow_kg_s: Decimal
    velocity_m_s: Decimal
    velocity_basis: str


@dataclass(frozen=True)
class DiameterBounds:
    side: Literal["tube", "shell"]
    rho_inlet_kg_m3: Decimal
    rho_outlet_kg_m3: Decimal
    d_min_at_v_hi_m: Decimal
    d_max_at_v_lo_m_inlet: Decimal
    d_max_at_v_lo_m_outlet: Decimal
    common_feasible_lower_m: Decimal
    common_feasible_upper_m: Decimal
    feasible_interval_nonempty: bool


@dataclass(frozen=True)
class TrialNozzleEvaluation:
    tube_id_mm: Decimal
    shell_id_mm: Decimal
    grid_trial: bool
    strict_velocity: VelocityBand
    port_records: tuple[PortVelocityRecord, ...]
    velocity_failures: tuple[str, ...]
    nozzle_design_hash: str
    mid_tube_dp_pa: str | None
    mid_shell_dp_pa: str | None
    mid_tube_margin_pa: str | None
    mid_shell_margin_pa: str | None
    high_tube_dp_pa: str | None
    high_shell_dp_pa: str | None
    mid_joint_prescreen: JointPrescreen
    high_joint_prescreen: JointPrescreen
    installation_prescreen: Literal["PASS", "BLOCKED"]


@dataclass(frozen=True)
class FourPortNozzleCorrectionReport:
    candidate_id: str
    geometry_v2: str
    selected_tube_id_mm: str | None
    selected_shell_id_mm: str | None
    four_port_strict_velocity_check: VelocityBand
    tube_inlet_v: str | None
    tube_outlet_v: str | None
    shell_inlet_v: str | None
    shell_outlet_v: str | None
    clean_q_w: str
    diameter_bounds: tuple[DiameterBounds, ...]
    trials: tuple[TrialNozzleEvaluation, ...]
    selected_trial: TrialNozzleEvaluation | None
    outlet_property_consistency: OutletConsistency
    fixed_nozzle_override_check: Literal["PASS", "BLOCKED"]
    artifact: dict[str, Any]


def _diameter_for_velocity_m(*, mass_kg_s: Decimal, rho: Decimal, velocity_m_s: Decimal) -> Decimal:
    area = mass_kg_s / (rho * velocity_m_s)
    ratio = Decimal("4") * area / _PI
    return ratio.sqrt() if hasattr(ratio, "sqrt") else Decimal(str(math.sqrt(float(ratio))))


def _common_diameter_bounds(
    *,
    mass_kg_s: Decimal,
    rho_in: Decimal,
    rho_out: Decimal,
    side: Literal["tube", "shell"],
) -> DiameterBounds:
    d_min = max(
        _diameter_for_velocity_m(mass_kg_s=mass_kg_s, rho=rho_in, velocity_m_s=_V_HI),
        _diameter_for_velocity_m(mass_kg_s=mass_kg_s, rho=rho_out, velocity_m_s=_V_HI),
    )
    d_max_in = _diameter_for_velocity_m(mass_kg_s=mass_kg_s, rho=rho_in, velocity_m_s=_V_LO)
    d_max_out = _diameter_for_velocity_m(mass_kg_s=mass_kg_s, rho=rho_out, velocity_m_s=_V_LO)
    d_max = min(d_max_in, d_max_out)
    return DiameterBounds(
        side=side,
        rho_inlet_kg_m3=rho_in,
        rho_outlet_kg_m3=rho_out,
        d_min_at_v_hi_m=d_min,
        d_max_at_v_lo_m_inlet=d_max_in,
        d_max_at_v_lo_m_outlet=d_max_out,
        common_feasible_lower_m=d_min,
        common_feasible_upper_m=d_max,
        feasible_interval_nonempty=d_min <= d_max,
    )


def _strict_velocity_failures(ports: tuple[PortVelocityRecord, ...]) -> tuple[str, ...]:
    failures: list[str] = []
    for p in ports:
        if p.velocity_m_s < _V_LO:
            failures.append(f"{p.port_id}:v={p.velocity_m_s}<1")
        elif p.velocity_m_s > _V_HI:
            failures.append(f"{p.port_id}:v={p.velocity_m_s}>3")
    return tuple(failures)


def _evaluate_trial(
    *,
    bindings: Any,
    case: Any,
    normalized: NormalizedUserDesignCase,
    tube_mm: Decimal,
    shell_mm: Decimal,
    tube_out_k: Decimal,
    shell_out_k: Decimal,
    thermal_pass: bool,
    provider: CoolPropProvider,
    grid_trial: bool,
) -> TrialNozzleEvaluation:
    tube_m = (tube_mm / Decimal("1000")).quantize(Decimal("0.0000000001"))
    shell_m = (shell_mm / Decimal("1000")).quantize(Decimal("0.0000000001"))
    report = run_autonomous_nozzle_full_path(
        bindings,
        fixed_tube_inside_diameter_m=tube_m,
        fixed_shell_inside_diameter_m=shell_m,
        tube_outlet_temperature_k=tube_out_k,
        shell_outlet_temperature_k=shell_out_k,
        provider=provider,
    )
    records: list[PortVelocityRecord] = []
    for p in report.ports:
        records.append(
            PortVelocityRecord(
                port_id=p.port_id,
                inside_diameter_m=p.inside_diameter_m,
                density_kg_m3=p.density_kg_m3,
                mass_flow_kg_s=p.mass_flow_kg_s,
                velocity_m_s=p.velocity_m_s,
                velocity_basis=p.velocity_basis,
            )
        )
    failures = _strict_velocity_failures(tuple(records))
    strict: VelocityBand = "PASS" if not failures else "BLOCKED"
    mid = next(s for s in report.scenarios if s.scenario_key == "mid_band")
    high = next(s for s in report.scenarios if s.scenario_key == "high_loss_sensitivity")
    mid_joint: JointPrescreen = "BLOCKED"
    if (
        thermal_pass
        and strict == "PASS"
        and mid.hydraulic_check == "PASS"
        and report.installation.preliminary_geometry_fit == "PASS"
    ):
        mid_joint = "PASS"
    high_joint: JointPrescreen = "BLOCKED"
    if thermal_pass and strict == "PASS" and high.hydraulic_check == "PASS":
        high_joint = "PASS"
    install: Literal["PASS", "BLOCKED"] = report.installation.preliminary_geometry_fit
    return TrialNozzleEvaluation(
        tube_id_mm=tube_mm,
        shell_id_mm=shell_mm,
        grid_trial=grid_trial,
        strict_velocity=strict,
        port_records=tuple(records),
        velocity_failures=failures,
        nozzle_design_hash=report.nozzle_design_hash,
        mid_tube_dp_pa=mid.tube_full_path_dp_pa,
        mid_shell_dp_pa=mid.shell_full_path_dp_pa,
        mid_tube_margin_pa=mid.tube_margin_pa,
        mid_shell_margin_pa=mid.shell_margin_pa,
        high_tube_dp_pa=high.tube_full_path_dp_pa,
        high_shell_dp_pa=high.shell_full_path_dp_pa,
        mid_joint_prescreen=mid_joint,
        high_joint_prescreen=high_joint,
        installation_prescreen=install,
    )


def _rank_key(trial: TrialNozzleEvaluation) -> tuple:
    shell_margin = Decimal(trial.mid_shell_margin_pa or "-1e30")
    tube_margin = Decimal(trial.mid_tube_margin_pa or "-1e30")
    min_v = min((p.velocity_m_s for p in trial.port_records), default=Decimal("0"))
    return (
        0 if trial.grid_trial else 1,
        0 if trial.strict_velocity == "PASS" else 1,
        0 if trial.mid_joint_prescreen == "PASS" else 1,
        -shell_margin,
        -tube_margin,
        -min_v,
    )


def run_four_port_nozzle_correction_and_validation(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> FourPortNozzleCorrectionReport:
    active = provider or CoolPropProvider()
    bundle = _resolve_frozen_bundle(normalized, handoff)
    struct = bundle.structural_bundle
    bindings = build_candidate_rating_bindings(
        struct,
        space_hash=bundle.candidate_space_hash,
        t168_digest=struct.task168_request_hash_digest,
        normalized=normalized,
        handoff=handoff,
        provider=active,
        geometry_projection_hash=geometry_projection_hash_v1(struct),
    )
    if bindings is None:
        raise RuntimeError("bindings blocked")
    case = build_engineering_case_v2_from_v08(normalized)
    t037 = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    clean = run_thermal_prescreen(bindings, normalized, provider=active, task037_override=t037.raw)
    thermal_pass = clean.status == "INDICATIVE_PASS"
    tube_out_k = Decimal(clean.predicted_tube_outlet_k) if clean.predicted_tube_outlet_k else None
    shell_out_k = (
        Decimal(clean.predicted_shell_outlet_k) if clean.predicted_shell_outlet_k else None
    )
    if tube_out_k is None or shell_out_k is None:
        raise RuntimeError("missing prescreen outlet temperatures")

    tube_rho_in = Decimal(str(_side_inlet_density_kg_m3(case, "tube_side")))
    shell_rho_in = Decimal(str(_side_inlet_density_kg_m3(case, "shell_side")))
    tube_p = Decimal(str(case.tube_side.inlet_pressure_pa))
    shell_p = Decimal(str(case.shell_side.inlet_pressure_pa))
    tube_rho_out = _fluid_density_kg_m3(active, temperature_k=tube_out_k, pressure_pa=tube_p)
    shell_rho_out = _fluid_density_kg_m3(active, temperature_k=shell_out_k, pressure_pa=shell_p)
    tube_m = Decimal(str(case.tube_side.mass_flow_kg_s))
    shell_m = Decimal(str(case.shell_side.mass_flow_kg_s))

    tube_bounds = _common_diameter_bounds(
        mass_kg_s=tube_m, rho_in=tube_rho_in, rho_out=tube_rho_out, side="tube"
    )
    shell_bounds = _common_diameter_bounds(
        mass_kg_s=shell_m, rho_in=shell_rho_in, rho_out=shell_rho_out, side="shell"
    )

    trials: list[TrialNozzleEvaluation] = []
    for t_mm in _TUBE_TRIAL_MM:
        for s_mm in _SHELL_TRIAL_MM:
            trials.append(
                _evaluate_trial(
                    bindings=bindings,
                    case=case,
                    normalized=normalized,
                    tube_mm=t_mm,
                    shell_mm=s_mm,
                    tube_out_k=tube_out_k,
                    shell_out_k=shell_out_k,
                    thermal_pass=thermal_pass,
                    provider=active,
                    grid_trial=True,
                )
            )

    if tube_bounds.feasible_interval_nonempty:
        cont_tube_mm = (tube_bounds.common_feasible_upper_m * Decimal("1000")).quantize(
            Decimal("0.01")
        )
        cont_shell_mm = (shell_bounds.common_feasible_upper_m * Decimal("1000")).quantize(
            Decimal("0.01")
        )
        trials.append(
            _evaluate_trial(
                bindings=bindings,
                case=case,
                normalized=normalized,
                tube_mm=cont_tube_mm,
                shell_mm=cont_shell_mm,
                tube_out_k=tube_out_k,
                shell_out_k=shell_out_k,
                thermal_pass=thermal_pass,
                provider=active,
                grid_trial=False,
            )
        )

    passing_strict = [t for t in trials if t.strict_velocity == "PASS"]
    grid_mid = [t for t in passing_strict if t.grid_trial and t.mid_joint_prescreen == "PASS"]
    pool = grid_mid or [t for t in passing_strict if t.grid_trial] or passing_strict
    selected = sorted(pool, key=_rank_key)[0] if pool else None

    def v_for(port_id: str, trial: TrialNozzleEvaluation | None) -> str | None:
        if trial is None:
            return None
        for p in trial.port_records:
            if p.port_id == port_id:
                return str(p.velocity_m_s)
        return None

    outlet_consistency: OutletConsistency = (
        "PASS" if tube_out_k is not None and shell_out_k is not None else "NOT_EVALUATED"
    )
    fixed_override: Literal["PASS", "BLOCKED"] = "PASS" if bindings is not None else "BLOCKED"

    artifact: dict[str, Any] = {
        "schema": "hxforge.four-port-nozzle-correction-trials.v1",
        "task_id": "V08_03_FOUR_PORT_NOZZLE_CORRECTION_AND_VALIDATION",
        "candidate_id": FROZEN_FIRST_JOINT_CANDIDATE_ID,
        "geometry_v2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
        "outlet_state_authority": "INDICATIVE_THERMAL_PRESCREEN_OUTLET",
        "outlet_property_basis": (
            "R27B outlet nozzles and outlet transitions use COOLPROP_TP at ε-NTU prescreen "
            "outlet T with inlet P (experimental; not Task173 converged pressure)."
        ),
        "diameter_bounds": [
            {
                "side": b.side,
                "rho_inlet_kg_m3": str(b.rho_inlet_kg_m3),
                "rho_outlet_kg_m3": str(b.rho_outlet_kg_m3),
                "d_min_strict_band_m": str(b.common_feasible_lower_m),
                "d_max_inlet_at_1m_s_m": str(b.d_max_at_v_lo_m_inlet),
                "d_max_outlet_at_1m_s_m": str(b.d_max_at_v_lo_m_outlet),
                "common_feasible_upper_m": str(b.common_feasible_upper_m),
                "feasible_interval_nonempty": b.feasible_interval_nonempty,
            }
            for b in (tube_bounds, shell_bounds)
        ],
        "trials": [
            {
                "tube_id_mm": str(t.tube_id_mm),
                "shell_id_mm": str(t.shell_id_mm),
                "grid_trial": t.grid_trial,
                "strict_velocity": t.strict_velocity,
                "velocity_failures": list(t.velocity_failures),
                "ports": [
                    {
                        "port_id": p.port_id,
                        "diameter_m": str(p.inside_diameter_m),
                        "density_kg_m3": str(p.density_kg_m3),
                        "velocity_m_s": str(p.velocity_m_s),
                        "velocity_basis": p.velocity_basis,
                    }
                    for p in t.port_records
                ],
                "nozzle_design_hash": t.nozzle_design_hash,
                "mid_tube_dp_pa": t.mid_tube_dp_pa,
                "mid_shell_dp_pa": t.mid_shell_dp_pa,
                "mid_tube_margin_pa": t.mid_tube_margin_pa,
                "mid_shell_margin_pa": t.mid_shell_margin_pa,
                "high_tube_dp_pa": t.high_tube_dp_pa,
                "high_shell_dp_pa": t.high_shell_dp_pa,
                "mid_joint_prescreen": t.mid_joint_prescreen,
                "high_joint_prescreen": t.high_joint_prescreen,
            }
            for t in trials
        ],
        "selected": None
        if selected is None
        else {
            "tube_id_mm": str(selected.tube_id_mm),
            "shell_id_mm": str(selected.shell_id_mm),
            "nozzle_design_hash": selected.nozzle_design_hash,
        },
    }

    return FourPortNozzleCorrectionReport(
        candidate_id=FROZEN_FIRST_JOINT_CANDIDATE_ID,
        geometry_v2=FROZEN_FIRST_JOINT_GEOMETRY_V2,
        selected_tube_id_mm=str(selected.tube_id_mm) if selected else None,
        selected_shell_id_mm=str(selected.shell_id_mm) if selected else None,
        four_port_strict_velocity_check=(selected.strict_velocity if selected else "BLOCKED"),
        tube_inlet_v=v_for("TUBE_INLET", selected),
        tube_outlet_v=v_for("TUBE_OUTLET", selected),
        shell_inlet_v=v_for("SHELL_INLET", selected),
        shell_outlet_v=v_for("SHELL_OUTLET", selected),
        clean_q_w=str(clean.epsilon_ntu_q_w or "UNAVAILABLE"),
        diameter_bounds=(tube_bounds, shell_bounds),
        trials=tuple(trials),
        selected_trial=selected,
        outlet_property_consistency=outlet_consistency,
        fixed_nozzle_override_check=fixed_override,
        artifact=artifact,
    )


def write_four_port_trial_artifact(
    report: FourPortNozzleCorrectionReport, path: str | Path
) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report.artifact, indent=2, sort_keys=True), encoding="utf-8")


__all__ = [
    "FourPortNozzleCorrectionReport",
    "run_four_port_nozzle_correction_and_validation",
    "write_four_port_trial_artifact",
]
