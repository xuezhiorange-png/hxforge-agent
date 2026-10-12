"""Replay the frozen inputs and blocked result for supplemental TASK173 R2.

This is a non-solving identity replay. It never invokes Candidate Rating or
public Sizing.
"""

from __future__ import annotations

import json
import runpy
import subprocess
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    Task173SizingBlockedResult,
)

ROOT = Path.cwd()
INPUT_REPLAY = Path(
    "docs/tasks/evidence/TASK-173-v0.7-supplemental-functional-acceptance-r2-replay.py"
)
INPUT_EVIDENCE = Path(
    "docs/tasks/evidence/TASK-173-v0.7-supplemental-functional-acceptance-r2.json"
)
EXECUTION_EVIDENCE = Path(
    "docs/tasks/evidence/TASK-173-v0.7-supplemental-functional-acceptance-r2-execution.json"
)
EXECUTION_HEAD = "7d9b98ebd5aab3108b7637a63c32000c27ce6697"
EXECUTION_TREE = "ec83f926e71ba33839f6fbdb197fe6091d5cf4ce"
REQUEST_HASH = "e5b085d238b2b1d9d7bcf23873c3ef04650135785fa4e6be1598aed3b8a9ab1e"
CANDIDATE_SPACE_HASH = "480e3249300d4b4a0668815cd18ebb7ed6fb5cf507c073449c9a509526eea668"
EXPECTED_CANDIDATES = (
    (
        "68a99368-a518-5482-b9df-4bc3357edea9",
        "bd0da145a592652e55a6fc8cd325a98d6f1cf349ed74b98e811d1343ce62ed54",
        "0.225",
    ),
    (
        "aa70248a-9f76-542d-bc77-1e935b9c32d4",
        "a30d1b0c01dcd0607bdd46e720a3a278e6b90b265b6bd4f109eb2c1cae58d8c5",
        "0.275",
    ),
    (
        "f3e14759-e05b-5088-bfb5-b6e16e918267",
        "b5bcf9258ff1cd455eab071a55cbdce7d8708391d1737e44d3dae2bccdaedb7e",
        "0.350",
    ),
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> None:
    frozen_evidence = json.loads(INPUT_EVIDENCE.read_text(encoding="utf-8"))
    execution = json.loads(EXECUTION_EVIDENCE.read_text(encoding="utf-8"))

    replay_namespace = runpy.run_path(
        str(ROOT / INPUT_REPLAY), run_name="task173_frozen_input_replay"
    )
    reconstructed_evidence, request = replay_namespace["_reconstruct"]()
    assert reconstructed_evidence == frozen_evidence
    assert request.request_metadata
    assert request.task168_candidate_request is not None

    candidate_space = frozen_evidence["candidate_space"]
    assert candidate_space["task168_candidate_space_hash"] == CANDIDATE_SPACE_HASH
    candidate_rows = tuple(
        (item["candidate_id"], item["candidate_hash"], item["baffle_cut_fraction"])
        for item in candidate_space["candidates"]
    )
    assert candidate_rows == EXPECTED_CANDIDATES
    assert frozen_evidence["sizing_request"]["sizing_request_hash"] == REQUEST_HASH

    assert execution["execution_kind"] == "ONE_PUBLIC_SIZING_INVOCATION"
    assert execution["public_sizing_invocation_count"] == 1
    assert execution["execution_head"] == EXECUTION_HEAD
    assert execution["execution_tree"] == EXECUTION_TREE
    assert _git("show", "-s", "--format=%T", f"{EXECUTION_HEAD}^{{commit}}") == EXECUTION_TREE
    assert (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", EXECUTION_HEAD, "HEAD"],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0
    )
    assert execution["sizing_request_hash"] == REQUEST_HASH

    result_projection: dict[str, Any] = execution["rating_or_sizing_result_projection"]
    expected_projection_keys = {
        "schema_version",
        "status",
        "failure_stage",
        "failure_code",
        "request_hash",
        "blockers",
        "result_hash",
        "result_id",
    }
    assert set(result_projection) == expected_projection_keys
    assert result_projection["schema_version"] == "task173.sizing-blocked.v1"
    assert result_projection["status"] == "BLOCKED"
    assert result_projection["failure_stage"] == "RUNTIME"
    assert result_projection["failure_code"] == "BLOCKED_SIZING_RUNTIME_FAILURE"
    assert result_projection["request_hash"] == REQUEST_HASH
    assert result_projection["blockers"] == [
        "PydanticSerializationError",
        (
            "Unable to serialize unknown type: <class "
            "'hexagent.exchangers.shell_tube.tube_side.owned_enums.ReferencePlanePair'>"
        ),
    ]

    hash_projection = {
        "schema_version": result_projection["schema_version"],
        "status": result_projection["status"],
        "failure_stage": result_projection["failure_stage"],
        "failure_code": result_projection["failure_code"],
        "request_hash": result_projection["request_hash"],
        "blockers": result_projection["blockers"],
    }
    result_hash = canonical_sha256(hash_projection)
    assert result_hash == execution["result_hash"] == result_projection["result_hash"]
    assert result_projection["result_id"] == execution["result_id"]
    assert result_projection["result_id"] == f"urn:hxforge:task173-sizing:blocked:{result_hash}"

    native_result = Task173SizingBlockedResult.model_validate(
        {**result_projection, "blockers": tuple(result_projection["blockers"])}, strict=True
    )
    assert native_result.model_dump(mode="json") == result_projection

    print("FROZEN_INPUT_REPLAY=PASS")
    print("CANDIDATE_IDENTITIES_REPLAY=PASS")
    print("PUBLIC_SIZING_INVOCATION_COUNT=1")
    print("BLOCKED_RESULT_PREIMAGE_REPLAY=PASS")
    print("BLOCKED_RESULT_HASH_AND_ID_REPLAY=PASS")
    print("CANDIDATE_RATING_RESULTS=NOT_RETURNED_BY_BLOCKED_SIZING_RESULT")
    print("HARD_CONSTRAINTS_RANKING_RECOMMENDATION=NOT_REACHED")
    print("PUBLIC_RATING_OR_SIZING_EXECUTED_BY_REPLAY=false")


if __name__ == "__main__":
    main()
