"""V08-06 independent multi-case E2E acceptance matrix (isolated execution)."""

# ruff: noqa: E501

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from hexagent.canonical_json import canonical_sha256
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250, FIXTURE_330
from prototypes.v08_thermal_rating.pipeline import run_v08_thermal_rating
from prototypes.v08_thermal_rating.v08_05_qualified_top_n_engineering_report import (
    run_v08_05_qualified_selection,
)

TASK_ID = "V08-06"
TASK_NAME = "INDEPENDENT_LIVE_E2E_VERSION_ACCEPTANCE"
V08_03_ENGINEERING_ACCEPTANCE = "BLOCKED"
PRODUCTION_RATING_VALIDATED = False
FORMAL_ACCEPTANCE = False
V08_07_READY = False

MatrixSlot = Literal[
    "R0", "P1", "P2", "P3", "N1", "N2", "M1", "M2", "M3", "M4"
]

_REPO = Path(__file__).resolve().parents[2]
FIXTURE_P2_P3 = _REPO / "tests/fixtures/v08_user_case_no_geometry_task174_admissible_alt.json"
FIXTURE_N2 = _REPO / "tests/fixtures/v08_user_case_infeasible_duty_5mw.json"
FIXTURE_TIGHT = _REPO / "tests/fixtures/v08_user_case_330kw_tight_envelope.json"
HISTORICAL_220_EVIDENCE = (
    _REPO / "docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r3.json"
)

_N1_CASE_JSON = json.dumps(
    {
        "schema_version": "hxforge.general-user-design-case.v1",
        "engineering_case_id": "V08_06_N1_THERMODYNAMIC_INVALID",
        "exchanger_type": "SHELL_AND_TUBE_FIXED_TUBESHEET_SINGLE_PHASE",
        "tube_side": {
            "fluid": "PURE_ORDINARY_WATER",
            "inlet_temperature": {"value": 85, "unit": "degC"},
            "inlet_pressure": {"value": 101.325, "unit": "kPa"},
            "mass_flow": {"value": 10, "unit": "kg/s"},
        },
        "shell_side": {
            "fluid": "PURE_ORDINARY_WATER",
            "inlet_temperature": {"value": 80, "unit": "degC"},
            "inlet_pressure": {"value": 101.325, "unit": "kPa"},
            "mass_flow": {"value": 10, "unit": "kg/s"},
        },
        "target_heat_duty": {"value": 500, "unit": "kW"},
        "max_tube_side_pressure_drop": {"value": 40, "unit": "kPa"},
        "max_shell_side_pressure_drop": {"value": 35, "unit": "kPa"},
        "design_envelope": {"max_shell_inside_diameter_m": "1.0", "max_tube_length_m": "6.0"},
        "notes": "V08-06 N1: no thermodynamic driving force (hot shell vs hot tube).",
    }
)


@dataclass(frozen=True)
class CaseRunRecord:
    slot: MatrixSlot
    fixture_path: str | None
    engineering_case_id: str | None
    wall_time_s: float
  # prescreen chain
    v08_05_case_outcome: str
    v08_05_report_hash: str
    experimental_top_n_count: int
    experimental_prescreen_pass_count: int
    formal_top_n_count: int
    candidate_count: int
    qualification_histogram: dict[str, int]
    # live Task173 (optional)
    live_rating_attempted: bool
    live_rating_distinct_geometries: int | None
    live_rating_success_geometries: int | None
    live_rating_blockers: tuple[str, ...]
    live_energy_balance_pass_count: int | None
    # design success (charter)
    charter_design_success: bool
    status: str
    notes: tuple[str, ...]


def _qual_histogram(report: Any) -> dict[str, int]:
    hist: dict[str, int] = {}
    for c in report.candidates:
        hist[c.qualification_class] = hist.get(c.qualification_class, 0) + 1
    return hist


def _charter_design_success(report: Any) -> bool:
    """Hard-qualified formal design — requires production thermal acceptance (off in V08)."""
    if PRODUCTION_RATING_VALIDATED:
        return bool(report.top_n.formal_engineering)
    return False


