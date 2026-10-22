"""R13 variable bundle live sizing CLI (subprocess, two new n=1 ratings)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
R13_CASE = REPO_ROOT / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_variable_bundle_r13.json"


def _run_cli(output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "prototypes.v07_general_rating_sizing_mvp",
            "--input",
            str(R13_CASE),
            "--output",
            str(output_dir),
            "--mode",
            "experimental-variable-bundle-sizing-r13",
            "--mesh",
            "1",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.timeout(3600)
def test_r13_live_two_ratings_variable_shell_geometry() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = _run_cli(out)
        assert proc.returncode == 0, proc.stderr
        blocker = json.loads(
            (out / "R12_25M_TASK174_BLOCKER_ANALYSIS.json").read_text(encoding="utf-8")
        )
        assert blocker["task174_status"] == "BLOCKED"
        decision = json.loads((out / "TARGET_DIRECTED_SIZING_DECISION.json").read_text())
        assert decision["C3_APPLICABILITY_STATUS"] == "NOT_C3_REFERENCE"
        assert decision["VARIABLE_PHYSICAL_TUBE_COUNT_SUPPORTED"] is True
        ratings = json.loads((out / "CANDIDATE_RATING_RESULTS.json").read_text(encoding="utf-8"))
        assert len(ratings["candidates"]) == 2
        assert all(row["mesh_status"] == "NUMERIC_VALID" for row in ratings["candidates"])
        tube_counts = {
            (row.get("bundle_geometry") or {}).get("physical_tube_count")
            for row in ratings["candidates"]
        }
        assert len(tube_counts) == 2
        flow_areas = {row.get("task025_parallel_area_m2") for row in ratings["candidates"]}
        assert len(flow_areas) == 2
        raw = json.loads((out / "RAW_RESULT.json").read_text(encoding="utf-8"))
        assert raw["task_id"] == "V07_GENERAL_VARIABLE_BUNDLE_GEOMETRY_SIZING_R13"
        manifest = json.loads((out / "EVIDENCE_MANIFEST.json").read_text(encoding="utf-8"))
        assert manifest["task_id"] == "V07_GENERAL_VARIABLE_BUNDLE_GEOMETRY_SIZING_R13"
