"""R16 E2E: live n=1 and n=2 rating on pinned candidate (subprocess)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_R16_CASE = REPO_ROOT / "tests/fixtures/r16_pinned_multi_mesh_case.json"


@pytest.mark.timeout(3600)
def test_r16_live_multi_mesh_e2e_n1_n2() -> None:
    case = load_general_engineering_case_json(_R16_CASE.read_text(encoding="utf-8"))
    selection = enumerate_experimental_rating_candidates(case)
    expected_candidate_id = selection.selected_candidate_ids[0]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "prototypes.v07_general_rating_sizing_mvp",
                "--input",
                str(_R16_CASE),
                "--output",
                str(out),
                "--mode",
                "experimental-live-multi-mesh-rating-r16",
                "--mesh-levels",
                "1,2",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        analysis = json.loads((out / "LIVE_MULTI_MESH_ANALYSIS.json").read_text(encoding="utf-8"))
        assert analysis["REAL_N1_RATING_STATUS"] == "NUMERIC_VALID"
        assert analysis["REAL_N2_RATING_STATUS"] == "NUMERIC_VALID"
        assert analysis["MESH_CONVERGENCE_STATUS"] == "MESH_COMPARISON_AVAILABLE"
        assert analysis["candidate_id"] == expected_candidate_id
        n1_duty = Decimal(
            next(
                row["total_duty_w"]
                for row in analysis["mesh_level_results"]
                if row["mesh_level"] == 1
            )
        )
        n2_duty = Decimal(
            next(
                row["total_duty_w"]
                for row in analysis["mesh_level_results"]
                if row["mesh_level"] == 2
            )
        )
        assert n1_duty != n2_duty
        rel = abs(n2_duty - n1_duty) / n1_duty * Decimal("100")
        assert rel < Decimal("5")
        post = analysis.get("HIGHEST_MESH_LIVE_HYDRAULIC_POSTPASS")
        assert post is not None
        assert post.get("recalculated_shell_dp_pa") is not None
        assert analysis["HIGHEST_VALID_MESH_LEVEL"] == 2
        assert (out / "R16_MULTI_MESH_ENGINEERING_REPORT.md").is_file()
        artifacts_dir = Path("/opt/cursor/artifacts")
        if artifacts_dir.is_dir():
            dest = artifacts_dir / "r16_live_multi_mesh_analysis.json"
            dest.write_text(
                (out / "LIVE_MULTI_MESH_ANALYSIS.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