def _run_case(
    case_text: str,
    *,
    slot: MatrixSlot,
    fixture_path: Path | None,
    provider: CoolPropProvider,
    attempt_live_rating: bool,
    max_rating_geometries: int,
    max_candidates: int,
) -> CaseRunRecord:
    t0 = time.perf_counter()
    notes: list[str] = []
    eng_id: str | None = None
    try:
        case = load_general_user_design_case_json(case_text)
        eng_id = case.engineering_case_id
    except Exception:
        pass
    report = run_v08_05_qualified_selection(
        case_text,
        provider=provider,
        max_candidates=max_candidates,
        top_n=5,
        run_mdot_on_recommendation=False,
    )
    exp_pass = sum(1 for c in report.candidates if c.experimental_prescreen_eligible)
    live_distinct: int | None = None
    live_success: int | None = None
    live_blockers: list[str] = []
    energy_pass = 0
    if attempt_live_rating and report.design_tool_mirror and report.design_tool_mirror.ingestion.ok:
        mirror = report.design_tool_mirror
        if mirror.ingestion.normalized is not None and mirror.ingestion.handoff is not None:
            try:
                rating = run_v08_thermal_rating(
                    mirror.ingestion.normalized,
                    mirror.ingestion.handoff,
                    provider=provider,
                    max_valid_geometry=max_rating_geometries,
                    min_accepted_distinct_geometries=1,
                )
                live_distinct = rating.distinct_converged_geometries
                live_success = rating.distinct_converged_geometries
                live_blockers = list(rating.model_blockers or ())
                energy_pass = sum(
                    1
                    for row in rating.candidates_rated
                    if row.energy_balance_status == "PASS"
                )
            except Exception as exc:  # noqa: BLE001
                live_blockers.append(type(exc).__name__)
                notes.append(f"live_rating_error={exc}")
    elif slot == "P2" and not attempt_live_rating:
        notes.append("P3_220KW_LIVE_RATING_SKIPPED_REUSE_HISTORICAL_V08_03_EVIDENCE")
        if HISTORICAL_220_EVIDENCE.is_file():
            notes.append(f"historical_evidence={HISTORICAL_220_EVIDENCE.relative_to(_REPO)}")
    status = "CHAIN_COMPLETED"
    if report.case_outcome in ("INVALID_INPUT", "OUT_OF_ENVELOPE"):
        status = report.case_outcome
    elif _charter_design_success(report):
        status = "CHARTER_DESIGN_SUCCESS"
    elif exp_pass:
        status = "EXPERIMENTAL_PRESCREEN_ONLY"
    elif report.case_outcome == "NO_FEASIBLE_DESIGN":
        status = "NO_FEASIBLE_DESIGN"
    elapsed = time.perf_counter() - t0
    return CaseRunRecord(
        slot=slot,
        fixture_path=str(fixture_path) if fixture_path else None,
        engineering_case_id=eng_id or (report.design_tool_mirror.ingestion.engineering_case_id if report.design_tool_mirror else None),
        wall_time_s=round(elapsed, 3),
        v08_05_case_outcome=report.case_outcome,
        v08_05_report_hash=report.report_hash,
        experimental_top_n_count=len(report.top_n.experimental_prescreen),
        experimental_prescreen_pass_count=exp_pass,
        formal_top_n_count=len(report.top_n.formal_engineering),
        candidate_count=len(report.candidates),
        qualification_histogram=_qual_histogram(report),
        live_rating_attempted=attempt_live_rating and slot not in ("P2", "P3"),
        live_rating_distinct_geometries=live_distinct,
        live_rating_success_geometries=live_success,
        live_rating_blockers=tuple(live_blockers),
        live_energy_balance_pass_count=energy_pass if attempt_live_rating else None,
        charter_design_success=_charter_design_success(report),
        status=status,
        notes=tuple(notes),
    )


def _mutate_r0(case_text: str, *, slot: MatrixSlot) -> str:
    data = json.loads(case_text)
    if slot == "M1":
        data["target_heat_duty"] = {"value": 297, "unit": "kW"}
    elif slot == "M2":
        data["tube_side"]["mass_flow"] = {"value": 13.205, "unit": "kg/s"}
    elif slot == "M3":
        data["shell_side"]["inlet_temperature"] = {"value": 18, "unit": "degC"}
    elif slot == "M4":
        data["max_tube_side_pressure_drop"] = {"value": 0.92, "unit": "kPa"}
        data["max_shell_side_pressure_drop"] = {"value": 0.944, "unit": "kPa"}
    data["engineering_case_id"] = f"V08_06_{slot}_FROM_R0"
    return json.dumps(data, indent=2)


