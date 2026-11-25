"""Bridge independent V08 kernel thermal rating into V08-04 / V08-05 chain."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from hexagent.canonical_json import canonical_sha256
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
    load_case_bindings,
)
from prototypes.v08_thermal_rating.v08_04_hydraulic_feasibility_gate import (
    evaluate_v08_04_candidate_hydraulics,
)
from prototypes.v08_thermal_rating.v08_05_qualified_top_n_engineering_report import (
    run_v08_05_qualified_selection,
)
from prototypes.v08_thermal_rating.v08_independent_engineering_rating_kernel_v1 import (
    KERNEL_AUTHORITY_ID,
    KernelThermalRatingResult,
    rate_candidate_engineering_kernel_v1,
)

TASK_ID = "V08-03"
EXECUTION_STAGE = "INDEPENDENT_ENGINEERING_RATING_KERNEL"

HydraulicPass = Literal["PASS", "FAIL", "ERROR"]
ThermalPass = Literal["RATING_SUCCESS", "RATING_BLOCKED"]
E2EPass = Literal["FULL_E2E_SUCCESS", "THERMAL_ONLY", "HYDRAULIC_OR_MODEL_FAIL", "THERMAL_BLOCKED"]


@dataclass(frozen=True)
class KernelChainCandidateRecord:
    candidate_id: str
    geometry_projection_hash: str
    thermal: KernelThermalRatingResult
    hydraulic_hard_gate: dict[str, Any] | None
    hydraulic_pass: HydraulicPass
    e2e_class: E2EPass
    integration_notes: tuple[str, ...]


@dataclass(frozen=True)
class KernelDesignChainReport:
    task_id: str
    execution_stage: str
    kernel_authority_id: str
    fixture_path: str
    engineering_case_id: str
    normalization_hash: str
    candidates_attempted: int
    distinct_successful_thermal_ids: tuple[str, ...]
    successful_e2e_ids: tuple[str, ...]
    records: tuple[KernelChainCandidateRecord, ...]
    v08_04_integration_pass: bool
    v08_05_prescreen_hash: str | None
    report_hash: str


def _hydraulic_pass(hard: dict[str, Any] | None) -> HydraulicPass:
    if hard is None:
        return "ERROR"
    g = hard
    ok = (
        g.get("tube_full_path") == "PASS"
        and g.get("shell_full_path") == "PASS"
        and g.get("four_nozzle_velocity") == "PASS"
        and g.get("geometry_legal") == "PASS"
        and g.get("model_applicability") == "PASS"
    )
    return "PASS" if ok else "FAIL"


def _e2e_class(thermal: KernelThermalRatingResult, hyd: HydraulicPass) -> E2EPass:
    if thermal.status != "RATING_SUCCESS":
        return "THERMAL_BLOCKED"
    if hyd == "PASS":
        return "FULL_E2E_SUCCESS"
    if hyd == "FAIL":
        return "HYDRAULIC_OR_MODEL_FAIL"
    return "THERMAL_ONLY"


def run_kernel_design_chain_for_fixture(
    fixture: Path,
    *,
    provider: CoolPropProvider | None = None,
    max_candidates: int = 48,
    include_v08_05_mirror: bool = True,
) -> KernelDesignChainReport:
    """Rate structural candidates with kernel v1; run V08-04 hydraulics on same bindings."""
    active = provider or CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(fixture, provider=active)
    space_hash, t168_digest, bundles, geom_hashes = enumerate_structural_bundles(
        normalized, handoff, max_valid=max_candidates
    )
    norm_hash = canonical_sha256(json.dumps(normalized.model_dump(mode="json"), sort_keys=True))
    records: list[KernelChainCandidateRecord] = []
    for bundle in bundles:
        cid = bundle.candidate.candidate_id
        gh = geom_hashes.get(cid, "")
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=space_hash,
            t168_digest=t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=active,
            geometry_projection_hash=gh,
        )
        if bindings is None:
            continue
        thermal = rate_candidate_engineering_kernel_v1(bindings, normalized, provider=active)
        hard_payload: dict[str, Any] | None = None
        hyd_pass: HydraulicPass = "ERROR"
        notes: list[str] = [
            "kernel_outlet_T_for_audit_only_v08_04_uses_case_inlet_mdot",
            f"space_hash={space_hash}",
        ]
        try:
            hyd = evaluate_v08_04_candidate_hydraulics(bindings, provider=active)
            hard_payload = asdict(hyd.hard_gate)
            hyd_pass = _hydraulic_pass(hard_payload)
        except (ValueError, TypeError, KeyError) as exc:
            notes.append(f"hydraulic_eval_error:{type(exc).__name__}")
        e2e = _e2e_class(thermal, hyd_pass)
        records.append(
            KernelChainCandidateRecord(
                candidate_id=cid,
                geometry_projection_hash=gh,
                thermal=thermal,
                hydraulic_hard_gate=hard_payload,
                hydraulic_pass=hyd_pass,
                e2e_class=e2e,
                integration_notes=tuple(notes),
            )
        )
    thermal_ok = tuple(
        sorted({r.candidate_id for r in records if r.thermal.status == "RATING_SUCCESS"})
    )
    e2e_ok = tuple(sorted({r.candidate_id for r in records if r.e2e_class == "FULL_E2E_SUCCESS"}))
    v08_05_hash: str | None = None
    if include_v08_05_mirror:
        v05 = run_v08_05_qualified_selection(
            fixture.read_text(encoding="utf-8"),
            provider=active,
            max_candidates=max_candidates,
            top_n=5,
            run_mdot_on_recommendation=False,
        )
        v08_05_hash = v05.report_hash
    payload = {
        "task_id": TASK_ID,
        "kernel_authority_id": KERNEL_AUTHORITY_ID,
        "case_id": normalized.engineering_case_id,
        "norm_hash": norm_hash,
        "thermal_success": thermal_ok,
        "e2e_success": e2e_ok,
        "records": [
            {
                "candidate_id": r.candidate_id,
                "thermal_status": r.thermal.status,
                "e2e": r.e2e_class,
                "q_w": r.thermal.q_w,
                "geometry_hash": r.geometry_projection_hash,
            }
            for r in records
        ],
    }
    rep_hash = canonical_sha256(json.dumps(payload, sort_keys=True))
    v04_pass = any(r.hydraulic_hard_gate is not None for r in records)
    return KernelDesignChainReport(
        task_id=TASK_ID,
        execution_stage=EXECUTION_STAGE,
        kernel_authority_id=KERNEL_AUTHORITY_ID,
        fixture_path=str(fixture),
        engineering_case_id=normalized.engineering_case_id,
        normalization_hash=norm_hash,
        candidates_attempted=len(records),
        distinct_successful_thermal_ids=thermal_ok,
        successful_e2e_ids=e2e_ok,
        records=tuple(records),
        v08_04_integration_pass=v04_pass,
        v08_05_prescreen_hash=v08_05_hash,
        report_hash=rep_hash,
    )


__all__ = [
    "KernelChainCandidateRecord",
    "KernelDesignChainReport",
    "run_kernel_design_chain_for_fixture",
]