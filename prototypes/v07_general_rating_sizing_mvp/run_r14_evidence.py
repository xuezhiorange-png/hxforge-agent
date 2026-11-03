"""R14 evidence: live thermal state hydraulic post-pass on pinned R13 0.56 m candidate."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.live_thermal_hydraulic_connection_analysis import (
    build_live_thermal_hydraulic_connection_analysis,
)
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    run_live_thermal_state_hydraulic_postpass,
)

_REPO = Path(__file__).resolve().parents[2]
_CASE = _REPO / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_variable_bundle_r13.json"
_R13_ROWS = _REPO / (
    "docs/tasks/evidence/V07-GENERAL-VARIABLE-BUNDLE-GEOMETRY-SIZING-R13/"
    "CANDIDATE_RATING_RESULTS.json"
)
_PINNED = "a409a550-4d1d-5b71-b3f5-0f1b665e2fe5"
_EVIDENCE = _REPO / "docs/tasks/evidence/V07-LIVE-THERMAL-STATE-HYDRAULIC-EVALUATION-R14"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(output_dir: Path) -> dict[str, Any]:
    t0 = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    case = load_general_engineering_case_json(_CASE.read_text(encoding="utf-8"))
    rows = json.loads(_R13_ROWS.read_text(encoding="utf-8"))["candidates"]
    row = next(item for item in rows if item["candidate_id"] == _PINNED)
    postpass = run_live_thermal_state_hydraulic_postpass(
        case,
        candidate_id=_PINNED,
        tube_inlet_temperature_k=case.tube_side.inlet_temperature_k,
        tube_outlet_temperature_k=row["tube_outlet_temperature_k"],
        shell_inlet_temperature_k=case.shell_side.inlet_temperature_k,
        shell_outlet_temperature_k=row["shell_outlet_temperature_k"],
        tube_inlet_pressure_pa=case.tube_side.inlet_pressure_pa,
        shell_inlet_pressure_pa=case.shell_side.inlet_pressure_pa,
        reference_tube_dp_pa=row["constraint_preview"]["modeled_tube_dp_pa"],
        reference_shell_dp_pa=row["constraint_preview"]["modeled_shell_dp_pa"],
    )
    analysis = build_live_thermal_hydraulic_connection_analysis(
        case,
        mesh={
            "status": "NUMERIC_VALID",
            "tube_outlet_temperature_k": row["tube_outlet_temperature_k"],
            "shell_outlet_temperature_k": row["shell_outlet_temperature_k"],
            "total_duty_w": row["total_duty_w"],
        },
    )
    raw = {
        "task_id": "V07_LIVE_THERMAL_STATE_HYDRAULIC_EVALUATION_R14",
        "candidate_id": _PINNED,
        "live_rating_duty_w": row["total_duty_w"],
        "postpass": postpass,
        "connection_analysis": analysis,
        "wall_seconds": round(time.perf_counter() - t0, 3),
    }
    (output_dir / "RAW_RESULT.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "LIVE_THERMAL_STATE_HYDRAULIC_POSTPASS.json").write_text(
        json.dumps(postpass, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "LIVE_THERMAL_HYDRAULIC_CONNECTION_ANALYSIS.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": "hxforge.evidence-manifest.v1",
        "task_id": "V07_LIVE_THERMAL_STATE_HYDRAULIC_EVALUATION_R14",
        "files": {
            name: _sha256(output_dir / name)
            for name in (
                "RAW_RESULT.json",
                "LIVE_THERMAL_STATE_HYDRAULIC_POSTPASS.json",
                "LIVE_THERMAL_HYDRAULIC_CONNECTION_ANALYSIS.json",
            )
        },
    }
    (output_dir / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return raw


if __name__ == "__main__":
    import sys

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else _EVIDENCE
    print(json.dumps(main(out), indent=2))
