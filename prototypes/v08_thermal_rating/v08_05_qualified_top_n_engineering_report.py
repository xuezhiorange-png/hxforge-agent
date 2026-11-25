"""V08-05 — qualified Top-N selection and traceable engineering report (experimental)."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.canonical_json import canonical_sha256
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import build_candidate_rating_bindings
from prototypes.v08_thermal_rating.v08_04_hydraulic_feasibility_gate import (
    PRODUCTION_RATING_VALIDATED,
    V08_03_ENGINEERING_ACCEPTANCE,
    evaluate_v08_04_candidate_hydraulics,
)
from prototypes.v08_thermal_rating.v08_autonomous_design_tool import (
    ENGINEERING_DESIGN_STATUS,
    AutonomousDesignToolReport,
    CandidateBaselineRecord,
    _collect_structural_entries,
    _evaluate_baseline_candidate,
    run_autonomous_design_tool,
)

TASK_ID = "V08-05"
TASK_NAME = "QUALIFIED_TOP_N_SELECTION_AND_ENGINEERING_REPORT"
FORMAL_ACCEPTANCE = False

QualificationClass = Literal[
    "FORMAL_ENGINEERING_FEASIBLE",
    "ASSUMPTION_CONDITIONAL_FEASIBLE",
    "EXPERIMENTAL_PRESCREEN_PASS",
    "THERMAL_INSUFFICIENT",
    "PRESSURE_DROP_EXCEEDED",
    "MODEL_BLOCKED",
    "NOT_CONVERGED",
    "BUDGET_STOP",
    "GEOMETRY_BLOCKED",
]

CaseOutcome = Literal[
    "SUCCESS_EXPERIMENTAL_TOP_N",
    "NO_FEASIBLE_DESIGN",
    "MODEL_BLOCKED",
    "OUT_OF_ENVELOPE",
    "INVALID_INPUT",
    "BUDGET_STOP",
]

RankingAxis = Literal[
    "duty_priority",
    "pressure_margin_priority",
    "area_and_size_priority",
    "composite_engineering",
]

_RANKING_METHOD = (
    "Hard-filter first: production formal list requires PRODUCTION_RATING_VALIDATED; "
    "prototype ranks only experimental_prescreen_pass separately. "
    "duty_priority: descending prescreen Q. "
    "pressure_margin_priority: descending min(tube,shell) high_loss margin Pa. "
    "area_and_size_priority: descending UA·A proxy from prescreen. "
    "composite_engineering: tuple (thermal_pass, min_margin, Q) lexicographic; "
    "ties broken by candidate_id lexicographic."
)


@dataclass(frozen=True)
class CandidateQualificationRecord:
    candidate_id: str
    layout_key: str
    qualification_class: QualificationClass
    formal_engineering_eligible: bool
    experimental_prescreen_eligible: bool
    baseline: CandidateBaselineRecord
    hydraulic_v08_04: dict[str, Any] | None
    design_specification: dict[str, Any] | None
    rejection_trace: tuple[str, ...]
    ranking_scores: dict[str, str | None]
    convergence_status: str
    authority_tier: str


@dataclass(frozen=True)
class TopNRankedLists:
    top_n_requested: int
    formal_engineering: tuple[str, ...]
    experimental_prescreen: tuple[str, ...]
    conditional_assumption: tuple[str, ...]
    rankings_by_axis: dict[str, tuple[str, ...]]
    tie_break_rule: str


@dataclass(frozen=True)
class V08_05EngineeringReport:
    task_id: str
    task_name: str
    engineering_design_status: str
    production_rating_validated: bool
    v08_03_engineering_acceptance: str
    case_outcome: CaseOutcome
    case_outcome_detail: str
    top_n: TopNRankedLists
    candidates: tuple[CandidateQualificationRecord, ...]
    normalization_hash: str
    design_tool_result_hash: str
    report_hash: str
    design_tool_mirror: AutonomousDesignToolReport | None


def _classify_candidate(
    baseline: CandidateBaselineRecord,
    *,
    hydraulic_payload: dict[str, Any] | None,
    design_spec: dict[str, Any] | None,
) -> tuple[QualificationClass, tuple[str, ...], bool, bool]:
    reasons: list[str] = list(baseline.block_reasons)
    if "TASK174_BINDINGS_BLOCKED" in reasons:
        return "GEOMETRY_BLOCKED", tuple(reasons), False, False
    if not baseline.task027_pass:
        return "MODEL_BLOCKED", tuple(reasons) or ("TASK027_BLOCKED",), False, False
    if not baseline.thermal_pass:
        return "THERMAL_INSUFFICIENT", tuple(reasons) or ("THERMAL_DUTY_NOT_MET",), False, False
    h_gate = (hydraulic_payload or {}).get("hard_gate") or {}
    tube_st = h_gate.get("tube_full_path")
    shell_st = h_gate.get("shell_full_path")
    if hydraulic_payload and (tube_st == "OVER_DP" or shell_st == "OVER_DP"):
        reasons = list(reasons) + ["FULL_PATH_OVER_DP"] if reasons else ["FULL_PATH_OVER_DP"]
        return "PRESSURE_DROP_EXCEEDED", tuple(reasons), False, False
    if baseline.engineering_joint_pass:
        k_rows = hydraulic_payload.get("k_scenarios") if hydraulic_payload else []
        all_k_pass = bool(k_rows and all(r.get("hydraulic_check") == "PASS" for r in k_rows))
        if all_k_pass:
            return (
                "ASSUMPTION_CONDITIONAL_FEASIBLE",
                tuple(reasons),
                False,
                True,
            )
        return (
            "EXPERIMENTAL_PRESCREEN_PASS",
            tuple(reasons),
            False,
            True,
        )
    if not baseline.nozzle_velocity_pass:
        return "PRESSURE_DROP_EXCEEDED", tuple(reasons) or ("NOZZLE_VELOCITY",), False, False
    return "MODEL_BLOCKED", tuple(reasons) or ("JOINT_PRESCREEN_FAIL",), False, False


def _ranking_scores(
    baseline: CandidateBaselineRecord,
    hydraulic_payload: dict[str, Any] | None,
    design_spec: dict[str, Any] | None,
) -> dict[str, str | None]:
    q = baseline.thermal_q_w
    min_margin: str | None = None
    if hydraulic_payload:
        high = next(
            (
                k
                for k in hydraulic_payload.get("k_scenarios", [])
                if k.get("scenario_key") == "high_loss_sensitivity"
            ),
            None,
        )
        if high:
            tm = high.get("tube_margin_pa")
            sm = high.get("shell_margin_pa")
            if tm is not None and sm is not None:
                min_margin = str(min(Decimal(tm), Decimal(sm)))
    ua = None
    if design_spec:
        ua = (design_spec.get("thermal_experimental_prescreen") or {}).get("overall_ua_w_per_k")
    return {
        "duty_w": q,
        "min_high_tier_margin_pa": min_margin,
        "overall_ua_w_per_k": str(ua) if ua is not None else None,
    }


def _dedupe_preserve_order(ids: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for cid in ids:
        if cid in seen:
            continue
        seen.add(cid)
        out.append(cid)
    return tuple(out)


def _sort_ids(
    records: list[CandidateQualificationRecord],
    *,
    axis: RankingAxis,
) -> tuple[str, ...]:
    if not records:
        return ()
    reverse = True

    def key_fn(r: CandidateQualificationRecord) -> tuple[Any, ...]:
        if axis == "duty_priority":
            return (Decimal(r.ranking_scores.get("duty_w") or "-1"),)
        if axis == "pressure_margin_priority":
            return (Decimal(r.ranking_scores.get("min_high_tier_margin_pa") or "-1e9"),)
        if axis == "area_and_size_priority":
            return (Decimal(r.ranking_scores.get("overall_ua_w_per_k") or "-1"),)
        margin = Decimal(r.ranking_scores.get("min_high_tier_margin_pa") or "-1e9")
        q = Decimal(r.ranking_scores.get("duty_w") or "-1")
        return (r.baseline.thermal_pass, margin, q)

    ordered = sorted(records, key=key_fn, reverse=reverse)
    # Stable tie-break
    stable: list[CandidateQualificationRecord] = []
    for r in ordered:
        stable.append(r)
    stable.sort(key=lambda r: (key_fn(r), r.candidate_id), reverse=reverse)
    return tuple(r.candidate_id for r in stable)


def _build_top_n(
    candidates: tuple[CandidateQualificationRecord, ...],
    *,
    top_n: int,
) -> TopNRankedLists:
    formal: list[str] = []
    if PRODUCTION_RATING_VALIDATED:
        formal = [c.candidate_id for c in candidates if c.formal_engineering_eligible][:top_n]
    experimental = [c for c in candidates if c.experimental_prescreen_eligible]
    conditional = [
        c.candidate_id
        for c in candidates
        if c.qualification_class == "ASSUMPTION_CONDITIONAL_FEASIBLE"
    ]
    axis_keys: tuple[RankingAxis, ...] = (
        "duty_priority",
        "pressure_margin_priority",
        "area_and_size_priority",
        "composite_engineering",
    )
    axes = {
        axis_key: _dedupe_preserve_order(_sort_ids(experimental, axis=axis_key)[:top_n])
        for axis_key in axis_keys
    }
    exp_ids = _dedupe_preserve_order(_sort_ids(experimental, axis="composite_engineering")[:top_n])
    return TopNRankedLists(
        top_n_requested=top_n,
        formal_engineering=tuple(formal),
        experimental_prescreen=tuple(exp_ids),
        conditional_assumption=tuple(conditional[:top_n]),
        rankings_by_axis=axes,
        tie_break_rule="candidate_id lexicographic after primary metric",
    )


def _case_outcome(
    ingestion_ok: bool,
    blockers: tuple[dict[str, str], ...],
    generated: int,
    experimental_count: int,
) -> tuple[CaseOutcome, str]:
    if not ingestion_ok:
        codes = {b.get("code", "") for b in blockers}
        if any("OUT_OF_ENVELOPE" in c or "ENVELOPE" in c for c in codes):
            return "OUT_OF_ENVELOPE", "Input validation or envelope failure"
        return "INVALID_INPUT", "Case ingestion blocked"
    if generated == 0:
        return "OUT_OF_ENVELOPE", "No structural candidates after envelope filter"
    if experimental_count == 0:
        return "NO_FEASIBLE_DESIGN", "No experimental prescreen pass under hard constraints"
    return "SUCCESS_EXPERIMENTAL_TOP_N", f"Ranked {experimental_count} experimental candidate(s)"


def run_v08_05_qualified_selection(
    case_json_text: str,
    *,
    provider: CoolPropProvider | None = None,
    max_candidates: int = 48,
    top_n: int = 5,
    run_mdot_on_recommendation: bool = True,
) -> V08_05EngineeringReport:
    """Canonical V08-05 pipeline: same chain for CLI, API, and web backend."""
    provider = provider or CoolPropProvider()
    tool: AutonomousDesignToolReport = run_autonomous_design_tool(
        case_json_text,
        provider=provider,
        max_candidates=max_candidates,
        run_mdot_on_recommendation=run_mdot_on_recommendation,
    )
    if not tool.ingestion.ok or tool.ingestion.normalized is None or tool.ingestion.handoff is None:
        return V08_05EngineeringReport(
            task_id=TASK_ID,
            task_name=TASK_NAME,
            engineering_design_status=ENGINEERING_DESIGN_STATUS,
            production_rating_validated=PRODUCTION_RATING_VALIDATED,
            v08_03_engineering_acceptance=V08_03_ENGINEERING_ACCEPTANCE,
            case_outcome=_case_outcome(False, tool.ingestion.blockers, 0, 0)[0],
            case_outcome_detail=_case_outcome(False, tool.ingestion.blockers, 0, 0)[1],
            top_n=_build_top_n((), top_n=top_n),
            candidates=(),
            normalization_hash=canonical_sha256(
                {"ingestion_blockers": [dict(b) for b in tool.ingestion.blockers]}
            ),
            design_tool_result_hash=tool.result_hash,
            report_hash=canonical_sha256({"blocked_ingestion": True}),
            design_tool_mirror=tool,
        )
    normalized = tool.ingestion.normalized
    handoff = tool.ingestion.handoff
    entries = _collect_structural_entries(normalized, handoff, max_candidates=max_candidates)
    qual_records: list[CandidateQualificationRecord] = []
    for entry in entries:
        structural = entry.bundle
        baseline, spec, _hyd = _evaluate_baseline_candidate(
            structural,
            space_hash=entry.space_hash,
            t168_digest=entry.t168_digest,
            geom_hash=entry.geom_hash,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
        )
        bindings = build_candidate_rating_bindings(
            structural,
            space_hash=entry.space_hash,
            t168_digest=entry.t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
            geometry_projection_hash=entry.geom_hash,
        )
        hydraulic_dict: dict[str, Any] | None = None
        if bindings is not None and baseline.task027_pass:
            try:
                hrec = evaluate_v08_04_candidate_hydraulics(bindings, provider=provider)
                hydraulic_dict = {
                    "hard_gate": asdict(hrec.hard_gate),
                    "k_scenarios": [asdict(k) for k in hrec.k_scenarios],
                    "ports": list(hrec.ports),
                    "task174_partial_tube_dp_pa": hrec.task174_partial_tube_dp_pa,
                    "task174_partial_shell_dp_pa": hrec.task174_partial_shell_dp_pa,
                    "result_hash": hrec.result_hash,
                }
            except (ValueError, TypeError):
                hydraulic_dict = None
        qclass, trace, formal_ok, exp_ok = _classify_candidate(
            baseline, hydraulic_payload=hydraulic_dict, design_spec=spec
        )
        scores = _ranking_scores(baseline, hydraulic_dict, spec)
        qual_records.append(
            CandidateQualificationRecord(
                candidate_id=baseline.candidate_id,
                layout_key=baseline.layout_key,
                qualification_class=qclass,
                formal_engineering_eligible=formal_ok and PRODUCTION_RATING_VALIDATED,
                experimental_prescreen_eligible=exp_ok,
                baseline=baseline,
                hydraulic_v08_04=hydraulic_dict,
                design_specification=spec,
                rejection_trace=trace,
                ranking_scores=scores,
                convergence_status="EXPERIMENTAL_PRESCREEN_NOT_TASK173",
                authority_tier="ASSUMPTION_K_AND_EPSILON_NTU_PRESCREEN",
            )
        )
    top_lists = _build_top_n(tuple(qual_records), top_n=top_n)
    exp_count = len([c for c in qual_records if c.experimental_prescreen_eligible])
    outcome, detail = _case_outcome(
        True,
        (),
        tool.structural_candidates_generated,
        exp_count,
    )
    norm_hash = canonical_sha256(
        {
            "engineering_case_id": normalized.engineering_case_id,
            "handoff_hash": handoff.normalized_input_hash,
            "target_duty_w": str(normalized.target_duty_w),
        }
    )
    stable = {
        "task_id": TASK_ID,
        "case_outcome": outcome,
        "top_n": asdict(top_lists),
        "candidates": [
            {
                "candidate_id": c.candidate_id,
                "qualification_class": c.qualification_class,
                "ranking_scores": c.ranking_scores,
                "rejection_trace": list(c.rejection_trace),
            }
            for c in qual_records
        ],
        "normalization_hash": norm_hash,
        "ranking_method": _RANKING_METHOD,
    }
    report_hash = canonical_sha256(stable)
    return V08_05EngineeringReport(
        task_id=TASK_ID,
        task_name=TASK_NAME,
        engineering_design_status=ENGINEERING_DESIGN_STATUS,
        production_rating_validated=PRODUCTION_RATING_VALIDATED,
        v08_03_engineering_acceptance=V08_03_ENGINEERING_ACCEPTANCE,
        case_outcome=outcome,
        case_outcome_detail=detail,
        top_n=top_lists,
        candidates=tuple(qual_records),
        normalization_hash=norm_hash,
        design_tool_result_hash=tool.result_hash,
        report_hash=report_hash,
        design_tool_mirror=tool,
    )


def merged_web_api_payload(report: V08_05EngineeringReport) -> dict[str, Any]:
    """Legacy web fields from design tool mirror + V08-05 qualification overlay."""
    from prototypes.v08_thermal_rating.v08_autonomous_design_tool import (
        report_to_json_dict,
    )

    tool = report.design_tool_mirror
    if tool is None:
        return v08_05_report_to_json(report)
    payload = report_to_json_dict(tool)
    payload["v08_05"] = v08_05_report_to_json(report)
    payload["case_outcome"] = report.case_outcome
    payload["formal_top_n"] = list(report.top_n.formal_engineering)
    payload["experimental_top_n"] = list(report.top_n.experimental_prescreen)
    return payload


def render_v08_05_markdown(report: V08_05EngineeringReport) -> str:
    lines = [
        f"# {TASK_ID} — {TASK_NAME}",
        "",
        f"**Case outcome:** `{report.case_outcome}` — {report.case_outcome_detail}",
        f"**Production rating validated:** {report.production_rating_validated}",
        f"**Formal Top-N:** {list(report.top_n.formal_engineering) or '[] (none — production gate off)'}",
        f"**Experimental Top-N:** {list(report.top_n.experimental_prescreen) or '[]'}",
        "",
        "## Ranking method",
        "",
        report.top_n.tie_break_rule,
        _RANKING_METHOD,
        "",
        "## Candidates",
        "",
    ]
    for c in report.candidates:
        lines.append(f"### `{c.layout_key}` ({c.candidate_id[:8]}…)")
        lines.append(f"- Qualification: **{c.qualification_class}**")
        lines.append(f"- Rejection trace: {', '.join(c.rejection_trace) or 'none'}")
        lines.append(
            f"- Scores: duty {c.ranking_scores.get('duty_w')} W, margin {c.ranking_scores.get('min_high_tier_margin_pa')} Pa"
        )
        if c.design_specification:
            th = c.design_specification.get("thermal_experimental_prescreen") or {}
            lines.append(
                f"- Thermal (prescreen): Q={th.get('clean_q_w')} W, U·A={th.get('overall_ua_w_per_k')} W/K"
            )
        if c.hydraulic_v08_04:
            hg = c.hydraulic_v08_04.get("hard_gate") or {}
            lines.append(
                f"- Hydraulic gate: tube={hg.get('tube_full_path')} shell={hg.get('shell_full_path')} "
                f"nozzle={hg.get('four_nozzle_velocity')}"
            )
        lines.append("")
    lines.extend(
        [
            "## Applicability",
            "",
            f"- Authority: {report.candidates[0].authority_tier if report.candidates else 'N/A'}",
            f"- Report hash: `{report.report_hash}`",
        ]
    )
    return "\n".join(lines)


def v08_05_report_to_json(report: V08_05EngineeringReport) -> dict[str, Any]:
    return {
        "schema": "hxforge.v08-05-engineering-report.v1",
        "task_id": report.task_id,
        "task_name": report.task_name,
        "engineering_design_status": report.engineering_design_status,
        "production_rating_validated": report.production_rating_validated,
        "v08_03_engineering_acceptance": report.v08_03_engineering_acceptance,
        "v08_04_module_acceptance": True,
        "v08_04_formal_acceptance": False,
        "case_outcome": report.case_outcome,
        "case_outcome_detail": report.case_outcome_detail,
        "top_n": asdict(report.top_n),
        "ranking_method_documentation": _RANKING_METHOD,
        "candidates": [
            {
                "candidate_id": c.candidate_id,
                "layout_key": c.layout_key,
                "qualification_class": c.qualification_class,
                "formal_engineering_eligible": c.formal_engineering_eligible,
                "experimental_prescreen_eligible": c.experimental_prescreen_eligible,
                "baseline": asdict(c.baseline),
                "hydraulic_v08_04": c.hydraulic_v08_04,
                "design_specification": c.design_specification,
                "rejection_trace": list(c.rejection_trace),
                "ranking_scores": c.ranking_scores,
                "convergence_status": c.convergence_status,
                "authority_tier": c.authority_tier,
            }
            for c in report.candidates
        ],
        "normalization_hash": report.normalization_hash,
        "design_tool_result_hash": report.design_tool_result_hash,
        "report_hash": report.report_hash,
    }


def write_v08_05_artifact(path: Path | None = None, **kwargs: Any) -> dict[str, Any]:
    from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330

    text = FIXTURE_330.read_text(encoding="utf-8")
    report = run_v08_05_qualified_selection(text, **kwargs)
    payload = v08_05_report_to_json(report)
    out = path or Path("/opt/cursor/artifacts/v08_05_engineering_report_sample.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


__all__ = [
    "TASK_ID",
    "V08_05EngineeringReport",
    "run_v08_05_qualified_selection",
    "render_v08_05_markdown",
    "v08_05_report_to_json",
    "write_v08_05_artifact",
]
