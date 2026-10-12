"""Strict experimental mesh identity replay against frozen R3/R4/R5 evidence."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.base import PropertyProvider
from prototypes.v07_fast_solver_n4_mesh_convergence_r5.mesh_replay import (
    mesh_observables_payload,
    replay_mesh_at_enthalpy,
)

ROOT = Path(__file__).resolve().parents[2]
R3_EVIDENCE = ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-outer-boundary-r3-20261012T122052Z.json"
R4_EVIDENCE = (
    ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-n2-outer-boundary-r4-20261012T134805Z.json"
)
R5_EVIDENCE = (
    ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-n4-mesh-convergence-r5-20261012T140705Z.json"
)

SUMMARY_FIELD_MAP: dict[str, str] = {
    "duty_w": "total_duty_w",
    "tube_outlet_temperature_k": "tube_outlet_temperature_k",
    "shell_outlet_temperature_k": "shell_outlet_temperature_k",
    "energy_balance_residual_w": "energy_balance_residual_w",
    "terminal_boundary_residual_k": "terminal_boundary_residual_k",
    "terminal_boundary_residual_j_kg": "terminal_boundary_residual_j_kg",
}


def _as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _field_diffs(expected: dict[str, Any], actual: dict[str, Any]) -> list[dict[str, str]]:
    diffs: list[dict[str, str]] = []
    keys = sorted(set(expected) | set(actual))
    for key in keys:
        ev = expected.get(key)
        av = actual.get(key)
        if ev == av:
            continue
        de = _as_decimal(ev)
        da = _as_decimal(av)
        if de is not None and da is not None and de == da:
            continue
        if isinstance(ev, list) and isinstance(av, list) and ev == av:
            continue
        diffs.append(
            {
                "field": key,
                "expected": json.dumps(ev, sort_keys=True) if not isinstance(ev, str) else ev,
                "actual": json.dumps(av, sort_keys=True) if not isinstance(av, str) else av,
            }
        )
    return diffs


def _load_n1_evidence() -> dict[str, Any]:
    data = json.loads(R3_EVIDENCE.read_text(encoding="utf-8"))
    for run in data.get("runs", []):
        if run.get("mesh_n") == 1 and run.get("status") == "COMPLETED":
            return run["result"]
    raise RuntimeError("R3 n=1 evidence missing")


def _load_n2_evidence() -> dict[str, Any]:
    data = json.loads(R4_EVIDENCE.read_text(encoding="utf-8"))
    body = data.get("n2_run", {}).get("result", {})
    if body.get("outer_boundary_status") != "TERMINAL_ACCEPTED":
        raise RuntimeError("R4 n=2 evidence missing")
    return body


def _load_n4_evidence() -> dict[str, Any]:
    data = json.loads(R5_EVIDENCE.read_text(encoding="utf-8"))
    body = data.get("n4_run", {}).get("result", {})
    if body.get("outer_boundary_status") != "TERMINAL_ACCEPTED":
        raise RuntimeError("R5 n=4 evidence missing")
    return body


def _bisection_iterations_from_evidence(body: dict[str, Any], subdivisions: int) -> int:
    iterations = body.get("bisection_iterations")
    if iterations is None:
        raise RuntimeError(f"bisection_iterations missing for n={subdivisions}")
    return int(iterations)


def _expected_summary_observables(body: dict[str, Any]) -> dict[str, Any]:
    summary = body.get("observables") or body.get("observables_summary") or {}
    mapped: dict[str, Any] = {}
    for summary_key, obs_key in SUMMARY_FIELD_MAP.items():
        if summary_key in summary:
            mapped[obs_key] = summary[summary_key]
    mesh_hash = summary.get("experimental_mesh_result_hash")
    if mesh_hash:
        mapped["rating_result_hash"] = mesh_hash
    return mapped


def strict_replay_level(
    subdivisions: int,
    evidence_body: dict[str, Any],
    evidence_path: Path,
    provider: PropertyProvider,
    shell_authority: Any,
    *,
    rating_request_hash: str,
) -> dict[str, Any]:
    outer_iterations = _bisection_iterations_from_evidence(evidence_body, subdivisions)
    shooting = evidence_body["shooting_enthalpy_j_kg"]
    expected_rating_hash = evidence_body["rating_request_hash"]
    expected_mesh_hash = (
        evidence_body.get("observables") or evidence_body.get("observables_summary") or {}
    )["experimental_mesh_result_hash"]
    full_expected = evidence_body.get("mesh_observables")

    run, replay_meta = replay_mesh_at_enthalpy(
        subdivisions,
        shooting,
        provider,
        shell_authority,
        outer_iterations=outer_iterations,
        expected_mesh_hash=expected_mesh_hash,
        source_label=str(evidence_path),
    )
    actual_obs = mesh_observables_payload(run)
    parity: Literal["PASS", "FAIL"] = "PASS"
    mismatches: list[dict[str, Any]] = []

    if expected_rating_hash != rating_request_hash:
        parity = "FAIL"
        mismatches.append(
            {
                "kind": "rating_request_hash",
                "expected": expected_rating_hash,
                "actual": rating_request_hash,
            }
        )

    if run.mesh_result_hash != expected_mesh_hash:
        parity = "FAIL"
        mismatches.append(
            {
                "kind": "mesh_result_hash",
                "expected": expected_mesh_hash,
                "actual": run.mesh_result_hash,
            }
        )

    if run.bisection_iterations != outer_iterations:
        parity = "FAIL"
        mismatches.append(
            {
                "kind": "mesh_run_bisection_iterations",
                "expected": str(outer_iterations),
                "actual": str(run.bisection_iterations),
            }
        )

    if not t173._terminal_tolerance_pass(run):
        parity = "FAIL"
        mismatches.append(
            {"kind": "terminal_tolerance_pass", "expected": "True", "actual": "False"}
        )

    if full_expected is not None:
        field_diffs = _field_diffs(full_expected, actual_obs)
        if field_diffs:
            parity = "FAIL"
            mismatches.append({"kind": "mesh_observables_field_diffs", "diffs": field_diffs})
    else:
        summary_expected = _expected_summary_observables(evidence_body)
        subset_actual = {k: actual_obs[k] for k in summary_expected if k in actual_obs}
        field_diffs = _field_diffs(summary_expected, subset_actual)
        if field_diffs:
            parity = "FAIL"
            mismatches.append({"kind": "summary_observables_field_diffs", "diffs": field_diffs})
        local_hashes = actual_obs.get("local_task172_result_hashes")
        if local_hashes is not None:
            replay_meta["local_task172_result_hashes"] = local_hashes

    replay_meta["hash_parity"] = parity
    replay_meta["mismatches"] = mismatches
    replay_meta["evidence_bisection_iterations"] = outer_iterations
    replay_meta["evidence_rating_request_hash"] = expected_rating_hash
    replay_meta["_mesh_run"] = run
    return replay_meta


def strict_replay_all(
    provider: PropertyProvider,
    shell_authority: Any,
    rating_request_hash: str,
) -> dict[str, Any]:
    n1 = strict_replay_level(
        1,
        _load_n1_evidence(),
        R3_EVIDENCE,
        provider,
        shell_authority,
        rating_request_hash=rating_request_hash,
    )
    n2 = strict_replay_level(
        2,
        _load_n2_evidence(),
        R4_EVIDENCE,
        provider,
        shell_authority,
        rating_request_hash=rating_request_hash,
    )
    n4 = strict_replay_level(
        4,
        _load_n4_evidence(),
        R5_EVIDENCE,
        provider,
        shell_authority,
        rating_request_hash=rating_request_hash,
    )
    all_pass = (
        n1["hash_parity"] == "PASS"
        and n2["hash_parity"] == "PASS"
        and n4["hash_parity"] == "PASS"
    )
    return {
        "n1_replay": {k: v for k, v in n1.items() if k != "_mesh_run"},
        "n2_replay": {k: v for k, v in n2.items() if k != "_mesh_run"},
        "n4_replay": {k: v for k, v in n4.items() if k != "_mesh_run"},
        "all_replay_hash_parity": all_pass,
        "_mesh_runs": {
            "n1": n1["_mesh_run"],
            "n2": n2["_mesh_run"],
            "n4": n4["_mesh_run"],
        },
    }
