"""Replay Candidate A root-representability feasibility evidence.

This checks committed identities, source bindings, the formatting-only replay
edit, and existing persisted replay artifacts. It does not call Rating,
Sizing, TASK175, or a property solver.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
START_HEAD = "94fd650aba2a3f6591c9c9eef865fa442167b328"
RATING_SERVICE = "src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py"
TASK172_SERVICE = "src/hexagent/exchangers/shell_tube/task172_local_runtime/service.py"
FORMAT_TARGET = (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-completion-r1-replay.py"
)
CANDIDATE_EVIDENCE = (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-ratings-r1.json"
)
COMPLETION_REPLAY = ROOT / FORMAT_TARGET
FEASIBILITY_EVIDENCE = ROOT / (
    "docs/tasks/evidence/TASK-173-v0.7-candidate-a-root-representability-feasibility-r1.json"
)
CELL_DIAGNOSTIC = ROOT / (
    "docs/tasks/evidence/TASK-173-v0.7-cell-root-precision-floor-adjudication-r1.json"
)
EXPECTED_CANDIDATE_EVIDENCE_SHA256 = (
    "80e4648a91d1da2798dc608252a1a67111f1248711b8595343ab8c0739705b42"
)
EXPECTED_COMPLETION_OUTPUT_SHA256 = (
    "8ada3766a0819b1088f3c821d68d8b1753772085dfa3593573040dad2043a665"
)
EXPECTED_CELL_DIAGNOSTIC_SHA256 = "8df90d3d1998219cb570f260dadd5676ee8a7be5f44dde1f1452cc5433416f8c"
EXPECTED_RATING_SERVICE_BLOB = "21f0eea0ceab099237ebc6af140858e65ab0fdf9"
EXPECTED_TASK172_SERVICE_BLOB = "b6a1cfab5ca2c083c9ad8b39925934574b957b29"
EXPECTED_A_RESULT = "daf0f61109676d50e9dac2c1d5ceb9afb206b232bc039fc0253f5b1ecdba774c"
EXPECTED_A_REQUEST = "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7"
EXPECTED_B_RESULT = "1cecb402cc44ec2690918b3479cf6c7e4e1079eb290835122ad53ddfce657743"
EXPECTED_B_REQUEST = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"
EXPECTED_R2A_HASH = "25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e"


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _blocked_preimage(projection: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": projection["schema_version"],
        "status": projection["status"],
        "failure_code": projection["failure_code"],
        "failed_mesh_subdivisions": projection["failed_mesh_subdivisions"],
        "request_hash": projection["request_hash"],
        "diagnostics": projection["diagnostics"],
    }


def main() -> None:
    evidence = json.loads(FEASIBILITY_EVIDENCE.read_text(encoding="utf-8"))
    current_head = _git("rev-parse", "HEAD")
    _git("merge-base", "--is-ancestor", START_HEAD, current_head)

    candidate_bytes = (ROOT / CANDIDATE_EVIDENCE).read_bytes()
    if _sha256(candidate_bytes) != EXPECTED_CANDIDATE_EVIDENCE_SHA256:
        raise RuntimeError("candidate Rating execution evidence SHA mismatch")
    candidate_evidence = json.loads(candidate_bytes)
    candidates = candidate_evidence["candidates"]
    record_a = candidates["adeab5b1-a339-5eb3-aa66-011ffe49bac0"]
    record_b = candidates["e152cca9-fd5d-59ca-9b46-1df574eee841"]
    result_a = record_a["result_projection"]
    if (
        record_a["candidate_rating_request_hash"] != EXPECTED_A_REQUEST
        or result_a["request_hash"] != EXPECTED_A_REQUEST
        or result_a["result_hash"] != EXPECTED_A_RESULT
        or canonical_sha256(_blocked_preimage(result_a)) != EXPECTED_A_RESULT
        or result_a["failure_code"]
        != "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"
        or result_a["failed_mesh_subdivisions"] != 32
    ):
        raise RuntimeError("Candidate A frozen blocked result identity mismatch")
    diagnostics = set(result_a["diagnostics"])
    required = {
        "physical_support_id=urn:hxforge:task171:candidate:"
        "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767:support:2",
        "left_q_w=268.4228547695099",
        "right_q_w=268.42285476950997",
    }
    if not required.issubset(diagnostics):
        raise RuntimeError("Candidate A failed-cell diagnostic identity mismatch")
    mesh_json = next(
        item.split("=", maxsplit=1)[1]
        for item in diagnostics
        if item.startswith("task172_numerical_hole_count_by_mesh=")
    )
    mesh_counts_by_level = json.loads(mesh_json)
    mesh_counts = next(
        item for item in mesh_counts_by_level if item["subdivisions_per_interval"] == 32
    )
    if (
        mesh_counts["task172_local_evaluation_count"]
        != evidence["candidate_a_failure"]["n32_task172_local_evaluation_count"]
        or mesh_counts["task172_numerical_hole_count"]
        != evidence["candidate_a_failure"]["n32_task172_numerical_hole_count"]
    ):
        raise RuntimeError("Candidate A n=32 mesh summary mismatch")
    left, right = float("268.4228547695099"), float("268.42285476950997")
    if (
        math.nextafter(left, math.inf) != right
        or left + (right - left) / 2.0 != right
        or left.hex() != "0x1.0c6c4035ce00bp+8"
        or right.hex() != "0x1.0c6c4035ce00cp+8"
    ):
        raise RuntimeError("Candidate A binary64 bracket replay mismatch")

    if (
        record_b["candidate_rating_request_hash"] != EXPECTED_B_REQUEST
        or record_b["result_hash"] != EXPECTED_B_RESULT
        or record_b["status"] != "VALIDATED"
    ):
        raise RuntimeError("Candidate B control identity mismatch")
    provenance_b = dict(record_b["result_projection"]["provenance"])
    mesh_ledger_b = json.loads(provenance_b["mesh_ledger_projection"])
    mesh_b_32 = next(
        item for item in mesh_ledger_b["mesh_levels"] if item["subdivisions_per_interval"] == 32
    )
    r2a_b_32 = next(
        item
        for item in mesh_ledger_b["per_mesh_r2a_provenance"]
        if item["subdivisions_per_interval"] == 32
    )
    if (
        mesh_b_32["mesh_level_identity"] != evidence["candidate_b_control"]["n32_mesh_identity"]
        or mesh_b_32["total_numerical_cell_count"]
        != evidence["candidate_b_control"]["n32_cell_count"]
        or mesh_b_32["task172_local_evaluation_count"]
        != evidence["candidate_b_control"]["n32_task172_evaluation_count"]
        or mesh_b_32["task172_numerical_hole_count"]
        != evidence["candidate_b_control"]["n32_task172_numerical_hole_count"]
        or r2a_b_32["transient_provider_enclosure_event_hashes"]
        or r2a_b_32["outer_decision_certificate_hashes"]
        or r2a_b_32["accepted_trajectory_provider_enclosure_count"] != 0
    ):
        raise RuntimeError("Candidate B n=32 control ledger mismatch")

    old_service_blob = _git("rev-parse", f"{START_HEAD}:{RATING_SERVICE}")
    old_task172_blob = _git("rev-parse", f"{START_HEAD}:{TASK172_SERVICE}")
    if old_service_blob != EXPECTED_RATING_SERVICE_BLOB:
        raise RuntimeError("frozen Rating service blob mismatch")
    if old_task172_blob != EXPECTED_TASK172_SERVICE_BLOB:
        raise RuntimeError("frozen TASK172 service blob mismatch")
    if _git("rev-parse", f"HEAD:{RATING_SERVICE}") != EXPECTED_RATING_SERVICE_BLOB:
        raise RuntimeError("Rating production code changed after start head")
    if _git("rev-parse", f"HEAD:{TASK172_SERVICE}") != EXPECTED_TASK172_SERVICE_BLOB:
        raise RuntimeError("TASK172 production code changed after start head")
    rating_source = (ROOT / RATING_SERVICE).read_text(encoding="utf-8")
    task172_source = (ROOT / TASK172_SERVICE).read_text(encoding="utf-8")
    for anchor in (
        "class _CellTrial:\n    q_w: float",
        "def _cell_evaluation(\n    q_w: float,",
        'abs(trial.residual) <= Decimal("1e-6")',
        "midpoint = left.q_w + (right.q_w - left.q_w) / 2.0",
        "residual = _d(q) - evaluation.task172_result.signed_q_hot_to_cold_w",
        "provider_enthalpy = Decimal(str(float(enthalpy_j_kg)))",
        "enthalpy_j_kg=float(enthalpy_j_kg)",
        'if control.mode == "DISABLED":',
        '"BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"',
    ):
        if anchor not in rating_source:
            raise RuntimeError(f"TASK173 source-contract anchor missing: {anchor}")
    for anchor in (
        "np.asarray([q_seed, wall_inner_seed, wall_outer_seed], dtype=float)",
        "max_nfev=6",
        '"signed_q_hot_to_cold_w": Decimal(str(q))',
    ):
        if anchor not in task172_source:
            raise RuntimeError(f"TASK172 source-contract anchor missing: {anchor}")

    old_formatter_target = subprocess.run(
        ["git", "show", f"{START_HEAD}:{FORMAT_TARGET}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    new_formatter_target = (ROOT / FORMAT_TARGET).read_text(encoding="utf-8")
    old_ast = ast.dump(ast.parse(old_formatter_target), include_attributes=False)
    new_ast = ast.dump(ast.parse(new_formatter_target), include_attributes=False)
    ast_hash = _sha256(old_ast.encode("utf-8"))
    if old_ast != new_ast or ast_hash != evidence["format_only_change"]["ast_sha256"]:
        raise RuntimeError("completion replay AST changed")
    if (
        _sha256((ROOT / FORMAT_TARGET).read_bytes())
        != evidence["format_only_change"]["post_format_raw_sha256"]
    ):
        raise RuntimeError("formatted replay script source hash mismatch")
    old_formatter_bytes = subprocess.run(
        ["git", "show", f"{START_HEAD}:{FORMAT_TARGET}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    if _sha256(old_formatter_bytes) != evidence["format_only_change"]["pre_format_raw_sha256"]:
        raise RuntimeError("pre-format replay script source hash mismatch")

    evidence_bindings = evidence["evidence_bindings"]
    for key, path in (
        (
            "completion_evidence_sha256",
            "docs/tasks/evidence/TASK-173-v0.7-full-sizing-reference-plane-serialization-completion-r1.json",
        ),
        (
            "r2a_candidate_evidence_sha256",
            "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a.json",
        ),
    ):
        if _sha256((ROOT / path).read_bytes()) != evidence_bindings[key]:
            raise RuntimeError(f"bound evidence SHA mismatch: {path}")

    cell_bytes = CELL_DIAGNOSTIC.read_bytes()
    if _sha256(cell_bytes) != EXPECTED_CELL_DIAGNOSTIC_SHA256:
        raise RuntimeError("historical cell diagnostic SHA mismatch")
    cell_diagnostic = json.loads(cell_bytes)
    target_a = cell_diagnostic["captures"][0]
    if not (
        target_a["candidate_id"] == "adeab5b1-a339-5eb3-aa66-011ffe49bac0"
        and target_a["mesh_subdivisions"] == 1
        and target_a["physical_support_id"].endswith(":support:1")
    ):
        raise RuntimeError("historical diagnostic distinction mismatch")
    if evidence["non_target_historical_diagnostic"]["used_as_target_cell_substitute"]:
        raise RuntimeError("non-target diagnostic was incorrectly substituted")

    replay = subprocess.run(
        [sys.executable, str(COMPLETION_REPLAY)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if replay.returncode != 0:
        raise RuntimeError(f"completion identity replay failed: {replay.stderr.strip()}")
    if _sha256(replay.stdout.encode("utf-8")) != EXPECTED_COMPLETION_OUTPUT_SHA256:
        raise RuntimeError("completion replay behavior/output hash mismatch")
    if "PUBLIC_SIZING_REEXECUTED=false" not in replay.stdout:
        raise RuntimeError("completion replay did not affirm no public Sizing")

    if evidence["reviewed_authority"]["canonical_hash"] != EXPECTED_R2A_HASH:
        raise RuntimeError("reviewed R2A authority identity mismatch")
    if evidence["execution_boundary"]["production_numerical_behavior_changed"]:
        raise RuntimeError("production numerical behavior change was recorded")

    print("CANDIDATE_A_BLOCKED_RESULT_HASH_REPLAY=PASS")
    print("CANDIDATE_B_CONTROL_IDENTITY_REPLAY=PASS")
    print("TARGET_Q_BINARY64_ADJACENCY_AND_COLLAPSE=PASS")
    print("PRODUCTION_SOURCE_BLOB_BINDING=PASS")
    print("FORMAT_ONLY_AST_IDENTITY_REPLAY=PASS")
    print("COMPLETION_REPLAY_BEHAVIOR_HASH=PASS")
    print("NON_TARGET_DIAGNOSTIC_NOT_SUBSTITUTED=PASS")
    print("ROOT_EXISTENCE_FOR_EXACT_TARGET_CELL=NOT_ESTABLISHED")
    print("RATING_OR_SIZING_REEXECUTED=false")
    print("ALL_ROOT_FEASIBILITY_EVIDENCE_REPLAY_PASS=true")


if __name__ == "__main__":
    main()
