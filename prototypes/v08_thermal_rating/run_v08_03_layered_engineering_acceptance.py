#!/usr/bin/env python3
"""V08-03 LAYERED_ENGINEERING_ACCEPTANCE_IMPLEMENTATION closeout."""

# ruff: noqa: E402

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    load_case_bindings,
    resolve_candidate_bindings_by_id,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250
from prototypes.v08_thermal_rating.engineering_physical_evaluator_v08 import (
    load_frozen_330_evidence,
    run_negative_controls_via_evaluator,
)
from prototypes.v08_thermal_rating.shadow_layered_acceptance import ORIGINAL_PRODUCTION_ACCEPTANCE
from prototypes.v08_thermal_rating.v08_layered_engineering_acceptance_v1 import (
    CONTRACT_ID,
    evaluate_dual_contract,
    run_layered_negative_controls,
)

OUT = Path("/opt/cursor/artifacts/v08_03_layered_engineering_acceptance_v1.json")
CANDIDATES = (
    "e1baa795-9cf5-5718-8fa8-0688d2102c5c",
    "9277ebb8-5b05-5130-8b90-92ee4768606b",
)
FROZEN_NEG = _REPO / "tests/fixtures/v08_03_frozen_330kw_engineering_evidence.json"


def _json_ready(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return _json_ready(asdict(value))
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


def _v07_golden() -> str:
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/exchangers/shell_tube/test_task173_integrated_rating.py::test_task172_support_identity_and_roundoff_floor_replay",
                "tests/prototypes/test_engineering_acceptance_decision_v08.py::test_negative_controls_on_real_evaluator",
                "-q",
                "--timeout=300",
            ],
            cwd=_REPO,
            check=True,
            capture_output=True,
        )
        return "PASS"
    except subprocess.CalledProcessError as exc:
        return f"FAIL:{exc.returncode}"


def _layer_status(verdict: Any, key: str) -> str:
    for layer in verdict.layers:
        if layer.layer == key:
            return layer.status
    return "NOT_EVALUATED"


