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
class BoundaryPrecisionAudit:
    candidate_id: str
    geometry_projection_hash: str
    outer_status: str
    h_low_final: str | None
    h_high_final: str | None
    float_h_low_hex: str | None
    float_h_high_hex: str | None
    shell_inlet_temperature_k: str
    shell_cold_inlet_enthalpy_j_kg: str
    shell_inlet_tp_enthalpy_j_kg: str | None
    shell_inlet_ph_rebuild_delta_j_kg: str | None
    last_two_valid_probes: tuple[ShootingProbeRow, ...]
    cumulative_enthalpy_audit: tuple[str, ...]
    terminal_precision_recovered: bool
    first_numerical_blocker: str
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


def _shell_inlet_ph_delta(
    provider: PropertyProvider, bindings: CandidateRatingBindings
) -> tuple[str | None, str | None]:
    """Compare bound cold-inlet enthalpy against provider PH rebuild at inlet T/P."""
    bound_h = effective_shell_cold_inlet_enthalpy_j_kg()
    t_in = effective_shell_inlet_temperature_k()
    p_pa = bindings.normalized.shell_side.inlet_pressure_pa
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
        state = provider.state_tp(shell_fluid, float(t_in), float(p_pa))
        ph_h = Decimal(str(state.enthalpy_j_kg))
        delta = ph_h - bound_h
        return str(ph_h), str(delta)
    except Exception:
        return None, None
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
    if len(highs) < 2:
        if result.h_high_final and result.h_low_final:
            return Decimal(result.h_low_final), Decimal(result.h_high_final)
        return None
    return highs[-2], highs[-1]


def run_boundary_precision_audit(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int = 1,
) -> BoundaryPrecisionAudit:
    """Probe last shooting bracket and report terminal plateau (no tolerance change)."""
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

    tp_h, ph_delta = _shell_inlet_ph_delta(provider, bindings)

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

    t172_hashes: tuple[str, ...] = ()
    if accepted is not None:
        t172_hashes = tuple(str(h) for h in accepted.observables.local_task172_result_hashes)

    cum: list[str] = []
    run: _MeshRun | None = accepted or solved.best_valid_run
    if run is not None:
        obs = run.observables
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
        h_low_final=solved.h_low_final,
        h_high_final=solved.h_high_final,
        float_h_low_hex=solved.float_h_low_hex,
        float_h_high_hex=solved.float_h_high_hex,
        shell_inlet_temperature_k=str(effective_shell_inlet_temperature_k()),
        shell_cold_inlet_enthalpy_j_kg=str(effective_shell_cold_inlet_enthalpy_j_kg()),
        shell_inlet_tp_enthalpy_j_kg=tp_h,
        shell_inlet_ph_rebuild_delta_j_kg=ph_delta,
        last_two_valid_probes=tuple(probes[:3]),
        cumulative_enthalpy_audit=tuple(cum),
        terminal_precision_recovered=recovered,
        first_numerical_blocker=blocker,
        task172_identity_hashes_on_accepted=t172_hashes,
    )


__all__ = ["BoundaryPrecisionAudit", "run_boundary_precision_audit"]
