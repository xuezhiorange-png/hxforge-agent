"""Replay frozen Candidate Rating requests and result identities.

This replay does not invoke Candidate Rating or public Sizing. It reconstructs
candidate-native requests from the committed completion request, checks the
complete request projections, and replays the complete blocked/success result
preimages already persisted by the one-shot execution runner.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating import (
    CandidateRatingSuccessResult,
    Task173BlockedResult,
    candidate_rating_request_hash,
    candidate_rating_result_hash,
)

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-completion-r1.json"
)
EXECUTION_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-ratings-r1.json"
)
REQUEST_RUNNER_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
)
RUNTIME_HEAD = "21386a88f8290538172e9389ed46f50c3697a426"
RUNTIME_TREE = "ce61a818b82f908729d2bdf4553cc27012354952"
COMPLETION_REQUEST_HASH = "5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae"
TASK168_SPACE_HASH = "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea"
R2A_AUTHORITY_HASH = "25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e"
BOUND_RUNTIME_PATHS = (
    "src/hexagent/exchangers/shell_tube/manufacturable_candidates",
    "src/hexagent/exchangers/shell_tube/task172_local_runtime",
    "src/hexagent/exchangers/shell_tube/task173_integrated_rating",
    "src/hexagent/exchangers/shell_tube/task173_integrated_sizing",
    "src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration",
    "src/hexagent/exchangers/shell_tube/bell_delaware/pressure_drop.py",
    "tests/exchangers/shell_tube/test_task173_integrated_rating.py",
)
EXPECTED_CANDIDATES = {
    "adeab5b1-a339-5eb3-aa66-011ffe49bac0": {
        "candidate_hash": "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767",
        "request_hash": "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7",
        "result_hash": "daf0f61109676d50e9dac2c1d5ceb9afb206b232bc039fc0253f5b1ecdba774c",
        "status": "BLOCKED",
    },
    "e152cca9-fd5d-59ca-9b46-1df574eee841": {
        "candidate_hash": "53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489",
        "request_hash": "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8",
        "result_hash": "1cecb402cc44ec2690918b3479cf6c7e4e1079eb290835122ad53ddfce657743",
        "status": "VALIDATED",
    },
}


def _load_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"replay dependency unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(*args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=False, capture_output=True, text=True
    )
    if check and completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _check_runtime_descendant() -> None:
    head = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", f"{RUNTIME_HEAD}^{{tree}}")
    if tree != RUNTIME_TREE:
        raise RuntimeError("frozen production runtime tree mismatch")
    _git("merge-base", "--is-ancestor", RUNTIME_HEAD, head)
    if _git("diff", "--name-only", RUNTIME_HEAD, head, "--", *BOUND_RUNTIME_PATHS):
        raise RuntimeError("runtime source differs between frozen runtime and evidence head")
    if _git("status", "--porcelain", "--", *BOUND_RUNTIME_PATHS):
        raise RuntimeError("bound runtime paths are dirty in the current worktree")
    if _git("diff", "--cached", "--name-only", "--", *BOUND_RUNTIME_PATHS):
        raise RuntimeError("bound runtime paths are staged in the current worktree")


def _blocked_hash(projection: dict[str, Any]) -> str:
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


def _verify_success_projection(projection: dict[str, Any]) -> dict[str, Any]:
    result = CandidateRatingSuccessResult.model_validate_json(
        json.dumps(projection, ensure_ascii=False, separators=(",", ":")), strict=True
    )
    digest = candidate_rating_result_hash(result)
    if digest != result.result_hash:
        raise RuntimeError("candidate success result hash replay mismatch")
    if result.result_id != f"urn:hxforge:task173:{digest}":
        raise RuntimeError("candidate success result ID mismatch")

    provenance = dict(result.provenance)
    mesh_ledger = json.loads(provenance["mesh_ledger_projection"])
    mesh_ledger_hash = mesh_ledger.pop("mesh_ledger_hash")
    if canonical_sha256(mesh_ledger) != provenance["mesh_ledger_hash"]:
        raise RuntimeError("candidate mesh ledger hash replay mismatch")
    if mesh_ledger_hash != provenance["mesh_ledger_hash"]:
        raise RuntimeError("mesh ledger embedded hash mismatch")

    trajectory = json.loads(provenance["accepted_trajectory_projection"])
    trajectory_hash = trajectory.pop("trajectory_hash")
    if canonical_sha256(trajectory) != trajectory_hash:
        raise RuntimeError("accepted trajectory hash replay mismatch")
    cells = trajectory["accepted_cells"]
    if trajectory["provider_enclosure_count_in_accepted_trajectory"] != 0:
        raise RuntimeError("accepted trajectory contains provider enclosure")
    if not cells or any(cell["cell_closure_mode"] != "EXACT_VALID_POINT_ROOT" for cell in cells):
        raise RuntimeError("accepted trajectory has non-exact cell closure")
    if any(abs(Decimal(cell["cell_root_residual_w"])) > Decimal("1e-6") for cell in cells):
        raise RuntimeError("accepted trajectory point-root residual exceeds tolerance")

    event_hashes = json.loads(provenance["transient_provider_enclosure_event_hashes"])
    certificate_hashes = json.loads(provenance["outer_decision_certificate_hashes"])
    certificate_set = json.loads(provenance["outer_decision_certificate_projection_sets"])
    # Provenance stores one projection-set collection, then the collection's
    # own item envelope. Keep both levels explicit instead of treating the
    # outer collection as the certificate list.
    certificate_sets = certificate_set.get("items")
    if not isinstance(certificate_sets, list) or any(
        not isinstance(certificate_group, dict)
        or not isinstance(certificate_group.get("items"), list)
        for certificate_group in certificate_sets
    ):
        raise RuntimeError("unexpected outer-decision certificate set shape")
    certificates = [
        certificate
        for certificate_group in certificate_sets
        for certificate in certificate_group["items"]
    ]
    if [item["certificate_hash"] for item in certificates] != certificate_hashes:
        raise RuntimeError("certificate hash list does not match certificate projections")
    for certificate in certificates:
        certificate_projection = dict(certificate)
        certificate_hash = certificate_projection.pop("certificate_hash")
        if canonical_sha256(certificate_projection) != certificate_hash:
            raise RuntimeError("outer-decision certificate hash replay mismatch")
        if not (
            certificate["left_outer_classification"]
            == certificate["right_outer_classification"]
            and certificate["left_terminal_tolerance_decision"]
            == certificate["right_terminal_tolerance_decision"]
            and certificate["left_outer_action"] == certificate["right_outer_action"]
            and certificate["midpoint_collapse_disposition_invariant"] is True
            and certificate["representative_branch_used_to_decide_outer_action"] is False
        ):
            raise RuntimeError("candidate certificate decision invariance mismatch")

    mesh_levels = result.mesh_levels
    subdivisions = [item["subdivisions_per_interval"] for item in mesh_levels]
    if subdivisions != [1, 2, 4, 8, 16, 32, 64]:
        raise RuntimeError("candidate mesh sequence mismatch")
    comparisons = result.convergence_comparisons
    comparison_map = {
        (item["coarse_subdivisions"], item["fine_subdivisions"]): item
        for item in comparisons
    }
    for pair in ((8, 16), (16, 32), (32, 64)):
        if comparison_map[pair]["overall_status"] != "PASS":
            raise RuntimeError(f"required convergence/headroom pair failed: {pair}")

    return {
        "result_hash": digest,
        "mesh_ledger_hash": provenance["mesh_ledger_hash"],
        "accepted_trajectory_hash": trajectory_hash,
        "accepted_cell_count": len(cells),
        "event_hashes": event_hashes,
        "certificate_hashes": certificate_hashes,
        "accepted_trajectory_provider_enclosure_count": 0,
    }


def main() -> None:
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    execution_bytes = EXECUTION_PATH.read_bytes()
    execution_sha = hashlib.sha256(execution_bytes).hexdigest()
    expected_execution_sha = evidence["candidate_rating_execution_evidence"]["sha256"]
    if execution_sha != expected_execution_sha:
        raise RuntimeError("candidate execution artifact SHA-256 mismatch")
    execution = json.loads(execution_bytes)

    if evidence["completion_request_hash"] != COMPLETION_REQUEST_HASH:
        raise RuntimeError("frozen completion request hash mismatch")
    if evidence["task168_candidate_space_hash"] != TASK168_SPACE_HASH:
        raise RuntimeError("frozen native TASK168 candidate space mismatch")
    if evidence["r2a_authority_hash"] != R2A_AUTHORITY_HASH:
        raise RuntimeError("reviewed R2A authority hash mismatch")
    if execution["completion_request_hash"] != COMPLETION_REQUEST_HASH:
        raise RuntimeError("execution evidence completion request mismatch")
    if execution["task168_candidate_space_hash"] != TASK168_SPACE_HASH:
        raise RuntimeError("execution evidence candidate space mismatch")
    if execution["public_sizing_invocation_performed"] is not False:
        raise RuntimeError("public Sizing was invoked by candidate execution")
    if execution["production_runtime_head"] != RUNTIME_HEAD:
        raise RuntimeError("candidate execution runtime head mismatch")
    if execution["production_runtime_tree"] != RUNTIME_TREE:
        raise RuntimeError("candidate execution runtime tree mismatch")

    _check_runtime_descendant()

    request_runner = _load_module(REQUEST_RUNNER_PATH, "task173_candidate_request_replay")
    requests = request_runner._build_candidate_requests()
    execution_candidates = execution["candidates"]
    evidence_candidates = evidence["candidates"]
    if set(requests) != set(EXPECTED_CANDIDATES):
        raise RuntimeError("frozen candidate set changed")

    for candidate_id, expected in EXPECTED_CANDIDATES.items():
        record = execution_candidates[candidate_id]
        summary = evidence_candidates[candidate_id]
        candidate, request = requests[candidate_id]
        request_hash = candidate_rating_request_hash(request)
        if candidate.candidate_hash != expected["candidate_hash"]:
            raise RuntimeError(f"candidate identity mismatch: {candidate_id}")
        if request_hash != expected["request_hash"]:
            raise RuntimeError(f"candidate Rating request hash mismatch: {candidate_id}")
        if record["candidate_hash"] != candidate.candidate_hash:
            raise RuntimeError(f"execution candidate hash mismatch: {candidate_id}")
        if record["candidate_rating_request_hash"] != request_hash:
            raise RuntimeError(f"execution request hash mismatch: {candidate_id}")
        if record["invocation_count"] != 1 or not record["invocation_completed"]:
            raise RuntimeError(
                f"candidate invocation was not completed exactly once: {candidate_id}"
            )
        if record["result_projection"]["request_hash"] != request_hash:
            raise RuntimeError(f"result/request binding mismatch: {candidate_id}")
        if record["result_projection"]["status"] != expected["status"]:
            raise RuntimeError(f"candidate status mismatch: {candidate_id}")

        projection = record["result_projection"]
        if expected["status"] == "BLOCKED":
            blocked = Task173BlockedResult.model_validate_json(
                json.dumps(projection, ensure_ascii=False, separators=(",", ":")),
                strict=True,
            )
            replayed_hash = _blocked_hash(projection)
            if blocked.result_hash != replayed_hash:
                raise RuntimeError("blocked candidate model/hash mismatch")
        else:
            replay = _verify_success_projection(projection)
            replayed_hash = replay["result_hash"]
            if replay["accepted_trajectory_provider_enclosure_count"] != 0:
                raise RuntimeError("accepted trajectory enclosure count is nonzero")

        if replayed_hash != expected["result_hash"]:
            raise RuntimeError(f"candidate result hash mismatch: {candidate_id}")
        if not record.get("result_hash_replay"):
            raise RuntimeError(f"execution hash replay receipt is false: {candidate_id}")
        if summary["result_hash"] != replayed_hash:
            raise RuntimeError(f"completion receipt result hash mismatch: {candidate_id}")
        print(f"CANDIDATE_RESULT_REPLAY=PASS candidate={candidate_id} status={expected['status']}")

    if evidence["public_sizing_reexecuted"] is not False:
        raise RuntimeError("public Sizing invocation boundary changed")
    if evidence["completion_request_public_sizing_invocation_count"] != 1:
        raise RuntimeError("completion request public invocation count changed")
    if evidence["second_completion_public_sizing_invocation_authorized"] is not False:
        raise RuntimeError("second completion Sizing should not be authorized")
    if evidence["candidate_full_rating_success_count"] != 1:
        raise RuntimeError("candidate success count mismatch")
    if evidence.get("completion_request_replay") != "PASS":
        raise RuntimeError("completion request replay receipt is not PASS")
    if evidence.get("candidate_rating_result_preimage_replay") != "PASS":
        raise RuntimeError("candidate Rating result preimage replay is not PASS")
    if evidence.get("full_sizing_identity_replay") != (
        "BLOCKED_CANDIDATE_A_FULL_RATING_INCOMPLETE"
    ):
        raise RuntimeError("full Sizing replay disposition does not match Candidate A blocker")

    print("COMPLETION_REQUEST_REPLAY=PASS")
    print("CANDIDATE_REQUEST_IDENTITIES_REPLAY=PASS")
    print("CANDIDATE_RATING_RESULT_PREIMAGES_REPLAY=PASS")
    print("R2A_ACCEPTED_TRAJECTORY_ENCLOSURE_COUNT=0")
    print("PUBLIC_SIZING_REEXECUTED=false")
    print("FULL_SIZING_COMPLETION=BLOCKED_CANDIDATE_A")
    print("FULL_SIZING_IDENTITY_REPLAY=BLOCKED_CANDIDATE_A_FULL_RATING_INCOMPLETE")
    print("ALL_REFERENCE_PLANE_SERIALIZATION_COMPLETION_REPLAY_PASS=true")


if __name__ == "__main__":
    main()
