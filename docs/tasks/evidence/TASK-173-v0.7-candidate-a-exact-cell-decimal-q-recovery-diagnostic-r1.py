"""Isolated exact-cell Decimal-q feasibility diagnostic for Candidate A.

The expensive path is opt-in and calls only the private n=32 outer-boundary
entrypoint.  The default mode replays committed evidence and never invokes a
rating or sizing solver.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal, getcontext, localcontext
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Any

import CoolProp.CoolProp as CP

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import (
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import (
    service as rating,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
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
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    ReferencePlanePair,
    ReferencePlaneToken,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "STAGE3_TASK173_CANDIDATE_A_EXACT_CELL_DECIMAL_Q_RECOVERY_DIAGNOSTIC_R1"
START_HEAD = "b3df78adf32b5469bdac5f6f41a50f2f0e94e8da"
RUNTIME_HEAD = "21386a88f8290538172e9389ed46f50c3697a426"
RUNTIME_TREE = "ce61a818b82f908729d2bdf4553cc27012354952"
COMPLETION_REQUEST_HASH = "5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae"
TASK168_SPACE_HASH = "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea"
CANDIDATE_ID = "adeab5b1-a339-5eb3-aa66-011ffe49bac0"
CANDIDATE_HASH = "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767"
RATING_REQUEST_HASH = "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7"
TARGET_N = 32
TARGET_SUPPORT_ID = (
    "urn:hxforge:task171:candidate:"
    "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767:support:2"
)
TARGET_LEFT_Q = 268.4228547695099
TARGET_RIGHT_Q = 268.42285476950997
EXPECTED_N32_EVALUATIONS = 144217
EXPECTED_N32_HOLES = 27
EXPECTED_BLOCKED_RESULT_HASH = "daf0f61109676d50e9dac2c1d5ceb9afb206b232bc039fc0253f5b1ecdba774c"
EXPECTED_CANDIDATE_RECEIPT_SHA256 = (
    "80e4648a91d1da2798dc608252a1a67111f1248711b8595343ab8c0739705b42"
)
R2A_AUTHORITY_HASH = "25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e"
PRODUCTION_PATHS = (
    "src/hexagent/exchangers/shell_tube/manufacturable_candidates",
    "src/hexagent/exchangers/shell_tube/task172_local_runtime",
    "src/hexagent/exchangers/shell_tube/task173_integrated_rating",
    "src/hexagent/exchangers/shell_tube/task173_integrated_sizing",
    "src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration",
    "src/hexagent/exchangers/shell_tube/bell_delaware/pressure_drop.py",
    "tests/exchangers/shell_tube/test_task173_integrated_rating.py",
    "tests/exchangers/shell_tube/test_task173_integrated_sizing.py",
    "tests/exchangers/shell_tube/test_task174_hydraulic_orchestration.py",
    "uv.lock",
)
REQUEST_REPLAY = ROOT / (
    "docs/tasks/evidence/TASK-173-v0.7-full-sizing-completion-request-r1-replay.py"
)
CANDIDATE_RUNNER = ROOT / (
    "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
)
CANDIDATE_RECEIPT = ROOT / (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-ratings-r1.json"
)
EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r1.json"
)
LIVE_CAPTURE: dict[str, Any] | None = None


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _native_projection(value: Any) -> Any:
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
        return {
            field.name: _native_projection(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _native_projection(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_native_projection(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported native diagnostic value: {type(value).__name__}")


def _model_json(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json", fallback=rating._candidate_json_fallback)


def _assert_runtime_binding(*, execution: bool) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    if execution and head != START_HEAD:
        raise RuntimeError(f"execution requires exact start HEAD: {head}")
    _git("merge-base", "--is-ancestor", RUNTIME_HEAD, head)
    actual_tree = _git("rev-parse", f"{RUNTIME_HEAD}^{{tree}}")
    if actual_tree != RUNTIME_TREE:
        raise RuntimeError("frozen production runtime tree mismatch")
    diff = subprocess.run(
        ["git", "diff", "--quiet", RUNTIME_HEAD, head, "--", *PRODUCTION_PATHS],
        cwd=ROOT,
        check=False,
    )
    if diff.returncode:
        raise RuntimeError("runtime paths differ between frozen source and current HEAD")
    dirty = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *PRODUCTION_PATHS],
        cwd=ROOT,
        check=False,
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "HEAD", "--", *PRODUCTION_PATHS],
        cwd=ROOT,
        check=False,
    )
    if dirty.returncode or staged.returncode:
        raise RuntimeError("bound runtime paths are dirty")
    return {
        "current_head": head,
        "current_tree": _git("rev-parse", "HEAD^{tree}"),
        "runtime_source_head": RUNTIME_HEAD,
        "runtime_source_tree": actual_tree,
        "runtime_paths_byte_identical": True,
        "bound_runtime_worktree_clean": True,
    }


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load evidence helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reconstruct_candidate_a() -> tuple[CandidateRatingRequest, dict[str, Any]]:
    started_wall = time.monotonic()
    started_cpu = time.process_time()
    request_replay = _load_module("task173_completion_request_replay", REQUEST_REPLAY)
    sizing_request, request_facts = request_replay._build_request_and_projection()
    if (
        request_facts["completion_sizing_request_hash"] != COMPLETION_REQUEST_HASH
        or request_facts["candidate_space_hash"] != TASK168_SPACE_HASH
    ):
        raise RuntimeError("frozen completion request or TASK168 space mismatch")
    task168_request = sizing_request.task168_candidate_request
    authority_map = task168._authority_map(task168_request)
    dimensions = tuple(
        task168._sort_values(authority_map[role].values)
        for role in task168.DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    candidate = None
    bundle = None
    selected_combination: tuple[Any, ...] | None = None
    for combination in product(task168_request.shell_geometry_catalog.records, *dimensions):
        candidate_trial = task168._candidate(
            task168_request, authority_map, combination[0], tuple(combination[1:])
        )
        if candidate_trial.candidate_id == CANDIDATE_ID:
            candidate = candidate_trial
            selected_combination = combination
            bundle, stage_failure, _ = task168._execute_candidate_chain(
                task168_request,
                candidate,
                combination[0],
                include_legacy_task162=False,
                include_legacy_task168_rating_dependencies=False,
                preserve_baffle_orientation_sequence=True,
            )
            if stage_failure is not None:
                raise RuntimeError(f"Candidate A upstream chain blocked: {stage_failure!r}")
            break
    if candidate is None or bundle is None or selected_combination is None:
        raise RuntimeError("frozen Candidate A not found in reconstructed TASK168 space")
    if candidate.candidate_hash != CANDIDATE_HASH:
        raise RuntimeError("Candidate A identity mismatch")
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
        raise RuntimeError("Candidate A TASK174 is not VALIDATED")
    request = _candidate_rating_request(
        candidate,
        TASK168_SPACE_HASH,
        bundle,
        topology,
        task174,
        COMPLETION_REQUEST_HASH,
    )
    actual_hash = candidate_rating_request_hash(request)
    if actual_hash != RATING_REQUEST_HASH:
        raise RuntimeError(f"Candidate A rating request mismatch: {actual_hash}")
    return request, {
        "candidate_id": candidate.candidate_id,
        "candidate_hash": candidate.candidate_hash,
        "rating_request_hash": actual_hash,
        "candidate_rating_request_projection_sha256": _sha256(
            json.dumps(
                _native_projection(request),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ),
        "upstream_candidate_chain_count": 1,
        "task174_candidate_validation_count": 1,
        "candidate_b_materialized": False,
        "candidate_a_upstream_preparation_wall_seconds": time.monotonic() - started_wall,
        "candidate_a_upstream_preparation_cpu_seconds": time.process_time() - started_cpu,
    }


def _context_snapshot(provider: CoolPropProvider | None = None) -> dict[str, Any]:
    decimal_context = getcontext()
    return {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "decimal_context": {
            "prec": decimal_context.prec,
            "rounding": decimal_context.rounding,
            "Emax": decimal_context.Emax,
            "Emin": decimal_context.Emin,
            "clamp": decimal_context.clamp,
            "capitals": decimal_context.capitals,
            "traps": {item.__name__: bool(value) for item, value in decimal_context.traps.items()},
            "flags": {item.__name__: bool(value) for item, value in decimal_context.flags.items()},
        },
        "environment": {
            name: os.environ.get(name) for name in ("PYTHONHASHSEED", "TZ", "LC_ALL", "LANG")
        },
        "coolprop": {
            "package_version": (
                str(CP.get_global_param_string("version")) if provider is None else provider.version
            ),
            "git_revision": (
                str(CP.get_global_param_string("gitrevision"))
                if provider is None
                else provider.git_revision
            ),
            "backend": "HEOS::Water",
            "reference_state": "DEF",
            "provider_name": "CoolProp",
            "allow_unvalidated_fluids": (
                None if provider is None else provider.allow_unvalidated_fluids
            ),
            "near_saturation_relative_tolerance": (
                None if provider is None else provider.near_saturation_relative_tolerance
            ),
            "cache_size": None if provider is None else provider.cache_size,
            "configuration_fingerprint": (
                None if provider is None else provider._construction_fingerprint
            ),
        },
        "runtime_head": _git("rev-parse", "HEAD"),
        "runtime_tree": _git("rev-parse", "HEAD^{tree}"),
    }


def _capture_state(state: Any) -> dict[str, Any]:
    return {
        "native": _native_projection(state.native),
        "property_snapshot": state.snapshot.model_dump(mode="json"),
        "property_snapshot_hash": state.snapshot_hash,
    }


def _run_exact_n32(request: CandidateRatingRequest, provider: CoolPropProvider) -> dict[str, Any]:
    global LIVE_CAPTURE
    expected_result = json.loads(CANDIDATE_RECEIPT.read_text(encoding="utf-8"))["candidates"][
        CANDIDATE_ID
    ]["result_projection"]
    if expected_result["result_hash"] != EXPECTED_BLOCKED_RESULT_HASH:
        raise RuntimeError("frozen Candidate A blocked receipt mismatch")
    context = rating._candidate_context(request)
    stats = rating._CellSearchStats()
    capture: dict[str, Any] = {
        "target_cell_trials": [],
        "transient_events": [],
        "failure": None,
        "task172_validator_call_count": 0,
        "provider_state_ph_call_count": 0,
        "target_support_seen": False,
    }
    LIVE_CAPTURE = capture
    active_target_trial: dict[str, Any] | None = None
    native_target_objects: dict[str, Any] = {}
    original_solve_cell = rating._solve_cell
    original_cell_evaluation = rating._cell_evaluation
    original_task172_candidate = rating.task172_validate_candidate
    original_event = rating._candidate_provider_enclosure_event

    def observed_task172(
        native_request: CandidateTask172LocalRequest | Task172LocalRequest,
        active_provider: Any,
    ) -> Any:
        capture["task172_validator_call_count"] += 1
        if capture["task172_validator_call_count"] % 10000 == 0:
            print(
                f"ISOLATED_N32_TASK172_CALLS={capture['task172_validator_call_count']}",
                flush=True,
            )
        result = original_task172_candidate(native_request, active_provider)
        if active_target_trial is not None:
            request_projection = _model_json(native_request)
            request_hash = rating.recompute_task172_request_hash(native_request)
            entry = {
                "request_projection": request_projection,
                "request_hash": request_hash,
                "request_hash_replay": request_hash == getattr(result, "request_hash", None),
                "result_type": type(result).__name__,
            }
            if type(result) is Task172LocalResult:
                entry["result_projection"] = _model_json(result)
                entry["result_hash"] = rating.recompute_task172_result_hash(result)
                entry["result_id"] = result.result_id
                entry["status"] = result.status
                entry["result_hash_replay"] = entry["result_hash"] == result.result_hash
            else:
                entry["result_projection"] = _model_json(result)
                entry["result_hash"] = rating.recompute_task172_blocked_result_hash(result)
                entry["result_id"] = getattr(result, "result_id", None)
                entry["status"] = result.status
                entry["failure_code"] = result.failure_code
                entry["field_path"] = result.field_path
                entry["blocked_result_hash"] = result.blocked_result_hash
                entry["result_hash_replay"] = entry["result_hash"] == result.blocked_result_hash
            active_target_trial["task172_call"] = entry
        return result

    def observed_event(*args: Any, **kwargs: Any) -> Any:
        result = original_event(*args, **kwargs)
        control = rating._CANDIDATE_TRANSIENT_CONTROL.get()
        if result is not None:
            capture["transient_events"].append(
                {
                    "event_hash": result.get("event_hash"),
                    "mode": control.mode if control is not None else None,
                    "mesh_subdivisions": (
                        control.mesh_subdivisions if control is not None else None
                    ),
                    "outer_iteration": control.outer_iteration if control is not None else None,
                    "shooting_enthalpy_j_kg": (
                        str(control.shooting_enthalpy) if control is not None else None
                    ),
                    "physical_support_id": result.get("physical_support_id"),
                }
            )
        return result

    original_canonical_sha256 = rating.canonical_sha256

    def observed_canonical_sha256(value: Any) -> str:
        digest = original_canonical_sha256(value)
        if (
            isinstance(value, dict)
            and value.get("schema_version")
            == "task173.r2a.production-outer-decision-certificate.v1"
        ):
            capture.setdefault("transient_outer_decision_certificates", []).append(
                {
                    "projection": json.loads(json.dumps(value)),
                    "certificate_hash": digest,
                }
            )
        return digest

    def observed_cell_evaluation(q_w: float, **kwargs: Any) -> Any:
        nonlocal active_target_trial
        control = rating._CANDIDATE_TRANSIENT_CONTROL.get()
        support = kwargs["support"]
        is_target = (
            control is not None
            and control.mode == "DISABLED"
            and control.mesh_subdivisions == TARGET_N
            and support.physical_segment_id == TARGET_SUPPORT_ID
        )
        if not is_target:
            return original_cell_evaluation(q_w, **kwargs)
        capture["target_support_seen"] = True
        trial: dict[str, Any] = {
            "q_w_repr": repr(q_w),
            "q_w_binary64_hex": float(q_w).hex(),
            "production_q_decimal": str(rating._d(q_w)),
            "exact_binary64_decimal": str(Decimal.from_float(float(q_w))),
            "control_mode": control.mode,
            "mesh_subdivisions": control.mesh_subdivisions,
            "outer_iteration": kwargs.get("outer_iteration"),
            "shooting_enthalpy_j_kg": str(kwargs.get("shooting_enthalpy")),
            "support_projection": _native_projection(support),
            "tube_upstream_state": _capture_state(kwargs["tube_upstream"]),
            "shell_physical_left_state": _capture_state(kwargs["shell_physical_left"]),
            "provider_ph_calls": [],
        }
        native_target_objects.update(
            {
                "support": support,
                "tube_upstream": kwargs["tube_upstream"],
                "shell_physical_left": kwargs["shell_physical_left"],
            }
        )
        active_target_trial = trial
        original_state_from_enthalpy = rating._state_from_enthalpy

        def observed_state_from_enthalpy(
            state_provider: Any, enthalpy: Decimal, **state_kwargs: Any
        ) -> Any:
            input_record = {
                "enthalpy_decimal_before_float": str(enthalpy),
                "provider_enthalpy_float": float(enthalpy),
                "provider_enthalpy_float_hex": float(enthalpy).hex(),
                "decimal_from_provider_float": str(Decimal.from_float(float(enthalpy))),
                "shell_search_state": state_kwargs.get("shell_search_state", False),
            }
            state = original_state_from_enthalpy(state_provider, enthalpy, **state_kwargs)
            input_record["state_after_provider"] = _capture_state(state)
            trial["provider_ph_calls"].append(input_record)
            capture["provider_state_ph_call_count"] += 1
            return state

        try:
            rating._state_from_enthalpy = observed_state_from_enthalpy
            result = original_cell_evaluation(q_w, **kwargs)
            trial["cell_evaluation_status"] = "VALIDATED"
            trial["task172_status"] = result.task172_result.status
            trial["task172_signed_q_hot_to_cold_w"] = str(
                result.task172_result.signed_q_hot_to_cold_w
            )
            trial["f_production_decimal_context"] = str(
                rating._d(q_w) - result.task172_result.signed_q_hot_to_cold_w
            )
            with localcontext() as decimal_context:
                decimal_context.prec = 100
                trial["f_exact_binary64_endpoint"] = str(
                    Decimal.from_float(float(q_w)) - result.task172_result.signed_q_hot_to_cold_w
                )
            trial["task172_request_hash"] = rating.recompute_task172_request_hash(
                result.task172_request
            )
            trial["task172_result_hash"] = result.task172_result.result_hash
            trial["task172_request_projection"] = _model_json(result.task172_request)
            trial["task172_result_projection"] = _model_json(result.task172_result)
            trial["cell_states"] = {
                "tube_downstream": _capture_state(result.tube_downstream),
                "shell_next_physical": _capture_state(result.shell_next_physical),
                "tube_local": _capture_state(result.tube_local),
                "shell_local": _capture_state(result.shell_local),
            }
            return result
        except rating._Task172NumericalHole as exc:
            trial["cell_evaluation_status"] = "TASK172_NUMERICAL_HOLE"
            trial["task172_hole"] = {
                "request_hash": exc.request_hash,
                "blocked_result_hash": exc.blocked_result_hash,
                "request_hash_replay_passed": exc.request_hash_replay_passed,
                "blocked_result_hash_replay_passed": exc.blocked_result_hash_replay_passed,
                "exact_blocked_result_type": exc.exact_blocked_result_type,
            }
            raise
        except BaseException as exc:
            trial["cell_evaluation_status"] = "RAISED"
            trial["exception_type"] = type(exc).__name__
            trial["exception_text"] = str(exc)
            raise
        finally:
            rating._state_from_enthalpy = original_state_from_enthalpy
            active_target_trial = None
            capture["target_cell_trial_count"] = len(capture["target_cell_trials"]) + 1
            capture["target_cell_trials"].append(trial)

    def observed_solve_cell(**kwargs: Any) -> Any:
        support = kwargs.get("support")
        control = rating._CANDIDATE_TRANSIENT_CONTROL.get()
        target_disabled = (
            support is not None
            and support.physical_segment_id == TARGET_SUPPORT_ID
            and kwargs.get("mesh_subdivisions") == TARGET_N
            and control is not None
            and control.mode == "DISABLED"
        )
        try:
            return original_solve_cell(**kwargs)
        except rating._Stage3Failure as exc:
            if target_disabled:
                capture["failure"] = {
                    "code": exc.code,
                    "diagnostics": list(exc.diagnostics),
                    "mesh_subdivisions": kwargs.get("mesh_subdivisions"),
                    "support_id": support.physical_segment_id,
                    "tube_cell_id": support.tube_cell_id,
                    "shell_cell_id": support.shell_cell_id,
                    "wall_interface_id": support.wall_interface_id,
                    "outer_iteration": kwargs.get("outer_iteration"),
                    "shooting_enthalpy_j_kg": str(kwargs.get("shooting_enthalpy")),
                    "tube_upstream_state": _capture_state(kwargs["tube_upstream"]),
                    "shell_physical_left_state": _capture_state(kwargs["shell_physical_left"]),
                }
            raise

    original_boundary = rating._candidate_transient_outer_boundary
    context_token = rating._CANDIDATE_RATING_CONTEXT.set(context)
    start_wall = time.monotonic()
    start_cpu = time.process_time()
    rating._solve_cell = observed_solve_cell
    rating._cell_evaluation = observed_cell_evaluation
    rating.task172_validate_candidate = observed_task172
    rating._candidate_provider_enclosure_event = observed_event
    rating.canonical_sha256 = observed_canonical_sha256
    try:
        try:
            mesh_run = original_boundary(TARGET_N, provider, context.shell_authority, stats)
            capture["n32_boundary_outcome"] = "RETURNED_ACCEPTED_MESH"
            capture["n32_mesh_result_hash"] = mesh_run.mesh_result_hash
            capture["n32_shooting_enthalpy_j_kg"] = str(mesh_run.shooting_enthalpy)
            capture["n32_outer_iteration_count"] = mesh_run.bisection_iterations
        except rating._Stage3Failure as exc:
            capture["n32_boundary_outcome"] = "BLOCKED"
            capture["n32_boundary_failure"] = {
                "code": exc.code,
                "diagnostics": list(exc.diagnostics),
            }
        finally:
            capture["wall_seconds"] = time.monotonic() - start_wall
            capture["process_cpu_seconds"] = time.process_time() - start_cpu
            capture["task172_local_evaluation_count_from_stats"] = (
                stats.task172_local_evaluation_count
            )
            capture["task172_numerical_hole_count_from_stats"] = stats.task172_numerical_hole_count
            capture["task172_hole_counts_by_code"] = dict(
                stats.task172_numerical_hole_counts_by_code
            )
            capture["task172_validator_call_count"] = capture["task172_validator_call_count"]
            capture["target_trial_count"] = len(capture["target_cell_trials"])
            capture["transient_event_count"] = len(capture["transient_events"])
            capture["_native_target_objects"] = native_target_objects
            capture["_native_provider"] = provider
    finally:
        rating._solve_cell = original_solve_cell
        rating._cell_evaluation = original_cell_evaluation
        rating.task172_validate_candidate = original_task172_candidate
        rating._candidate_provider_enclosure_event = original_event
        rating.canonical_sha256 = original_canonical_sha256
        rating._CANDIDATE_RATING_CONTEXT.reset(context_token)
    return capture


def _probe_decimal_q(
    q: Decimal,
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: CoolPropProvider,
    shell_authority: Any,
    context: Any,
    ordinal: int,
) -> dict[str, Any]:
    if type(q) is not Decimal or not q.is_finite() or q < 0:
        raise ValueError("diagnostic Decimal q must be finite and non-negative")
    with localcontext() as decimal_context:
        decimal_context.prec = 70
        tube_upstream_h = rating._d(tube_upstream.native.enthalpy_j_kg)
        shell_left_h = rating._d(shell_physical_left.native.enthalpy_j_kg)
        tube_downstream_h = tube_upstream_h - q / rating.TUBE_MASS_FLOW_KG_S
        shell_next_h = shell_left_h - q / rating.SHELL_MASS_FLOW_KG_S
        tube_mid_h = (tube_upstream_h + tube_downstream_h) / Decimal(2)
        shell_mid_h = (shell_left_h + shell_next_h) / Decimal(2)
    enthalpies = {
        "tube_downstream": tube_downstream_h,
        "shell_next_physical": shell_next_h,
        "tube_midpoint": tube_mid_h,
        "shell_midpoint": shell_mid_h,
    }
    states: dict[str, Any] = {}
    provider_ph: list[dict[str, Any]] = []
    for label, enthalpy in enthalpies.items():
        provider_float = float(enthalpy)
        state = rating._state_from_enthalpy(
            provider,
            enthalpy,
            shell_search_state=label == "shell_next_physical",
        )
        states[label] = state
        provider_ph.append(
            {
                "state_role": label,
                "enthalpy_decimal_before_float": str(enthalpy),
                "provider_enthalpy_float": provider_float,
                "provider_enthalpy_float_hex": provider_float.hex(),
                "decimal_from_provider_float": str(Decimal.from_float(provider_float)),
                "provider_input_snapshot": state.snapshot.model_dump(mode="json"),
                "provider_input_snapshot_hash": state.snapshot_hash,
                "provider_output_native": _native_projection(state.native),
                "provider_output_enthalpy_j_kg": str(state.native.enthalpy_j_kg),
            }
        )
    request = rating._task172_request(
        support, states["tube_midpoint"], states["shell_midpoint"], shell_authority
    )
    if type(request) is not CandidateTask172LocalRequest:
        raise RuntimeError("decimal probe did not produce candidate-native TASK172 request")
    support_hash = rating.recompute_task172_support_id(request)
    if (
        request.case_id != context.request.candidate_id
        or request.case_revision_id != context.request.candidate_id
        or request.topology.topology_id != context.topology_id
        or request.topology.task171_result_hash != context.task171_result_hash
        or request.topology.physical_ownership_hash != context.physical_ownership_hash
        or request.support != support
        or len(support_hash) != 64
        or request.topology.tube_role != "HOT"
        or request.topology.shell_role != "COLD"
    ):
        raise RuntimeError("decimal probe candidate/support preflight failed")
    if states["tube_midpoint"].native.temperature_k < states["shell_midpoint"].native.temperature_k:
        raise RuntimeError("decimal probe violates the native hot/cold preflight")
    for state in (states["tube_midpoint"], states["shell_midpoint"]):
        native = state.native
        if (
            native.phase.value != "LIQUID"
            or native.pressure_pa != float(rating.REFERENCE_PRESSURE_PA)
            or state.snapshot.backend != "HEOS::Water"
            or state.snapshot.provider != "CoolProp"
            or state.snapshot.provider_version != "8.0.0"
            or state.snapshot.reference_state != "DEF"
        ):
            raise RuntimeError("decimal probe property-profile preflight failed")
    native_request_hash = rating.recompute_task172_request_hash(request)
    request_projection = _model_json(request)
    native_result = rating.task172_validate_candidate(request, provider)
    record: dict[str, Any] = {
        "probe_index": ordinal,
        "q_decimal_exact": str(q),
        "q_python_type": type(q).__name__,
        "intermediate_enthalpy_decimal_inputs": {
            name: str(value) for name, value in enthalpies.items()
        },
        "provider_ph_inputs_outputs": provider_ph,
        "task172_request_projection": request_projection,
        "task172_request_hash": native_request_hash,
        "task172_support_hash": support_hash,
        "task172_request_hash_replay": native_request_hash
        == getattr(native_result, "request_hash", None),
        "task172_result_type": type(native_result).__name__,
        "task172_result_projection": _model_json(native_result),
        "task172_status": native_result.status,
        "task172_result_hash_replay": False,
        "F_decimal_high_precision": None,
        "F_native_contract_context": None,
        "ordinary_point_root_tolerance_pass": False,
    }
    if type(native_result) is Task172LocalResult:
        native_result_hash = rating.recompute_task172_result_hash(native_result)
        if (
            native_result.status != "VALIDATED"
            or native_result.request_hash != native_request_hash
            or native_result.physical_support_id != support_hash
            or native_result.physical_segment_id != support.physical_segment_id
            or native_result.tube_cell_id != support.tube_cell_id
            or native_result.shell_cell_id != support.shell_cell_id
            or native_result.wall_interface_id != support.wall_interface_id
            or native_result_hash != native_result.result_hash
        ):
            raise RuntimeError("native Task172 valid result identity/preflight mismatch")
        with localcontext() as decimal_context:
            decimal_context.prec = 100
            exact_f = q - native_result.signed_q_hot_to_cold_w
        with localcontext() as decimal_context:
            decimal_context.prec = 100
            contract_f = q - native_result.signed_q_hot_to_cold_w
        record.update(
            {
                "task172_result_hash": native_result_hash,
                "task172_result_id": native_result.result_id,
                "task172_result_hash_replay": native_result_hash == native_result.result_hash,
                "task172_signed_q_hot_to_cold_w": str(native_result.signed_q_hot_to_cold_w),
                "F_decimal_high_precision": str(exact_f),
                "F_native_contract_context": str(contract_f),
                "ordinary_point_root_tolerance_pass": abs(exact_f) <= Decimal("1e-6"),
                "provider_state_output_hashes": [state.snapshot_hash for state in states.values()],
            }
        )
    else:
        if native_result.request_hash != native_request_hash:
            raise RuntimeError("native Task172 blocked result request identity mismatch")
        record["task172_result_hash"] = rating.recompute_task172_blocked_result_hash(native_result)
        record["task172_result_id"] = native_result.result_id
        record["task172_failure_code"] = native_result.failure_code
        record["task172_result_hash_replay"] = (
            record["task172_result_hash"] == native_result.blocked_result_hash
        )
        if not record["task172_result_hash_replay"]:
            raise RuntimeError("native Task172 blocked result hash mismatch")
    record["q_binary64_conversion_after_native_evaluation_and_F_only"] = float(q)
    record["q_binary64_conversion_hex_after_native_evaluation_and_F_only"] = float(q).hex()
    return record


def _run_decimal_probes(
    capture: dict[str, Any],
    request: CandidateRatingRequest,
    *,
    uniform_intervals: int = 64,
    adaptive_bisection_cap: int = 64,
) -> dict[str, Any]:
    target_trials = capture["target_cell_trials"]
    endpoint_by_q = {
        item["q_w_repr"]: item
        for item in target_trials
        if item.get("cell_evaluation_status") == "VALIDATED"
    }
    if repr(TARGET_LEFT_Q) not in endpoint_by_q or repr(TARGET_RIGHT_Q) not in endpoint_by_q:
        raise RuntimeError("exact original binary64 endpoint evaluations were not captured")
    failure = capture.get("failure")
    if failure is None:
        raise RuntimeError("target accepted-cell failure record is missing")
    if (
        capture.get("n32_boundary_outcome") != "BLOCKED"
        or failure["code"] != "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"
        or failure["support_id"] != TARGET_SUPPORT_ID
        or failure["mesh_subdivisions"] != TARGET_N
    ):
        raise RuntimeError("isolated n32 reconstruction did not reproduce frozen target failure")
    frozen_diagnostics = capture["frozen_blocked_result_projection"]["diagnostics"]
    cell_failure_diagnostics = failure.get("diagnostics", [])
    if frozen_diagnostics[: len(cell_failure_diagnostics)] != cell_failure_diagnostics:
        raise RuntimeError("reconstructed exact-cell failure diagnostics differ from frozen result")
    if (
        capture["task172_local_evaluation_count_from_stats"] != EXPECTED_N32_EVALUATIONS
        or capture["task172_numerical_hole_count_from_stats"] != EXPECTED_N32_HOLES
        or capture["task172_validator_call_count"] != EXPECTED_N32_EVALUATIONS
    ):
        raise RuntimeError("isolated n32 Task172 call counts differ from frozen receipt")
    if not capture["target_support_seen"]:
        raise RuntimeError("isolated accepted trajectory did not reach exact target support")

    left_q = Decimal.from_float(TARGET_LEFT_Q)
    right_q = Decimal.from_float(TARGET_RIGHT_Q)
    if not left_q < right_q:
        raise RuntimeError("binary64 endpoints do not define an increasing Decimal interval")
    context = rating._candidate_context(request)
    failure_capture = capture["failure"]
    support_projection = next(
        item["support_projection"]
        for item in target_trials
        if item["q_w_repr"] == repr(TARGET_LEFT_Q)
    )
    # The reconstructed accepted-cell arguments are bound in each target trial.
    # Rehydrate the actual objects from the deterministic n=32 reconstruction by
    # running no solver again: the capture stores full provider snapshots, while
    # the original native objects are intentionally retained in this process.
    objects = capture.get("_native_target_objects")
    if objects is None:
        raise RuntimeError("native target objects were not retained for Decimal probes")
    provider = capture.get("_native_provider")
    if provider is None:
        raise RuntimeError("native provider was not retained for Decimal probes")

    probe_results: list[dict[str, Any]] = []
    by_q: dict[Decimal, dict[str, Any]] = {}

    def run_one(q: Decimal) -> dict[str, Any]:
        if q in by_q:
            return by_q[q]
        result = _probe_decimal_q(
            q,
            support=objects["support"],
            tube_upstream=objects["tube_upstream"],
            shell_physical_left=objects["shell_physical_left"],
            provider=provider,
            shell_authority=context.shell_authority,
            context=context,
            ordinal=len(probe_results) + 1,
        )
        by_q[q] = result
        probe_results.append(result)
        return result

    with localcontext() as decimal_context:
        decimal_context.prec = 100
        width = right_q - left_q
        for index in range(uniform_intervals + 1):
            run_one(left_q + width * Decimal(index) / Decimal(uniform_intervals))

    for endpoint in (endpoint_by_q[repr(TARGET_LEFT_Q)], endpoint_by_q[repr(TARGET_RIGHT_Q)]):
        task_result = endpoint["task172_result_projection"]
        proposed = Decimal(task_result["signed_q_hot_to_cold_w"])
        if left_q <= proposed <= right_q:
            run_one(proposed)

    adaptive_calls = 0
    while adaptive_calls < adaptive_bisection_cap and not any(
        item["ordinary_point_root_tolerance_pass"] for item in probe_results
    ):
        ordered = sorted(by_q.items(), key=lambda item: item[0])
        eligible_bracket: tuple[Decimal, Decimal] | None = None
        for (q_left, left_record), (q_right, right_record) in zip(
            ordered, ordered[1:], strict=False
        ):
            if (
                left_record["task172_status"] == "VALIDATED"
                and right_record["task172_status"] == "VALIDATED"
                and not left_record["ordinary_point_root_tolerance_pass"]
                and not right_record["ordinary_point_root_tolerance_pass"]
                and Decimal(left_record["F_decimal_high_precision"])
                * Decimal(right_record["F_decimal_high_precision"])
                < 0
            ):
                eligible_bracket = (q_left, q_right)
                break
        if eligible_bracket is None:
            break
        q_left, q_right = eligible_bracket
        with localcontext() as decimal_context:
            decimal_context.prec = 100
            midpoint = (q_left + q_right) / Decimal(2)
        if midpoint in by_q or midpoint in {q_left, q_right}:
            break
        run_one(midpoint)
        adaptive_calls += 1
        if probe_results[-1]["ordinary_point_root_tolerance_pass"]:
            break

    validated = [item for item in probe_results if item["task172_status"] == "VALIDATED"]
    min_abs_f = min(
        (abs(Decimal(item["F_decimal_high_precision"])) for item in validated),
        default=None,
    )
    passing = [item for item in validated if item["ordinary_point_root_tolerance_pass"]]
    probe_signatures = []
    for item in probe_results:
        input_signature = tuple(
            call["provider_enthalpy_float_hex"] for call in item["provider_ph_inputs_outputs"]
        )
        output_signature = tuple(
            call["provider_input_snapshot_hash"] for call in item["provider_ph_inputs_outputs"]
        )
        probe_signatures.append((input_signature, output_signature))
    unique_provider_input_signatures = {item[0] for item in probe_signatures}
    unique_provider_output_signatures = {item[1] for item in probe_signatures}

    ordered_uniform = sorted(
        (item for item in probe_results if item["probe_index"] <= uniform_intervals + 1),
        key=lambda item: Decimal(item["q_decimal_exact"]),
    )
    adjacent_steps: list[dict[str, Any]] = []
    provider_plateau_pairs: list[dict[str, Any]] = []
    task172_same_request_output_changes: list[dict[str, Any]] = []
    for left, right in zip(ordered_uniform, ordered_uniform[1:], strict=False):
        if left["task172_status"] != "VALIDATED" or right["task172_status"] != "VALIDATED":
            continue
        left_task_q = Decimal(left["task172_signed_q_hot_to_cold_w"])
        right_task_q = Decimal(right["task172_signed_q_hot_to_cold_w"])
        delta_input = Decimal(right["q_decimal_exact"]) - Decimal(left["q_decimal_exact"])
        delta_task = right_task_q - left_task_q
        left_input_signature = tuple(
            call["provider_enthalpy_float_hex"] for call in left["provider_ph_inputs_outputs"]
        )
        right_input_signature = tuple(
            call["provider_enthalpy_float_hex"] for call in right["provider_ph_inputs_outputs"]
        )
        left_output_signature = tuple(
            call["provider_input_snapshot_hash"] for call in left["provider_ph_inputs_outputs"]
        )
        right_output_signature = tuple(
            call["provider_input_snapshot_hash"] for call in right["provider_ph_inputs_outputs"]
        )
        if (
            left_input_signature == right_input_signature
            and left_output_signature == right_output_signature
            and left["task172_request_hash"] == right["task172_request_hash"]
            and left["task172_result_hash"] == right["task172_result_hash"]
        ):
            provider_plateau_pairs.append(
                {
                    "left_probe_index": left["probe_index"],
                    "right_probe_index": right["probe_index"],
                    "left_q_decimal": left["q_decimal_exact"],
                    "right_q_decimal": right["q_decimal_exact"],
                    "provider_ph_input_signature": list(left_input_signature),
                    "provider_ph_output_snapshot_hashes": list(left_output_signature),
                    "task172_request_hash": left["task172_request_hash"],
                    "task172_result_hash": left["task172_result_hash"],
                    "left_F_w": left["F_decimal_high_precision"],
                    "right_F_w": right["F_decimal_high_precision"],
                }
            )
        if (
            left_input_signature == right_input_signature
            and left_output_signature == right_output_signature
            and left["task172_request_hash"] == right["task172_request_hash"]
            and (
                left["task172_result_hash"] != right["task172_result_hash"]
                or left_task_q != right_task_q
            )
        ):
            task172_same_request_output_changes.append(
                {
                    "left_probe_index": left["probe_index"],
                    "right_probe_index": right["probe_index"],
                    "provider_ph_input_signature": list(left_input_signature),
                    "provider_ph_output_snapshot_hashes": list(left_output_signature),
                    "task172_request_hash": left["task172_request_hash"],
                    "left_result_hash": left["task172_result_hash"],
                    "right_result_hash": right["task172_result_hash"],
                    "left_task172_q_w": str(left_task_q),
                    "right_task172_q_w": str(right_task_q),
                }
            )
        if delta_task != 0:
            adjacent_steps.append(
                {
                    "left_probe_index": left["probe_index"],
                    "right_probe_index": right["probe_index"],
                    "left_q_decimal": left["q_decimal_exact"],
                    "right_q_decimal": right["q_decimal_exact"],
                    "delta_q_w": str(delta_input),
                    "left_task172_q_w": str(left_task_q),
                    "right_task172_q_w": str(right_task_q),
                    "delta_task172_q_w": str(delta_task),
                    "left_request_hash": left["task172_request_hash"],
                    "right_request_hash": right["task172_request_hash"],
                    "left_result_hash": left["task172_result_hash"],
                    "right_result_hash": right["task172_result_hash"],
                    "provider_input_signature_changed": (
                        left_input_signature != right_input_signature
                    ),
                    "provider_output_signature_changed": (
                        left_output_signature != right_output_signature
                    ),
                    "task172_request_identity_changed": (
                        left["task172_request_hash"] != right["task172_request_hash"]
                    ),
                    "classification": (
                        "PROVIDER_STATE_STEP"
                        if left_input_signature != right_input_signature
                        or left_output_signature != right_output_signature
                        else "TASK172_RESULT_STEP_WITH_IDENTICAL_PROVIDER_STATE"
                    ),
                }
            )
    root_recovered = bool(passing)
    return {
        "decimal_probe_plan": {
            "uniform_intervals": uniform_intervals,
            "uniform_probe_count_expected": uniform_intervals + 1,
            "endpoint_task172_heat_rate_points_added_if_inside": True,
            "adaptive_sign_bracket_bisection_cap": adaptive_bisection_cap,
            "adaptive_bisection_calls_used": adaptive_calls,
            "original_left_q_exact_decimal_from_float": str(left_q),
            "original_right_q_exact_decimal_from_float": str(right_q),
            "q_float_conversion_before_enthalpy_or_F": False,
        },
        "decimal_q_probe_count": len(probe_results),
        "validated_task172_probe_count": len(validated),
        "blocked_task172_probe_count": len(probe_results) - len(validated),
        "min_abs_f_w": str(min_abs_f) if min_abs_f is not None else None,
        "point_root_recovered": root_recovered,
        "point_root_probe_indices": [item["probe_index"] for item in passing],
        "provider_ph_plateau_confirmed": bool(provider_plateau_pairs),
        "provider_ph_plateau_adjacent_pair_count": len(provider_plateau_pairs),
        "provider_ph_plateau_adjacent_pairs": provider_plateau_pairs,
        "provider_ph_unique_input_signature_count": len(unique_provider_input_signatures),
        "provider_ph_unique_output_signature_count": len(unique_provider_output_signatures),
        "provider_state_changes_observed_between_adjacent_probes": any(
            item["provider_input_signature_changed"] or item["provider_output_signature_changed"]
            for item in adjacent_steps
        ),
        "task172_discontinuity_observed": bool(task172_same_request_output_changes),
        "task172_same_request_output_changes": task172_same_request_output_changes,
        "adjacent_native_task172_output_steps": adjacent_steps,
        "probes": probe_results,
        "target_failure_reference": {
            "code": failure_capture["code"],
            "support_id": failure_capture["support_id"],
            "mesh_subdivisions": failure_capture["mesh_subdivisions"],
            "outer_iteration": failure_capture["outer_iteration"],
            "shooting_enthalpy_j_kg": failure_capture["shooting_enthalpy_j_kg"],
            "support_projection": support_projection,
        },
    }


def _check_capture_replay(capture: dict[str, Any]) -> dict[str, Any]:
    target_trials = capture.get("target_cell_trials", [])
    endpoint_map = {item.get("q_w_repr"): item for item in target_trials}
    left = endpoint_map.get(repr(TARGET_LEFT_Q))
    right = endpoint_map.get(repr(TARGET_RIGHT_Q))
    if left is None or right is None:
        raise RuntimeError("original bracket endpoint trace missing")
    if (
        left.get("cell_evaluation_status") != "VALIDATED"
        or right.get("cell_evaluation_status") != "VALIDATED"
    ):
        raise RuntimeError("frozen endpoint evaluations were not both native VALIDATED")
    if left["task172_request_hash"] != left["task172_result_projection"]["request_hash"]:
        raise RuntimeError("left endpoint Task172 request hash mismatch")
    if right["task172_request_hash"] != right["task172_result_projection"]["request_hash"]:
        raise RuntimeError("right endpoint Task172 request hash mismatch")
    if (
        not left["task172_result_hash"] == left["task172_result_projection"]["result_hash"]
        or not right["task172_result_hash"] == right["task172_result_projection"]["result_hash"]
    ):
        raise RuntimeError("endpoint Task172 result hash mismatch")
    endpoint_identity_replays: list[dict[str, str]] = []
    target_trial_identity_replay_count = 0
    for trial in target_trials:
        for state_capture in trial.get("provider_ph_calls", []):
            state = state_capture["state_after_provider"]
            if canonical_sha256(state["property_snapshot"]) != state["property_snapshot_hash"]:
                raise RuntimeError("target-trial provider snapshot hash replay failed")
        native_call = trial.get("task172_call")
        if native_call is None:
            continue
        native_request = CandidateTask172LocalRequest.model_validate(
            _restore_pairs(native_call["request_projection"]), strict=True
        )
        replayed_request_hash = rating.recompute_task172_request_hash(native_request)
        if replayed_request_hash != native_call["request_hash"]:
            raise RuntimeError("target-trial Task172 request hash replay failed")
        if native_call["result_type"] == "Task172LocalResult":
            native_result = Task172LocalResult.model_validate(
                _restore_pairs(native_call["result_projection"]), strict=True
            )
            replayed_result_hash = rating.recompute_task172_result_hash(native_result)
            expected_result_hash = native_result.result_hash
        else:
            native_result = rating.Task172BlockedResult.model_validate(
                _restore_pairs(native_call["result_projection"]), strict=True
            )
            replayed_result_hash = rating.recompute_task172_blocked_result_hash(native_result)
            expected_result_hash = native_result.blocked_result_hash
        if (
            replayed_result_hash != expected_result_hash
            or replayed_result_hash != native_call["result_hash"]
        ):
            raise RuntimeError("target-trial Task172 result hash replay failed")
        target_trial_identity_replay_count += 1
    for label, endpoint in (("LEFT", left), ("RIGHT", right)):
        native_request = CandidateTask172LocalRequest.model_validate(
            _restore_pairs(endpoint["task172_request_projection"]), strict=True
        )
        native_result = Task172LocalResult.model_validate(
            _restore_pairs(endpoint["task172_result_projection"]), strict=True
        )
        replayed_request_hash = rating.recompute_task172_request_hash(native_request)
        replayed_result_hash = rating.recompute_task172_result_hash(native_result)
        if (
            replayed_request_hash != endpoint["task172_request_hash"]
            or replayed_result_hash != endpoint["task172_result_hash"]
            or native_request.support.physical_segment_id != TARGET_SUPPORT_ID
            or native_result.status != "VALIDATED"
        ):
            raise RuntimeError(f"{label} endpoint native Task172 identity replay failed")
        replayed_f = rating._d(float(endpoint["q_w_repr"])) - native_result.signed_q_hot_to_cold_w
        if str(replayed_f) != endpoint["f_production_decimal_context"]:
            raise RuntimeError(f"{label} endpoint production F replay failed")
        exact_binary_f = Decimal.from_float(float(endpoint["q_w_repr"]))
        with localcontext() as decimal_context:
            decimal_context.prec = 100
            exact_binary_f -= native_result.signed_q_hot_to_cold_w
        if str(exact_binary_f) != endpoint["f_exact_binary64_endpoint"]:
            raise RuntimeError(f"{label} endpoint exact binary64 F replay failed")
        for state_capture in endpoint["provider_ph_calls"]:
            state = state_capture["state_after_provider"]
            if canonical_sha256(state["property_snapshot"]) != state["property_snapshot_hash"]:
                raise RuntimeError(f"{label} endpoint provider snapshot hash replay failed")
        endpoint_identity_replays.append(
            {
                "side": label,
                "request_hash": replayed_request_hash,
                "result_hash": replayed_result_hash,
            }
        )
    if (
        Decimal(left["f_production_decimal_context"]) >= 0
        or Decimal(right["f_production_decimal_context"]) <= 0
    ):
        raise RuntimeError("original cell bracket no longer has the frozen sign orientation")
    if Decimal(left["f_production_decimal_context"]).copy_abs() <= Decimal("1e-6") or Decimal(
        right["f_production_decimal_context"]
    ).copy_abs() <= Decimal("1e-6"):
        raise RuntimeError("one frozen binary64 endpoint already satisfies point-root tolerance")
    if capture["failure"].get("shooting_enthalpy_j_kg") is None:
        raise RuntimeError("selected accepted shooting enthalpy was not captured")
    if capture["failure"].get("outer_iteration") is None:
        raise RuntimeError("accepted outer iteration was not captured")
    if (
        capture["failure"].get("tube_cell_id") is None
        or capture["failure"].get("shell_cell_id") is None
        or capture["failure"].get("wall_interface_id") is None
    ):
        raise RuntimeError("target cell physical identity capture is incomplete")
    certificate_replays = 0
    for certificate in capture.get("transient_outer_decision_certificates", []):
        if canonical_sha256(certificate["projection"]) != certificate["certificate_hash"]:
            raise RuntimeError("transient outer decision certificate hash replay failed")
        certificate_replays += 1
    return {
        "endpoint_request_result_identity_replay": "PASS",
        "left_f_production_decimal_context": left["f_production_decimal_context"],
        "right_f_production_decimal_context": right["f_production_decimal_context"],
        "left_task172_request_hash": left["task172_request_hash"],
        "right_task172_request_hash": right["task172_request_hash"],
        "left_task172_result_hash": left["task172_result_hash"],
        "right_task172_result_hash": right["task172_result_hash"],
        "endpoint_native_identity_replays": endpoint_identity_replays,
        "target_cell_trial_task172_identity_replay_count": target_trial_identity_replay_count,
        "transient_outer_decision_certificate_hash_replay_count": certificate_replays,
    }


def _execute() -> dict[str, Any]:
    runtime_binding = _assert_runtime_binding(execution=True)
    receipt_raw = CANDIDATE_RECEIPT.read_bytes()
    if _sha256(receipt_raw) != EXPECTED_CANDIDATE_RECEIPT_SHA256:
        raise RuntimeError("frozen Candidate A receipt raw SHA mismatch")
    receipt = json.loads(receipt_raw)
    frozen = receipt["candidates"][CANDIDATE_ID]
    frozen_result = frozen["result_projection"]
    if (
        receipt["completion_request_hash"] != COMPLETION_REQUEST_HASH
        or receipt["task168_candidate_space_hash"] != TASK168_SPACE_HASH
        or frozen["candidate_rating_request_hash"] != RATING_REQUEST_HASH
        or frozen["result_hash"] != EXPECTED_BLOCKED_RESULT_HASH
        or frozen["failed_mesh_subdivisions"] != TARGET_N
        or canonical_sha256(
            {
                key: frozen_result[key]
                for key in (
                    "schema_version",
                    "status",
                    "failure_code",
                    "failed_mesh_subdivisions",
                    "request_hash",
                    "diagnostics",
                )
            }
        )
        != EXPECTED_BLOCKED_RESULT_HASH
    ):
        raise RuntimeError("frozen target request/result binding mismatch")
    frozen_result_projection = {
        key: frozen_result[key]
        for key in (
            "schema_version",
            "status",
            "failure_code",
            "failed_mesh_subdivisions",
            "request_hash",
            "diagnostics",
            "result_hash",
            "result_id",
        )
    }
    started = time.monotonic()
    cpu_started = time.process_time()
    request_replay_started = time.monotonic()
    request_replay = subprocess.run(
        [sys.executable, str(REQUEST_REPLAY)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    request_replay_wall = time.monotonic() - request_replay_started
    if request_replay.returncode or "ALL_COMPLETION_REQUEST_REPLAY_PASS=true" not in (
        request_replay.stdout
    ):
        raise RuntimeError(
            f"committed completion request replay failed: {request_replay.stderr.strip()}"
        )
    request, request_facts = _reconstruct_candidate_a()
    if candidate_rating_request_hash(request) != RATING_REQUEST_HASH:
        raise RuntimeError("exact Candidate A request did not replay")
    ambient_before_provider = _context_snapshot()
    provider = CoolPropProvider()
    ambient_before_reconstruction = _context_snapshot(provider)
    provider_call_counts = {"state_ph": 0, "state_tp": 0}
    original_provider_state_ph = provider.state_ph
    original_provider_state_tp = provider.state_tp

    def counted_state_ph(*args: Any, **kwargs: Any) -> Any:
        provider_call_counts["state_ph"] += 1
        return original_provider_state_ph(*args, **kwargs)

    def counted_state_tp(*args: Any, **kwargs: Any) -> Any:
        provider_call_counts["state_tp"] += 1
        return original_provider_state_tp(*args, **kwargs)

    provider.state_ph = counted_state_ph
    provider.state_tp = counted_state_tp
    try:
        capture = _run_exact_n32(request, provider)
        capture["frozen_blocked_result_projection"] = frozen_result_projection
        actual_cell_failure = capture.get("failure", {})
        frozen_diagnostics = frozen_result["diagnostics"]
        actual_cell_diagnostics = actual_cell_failure.get("diagnostics", [])
        capture["frozen_failure_diagnostics_match"] = (
            actual_cell_failure.get("code") == frozen_result["failure_code"]
            and actual_cell_failure.get("mesh_subdivisions")
            == frozen_result["failed_mesh_subdivisions"]
            and actual_cell_failure.get("support_id") == TARGET_SUPPORT_ID
            and frozen_diagnostics[: len(actual_cell_diagnostics)] == actual_cell_diagnostics
            and frozen_diagnostics[-1] == f"mesh_subdivisions={TARGET_N}"
            and capture.get("n32_boundary_failure", {}).get("code") == frozen_result["failure_code"]
        )
        ambient_after_reconstruction = _context_snapshot(provider)
        capture["provider_state_ph_call_count_total"] = provider_call_counts["state_ph"]
        capture["provider_state_tp_call_count_total"] = provider_call_counts["state_tp"]
        capture["completion_request_replay"] = {
            "status": "PASS",
            "stdout": request_replay.stdout.strip().splitlines(),
            "wall_seconds": request_replay_wall,
        }
        capture["candidate_a_request_reconstruction"] = request_facts
        capture["runtime_binding"] = runtime_binding
        capture["ambient_before_provider_construction"] = ambient_before_provider
        capture["ambient_before_n32_reconstruction"] = ambient_before_reconstruction
        capture["ambient_after_n32_reconstruction"] = ambient_after_reconstruction
        capture["total_wall_seconds_including_candidate_preparation"] = time.monotonic() - started
        capture["total_process_cpu_seconds_including_candidate_preparation"] = (
            time.process_time() - cpu_started
        )
        capture["original_frozen_blocked_result_hash"] = EXPECTED_BLOCKED_RESULT_HASH
        capture["frozen_receipt_n32_evaluation_count"] = EXPECTED_N32_EVALUATIONS
        capture["frozen_receipt_n32_hole_count"] = EXPECTED_N32_HOLES
        capture["full_rating_invocation_performed"] = False
        capture["public_sizing_invocation_performed"] = False
        if (
            capture.get("task172_local_evaluation_count_from_stats") != EXPECTED_N32_EVALUATIONS
            or capture.get("task172_numerical_hole_count_from_stats") != EXPECTED_N32_HOLES
            or capture.get("failure", {}).get("code")
            != "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"
            or capture.get("failure", {}).get("support_id") != TARGET_SUPPORT_ID
            or not capture["frozen_failure_diagnostics_match"]
        ):
            capture["exact_target_cell_reconstructed"] = False
            capture["decimal_probe_count"] = 0
            capture["stop_reason"] = "ISOLATED_N32_FAILURE_SIGNATURE_DID_NOT_MATCH_FROZEN_TARGET"
            capture.pop("_native_target_objects", None)
            capture.pop("_native_provider", None)
            return capture
        capture["exact_target_cell_reconstructed"] = True
        replay = _check_capture_replay(capture)
        capture["original_endpoint_identity_replay"] = replay
        probe_wall_start = time.monotonic()
        probe_cpu_start = time.process_time()
        probes = _run_decimal_probes(capture, request)
        capture["decimal_probe_wall_seconds"] = time.monotonic() - probe_wall_start
        capture["decimal_probe_cpu_seconds"] = time.process_time() - probe_cpu_start
        capture["decimal_probe_experiment"] = probes
        capture["decimal_probe_count"] = probes["decimal_q_probe_count"]
        capture["decimal_probe_task172_invocation_count"] = probes["decimal_q_probe_count"]
        capture["total_solver_work"] = {
            "candidate_a_upstream_chain_count": 1,
            "candidate_a_task174_validation_count": 1,
            "isolated_n32_task172_validations": capture[
                "task172_local_evaluation_count_from_stats"
            ],
            "decimal_probe_native_task172_validations": probes["decimal_q_probe_count"],
            "task172_validations_total_in_gate": (
                capture["task172_local_evaluation_count_from_stats"]
                + probes["decimal_q_probe_count"]
            ),
            "public_candidate_rating_calls": 0,
            "public_sizing_calls": 0,
            "public_candidate_full_rating_reexecuted": False,
            "provider_state_ph_calls_total": provider_call_counts["state_ph"],
            "provider_state_tp_calls_total": provider_call_counts["state_tp"],
        }
        capture["accepted_trajectory_r2a_event_count"] = 0
        capture["accepted_trajectory_decision_certificate_hashes"] = []
        if any(event["mode"] == "DISABLED" for event in capture["transient_events"]):
            raise RuntimeError("an R2A event was incorrectly captured in accepted mode")
        capture.pop("_native_target_objects", None)
        capture.pop("_native_provider", None)
    finally:
        if "state_ph" in provider.__dict__:
            del provider.__dict__["state_ph"]
        if "state_tp" in provider.__dict__:
            del provider.__dict__["state_tp"]
    return capture


def _replay() -> None:
    _assert_runtime_binding(execution=False)
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if evidence["task_id"] != TASK_ID:
        raise RuntimeError("diagnostic evidence task identity mismatch")
    recorded_evidence_hash = evidence.pop("canonical_evidence_hash", None)
    if canonical_sha256(evidence) != recorded_evidence_hash:
        raise RuntimeError("diagnostic evidence canonical hash replay failed")
    if evidence["runtime_binding"]["runtime_source_head"] != RUNTIME_HEAD:
        raise RuntimeError("diagnostic runtime head binding mismatch")
    capture = evidence["diagnostic_execution"]
    if not capture.get("exact_target_cell_reconstructed"):
        fatal = capture.get("fatal_exception", {})
        if (
            evidence.get("result") == "BLOCKED_DIAGNOSTIC_RUNNER_OBSERVER_FAILURE"
            and fatal.get("type") == "AttributeError"
            and "Task172BlockedResult" in fatal.get("text", "")
            and capture.get("decimal_probe_count") == 0
        ):
            print("DIAGNOSTIC_ATTEMPT_RECEIPT_HASH_REPLAY=PASS")
            print("EXACT_TARGET_CELL_EVIDENCE_REPLAY=NOT_ESTABLISHED")
            print("DECIMAL_Q_PROBE_COUNT=0")
            return
        raise RuntimeError("committed evidence does not establish exact target cell")
    _check_capture_replay(capture)
    probes = capture["decimal_probe_experiment"]
    for probe in probes["probes"]:
        request = CandidateTask172LocalRequest.model_validate(
            _restore_pairs(probe["task172_request_projection"]), strict=True
        )
        if rating.recompute_task172_request_hash(request) != probe["task172_request_hash"]:
            raise RuntimeError(f"probe request hash mismatch: {probe['probe_index']}")
        result = (
            Task172LocalResult.model_validate(
                _restore_pairs(probe["task172_result_projection"]), strict=True
            )
            if probe["task172_status"] == "VALIDATED"
            else None
        )
        if result is None:
            blocked_type = rating.Task172BlockedResult
            blocked = blocked_type.model_validate(
                _restore_pairs(probe["task172_result_projection"]), strict=True
            )
            result_hash = rating.recompute_task172_blocked_result_hash(blocked)
            if result_hash != probe["task172_result_hash"]:
                raise RuntimeError(f"probe blocked result hash mismatch: {probe['probe_index']}")
        else:
            result_hash = rating.recompute_task172_result_hash(result)
            if result_hash != probe["task172_result_hash"]:
                raise RuntimeError(f"probe result hash mismatch: {probe['probe_index']}")
            with localcontext() as decimal_context:
                decimal_context.prec = 100
                replayed_f = Decimal(probe["q_decimal_exact"]) - result.signed_q_hot_to_cold_w
            if str(replayed_f) != probe["F_decimal_high_precision"]:
                raise RuntimeError(f"probe F replay mismatch: {probe['probe_index']}")
        for state in probe["provider_ph_inputs_outputs"]:
            if (
                canonical_sha256(state["provider_input_snapshot"])
                != state["provider_input_snapshot_hash"]
            ):
                raise RuntimeError(f"provider input snapshot hash mismatch: {probe['probe_index']}")
    print("EXACT_TARGET_CELL_EVIDENCE_REPLAY=PASS")
    print("TASK172_REQUEST_RESULT_IDENTITY_REPLAY=PASS")
    print("PROVIDER_SNAPSHOT_IDENTITY_REPLAY=PASS")
    print(f"DECIMAL_Q_PROBE_COUNT={probes['decimal_q_probe_count']}")
    print(f"MIN_ABS_F_W={probes['min_abs_f_w']}")
    print(f"POINT_ROOT_RECOVERED={str(probes['point_root_recovered']).lower()}")


def _restore_pairs(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("__task173_type__") == "ReferencePlanePair":
            return ReferencePlanePair(
                start=ReferencePlaneToken(value["start"]),
                end=ReferencePlaneToken(value["end"]),
            )
        return {key: _restore_pairs(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_pairs(item) for item in value]
    return value


def main() -> None:
    global LIVE_CAPTURE
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-exact-n32", action="store_true")
    parser.add_argument("--replay-only", action="store_true")
    args = parser.parse_args()
    if args.replay_only:
        _replay()
        return
    if not args.execute_exact_n32:
        raise SystemExit("select --execute-exact-n32 or --replay-only")
    started = time.monotonic()
    try:
        capture = _execute()
    except BaseException as exc:
        capture = (
            {key: value for key, value in LIVE_CAPTURE.items() if not key.startswith("_")}
            if LIVE_CAPTURE is not None
            else {}
        )
        capture.update(
            {
                "task_id": TASK_ID,
                "start_head": START_HEAD,
                "runtime_source_head": RUNTIME_HEAD,
                "fatal_exception": {
                    "type": type(exc).__name__,
                    "text": str(exc),
                },
                "decimal_probe_count": 0,
                "exact_target_cell_reconstructed": False,
                "elapsed_wall_seconds": time.monotonic() - started,
            }
        )
    finally:
        LIVE_CAPTURE = None
    payload: dict[str, Any] = {
        "schema_version": "task173.candidate-a-exact-cell-decimal-q-diagnostic.v1",
        "task_id": TASK_ID,
        "repository": "xuezhiorange-png/hxforge-agent",
        "pr_number": 283,
        "pr_state_required": "OPEN_DRAFT",
        "start_head": START_HEAD,
        "runtime_source_head": RUNTIME_HEAD,
        "runtime_source_tree": RUNTIME_TREE,
        "completion_sizing_request_hash": COMPLETION_REQUEST_HASH,
        "candidate_rating_request_hash": RATING_REQUEST_HASH,
        "candidate_id": CANDIDATE_ID,
        "candidate_hash": CANDIDATE_HASH,
        "task168_candidate_space_hash": TASK168_SPACE_HASH,
        "reviewed_r2a_authority_hash": R2A_AUTHORITY_HASH,
        "target": {
            "mesh_subdivisions": TARGET_N,
            "physical_support_id": TARGET_SUPPORT_ID,
            "left_q_w": repr(TARGET_LEFT_Q),
            "right_q_w": repr(TARGET_RIGHT_Q),
        },
        "production_code_changed": False,
        "r2a_authority_changed": False,
        "public_candidate_full_rating_reexecuted": False,
        "public_sizing_reexecuted": False,
        "task175_executed": False,
        "diagnostic_execution": capture,
    }
    payload["canonical_evidence_hash"] = canonical_sha256(payload)
    EVIDENCE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"EVIDENCE_PATH={EVIDENCE_PATH.relative_to(ROOT)}")
    print(f"EXACT_TARGET_CELL_RECONSTRUCTED={capture.get('exact_target_cell_reconstructed')}")
    print(f"DECIMAL_Q_PROBE_COUNT={capture.get('decimal_probe_count', 0)}")
    if capture.get("fatal_exception"):
        print(f"FATAL={capture['fatal_exception']['type']}:{capture['fatal_exception']['text']}")


if __name__ == "__main__":
    main()
