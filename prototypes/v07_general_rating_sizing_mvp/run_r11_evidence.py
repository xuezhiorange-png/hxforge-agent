"""R11 evidence: constraint-aware sizing + CI schema fix (no new full rating mesh)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_EVIDENCE = (
    _REPO_ROOT / "docs/tasks/evidence/V07-GENERAL-CONSTRAINT-AWARE-SIZING-CI-CLOSURE-R11"
)
_R10_EVIDENCE = (
    _REPO_ROOT / "docs/tasks/evidence/V07-GENERAL-MULTI-CANDIDATE-LIVE-RATING-R10"
)
_R10_BRANCH_PATH = (
    "origin/cursor/v07-general-rating-sizing-e2e-mvp-r1-1201:"
    "docs/tasks/evidence/V07-GENERAL-MULTI-CANDIDATE-LIVE-RATING-R10"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(output_dir: Path) -> dict[str, Any]:
    from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
        enumerate_experimental_rating_candidates,
    )
    from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
        load_general_engineering_case_json,
    )
    from prototypes.v07_general_rating_sizing_mvp.experimental_candidate_eligibility import (
        build_candidate_eligibility,
    )
    from prototypes.v07_general_rating_sizing_mvp.experimental_ranking import (
        build_experimental_ranking,
        build_offline_duty_scenarios,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    case_path = (
        _REPO_ROOT / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_multi_candidate_r10.json"
    )
    case = load_general_engineering_case_json(case_path.read_text(encoding="utf-8"))

    frozen_path = _R10_EVIDENCE / "CANDIDATE_RATING_RESULTS.json"
    if not frozen_path.is_file():
        proc = subprocess.run(
            ["git", "show", f"{_R10_BRANCH_PATH}/CANDIDATE_RATING_RESULTS.json"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        frozen_doc = json.loads(proc.stdout)
    else:
        frozen_doc = json.loads(frozen_path.read_text(encoding="utf-8"))
    rows = frozen_doc["candidates"]
    selection = enumerate_experimental_rating_candidates(case)
    eligibility = build_candidate_eligibility(case, selection, rows)

    from decimal import Decimal

    scenarios = build_offline_duty_scenarios(
        case,
        rows,
        scenario_targets_w=(Decimal("9500"), Decimal("38000"), Decimal("38500")),
    )
    ranking = build_experimental_ranking(case, rows, objective="PARETO_ONLY")

    artifacts = {
        "R10_CI_COMPATIBILITY_FIX.json": {
            "schema_version": "hxforge.r10-ci-compatibility-fix.v1",
            "MESH_RESULT_STATUS_SCHEMA_FIXED": True,
            "status_field_source": "solver_mesh_status",
        },
        "EXPERIMENTAL_CANDIDATE_ELIGIBILITY.json": {
            "schema_version": "hxforge.experimental-candidate-eligibility.v1",
            "OFFLINE_SCREENING_USING_R10_FROZEN_MESH": True,
            "candidates": eligibility,
            "HYDRAULIC_MODEL_SCOPE": "HYDRAULIC_REFERENCE_MODEL_PREVIEW",
        },
        "NOMINAL_GEOMETRY_AREA_COMPARISON.json": {
            "schema_version": "hxforge.nominal-geometry-area-comparison.v1",
            "OFFLINE_SCREENING_USING_R10_FROZEN_MESH": True,
            "candidates": [
                {"candidate_id": r["candidate_id"], "nominal_geometry": r.get("nominal_geometry")}
                for r in rows
            ],
        },
        "SIZING_OBJECTIVE_SCENARIOS.json": scenarios,
        "EXPERIMENTAL_PARETO_RESULT.json": {
            "schema_version": "hxforge.experimental-pareto-result.v1",
            "pareto_frontier_candidate_ids": ranking.get("pareto_frontier_candidate_ids"),
            "OFFLINE_SCREENING_USING_R10_FROZEN_MESH": True,
        },
        "RAW_RESULT.json": {
            "schema_version": "hxforge.experimental-live-raw-result.v2",
            "task_id": "V07_GENERAL_CONSTRAINT_AWARE_SIZING_AND_CI_CLOSURE_R11",
            "OFFLINE_SCREENING_USING_R10_FROZEN_MESH": True,
            "candidate_rating_results": rows,
            "ranking": ranking,
        },
    }
    for name, payload in artifacts.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    report = {
        "schema_version": "hxforge.engineering-report.v1",
        "engineering_case_id": case.engineering_case_id,
        "experimental_ranking_status": ranking["EXPERIMENTAL_RANKING_STATUS"],
        "experimental_comparison_status": ranking["EXPERIMENTAL_COMPARISON_STATUS"],
        "conditional_preference_status": ranking["CONDITIONAL_PREFERENCE_STATUS"],
        "OFFLINE_SCREENING_USING_R10_FROZEN_MESH": True,
    }
    (output_dir / "ENGINEERING_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "ENGINEERING_REPORT.md").write_text(
        "# R11 offline engineering report\n\nFrozen R10 mesh rows; no new rating.\n",
        encoding="utf-8",
    )

    manifest = {name: _sha256_file(output_dir / name) for name in artifacts}
    manifest.update(
        {
            "ENGINEERING_REPORT.json": _sha256_file(output_dir / "ENGINEERING_REPORT.json"),
            "ENGINEERING_REPORT.md": _sha256_file(output_dir / "ENGINEERING_REPORT.md"),
        }
    )
    (output_dir / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.evidence-manifest.v1",
                "task_id": "V07_GENERAL_CONSTRAINT_AWARE_SIZING_AND_CI_CLOSURE_R11",
                "files": manifest,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"evidence_dir": str(output_dir), "file_count": len(manifest)}


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_EVIDENCE
    print(json.dumps(main(out), indent=2))
