"""R9 experimental live-rating CLI and scope gates."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_live_scope import (
    check_experimental_live_rating_scope,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_live_workflow import (
    run_experimental_live_rating_from_paths,
)

R9_CASE = (
    Path(__file__).resolve().parents[2]
    / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_tube_hot_shell_cold_r9.json"
)
R8C_CASE = (
    Path(__file__).resolve().parents[2]
    / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_tube_hot_shell_cold_r8c.json"
)


def test_scope_rejects_unverified_shell_inlet_temperature() -> None:
    case = load_general_engineering_case_json(R8C_CASE.read_text(encoding="utf-8"))
    code, detail = check_experimental_live_rating_scope(case)
    assert code == "INPUT_OUT_OF_SUPPORTED_SCOPE"
    assert detail is not None
    assert "298.15" in detail


def test_run_identity_distinguishes_tube_inlet_temperature() -> None:
    from prototypes.v07_general_rating_sizing_mvp.experimental_live_run_identity import (
        build_experimental_live_rating_run_identity,
    )

    case_r7 = load_general_engineering_case_json(
        (
            Path(__file__).resolve().parents[2]
            / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_tube_hot_shell_cold_r7.json"
        ).read_text(encoding="utf-8")
    )
    case_r9 = load_general_engineering_case_json(R9_CASE.read_text(encoding="utf-8"))
    binding_r7 = {
        "tube_inlet_temperature_k": "299.80",
        "shell_inlet_temperature_k": "298.15",
        "tube_inlet_enthalpy_j_kg": "1",
        "shell_inlet_enthalpy_j_kg": "2",
        "authority_id": "hxforge.experimental-thermal-boundary.v1",
    }
    binding_r9 = {
        "tube_inlet_temperature_k": "299.70",
        "shell_inlet_temperature_k": "298.15",
        "tube_inlet_enthalpy_j_kg": "1",
        "shell_inlet_enthalpy_j_kg": "2",
        "authority_id": "hxforge.experimental-thermal-boundary.v1",
    }
    common = {
        "native_candidate_id": "cand",
        "native_candidate_hash": "hash",
        "rating_request_hash": "req",
        "task171_result_hash": "t171",
        "task174_result_hash": "t174",
        "task025_parallel_area_m2": "1.0",
        "mesh_level": 1,
        "enable_ephemeral_tp_cache": False,
    }
    id_r7 = build_experimental_live_rating_run_identity(
        case=case_r7, thermal_boundary_binding_doc=binding_r7, **common
    )
    id_r9 = build_experimental_live_rating_run_identity(
        case=case_r9, thermal_boundary_binding_doc=binding_r9, **common
    )
    assert id_r7["EXPERIMENTAL_LIVE_RATING_RUN_HASH"] != id_r9["EXPERIMENTAL_LIVE_RATING_RUN_HASH"]


def test_r9_case_in_scope() -> None:
    case = load_general_engineering_case_json(R9_CASE.read_text(encoding="utf-8"))
    assert check_experimental_live_rating_scope(case) == ("IN_SCOPE", None)


@pytest.mark.timeout(600)
def test_r9_experimental_live_n1_cli_e2e() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        outcome = run_experimental_live_rating_from_paths(R9_CASE, out, mesh_level=1)
        assert outcome.status in {"EXPERIMENTAL_COMPLETE", "EXPERIMENTAL_BLOCKED"}
        raw = json.loads((out / "RAW_RESULT.json").read_text(encoding="utf-8"))
        assert raw.get("EXPERIMENTAL_LIVE_RATING_RUN_HASH")
        assert (out / "ENGINEERING_REPORT.json").is_file()
        assert (out / "EXPERIMENTAL_CONSTRAINT_PREVIEW.json").is_file()
        report = json.loads((out / "ENGINEERING_REPORT.json").read_text(encoding="utf-8"))
        assert report.get("experimental_constraint_preview") is not None
        if outcome.status == "EXPERIMENTAL_COMPLETE":
            assert (out / "REAL_N1_MESH_RESULT.json").is_file()
            mesh = json.loads((out / "REAL_N1_MESH_RESULT.json").read_text(encoding="utf-8"))
            assert mesh["status"] == "NUMERIC_VALID"
        else:
            assert (out / "REAL_N1_BLOCKED_RESULT.json").is_file()
