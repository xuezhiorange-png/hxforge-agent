#!/usr/bin/env python3
"""Controlled Task172 Decimal-context identity adjudication.

This is an evidence-only runner. It rehydrates the exact saved R2 RIGHT request
and performs at most four isolated native Task172 validations: two under the
saved R2 ambient Decimal configuration and two under the R3 precision-100
configuration. It never runs Task173 Rating or Sizing.
"""

from __future__ import annotations

import argparse
import decimal
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256
from hexagent.exchangers.shell_tube.task172_local_runtime import (
    service as task172_service,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172BlockedResult,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import (
    service as rating,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

ROOT = Path(__file__).resolve().parents[3]
START_HEAD = "fe99de204b1a626455f8447d19a80783a6ed2dcb"
R2_EXECUTION_HEAD = "2348b977e71d8f88f4107fceab35392962f8aa92"
RUNTIME_SOURCE_HEAD = "21386a88f8290538172e9389ed46f50c3697a426"
RUNTIME_SOURCE_TREE = "ce61a818b82f908729d2bdf4553cc27012354952"
R2_REQUEST_HASH = "b2472ec62e4a9e53517cdb5cc3a3f6c8d70106cd2cf34663ed2191bdaa9ce072"
R2_RESULT_HASH = "ea8869a56cdd300ba42631aa967958aa01daa7e462ed7e5134b10d3d19893573"
R3_RESULT_HASH = "7e0512079ac5f28765f5685ff9ba761d56e0db277698b25ae6c26dc9984b8acc"
CANDIDATE_RATING_REQUEST_HASH = "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7"
EVIDENCE_BASE = ROOT / "docs/tasks/evidence"
R2_EXECUTION = EVIDENCE_BASE / (
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2.json"
)
R2_CHECKPOINT = EVIDENCE_BASE / (
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2-execution"
    "/checkpoint.json"
)
R2_TRACE = EVIDENCE_BASE / (
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2-execution/trace.jsonl"
)
R3_RUNNER = EVIDENCE_BASE / ("TASK-173-v0.7-candidate-a-r2-snapshot-decimal-q-probe-only-r1.py")
R3_PREFLIGHT = EVIDENCE_BASE / (
    "TASK-173-v0.7-candidate-a-r2-snapshot-decimal-q-probe-only-r1-preflight-r2.json"
)
R3_EVIDENCE = EVIDENCE_BASE / ("TASK-173-v0.7-candidate-a-r2-snapshot-decimal-q-probe-only-r1.json")
R1_RUNNER = EVIDENCE_BASE / (
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r1.py"
)
EVIDENCE_PATH = EVIDENCE_BASE / ("TASK-173-v0.7-task172-decimal-context-adjudication-r1.json")
CALLS_DIR = EVIDENCE_BASE / ("TASK-173-v0.7-task172-decimal-context-adjudication-r1-calls")
CONTROL_PATH = CALLS_DIR / "control.json"
LEDGER_PATH = CALLS_DIR / "native-task172-call-ledger.jsonl"
EXPECTED_RAW = {
    "r2_execution": {
        "path": R2_EXECUTION,
        "bytes": 471057121,
        "sha256": "59e4e8218f61551ae00421ebcc88cf4ea8870cadd5bbca22420caa9c8930c6fe",
    },
    "r2_checkpoint": {
        "path": R2_CHECKPOINT,
        "bytes": 471036749,
        "sha256": "87f0391c4ae26008a6bfe93c6e7a1f1657e1925658550dbd0ca55da96e9f138f",
    },
    "r2_trace": {
        "path": R2_TRACE,
        "bytes": 311208673,
        "sha256": "e8c719c48842ecb5369a63a375c5004af81152c260c07dbc96a218c9113d1618",
    },
}
R3_CONTEXT_PRECISION = 100
TASK172_BOUND_PATHS = (
    "src/hexagent/exchangers/shell_tube/task172_local_runtime",
    "src/hexagent/exchangers/shell_tube/tube_side_thermal",
    "src/hexagent/exchangers/shell_tube/shell_side_flow_state",
    "src/hexagent/exchangers/shell_tube/bell_delaware",
    "src/hexagent/exchangers/shell_tube/overall_heat_transfer_resistance",
    "src/hexagent/properties/coolprop_provider.py",
)


def _git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    length = 0
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
            length += len(chunk)
    return digest.hexdigest(), length


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _context_projection(context: decimal.Context | None = None) -> dict[str, Any]:
    selected = decimal.getcontext() if context is None else context
    return {
        "prec": selected.prec,
        "rounding": selected.rounding,
        "Emax": selected.Emax,
        "Emin": selected.Emin,
        "clamp": selected.clamp,
        "capitals": selected.capitals,
        "traps": {signal.__name__: bool(flag) for signal, flag in selected.traps.items()},
        "flags": {signal.__name__: bool(flag) for signal, flag in selected.flags.items()},
    }


def _context_from_projection(projection: dict[str, Any]) -> decimal.Context:
    context = decimal.Context(
        prec=int(projection["prec"]),
        rounding=projection["rounding"],
        Emin=int(projection["Emin"]),
        Emax=int(projection["Emax"]),
        capitals=int(projection["capitals"]),
        clamp=int(projection["clamp"]),
    )
    signals = {signal.__name__: signal for signal in context.traps}
    for name, value in projection["traps"].items():
        context.traps[signals[name]] = bool(value)
    for name, value in projection["flags"].items():
        context.flags[signals[name]] = bool(value)
    return context


def _r2_contexts_from_prefix() -> tuple[dict[str, Any], dict[str, Any]]:
    prefix = R2_EXECUTION.read_bytes()[:200_000].decode("utf-8")
    decoder = json.JSONDecoder()
    snapshots = []
    for key in ("ambient_before_n32_reconstruction", "ambient_after_n32_reconstruction"):
        marker = f'"{key}":'
        offset = prefix.find(marker)
        if offset < 0:
            raise RuntimeError(f"R2 execution prefix lacks {key}")
        offset += len(marker)
        while prefix[offset].isspace():
            offset += 1
        value, _end = decoder.raw_decode(prefix, offset)
        if "decimal_context" not in value:
            raise RuntimeError(f"R2 execution {key} lacks Decimal context")
        snapshots.append(value)
    return snapshots[0], snapshots[1]


def _load_r3_module() -> Any:
    spec = importlib.util.spec_from_file_location("task173_r3_probe_context_review", R3_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import the frozen R3 helper source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_basis() -> tuple[dict[str, Any], dict[str, Any], Any, Any, dict[str, Any]]:
    preflight = json.loads(R3_PREFLIGHT.read_text(encoding="utf-8"))
    preflight_hash = preflight.pop("canonical_preflight_hash", None)
    if canonical_sha256(preflight) != preflight_hash:
        raise RuntimeError("R3 preflight canonical identity replay failed")
    preflight["canonical_preflight_hash"] = preflight_hash
    evidence = json.loads(R3_EVIDENCE.read_text(encoding="utf-8"))
    evidence_hash = evidence.pop("canonical_evidence_hash", None)
    if canonical_sha256(evidence) != evidence_hash:
        raise RuntimeError("R3 evidence canonical identity replay failed")
    evidence["canonical_evidence_hash"] = evidence_hash
    if (
        preflight.get("captured_head") != "bfe4566229e7f70b234f6d1dcf9874cea4b1068f"
        or preflight.get("candidate_rating_request_hash") != CANDIDATE_RATING_REQUEST_HASH
        or preflight.get("r2a_authority_hash")
        != "25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e"
        or evidence.get("execution", {}).get("decimal_q_probe_count") != 65
        or evidence.get("execution", {}).get("point_root_recovered") is not False
    ):
        raise RuntimeError("R2/R3 frozen source identities do not match adjudication inputs")
    r3 = _load_r3_module()
    endpoint = preflight["rehydration_basis"]["right_endpoint"]
    request, expected_result, endpoint_facts = r3._endpoint_native(endpoint, "RIGHT")
    if (
        type(request) is not CandidateTask172LocalRequest
        or type(expected_result) is not Task172LocalResult
        or rating.recompute_task172_request_hash(request) != R2_REQUEST_HASH
        or rating.recompute_task172_result_hash(expected_result) != R2_RESULT_HASH
        or endpoint_facts["task172_request_hash"] != R2_REQUEST_HASH
        or endpoint_facts["task172_result_hash"] != R2_RESULT_HASH
    ):
        raise RuntimeError("saved R2 RIGHT native request/result identity mismatch")
    first_probe = evidence["execution"]["probes"][0]
    r3_probe_replay = r3._probe_projection_replay(first_probe)
    if (
        first_probe["task172_request_hash"] != R2_REQUEST_HASH
        or first_probe["task172_result_hash"] != R3_RESULT_HASH
        or r3_probe_replay["result_hash"] != R3_RESULT_HASH
    ):
        raise RuntimeError("saved R3 first probe does not replay the frozen cross-run result")
    return (
        preflight,
        evidence,
        request,
        expected_result,
        {
            "right_endpoint": endpoint,
            "left_endpoint": preflight["rehydration_basis"]["left_endpoint"],
            "right_endpoint_facts": endpoint_facts,
            "r3_first_probe": first_probe,
            "r3_first_probe_replay": r3_probe_replay,
        },
    )


def _source_and_raw_integrity() -> dict[str, Any]:
    raw = {}
    for name, expected in EXPECTED_RAW.items():
        digest, length = _sha256_file(expected["path"])
        raw[name] = {
            "path": str(expected["path"].relative_to(ROOT)),
            "raw_bytes": length,
            "sha256": digest,
            "expected_raw_bytes": expected["bytes"],
            "expected_sha256": expected["sha256"],
            "match": length == expected["bytes"] and digest == expected["sha256"],
        }
        if not raw[name]["match"]:
            raise RuntimeError(f"historical R2 raw artifact changed: {name}")
    code_paths = (
        R3_RUNNER,
        R1_RUNNER,
        ROOT / "src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py",
        ROOT / "src/hexagent/exchangers/shell_tube/task172_local_runtime/service.py",
        ROOT / "src/hexagent/exchangers/shell_tube/task172_local_runtime/models.py",
        ROOT / "src/hexagent/exchangers/shell_tube/tube_side_thermal/single_phase.py",
        ROOT / "src/hexagent/exchangers/shell_tube/tube_side_thermal/decimal_primitives.py",
        ROOT / "src/hexagent/exchangers/shell_tube/shell_side_flow_state/formulas.py",
        ROOT / "src/hexagent/exchangers/shell_tube/bell_delaware/heat_transfer.py",
        ROOT / "src/hexagent/exchangers/shell_tube/bell_delaware/decimal_math.py",
        ROOT / "src/hexagent/properties/coolprop_provider.py",
    )
    source_hashes = {}
    for path in code_paths:
        relative = str(path.relative_to(ROOT))
        source_hashes[relative] = {
            "raw_sha256": _sha256_file(path)[0],
            "git_blob": _git("hash-object", relative),
        }
    evidence_file_hashes = {}
    for path in (R3_PREFLIGHT, R3_EVIDENCE):
        relative = str(path.relative_to(ROOT))
        evidence_file_hashes[relative] = {
            "raw_sha256": _sha256_file(path)[0],
            "git_blob": _git("hash-object", relative),
        }
    diff = subprocess.run(
        [
            "git",
            "diff",
            "--name-status",
            R2_EXECUTION_HEAD,
            RUNTIME_SOURCE_HEAD,
            "--",
            *TASK172_BOUND_PATHS,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    runtime_diff_current = subprocess.run(
        [
            "git",
            "diff",
            "--name-status",
            RUNTIME_SOURCE_HEAD,
            START_HEAD,
            "--",
            *TASK172_BOUND_PATHS,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    source_tree = _git("rev-parse", f"{RUNTIME_SOURCE_HEAD}^{{tree}}")
    source_is_ancestor = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", RUNTIME_SOURCE_HEAD, START_HEAD],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )
    r2_execution_tree = _git("rev-parse", f"{R2_EXECUTION_HEAD}^{{tree}}")
    return {
        "raw_artifacts": raw,
        "source_files": source_hashes,
        "r3_evidence_files": evidence_file_hashes,
        "r2_execution_head": R2_EXECUTION_HEAD,
        "r2_execution_tree_actual": r2_execution_tree,
        "r2_execution_tree_expected_from_r2_ambient_receipt": (
            "f6b25dd9078f0637c14797089d6fd3354b26a3e1"
        ),
        "r2_execution_tree_exact": (
            r2_execution_tree == "f6b25dd9078f0637c14797089d6fd3354b26a3e1"
        ),
        "runtime_source_tree_actual": source_tree,
        "runtime_source_tree_expected": RUNTIME_SOURCE_TREE,
        "runtime_source_tree_exact": source_tree == RUNTIME_SOURCE_TREE,
        "runtime_source_head_is_ancestor_of_start_head": source_is_ancestor,
        "r2_execution_to_r3_runtime_task172_dependency_diff": diff,
        "r3_runtime_to_start_head_task172_dependency_diff": runtime_diff_current,
        "task172_runtime_dependencies_byte_identical_r2_to_r3": not diff,
        "task172_runtime_dependencies_byte_identical_r3_to_start_head": not runtime_diff_current,
    }


def _append_ledger(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _run_validator_at_context(
    request: CandidateTask172LocalRequest,
    provider: CoolPropProvider,
    context: decimal.Context,
    validator: Any,
) -> Any:
    """Run one unmodified native validator under an explicit context copy."""
    with decimal.localcontext(context):
        return validator(request, provider)


def _preflight_context_fence(r2_context: dict[str, Any]) -> dict[str, Any]:
    baseline = _context_from_projection(r2_context)
    seen: list[dict[str, Any]] = []

    def stub(_request: Any, _provider: Any) -> str:
        seen.append(_context_projection())
        return "stub-returned"

    with decimal.localcontext() as high_precision:
        high_precision.prec = 100
        result = _run_validator_at_context(None, None, baseline, stub)
        enclosing = _context_projection()
    if (
        result != "stub-returned"
        or len(seen) != 1
        or seen[0]["prec"] != int(r2_context["prec"])
        or enclosing["prec"] != 100
    ):
        raise RuntimeError("explicit Task172 context fence regression failed")
    return {
        "context_fence_stub_invocation_count": 1,
        "outer_context_precision_during_test": enclosing["prec"],
        "validator_context_precision": seen[0]["prec"],
        "pass": True,
    }


def _context_for_case(control: dict[str, Any], case_name: str) -> decimal.Context:
    if case_name.startswith("baseline"):
        projection = control["r2_baseline_context"]["decimal_context"]
    elif case_name.startswith("precision100"):
        projection = dict(control["r2_baseline_context"]["decimal_context"])
        projection["prec"] = R3_CONTEXT_PRECISION
        # A fresh R3 process creates its localcontext from the interpreter
        # default. The historical call-time flags were not captured.
        projection["flags"] = {name: False for name in projection["flags"]}
    else:
        raise ValueError(f"unknown context case: {case_name}")
    return _context_from_projection(projection)


def _invoke_one(case_name: str) -> None:
    if _git("rev-parse", "HEAD") != START_HEAD:
        raise RuntimeError("native comparison calls require the exact frozen start HEAD")
    if not CONTROL_PATH.is_file():
        raise RuntimeError("controlled execution preflight is missing")
    control = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    authorized_cases = (
        "baseline-1",
        "baseline-2",
        "precision100-1",
        "precision100-2",
    )
    if case_name not in authorized_cases:
        raise RuntimeError(f"case is outside the frozen four-call plan: {case_name}")
    ledger_rows = [
        json.loads(line) for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines()
    ]
    if (
        len(ledger_rows) > 6
        or not ledger_rows
        or ledger_rows[-1].get("case") != case_name
        or ledger_rows[-1].get("sequence") != len(ledger_rows)
        or any(row.get("case") == case_name for row in ledger_rows[:-1])
    ):
        raise RuntimeError("Task172 call ledger does not authorize this unique validation")
    target_path = CALLS_DIR / f"{case_name}.json"
    if target_path.exists():
        raise RuntimeError(f"refusing repeat of already-recorded Task172 call {case_name}")
    if not control.get("zero_solver_and_identity_gates_pass"):
        raise RuntimeError("pre-execution identity gates did not pass")

    r3 = _load_r3_module()
    preflight = json.loads(R3_PREFLIGHT.read_text(encoding="utf-8"))
    request, r2_result, endpoint_facts = r3._endpoint_native(
        preflight["rehydration_basis"]["right_endpoint"], "RIGHT"
    )
    if rating.recompute_task172_request_hash(request) != R2_REQUEST_HASH:
        raise RuntimeError("Task172 request identity did not replay immediately before call")
    provider = CoolPropProvider()
    provider_identity = {
        "name": provider.name,
        "version": provider.version,
        "git_revision": provider.git_revision,
        "backend": "HEOS::Water",
        "reference_state": provider.reference_state_policy.value,
        "allow_unvalidated_fluids": provider.allow_unvalidated_fluids,
        "near_saturation_relative_tolerance": provider.near_saturation_relative_tolerance,
        "cache_size": provider.cache_size,
        "configuration_fingerprint": provider._construction_fingerprint,
    }
    if (
        provider.version != "8.0.0"
        or provider.git_revision != "ae81610e7d23efc57f9d051c8e70a4d66e87537f"
        or provider._construction_fingerprint != "8d37dea32044ee8d"
        or provider.reference_state_policy.value != "DEF"
    ):
        raise RuntimeError("CoolProp provider identity differs from frozen R2/R3 provider")

    context = _context_for_case(control, case_name)
    request_preimage = task172_service._request_projection(request)
    request_canonical_bytes = canonical_json_bytes(request_preimage)
    request_hash = rating.recompute_task172_request_hash(request)
    if request_hash != R2_REQUEST_HASH:
        raise RuntimeError("canonical Task172 request hash mismatch")
    started_at = datetime.now(UTC).isoformat()
    started_record = {
        "schema_version": "task173.task172-decimal-context-call.v1",
        "case": case_name,
        "state": "VALIDATION_STARTED",
        "started_at_utc": started_at,
        "git_head": _git("rev-parse", "HEAD"),
        "git_tree": _git("rev-parse", "HEAD^{tree}"),
        "runtime_source_head": RUNTIME_SOURCE_HEAD,
        "runtime_source_tree": RUNTIME_SOURCE_TREE,
        "request_hash": request_hash,
        "request_projection": request_preimage,
        "request_canonical_json_utf8": request_canonical_bytes.decode("utf-8"),
        "request_canonical_json_sha256": _sha256_bytes(request_canonical_bytes),
        "provider_identity": provider_identity,
        "context_at_validator_entry": _context_projection(context),
        "historical_r2_endpoint_result_hash": endpoint_facts["task172_result_hash"],
    }
    _atomic_json(target_path, started_record)
    wall_start = time.monotonic()
    observed_context: dict[str, Any] = {}

    def native_call(active_request: Any, active_provider: Any) -> Any:
        observed_context["at_validator_entry"] = _context_projection()
        try:
            return rating.task172_validate_candidate(active_request, active_provider)
        finally:
            observed_context["after_validator"] = _context_projection()

    try:
        result = _run_validator_at_context(request, provider, context, native_call)
    except BaseException as exc:
        failed_record = dict(started_record)
        failed_record.update(
            {
                "state": "VALIDATION_RAISED",
                "completed_at_utc": datetime.now(UTC).isoformat(),
                "elapsed_seconds": time.monotonic() - wall_start,
                "context_at_validator_entry": observed_context.get("at_validator_entry"),
                "context_after_validator": observed_context.get("after_validator"),
                "exception_type": type(exc).__name__,
                "exception_text": str(exc),
            }
        )
        _atomic_json(target_path, failed_record)
        raise
    elapsed = time.monotonic() - wall_start
    result_type = type(result).__name__
    if type(result) in (Task172LocalResult, Task172BlockedResult):
        result_projection = result.model_dump(mode="json")
    else:
        result_projection = None
    completed_record = dict(started_record)
    completed_record.update(
        {
            "state": "RESULT_PREIMAGE_PERSISTED",
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "elapsed_seconds": elapsed,
            "context_at_validator_entry": observed_context["at_validator_entry"],
            "context_after_validator": observed_context["after_validator"],
            "result_type": result_type,
            "result_projection": result_projection,
            "result_hash": None,
            "result_hash_replay": None,
            "result_id": getattr(result, "result_id", None),
            "blocked_result_hash": getattr(result, "blocked_result_hash", None),
            "failure_code": getattr(result, "failure_code", None),
            "field_path": getattr(result, "field_path", None),
        }
    )
    _atomic_json(target_path, completed_record)
    if type(result) is Task172LocalResult:
        result_hash = rating.recompute_task172_result_hash(result)
        result_hash_replay = result_hash == result.result_hash
        result_id = result.result_id
        key_outputs = {
            "tube_htc_w_m2_k": str(result.tube_htc_w_m2_k),
            "shell_htc_w_m2_k": str(result.shell_htc_w_m2_k),
            "shell_j_mu": str(result.shell_j_mu),
            "signed_q_hot_to_cold_w": str(result.signed_q_hot_to_cold_w),
            "residual_vector_w": [str(value) for value in result.residual_vector_w],
            "solver_status": result.solver_status,
            "solver_nfev": result.solver_nfev,
            "residual_callback_count": result.residual_callback_count,
            "residual_acceptance_state": result.residual_acceptance_state,
            "tube_reynolds_number": str(result.tube_reynolds_number),
            "tube_prandtl_number_bulk": str(result.tube_prandtl_number_bulk),
            "shell_reynolds_number": str(result.shell_reynolds_number),
            "shell_prandtl_number": str(result.shell_prandtl_number),
            "tube_inner_film_resistance_k_w": str(result.inner_film_resistance_k_w),
            "outer_film_resistance_k_w": str(result.outer_film_resistance_k_w),
        }
        status = result.status
    elif type(result) is Task172BlockedResult:
        result_hash = rating.recompute_task172_blocked_result_hash(result)
        result_hash_replay = result_hash == result.blocked_result_hash
        result_id = None
        key_outputs = {
            "failure_code": result.failure_code,
            "field_path": result.field_path,
            "diagnostics": list(result.diagnostics),
        }
        status = result.status
    else:
        raise TypeError(f"unknown native Task172 result type: {result_type}")
    completed_record.update(
        {
            "state": "COMPLETE",
            "status": status,
            "result_hash": result_hash,
            "result_hash_replay": result_hash_replay,
            "result_id": result_id,
            "key_outputs_and_solver_diagnostics": key_outputs,
            "result_canonical_projection": (
                task172_service._result_projection(result.model_dump(mode="python"))
                if type(result) is Task172LocalResult
                else None
            ),
        }
    )
    _atomic_json(target_path, completed_record)
    print(json.dumps({"case": case_name, "result_hash": result_hash, "elapsed_seconds": elapsed}))


def _execute() -> dict[str, Any]:
    if _git("rev-parse", "HEAD") != START_HEAD:
        raise RuntimeError(f"execution requires exact start head {START_HEAD}")
    if EVIDENCE_PATH.exists() or CALLS_DIR.exists():
        raise RuntimeError("adjudication outputs already exist; refusing any additional calls")
    worktree_diff = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *TASK172_BOUND_PATHS],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if worktree_diff.returncode != 0:
        raise RuntimeError("tracked Task172/provider runtime paths are dirty")
    staged_diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *TASK172_BOUND_PATHS],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if staged_diff.returncode != 0:
        raise RuntimeError("staged Task172/provider runtime paths are dirty")

    before, after = _r2_contexts_from_prefix()
    r2_context = before["decimal_context"]
    r2_after_context = after["decimal_context"]
    context_settings = ("prec", "rounding", "Emax", "Emin", "clamp", "capitals", "traps")
    if any(r2_context[key] != r2_after_context[key] for key in context_settings):
        raise RuntimeError(
            "R2 Decimal context computational settings changed during reconstruction"
        )
    preflight, r3_evidence, request, r2_result, basis_facts = _load_basis()
    raw_and_source = _source_and_raw_integrity()
    if not (
        raw_and_source["task172_runtime_dependencies_byte_identical_r2_to_r3"]
        and raw_and_source["task172_runtime_dependencies_byte_identical_r3_to_start_head"]
        and raw_and_source["runtime_source_tree_exact"]
        and raw_and_source["runtime_source_head_is_ancestor_of_start_head"]
        and raw_and_source["r2_execution_tree_exact"]
    ):
        raise RuntimeError("Task172/provider implementation differs across bound source heads")
    if rating.recompute_task172_request_hash(request) != R2_REQUEST_HASH:
        raise RuntimeError("exact R2 RIGHT request did not replay before controlled calls")
    context_test = _preflight_context_fence(r2_context)
    CALLS_DIR.mkdir(parents=True, exist_ok=False)

    fresh_default = _context_projection()
    control = {
        "schema_version": "task173.task172-decimal-context-control.v1",
        "start_head": START_HEAD,
        "request_hash": R2_REQUEST_HASH,
        "r2_baseline_context": before,
        "r2_after_context": after,
        "r3_actual_context_capture": "NOT_CAPTURED_IN_HISTORICAL_R3_RECORD",
        "r3_call_precision_source": {
            "runner": str(R3_RUNNER.relative_to(ROOT)),
            "outer_localcontext_line": 1277,
            "precision_assignment_line": 1278,
            "run_one_invoked_inside_that_context": True,
            "probe_helper_localcontext_70_exits_before_validator_call": True,
        },
        "fresh_process_default_context_before_any_call": fresh_default,
        "r2_flags_at_actual_validator_call": (
            "NOT_CAPTURED; saved pre/post-run flags retained separately"
        ),
        "preflight_context_fence": context_test,
        "zero_solver_and_identity_gates_pass": True,
        "authorized_native_task172_call_plan": [
            "baseline-1",
            "baseline-2",
            "precision100-1",
            "precision100-2",
        ],
        "native_task172_validation_limit": 6,
    }
    _atomic_json(CONTROL_PATH, control)
    planned = (
        "baseline-1",
        "baseline-2",
        "precision100-1",
        "precision100-2",
    )
    invocation_receipts = []
    for index, case_name in enumerate(planned, start=1):
        if index > 6:
            raise RuntimeError("native Task172 call limit exceeded")
        _append_ledger(
            LEDGER_PATH,
            {
                "sequence": index,
                "case": case_name,
                "request_hash": R2_REQUEST_HASH,
                "state": "CALL_AUTHORIZED_AND_STARTING",
                "recorded_at_utc": datetime.now(UTC).isoformat(),
            },
        )
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--invoke-one", case_name],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode:
            raise RuntimeError(
                f"controlled Task172 call {case_name} failed after its durable start record: "
                f"{completed.stderr.strip()}"
            )
        call_record = json.loads((CALLS_DIR / f"{case_name}.json").read_text(encoding="utf-8"))
        if call_record.get("state") != "COMPLETE" or not call_record.get("result_hash_replay"):
            raise RuntimeError(f"controlled Task172 call {case_name} did not complete/replay")
        invocation_receipts.append(call_record)
        _atomic_json(
            CALLS_DIR / "progress.json",
            {
                "completed_call_count": len(invocation_receipts),
                "task172_calls_started": index,
                "last_completed_case": case_name,
                "last_result_hash": call_record["result_hash"],
            },
        )

    baseline = invocation_receipts[:2]
    precision100 = invocation_receipts[2:]
    baseline_hashes = [item["result_hash"] for item in baseline]
    precision100_hashes = [item["result_hash"] for item in precision100]
    context_causality = (
        all(value == R2_RESULT_HASH for value in baseline_hashes)
        and all(value == R3_RESULT_HASH for value in precision100_hashes)
        and baseline[0]["result_projection"] == baseline[1]["result_projection"]
        and precision100[0]["result_projection"] == precision100[1]["result_projection"]
    )
    sensitivity = baseline[0]["result_projection"] != precision100[0]["result_projection"]
    r3_probes = r3_evidence["execution"]["probes"]
    derived_f = None
    if baseline[0]["key_outputs_and_solver_diagnostics"].get("signed_q_hot_to_cold_w") == str(
        r2_result.signed_q_hot_to_cold_w
    ):
        with decimal.localcontext() as high_precision:
            high_precision.prec = 100
            signed_q = r2_result.signed_q_hot_to_cold_w
            derived = [
                {
                    "probe_index": item["probe_index"],
                    "q_decimal_exact": item["q_decimal_exact"],
                    "F_derived_offline": str(Decimal(item["q_decimal_exact"]) - signed_q),
                    "stored_r3_F": item["F_decimal_high_precision"],
                    "matches_stored_r3_F": str(Decimal(item["q_decimal_exact"]) - signed_q)
                    == item["F_decimal_high_precision"],
                }
                for item in r3_probes
            ]
        derived_f = {
            "classification": "DERIVED_OFFLINE_RECALCULATION",
            "native_task172_validations_performed": 0,
            "probe_count": len(derived),
            "all_match_stored_r3_f": all(item["matches_stored_r3_F"] for item in derived),
            "min_abs_f_w": str(min(abs(Decimal(item["F_derived_offline"])) for item in derived)),
            "point_root_recovered": any(
                abs(Decimal(item["F_derived_offline"])) <= Decimal("1e-6") for item in derived
            ),
            "probes": derived,
        }
    report = {
        "schema_version": "task173.task172-decimal-context-adjudication.r1",
        "task_id": "STAGE3_TASK173_R3_TASK172_DECIMAL_CONTEXT_INHERITANCE_ADJUDICATION_R1",
        "repository": "xuezhiorange-png/hxforge-agent",
        "pr_number": 283,
        "pr_state_required": "OPEN_DRAFT",
        "start_head": START_HEAD,
        "final_head_at_execution": _git("rev-parse", "HEAD"),
        "production_code_changed": False,
        "task172_contract_changed": False,
        "r2a_authority_changed": False,
        "numerical_tolerance_changed": False,
        "full_n32_reconstruction_executed": False,
        "public_full_rating_reexecuted": False,
        "public_sizing_reexecuted": False,
        "task175_executed": False,
        "source_integrity": raw_and_source,
        "frozen_identities": {
            "candidate_rating_request_hash": CANDIDATE_RATING_REQUEST_HASH,
            "task172_request_hash": R2_REQUEST_HASH,
            "r2_task172_result_hash": R2_RESULT_HASH,
            "r3_task172_same_request_result_hash": R3_RESULT_HASH,
            "r2_right_request_hash_replay": rating.recompute_task172_request_hash(request),
            "r2_right_result_hash_replay": rating.recompute_task172_result_hash(r2_result),
            "r3_first_probe_replay": basis_facts["r3_first_probe_replay"],
        },
        "decimal_context_r2": {
            "before_n32_reconstruction": before["decimal_context"],
            "after_n32_reconstruction": after["decimal_context"],
            "computational_settings_equal_before_after": all(
                before["decimal_context"][key] == after["decimal_context"][key]
                for key in context_settings
            ),
            "actual_flags_at_each_task172_call": "NOT_ESTABLISHED",
            "call_precision_inferred_from_saved_context_and_production_call_path": 28,
        },
        "decimal_context_r3": {
            "actual_historical_call_context_snapshot": "NOT_CAPTURED",
            "precision_at_validator_call_proven_by_dynamic_scope": 100,
            "rounding_traps_exponent_limits_inherited_from_fresh_process_context": fresh_default,
            "flags_at_historical_validator_call": "NOT_ESTABLISHED",
        },
        "controlled_native_task172_validations": invocation_receipts,
        "native_task172_validation_count": len(invocation_receipts),
        "controlled_baseline_result_hashes": baseline_hashes,
        "controlled_100_precision_result_hashes": precision100_hashes,
        "decimal_context_causality": "CONFIRMED" if context_causality else "NOT_CONFIRMED",
        "task172_ambient_context_sensitivity": "CONFIRMED" if sensitivity else "NOT_CONFIRMED",
        "task172_heat_rate_changed": (
            baseline[0]["key_outputs_and_solver_diagnostics"].get("signed_q_hot_to_cold_w")
            != precision100[0]["key_outputs_and_solver_diagnostics"].get("signed_q_hot_to_cold_w")
        ),
        "context_sensitive_fields": {
            field: {
                "baseline": baseline[0]["key_outputs_and_solver_diagnostics"].get(field),
                "precision100": precision100[0]["key_outputs_and_solver_diagnostics"].get(field),
                "changed": baseline[0]["key_outputs_and_solver_diagnostics"].get(field)
                != precision100[0]["key_outputs_and_solver_diagnostics"].get(field),
            }
            for field in (
                "tube_htc_w_m2_k",
                "shell_htc_w_m2_k",
                "shell_j_mu",
                "signed_q_hot_to_cold_w",
            )
        },
        "provider_signature_comparison": {
            "r2_left": [
                item["provider_enthalpy_float_hex"]
                for item in basis_facts["left_endpoint"].get("provider_ph_calls", [])
            ],
            "r2_right": [
                item["provider_enthalpy_float_hex"]
                for item in basis_facts["right_endpoint"].get("provider_ph_calls", [])
            ],
            "r3_probe_1": [
                item["provider_enthalpy_float_hex"]
                for item in basis_facts["r3_first_probe"].get("provider_ph_inputs_outputs", [])
            ],
            "r3_decimal_from_float_vs_decimal_str": preflight["rehydration_basis"][
                "decimal_from_float_vs_decimal_str"
            ],
            "r3_provider_ph_signature_count": r3_evidence["execution"][
                "provider_ph_signature_count"
            ],
        },
        "derived_offline_recalculation": derived_f,
        "r3_historical_probe_count": r3_evidence["execution"]["decimal_q_probe_count"],
        "r3_historical_point_root_recovered": r3_evidence["execution"]["point_root_recovered"],
        "root_cause_classification": (
            "CONFIRMED_R3_DIAGNOSTIC_DECIMAL_CONTEXT_LEAK"
            if context_causality
            else "CROSS_RUN_RESULT_IDENTITY_DIVERGENCE_NOT_FULLY_ATTRIBUTED"
        ),
        "production_authority_change_required": False,
        "next_recommended_action": (
            "Keep R2/R3 immutable; use an evidence-only corrected runner that computes "
            "Decimal-q state "
            "under its local high-precision context but exits that context before native Task172. "
            "Do not change Task172 production context or numerical authority in this adjudication."
        ),
    }
    report["canonical_evidence_hash"] = canonical_sha256(report)
    _atomic_json(EVIDENCE_PATH, report)
    return report


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--invoke-one", metavar="CASE")
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    if args.invoke_one:
        _invoke_one(args.invoke_one)
        return 0
    if args.execute:
        report = _execute()
        print(f"DECIMAL_CONTEXT_CAUSALITY={report['decimal_context_causality']}")
        print(
            f"TASK172_AMBIENT_CONTEXT_SENSITIVITY={report['task172_ambient_context_sensitivity']}"
        )
        print(f"NATIVE_TASK172_VALIDATION_COUNT={report['native_task172_validation_count']}")
        print(f"EVIDENCE_SHA256={report['canonical_evidence_hash']}")
        return 0
    if args.replay:
        evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        recorded = evidence.pop("canonical_evidence_hash", None)
        if canonical_sha256(evidence) != recorded:
            raise RuntimeError("adjudication evidence canonical hash replay failed")
        evidence["canonical_evidence_hash"] = recorded
        if _git("rev-parse", "HEAD") != START_HEAD:
            raise RuntimeError("replay must run from start HEAD in this first-stage runner")
        print(f"CROSS_RUN_REQUEST_IDENTITY={R2_REQUEST_HASH}")
        print(f"CONTROLLED_BASELINE_RESULT_HASH={evidence['controlled_baseline_result_hashes'][0]}")
        print(
            f"CONTROLLED_100_PRECISION_RESULT_HASH={evidence['controlled_100_precision_result_hashes'][0]}"
        )
        print(f"DECIMAL_CONTEXT_CAUSALITY={evidence['decimal_context_causality']}")
        print("EVIDENCE_CANONICAL_HASH_REPLAY=PASS")
        return 0
    parser.error("choose --execute, --invoke-one, or --replay")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
