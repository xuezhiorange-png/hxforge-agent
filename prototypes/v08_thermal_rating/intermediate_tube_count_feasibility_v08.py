"""Finite envelope-scale scan (0.80–0.85) for intermediate tube counts near frozen design C."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    LAMINAR_UPPER_RE,
    TURBULENT_LOWER_RE,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.structural_bundles import (
    V08StructuralGeometryBundle,
)
from prototypes.v08_thermal_rating.candidate_c_identity_v08 import (
    CANDIDATE_C_SHELL_NOZZLE_ID_MM,
    CANDIDATE_C_TUBE_NOZZLE_ID_MM,
)
from prototypes.v08_thermal_rating.first_joint_candidate_freeze_v08 import _resolve_frozen_bundle
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.high_k_tube_side_structural_feasibility_v08 import (
    AuthorizedVariantResult,
    _evaluate_authorized_bundle,
)
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    RECOVERY_AUTHORITY_LABEL,
    SHELL_052_PROBE_M,
    RecoveredShell052Bundle,
    _with_envelope_override,
)
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    BREAKTHROUGH_DISCRETE_SPACE_PATH,
    baffle_spacing_for_length_m,
)
from prototypes.v08_thermal_rating.tube_side_replay_root_cause_v08 import (
    ComboIsolationDiagnostic,
    _diagnose_single_combo,
)

Task027RegimeUnchanged = Literal[True]

# Finite scan grid (not an exhaustive continuous search). Task021 yields discrete tube-count
# plateaus between these envelope diameter breakpoints.
FINITE_ENVELOPE_SCALES: tuple[Decimal, ...] = (
    Decimal("0.80"),
    Decimal("0.805"),
    Decimal("0.81"),
    Decimal("0.815"),
    Decimal("0.82"),
    Decimal("0.825"),
    Decimal("0.83"),
    Decimal("0.835"),
    Decimal("0.84"),
    Decimal("0.845"),
    Decimal("0.85"),
)
_TUBE_LENGTHS_M: tuple[Decimal, ...] = (Decimal("5.5"), Decimal("6.0"))
_FROZEN_ENVELOPE_SCALE = Decimal("0.80")

GeometryAuthorityState = Literal[
    "FROZEN_DESIGN_C_BREAKTHROUGH",
    "EXPERIMENTAL_SHADOW_ONLY",
    "TASK168_ENUMERATION_BLOCKED",
]


@dataclass(frozen=True)
class IntermediateLayoutScanRow:
    combo_key: str
    envelope_scale: str
    placement_envelope_diameter_m: str
    tube_length_m: str
    geometry_authority_state: GeometryAuthorityState
    authority_rationale: str
    isolation: ComboIsolationDiagnostic
    full_chain: AuthorizedVariantResult | None
    re_margin_below_turbulent_lower: str | None
    re_margin_note: str | None


@dataclass(frozen=True)
class HighKEvidenceSupersession:
    superseded_artifact_path: str
    supersession_artifact_revision: str
    historical_errors: tuple[str, ...]
    corrected_attribution: tuple[str, ...]
    new_tube_geometry_authority_decision: Literal["not_proven"]
    engineering_language_correction: str
    frozen_r1_artifact_preserved: Literal[True]


@dataclass(frozen=True)
class IntermediateTubeCountFeasibilityReport:
    task027_regime_unchanged: Task027RegimeUnchanged
    frozen_candidate_c_unchanged: Literal[True]
    frozen_baseline: dict[str, Any]
    scan_method: dict[str, Any]
    layouts_evaluated: tuple[IntermediateLayoutScanRow, ...]
    discrete_tube_count_plateaus: tuple[dict[str, Any], ...]
    model_supported_variant_count: int
    high_k_joint_prescreen_pass_count: int
    passing_variants: tuple[AuthorizedVariantResult, ...]
    best_variant: AuthorizedVariantResult | None
    evidence_supersession: HighKEvidenceSupersession
    new_authority_required: str
    design_decision: Literal[
        "EXPERIMENTAL_PRESCREEN_PASS",
        "NO_HIGH_K_JOINT_PASS_IN_SCAN",
    ]


def _enrich_pass_isolation(
    iso: ComboIsolationDiagnostic,
    item: V08StructuralGeometryBundle,
) -> ComboIsolationDiagnostic:
    t026 = getattr(item.bundle, "task026_result", None)
    reynolds = (
        str(t026.reynolds_number)
        if t026 is not None and t026.reynolds_number is not None
        else iso.task026_reynolds_number
    )
    physical = (
        int(item.bundle.task021_layout.physical_tube_count)
        if item.bundle.task021_layout
        else iso.task021_physical_tube_count
    )
    return replace(
        iso,
        candidate_id=item.candidate.candidate_id,
        task021_physical_tube_count=physical,
        task026_status="PASS",
        task026_reynolds_number=reynolds,
        task027_status="PASS",
        root_cause_class="STRUCTURAL_PASS",
        root_cause_summary="Task021–027 structural pass under placement envelope override.",
    )


def _re_margins(reynolds: str | None) -> tuple[str | None, str | None]:
    if reynolds is None:
        return None, None
    re_val = Decimal(reynolds)
    margin = (re_val - TURBULENT_LOWER_RE).quantize(Decimal("0.0001"))
    gap_blocked = LAMINAR_UPPER_RE < re_val < TURBULENT_LOWER_RE
    note = (
        f"Re={re_val}; margin vs turbulent lower bound Re≥{TURBULENT_LOWER_RE}: {margin} "
        f"(positive => Task027 turbulent branch eligible). "
        "Applicability can fail if mass flow, temperature, or properties shift Re into "
        f"the blocked transitional band {LAMINAR_UPPER_RE}–{TURBULENT_LOWER_RE}."
    )
    if gap_blocked:
        note += " CURRENT_VALUE_IN_BLOCKED_BAND."
    return str(margin), note


def _authority_for_scale(scale: Decimal) -> tuple[GeometryAuthorityState, str]:
    if scale == _FROZEN_ENVELOPE_SCALE:
        return (
            "FROZEN_DESIGN_C_BREAKTHROUGH",
            "Matches frozen design C breakthrough envelope; not re-derived as new catalog authority.",
        )
    return (
        "EXPERIMENTAL_SHADOW_ONLY",
        f"Envelope scale {scale} is not first-joint frozen authority; "
        f"placement override uses label {RECOVERY_AUTHORITY_LABEL} for prototype replay only.",
    )


def _plateaus(rows: tuple[IntermediateLayoutScanRow, ...]) -> tuple[dict[str, Any], ...]:
    seen: set[tuple[str, int]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        iso = row.isolation
        if iso.task021_physical_tube_count is None:
            continue
        key = (row.envelope_scale, iso.task021_physical_tube_count)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "envelope_scale": row.envelope_scale,
                "physical_tube_count": iso.task021_physical_tube_count,
                "task027_status": iso.task027_status,
                "reynolds_number": iso.task026_reynolds_number,
                "first_combo_key": row.combo_key,
            }
        )
    return tuple(out)


def run_intermediate_tube_count_feasibility(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> IntermediateTubeCountFeasibilityReport:
    active = provider or CoolPropProvider()
    frozen = _resolve_frozen_bundle(normalized, handoff)
    frozen_struct = frozen.structural_bundle
    frozen_baseline = {
        "candidate_id": FROZEN_FIRST_JOINT_CANDIDATE_ID,
        "geometry_v2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
        "physical_tube_count": int(frozen_struct.bundle.task021_layout.physical_tube_count),
        "tube_length_m": str(frozen_struct.candidate.tube_length_m),
        "envelope_scale": "0.80",
        "placement_envelope_diameter_m": str(
            (SHELL_052_PROBE_M * _FROZEN_ENVELOPE_SCALE).quantize(Decimal("0.0000000001"))
        ),
        "tube_nozzle_id_mm": str(CANDIDATE_C_TUBE_NOZZLE_ID_MM),
        "shell_nozzle_id_mm": str(CANDIDATE_C_SHELL_NOZZLE_ID_MM),
        "task168_request_hash_digest": frozen_struct.task168_request_hash_digest,
    }

    baseline_bundle = RecoveredShell052Bundle(
        structural_bundle=frozen_struct,
        candidate_space_hash=frozen.candidate_space_hash,
        discrete_space_authority_id="FROZEN_DESIGN_C",
        discrete_space_content_hash="FROZEN_DESIGN_C",
        placement_envelope_diameter_m=frozen_baseline["placement_envelope_diameter_m"],
        envelope_scale="0.80",
        baffle_cut_fraction="0.35",
        experimental_authority_label=RECOVERY_AUTHORITY_LABEL,
        recovery_note="frozen_design_c_baseline",
    )
    baseline_chain = _evaluate_authorized_bundle(
        baseline_bundle,
        label="frozen_design_c_223",
        normalized=normalized,
        handoff=handoff,
        provider=active,
    )
    frozen_baseline["clean_q_w"] = baseline_chain.clean_q_w if baseline_chain else None
    frozen_baseline["fouled_q_w"] = baseline_chain.fouled_q_w if baseline_chain else None
    frozen_baseline["high_tube_dp_pa"] = baseline_chain.high_tube_dp_pa if baseline_chain else None
    frozen_baseline["high_shell_dp_pa"] = (
        baseline_chain.high_shell_dp_pa if baseline_chain else None
    )
    frozen_baseline["high_k_joint_prescreen_pass"] = (
        baseline_chain.full_joint_pass if baseline_chain else False
    )

    rows: list[IntermediateLayoutScanRow] = []
    for scale in FINITE_ENVELOPE_SCALES:
        outcome = _with_envelope_override(
            normalized,
            handoff,
            discrete_path=BREAKTHROUGH_DISCRETE_SPACE_PATH,
            shell_m=SHELL_052_PROBE_M,
            envelope_scale=scale,
        )
        auth_state, auth_note = _authority_for_scale(scale)
        for length in _TUBE_LENGTHS_M:
            iso = _diagnose_single_combo(
                normalized,
                handoff,
                tube_length_m=length,
                envelope_scale=scale,
                enum_outcome=outcome,
            )
            full_chain: AuthorizedVariantResult | None = None
            spacing = baffle_spacing_for_length_m(length)
            matched_item: V08StructuralGeometryBundle | None = None
            for item in outcome.valid_structural:
                if Decimal(str(item.shell_record.shell_inside_diameter_m)) != SHELL_052_PROBE_M:
                    continue
                if Decimal(str(item.candidate.tube_length_m)) != length:
                    continue
                if Decimal(str(item.candidate.baffle_spacing_m)) != spacing:
                    continue
                matched_item = item
                break
            if matched_item is not None and iso.root_cause_class == "STRUCTURAL_PASS":
                iso = _enrich_pass_isolation(iso, matched_item)
            if iso.task027_status == "PASS" and matched_item is not None:
                item = matched_item
                bundle = RecoveredShell052Bundle(
                    structural_bundle=item,
                    candidate_space_hash=outcome.space_hash,
                    discrete_space_authority_id=outcome.filtered_space.authority_id,
                    discrete_space_content_hash=outcome.filtered_space.content_hash,
                    placement_envelope_diameter_m=outcome.placement_envelope_diameter_m,
                    envelope_scale=str(scale),
                    baffle_cut_fraction="0.35",
                    experimental_authority_label=RECOVERY_AUTHORITY_LABEL,
                    recovery_note=f"intermediate_scan_{iso.combo_key}",
                )
                full_chain = _evaluate_authorized_bundle(
                    bundle,
                    label=iso.combo_key,
                    normalized=normalized,
                    handoff=handoff,
                    provider=active,
                )
            elif iso.task026_reynolds_number is not None and iso.task027_status == "BLOCKED":
                auth_state = "TASK168_ENUMERATION_BLOCKED"
            margin, margin_note = _re_margins(iso.task026_reynolds_number)
            rows.append(
                IntermediateLayoutScanRow(
                    combo_key=iso.combo_key,
                    envelope_scale=str(scale),
                    placement_envelope_diameter_m=outcome.placement_envelope_diameter_m,
                    tube_length_m=str(length),
                    geometry_authority_state=auth_state,
                    authority_rationale=auth_note,
                    isolation=iso,
                    full_chain=full_chain,
                    re_margin_below_turbulent_lower=margin,
                    re_margin_note=margin_note,
                )
            )

    supported = [r for r in rows if r.full_chain is not None]
    passing_rows = [
        r.full_chain for r in supported if r.full_chain and r.full_chain.full_joint_pass
    ]
    unique_passing = {v.geometry_v2: v for v in passing_rows}
    passing = list(unique_passing.values())
    pass_count = len(passing)
    best: AuthorizedVariantResult | None = None
    if passing:
        best = sorted(
            passing,
            key=lambda v: (
                Decimal(v.high_tube_dp_pa or "1e30"),
                -Decimal(v.clean_q_w or "0"),
            ),
        )[0]

    supersession = HighKEvidenceSupersession(
        superseded_artifact_path="docs/tasks/evidence/V08-03-high-k-tube-side-structural-feasibility-r1.json",
        supersession_artifact_revision="r2",
        historical_errors=(
            "V08-03-high-k-tube-side-structural-feasibility-r1.md attributed 0.85/0.90 "
            "combo blocks to Task168/Task021 failures.",
            "r1 JSON set new_tube_geometry_authority_required=true from sole R1 tube catalog count.",
        ),
        corrected_attribution=(
            "Root-cause r1: Task021/024/025/026 PASS; Task027 BL_T027_UNSUPPORTED_REYNOLDS_REGIME "
            "for Re in transitional band on 0.85/0.90 scales.",
            "New tube OD/ID authority is NOT_PROVEN; placement-envelope expansion is a separate lever.",
        ),
        new_tube_geometry_authority_decision="not_proven",
        engineering_language_correction=(
            "Fewer parallel tubes raise per-tube mass flow and Reynolds; increasing tube count "
            "(larger placement envelope) lowers per-tube flow. Larger tube ID is not a direct Re lever "
            "in the fixed catalog scan."
        ),
        frozen_r1_artifact_preserved=True,
    )

    decision: Literal["EXPERIMENTAL_PRESCREEN_PASS", "NO_HIGH_K_JOINT_PASS_IN_SCAN"] = (
        "EXPERIMENTAL_PRESCREEN_PASS" if pass_count > 0 else "NO_HIGH_K_JOINT_PASS_IN_SCAN"
    )

    if pass_count > 0:
        new_auth = (
            "APPROVAL_REQUIRED: Task168 placement envelope authority for scales "
            "0.815–0.835 (235–241 tubes) as EXPERIMENTAL_SHADOW_ONLY until engineering sign-off; "
            "tube catalog OD19.05/ID15.75 unchanged; NOT_PROVEN that new tube record is required."
        )
    else:
        new_auth = (
            "Either Task027 transitional-flow correlation engineering validation, "
            "placement envelope authority, or thermal design adjustment — none auto-approved."
        )

    return IntermediateTubeCountFeasibilityReport(
        task027_regime_unchanged=True,
        frozen_candidate_c_unchanged=True,
        frozen_baseline=frozen_baseline,
        scan_method={
            "shell_inside_diameter_m": str(SHELL_052_PROBE_M),
            "envelope_scales_tested": [str(s) for s in FINITE_ENVELOPE_SCALES],
            "tube_lengths_m": [str(t) for t in _TUBE_LENGTHS_M],
            "baffle_cut_fraction": "0.35",
            "discrete_space_path": str(BREAKTHROUGH_DISCRETE_SPACE_PATH),
            "scan_type": "FINITE_DISCRETE_GRID",
            "exhaustive_search_claim": False,
            "focus_tube_count_band": "224-242",
            "nozzle_ids_mm_frozen": {
                "tube": str(CANDIDATE_C_TUBE_NOZZLE_ID_MM),
                "shell": str(CANDIDATE_C_SHELL_NOZZLE_ID_MM),
            },
        },
        layouts_evaluated=tuple(rows),
        discrete_tube_count_plateaus=_plateaus(tuple(rows)),
        model_supported_variant_count=len(supported),
        high_k_joint_prescreen_pass_count=pass_count,
        passing_variants=tuple(passing),
        best_variant=best,
        evidence_supersession=supersession,
        new_authority_required=new_auth,
        design_decision=decision,
    )


def _iso_dict(iso: ComboIsolationDiagnostic) -> dict[str, Any]:
    return {
        "combo_key": iso.combo_key,
        "candidate_id": iso.candidate_id,
        "physical_tube_count": iso.task021_physical_tube_count,
        "task021_status": iso.task021_status,
        "task024_status": iso.task024_status,
        "task025_status": iso.task025_status,
        "task026_status": iso.task026_status,
        "task026_reynolds_number": iso.task026_reynolds_number,
        "task027_status": iso.task027_status,
        "task027_blocker_code": iso.task027_blocker_code,
        "task168_failure_stage": iso.task168_failure_stage,
        "root_cause_class": iso.root_cause_class,
        "root_cause_summary": iso.root_cause_summary,
    }


def _variant_dict(v: AuthorizedVariantResult) -> dict[str, Any]:
    return {
        "label": v.label,
        "candidate_id": v.candidate_id,
        "geometry_v2": v.geometry_v2,
        "physical_tube_count": v.physical_tube_count,
        "tube_length_m": v.tube_length_m,
        "envelope_scale": v.envelope_scale,
        "clean_q_w": v.clean_q_w,
        "fouled_q_w": v.fouled_q_w,
        "mid_tube_dp_pa": v.mid_tube_dp_pa,
        "mid_shell_dp_pa": v.mid_shell_dp_pa,
        "high_tube_dp_pa": v.high_tube_dp_pa,
        "high_shell_dp_pa": v.high_shell_dp_pa,
        "four_port_check": v.four_port_check,
        "full_joint_pass": v.full_joint_pass,
        "failure_reasons": list(v.failure_reasons),
    }


def feasibility_artifact_dict(report: IntermediateTubeCountFeasibilityReport) -> dict[str, Any]:
    return {
        "schema": "hxforge.intermediate-tube-count-feasibility.v1",
        "task_id": "V08_03_INTERMEDIATE_TUBE_COUNT_FEASIBILITY_AND_EVIDENCE_RECONCILIATION",
        "task027_regime_unchanged": report.task027_regime_unchanged,
        "frozen_candidate_c_unchanged": report.frozen_candidate_c_unchanged,
        "frozen_baseline_223": report.frozen_baseline,
        "scan_method": report.scan_method,
        "discrete_tube_count_plateaus": list(report.discrete_tube_count_plateaus),
        "layouts_evaluated": [
            {
                "combo_key": row.combo_key,
                "envelope_scale": row.envelope_scale,
                "placement_envelope_diameter_m": row.placement_envelope_diameter_m,
                "tube_length_m": row.tube_length_m,
                "geometry_authority_state": row.geometry_authority_state,
                "authority_rationale": row.authority_rationale,
                "isolation": _iso_dict(row.isolation),
                "re_margin_below_turbulent_lower": row.re_margin_below_turbulent_lower,
                "re_margin_note": row.re_margin_note,
                "full_chain": _variant_dict(row.full_chain) if row.full_chain else None,
            }
            for row in report.layouts_evaluated
        ],
        "model_supported_variant_count": report.model_supported_variant_count,
        "high_k_joint_prescreen_pass_count": report.high_k_joint_prescreen_pass_count,
        "passing_variants": [_variant_dict(v) for v in report.passing_variants],
        "best_variant": _variant_dict(report.best_variant) if report.best_variant else None,
        "evidence_supersession": {
            "superseded_artifact_path": report.evidence_supersession.superseded_artifact_path,
            "supersession_artifact_revision": report.evidence_supersession.supersession_artifact_revision,
            "historical_errors": list(report.evidence_supersession.historical_errors),
            "corrected_attribution": list(report.evidence_supersession.corrected_attribution),
            "new_tube_geometry_authority_decision": report.evidence_supersession.new_tube_geometry_authority_decision,
            "engineering_language_correction": report.evidence_supersession.engineering_language_correction,
            "frozen_r1_artifact_preserved": report.evidence_supersession.frozen_r1_artifact_preserved,
        },
        "new_authority_required": report.new_authority_required,
        "design_decision": report.design_decision,
        "engineering_design_status": "EXPERIMENTAL_PRESCREEN_ONLY",
    }


def write_feasibility_artifacts(
    report: IntermediateTubeCountFeasibilityReport,
    *,
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    artifact = feasibility_artifact_dict(report)
    jp = Path(json_path)
    mp = Path(md_path)
    jp.parent.mkdir(parents=True, exist_ok=True)
    mp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Intermediate tube count feasibility (design C frozen)",
        "",
        f"- **Design decision:** {report.design_decision}",
        f"- **High-K joint prescreen pass count:** {report.high_k_joint_prescreen_pass_count}",
        f"- **Model-supported variants:** {report.model_supported_variant_count}",
        f"- **Frozen baseline tubes:** {report.frozen_baseline['physical_tube_count']} @ scale 0.80",
        "",
        "## Scan bounds",
        "",
        f"Finite grid: scales {', '.join(report.scan_method['envelope_scales_tested'])}; "
        f"lengths {', '.join(report.scan_method['tube_lengths_m'])} m; "
        "not a continuous exhaustive search.",
        "",
        "## Discrete tube-count plateaus (Task021 effective parallel count)",
        "",
    ]
    for p in report.discrete_tube_count_plateaus:
        lines.append(
            f"- scale **{p['envelope_scale']}** → **{p['physical_tube_count']}** tubes; "
            f"Task027={p['task027_status']}; Re={p.get('reynolds_number')}"
        )
    lines.extend(
        [
            "",
            "## Evidence supersession",
            "",
            f"Supersedes wording in `{report.evidence_supersession.superseded_artifact_path}` (r1 preserved).",
            "",
            report.evidence_supersession.engineering_language_correction,
            "",
            f"**New tube geometry authority:** {report.evidence_supersession.new_tube_geometry_authority_decision}",
            "",
            f"**Authority / next step:** {report.new_authority_required}",
            "",
            "Status: EXPERIMENTAL_PRESCREEN_ONLY — not manufacturing acceptance.",
        ]
    )
    if report.best_variant:
        b = report.best_variant
        lines.extend(
            [
                "",
                "## Best high-K joint-prescreen variant",
                "",
                f"- Tubes: {b.physical_tube_count} @ envelope scale {b.envelope_scale}, L={b.tube_length_m} m",
                f"- geometry_v2: `{b.geometry_v2}`",
                f"- clean Q: {b.clean_q_w} W; fouled Q: {b.fouled_q_w} W",
                f"- high tube Δp: {b.high_tube_dp_pa} Pa; high shell Δp: {b.high_shell_dp_pa} Pa",
            ]
        )
    mp.write_text("\n".join(lines), encoding="utf-8")


__all__ = [
    "FINITE_ENVELOPE_SCALES",
    "IntermediateTubeCountFeasibilityReport",
    "feasibility_artifact_dict",
    "run_intermediate_tube_count_feasibility",
    "write_feasibility_artifacts",
]
