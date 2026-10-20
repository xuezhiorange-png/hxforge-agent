"""Generate R3 engineering evidence bundle (real execution only)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from hexagent.exchangers.shell_tube.task173_integrated_sizing import validate_sizing_request
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1
from prototypes.v07_general_rating_sizing_mvp.real_cell_evidence import write_real_cell_result
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
)
from prototypes.v07_general_rating_sizing_mvp.task172_root_cause import write_task172_root_cause
from prototypes.v07_general_rating_sizing_mvp.workflow import run_general_engineering_workflow

R2_CASE = Path(__file__).resolve().parent / "cases" / "mvp_water_water_physical_r2.json"
R3_CASE = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r3.json"
_DEFAULT_EVIDENCE_DIR = "docs/tasks/evidence/V07-GENERAL-RATING-FIRST-ACCEPTED-MESH-R3"


class _RatingBudgetExceeded(Exception):
    """Raised when Task173 sizing exceeds the configured numerical budget."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    t_num = time.perf_counter()
    r2_case = GeneralEngineeringCaseV1.model_validate_json(R2_CASE.read_text(encoding="utf-8"))
    write_task172_root_cause(r2_case, output_dir / "TASK172_FAILURE_ROOT_CAUSE.json")
    r3_case = GeneralEngineeringCaseV1.model_validate_json(R3_CASE.read_text(encoding="utf-8"))
    write_real_cell_result(r3_case, output_dir / "REAL_CELL_RESULT.json")
    workflow = run_general_engineering_workflow(
        r3_case,
        output_dir,
        run_full_rating=False,
    )
    rating_budget_s = min(r3_case.solver_budget.total_budget_s, 90.0)
    sizing_request = build_task173_sizing_request(r3_case)
    rating_outcome: dict[str, object] = {"status": "NOT_RUN"}
    rating_started = time.perf_counter()
    try:
        import signal

        def _alarm_handler(_signum: int, _frame: object) -> None:
            raise _RatingBudgetExceeded

        signal.signal(signal.SIGALRM, _alarm_handler)
        signal.setitimer(signal.ITIMER_REAL, rating_budget_s)
        outcome = validate_sizing_request(sizing_request)
        rating_outcome = json.loads(outcome.model_dump_json())
    except _RatingBudgetExceeded:
        rating_outcome = {
            "status": "BLOCKED",
            "failure_code": "NUMERICAL_BUDGET_EXCEEDED",
            "elapsed_s": round(time.perf_counter() - rating_started, 3),
        }
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    (output_dir / "TASK173_SIZING_OUTCOME.json").write_text(
        json.dumps(rating_outcome, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raw_path = output_dir / "RAW_RESULT.json"
    raw_path.write_text(
        json.dumps(workflow.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_entries: dict[str, str] = {}
    for name in (
        "INPUT_TO_SOLVER_BINDING.json",
        "TASK172_FAILURE_ROOT_CAUSE.json",
        "REAL_CELL_RESULT.json",
        "ENGINEERING_REPORT.json",
        "ENGINEERING_REPORT.md",
        "RAW_RESULT.json",
        "TASK173_SIZING_OUTCOME.json",
    ):
        path = output_dir / name
        if path.is_file():
            manifest_entries[name] = _sha256_file(path)
    mesh_path = output_dir / "REAL_MESH_RESULT.json"
    if workflow.status in {"PARTIAL_RATING_ACCEPTED", "SIZING_EVALUATED"}:
        mesh_path.write_text(
            json.dumps(
                {
                    "schema_version": "hxforge.real-mesh-result.v1",
                    "status": "ACCEPTED",
                    "workflow_status": workflow.status,
                    "sizing_outcome": workflow.sizing_result,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        manifest_entries["REAL_MESH_RESULT.json"] = _sha256_file(mesh_path)
    else:
        mesh_path.write_text(
            json.dumps(
                {
                    "schema_version": "hxforge.real-mesh-result.v1",
                    "status": "BLOCKED",
                    "workflow_status": workflow.status,
                    "notes": "Full Task173 mesh ladder did not complete within engineering budget.",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        manifest_entries["REAL_MESH_RESULT.json"] = _sha256_file(mesh_path)
    manifest_path = output_dir / "EVIDENCE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "hxforge.evidence-manifest.v1",
                "task_id": "V07_GENERAL_RATING_FIRST_ACCEPTED_MESH_R3",
                "files": manifest_entries,
                "total_numerical_seconds": round(time.perf_counter() - t_num, 3),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    import sys

    target = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else "docs/tasks/evidence/V07-GENERAL-RATING-FIRST-ACCEPTED-MESH-R3"
    )
    main(target)
