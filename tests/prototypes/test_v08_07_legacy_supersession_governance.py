"""Governance: legacy Task173 heavy path classified as superseded in formal CI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def test_task173_independent_heavy_skipped_in_formal_ci() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src:."
    env.pop("HXFORGE_LEGACY_EXPERIMENTAL_V08_TASK173", None)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/prototypes/test_v08_thermal_rating_independent_case_heavy.py::test_v08_03_independent_case_input_delta",
            "-q",
            "-rs",
        ],
        cwd=_REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0
    assert "SUPERSEDED_BY_V08_KERNEL_P2" in proc.stdout + proc.stderr


def test_p2_kernel_replaces_alt_fixture_obligation() -> None:
    evidence = _REPO / "docs/tasks/evidence/V08-07-task173-independent-heavy-supersession-r1.md"
    p2 = _REPO / "tests/fixtures/v08_user_case_no_geometry_task174_admissible_alt.json"
    assert evidence.is_file()
    assert p2.is_file()
