"""Replay the single frozen TASK173 completion invocation and its blocker."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_json_bytes
from hexagent.exchangers.shell_tube.task173_integrated_sizing import (
    Task173SizingSuccessResult,
    recompute_sizing_result_hash,
    sizing_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    sizing_result_projection,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))
EVIDENCE_PATH = Path(__file__).with_name(
    "TASK-173-v0.7-full-sizing-implementation-r1-completion.json"
)
REQUEST_EVIDENCE = Path(__file__).with_name("TASK-173-v0.7-full-sizing-completion-request-r1.json")
REQUEST_REPLAY = Path(__file__).with_name(
    "TASK-173-v0.7-full-sizing-completion-request-r1-replay.py"
)
START_MARKER = Path(__file__).with_name(
    "TASK-173-v0.7-full-sizing-completion-execution-start-r1.json"
)
EXECUTION_RESULT = Path(__file__).with_name(
    "TASK-173-v0.7-full-sizing-completion-execution-r1.json"
)
EXPECTED_CANDIDATES = (
    (
        "adeab5b1-a339-5eb3-aa66-011ffe49bac0",
        "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767",
    ),
    (
        "e152cca9-fd5d-59ca-9b46-1df574eee841",
        "53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489",
    ),
)
EXPECTED_TASK168_SPACE_HASH = "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea"
EXPECTED_RATING_BLOCKER = "PRECISION_FLOOR_UNRESOLVED"


def _module_from_path(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load replay module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_completion_evidence() -> dict[str, Any]:
    request_evidence = json.loads(REQUEST_EVIDENCE.read_text(encoding="utf-8"))
    request_replay = _module_from_path("completion_request_replay", REQUEST_REPLAY)
    request, request_facts = request_replay._build_request_and_projection()
    if request_replay._make_evidence(request_facts) != request_evidence:
        raise AssertionError("completion request preimage replay failed")
    if sizing_request_hash(request) != request_evidence["completion_sizing_request_hash"]:
        raise AssertionError("completion request hash does not match frozen request")

    start = json.loads(START_MARKER.read_text(encoding="utf-8"))
    execution = json.loads(EXECUTION_RESULT.read_text(encoding="utf-8"))
    if execution.get("execution_status") != "RETURNED":
        raise AssertionError("the single completion invocation did not return")
    if (
        execution["completion_sizing_request_hash"]
        != request_evidence["completion_sizing_request_hash"]
    ):
        raise AssertionError("execution used a different completion request")
    if start["completion_sizing_request_hash"] != execution["completion_sizing_request_hash"]:
        raise AssertionError("start marker and returned execution disagree")
    if (
        start["completion_request_public_sizing_invocation_count"] != 1
        or execution["completion_request_public_sizing_invocation_count"] != 1
        or execution["total_recorded_task173_public_sizing_invocations"] != 3
        or execution["historical_r4_public_sizing_invocation_count"] != 2
    ):
        raise AssertionError("public Sizing invocation accounting mismatch")

    raw_projection = execution["sizing_result_projection"]
    result = Task173SizingSuccessResult.model_validate_json(
        json.dumps(raw_projection, ensure_ascii=False), strict=True
    )
    result_projection = sizing_result_projection(result)
    result_bytes = canonical_json_bytes(result_projection)
    replayed_result_hash = recompute_sizing_result_hash(result)
    if replayed_result_hash != result.result_hash:
        raise AssertionError("final Sizing result hash does not replay")
    if execution["sizing_result_hash"] != result.result_hash:
        raise AssertionError("execution envelope and Sizing result hash disagree")
    if execution["sizing_result_id"] != result.result_id:
        raise AssertionError("execution envelope and Sizing result ID disagree")
    if result.request_hash != request_evidence["completion_sizing_request_hash"]:
        raise AssertionError("Sizing result is not bound to the frozen request")
    if result.candidate_space_hash != EXPECTED_TASK168_SPACE_HASH:
        raise AssertionError("Sizing result used a different candidate space")

    candidates = tuple(result.candidate_records)
    candidate_identities = tuple((item.candidate_id, item.candidate_hash) for item in candidates)
    if candidate_identities != EXPECTED_CANDIDATES or result.candidate_count != 2:
        raise AssertionError("Sizing result candidate identities differ from frozen R4")
    for item in candidates:
        if (
            item.disposition != "BLOCKED"
            or item.status != "BLOCKED"
            or item.stage != "TASK173_CANDIDATE_RATING"
            or EXPECTED_RATING_BLOCKER not in item.blockers
            or item.candidate_rating_request_hash is None
            or item.candidate_rating_result_hash is None
            or item.candidate_rating_result_id is None
        ):
            raise AssertionError(f"candidate result is not the recorded Rating blocker: {item}")

    # This is a blocked attempt, not the authorized zero-recommendable business
    # outcome: neither candidate completed its full Rating or reached hard-constraint
    # evaluation. The Sizing service retained blocked result hashes but not their
    # Task173BlockedResult preimages, so those inner hashes cannot be replayed here.
    if (
        result.selection_status != "NO_RECOMMENDABLE_CANDIDATE"
        or result.recommendable_count != 0
        or result.ranked_candidate_ids
        or result.ranking_trace
    ):
        raise AssertionError("unexpected selection/ranking state for blocked candidates")

    return {
        "schema_version": "task173.full-sizing-implementation-completion-attempt.v1",
        "result": "BLOCKED_TASK173_FULL_SIZING_IMPLEMENTATION",
        "blocker_class": "RATING_PRECISION_FLOOR_UNRESOLVED",
        "first_blocker": {
            "candidate_id": candidates[0].candidate_id,
            "stage": candidates[0].stage,
            "code": EXPECTED_RATING_BLOCKER,
            "candidate_rating_request_hash": candidates[0].candidate_rating_request_hash,
            "candidate_rating_result_hash": candidates[0].candidate_rating_result_hash,
            "candidate_rating_result_id": candidates[0].candidate_rating_result_id,
            "diagnostic_scope": (
                "Sizing ledger exposes the exact blocker code and result identity, but "
                "does not retain the inner Task173BlockedResult diagnostic preimage"
            ),
        },
        "runtime_source_head": execution["runtime_source_head"],
        "request_freeze_head": execution["request_freeze_head"],
        "strict_json_model_roundtrip_required": False,
        "strict_native_python_request_validation": "PASS",
        "canonical_identity_preimage_freeze": "PASS",
        "task168_request_canonical_preimage_replay": "PASS",
        "sizing_identity_canonical_preimage_replay": "PASS",
        "production_serialization_code_changed": False,
        "completion_requirement_authority_hash": request_evidence[
            "completion_requirement_authority_hash"
        ],
        "completion_sizing_request_hash": request_evidence["completion_sizing_request_hash"],
        "task168_request_hash": request_evidence["task168_request_hash"],
        "task168_candidate_space_hash": result.candidate_space_hash,
        "r4_baffle_cut_authority_hash": request_evidence["r4_baffle_cut_authority_hash"],
        "candidate_count": result.candidate_count,
        "candidate_rating_invocation_count": len(candidates),
        "candidate_full_rating_completed_count": 0,
        "candidate_A_full_rating_complete": False,
        "candidate_B_full_rating_complete": False,
        "accepted_mesh_ledger_count": 0,
        "hard_constraints_evaluated": False,
        "recommendable_candidate_count": result.recommendable_count,
        "sizing_result_type": execution["sizing_result_type"],
        "sizing_status": result.status,
        "selection_status": result.selection_status,
        "sizing_result_id": result.result_id,
        "sizing_result_hash": result.result_hash,
        "sizing_result_hash_replay": "PASS",
        "candidate_rating_blocked_result_preimages_persisted": False,
        "candidate_records": [item.model_dump(mode="json") for item in candidates],
        "execution_start_record": start,
        "execution_return_record": execution,
        "sizing_result_projection": raw_projection,
        "sizing_result_identity_projection": result_projection,
        "sizing_result_identity_canonical_json_utf8": result_bytes.decode("utf-8"),
        "sizing_result_identity_canonical_json_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "historical_r4_public_sizing_invocation_count": 2,
        "completion_request_public_sizing_invocation_count": 1,
        "total_recorded_task173_public_sizing_invocations": 3,
        "task173_rating_complete": True,
        "task173_sizing_complete": False,
        "task173_complete": False,
        "task175_release_acceptance_performed": False,
        "ready_authorized": False,
        "merge_authorized": False,
    }


def replay(evidence: dict[str, Any]) -> None:
    regenerated = _build_completion_evidence()
    if evidence != regenerated:
        raise AssertionError("completion-attempt evidence differs from frozen execution")
    print("COMPLETION_REQUEST_REPLAY=PASS")
    print("PUBLIC_SIZING_INVOCATION_ACCOUNTING=PASS")
    print("SIZING_RESULT_HASH_REPLAY=PASS")
    print("R4_CANDIDATE_IDENTITY_REPLAY=PASS")
    print("CANDIDATE_RATING_BLOCKER_REPLAY=PASS")
    print("CANDIDATE_RATING_RESULT_PREIMAGE_REPLAY=UNAVAILABLE")
    print("FULL_SIZING_IDENTITY_REPLAY=BLOCKED")
    print("TASK173_SIZING_COMPLETE=false")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        evidence = _build_completion_evidence()
        EVIDENCE_PATH.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    replay(json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
