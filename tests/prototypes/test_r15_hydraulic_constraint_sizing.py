"""R15: live hydraulic post-pass drives sizing eligibility and ranking."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_candidate_eligibility import (
    constraint_satisfied_ids,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_hydraulic_constraint_decision import (
    HYDRAULIC_DECISION_SOURCE_LIVE,
    HYDRAULIC_DECISION_SOURCE_REFERENCE,
    build_hydraulic_constraint_decision,
)
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    run_live_thermal_state_hydraulic_postpass,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_CASE = REPO_ROOT / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_variable_bundle_r13.json"
_R13_EVIDENCE = REPO_ROOT / (
    "docs/tasks/evidence/V07-GENERAL-VARIABLE-BUNDLE-GEOMETRY-SIZING-R13/"
    "CANDIDATE_RATING_RESULTS.json"
)
_PINNED = "a409a550-4d1d-5b71-b3f5-0f1b665e2fe5"
_R15_E2E_CASE = REPO_ROOT / "tests/fixtures/r15_live_hydraulic_single_candidate_case.json"


@pytest.fixture(scope="module")
def r13_case():
    return load_general_engineering_case_json(_CASE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pinned_row() -> dict:
    doc = json.loads(_R13_EVIDENCE.read_text(encoding="utf-8"))
    for row in doc["candidates"]:
        if row["candidate_id"] == _PINNED:
            return row
    raise RuntimeError("pinned candidate missing")


def _synthetic_row(
    pinned_row: dict,
    *,
    postpass: dict | None,
    preview_shell_constraint: str = "SATISFIED",
) -> dict:
    preview = dict(pinned_row["constraint_preview"])
    preview["shell_dp_constraint"] = preview_shell_constraint
    if preview_shell_constraint == "NOT_SATISFIED":
        preview["modeled_shell_dp_pa"] = "1200"
    return {
        "candidate_id": pinned_row["candidate_id"],
        "mesh_status": "NUMERIC_VALID",
        "total_duty_w": pinned_row["total_duty_w"],
        "constraint_preview": preview,
        "live_thermal_state_hydraulic_postpass": postpass,
    }


@pytest.fixture(scope="module")
def live_postpass_doc(r13_case, pinned_row) -> dict:
    return run_live_thermal_state_hydraulic_postpass(
        r13_case,
        candidate_id=_PINNED,
        tube_inlet_temperature_k=Decimal("299.70"),
        tube_outlet_temperature_k=Decimal(str(pinned_row["tube_outlet_temperature_k"])),
        shell_inlet_temperature_k=Decimal("298.15"),
        shell_outlet_temperature_k=Decimal(str(pinned_row["shell_outlet_temperature_k"])),
        tube_inlet_pressure_pa=Decimal("101325"),
        shell_inlet_pressure_pa=Decimal("101325"),
        reference_tube_dp_pa=pinned_row["constraint_preview"]["modeled_tube_dp_pa"],
        reference_shell_dp_pa=pinned_row["constraint_preview"]["modeled_shell_dp_pa"],
    )


def test_reference_fails_live_passes_at_1175_pa_limit(
    r13_case, pinned_row, live_postpass_doc
) -> None:
    case = r13_case.model_copy(
        update={
            "experimental_live_thermal_hydraulic_postpass": True,
            "max_shell_side_pressure_drop_pa": Decimal("1175"),
        }
    )
    row = _synthetic_row(pinned_row, postpass=live_postpass_doc)
    decision = build_hydraulic_constraint_decision(case, row, rating_status="NUMERIC_VALID")
    assert decision["hydraulic_decision_source"] == HYDRAULIC_DECISION_SOURCE_LIVE
    assert decision["REFERENCE_CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_FAILED"
    assert decision["LIVE_HYDRAULIC_CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_SATISFIED"
    assert decision["reference_vs_live_feasibility_changed"] is True
    ref_shell = Decimal(str(decision["reference_shell_dp_pa"]))
    live_shell = Decimal(str(decision["live_recalculated_shell_dp_pa"]))
    assert ref_shell > Decimal("1175")
    assert live_shell < Decimal("1175")


def test_reference_passes_live_fails_does_not_enter_feasible_set(
    r13_case, pinned_row, live_postpass_doc
) -> None:
    case = r13_case.model_copy(update={"experimental_live_thermal_hydraulic_postpass": True})
    failing = dict(live_postpass_doc)
    failing["recalculated_shell_dp_pa"] = "2000"
    failing["shell_dp_constraint"] = "NOT_SATISFIED"
    failing["hydraulic_constraint_status"] = "NOT_SATISFIED"
    row = _synthetic_row(
        pinned_row,
        postpass=failing,
        preview_shell_constraint="SATISFIED",
    )
    decision = build_hydraulic_constraint_decision(case, row, rating_status="NUMERIC_VALID")
    assert decision["REFERENCE_CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_SATISFIED"
    assert decision["LIVE_HYDRAULIC_CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_FAILED"
    assert decision["EFFECTIVE_CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_FAILED"
    assert (
        constraint_satisfied_ids(
            [
                {
                    "candidate_id": row["candidate_id"],
                    "CONSTRAINT_STATUS": decision["EFFECTIVE_CONSTRAINT_STATUS"],
                }
            ]
        )
        == []
    )


def test_live_mode_missing_postpass_fail_closed(r13_case, pinned_row) -> None:
    case = r13_case.model_copy(update={"experimental_live_thermal_hydraulic_postpass": True})
    row = _synthetic_row(pinned_row, postpass=None)
    decision = build_hydraulic_constraint_decision(case, row, rating_status="NUMERIC_VALID")
    assert decision["LIVE_HYDRAULIC_CONSTRAINT_STATUS"] == "NOT_EVALUATED"
    assert decision["EFFECTIVE_CONSTRAINT_STATUS"] == "NOT_EVALUATED"


def test_live_mode_blocked_postpass_fail_closed(r13_case, pinned_row, live_postpass_doc) -> None:
    case = r13_case.model_copy(update={"experimental_live_thermal_hydraulic_postpass": True})
    blocked = dict(live_postpass_doc)
    blocked["hydraulic_constraint_status"] = "BLOCKED"
    blocked["blockers"] = [{"code": "SYNTHETIC_BLOCK", "scope": "TEST", "detail": "R15"}]
    row = _synthetic_row(pinned_row, postpass=blocked)
    decision = build_hydraulic_constraint_decision(case, row, rating_status="NUMERIC_VALID")
    assert decision["LIVE_HYDRAULIC_CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_FAILED"
    assert decision["EFFECTIVE_CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_FAILED"


def test_legacy_mode_unchanged_when_flag_false(r13_case, pinned_row) -> None:
    row = _synthetic_row(pinned_row, postpass=None)
    decision = build_hydraulic_constraint_decision(r13_case, row, rating_status="NUMERIC_VALID")
    assert decision["hydraulic_decision_source"] == HYDRAULIC_DECISION_SOURCE_REFERENCE
    assert decision["LIVE_HYDRAULIC_CONSTRAINT_STATUS"] is None
    assert decision["EFFECTIVE_CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_SATISFIED"


def test_constraint_satisfied_ids_uses_live_effective_status(
    r13_case, pinned_row, live_postpass_doc
) -> None:
    case = r13_case.model_copy(
        update={
            "experimental_live_thermal_hydraulic_postpass": True,
            "max_shell_side_pressure_drop_pa": Decimal("1175"),
        }
    )
    row = _synthetic_row(pinned_row, postpass=live_postpass_doc)
    decision = build_hydraulic_constraint_decision(case, row, rating_status="NUMERIC_VALID")
    eligibility = [
        {
            "candidate_id": _PINNED,
            "CONSTRAINT_STATUS": decision["EFFECTIVE_CONSTRAINT_STATUS"],
        }
    ]
    assert _PINNED in constraint_satisfied_ids(eligibility)


@pytest.mark.timeout(1800)
def test_r15_live_hydraulic_e2e_single_rating() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "prototypes.v07_general_rating_sizing_mvp",
                "--input",
                str(_R15_E2E_CASE),
                "--output",
                str(out),
                "--mode",
                "experimental-live-rating",
                "--mesh",
                "1",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        eligibility = json.loads(
            (out / "EXPERIMENTAL_CANDIDATE_ELIGIBILITY.json").read_text(encoding="utf-8")
        )
        assert eligibility["HYDRAULIC_DECISION_SOURCE"] == HYDRAULIC_DECISION_SOURCE_LIVE
        rated = json.loads((out / "CANDIDATE_RATING_RESULTS.json").read_text())["candidates"]
        assert len(rated) == 1
        assert rated[0]["mesh_status"] == "NUMERIC_VALID"
        assert rated[0]["live_thermal_state_hydraulic_postpass"] is not None
        sizing = json.loads((out / "LIVE_HYDRAULIC_SIZING_DECISION.json").read_text())
        per = sizing["per_candidate"][0]
        assert per["REFERENCE_CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_FAILED"
        assert per["LIVE_HYDRAULIC_CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_SATISFIED"
        feasible = [
            c
            for c in eligibility["candidates"]
            if c["CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_SATISFIED"
        ]
        assert len(feasible) == 1
