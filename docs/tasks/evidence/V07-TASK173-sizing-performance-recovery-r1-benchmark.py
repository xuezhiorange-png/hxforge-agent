"""Real TASK173/TASK172 performance samples for V07_TASK173_SIZING_PERFORMANCE_RECOVERY_R1.

Uses production validate_request paths only (no mock solvers). Each sample is bounded
by the caller (see bounded_runner).
"""

from __future__ import annotations

import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from hexagent.exchangers.shell_tube.task172_local_runtime import (
    recompute_task172_result_hash,
    validate_request,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as task173_service
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    REVIEWED_MESH_SEQUENCE,
    TASK173_COOLPROP_CACHE_SIZE,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.replay import (
    replay_shell_flow_authority,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EVIDENCE_REPLAY = (
    ROOT / "docs/tasks/evidence/TASK-172-stage2-native-shell-flow-replay-correction-r1.json"
)
TASK172_FIXTURE = ROOT / "tests/exchangers/shell_tube/fixtures/task172_fail_only_dogbox_characterization_r1.json"


@dataclass(frozen=True)
class BenchmarkSample:
    name: str
    wall_seconds: float
    task172_evaluations: int | None
    coolprop_cache_hits: int | None
    coolprop_cache_misses: int | None
    coolprop_cache_size: int | None
    result_hash: str | None
    status: str
    notes: str


def _load_task172_request() -> Any:
    from tests.exchangers.shell_tube.test_task172_local_runtime import _request

    return _request()


def _task172_hash(outcome: Any) -> str:
    if hasattr(outcome, "result_hash"):
        return str(outcome.result_hash)
    return recompute_task172_result_hash(outcome)


def benchmark_task172_mesh_provider_pattern() -> dict[str, Any]:
    """Simulate per-mesh fresh provider (pre-fix validate_request) vs shared mesh factory."""
    request = _load_task172_request()
    mesh_steps = len(REVIEWED_MESH_SEQUENCE)

    def per_mesh_fresh() -> tuple[float, str, Any]:
        hashes: list[str] = []
        t0 = time.perf_counter()
        last_info = None
        for _ in REVIEWED_MESH_SEQUENCE:
            provider = CoolPropProvider(cache_size=256)
            outcome = validate_request(request, provider)
            hashes.append(_task172_hash(outcome))
            last_info = provider.cache_info()
        elapsed = time.perf_counter() - t0
        assert all(h == hashes[0] for h in hashes)
        return elapsed, hashes[0], last_info

    def shared_mesh_factory() -> tuple[float, str, Any]:
        factory = task173_service._mesh_sequence_provider_factory(None)
        hashes: list[str] = []
        t0 = time.perf_counter()
        last_info = None
        for _ in REVIEWED_MESH_SEQUENCE:
            provider = factory()
            outcome = validate_request(request, provider)
            hashes.append(_task172_hash(outcome))
            last_info = provider.cache_info()
        elapsed = time.perf_counter() - t0
        assert all(h == hashes[0] for h in hashes)
        return elapsed, hashes[0], last_info

    before_s, before_hash, before_info = per_mesh_fresh()
    after_s, after_hash, after_info = shared_mesh_factory()
    speedup = before_s / after_s if after_s > 0 else None
    return {
        "scenario": "task172_validate_request_x_mesh_steps",
        "mesh_steps": mesh_steps,
        "baseline": {
            "pattern": "new CoolPropProvider(cache_size=256) per mesh step",
            "wall_seconds": before_s,
            "result_hash": before_hash,
            "cache_hits": before_info.hits if before_info else None,
            "cache_misses": before_info.misses if before_info else None,
        },
        "optimized": {
            "pattern": f"shared provider via _mesh_sequence_provider_factory (cache_size={TASK173_COOLPROP_CACHE_SIZE})",
            "wall_seconds": after_s,
            "result_hash": after_hash,
            "cache_hits": after_info.hits if after_info else None,
            "cache_misses": after_info.misses if after_info else None,
        },
        "engineering_hash_match": before_hash == after_hash,
        "speedup_ratio": speedup,
    }


def benchmark_native_replay() -> dict[str, Any]:
    evidence = json.loads(EVIDENCE_REPLAY.read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    provider = task173_service.default_task173_coolprop_provider()
    authority, _task174, replay = replay_shell_flow_authority(evidence, provider)
    elapsed = time.perf_counter() - t0
    info = provider.cache_info()
    return {
        "scenario": "task173_native_shell_flow_replay",
        "wall_seconds": elapsed,
        "replay_status": replay.get("status"),
        "cache_hits": info.hits,
        "cache_misses": info.misses,
        "cache_size": info.size,
        "cache_max_size": info.max_size,
    }


def _outer_boundary_subdivisions_1_payload(evidence: dict[str, Any]) -> dict[str, Any]:
    provider = task173_service.default_task173_coolprop_provider()
    authority, _, _ = replay_shell_flow_authority(evidence, provider)
    stats = task173_service._CellSearchStats()
    run = task173_service._solve_outer_boundary(1, provider, authority, stats)
    info = provider.cache_info()
    return {
        "mesh_result_hash": run.mesh_result_hash,
        "task172_local_evaluation_count": stats.task172_local_evaluation_count,
        "task172_numerical_hole_count": stats.task172_numerical_hole_count,
        "cache_hits": info.hits,
        "cache_misses": info.misses,
    }


def benchmark_task173_outer_boundary_subdivisions_1(timeout_s: float) -> dict[str, Any]:
    """Heavy sample; thread join timeout (parent returns TIMEOUT without inferring failure)."""
    import threading

    evidence = json.loads(EVIDENCE_REPLAY.read_text(encoding="utf-8"))
    holder: dict[str, Any] = {}
    error: list[str] = []

    def _target() -> None:
        try:
            holder["payload"] = _outer_boundary_subdivisions_1_payload(evidence)
        except Exception as exc:
            error.append(f"{type(exc).__name__}: {exc}")

    t0 = time.perf_counter()
    thread = threading.Thread(target=_target, name="task173-outer-n1", daemon=True)
    thread.start()
    thread.join(timeout=timeout_s)
    elapsed = time.perf_counter() - t0
    if thread.is_alive():
        return {
            "scenario": "task173_solve_outer_boundary_subdivisions_1",
            "status": "TIMEOUT",
            "wall_seconds": elapsed,
            "timeout_budget_s": timeout_s,
            "notes": "Thread still running at budget; no numerical failure inferred",
        }
    if error:
        return {
            "scenario": "task173_solve_outer_boundary_subdivisions_1",
            "status": "FAIL",
            "wall_seconds": elapsed,
            "error": error[0],
        }
    return {
        "scenario": "task173_solve_outer_boundary_subdivisions_1",
        "status": "PASS",
        "wall_seconds": elapsed,
        "timeout_budget_s": timeout_s,
        **holder.get("payload", {}),
    }


def run_all(timeout_s: float = 120.0) -> dict[str, Any]:
    started = time.time()
    report: dict[str, Any] = {
        "task_id": "V07_TASK173_SIZING_PERFORMANCE_RECOVERY_R1",
        "attempt3_final_result": "NONE — user-terminated Mac Attempt 3; not numerical evidence",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "coolprop": __import__("CoolProp").__version__,
        },
        "samples": [],
    }
    report["samples"].append(benchmark_task172_mesh_provider_pattern())
    report["samples"].append(benchmark_native_replay())
    remaining = max(5.0, timeout_s - (time.time() - started))
    report["samples"].append(
        benchmark_task173_outer_boundary_subdivisions_1(min(remaining, timeout_s))
    )
    report["ended_at_epoch_s"] = time.time()
    report["total_wall_seconds"] = report["ended_at_epoch_s"] - started
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run_all(timeout_s=args.timeout_s)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "total_wall_seconds": payload["total_wall_seconds"]}))
