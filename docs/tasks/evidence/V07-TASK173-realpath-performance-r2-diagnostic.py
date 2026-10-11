"""Real TASK173 Candidate path diagnostics (R2) — external profiling only."""

from __future__ import annotations

import cProfile
import importlib.util
import json
import pstats
import signal
import sys
import time
import tracemalloc
from io import StringIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"
REQUEST_RUNNER = (
    ROOT / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
)


def _load_request_builder() -> Any:
    spec = importlib.util.spec_from_file_location("task173_q13_runner", REQUEST_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate request runner unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cumulative_coolprop_cache_stats(providers: list[Any]) -> dict[str, int]:
    hits = misses = size = 0
    for provider in providers:
        info = provider.cache_info()
        hits += info.hits
        misses += info.misses
        size += info.size
    return {
        "cumulative_cache_hits": hits,
        "cumulative_cache_misses": misses,
        "cumulative_cache_entries": size,
        "provider_instance_count": len(providers),
    }


def _install_counters(service: Any, counters: dict[str, int]) -> None:
    def wrap(name: str, fn: Any) -> Any:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            counters[name] = counters.get(name, 0) + 1
            return fn(*args, **kwargs)

        return wrapped

    for name, fn in (
        ("task172_validate", service.task172_validate),
        ("task172_validate_candidate", service.task172_validate_candidate),
        ("_solve_cell", service._solve_cell),
        ("_outer_trial", service._outer_trial),
    ):
        setattr(service, name, wrap(name, fn))


def _top_cprofile_stats(profiler: cProfile.Profile, limit: int = 25) -> list[dict[str, Any]]:
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(limit)
    rows: list[dict[str, Any]] = []
    for line in stream.getvalue().splitlines()[5 : 5 + limit]:
        parts = line.split()
        if len(parts) < 6:
            continue
        rows.append({"raw": line.strip()})
    return rows


def run_candidate_n1_realpath(
    *,
    cache_size: int,
    budget_s: float,
) -> dict[str, Any]:
    from hexagent.exchangers.shell_tube.task173_integrated_rating import service as task173_service
    from hexagent.properties.coolprop_provider import CoolPropProvider

    build_t0 = time.perf_counter()
    builder = _load_request_builder()
    requests = builder._build_candidate_requests()
    build_s = time.perf_counter() - build_t0
    _candidate, rating_request = requests[CANDIDATE_B_ID]

    context = task173_service._candidate_context(rating_request)
    token = task173_service._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=cache_size)
    providers_used = [provider]
    stats = task173_service._CellSearchStats()
    counters: dict[str, int] = {}
    _install_counters(task173_service, counters)

    holder: dict[str, Any] = {}
    error: list[str] = []

    class _DiagTimeout(Exception):
        pass

    def _on_alarm(signum: int, frame: Any) -> None:
        raise _DiagTimeout(f"budget_s={budget_s}")

    profiler = cProfile.Profile()
    tracemalloc.start()
    wall_t0 = time.perf_counter()
    previous = signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, budget_s)
    try:
        profiler.enable()
        holder["mesh_run"] = task173_service._candidate_transient_outer_boundary(
            1,
            provider,
            context.shell_authority,
            stats,
        )
        status = "PASS"
    except _DiagTimeout as exc:
        status = "TIMEOUT"
        error.append(str(exc))
    except Exception as exc:
        status = "FAIL"
        error.append(f"{type(exc).__name__}: {exc}")
    finally:
        profiler.disable()
        try:
            _, peak = tracemalloc.get_traced_memory()
            holder["peak_tracemalloc_bytes"] = peak
        except Exception:
            holder["peak_tracemalloc_bytes"] = None
        holder["cprofile_top"] = _top_cprofile_stats(profiler)
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        tracemalloc.stop()
        task173_service._CANDIDATE_RATING_CONTEXT.reset(token)

    wall_s = time.perf_counter() - wall_t0
    rating_completed = False
    if status == "PASS" and "mesh_run" in holder:
        holder["partial_mesh_subdivisions"] = 1

    cache = cumulative_coolprop_cache_stats(providers_used)
    return {
        "path": "candidate_rating._candidate_transient_outer_boundary",
        "candidate_id": CANDIDATE_B_ID,
        "cache_size": cache_size,
        "request_build_wall_seconds": build_s,
        "diagnostic_wall_seconds": wall_s,
        "budget_s": budget_s,
        "status": status,
        "rating_solve_completed": rating_completed,
        "task173_sizing_complete": False,
        "task172_local_evaluation_count": stats.task172_local_evaluation_count,
        "task172_numerical_hole_count": stats.task172_numerical_hole_count,
        "call_counters": counters,
        "coolprop_cache": cache,
        "error": error[0] if error else None,
        "cprofile_top": holder.get("cprofile_top"),
        "peak_tracemalloc_bytes": holder.get("peak_tracemalloc_bytes"),
        "notes": (
            "TIMEOUT means diagnostic budget exhausted, not BLOCKED/FAIL engineering outcome"
        ),
    }


