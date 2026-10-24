"""R19 E2E: 12/20 baseline reference vs live 12/19 shell flow n=1 rating."""

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
_R19_CASE = REPO_ROOT / "tests/fixtures/r19_variable_shell_flow_case.json"
_BASELINE_REF = REPO_ROOT / "tests/fixtures/r19_baseline_12_20_reference.json"


@pytest.mark.timeout(3600)
def test_r19_new_shell_flow_n1_vs_baseline_reference() -> None:
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
                    "from prototypes.v07_general_rating_sizing_mvp.variable_shell_mass_flow_live_rating "
                    "import (build_comparison_against_baseline, load_baseline_reference, "
                    "run_new_shell_flow_n1_rating, write_r19_report); "
                    "case=load_general_engineering_case_json(Path(sys.argv[1]).read_text()); "
                    "baseline=load_baseline_reference(Path(sys.argv[2])); "
                    "payload=run_new_shell_flow_n1_rating(case, budget_s=2400); "
                    "comparison=build_comparison_against_baseline(baseline, payload['n1_summary']); "
                    "comparison['total_wall_seconds']=payload['total_wall_seconds']; "
                    "out=Path(sys.argv[3]); "
                    "out.mkdir(parents=True, exist_ok=True); "
                    "(out/'R19_VARIABLE_SHELL_FLOW_COMPARISON.json').write_text("
                    "json.dumps(comparison, indent=2)+'\\n'); "
                    "write_r19_report(comparison, out/'R19_ENGINEERING_REPORT.md'); "
                    "print(json.dumps(comparison))"
                ),
                str(_R19_CASE),
                str(_BASELINE_REF),
                str(out),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        comparison = json.loads(proc.stdout.strip())
        assert comparison["rating_outcome"] == "NUMERIC_VALID"
        var = comparison["variable_flow"]
        assert var["shell_mass_flow_kg_s"] == "19.000000"
        assert var["tube_mass_flow_kg_s"] == "12.000000"
        base_duty = Decimal(str(comparison["baseline"]["duty_w"]))
        var_duty = Decimal(str(var["duty_w"]))
        assert var_duty != base_duty
        shell_re = Decimal(str(var["shell_reynolds_number"]))
        base_shell_dp = Decimal(str(comparison["baseline"]["shell_dp_pa"]))
        var_shell_dp = Decimal(str(var["shell_dp_pa"]))
        assert var_shell_dp < base_shell_dp
        assert shell_re > Decimal("0")
        assert var.get("task032_input_mass_flow_kg_s") == "19.000000"
        assert var.get("tube_hydraulic_recompute_status") == "BLOCKED"
        artifacts_dir = Path("/opt/cursor/artifacts")
        if artifacts_dir.is_dir():
            (artifacts_dir / "r19_variable_shell_flow_comparison.json").write_text(
                (out / "R19_VARIABLE_SHELL_FLOW_COMPARISON.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            report = out / "R19_ENGINEERING_REPORT.md"
            if report.is_file():
                (artifacts_dir / "R19_ENGINEERING_REPORT.md").write_text(
                    report.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
