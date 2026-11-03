"""Replay the committed Candidate A accepted-path blocker adjudication.

This script verifies persisted identities and source-level branch bindings. It
does not invoke Candidate Rating, public Sizing, or any property solver.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

from hexagent.canonical_json import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
RECEIPT_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-candidate-a-accepted-trajectory-provider-quantization-"
    "blocker-adjudication-r1.json"
)
CANDIDATE_EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-"
    "ratings-r1.json"
)
COMPLETION_EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/TASK-173-v0.7-full-sizing-reference-plane-serialization-completion-r1.json"
)
R2A_EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a.json"
)
COMPLETION_REPLAY_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-completion-"
    "r1-replay.py"
)
SERVICE_PATH = "src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py"
START_HEAD = "e2969fe98bdabee2a72ea478a868bece4cd34216"
SERVICE_BLOB = "21f0eea0ceab099237ebc6af140858e65ab0fdf9"
CANDIDATE_EVIDENCE_SHA256 = "80e4648a91d1da2798dc608252a1a67111f1248711b8595343ab8c0739705b42"
COMPLETION_EVIDENCE_SHA256 = "8163a8eddb2582400ec4ec3492cdddcb38de2aef7a965ecaaddcd50777ec1142"
R2A_EVIDENCE_SHA256 = "aa82f61211b9ae2b501b7bd46bf2be61f789855e0051a23936f35f6a26b7db70"
CANDIDATE_A_ID = "adeab5b1-a339-5eb3-aa66-011ffe49bac0"
CANDIDATE_A_HASH = "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767"
CANDIDATE_A_REQUEST_HASH = "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7"
CANDIDATE_A_RESULT_HASH = "daf0f61109676d50e9dac2c1d5ceb9afb206b232bc039fc0253f5b1ecdba774c"


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _blocked_preimage(projection: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": projection["schema_version"],
        "status": projection["status"],
        "failure_code": projection["failure_code"],
        "failed_mesh_subdivisions": projection["failed_mesh_subdivisions"],
        "request_hash": projection["request_hash"],
        "diagnostics": projection["diagnostics"],
    }


def main() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    candidate_bytes = CANDIDATE_EVIDENCE_PATH.read_bytes()
    if hashlib.sha256(candidate_bytes).hexdigest() != CANDIDATE_EVIDENCE_SHA256:
        raise RuntimeError("candidate Rating evidence byte hash mismatch")
    if hashlib.sha256(COMPLETION_EVIDENCE_PATH.read_bytes()).hexdigest() != (
        COMPLETION_EVIDENCE_SHA256
    ):
        raise RuntimeError("completion evidence byte hash mismatch")
    if hashlib.sha256(R2A_EVIDENCE_PATH.read_bytes()).hexdigest() != R2A_EVIDENCE_SHA256:
        raise RuntimeError("reviewed R2A evidence byte hash mismatch")
    execution = json.loads(candidate_bytes)
    record = execution["candidates"][CANDIDATE_A_ID]
    projection = record["result_projection"]

    _git("merge-base", "--is-ancestor", START_HEAD, "HEAD")
    if _git("rev-parse", f"{START_HEAD}:{SERVICE_PATH}") != SERVICE_BLOB:
        raise RuntimeError("production service source blob at start head changed")
    if _git("rev-parse", f"HEAD:{SERVICE_PATH}") != SERVICE_BLOB:
        raise RuntimeError("production service changed after adjudication start")
    if receipt["start_head"] != START_HEAD:
        raise RuntimeError("receipt start head mismatch")
    if receipt["candidate_a"]["preimage_file_sha256"] != CANDIDATE_EVIDENCE_SHA256:
        raise RuntimeError("receipt candidate evidence binding mismatch")

    expected_identity = {
        "candidate_id": CANDIDATE_A_ID,
        "candidate_hash": CANDIDATE_A_HASH,
        "candidate_rating_request_hash": CANDIDATE_A_REQUEST_HASH,
        "failure_code": "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED",
        "result_hash": CANDIDATE_A_RESULT_HASH,
        "result_type": "Task173BlockedResult",
        "status": "BLOCKED",
    }
    for key, expected in expected_identity.items():
        if record[key] != expected:
            raise RuntimeError(f"Candidate A identity mismatch: {key}")

    if canonical_sha256(_blocked_preimage(projection)) != CANDIDATE_A_RESULT_HASH:
        raise RuntimeError("Candidate A blocked-result preimage hash mismatch")
    if projection["result_hash"] != CANDIDATE_A_RESULT_HASH:
        raise RuntimeError("Candidate A projection result hash mismatch")
    expected_result_id = f"urn:hxforge:task173:blocked:{CANDIDATE_A_RESULT_HASH}"
    if projection["result_id"] != expected_result_id:
        raise RuntimeError("Candidate A result ID mismatch")
    if record["recomputed_result_hash"] != CANDIDATE_A_RESULT_HASH:
        raise RuntimeError("Candidate A persisted recomputed hash mismatch")

    diagnostics = projection["diagnostics"]
    required_diagnostics = {
        f"physical_support_id=urn:hxforge:task171:candidate:{CANDIDATE_A_HASH}:support:2",
        "left_q_w=268.4228547695099",
        "right_q_w=268.42285476950997",
        "mesh_subdivisions=32",
    }
    if not required_diagnostics.issubset(set(diagnostics)):
        raise RuntimeError("Candidate A blocker diagnostics mismatch")

    candidate_b = execution["candidates"]["e152cca9-fd5d-59ca-9b46-1df574eee841"]
    if candidate_b["status"] != "VALIDATED":
        raise RuntimeError("Candidate B control result is not validated")
    b_provenance = dict(candidate_b["result_projection"]["provenance"])
    b_mesh_ledger = json.loads(b_provenance["mesh_ledger_projection"])
    b_mesh_32 = next(
        item for item in b_mesh_ledger["mesh_levels"] if item["subdivisions_per_interval"] == 32
    )
    b_r2a_32 = next(
        item
        for item in b_mesh_ledger["per_mesh_r2a_provenance"]
        if item["subdivisions_per_interval"] == 32
    )
    if (
        b_mesh_32["mesh_level_identity"]
        != "0786c3f127dadb69a2c99441a393d6cc4c1332cb74e9ce673aebb43dfc71948c"
        or b_mesh_32["total_numerical_cell_count"] != 320
        or b_mesh_32["task172_local_evaluation_count"] != 155402
        or b_mesh_32["task172_numerical_hole_count"] != 16
        or b_r2a_32["transient_provider_enclosure_event_hashes"]
        or b_r2a_32["outer_decision_certificate_hashes"]
        or b_r2a_32["accepted_trajectory_provider_enclosure_count"] != 0
    ):
        raise RuntimeError("Candidate B n=32 control evidence mismatch")

    left_q = float("268.4228547695099")
    right_q = float("268.42285476950997")
    midpoint = left_q + (right_q - left_q) / 2.0
    if not math.nextafter(left_q, math.inf) == right_q:
        raise RuntimeError("reported q endpoints are not adjacent binary64 values")
    if midpoint != right_q:
        raise RuntimeError("reported midpoint does not collapse to right endpoint")
    if left_q.hex() != "0x1.0c6c4035ce00bp+8":
        raise RuntimeError("left q binary64 encoding mismatch")
    if right_q.hex() != "0x1.0c6c4035ce00cp+8":
        raise RuntimeError("right q binary64 encoding mismatch")

    service = (ROOT / SERVICE_PATH).read_text(encoding="utf-8")
    required_source = (
        'abs(trial.residual) <= Decimal("1e-6")',
        "if midpoint == left.q_w or midpoint == right.q_w:",
        "eligible_endpoint = next(",
        'if control.mode == "DISABLED":',
        '"BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"',
        'mode="DISABLED",',
        "accepted = _valid_trajectory(",
        "selected = _solve_outer_boundary_from_trial(trial_at)",
    )
    missing = [needle for needle in required_source if needle not in service]
    if missing:
        raise RuntimeError(f"production fail-closed source anchors missing: {missing}")
    disabled_at = service.index('if control.mode == "DISABLED":')
    event_at = service.index("event = _candidate_provider_enclosure_event(", disabled_at)
    if disabled_at > event_at:
        raise RuntimeError("disabled accepted mode no longer precedes enclosure detection")

    completed = subprocess.run(
        ["uv", "run", "--locked", "--no-sync", "python", str(COMPLETION_REPLAY_PATH)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"completion identity replay failed:\n{completed.stdout}\n{completed.stderr}"
        )
    if "ALL_REFERENCE_PLANE_SERIALIZATION_COMPLETION_REPLAY_PASS=true" not in (completed.stdout):
        raise RuntimeError("completion replay did not report its final PASS marker")

    print(f"CANDIDATE_EVIDENCE_SHA256={CANDIDATE_EVIDENCE_SHA256}")
    print(f"COMPLETION_EVIDENCE_SHA256={COMPLETION_EVIDENCE_SHA256}")
    print(f"R2A_EVIDENCE_SHA256={R2A_EVIDENCE_SHA256}")
    print(f"CANDIDATE_A_BLOCKED_RESULT_HASH={CANDIDATE_A_RESULT_HASH}")
    print("CANDIDATE_A_BLOCKED_RESULT_HASH_REPLAY=PASS")
    print("CANDIDATE_B_N32_CONTROL_REPLAY=PASS")
    print(f"LEFT_Q_BINARY64_HEX={left_q.hex()}")
    print(f"RIGHT_Q_BINARY64_HEX={right_q.hex()}")
    print("Q_BINARY64_ADJACENCY_AND_MIDPOINT_COLLAPSE=PASS")
    print("ACCEPTED_PATH_DISABLED_ENCLOSURE_BRANCH=PASS")
    print("COMPLETION_REQUEST_AND_CANDIDATE_RESULT_REPLAY=PASS")
    print("FULL_RATING_REEXECUTED=false")
    print("PUBLIC_SIZING_REEXECUTED=false")
    print("FAILED_CELL_RECONSTRUCTED=PARTIAL")
    print("ROOT_CAUSE_CLASSIFICATION=CONFIRMED_REVIEWED_AUTHORITY_FAIL_CLOSED")
    print("ALL_ADJUDICATION_REPLAY_PASS=true")


if __name__ == "__main__":
    main()
