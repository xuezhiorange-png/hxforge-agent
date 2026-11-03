#!/usr/bin/env python3
"""Zero-solver replay for the Task172 Decimal-context adjudication."""

from __future__ import annotations

import decimal
import hashlib
import json
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256
from hexagent.exchangers.shell_tube.task172_local_runtime.models import Task172LocalResult
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as rating

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "docs/tasks/evidence"
EVIDENCE_PATH = EVIDENCE_DIR / "TASK-173-v0.7-task172-decimal-context-adjudication-r1.json"
CALLS_DIR = EVIDENCE_DIR / "TASK-173-v0.7-task172-decimal-context-adjudication-r1-calls"
R3_EVIDENCE = EVIDENCE_DIR / "TASK-173-v0.7-candidate-a-r2-snapshot-decimal-q-probe-only-r1.json"
R2_RESULT_HASH = "ea8869a56cdd300ba42631aa967958aa01daa7e462ed7e5134b10d3d19893573"
R3_RESULT_HASH = "7e0512079ac5f28765f5685ff9ba761d56e0db277698b25ae6c26dc9984b8acc"
REQUEST_HASH = "b2472ec62e4a9e53517cdb5cc3a3f6c8d70106cd2cf34663ed2191bdaa9ce072"
START_HEAD = "fe99de204b1a626455f8447d19a80783a6ed2dcb"
RUNTIME_SOURCE_HEAD = "21386a88f8290538172e9389ed46f50c3697a426"
RUNTIME_SOURCE_TREE = "ce61a818b82f908729d2bdf4553cc27012354952"
BOUND_PATHS = (
    "src/hexagent/exchangers/shell_tube/task172_local_runtime",
    "src/hexagent/exchangers/shell_tube/tube_side_thermal",
    "src/hexagent/exchangers/shell_tube/shell_side_flow_state",
    "src/hexagent/exchangers/shell_tube/bell_delaware",
    "src/hexagent/exchangers/shell_tube/overall_heat_transfer_resistance",
    "src/hexagent/properties/coolprop_provider.py",
)
CALL_NAMES = ("baseline-1", "baseline-2", "precision100-1", "precision100-2")
RESULT_OMISSIONS = {
    "schema_version",
    "status",
    "request_hash",
    "result_hash",
    "result_id",
    "warnings",
    "blockers",
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    length = 0
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
            length += len(chunk)
    return digest.hexdigest(), length


def _require_evidence_descendant() -> None:
    head = _git("rev-parse", "HEAD")
    is_descendant = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", START_HEAD, head],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )
    if head != START_HEAD and not is_descendant:
        raise RuntimeError("current evidence head is not the frozen start head or its descendant")
    if _git("rev-parse", f"{RUNTIME_SOURCE_HEAD}^{{tree}}") != RUNTIME_SOURCE_TREE:
        raise RuntimeError("frozen runtime source tree mismatch")
    for args in (
        ["diff", "--quiet", f"{RUNTIME_SOURCE_HEAD}..{head}", "--", *BOUND_PATHS],
        ["diff", "--quiet", "HEAD", "--", *BOUND_PATHS],
        ["diff", "--cached", "--quiet", "--", *BOUND_PATHS],
    ):
        if subprocess.run(
            ["git", *args], cwd=ROOT, check=False, capture_output=True, text=True
        ).returncode:
            raise RuntimeError(
                "bound Task172/provider paths differ from frozen runtime or worktree"
            )


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected a JSON object: {path}")
    return value


def _replay_raw_artifacts(evidence: dict[str, Any]) -> None:
    rehashed_raw_count = 0
    for item in evidence["source_integrity"]["raw_artifacts"].values():
        path = ROOT / item["path"]
        if (
            item["sha256"] != item["expected_sha256"]
            or item["raw_bytes"] != item["expected_raw_bytes"]
        ):
            raise RuntimeError(f"committed R2 raw-source manifest mismatch: {path}")
        if not path.is_file():
            # The very large R2 reconstruction artifacts were intentionally
            # preserved as local, untracked source evidence, not copied into
            # this adjudication commit. Their measured raw identities remain
            # in the committed manifest.
            continue
        digest, length = _sha256_file(path)
        if digest != item["sha256"] or length != item["raw_bytes"]:
            raise RuntimeError(f"historical raw evidence identity changed: {path}")
        if digest != item["expected_sha256"] or length != item["expected_raw_bytes"]:
            raise RuntimeError(f"historical raw evidence does not match frozen receipt: {path}")
        rehashed_raw_count += 1
    print(f"R2_RAW_SOURCE_FILES_REHASHED_COUNT={rehashed_raw_count}")
    if not evidence["source_integrity"]["r2_execution_tree_exact"]:
        raise RuntimeError("R2 execution tree identity was not established")
    if not evidence["source_integrity"]["task172_runtime_dependencies_byte_identical_r2_to_r3"]:
        raise RuntimeError("Task172/provider dependencies differ between R2 and R3")
    if not evidence["source_integrity"][
        "task172_runtime_dependencies_byte_identical_r3_to_start_head"
    ]:
        raise RuntimeError("Task172/provider dependencies differ between R3 and start head")
    for section in ("source_files", "r3_evidence_files"):
        for relative, recorded in evidence["source_integrity"][section].items():
            path = ROOT / relative
            if not path.is_file():
                continue
            digest, _length = _sha256_file(path)
            if (
                digest != recorded["raw_sha256"]
                or _git("hash-object", relative) != recorded["git_blob"]
            ):
                raise RuntimeError(f"bound source/evidence artifact changed: {relative}")


def _replay_call(call: dict[str, Any], expected_precision: int) -> dict[str, Any]:
    if call.get("state") != "COMPLETE" or call.get("result_type") != "Task172LocalResult":
        raise RuntimeError(f"incomplete or unexpected native call record: {call.get('case')}")
    request_bytes = call["request_canonical_json_utf8"].encode("utf-8")
    request_projection = json.loads(request_bytes)
    if canonical_json_bytes(request_projection) != request_bytes:
        raise RuntimeError("request canonical bytes are not canonical")
    if hashlib.sha256(request_bytes).hexdigest() != call["request_canonical_json_sha256"]:
        raise RuntimeError("request canonical-byte SHA256 mismatch")
    request_hash = canonical_sha256(request_projection)
    if request_hash != REQUEST_HASH or request_hash != call["request_hash"]:
        raise RuntimeError("frozen Task172 request identity mismatch")
    context = call["context_at_validator_entry"]
    if context["prec"] != expected_precision:
        raise RuntimeError(f"{call['case']} ran under the wrong Decimal precision")
    if context["rounding"] != "ROUND_HALF_EVEN":
        raise RuntimeError("unexpected Decimal rounding mode")

    result_projection = call["result_projection"]
    result = Task172LocalResult.model_validate_json(
        json.dumps(result_projection, ensure_ascii=False, separators=(",", ":")),
        strict=True,
    )
    if result.model_dump(mode="json") != result_projection:
        raise RuntimeError("native Task172 result projection did not roundtrip exactly")
    result_hash = rating.recompute_task172_result_hash(result)
    if result_hash != result.result_hash or result_hash != call["result_hash"]:
        raise RuntimeError("native Task172 result hash did not replay")
    if call["result_hash_replay"] is not True:
        raise RuntimeError("recorded result replay flag is false")
    expected_result_projection = {
        key: value for key, value in result_projection.items() if key not in RESULT_OMISSIONS
    }
    if expected_result_projection != call["result_canonical_projection"]:
        raise RuntimeError("Task172 canonical result projection differs from full result preimage")
    key_fields = call["key_outputs_and_solver_diagnostics"]
    for field in (
        "tube_htc_w_m2_k",
        "shell_htc_w_m2_k",
        "shell_j_mu",
        "signed_q_hot_to_cold_w",
    ):
        if key_fields[field] != str(getattr(result, field)):
            raise RuntimeError(f"recorded Task172 output mismatch: {field}")
    return {"request_hash": request_hash, "result_hash": result_hash, "result": result}


def main() -> int:
    _require_evidence_descendant()
    evidence = _load_json(EVIDENCE_PATH)
    recorded_hash = evidence.pop("canonical_evidence_hash", None)
    if canonical_sha256(evidence) != recorded_hash:
        raise RuntimeError("adjudication aggregate canonical hash mismatch")
    evidence["canonical_evidence_hash"] = recorded_hash
    _replay_raw_artifacts(evidence)

    control = _load_json(CALLS_DIR / "control.json")
    ledger = [
        json.loads(line)
        for line in (CALLS_DIR / "native-task172-call-ledger.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    if len(ledger) != 4 or [item["case"] for item in ledger] != list(CALL_NAMES):
        raise RuntimeError("native Task172 call ledger is not the authorized four-call sequence")
    recorded_calls = evidence["controlled_native_task172_validations"]
    if len(recorded_calls) != 4 or evidence["native_task172_validation_count"] != 4:
        raise RuntimeError("controlled Task172 validation count is not exactly four")

    replayed: dict[str, dict[str, Any]] = {}
    for name, call in zip(CALL_NAMES, recorded_calls, strict=True):
        disk_call = _load_json(CALLS_DIR / f"{name}.json")
        if disk_call != call or disk_call["case"] != name:
            raise RuntimeError(f"aggregate and per-call receipt differ: {name}")
        if ledger[CALL_NAMES.index(name)]["request_hash"] != REQUEST_HASH:
            raise RuntimeError("call ledger request hash mismatch")
        precision = 28 if name.startswith("baseline") else 100
        replayed[name] = _replay_call(disk_call, precision)

    provider_identities = [call["provider_identity"] for call in recorded_calls]
    expected_provider = {
        "name": "CoolProp",
        "version": "8.0.0",
        "git_revision": "ae81610e7d23efc57f9d051c8e70a4d66e87537f",
        "backend": "HEOS::Water",
        "reference_state": "DEF",
        "allow_unvalidated_fluids": False,
        "near_saturation_relative_tolerance": 1e-6,
        "cache_size": 256,
        "configuration_fingerprint": "8d37dea32044ee8d",
    }
    if any(identity != expected_provider for identity in provider_identities):
        raise RuntimeError("native Task172 calls do not share the frozen provider identity")

    baseline_context = recorded_calls[0]["context_at_validator_entry"]
    hundred_context = recorded_calls[2]["context_at_validator_entry"]
    for field in ("rounding", "Emax", "Emin", "clamp", "capitals", "traps"):
        if baseline_context[field] != hundred_context[field]:
            raise RuntimeError(f"controlled contexts differ in more than precision/flags: {field}")

    if control["request_hash"] != REQUEST_HASH:
        raise RuntimeError("control record request hash mismatch")
    baseline = [replayed["baseline-1"], replayed["baseline-2"]]
    precision100 = [replayed["precision100-1"], replayed["precision100-2"]]
    baseline_hashes = [item["result_hash"] for item in baseline]
    precision100_hashes = [item["result_hash"] for item in precision100]
    if baseline_hashes != [R2_RESULT_HASH, R2_RESULT_HASH]:
        raise RuntimeError("controlled baseline did not reproduce R2 twice")
    if precision100_hashes != [R3_RESULT_HASH, R3_RESULT_HASH]:
        raise RuntimeError("controlled precision-100 context did not reproduce R3 twice")
    if baseline[0]["result"].model_dump(mode="json") != baseline[1]["result"].model_dump(
        mode="json"
    ):
        raise RuntimeError("baseline repeats are not deterministic")
    if precision100[0]["result"].model_dump(mode="json") != precision100[1]["result"].model_dump(
        mode="json"
    ):
        raise RuntimeError("precision-100 repeats are not deterministic")
    if evidence["decimal_context_causality"] != "CONFIRMED":
        raise RuntimeError("evidence does not classify context causality as confirmed")
    if evidence["task172_ambient_context_sensitivity"] != "CONFIRMED":
        raise RuntimeError("evidence does not classify ambient context sensitivity as confirmed")

    r3 = _load_json(R3_EVIDENCE)
    probes = r3["execution"]["probes"]
    if len(probes) != 65:
        raise RuntimeError("historical R3 probe count changed")
    r2_signed_q = baseline[0]["result"].signed_q_hot_to_cold_w
    derived_values = []
    with decimal.localcontext() as context:
        context.prec = 100
        for probe in probes:
            if (
                probe["task172_request_hash"] != REQUEST_HASH
                or probe["task172_result_hash"] != R3_RESULT_HASH
                or probe["task172_status"] != "VALIDATED"
            ):
                raise RuntimeError("R3 probe does not share the frozen endpoint Task172 identity")
            value = Decimal(probe["q_decimal_exact"]) - r2_signed_q
            text = str(value)
            if text != probe["F_decimal_high_precision"]:
                raise RuntimeError("offline baseline F recalculation differs from R3 stored F")
            derived_values.append((value, text))
    derived = evidence["derived_offline_recalculation"]
    minimum = min(abs(value) for value, _text in derived_values)
    if (
        derived["classification"] != "DERIVED_OFFLINE_RECALCULATION"
        or derived["native_task172_validations_performed"] != 0
        or derived["probe_count"] != 65
        or derived["all_match_stored_r3_f"] is not True
        or derived["min_abs_f_w"] != str(minimum)
        or derived["point_root_recovered"] is not False
    ):
        raise RuntimeError("65-probe offline F recalculation contract mismatch")

    print("R2_RAW_SOURCE_HASH_REPLAY=PASS")
    print("TASK172_REQUEST_PREIMAGE_REPLAY=PASS")
    print("TASK172_RESULT_PREIMAGE_HASH_REPLAY=PASS")
    print("PROVIDER_IDENTITY_BINDING=PASS")
    print("CONTROLLED_CONTEXT_SETTINGS_BINDING=PASS")
    print("CONTROLLED_REPEAT_DETERMINISM=PASS")
    print("R3_65_PROBE_OFFLINE_F_RECALCULATION=PASS")
    print(f"CROSS_RUN_REQUEST_IDENTITY={REQUEST_HASH}")
    print(f"CONTROLLED_BASELINE_RESULT_HASH={R2_RESULT_HASH}")
    print(f"CONTROLLED_100_PRECISION_RESULT_HASH={R3_RESULT_HASH}")
    print("DECIMAL_CONTEXT_CAUSALITY=CONFIRMED")
    print(f"NATIVE_TASK172_VALIDATION_COUNT={len(ledger)}")
    print(f"R3_PROBE_COUNT={len(probes)}")
    print(f"MIN_ABS_F_W={minimum}")
    print(f"EVIDENCE_CANONICAL_HASH={recorded_hash}")
    print("ALL_DECIMAL_CONTEXT_ADJUDICATION_REPLAY_PASS=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
