"""R18 E2E: baseline 12 kg/s vs opt-in 10 kg/s live n=1 rating."""

# ruff: noqa: E501

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_R16_CASE = REPO_ROOT / "tests/fixtures/r16_pinned_multi_mesh_case.json"
_R18_CASE = REPO_ROOT / "tests/fixtures/r18_variable_tube_flow_case.json"


@pytest.mark.timeout(3600)
def test_r18_baseline_vs_variable_flow_n1_e2e() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json,sys; from pathlib import Path; "
                    "from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader "
                    "import load_general_engineering_case_json; "
                    "from prototypes.v07_general_rating_sizing_mvp.variable_tube_mass_flow_live_rating "
                    "import run_baseline_vs_variable_comparison, write_comparison_artifacts; "
                    "baseline=load_general_engineering_case_json(Path(sys.argv[1]).read_text()); "
                    "variable=load_general_engineering_case_json(Path(sys.argv[2]).read_text()); "
                    "payload=run_baseline_vs_variable_comparison(baseline, variable); "
                    "write_comparison_artifacts(payload, Path(sys.argv[3])); "
                    "print(json.dumps(payload['comparison']))"
                ),
                str(_R16_CASE),
                str(_R18_CASE),
                str(out),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        comparison = json.loads(proc.stdout.strip())
        assert comparison["baseline"]["rating_status"] == "NUMERIC_VALID"
        assert comparison["variable_flow"]["rating_status"] == "NUMERIC_VALID"
        base_duty = Decimal(str(comparison["baseline"]["duty_w"]))
        var_duty = Decimal(str(comparison["variable_flow"]["duty_w"]))
        assert base_duty != var_duty
        assert comparison["baseline"]["tube_mass_flow_kg_s"] == "12.000000"
        assert comparison["variable_flow"]["tube_mass_flow_kg_s"] == "11.000000"
        var_re = Decimal(str(comparison["variable_flow"]["tube_reynolds_number"]))
        base_re = Decimal(str(comparison["baseline"]["tube_reynolds_number"]))
        assert var_re < base_re
        assert var_re > Decimal("2500")
        assert comparison["variable_flow"].get("tube_hydraulic_recompute_status") == "BLOCKED"
        artifacts_dir = Path("/opt/cursor/artifacts")
        if artifacts_dir.is_dir():
            dest = artifacts_dir / "r18_variable_tube_flow_comparison.json"
            dest.write_text(
                (out / "R18_VARIABLE_TUBE_FLOW_COMPARISON.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            report = out / "R18_ENGINEERING_REPORT.md"
            if report.is_file():
                (artifacts_dir / "R18_ENGINEERING_REPORT.md").write_text(
                    report.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
