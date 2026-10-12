"""Reconstruct frozen candidate Rating requests and run each at most once.

This evidence runner never invokes public Sizing. Preparation mode only builds
candidate-native upstream identities. ``--execute-ratings`` makes one guarded
Rating call per frozen candidate and persists each complete result projection
before computing or asserting its result identity.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.task173_integrated_rating import (
    candidate_rating_request_hash,
    candidate_rating_result_hash,
    validate_candidate_rating,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    _candidate_rating_request,
    _candidate_request_for_task174,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174NativeOutputs,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    validate_candidate_request as validate_task174_candidate,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import ReferencePlanePair

ROOT = Path(__file__).resolve().parents[3]
REQUEST_REPLAY = (
    ROOT / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-completion-request-r1-replay.py"
)
EVIDENCE_PATH = (
    ROOT / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-completion-r1.json"
)
EXPECTED_COMPLETION_REQUEST_HASH = (
    "5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae"
)
EXPECTED_SPACE_HASH = "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea"
EXPECTED_CANDIDATES = {
    "adeab5b1-a339-5eb3-aa66-011ffe49bac0": {
        "candidate_hash": "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767",
        "rating_request_hash": "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7",
    },
    "e152cca9-fd5d-59ca-9b46-1df574eee841": {
        "candidate_hash": "53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489",
        "rating_request_hash": "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8",
    },
}


def _load_request_replay() -> Any:
    spec = importlib.util.spec_from_file_location(
        "task173_completion_request_replay", REQUEST_REPLAY
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("completion request replay module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_candidate_requests() -> dict[str, tuple[Any, Any]]:
    replay = _load_request_replay()
    sizing_request, facts = replay._build_request_and_projection()
    if facts["completion_sizing_request_hash"] != EXPECTED_COMPLETION_REQUEST_HASH:
        raise RuntimeError("frozen completion request hash mismatch")
    if facts["candidate_space_hash"] != EXPECTED_SPACE_HASH:
        raise RuntimeError("frozen native TASK168 candidate-space hash mismatch")

    task168_request = sizing_request.task168_candidate_request
    authority_map = task168._authority_map(task168_request)
    dimensions = tuple(
        task168._sort_values(authority_map[role].values)
        for role in task168.DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    request_hash = facts["completion_sizing_request_hash"]
    found: dict[str, tuple[Any, Any]] = {}
    for combination in product(task168_request.shell_geometry_catalog.records, *dimensions):
        candidate = task168._candidate(
            task168_request, authority_map, combination[0], tuple(combination[1:])
        )
        if candidate.candidate_id not in EXPECTED_CANDIDATES:
            continue
        if (
            candidate.candidate_hash
            != EXPECTED_CANDIDATES[candidate.candidate_id]["candidate_hash"]
        ):
            raise RuntimeError(f"candidate identity mismatch: {candidate.candidate_id}")
        bundle, stage_failure, _ = task168._execute_candidate_chain(
            task168_request,
            candidate,
            combination[0],
            include_legacy_task162=False,
            include_legacy_task168_rating_dependencies=False,
            preserve_baffle_orientation_sequence=True,
        )
        if stage_failure is not None:
            raise RuntimeError(f"candidate upstream chain blocked: {stage_failure!r}")
        topology = materialize_candidate_task171(
            candidate=candidate,
            configuration=bundle.task020_configuration,
            layout=bundle.task021_layout,
            bundle_geometry=bundle.task022_geometry,
            baffle_geometry=bundle.task024_geometry,
            task025_result=bundle.task025_result,
            task024_request=bundle.task024_request,
            task025_request=bundle.task025_request,
        )
        task174_request = _candidate_request_for_task174(candidate, bundle, topology)
        task174 = validate_task174_candidate(
            task174_request,
            Task174NativeOutputs(
                task029=bundle.task029_result,
                task034=None,
                task166=bundle.task166_result,
            ),
        )
        if task174.status != "VALIDATED":
            raise RuntimeError(f"candidate TASK174 blocked: {candidate.candidate_id}")
        rating_request = _candidate_rating_request(
            candidate,
            facts["candidate_space_hash"],
            bundle,
            topology,
            task174,
            request_hash,
        )
        actual_hash = candidate_rating_request_hash(rating_request)
        if actual_hash != EXPECTED_CANDIDATES[candidate.candidate_id]["rating_request_hash"]:
            raise RuntimeError(
                f"candidate Rating request identity mismatch: {candidate.candidate_id}"
            )
        found[candidate.candidate_id] = (candidate, rating_request)

    if set(found) != set(EXPECTED_CANDIDATES):
        raise RuntimeError(f"frozen candidate set mismatch: {sorted(found)}")
    return found


def _save(evidence: dict[str, Any]) -> None:
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _native_projection(value: Any) -> Any:
    """Project complete native request/result fields without lossy reprs."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if type(value) is ReferencePlanePair:
        return {"start": value.start.value, "end": value.end.value, "kind": value.kind}
    model_fields = getattr(type(value), "model_fields", None)
    if model_fields is not None:
        return {name: _native_projection(getattr(value, name)) for name in model_fields}
    if is_dataclass(value):
        return {item.name: _native_projection(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _native_projection(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_native_projection(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported native evidence value: {type(value).__name__}")


def _new_evidence(requests: dict[str, tuple[Any, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "task173.full-sizing-q13-correction-rating-execution.v1",
        "completion_request_hash": EXPECTED_COMPLETION_REQUEST_HASH,
        "task168_candidate_space_hash": EXPECTED_SPACE_HASH,
        "production_runtime_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "public_sizing_invocation_performed": False,
        "completion_request_public_sizing_invocation_count": 1,
        "historical_r4_public_sizing_invocation_count": 2,
        "candidates": {
            candidate_id: {
                "candidate_id": candidate_id,
                "candidate_hash": candidate.candidate_hash,
                "rating_request_hash": candidate_rating_request_hash(request),
                "rating_request_projection": _native_projection(request),
                "invocation_count": 0,
                "invocation_started": False,
                "invocation_completed": False,
                "result_projection": None,
            }
            for candidate_id, (candidate, request) in requests.items()
        },
    }


def _result_hash_from_projection(projection: dict[str, Any]) -> str:
    if projection.get("status") == "VALIDATED":
        from hexagent.exchangers.shell_tube.task173_integrated_rating import (
            CandidateRatingSuccessResult,
        )

        result = CandidateRatingSuccessResult.model_validate(projection, strict=True)
        return candidate_rating_result_hash(result)
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-ratings", action="store_true")
    args = parser.parse_args()
    requests = _build_candidate_requests()
    if not EVIDENCE_PATH.exists():
        evidence = _new_evidence(requests)
        _save(evidence)
        print("CANDIDATE_REQUEST_PREIMAGES_FROZEN=true")
    else:
        evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        expected = _new_evidence(requests)
        for candidate_id in EXPECTED_CANDIDATES:
            for key in (
                "candidate_id",
                "candidate_hash",
                "rating_request_hash",
                "rating_request_projection",
            ):
                if (
                    evidence["candidates"][candidate_id][key]
                    != expected["candidates"][candidate_id][key]
                ):
                    raise RuntimeError(
                        f"frozen candidate request evidence changed: {candidate_id}/{key}"
                    )

    if not args.execute_ratings:
        print("PUBLIC_RATING_CALLS_PERFORMED=0")
        return

    for candidate_id in EXPECTED_CANDIDATES:
        record = evidence["candidates"][candidate_id]
        if record["invocation_started"] or record["invocation_count"] != 0:
            raise RuntimeError(f"refusing duplicate Candidate Rating invocation: {candidate_id}")
        record["invocation_started"] = True
        record["invocation_count"] = 1
        _save(evidence)

        # The complete native result projection is persisted before identity checks.
        outcome = validate_candidate_rating(requests[candidate_id][1])
        result_projection = _native_projection(outcome)
        record["result_projection"] = result_projection
        record["invocation_completed"] = True
        record["result_type"] = type(outcome).__name__
        _save(evidence)

        replayed_hash = _result_hash_from_projection(result_projection)
        record["recomputed_result_hash"] = replayed_hash
        record["result_hash_replay"] = replayed_hash == result_projection["result_hash"]
        record["result_identity"] = result_projection["result_id"]
        record["status"] = result_projection["status"]
        if result_projection["status"] == "BLOCKED":
            record["failure_code"] = result_projection["failure_code"]
            record["failed_mesh_subdivisions"] = result_projection["failed_mesh_subdivisions"]
            record["diagnostics"] = result_projection["diagnostics"]
        _save(evidence)
        print(
            f"CANDIDATE_RATING_RESULT_PERSISTED id={candidate_id} "
            f"type={record['result_type']} status={record['status']} "
            f"result_hash={result_projection['result_hash']} "
            f"hash_replay={record['result_hash_replay']}"
        )


if __name__ == "__main__":
    main()
