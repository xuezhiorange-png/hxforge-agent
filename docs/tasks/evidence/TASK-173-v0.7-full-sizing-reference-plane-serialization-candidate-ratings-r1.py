"""One-shot post-serialization-fix candidate Rating execution and evidence capture."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating import (
    CandidateRatingSuccessResult,
    Task173BlockedResult,
    candidate_rating_result_hash,
    validate_candidate_rating,
)

ROOT = Path(__file__).resolve().parents[3]
REQUEST_RUNNER_PATH = (
    ROOT / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
)
EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-ratings-r1.json"
)
EXPECTED = {
    "adeab5b1-a339-5eb3-aa66-011ffe49bac0": {
        "candidate_hash": "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767",
        "rating_request_hash": "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7",
    },
    "e152cca9-fd5d-59ca-9b46-1df574eee841": {
        "candidate_hash": "53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489",
        "rating_request_hash": "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8",
    },
}
COMPLETION_REQUEST_HASH = "5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae"
TASK168_SPACE_HASH = "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea"
EXPECTED_RUNTIME_HEAD = "21386a88f8290538172e9389ed46f50c3697a426"
R2A_AUTHORITY_ID = "V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R2A"
R2A_AUTHORITY_HASH = "25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e"


def _save(payload: dict[str, Any]) -> None:
    EVIDENCE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_request_runner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "task173_q13_candidate_rating_request_builder", REQUEST_RUNNER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("FROZEN_CANDIDATE_REQUEST_BUILDER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _blocked_result_hash(projection: dict[str, Any]) -> str:
    return canonical_sha256(
        {
            "schema_version": projection["schema_version"],
            "status": projection["status"],
            "failure_code": projection["failure_code"],
            "failed_mesh_subdivisions": projection["failed_mesh_subdivisions"],
            "request_hash": projection["request_hash"],
            "diagnostics": projection["diagnostics"],
        }
    )


def main() -> None:
    if EVIDENCE_PATH.exists():
        raise RuntimeError(f"REFUSING_DUPLICATE_POST_FIX_RATING_RUN:{EVIDENCE_PATH}")
    runtime_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if runtime_head != EXPECTED_RUNTIME_HEAD:
        raise RuntimeError(f"UNEXPECTED_POST_FIX_RUNTIME_HEAD:{runtime_head}")
    bound_runtime_paths = (
        "src/hexagent/exchangers/shell_tube/manufacturable_candidates",
        "src/hexagent/exchangers/shell_tube/task172_local_runtime",
        "src/hexagent/exchangers/shell_tube/task173_integrated_rating",
        "src/hexagent/exchangers/shell_tube/task173_integrated_sizing",
        "src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration",
        "src/hexagent/exchangers/shell_tube/bell_delaware/pressure_drop.py",
        "tests/exchangers/shell_tube/test_task173_integrated_rating.py",
    )
    dirty_runtime = subprocess.check_output(
        ["git", "status", "--porcelain", "--", *bound_runtime_paths], cwd=ROOT, text=True
    ).strip()
    if dirty_runtime:
        raise RuntimeError(f"POST_FIX_RUNTIME_PATHS_DIRTY:{dirty_runtime}")
    request_runner = _load_request_runner()
    requests = request_runner._build_candidate_requests()
    records: dict[str, dict[str, Any]] = {}
    for candidate_id, (candidate, request) in requests.items():
        expected = EXPECTED[candidate_id]
        request_hash = request_runner.candidate_rating_request_hash(request)
        if (
            candidate.candidate_hash != expected["candidate_hash"]
            or request_hash != expected["rating_request_hash"]
        ):
            raise RuntimeError(f"FROZEN_CANDIDATE_RATING_REQUEST_MISMATCH:{candidate_id}")
        records[candidate_id] = {
            "candidate_id": candidate_id,
            "candidate_hash": candidate.candidate_hash,
            "candidate_rating_request_hash": request_hash,
            "candidate_rating_request_projection": request_runner._native_projection(request),
            "invocation_count": 0,
            "invocation_started": False,
            "invocation_completed": False,
            "result_projection": None,
        }

    evidence: dict[str, Any] = {
        "schema_version": "task173.full-sizing-reference-plane-serialization-candidate-ratings.v1",
        "completion_request_hash": COMPLETION_REQUEST_HASH,
        "task168_candidate_space_hash": TASK168_SPACE_HASH,
        "reviewed_r2a_authority_id": R2A_AUTHORITY_ID,
        "reviewed_r2a_authority_hash": R2A_AUTHORITY_HASH,
        "production_runtime_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "production_runtime_tree": subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True
        ).strip(),
        "public_sizing_invocation_performed": False,
        "candidates": records,
    }
    _save(evidence)

    for candidate_id in EXPECTED:
        record = records[candidate_id]
        if record["invocation_count"] != 0 or record["invocation_started"]:
            raise RuntimeError(f"REFUSING_DUPLICATE_CANDIDATE_RATING_CALL:{candidate_id}")
        record["invocation_count"] = 1
        record["invocation_started"] = True
        _save(evidence)

        outcome = validate_candidate_rating(requests[candidate_id][1])
        result_projection = request_runner._native_projection(outcome)
        record["result_type"] = type(outcome).__name__
        record["result_projection"] = result_projection
        record["invocation_completed"] = True
        _save(evidence)

        if type(outcome) is CandidateRatingSuccessResult:
            replayed_hash = candidate_rating_result_hash(outcome)
        elif type(outcome) is Task173BlockedResult:
            replayed_hash = _blocked_result_hash(result_projection)
        else:
            raise TypeError(f"unexpected candidate Rating outcome: {type(outcome).__name__}")
        record["recomputed_result_hash"] = replayed_hash
        record["result_hash_replay"] = replayed_hash == result_projection["result_hash"]
        record["result_hash"] = result_projection["result_hash"]
        record["result_id"] = result_projection["result_id"]
        record["status"] = result_projection["status"]
        if type(outcome) is Task173BlockedResult:
            record["failure_code"] = outcome.failure_code
            record["failed_mesh_subdivisions"] = outcome.failed_mesh_subdivisions
            record["diagnostics"] = list(outcome.diagnostics)
        else:
            record["accepted_mesh_subdivisions"] = outcome.accepted_subdivisions_per_interval
            record["headroom_mesh_subdivisions"] = outcome.headroom_subdivisions_per_interval
            provenance = dict(outcome.provenance)
            record["transient_provider_enclosure_event_hashes"] = json.loads(
                provenance["transient_provider_enclosure_event_hashes"]
            )
            record["outer_decision_certificate_hashes"] = json.loads(
                provenance["outer_decision_certificate_hashes"]
            )
            accepted_trajectory = json.loads(provenance["accepted_trajectory_projection"])
            record["accepted_trajectory_provider_enclosure_count"] = accepted_trajectory[
                "provider_enclosure_count_in_accepted_trajectory"
            ]
            record["accepted_trajectory_hash"] = accepted_trajectory["trajectory_hash"]
            record["mesh_ledger_hash"] = provenance["mesh_ledger_hash"]
            record["mesh_ledger_projection"] = json.loads(provenance["mesh_ledger_projection"])
        _save(evidence)
        print(
            f"CANDIDATE_RATING_RESULT_PERSISTED candidate={candidate_id} "
            f"status={record['status']} result_hash={record['result_hash']} "
            f"hash_replay={record['result_hash_replay']}"
        )

    print("POST_FIX_CANDIDATE_RATING_INVOCATIONS_COMPLETE=true")


if __name__ == "__main__":
    main()
