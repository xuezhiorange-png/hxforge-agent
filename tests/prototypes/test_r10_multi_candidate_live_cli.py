"""R10 multi-candidate experimental live-rating CLI (subprocess + product gates)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)

R10_CASE = (
    Path(__file__).resolve().parents[2]
    / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_multi_candidate_r10.json"
)
R9_CASE = (
    Path(__file__).resolve().parents[2]
    / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_tube_hot_shell_cold_r9.json"
)
REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_cli(input_path: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "prototypes.v07_general_rating_sizing_mvp",
            "--input",
            str(input_path),
            "--output",
            str(output_dir),
            "--mode",
            "experimental-live-rating",
            "--mesh",
            "1",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_r10_space_has_two_distinct_task174_ready_candidates() -> None:
    case = load_general_engineering_case_json(R10_CASE.read_text(encoding="utf-8"))
    sel = enumerate_experimental_rating_candidates(case)
    ready = [r for r in sel.records if r.rating_request_ready]
    assert len(ready) >= 2
    assert len(sel.selected_candidate_ids) == 2
    hashes = {r.geometry_projection_hash for r in ready}
    assert len(hashes) >= 2
    request_hashes = {r.rating_request_hash for r in ready if r.rating_request_hash}
    assert len(request_hashes) == 2


def test_cli_blocked_scope_returns_nonzero() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = _run_cli(R9_CASE.parent / "mvp_tube_hot_shell_cold_r8c.json", out)
        assert proc.returncode != 0


@pytest.mark.timeout(1200)
def test_r10_cli_subprocess_two_numeric_valid_candidates() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = _run_cli(R10_CASE, out)
        assert proc.returncode == 0, proc.stderr
        raw = json.loads((out / "RAW_RESULT.json").read_text(encoding="utf-8"))
        results = raw["candidate_rating_results"]
        assert len(results) == 2
        assert all(row["mesh_status"] == "NUMERIC_VALID" for row in results)
        assert results[0]["mesh_result_hash"] != results[1]["mesh_result_hash"]
        assert results[0]["rating_request_hash"] != results[1]["rating_request_hash"]
        ranking = json.loads((out / "EXPERIMENTAL_RANKING_RESULT.json").read_text(encoding="utf-8"))
        assert ranking["EXPERIMENTAL_RANKING_STATUS"] == "COMPARISON_ONLY"
        assert ranking["preferred_candidate_id"] is None
        assert ranking["experimental_sizing_objective"] == "PARETO_ONLY"
        provider = raw["property_provider_identity"]
        assert provider["coolprop_version"]
        assert provider["coolprop_git_revision"]
        assert provider["coolprop_git_revision"] != "CoolPropProvider"