def main() -> int:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_250, provider=provider)
    candidate_rows: list[dict[str, Any]] = []
    geometries: set[str] = set()
    experimental_success = 0

    for _idx, cid in enumerate(CANDIDATES):
        bindings = resolve_candidate_bindings_by_id(
            cid, normalized, handoff, provider, max_valid=32
        )
        if bindings is None:
            candidate_rows.append({"candidate_id": cid, "status": "NOT_FOUND"})
            continue
        run_prod = True
        verdict = evaluate_dual_contract(
            bindings,
            provider,
            run_production_rating=run_prod,
        )
        if verdict.experimental_engineering_acceptance == "PASS":
            experimental_success += 1
            geometries.add(verdict.geometry_projection_hash)
        candidate_rows.append(_json_ready(verdict))

    layered_template = evaluate_dual_contract(
        resolve_candidate_bindings_by_id(
            CANDIDATES[0], normalized, handoff, provider, max_valid=32
        ),
        provider,
        run_production_rating=False,
    )
    layered_neg = run_layered_negative_controls(layered_template)

    frozen330 = load_frozen_330_evidence(FROZEN_NEG)
    eng_neg = run_negative_controls_via_evaluator(
        frozen330, tp_ph_query_status=frozen330.raw.get("tp_ph_query_status", "PASS")
    )

    candidate_rows[-1] if candidate_rows else {}
    candidate_rows[0] if candidate_rows else {}

    payload: dict[str, Any] = {
        "TASK_ID": "V08-03",
        "EXECUTION_STAGE": "LAYERED_ENGINEERING_ACCEPTANCE_IMPLEMENTATION",
        "LAYERED_CONTRACT_ID": CONTRACT_ID,
        "ORIGINAL_PRODUCTION_MODE": ORIGINAL_PRODUCTION_ACCEPTANCE,
        "ERROR_BUDGET_INDEPENDENTLY_DERIVED": True,
        "LAYERED_CONTRACT_IMPLEMENTED": True,
        "fixtures_note": "Use per-candidate rows below for layer statuses",
        "candidates": candidate_rows,
        "aggregate": {
            "L1_LOCAL_CONSTITUTIVE_STATUS": [
                _layer_status_from_row(r, "L1") for r in candidate_rows
            ],
            "L2_PROPERTY_CONSISTENCY_STATUS": [
                _layer_status_from_row(r, "L2") for r in candidate_rows
            ],
            "L3_GLOBAL_ENERGY_BALANCE_STATUS": [
                _layer_status_from_row(r, "L3") for r in candidate_rows
            ],
            "L3_MESH_CONVERGENCE_STATUS": [
                _layer_metric_from_row(r, "L3", "mesh_convergence_all_accepted")
                for r in candidate_rows
            ],
            "L4_ENGINEERING_FEASIBILITY_STATUS": [
                _layer_status_from_row(r, "L4") for r in candidate_rows
            ],
            "ORIGINAL_PRODUCTION_ACCEPTANCE": [
                r.get("original_production_acceptance") for r in candidate_rows
            ],
            "EXPERIMENTAL_ENGINEERING_ACCEPTANCE": [
                r.get("experimental_engineering_acceptance") for r in candidate_rows
            ],
        },
        "SUCCESSFUL_DISTINCT_GEOMETRY_COUNT": len(geometries),
        "LAYERED_NEGATIVE_CONTROLS": _json_ready(layered_neg),
        "ENGINEERING_PHYSICAL_NEGATIVE_CONTROLS_SYNTHETIC_330": {
            "fixture": str(FROZEN_NEG.relative_to(_REPO)),
            "status": eng_neg.status,
            "note": "Synthetic 330kW frozen bundle — not a 250kW acceptance case",
        },
        "FALSE_ACCEPTANCE_NEGATIVE_CONTROL_COUNT": layered_neg.false_acceptance_count
        + (0 if eng_neg.status == "PASS" else 1),
        "V07_GOLDEN_REGRESSION_STATUS": _v07_golden(),
        "PROPOSED_CONTRACT_MIGRATION_READY": layered_neg.status == "PASS",
        "STOP": experimental_success == 0,
        "STOP_REASON": (
            "No candidate reached experimental L1–L4 PASS under V1; "
            "original production remains authoritative."
            if experimental_success == 0
            else None
        ),
    }
    if candidate_rows:
        first = candidate_rows[0]
        payload["L1_LOCAL_CONSTITUTIVE_STATUS"] = _layer_status_from_row(first, "L1")
        payload["L2_PROPERTY_CONSISTENCY_STATUS"] = _layer_status_from_row(first, "L2")
        payload["L3_GLOBAL_ENERGY_BALANCE_STATUS"] = _layer_status_from_row(first, "L3")
        payload["L3_MESH_CONVERGENCE_STATUS"] = _layer_metric_from_row(
            first, "L3", "mesh_convergence_all_accepted"
        )
        payload["L4_ENGINEERING_FEASIBILITY_STATUS"] = _layer_status_from_row(first, "L4")
        payload["ORIGINAL_PRODUCTION_ACCEPTANCE"] = first.get("original_production_acceptance")
        payload["EXPERIMENTAL_ENGINEERING_ACCEPTANCE"] = first.get(
            "experimental_engineering_acceptance"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


def _layer_status_from_row(row: dict[str, Any], layer: str) -> str:
    for item in row.get("layers", []):
        if item.get("layer") == layer:
            return str(item.get("status", "NOT_EVALUATED"))
    return "NOT_EVALUATED"


def _layer_metric_from_row(row: dict[str, Any], layer: str, key: str) -> Any:
    for item in row.get("layers", []):
        if item.get("layer") == layer:
            return item.get("metrics", {}).get(key)
    return None


if __name__ == "__main__":
    raise SystemExit(main())