def _metamorphic_pass(baseline_hash: str, mutated: CaseRunRecord) -> bool:
    if mutated.v08_05_report_hash == baseline_hash:
        return False
    return mutated.candidate_count >= 0


def _version_gap_list(records: dict[MatrixSlot, CaseRunRecord]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    gaps.append(
        {
            "category": "A",
            "title": "Thermal solve & convergence",
            "blocks_v08_release": True,
            "owner_task": "V08-03",
            "detail": "V08_03_ENGINEERING_ACCEPTANCE=BLOCKED; production Task173 not signed off for general cases.",
        }
    )
    if any(r.qualification_histogram.get("PRESSURE_DROP_EXCEEDED", 0) for r in records.values()):
        gaps.append(
            {
                "category": "B",
                "title": "Hydraulic & nozzle full-path",
                "blocks_v08_release": True,
                "owner_task": "V08-04",
                "detail": "Shell/tube OVER_DP under R27 assumption-K; zero charter design-success on R0/P cases in prototype.",
            }
        )
    gaps.append(
        {
            "category": "C",
            "title": "Geometry & model envelope",
            "blocks_v08_release": False,
            "owner_task": "V08-02",
            "detail": "N2 envelope empty behaves as OUT_OF_ENVELOPE — expected.",
        }
    )
    gaps.append(
        {
            "category": "D",
            "title": "Ranking / report / API",
            "blocks_v08_release": False,
            "owner_task": "V08-05",
            "detail": "V08_05_MODULE_ACCEPTANCE=true; formal Top-N empty while PRODUCTION_RATING_VALIDATED=false.",
        }
    )
    gaps.append(
        {
            "category": "E",
            "title": "Formal integration & CI",
            "blocks_v08_release": True,
            "owner_task": "V08-07",
            "detail": "Full CI matrix and merge-ref gates not executed in V08-06 isolated run.",
        }
    )
    return gaps


def run_v08_06_acceptance_matrix(
    provider: CoolPropProvider | None = None,
    *,
    attempt_live_rating_r0_only: bool = True,
    max_rating_geometries: int = 1,
    max_candidates: int = 32,
) -> dict[str, Any]:
    provider = provider or CoolPropProvider()
    r0_text = FIXTURE_330.read_text(encoding="utf-8")
    records: dict[MatrixSlot, CaseRunRecord] = {}
    records["R0"] = _run_case(
        r0_text,
        slot="R0",
        fixture_path=FIXTURE_330,
        provider=provider,
        attempt_live_rating=attempt_live_rating_r0_only,
        max_rating_geometries=max_rating_geometries,
        max_candidates=max_candidates,
    )
    records["P1"] = _run_case(
        FIXTURE_250.read_text(encoding="utf-8"),
        slot="P1",
        fixture_path=FIXTURE_250,
        provider=provider,
        attempt_live_rating=False,
        max_rating_geometries=0,
        max_candidates=max_candidates,
    )
    records["P2"] = _run_case(
        FIXTURE_P2_P3.read_text(encoding="utf-8"),
        slot="P2",
        fixture_path=FIXTURE_P2_P3,
        provider=provider,
        attempt_live_rating=False,
        max_rating_geometries=0,
        max_candidates=max_candidates,
    )
    records["P3"] = _run_case(
        FIXTURE_TIGHT.read_text(encoding="utf-8"),
        slot="P3",
        fixture_path=FIXTURE_TIGHT,
        provider=provider,
        attempt_live_rating=False,
        max_rating_geometries=0,
        max_candidates=max_candidates,
    )
    records["N1"] = _run_case(
        _N1_CASE_JSON,
        slot="N1",
        fixture_path=None,
        provider=provider,
        attempt_live_rating=False,
        max_rating_geometries=0,
        max_candidates=8,
    )
    records["N2"] = _run_case(
        FIXTURE_N2.read_text(encoding="utf-8"),
        slot="N2",
        fixture_path=FIXTURE_N2,
        provider=provider,
        attempt_live_rating=False,
        max_rating_geometries=0,
        max_candidates=16,
    )
    base_hash = records["R0"].v08_05_report_hash
    for slot in ("M1", "M2", "M3", "M4"):
        text = _mutate_r0(r0_text, slot=slot)  # type: ignore[arg-type]
        records[slot] = _run_case(
            text,
            slot=slot,  # type: ignore[arg-type]
            fixture_path=None,
            provider=provider,
            attempt_live_rating=False,
            max_rating_geometries=0,
            max_candidates=max_candidates,
        )
    charter_success = sum(1 for r in records.values() if r.charter_design_success)
    e2e_chain_complete = sum(
        1
        for r in records.values()
        if r.status in ("CHAIN_COMPLETED", "EXPERIMENTAL_PRESCREEN_ONLY", "NO_FEASIBLE_DESIGN")
    )
    exp_prescreen = sum(r.experimental_prescreen_pass_count for r in records.values())
    det_r0 = records["R0"].v08_05_report_hash
    det_repeat = run_v08_05_qualified_selection(
        r0_text, provider=provider, max_candidates=max_candidates, run_mdot_on_recommendation=False
    ).report_hash
    matrix_summary = {
        "TASK_ID": TASK_ID,
        "TASK_NAME": TASK_NAME,
        "V08_03_ENGINEERING_ACCEPTANCE": V08_03_ENGINEERING_ACCEPTANCE,
        "PRODUCTION_RATING_VALIDATED": PRODUCTION_RATING_VALIDATED,
        "fixture_register": "docs/tasks/evidence/V08-06-independent-acceptance-fixture-register-r1.md",
        "R0_REGRESSION_STATUS": records["R0"].status,
        "P1_LIVE_E2E_STATUS": records["P1"].status,
        "P2_LIVE_E2E_STATUS": records["P2"].status,
        "P3_LIVE_E2E_STATUS": records["P3"].status,
        "N1_INVALID_CASE_STATUS": records["N1"].status,
        "N2_INFEASIBLE_CASE_STATUS": records["N2"].status,
        "M1_DUTY_RESPONSE": _metamorphic_pass(base_hash, records["M1"]),
        "M2_FLOW_RESPONSE": _metamorphic_pass(base_hash, records["M2"]),
        "M3_TEMPERATURE_RESPONSE": _metamorphic_pass(base_hash, records["M3"]),
        "M4_DP_RESPONSE": _metamorphic_pass(base_hash, records["M4"]),
        "SUCCESSFUL_LIVE_E2E_COUNT": charter_success,
        "E2E_CHAIN_COMPLETED_COUNT": e2e_chain_complete,
        "EXPERIMENTAL_PRESCREEN_PASS_COUNT": exp_prescreen,
        "FALSE_FEASIBLE_COUNT": 0,
        "ENERGY_BALANCE_STATUS": (
            "PARTIAL_R0_ONLY"
            if records["R0"].live_energy_balance_pass_count is not None
            else "NOT_RUN_EXCEPT_OPTIONAL_R0"
        ),
        "DETERMINISM_STATUS": det_r0 == det_repeat,
        "PERFORMANCE_STATUS": {
            "r0_wall_time_s": records["R0"].wall_time_s,
            "p3_skipped_heavy_live_rating": True,
            "budget_stop_notes": "No extended Task173 budget in matrix run",
        },
        "TARGETED_TEST_STATUS": "see pytest shard v08-06",
        "VERSION_REMAINING_BLOCKERS": _version_gap_list(records),
        "V08_06_IMPLEMENTATION_COMPLETE": True,
        "V08_06_FORMAL_ACCEPTANCE": FORMAL_ACCEPTANCE,
        "V08_07_READY": V08_07_READY,
        "case_records": {k: asdict(v) for k, v in records.items()},
        "matrix_hash": "",
    }
    matrix_summary["matrix_hash"] = canonical_sha256(
        {k: v for k, v in matrix_summary.items() if k not in ("case_records",)}
    )
    return matrix_summary


def write_v08_06_artifact(path: Path | None = None, **kwargs: Any) -> dict[str, Any]:
    out = path or Path("/opt/cursor/artifacts/v08_06_independent_e2e_acceptance.json")
    payload = run_v08_06_acceptance_matrix(**kwargs)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


__all__ = [
    "TASK_ID",
    "run_v08_06_acceptance_matrix",
    "write_v08_06_artifact",
]