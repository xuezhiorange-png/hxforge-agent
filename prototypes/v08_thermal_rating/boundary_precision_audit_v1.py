"""Terminal precision plateau audit near outer shooting root (EXPERIMENTAL_NOT_APPROVED)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    _binary64_enthalpy_step_toward,
    _candidate_context,
    _CellSearchStats,
    _MeshRun,
    _outer_trial,
    _terminal_tolerance_pass,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_inlet_temperature_k,
)
from hexagent.properties.base import PropertyProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    solve_isolated_outer_boundary,
)


@dataclass(frozen=True)
class ShootingProbeRow:
    shooting_enthalpy_j_kg: str
    float64_hex: str
    classification: str
    terminal_residual_k: str | None
    terminal_residual_j_kg: str | None
    terminal_tolerance_pass: bool
    total_duty_w: str | None
    local_task172_result_hashes: tuple[str, ...]


@dataclass(frozen=True)
class TpPhRoundtripAudit:
    t_tp_k: str
    p_pa: str
    h_tp_j_kg: str
    t_ph_k: str
    h_ph_j_kg: str
    delta_t_k: str
    delta_h_j_kg: str
    h_inlet_bound_j_kg: str
    h_last_face_minus_h_inlet_j_kg: str | None


@dataclass(frozen=True)
class BoundaryPrecisionAudit:
    candidate_id: str
    geometry_projection_hash: str
    outer_status: str
    outer_bracket_low_endpoint_j_kg: str | None
    outer_bracket_high_endpoint_j_kg: str | None
    outer_bracket_low_hex: str | None
    outer_bracket_high_hex: str | None
    supplementary_valid_trial_probes: tuple[ShootingProbeRow, ...]
    tp_ph_roundtrip: TpPhRoundtripAudit | None
    cumulative_enthalpy_audit: tuple[str, ...]
    terminal_precision_recovered: bool
    first_numerical_blocker: str
    minimal_architecture_recommendation: str | None
    task172_identity_hashes_on_accepted: tuple[str, ...]


def _probe_at_h(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int,
    enthalpy: Decimal,
) -> ShootingProbeRow:
    exp = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=bindings.normalized.tube_side.inlet_temperature_k,
        shell_inlet_temperature_k=bindings.normalized.shell_side.inlet_temperature_k,
        tube_mass_flow_kg_s=bindings.normalized.tube_side.mass_flow_kg_s,
        shell_mass_flow_kg_s=bindings.normalized.shell_side.mass_flow_kg_s,
        tube_property_evaluation_pressure_pa=bindings.normalized.tube_side.inlet_pressure_pa,
        shell_property_evaluation_pressure_pa=bindings.normalized.shell_side.inlet_pressure_pa,
        allow_live_variable_tube_mass_flow=True,
        allow_live_variable_shell_mass_flow=True,
        allow_variable_water_temperature=True,
    )
    btoken = bind_experimental_thermal_boundary_v1(exp)
    context = _candidate_context(bindings.rating_request)
    ctx_token = _CANDIDATE_RATING_CONTEXT.set(context)
    stats = _CellSearchStats()
    try:
        trial = _outer_trial(
            subdivisions,
            enthalpy,
            provider,
            context.shell_authority,
            0,
            stats,
        )
        run = trial.mesh_run
        obs = run.observables if run is not None else None
        hashes: tuple[str, ...] = ()
        if run is not None and run.observables.local_task172_result_hashes:
            hashes = tuple(str(h) for h in run.observables.local_task172_result_hashes)
        return ShootingProbeRow(
            shooting_enthalpy_j_kg=str(enthalpy),
            float64_hex=float(enthalpy).hex(),
            classification=trial.classification,
            terminal_residual_k=str(obs.terminal_boundary_residual_k) if obs else None,
            terminal_residual_j_kg=str(obs.terminal_boundary_residual_j_kg) if obs else None,
            terminal_tolerance_pass=_terminal_tolerance_pass(run) if run is not None else False,
            total_duty_w=str(obs.total_duty_w) if obs else None,
            local_task172_result_hashes=hashes,
        )
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ctx_token)
        reset_experimental_thermal_boundary(btoken)


def _shell_inlet_tp_ph_roundtrip(
    provider: PropertyProvider, bindings: CandidateRatingBindings
) -> TpPhRoundtripAudit | None:
    """TP(T_in,P)->H_TP then PH(P,H_TP)->(T_PH,H_PH); compare to bound inlet enthalpy."""
    t_tp = effective_shell_inlet_temperature_k()
    p_pa = bindings.normalized.shell_side.inlet_pressure_pa
    h_inlet = effective_shell_cold_inlet_enthalpy_j_kg()
    exp = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=bindings.normalized.tube_side.inlet_temperature_k,
        shell_inlet_temperature_k=bindings.normalized.shell_side.inlet_temperature_k,
        tube_mass_flow_kg_s=bindings.normalized.tube_side.mass_flow_kg_s,
        shell_mass_flow_kg_s=bindings.normalized.shell_side.mass_flow_kg_s,
        tube_property_evaluation_pressure_pa=bindings.normalized.tube_side.inlet_pressure_pa,
        shell_property_evaluation_pressure_pa=p_pa,
        allow_live_variable_tube_mass_flow=True,
        allow_live_variable_shell_mass_flow=True,
        allow_variable_water_temperature=True,
    )
    token = bind_experimental_thermal_boundary_v1(exp)
    try:
        shell_fluid = bindings.normalized.shell_side.fluid
        ref = provider.reference_state_policy()
        tp_state = provider.state_tp(shell_fluid, float(t_tp), float(p_pa))
        h_tp = Decimal(str(tp_state.enthalpy_j_kg))
        ph_state = provider.state_ph(shell_fluid, float(p_pa), float(h_tp), reference_state=ref)
        t_ph = Decimal(str(ph_state.temperature_k))
        h_ph = Decimal(str(ph_state.enthalpy_j_kg))
        return TpPhRoundtripAudit(
            t_tp_k=str(t_tp),
            p_pa=str(p_pa),
            h_tp_j_kg=str(h_tp),
            t_ph_k=str(t_ph),
            h_ph_j_kg=str(h_ph),
            delta_t_k=str(t_ph - t_tp),
            delta_h_j_kg=str(h_ph - h_tp),
            h_inlet_bound_j_kg=str(h_inlet),
            h_last_face_minus_h_inlet_j_kg=None,
        )
    except Exception:
        return None
    finally:
        reset_experimental_thermal_boundary(token)


def _last_two_valid_shooting_hs(result: Any) -> tuple[Decimal, Decimal] | None:
    highs: list[Decimal] = []
    for step in result.search_trace:
        if step.classification != "VALID_TRAJECTORY":
            continue
        if step.decision_update in {
            "UPDATE_H_HIGH",
            "UPDATE_H_HIGH_BINARY64_STEP",
            "INITIAL_HIGH_ENDPOINT",
            "ACCEPTED_TERMINAL",
            "ACCEPTED_AFTER_ITERATION_BUDGET",
        }:
            highs.append(Decimal(step.h_trial))
    if len(highs) >= 2:
        return highs[-2], highs[-1]
    return None


def run_boundary_precision_audit(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int = 1,
) -> BoundaryPrecisionAudit:
    """Audit outer bracket endpoints and terminal plateau without tolerance overrides."""
    solved = solve_isolated_outer_boundary(bindings, provider, subdivisions=subdivisions)
    pair = _last_two_valid_shooting_hs(solved)
    probes: list[ShootingProbeRow] = []
    if pair is not None:
        h_lo, h_hi = pair
        probes.append(_probe_at_h(bindings, provider, subdivisions=subdivisions, enthalpy=h_lo))
        probes.append(_probe_at_h(bindings, provider, subdivisions=subdivisions, enthalpy=h_hi))
        stepped = _binary64_enthalpy_step_toward(h_hi, h_lo)
        if stepped is not None:
            probes.append(
                _probe_at_h(bindings, provider, subdivisions=subdivisions, enthalpy=stepped)
            )

    tp_ph = _shell_inlet_tp_ph_roundtrip(provider, bindings)

    accepted = solved.accepted_run
    recovered = (
        solved.status == "ACCEPTED" and accepted is not None and _terminal_tolerance_pass(accepted)
    )
    blocker = "NONE"
    if not recovered:
        if accepted is None:
            br = solved.best_valid_run
            if br is not None and not _terminal_tolerance_pass(br):
                blocker = "TERMINAL_ENTHALPY_OR_TEMPERATURE_RESIDUAL_PLATEAU"
            else:
                blocker = solved.failure_code or solved.status
        else:
            blocker = "OUTER_NOT_ACCEPTED"

    run_for_face: _MeshRun | None = accepted or solved.best_valid_run
    if tp_ph is not None and run_for_face is not None and solved.shooting_enthalpy_j_kg:
        h_face = Decimal(solved.shooting_enthalpy_j_kg)
        h_in = Decimal(tp_ph.h_inlet_bound_j_kg)
        tp_ph = TpPhRoundtripAudit(
            t_tp_k=tp_ph.t_tp_k,
            p_pa=tp_ph.p_pa,
            h_tp_j_kg=tp_ph.h_tp_j_kg,
            t_ph_k=tp_ph.t_ph_k,
            h_ph_j_kg=tp_ph.h_ph_j_kg,
            delta_t_k=tp_ph.delta_t_k,
            delta_h_j_kg=tp_ph.delta_h_j_kg,
            h_inlet_bound_j_kg=tp_ph.h_inlet_bound_j_kg,
            h_last_face_minus_h_inlet_j_kg=str(h_face - h_in),
        )

    arch: str | None = None
    if blocker == "TERMINAL_ENTHALPY_OR_TEMPERATURE_RESIDUAL_PLATEAU":
        arch = (
            "Store outer shooting enthalpy and shell-face coupling in a single Decimal lane "
            "with explicit TP→PH property replay at shell face 0 before each outer trial; "
            "keep production TERMINAL_TOLERANCE_K and _terminal_tolerance_pass unchanged."
        )

    t172_hashes: tuple[str, ...] = ()
    if accepted is not None and accepted.observables.local_task172_result_hashes:
        t172_hashes = tuple(str(h) for h in accepted.observables.local_task172_result_hashes)

    cum: list[str] = []
    if run_for_face is not None:
        obs = run_for_face.observables
        cum.append(f"total_duty_w={obs.total_duty_w}")
        cum.append(f"hot_loss_w={obs.hot_energy_loss_w}")
        cum.append(f"cold_gain_w={obs.cold_energy_gain_w}")
        cum.append(f"energy_balance_residual_w={obs.energy_balance_residual_w}")
        cum.append(f"terminal_residual_k={obs.terminal_boundary_residual_k}")
        cum.append(f"terminal_residual_j_kg={obs.terminal_boundary_residual_j_kg}")

    return BoundaryPrecisionAudit(
        candidate_id=bindings.rating_request.candidate_id,
        geometry_projection_hash=bindings.geometry_projection_hash,
        outer_status=solved.status,
        outer_bracket_low_endpoint_j_kg=solved.h_low_final,
        outer_bracket_high_endpoint_j_kg=solved.h_high_final,
        outer_bracket_low_hex=solved.float_h_low_hex,
        outer_bracket_high_hex=solved.float_h_high_hex,
        supplementary_valid_trial_probes=tuple(probes[:3]),
        tp_ph_roundtrip=tp_ph,
        cumulative_enthalpy_audit=tuple(cum),
        terminal_precision_recovered=recovered,
        first_numerical_blocker=blocker,
        minimal_architecture_recommendation=arch,
        task172_identity_hashes_on_accepted=t172_hashes,
    )


__all__ = ["BoundaryPrecisionAudit", "TpPhRoundtripAudit", "run_boundary_precision_audit"]
