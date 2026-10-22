"""R14: live thermal state hydraulic post-pass (experimental, opt-in)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_constraint_preview import (
    build_experimental_constraint_preview,
)
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    HYDRAULIC_STATUS_LIVE_POSTPASS,
    LIVE_THERMAL_HYDRAULIC_AUTHORITY_ID,
    run_live_thermal_state_hydraulic_postpass,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import NativeCellContext

_CASE = Path("prototypes/v07_general_rating_sizing_mvp/cases/mvp_variable_bundle_r13.json")
_R13_EVIDENCE = Path(
    "docs/tasks/evidence/V07-GENERAL-VARIABLE-BUNDLE-GEOMETRY-SIZING-R13/CANDIDATE_RATING_RESULTS.json"
)
_PINNED_CANDIDATE = "a409a550-4d1d-5b71-b3f5-0f1b665e2fe5"


@pytest.fixture(scope="module")
def r13_case():
    return load_general_engineering_case_json(_CASE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pinned_row() -> dict:
    doc = json.loads(_R13_EVIDENCE.read_text(encoding="utf-8"))
    for row in doc["candidates"]:
        if row["candidate_id"] == _PINNED_CANDIDATE:
            return row
    raise RuntimeError("pinned R13 candidate missing from evidence")


def test_legacy_constraint_preview_unchanged_semantics(r13_case, pinned_row) -> None:
    native = NativeCellContext(
        candidate_id=_PINNED_CANDIDATE,
        candidate_hash=pinned_row["candidate_hash"],
        rating_request_hash=pinned_row["rating_request_hash"],
        task171_result_hash=pinned_row["task171_result_hash"],
        task174_result_hash=pinned_row["task174_result_hash"],
        task025_parallel_area_m2=pinned_row["task025_parallel_area_m2"],
        physical_tube_count=pinned_row["bundle_geometry"]["physical_tube_count"],
        modeled_tube_side_pressure_drop_pa=pinned_row["constraint_preview"]["modeled_tube_dp_pa"],
        modeled_shell_side_pressure_drop_pa=pinned_row["constraint_preview"]["modeled_shell_dp_pa"],
        context=None,
        support=None,
        shell_authority=None,
    )
    preview = build_experimental_constraint_preview(
        r13_case,
        mesh={
            "status": "NUMERIC_VALID",
            "total_duty_w": pinned_row["total_duty_w"],
        },
        native=native,
    )
    assert preview["task174_hydraulic_status"] == "HYDRAULIC_REFERENCE_MODEL_PREVIEW"
    assert preview["shell_dp_constraint"] == "SATISFIED"


def test_live_postpass_recomputes_shell_dp_for_r13_pinned_candidate(r13_case, pinned_row) -> None:
    result = run_live_thermal_state_hydraulic_postpass(
        r13_case,
        candidate_id=_PINNED_CANDIDATE,
        tube_inlet_temperature_k=Decimal("299.70"),
        tube_outlet_temperature_k=Decimal(str(pinned_row["tube_outlet_temperature_k"])),
        shell_inlet_temperature_k=Decimal("298.15"),
        shell_outlet_temperature_k=Decimal(str(pinned_row["shell_outlet_temperature_k"])),
        tube_inlet_pressure_pa=Decimal("101325"),
        shell_inlet_pressure_pa=Decimal("101325"),
    )
    assert result["authority_id"] == LIVE_THERMAL_HYDRAULIC_AUTHORITY_ID
    assert result["task174_hydraulic_status"] == HYDRAULIC_STATUS_LIVE_POSTPASS
    assert result["hydraulic_constraint_status"] == "SATISFIED"
    ref_shell = Decimal(result["reference_shell_dp_pa"])
    live_shell = Decimal(result["recalculated_shell_dp_pa"])
    assert ref_shell != live_shell
    assert live_shell < Decimal("1180")
    assert result["physical_tube_count"] == 337


def test_case_flag_defaults_false(r13_case) -> None:
    assert r13_case.experimental_live_thermal_hydraulic_postpass is False