def run_reference_r1_impact_note() -> dict[str, Any]:
    """Static analysis of R1 provider wiring (no extra compute)."""
    return {
        "reference_rating_validate_request": {
            "before_r1": "provider_factory=CoolPropProvider → new instance per mesh step",
            "after_r1": "_mesh_sequence_provider_factory → one shared default provider per call",
            "r1_behavior_change": True,
        },
        "candidate_rating_validate_candidate_rating": {
            "before_r1": "single active_provider + lambda factory (already shared per rating call)",
            "after_r1": "same sharing; default cache_size 256→2048 via default_task173_coolprop_provider",
            "r1_behavior_change": "cache_capacity_only",
        },
    }


def run_cache_256_vs_2048(budget_s_each: float = 25.0) -> dict[str, Any]:
    samples = []
    for size in (256, 2048):
        samples.append(run_candidate_n1_realpath(cache_size=size, budget_s=budget_s_each))
    a, b = samples[0], samples[1]
    eval_a = a.get("task172_local_evaluation_count") or 0
    eval_b = b.get("task172_local_evaluation_count") or 0
    wall_a = a["diagnostic_wall_seconds"]
    wall_b = b["diagnostic_wall_seconds"]
    throughput_a = eval_a / wall_a if wall_a > 0 else None
    throughput_b = eval_b / wall_b if wall_b > 0 else None
    return {
        "scenario": "candidate_b_n1_cache_compare",
        "samples": samples,
        "cumulative_cache_method": "sum(cache_info) over provider instances created in run",
        "task172_evaluations_per_wall_second": {
            "cache_256": throughput_a,
            "cache_2048": throughput_b,
        },
        "peak_tracemalloc_bytes": {
            "cache_256": a.get("peak_tracemalloc_bytes"),
            "cache_2048": b.get("peak_tracemalloc_bytes"),
        },
    }


def run_all(total_budget_s: float = 180.0) -> dict[str, Any]:
    started = time.time()
    report: dict[str, Any] = {
        "task_id": "V07_TASK173_REALPATH_PERFORMANCE_R2",
        "attempt3_final_result": "NONE",
        "r1_impact": run_reference_r1_impact_note(),
        "sections": [],
    }
    per = min(60.0, total_budget_s / 2.0)
    report["sections"].append(
        run_candidate_n1_realpath(cache_size=2048, budget_s=per)
    )
    remaining = total_budget_s - (time.time() - started)
    if remaining > 10:
        report["sections"].append(
            run_cache_256_vs_2048(budget_s_each=min(25.0, remaining / 2.0))
        )
    report["total_wall_seconds"] = time.time() - started
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--total-budget-s", type=float, default=180.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run_all(total_budget_s=args.total_budget_s)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "total_wall_seconds": payload["total_wall_seconds"]}))
