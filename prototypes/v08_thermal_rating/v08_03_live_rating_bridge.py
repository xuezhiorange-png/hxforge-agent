"""V08-03 live Task173 rating bridge into the V08-05 qualification chain (no prescreen substitute)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    build_candidate_rating_bindings,
)
from prototypes.v08_thermal_rating.pipeline import (
    V08ThermalCandidateRatingRow,
    V08ThermalRatingResult,
    run_v08_thermal_rating,
)
from prototypes.v08_thermal_rating.v08_04_hydraulic_feasibility_gate import (
    evaluate_v08_04_candidate_hydraulics,
)
from prototypes.v08_thermal_rating.v08_05_qualified_top_n_engineering_report import (
    V08_05EngineeringReport,
    run_v08_05_qualified_selection,
)
from prototypes.v08_thermal_rating.v08_autonomous_design_tool import _collect_structural_entries

TASK_ID = "V08-03"
EXECUTION_STAGE = "LIVE_RATING_ACCEPTANCE_RECOVERY"

# Frozen blocker evidence — do not re-run unchanged identities (Issue #324 / layered RFC).
KNOWN_RATING_BLOCKER_EVIDENCE: dict[str, dict[str, str]] = {
    "e1baa795-9cf5-5718-8fa8-0688d2102c5c": {
        "rating_blocked_code": "BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
        "evidence": "docs/decisions/V08_03_LAYERED_ACCEPTANCE_RFC.md",
        "mesh_terminal": "N1",
    },
    "9277ebb8-5b05-5130-8b90-92ee4768606b": {
        "rating_blocked_code": "BLOCKED_TASK172_LOCAL_CONSTITUTIVE_CLOSURE",
        "evidence": "docs/decisions/V08_03_LAYERED_ACCEPTANCE_RFC.md",
        "mesh_terminal": "N4",
    },
}

LiveAttemptSource = Literal["EXECUTED", "EVIDENCE_ONLY_SKIP"]


@dataclass(frozen=True)
class LiveRatingAttemptRecord:
    candidate_id: str
    attempt_source: LiveAttemptSource
    rating_row: V08ThermalCandidateRatingRow | None
    evidence_note: str | None


@dataclass(frozen=True)
class V08_03LiveRatingBridgeReport:
    task_id: str
    execution_stage: str
    v08_05_report_hash: str
    live_rating: V08ThermalRatingResult | None
    attempts: tuple[LiveRatingAttemptRecord, ...]
    live_rating_actually_executed: bool
    successful_live_rating_count: int
    successful_live_e2e_count: int
    remaining_numerical_blocker: str | None


def _bindings_for_candidate(
    report: V08_05EngineeringReport,
    candidate_id: str,
    *,
    provider: CoolPropProvider,
) -> CandidateRatingBindings | None:
    tool = report.design_tool_mirror
    if tool is None or tool.ingestion.normalized is None or tool.ingestion.handoff is None:
        return None
    normalized = tool.ingestion.normalized
    handoff = tool.ingestion.handoff
    entries = _collect_structural_entries(normalized, handoff, max_candidates=64)
    for entry in entries:
        if entry.bundle.candidate.candidate_id != candidate_id:
            continue
        return build_candidate_rating_bindings(
            entry.bundle,
            space_hash=entry.space_hash,
            t168_digest=entry.t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
            geometry_projection_hash=entry.geom_hash,
        )
    return None


def _live_e2e_success(
    row: V08ThermalCandidateRatingRow,
    *,
    bindings: CandidateRatingBindings | None,
    provider: CoolPropProvider,
) -> bool:
    if row.rating_outcome != "RATING_SUCCESS":
        return False
    if row.mesh_convergence_n1_n2_n4 != "PASS" or row.energy_balance_status != "PASS":
        return False
    if bindings is None:
        return False
    try:
        hyd = evaluate_v08_04_candidate_hydraulics(bindings, provider=provider)
    except (ValueError, TypeError):
        return False
    g = hyd.hard_gate
    return (
        g.tube_full_path == "PASS"
        and g.shell_full_path == "PASS"
        and g.four_nozzle_velocity == "PASS"
        and g.geometry_legal == "PASS"
        and g.model_applicability == "PASS"
    )


def run_v08_05_with_live_thermal_rating(
    case_json_text: str,
    *,
    provider: CoolPropProvider | None = None,
    max_candidates: int = 48,
    top_n: int = 5,
    max_live_rating_geometries: int = 32,
    min_accepted_distinct_geometries: int = 2,
    skip_candidate_ids: frozenset[str] | None = None,
) -> V08_03LiveRatingBridgeReport:
    """V08-05 prescreen chain, then production ``run_v08_thermal_rating`` (never ε-NTU as live)."""
    active = provider or CoolPropProvider()
    skip = skip_candidate_ids or frozenset(KNOWN_RATING_BLOCKER_EVIDENCE.keys())
    report = run_v08_05_qualified_selection(
        case_json_text,
        provider=active,
        max_candidates=max_candidates,
        top_n=top_n,
        run_mdot_on_recommendation=False,
    )
    live_result: V08ThermalRatingResult | None = None
    attempts: list[LiveRatingAttemptRecord] = []
    executed = False
    if (
        (mirror := report.design_tool_mirror)
        and mirror.ingestion.ok
        and mirror.ingestion.normalized
        and mirror.ingestion.handoff
    ):
        executed = True
        live_result = run_v08_thermal_rating(
            mirror.ingestion.normalized,
            mirror.ingestion.handoff,
            provider=active,
            max_valid_geometry=max_live_rating_geometries,
            min_accepted_distinct_geometries=min_accepted_distinct_geometries,
            skip_candidate_ids=skip,
        )
        rated_by_id = {r.candidate_id: r for r in live_result.candidates_rated}
        for row in live_result.candidates_rated:
            attempts.append(
                LiveRatingAttemptRecord(
                    candidate_id=row.candidate_id,
                    attempt_source="EXECUTED",
                    rating_row=row,
                    evidence_note=None,
                )
            )
        for cid in skip:
            if cid in rated_by_id:
                continue
            meta = KNOWN_RATING_BLOCKER_EVIDENCE.get(cid, {})
            attempts.append(
                LiveRatingAttemptRecord(
                    candidate_id=cid,
                    attempt_source="EVIDENCE_ONLY_SKIP",
                    rating_row=None,
                    evidence_note=(
                        f"{meta.get('rating_blocked_code', 'KNOWN_BLOCKER')} @ "
                        f"{meta.get('mesh_terminal', '?')}; {meta.get('evidence', '')}"
                    ).strip("; "),
                )
            )

    live_success = 0
    e2e_success = 0
    blockers: list[str] = []
    if live_result is not None:
        live_success = live_result.distinct_fully_converged_rating_count
        blockers.extend(live_result.model_blockers or ())
        for row in live_result.candidates_rated:
            if row.rating_outcome == "RATING_SUCCESS" and row.mesh_convergence_n1_n2_n4 == "PASS":
                bindings = _bindings_for_candidate(report, row.candidate_id, provider=active)
                if _live_e2e_success(row, bindings=bindings, provider=active):
                    e2e_success += 1
        for rec in attempts:
            if rec.attempt_source == "EVIDENCE_ONLY_SKIP" and rec.evidence_note:
                blockers.append(rec.evidence_note.split(";")[0])

    remaining: str | None = None
    if live_success == 0:
        if blockers:
            remaining = "; ".join(sorted(frozenset(blockers))[:6])
        else:
            remaining = "NO_LIVE_RATING_ATTEMPT"

    return V08_03LiveRatingBridgeReport(
        task_id=TASK_ID,
        execution_stage=EXECUTION_STAGE,
        v08_05_report_hash=report.report_hash,
        live_rating=live_result,
        attempts=tuple(attempts),
        live_rating_actually_executed=executed,
        successful_live_rating_count=live_success,
        successful_live_e2e_count=e2e_success,
        remaining_numerical_blocker=remaining,
    )


def bridge_report_to_delivery_fields(
    bridge: V08_03LiveRatingBridgeReport,
    *,
    engineering_case_id: str,
) -> dict[str, Any]:
    """Map bridge output to V08-03 closeout field names."""
    first_row: V08ThermalCandidateRatingRow | None = None
    if bridge.live_rating is not None:
        for row in bridge.live_rating.candidates_rated:
            if row.rating_outcome == "RATING_SUCCESS":
                first_row = row
                break

    distinct_success = bridge.successful_live_rating_count
    return {
        "TASK_ID": TASK_ID,
        "EXECUTION_STAGE": EXECUTION_STAGE,
        "ENGINEERING_CASE_ID": engineering_case_id,
        "LIVE_RATING_ACTUALLY_EXECUTED": bridge.live_rating_actually_executed,
        "FIRST_SUCCESSFUL_LIVE_CASE": engineering_case_id if first_row else None,
        "FIRST_SUCCESSFUL_GEOMETRY": (
            first_row.geometry_projection_hash
            if first_row and first_row.geometry_projection_hash
            else (first_row.candidate_id if first_row else None)
        ),
        "N1_N2_N4_CONVERGENCE": (first_row.mesh_convergence_n1_n2_n4 if first_row else "NONE"),
        "LIVE_DUTY_W": first_row.total_duty_w if first_row else None,
        "ENERGY_BALANCE_ERROR": first_row.energy_balance_residual_w if first_row else None,
        "TUBE_OUTLET_TEMPERATURE": first_row.tube_outlet_temperature_k if first_row else None,
        "SHELL_OUTLET_TEMPERATURE": first_row.shell_outlet_temperature_k if first_row else None,
        "FULL_PATH_HYDRAULIC_STATUS": (
            "PASS" if bridge.successful_live_e2e_count else "NOT_ACHIEVED"
        ),
        "SUCCESSFUL_LIVE_RATING_COUNT": distinct_success,
        "SUCCESSFUL_LIVE_E2E_COUNT": bridge.successful_live_e2e_count,
        "REMAINING_NUMERICAL_BLOCKER": bridge.remaining_numerical_blocker,
        "V08_03_ENGINEERING_ACCEPTANCE": "PASS" if distinct_success >= 2 else "BLOCKED",
        "V08_06_FORMAL_ACCEPTANCE": bridge.successful_live_e2e_count >= 1,
        "LIVE_ATTEMPTS": [
            {
                "candidate_id": a.candidate_id,
                "source": a.attempt_source,
                "rating_outcome": a.rating_row.rating_outcome if a.rating_row else None,
                "rating_blocked_code": (
                    a.rating_row.rating_blocked_code
                    if a.rating_row
                    else KNOWN_RATING_BLOCKER_EVIDENCE.get(a.candidate_id, {}).get(
                        "rating_blocked_code"
                    )
                ),
                "evidence_note": a.evidence_note,
            }
            for a in bridge.attempts
        ],
        "ARCHITECTURE_DECISION_REQUIRED": (
            distinct_success == 0
            and "BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED"
            in (bridge.remaining_numerical_blocker or "")
        ),
        "ARCHITECTURE_NOTE": (
            "Task173 outer enthalpy shooting hits C-ULP precision floor before N1/N2/N4 mesh "
            "acceptance on 250 kW admissible space (3 structures). Authorized path: "
            "TASK173_OUTER_ENTHALPY_NUMERICAL_REPRESENTATION per V08_03_BVP_ROUTE_STOP.md; "
            "not TRF/BVP/cache expansion in this recovery stage."
            if distinct_success == 0
            else None
        ),
    }
