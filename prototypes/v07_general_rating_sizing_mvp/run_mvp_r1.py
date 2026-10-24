#!/usr/bin/env python3
"""R1 evidence runner for general rating + sizing MVP."""

# ruff: noqa: E501, E402

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.hash_audit import (
    audit_r19_r21e_full_hash_replay,
    audit_r22_raw_result,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1
from prototypes.v07_general_rating_sizing_mvp.workflow import run_general_engineering_workflow

TASK_ID = "V07_GENERAL_RATING_SIZING_END_TO_END_MVP_R1"
BASE_HEAD = "7a6e48bfebec55bb8ffa3375586fd08613612310"
CASE_REL = "prototypes/v07_general_rating_sizing_mvp/cases/mvp_district_heating_water_water_r1.json"


def _gates() -> None:
    subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "pytest",
            "prototypes/v07_general_rating_sizing_mvp/test_general_mvp.py",
            "-q",
            "-m",
            "not slow",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["uv", "run", "--locked", "ruff", "check", "prototypes/v07_general_rating_sizing_mvp"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "ruff",
            "format",
            "--check",
            "prototypes/v07_general_rating_sizing_mvp",
        ],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--full-rating", action="store_true")
    args = parser.parse_args()
    t0 = time.perf_counter()
    code_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    _gates()
    case_path = ROOT / CASE_REL
    case = GeneralEngineeringCaseV1.model_validate_json(case_path.read_text(encoding="utf-8"))
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / f"docs/tasks/evidence/V07-GENERAL-RATING-SIZING-MVP-r1-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    outcome = run_general_engineering_workflow(
        case,
        out_dir,
        run_full_rating=args.full_rating,
    )
    golden = {
        "r19_r21e": audit_r19_r21e_full_hash_replay(ROOT),
        "r22_raw": audit_r22_raw_result(ROOT),
    }
    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "final_head": code_head,
        "general_input_schema": "hxforge.general-engineering-case.v1",
        "engineering_case_id": case.engineering_case_id,
        "workflow_status": outcome.status,
        "experimental_ranking_status": outcome.experimental_ranking_status,
        "production_design_approved": False,
        "preflight": outcome.preflight,
        "total_wall_seconds": outcome.total_wall_seconds,
        "rating_solver_calls": outcome.rating_solver_calls,
        "historical_golden_unchanged": golden,
        "fixed_golden_result_reused": False,
        "hardcoded_candidate_id": False,
        "general_workflow_entrypoint": "python -m prototypes.v07_general_rating_sizing_mvp",
        "readme_path": "prototypes/v07_general_rating_sizing_mvp/README.md",
        "wall_seconds_runner": time.perf_counter() - t0,
    }
    raw_path = out_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    if args.execute:
        subprocess.run(["git", "add", str(out_dir.relative_to(ROOT))], cwd=ROOT, check=True)
    print("RAW_RESULT_PATH", raw_path)
    print("RAW_RESULT_SHA256", raw_sha)


if __name__ == "__main__":
    main()
