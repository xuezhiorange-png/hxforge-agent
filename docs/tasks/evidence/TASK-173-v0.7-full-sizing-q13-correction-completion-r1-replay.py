"""Replay Q13 correction candidate-request and blocked-result identities."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating import Task173BlockedResult

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = (
    ROOT / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-completion-r1.json"
)
RUNNER_PATH = (
    ROOT / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
)
RUNTIME_HEAD = "c36d54d0a8c162bbb4c585acfc6ec5615ce1f6cf"
RUNTIME_TREE = "c07ea99cca0ecf16054bfa855711f5e042e59be7"
BOUND_PATHS = (
    "src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py",
    "tests/exchangers/shell_tube/test_task173_integrated_rating.py",
)
EXPECTED = {
    "adeab5b1-a339-5eb3-aa66-011ffe49bac0": {
        "candidate_hash": "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767",
        "request_hash": "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7",
    },
    "e152cca9-fd5d-59ca-9b46-1df574eee841": {
        "candidate_hash": "53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489",
        "request_hash": "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8",
    },
}


def _load_runner() -> Any:
    spec = importlib.util.spec_from_file_location("q13_candidate_rating_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate Rating runner is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check_runtime_binding() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tree = subprocess.check_output(
        ["git", "rev-parse", f"{RUNTIME_HEAD}^{{tree}}"], cwd=ROOT, text=True
    ).strip()
    if tree != RUNTIME_TREE:
        raise AssertionError(f"runtime tree mismatch: {tree}")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", RUNTIME_HEAD, head],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["git", "diff", "--exit-code", RUNTIME_HEAD, head, "--", *BOUND_PATHS],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["git", "diff", "--exit-code", "HEAD", "--", *BOUND_PATHS],
        cwd=ROOT,
        check=True,
    )


def _blocked_hash(result: Task173BlockedResult) -> str:
    projection = result.model_dump(mode="json")
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
    _check_runtime_binding()
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if (
        evidence["completion_request_hash"]
        != "5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae"
        or evidence["task168_candidate_space_hash"]
        != "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea"
    ):
        raise AssertionError("frozen completion request or candidate-space identity mismatch")
    runner = _load_runner()
    requests = runner._build_candidate_requests()
    if set(evidence["candidates"]) != set(EXPECTED):
        raise AssertionError("candidate set differs from the frozen R4 space")

    for candidate_id, expected in EXPECTED.items():
        candidate, request = requests[candidate_id]
        record = evidence["candidates"][candidate_id]
        if candidate.candidate_hash != expected["candidate_hash"]:
            raise AssertionError(f"candidate hash mismatch: {candidate_id}")
        if runner.candidate_rating_request_hash(request) != expected["request_hash"]:
            raise AssertionError(f"native candidate request hash mismatch: {candidate_id}")
        if record["rating_request_projection"] != runner._native_projection(request):
            raise AssertionError(f"full candidate request projection mismatch: {candidate_id}")
        if record["invocation_count"] != 1 or not record["invocation_completed"]:
            raise AssertionError(f"candidate invocation accounting incomplete: {candidate_id}")
        if record["result_type"] != "Task173BlockedResult":
            raise AssertionError(f"unexpected candidate outcome type: {candidate_id}")
        native_result_projection = dict(record["result_projection"])
        native_result_projection["diagnostics"] = tuple(native_result_projection["diagnostics"])
        result = Task173BlockedResult.model_validate(native_result_projection, strict=True)
        digest = _blocked_hash(result)
        if digest != result.result_hash or digest != record["recomputed_result_hash"]:
            raise AssertionError(f"blocked result hash mismatch: {candidate_id}")
        if result.request_hash != expected["request_hash"]:
            raise AssertionError(f"blocked result request binding mismatch: {candidate_id}")
        if result.result_id != f"urn:hxforge:task173:blocked:{digest}":
            raise AssertionError(f"blocked result ID mismatch: {candidate_id}")
        if result.failure_code != "BLOCKED_TASK173_CANDIDATE_UNEXPECTED_RUNTIME_FAILURE":
            raise AssertionError(f"unexpected first blocker classification: {candidate_id}")
        if not record["result_hash_replay"]:
            raise AssertionError(f"stored result hash replay flag is false: {candidate_id}")
        print(
            f"CANDIDATE_BLOCKED_RESULT_REPLAY=PASS id={candidate_id} "
            f"request_hash={expected['request_hash']} result_hash={digest}"
        )

    if evidence["public_sizing_invocation_performed"] is not False:
        raise AssertionError("public Sizing was unexpectedly invoked by this gate")
    if evidence["second_completion_public_sizing_invocation_authorized"] is not False:
        raise AssertionError("second completion Sizing invocation must remain unauthorized")
    if evidence["total_recorded_task173_public_sizing_invocations"] != 3:
        raise AssertionError("public Sizing invocation accounting mismatch")
    print("CANDIDATE_RATING_BLOCKED_RESULT_PREIMAGE_REPLAY=PASS")
    print("PUBLIC_SIZING_REEXECUTED=false")
    print("FULL_RATING_COMPLETION_STATUS=BLOCKED")


if __name__ == "__main__":
    main()
