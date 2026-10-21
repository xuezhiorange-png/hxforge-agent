"""R12 target-directed live sizing CLI (subprocess, two new n=1 ratings)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
R12_CASE = (
    REPO_ROOT / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_target_directed_r12.json"
)


def _run_cli(output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "prototypes.v07_general_rating_sizing_mvp",
            "--input",
            str(R12_CASE),
            "--output",
            str(output_dir),
            "--mode",
            "experimental-target-directed-sizing-r12",
            "--mesh",
            "1",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.timeout(2400)
def test_r12_live_two_new_ratings_and_target_directed_decision() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = _run_cli(out)
        assert proc.returncode == 0, proc.stderr
        decision_path = out / "TARGET_DIRECTED_SIZING_DECISION.json"
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        assert decision["HYDRAULIC_MODEL_SCOPE"] == "HYDRAULIC_REFERENCE_MODEL_PREVIEW"
        assert decision["full_rating_converged"] is False
        ratings = json.loads((out / "CANDIDATE_RATING_RESULTS.json").read_text(encoding="utf-8"))
        assert len(ratings["candidates"]) == 2
        assert all(row["mesh_status"] == "NUMERIC_VALID" for row in ratings["candidates"])
        hashes = {row["mesh_result_hash"] for row in ratings["candidates"]}
        assert len(hashes) == 2
        assert decision["BEST_EVALUATED_CANDIDATE_ID"] is not None
        assert decision["TARGET_CONSTRAINT_STATUS"].startswith("PRELIMINARY_CONSTRAINT_SATISFIED")
        reduction = decision.get("AREA_REDUCTION_VS_R10_A_PERCENT")
        assert reduction is not None and float(reduction) > 0
        raw = json.loads((out / "RAW_RESULT.json").read_text(encoding="utf-8"))
        assert raw["task_id"] == "V07_GENERAL_TARGET_DIRECTED_LIVE_SIZING_R12"
