"""Run the frozen R95 mesh matrix with reviewed R98/R102 overlays.

This test-only runner does not change production code or numerical authority.
It uses the frozen synthetic fixture and mesh definitions, the reviewed R98
cell residual overlay, and the reviewed R102 SciPy canonical reference rows.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256  # noqa: E402

REGISTRY = ROOT / "docs/tasks/TASK-172-v0.7-authority-registry-r1.json"
R95_RUNNER = ROOT / "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-runner-r1.py"
R99_RUNNER = ROOT / "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-runner-r2.py"
R99_EVIDENCE = ROOT / "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-r2.json"
R99_RESULTS = ROOT / "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-results-r2.json"
R100_RESULTS = (
    ROOT / "docs/tasks/evidence/TASK-172-continuous-reference-oracle-precision-results-r1.json"
)
R102_RESULTS = ROOT / (
    "docs/tasks/evidence/"
    "TASK-172-continuous-reference-oracle-scipy-canonical-envelope-binding-results-r1.json"
)

AUTHORIZED_HEAD = "a651c9ad92e391f203f79440b1855405a0d2a46f"
PRE_APPEND_REGISTRY_HASH = "34b613b6e6aff581b48adb7245e9541f4c1b7d2367bb21c8f9bd7d992923f25f"
R95_INPUT_HASH = "b13d4306f3a2a60f248fbd1b222a6069599ec08a3c094996b17019ac315ae2d8"
R99_EXTENSION_HASH = "004f8d19ffd85b0d1429e3d2da298676d953c40fa61635a8a8144a3117a0a934"
R100_EXTENSION_HASH = "9e1210f35c3e52f83cdffde3b23f0fc78f8b8b75e1fbbd2e35c07039095b6701"
R101_EXTENSION_HASH = "fc4265c2f2db3bcda49dc032a5d5cd6065a79a1e26f31f2ea40cbaed0fde0b3c"
R102_EXTENSION_HASH = "312e738418251861ccf2c1850e9d487069dd695d5295cff5a3af680c5a7ef615"
R102_RESULTS_FILE_SHA256 = "1515994982ac948fd79b687fec989ee39e8639aa5416fa6db789d039f21a0222"
R102_RESULTS_CANONICAL_HASH = "8ff57c42b8a78afad395ca6f560886ec1d3f915fda6f2d65bf6d3b3c16cf53ae"
R102_PRODUCER = "SCIPY_SPECIAL_ROOTS_LEGENDRE_ORDER_1024"
EXPECTED_R99_RESULT = "BLOCKED_MESH_CONVERGENCE_QUALIFICATION_R2"
EXPECTED_LIFECYCLE = "REVIEWED_AUTHORITY"
EXPECTED_UQ_CLASS = "MEASURED_EMPIRICAL_NUMERICAL_REFERENCE_UNCERTAINTY_ENVELOPE"
EXPECTED_PROFILE: dict[str, Any] = {
    "candidate_id": "P1_ACCEPTANCE_EXTENSION",
    "method": "trf",
    "loss": "linear",
    "ftol": 1e-6,
    "xtol": 1e-12,
    "gtol": 1e-12,
    "jacobian": "2-point",
    "diff_step": 1e-5,
    "x_scale": "INITIALIZATION_DERIVED",
    "max_nfev": 6,
    "residual_callback_cap": 24,
    "residual_scale": "abs(q_ts_seed)",
    "c_round": 1.0,
    "tr_solver": "exact",
    "tr_options": {},
    "f_scale": 1.0,
    "jac_sparsity": None,
}


class GateFailure(RuntimeError):
    """A fail-closed input, execution, or qualification error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{data}\n", encoding="utf-8")


def load_module(path: Path, name: str) -> Any:
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateFailure(f"cannot load frozen runner: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def current_head() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def artifact_pairs(artifacts: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for path_key, path_value in artifacts.items():
        if not path_key.endswith("_path") or not isinstance(path_value, str):
            continue
        prefix = path_key[:-5]
        candidate_keys = (f"{prefix}_sha256", f"{prefix}_file_sha256")
        hash_key = next((key for key in candidate_keys if key in artifacts), None)
        if hash_key is not None:
            pairs.append((path_value, str(artifacts[hash_key])))
    return pairs


def verify_predecessor_and_history() -> dict[str, Any]:
    observed_head = current_head()
    require(observed_head == AUTHORIZED_HEAD, f"BLOCKED_HEAD_CHANGED:{observed_head}")
    registry = read_json(REGISTRY)
    require(
        canonical_sha256(registry) == PRE_APPEND_REGISTRY_HASH, "pre-append registry root changed"
    )
    ext_hashes: dict[str, str] = {}
    artifact_hash_count = 0
    # The registry's original frozen record is not named r1_extension; its
    # append-only numbered chain begins at r2_extension.
    for number in range(2, 103):
        key = f"r{number}_extension"
        extension = cast(dict[str, Any], registry[key])
        actual_extension_hash = canonical_sha256(extension)
        if number >= 95 and "canonical_hash" in extension:
            require(
                actual_extension_hash == str(extension["canonical_hash"]),
                f"bad {key} canonical hash",
            )
        ext_hashes[key] = actual_extension_hash
        if number >= 95:
            artifacts = cast(dict[str, Any], extension.get("artifacts", {}))
            for relative_path, expected_hash in artifact_pairs(artifacts):
                path = ROOT / relative_path
                require(
                    path.is_file() and sha256_file(path) == expected_hash,
                    f"historical artifact hash mismatch: {relative_path}",
                )
                artifact_hash_count += 1

    require(ext_hashes["r99_extension"] == R99_EXTENSION_HASH, "R99 extension changed")
    require(ext_hashes["r100_extension"] == R100_EXTENSION_HASH, "R100 extension changed")
    require(ext_hashes["r101_extension"] == R101_EXTENSION_HASH, "R101 extension changed")
    require(ext_hashes["r102_extension"] == R102_EXTENSION_HASH, "R102 extension changed")
    r99 = cast(dict[str, Any], registry["r99_extension"])
    r100 = cast(dict[str, Any], registry["r100_extension"])
    r101 = cast(dict[str, Any], registry["r101_extension"])
    r102 = cast(dict[str, Any], registry["r102_extension"])
    require(r99["result"] == EXPECTED_R99_RESULT, "R99 historical blocker result changed")
    require(
        r101["independent_review"]["continuous_reference_oracle_precision_independent_review_pass"]
        and r101["independent_review"]["canonical_reference_producer"] == R102_PRODUCER,
        "R101 precision authority replay failed",
    )
    require(
        r102["result"] == "PASS_SCIPY_CANONICAL_ENVELOPE_BINDING_CORRECTION"
        and r102["lifecycle_and_blockers"]["continuous_reference_oracle_precision_lifecycle"]
        == EXPECTED_LIFECYCLE,
        "R102 reviewed authority replay failed",
    )
    require(
        r100["result"] == "CONTINUOUS_REFERENCE_ORACLE_PRECISION_CANDIDATE_COMPLETED",
        "R100 historical candidate identity changed",
    )

    r99_evidence = read_json(R99_EVIDENCE)
    r99_results = read_json(R99_RESULTS)
    require(
        r99_evidence["result"] == EXPECTED_R99_RESULT,
        "R99 evidence is not the frozen blocked result",
    )
    require(r99_results["study_status"] == EXPECTED_R99_RESULT, "R99 results blocker not preserved")
    q_hist = {
        "128": 0.2222234220550436,
        "256": 0.22222342205515927,
        "512": 0.22222342205526033,
    }
    q_hist_observed = r99_evidence["continuous_oracle_blocker"]["Q_ref_W"]
    require(
        all(float(q_hist_observed[key]) == value for key, value in q_hist.items()),
        "R99 M05 quadrature values changed",
    )
    d_256_512 = abs(q_hist["256"] - q_hist["512"])
    criterion = 64.0 * math.ulp(q_hist["512"])
    require(d_256_512 > criterion, "R99 historical 64-ULP failure did not reproduce")
    r99_replay = {
        "result": EXPECTED_R99_RESULT,
        "historical_values_exact": True,
        "M05_GL128_W": q_hist["128"],
        "M05_GL256_W": q_hist["256"],
        "M05_GL512_W": q_hist["512"],
        "difference_GL256_GL512_W": d_256_512,
        "64_ulp_criterion_W": criterion,
        "historical_64_ulp_gate_still_fails": True,
        "historical_record_rewritten": False,
    }

    r102_results = read_json(R102_RESULTS)
    require(
        sha256_file(R102_RESULTS) == R102_RESULTS_FILE_SHA256, "R102 result file SHA256 mismatch"
    )
    require(
        canonical_sha256(r102_results) == R102_RESULTS_CANONICAL_HASH,
        "R102 results canonical hash mismatch",
    )
    require(r102_results["canonical_reference_producer"] == R102_PRODUCER, "R102 producer mismatch")
    require(
        r102_results["uncertainty_classification"] == EXPECTED_UQ_CLASS
        and r102_results["formal_true_error_bound"] is False
        and r102_results["conservative_wording_accepted"] is False
        and r102_results["reference_uncertainty_propagation_required"] is True,
        "R102 uncertainty semantics changed",
    )

    return {
        "authorized_head": observed_head,
        "pre_append_registry_canonical_hash": PRE_APPEND_REGISTRY_HASH,
        "historical_extension_canonical_hashes": ext_hashes,
        "historical_artifact_hash_count_verified": artifact_hash_count,
        "historical_R1_R102_payloads_immutable_at_predecessor": True,
        "historical_R1_R102_extensions_rewritten": False,
        "R99_historical_replay": r99_replay,
        "R100_R101_R102_authority_replay": {
            "R100_candidate_result_preserved": True,
            "R101_independent_review_passed": True,
            "R102_result": "PASS_SCIPY_CANONICAL_ENVELOPE_BINDING_CORRECTION",
            "continuous_reference_precision_lifecycle": EXPECTED_LIFECYCLE,
            "canonical_reference_producer": R102_PRODUCER,
            "reference_uncertainty_propagation_required": True,
            "formal_true_error_bound": False,
        },
        "R102_results_canonical_hash": R102_RESULTS_CANONICAL_HASH,
    }


def pointwise_domain_audits(r95: Any, r99: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in r95.FIXTURE_ROWS:
        fixture_id = str(row["fixture_id"])
        result[fixture_id] = r99.pointwise_state_domain_audit(r95, fixture_id)
    return result


def make_reference_provider(r95: Any, r102_rows: dict[str, dict[str, Any]]) -> Any:
    def provide(
        r94: Any,
        fixture_id: str,
        oracle_cache: dict[tuple[str, str], dict[str, Any]],
    ) -> dict[str, Any]:
        canonical = r102_rows[fixture_id]
        extrema_by_grid = {
            "257": r95.wall_extrema_for_grid(fixture_id, 257, oracle_cache, r94),
            "513": r95.wall_extrema_for_grid(fixture_id, 513, oracle_cache, r94),
        }
        low = extrema_by_grid["257"]
        high = extrema_by_grid["513"]
        wall_keys = ("Twi_min", "Twi_max", "Two_min", "Two_max")
        differences = {
            key: abs(float(low[key]["value_K"]) - float(high[key]["value_K"])) for key in wall_keys
        }
        max_difference = max(differences.values())
        stable = max_difference <= 1e-8
        require(stable, f"continuous wall extrema stability failed: {fixture_id}")
        return {
            "Q_ref_W": float(canonical["Q_REF_CANONICAL_W"]),
            "Q_ref_producer": R102_PRODUCER,
            "U_Q_CANONICAL_W": float(
                canonical["canonical_uncertainty_components_W"]["U_Q_CANONICAL"]
            ),
            "uncertainty_components_W": canonical["canonical_uncertainty_components_W"],
            "uncertainty_classification": EXPECTED_UQ_CLASS,
            "formal_true_error_bound": False,
            "proven_global_upper_bound": False,
            "reference_uncertainty_propagation_required": True,
            "gauss_legendre_orders": {
                key: float(value["Q_W"]) for key, value in canonical["scipy_gauss_legendre"].items()
            },
            "gauss_legendre_precision_audit": {
                "abs_Q256_minus_Q512_W": float(
                    canonical["canonical_uncertainty_components_W"]["U_GL_CANONICAL"]
                ),
                "criterion_pass": True,
            },
            "wall_extrema_reference_K": {key: float(high[key]["value_K"]) for key in wall_keys},
            "wall_extrema_reference_locations_xi": {
                key: float(high[key]["xi"]) for key in wall_keys
            },
            "wall_extrema_sampling_refinement": extrema_by_grid,
            "wall_extrema_sampling_refinement_differences_K": differences,
            "wall_extrema_sampling_refinement_max_difference_K": max_difference,
            "wall_extrema_stability_criterion_K": 1e-8,
            "wall_extrema_reference_stable": stable,
            "independent_scalar_oracle_at_each_node": True,
            "oracle_grid_count_each_root": 33,
            "production_mesh_used_as_reference": False,
            "production_scalar_reduction_selected": False,
        }

    return provide


def attach_r102_reference_uncertainty(r95: Any, fixture_results: list[dict[str, Any]]) -> None:
    original_enrich = r95.enrich_mesh_levels

    def enrich(
        fixture_id: str,
        sequence_id: str,
        levels: list[dict[str, Any]],
        reference: dict[str, Any],
    ) -> None:
        original_enrich(fixture_id, sequence_id, levels, reference)
        uq = float(reference["U_Q_CANONICAL_W"])
        q_ref = abs(float(reference["Q_ref_W"]))
        for level in levels:
            audit = cast(dict[str, Any], level["independent_continuous_oracle"])
            raw = float(audit["Q_abs_error_W"])
            solver_floor = float(audit["Q_solver_precision_floor_W"])
            lower = q_ref - uq
            if fixture_id == "M05":
                aware_abs = raw + uq
                aware_metric: float | None = None
                aware_pass_basis = "ABSOLUTE_W"
            else:
                aware_abs = raw + uq
                aware_metric = aware_abs / lower if lower > 0.0 else None
                aware_pass_basis = "RELATIVE"
            audit.update(
                {
                    "Q_oracle_quadrature_difference_W": uq,
                    "Q_reference_uncertainty_envelope_W": uq,
                    "Q_reference_lower_magnitude_W": None if fixture_id == "M05" else lower,
                    "Q_raw_abs_error_W": raw,
                    "Q_reference_aware_abs_error_plus_UQ_W": aware_abs,
                    "Q_reference_aware_relative_error": aware_metric,
                    "Q_solver_precision_floor_W": solver_floor,
                    "Q_error_envelope_class": "R102_EMPIRICAL_UQ_PROPAGATED_FOR_ACCEPTANCE",
                    "formal_true_error_bound": False,
                    "reference_uncertainty_propagated": True,
                    "acceptance_metric_basis": aware_pass_basis,
                }
            )

    r95.enrich_mesh_levels = enrich


def install_r102_acceptance_rule(r95: Any) -> None:
    def oracle_error_class_pass(
        level: dict[str, Any],
        *,
        duty_relative_threshold: float,
        near_zero_absolute_threshold_W: float,
        wall_threshold_K: float,
        near_zero: bool,
    ) -> dict[str, Any]:
        audit = cast(dict[str, Any], level["independent_continuous_oracle"])
        q_floor = float(audit["Q_solver_precision_floor_W"])
        uq = float(audit["Q_reference_uncertainty_envelope_W"])
        q_error = float(audit["Q_raw_abs_error_W"])
        wall_floor = float(audit["wall_solver_precision_floor_K"])
        wall_error = float(audit["wall_extrema_max_abs_error_K"])
        if near_zero:
            q_upper = q_error + q_floor + uq
            q_pass = q_upper <= near_zero_absolute_threshold_W
            q_observed: float | None = q_error
            q_threshold = near_zero_absolute_threshold_W
            denominator_lower: float | None = None
        else:
            q_ref = abs(float(audit["Q_ref_W"]))
            denominator_lower = q_ref - uq
            q_upper = (
                (q_error + q_floor + uq) / denominator_lower
                if denominator_lower > 0.0
                else math.inf
            )
            q_pass = denominator_lower > 0.0 and q_upper <= duty_relative_threshold
            q_observed = float(audit["Q_relative_error"])
            q_threshold = duty_relative_threshold
        wall_stability = float(level.get("wall_extrema_oracle_reference_stability_error_K", 0.0))
        wall_upper = wall_error + wall_floor + wall_stability
        wall_pass = wall_upper <= wall_threshold_K
        return {
            "Q_raw_abs_error_W": q_error,
            "U_Q_CANONICAL_W": uq,
            "Q_solver_precision_floor_W": q_floor,
            "Q_reference_aware_abs_error_W": q_error + uq,
            "Q_error_upper_with_solver_and_reference_floors": q_upper,
            "Q_reference_lower_magnitude_W": denominator_lower,
            "Q_error_observed": q_observed,
            "Q_threshold_same_class": q_threshold,
            "Q_pass": q_pass,
            "wall_extrema_error_upper_K": wall_upper,
            "wall_extrema_threshold_K": wall_threshold_K,
            "wall_pass": wall_pass,
            "all_oracle_error_classes_pass": q_pass and wall_pass,
            "U_Q_is_formal_error_bound": False,
        }

    r95.oracle_error_class_pass = oracle_error_class_pass


def sequence_diagnostics(fixtures: list[dict[str, Any]], r95: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for fixture in fixtures:
        fixture_id = str(fixture["fixture_id"])
        ref = cast(dict[str, Any], fixture["continuous_reference"])
        per_sequence: dict[str, Any] = {}
        for sequence_id in ("PRIMARY", "SECONDARY_ALIGNMENT"):
            levels = cast(list[dict[str, Any]], fixture["mesh_sequences"][sequence_id])
            rows: list[dict[str, Any]] = []
            previous_q_error: float | None = None
            previous_dq: float | None = None
            error_reversals: list[int] = []
            increment_reversals: list[int] = []
            for index, level in enumerate(levels):
                q = float(level["Q_support_signed_hot_to_cold_W"])
                q_error = abs(q - float(ref["Q_ref_W"]))
                wall = cast(dict[str, float], level["wall_extrema_K"])
                wall_error = {
                    key: abs(float(wall[key]) - float(ref["wall_extrema_reference_K"][key]))
                    for key in ("Twi_min", "Twi_max", "Two_min", "Two_max")
                }
                dq: float | None = None
                if index:
                    dq = float(
                        cast(dict[str, Any], level["refinement_indicators"])["Q_abs_difference_W"]
                    )
                    if previous_dq is not None and dq >= previous_dq:
                        increment_reversals.append(int(level["cell_count"]))
                if previous_q_error is not None and q_error > previous_q_error:
                    error_reversals.append(int(level["cell_count"]))
                rows.append(
                    {
                        "mesh_id": level["mesh_id"],
                        "mesh_hash": level["mesh_hash"],
                        "mesh_size": f"1/{int(level['cell_count'])}",
                        "cell_count": int(level["cell_count"]),
                        "accepted_local_cell_count": len(level["cell_results"]),
                        "all_local_solves_accepted": bool(level["all_local_R94_solves_accepted"]),
                        "Q_mesh_W": q,
                        "Q_ref_canonical_W": float(ref["Q_ref_W"]),
                        "U_Q_canonical_W": float(ref["U_Q_CANONICAL_W"]),
                        "raw_abs_error_W": q_error,
                        "reference_aware_abs_error_plus_UQ_W": q_error
                        + float(ref["U_Q_CANONICAL_W"]),
                        "reference_aware_relative_error": (
                            None
                            if fixture_id == "M05"
                            else (q_error + float(ref["U_Q_CANONICAL_W"]))
                            / (abs(float(ref["Q_ref_W"])) - float(ref["U_Q_CANONICAL_W"]))
                        ),
                        "delta_Q_from_previous_W": dq,
                        "wall_extrema_K": wall,
                        "wall_extrema_raw_errors_K": wall_error,
                        "max_wall_extrema_raw_error_K": max(wall_error.values()),
                        "nfev_max": int(level["maximum_nfev"]),
                        "runtime_seconds": float(level["runtime_seconds"]),
                        "status": "PASS_LOCAL_CELLS",
                        "refinement_indicators": level["refinement_indicators"],
                    }
                )
                previous_q_error = q_error
                previous_dq = dq
            per_sequence[sequence_id] = {
                "levels": rows,
                "observed_reference_error_reversals_at_cell_counts": error_reversals,
                "observed_successive_delta_non_decreases_at_cell_counts": increment_reversals,
                "nonmonotonic_behavior_observed": bool(error_reversals or increment_reversals),
                "frozen_acceptance_rule_requires_monotonicity": False,
            }
        result[fixture_id] = per_sequence
    return result


def threshold_monotonicity_audit(threshold_audit: dict[str, Any]) -> dict[str, Any]:
    matrix = cast(list[dict[str, Any]], threshold_audit["threshold_matrix"])
    feasible = [
        bool(row["all_training_groups_converged_with_two_pairs_and_headroom"])
        and any(
            bool(cap["supports_all_training_with_headroom"])
            for cap in row["resource_cap_sensitivity"]
        )
        for row in matrix
    ]
    violations: list[dict[str, int]] = []
    for strict_index, strict in enumerate(matrix):
        if not feasible[strict_index]:
            continue
        for loose_index, loose in enumerate(matrix):
            is_componentwise_looser = (
                float(loose["duty_relative_threshold"]) >= float(strict["duty_relative_threshold"])
                and float(loose["near_zero_duty_absolute_threshold_W"])
                >= float(strict["near_zero_duty_absolute_threshold_W"])
                and float(loose["wall_extrema_absolute_threshold_K"])
                >= float(strict["wall_extrema_absolute_threshold_K"])
            )
            if is_componentwise_looser and not feasible[loose_index]:
                violations.append(
                    {
                        "strict_feasible_tuple_index": strict_index,
                        "componentwise_looser_tuple_index": loose_index,
                    }
                )
    return {
        "feasible_tuple_count": sum(feasible),
        "componentwise_looser_tuple_never_loses_feasibility": not violations,
        "monotonicity_violations": violations,
        "qualification_effect": "FAIL_CLOSED" if violations else "DIAGNOSTIC_PASS",
    }


def selected_sequence_comparisons(
    fixtures: list[dict[str, Any]], threshold_audit: dict[str, Any]
) -> dict[str, Any]:
    selected = threshold_audit.get("selected_threshold_tuple")
    if not isinstance(selected, dict):
        return {"selected_threshold_tuple_available": False, "fixtures": {}}
    grouped = {
        (str(row["fixture_id"]), str(row["sequence_id"])): row
        for row in cast(list[dict[str, Any]], selected["groups"])
    }
    output: dict[str, Any] = {}
    for fixture in fixtures:
        fixture_id = str(fixture["fixture_id"])
        seq_rows: dict[str, Any] = {}
        selected_levels: dict[str, dict[str, Any]] = {}
        for sequence_id in ("PRIMARY", "SECONDARY_ALIGNMENT"):
            group = grouped[(fixture_id, sequence_id)]
            conv = group.get("first_convergence")
            seq_rows[sequence_id] = {
                "pass": bool(group["converged"]),
                "first_convergence": conv,
            }
            if isinstance(conv, dict):
                count = int(conv["first_declared_converged_cell_count"])
                selected_levels[sequence_id] = next(
                    row
                    for row in cast(list[dict[str, Any]], fixture["mesh_sequences"][sequence_id])
                    if int(row["cell_count"]) == count
                )
        disagreement: dict[str, Any] | None = None
        if len(selected_levels) == 2:
            primary = selected_levels["PRIMARY"]
            secondary = selected_levels["SECONDARY_ALIGNMENT"]
            p_wall = cast(dict[str, float], primary["wall_extrema_K"])
            s_wall = cast(dict[str, float], secondary["wall_extrema_K"])
            disagreement = {
                "selected_threshold_classification_disagreement": (
                    bool(seq_rows["PRIMARY"]["pass"])
                    != bool(seq_rows["SECONDARY_ALIGNMENT"]["pass"])
                ),
                "selected_Q_abs_disagreement_W": abs(
                    float(primary["Q_support_signed_hot_to_cold_W"])
                    - float(secondary["Q_support_signed_hot_to_cold_W"])
                ),
                "selected_wall_extrema_max_abs_disagreement_K": max(
                    abs(float(p_wall[key]) - float(s_wall[key]))
                    for key in ("Twi_min", "Twi_max", "Two_min", "Two_max")
                ),
                "selected_mesh_ids": {
                    "PRIMARY": primary["mesh_id"],
                    "SECONDARY_ALIGNMENT": secondary["mesh_id"],
                },
            }
        output[fixture_id] = {"sequences": seq_rows, "between_sequence_disagreement": disagreement}
    return {
        "selected_threshold_tuple": {
            key: selected[key]
            for key in (
                "duty_relative_threshold",
                "near_zero_duty_absolute_threshold_W",
                "wall_extrema_absolute_threshold_K",
            )
        },
        "selected_threshold_tuple_available": True,
        "fixtures": output,
    }


def runtime_metadata(r98: Any) -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "numpy": str(r98.np.__version__),
        "scipy": str(r98.scipy.__version__),
        "coolprop": str(r98.CoolProp.__version__),
        "platform": platform.platform(),
    }


def run_worker(runtime_key: str, output: Path) -> dict[str, Any]:
    upstream = verify_predecessor_and_history()
    r99 = load_module(R99_RUNNER, f"task172_r99_mesh_final_{runtime_key}")
    r95, r98, r94 = r99.load_frozen_modules()
    input_matrix = r95.fixture_input_matrix()
    input_hash = canonical_sha256(input_matrix)
    require(input_hash == R95_INPUT_HASH, "R95 frozen input matrix changed")
    require(
        tuple(input_matrix["mesh_sequences"]["primary_nested_equal_bisection"])
        == tuple(r99.PRIMARY_SEQUENCE)
        and tuple(input_matrix["mesh_sequences"]["secondary_phase_alignment"])
        == tuple(r99.SECONDARY_SEQUENCE)
        and tuple(input_matrix["comparison"]["threshold_grid"]["duty_relative"])
        == tuple(r99.THRESHOLD_GRID)
        and tuple(input_matrix["mesh_sequences"]["threshold_sensitivity_candidate_caps_cells"])
        == tuple(r99.RESOURCE_CAP_GRID),
        "frozen mesh sequences/threshold/resource grid changed",
    )
    require(
        canonical_sha256(r98.EXPECTED_PROFILE) == r99.R98_PROFILE_HASH, "R98 profile hash mismatch"
    )
    require(
        r98.EXPECTED_PROFILE == r99.EXPECTED_PROFILE and r98.EXPECTED_PROFILE["c_round"] == 1.0,
        "R98 C_round overlay mismatch",
    )

    r102_results = read_json(R102_RESULTS)
    worker = cast(dict[str, Any], r102_results["workers"][runtime_key]["worker_result"])
    require(
        worker["canonical_producer"] == R102_PRODUCER and worker["all_six_fixtures_pass"] is True,
        "R102 runtime authority mismatch",
    )
    r102_rows = {
        str(row["fixture_id"]): row for row in cast(list[dict[str, Any]], worker["fixtures"])
    }
    require(
        set(r102_rows) == {"M01", "M02", "M03", "M04", "M05", "M06"}, "R102 fixture list incomplete"
    )
    require(
        all(bool(row["precision_pass"]) for row in r102_rows.values()),
        f"R102 precision review failed in {runtime_key}",
    )

    domain_audits = pointwise_domain_audits(r95, r99)
    r95.state_domain_audit = lambda fixture_id: domain_audits[str(fixture_id)]
    profile = dict(r98.EXPECTED_PROFILE)
    call_count = 0
    progress_base = 0
    started = time.monotonic()

    def solve_local(r94_module: Any, case: Any) -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        solved = r98.solve_frozen_profile(r94_module, case, profile)
        if not bool(solved.get("accepted")):
            error = (
                "MESH_RESOURCE_EXHAUSTED"
                if solved.get("resource_cap_hit")
                else "MESH_NOT_CONVERGED"
            )
            raise r95.MeshFailure(
                error, f"R98 reviewed local solve rejected {case.case_id}", diagnostics=solved
            )
        completed_in_pass = call_count - progress_base
        if completed_in_pass and completed_in_pass % 400 == 0:
            print(
                f"{runtime_key}: accepted {completed_in_pass} of 2664 mesh-cell solves",
                flush=True,
            )
        return cast(dict[str, Any], solved)

    r95.solve_local = solve_local
    r95.continuous_reference = make_reference_provider(r95, r102_rows)
    attach_r102_reference_uncertainty(r95, [])
    install_r102_acceptance_rule(r95)
    original_level_result = r95.mesh_level_result

    def measured_level_result(*args: Any, **kwargs: Any) -> dict[str, Any]:
        level_started = time.monotonic()
        level = cast(dict[str, Any], original_level_result(*args, **kwargs))
        level["runtime_seconds"] = time.monotonic() - level_started
        return level

    r95.mesh_level_result = measured_level_result
    print(f"{runtime_key}: begin full six-fixture dual-sequence matrix", flush=True)
    fixtures = cast(list[dict[str, Any]], r95.run_mesh_matrix(r94, include_oracles=True))
    require(
        call_count == 6 * (sum(r99.PRIMARY_SEQUENCE) + sum(r99.SECONDARY_SEQUENCE)),
        "incomplete mesh-cell solve count",
    )
    matrix_audit = r99.verify_matrix_structure(fixtures, r95)
    require(matrix_audit["all_local_solves_accepted"], "one or more mesh-cell solves rejected")
    for fixture in fixtures:
        reference = cast(dict[str, Any], fixture["continuous_reference"])
        require(reference["Q_ref_producer"] == R102_PRODUCER, "noncanonical reference used")
        require(
            reference["uncertainty_classification"] == EXPECTED_UQ_CLASS, "R102 U_Q class changed"
        )
        require(reference["formal_true_error_bound"] is False, "R102 U_Q overstated")
        require(reference["wall_extrema_reference_stable"], "continuous wall reference not stable")

    # Use the frozen R95 three-axis threshold grid, two consecutive passing
    # refinement pairs, same-class continuous-oracle agreement, and one later
    # headroom level. Only the R95 oracle uncertainty term is replaced by the
    # reviewed R102 U_Q envelope; the physical and mesh rules are unchanged.
    threshold_audit = r95.threshold_sensitivity(fixtures)
    threshold_behavior = threshold_monotonicity_audit(threshold_audit)
    failures = r95.mesh_failure_fixtures()
    require(
        bool(failures["all_expected_typed_outcomes_observed"]), "frozen failure taxonomy failed"
    )
    selected = threshold_audit.get("selected_threshold_tuple")
    selected_cap = threshold_audit.get("selected_resource_cap_cells")
    selected_groups = (
        cast(list[dict[str, Any]], selected["groups"]) if isinstance(selected, dict) else []
    )
    all_groups = len(selected_groups) == 12 and all(
        bool(group["converged"]) for group in selected_groups
    )
    threshold_complete = (
        threshold_audit["candidate_grid"]["candidate_tuple_count"] == 64
        and len(threshold_audit["threshold_matrix"]) == 64
    )
    projection = r95.numeric_mesh_projection(fixtures)
    projection_bytes = canonical_json_bytes({"mesh_result_matrix": projection})
    projection_hash = canonical_sha256({"mesh_result_matrix": projection})

    print(f"{runtime_key}: full matrix complete; replaying mesh numerical path", flush=True)
    first_matrix_solve_count = call_count
    progress_base = call_count
    replay = cast(list[dict[str, Any]], r95.run_mesh_matrix(r94, include_oracles=False))
    replay_solve_count = call_count - progress_base
    replay_projection = r95.numeric_mesh_projection(replay)
    replay_bytes = canonical_json_bytes({"mesh_result_matrix": replay_projection})
    replay_hash = canonical_sha256({"mesh_result_matrix": replay_projection})
    same_bytes = projection_bytes == replay_bytes
    same_hash = projection_hash == replay_hash

    # Enrich each emitted mesh record with an explicit elapsed-time field while
    # retaining the frozen result rows unchanged for canonical projection.
    elapsed = time.monotonic() - started
    diagnostics = sequence_diagnostics(fixtures, r95)
    selection = selected_sequence_comparisons(fixtures, threshold_audit)
    elapsed = time.monotonic() - started
    output_payload: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_MESH_CONVERGENCE_QUALIFICATION_FINAL_R1",
        "worker_status": "COMPLETE_SINGLE_RUNTIME_MESH_MATRIX",
        "runtime_key": runtime_key,
        "authorized_predecessor_head": upstream["authorized_head"],
        "historical_precheck": upstream,
        "runtime": runtime_metadata(r98),
        "frozen_input_matrix_canonical_hash": input_hash,
        "frozen_fixture_ids": ["M01", "M02", "M03", "M04", "M05", "M06"],
        "frozen_primary_sequence": list(r99.PRIMARY_SEQUENCE),
        "frozen_secondary_sequence": list(r99.SECONDARY_SEQUENCE),
        "frozen_threshold_grid": list(r99.THRESHOLD_GRID),
        "frozen_resource_cap_grid_cells": list(r99.RESOURCE_CAP_GRID),
        "effective_R98_profile": profile,
        "effective_C_round": 1.0,
        "roundoff_formula": (
            "effective_bound_j = R94_candidate_bound_j * (C_round_effective / R94_C_ROUND); "
            "R94_C_ROUND=0.5, C_round_effective=1.0"
        ),
        "reference_authority": {
            "producer": R102_PRODUCER,
            "uncertainty_classification": EXPECTED_UQ_CLASS,
            "formal_true_error_bound": False,
            "proven_global_upper_bound": False,
            "conservative_wording_accepted": False,
            "uncertainty_propagation_required": True,
            "all_six_runtime_rows_pass_R102": True,
        },
        "mesh_matrix_structure": matrix_audit,
        "full_mesh_matrix_rerun": True,
        "mesh_threshold_sensitivity_performed": threshold_complete,
        "runtime_seconds_including_replay": elapsed,
        "fixtures": fixtures,
        "sequence_diagnostics": diagnostics,
        "threshold_sensitivity": threshold_audit,
        "threshold_behavior_audit": threshold_behavior,
        "selected_sequence_results_and_cross_sequence_disagreement": selection,
        "failure_fixture_audit": failures,
        "deterministic_replay": {
            "repeated_mesh_projection_canonical_hash": replay_hash,
            "first_mesh_projection_canonical_hash": projection_hash,
            "same_input_same_mesh_result_bytes": same_bytes,
            "same_input_same_mesh_result_hash": same_hash,
            "repeat_scope": (
                "all 2664 accepted local cell solves across all fixture/sequence/mesh levels; "
                "continuous wall-reference calculation is not repeated"
            ),
            "first_matrix_cell_count": first_matrix_solve_count,
            "repeat_matrix_cell_count": replay_solve_count,
            "replay_matrix_cell_count": 6
            * (sum(r99.PRIMARY_SEQUENCE) + sum(r99.SECONDARY_SEQUENCE)),
        },
        "qualification_prerequisites": {
            "all_mesh_cell_solves_accepted": bool(matrix_audit["all_local_solves_accepted"]),
            "threshold_matrix_complete": threshold_complete,
            "all_selected_threshold_groups_converged": all_groups,
            "selected_threshold_tuple": selected,
            "selected_resource_cap_cells": selected_cap,
            "same_runtime_deterministic_replay_pass": same_bytes and same_hash,
        },
        "governance": {
            "mesh_study_performed": True,
            "mesh_threshold_sensitivity_performed": threshold_complete,
            "full_mesh_matrix_rerun": True,
            "mesh_policy_retuned": False,
            "precision_policy_retuned": False,
            "reference_oracle_redefined": False,
            "production_code_changed": False,
            "task172_implementation_started": False,
            "task173_solve_performed": False,
            "task174_solve_performed": False,
            "ready_authorized": False,
            "merge_authorized": False,
            "no_step_implies_the_next": True,
        },
    }
    output_payload["canonical_hash"] = canonical_sha256(output_payload)
    write_json(output, output_payload)
    print(
        json.dumps(
            {
                "runtime": runtime_key,
                "mesh_cell_solves": first_matrix_solve_count,
                "threshold_tuples": len(threshold_audit["threshold_matrix"]),
                "threshold_monotonicity_pass": threshold_behavior[
                    "componentwise_looser_tuple_never_loses_feasibility"
                ],
                "selected_threshold": (
                    None
                    if not isinstance(selected, dict)
                    else {
                        "duty": selected["duty_relative_threshold"],
                        "near_zero_W": selected["near_zero_duty_absolute_threshold_W"],
                        "wall_K": selected["wall_extrema_absolute_threshold_K"],
                    }
                ),
                "same_runtime_replay": same_bytes and same_hash,
                "output": str(output),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return output_payload


def compare_workers(py311: dict[str, Any], py312: dict[str, Any]) -> dict[str, Any]:
    grid311 = py311["threshold_sensitivity"]["threshold_matrix"]
    grid312 = py312["threshold_sensitivity"]["threshold_matrix"]
    require(len(grid311) == len(grid312) == 64, "cross-runtime threshold grid incomplete")

    def classification(row: dict[str, Any]) -> tuple[bool, tuple[bool, ...]]:
        return (
            bool(row["all_training_groups_converged_with_two_pairs_and_headroom"]),
            tuple(bool(group["converged"]) for group in row["groups"]),
        )

    equal = all(
        classification(left) == classification(right)
        for left, right in zip(grid311, grid312, strict=True)
    )
    selected311 = py311["qualification_prerequisites"]["selected_threshold_tuple"]
    selected312 = py312["qualification_prerequisites"]["selected_threshold_tuple"]
    selected_equal = (
        selected311 is None
        and selected312 is None
        or isinstance(selected311, dict)
        and isinstance(selected312, dict)
        and all(
            selected311[key] == selected312[key]
            for key in (
                "duty_relative_threshold",
                "near_zero_duty_absolute_threshold_W",
                "wall_extrema_absolute_threshold_K",
            )
        )
        and py311["qualification_prerequisites"]["selected_resource_cap_cells"]
        == py312["qualification_prerequisites"]["selected_resource_cap_cells"]
    )
    return {
        "threshold_classification_equal_across_runtimes": equal,
        "selected_threshold_and_cap_equal_across_runtimes": selected_equal,
        "python311_all_selected_groups_pass": py311["qualification_prerequisites"][
            "all_selected_threshold_groups_converged"
        ],
        "python312_all_selected_groups_pass": py312["qualification_prerequisites"][
            "all_selected_threshold_groups_converged"
        ],
        "same_input_replay_pass_python311": py311["deterministic_replay"][
            "same_input_same_mesh_result_bytes"
        ]
        and py311["deterministic_replay"]["same_input_same_mesh_result_hash"],
        "same_input_replay_pass_python312": py312["deterministic_replay"][
            "same_input_same_mesh_result_bytes"
        ]
        and py312["deterministic_replay"]["same_input_same_mesh_result_hash"],
        "classification_pass": equal and selected_equal,
    }


def selected_sequence_crosschecks_pass(worker: dict[str, Any]) -> bool:
    fixtures = worker["selected_sequence_results_and_cross_sequence_disagreement"]["fixtures"]
    if set(fixtures) != {"M01", "M02", "M03", "M04", "M05", "M06"}:
        return False
    for fixture in fixtures.values():
        sequences = fixture["sequences"]
        disagreement = fixture["between_sequence_disagreement"]
        if set(sequences) != {"PRIMARY", "SECONDARY_ALIGNMENT"}:
            return False
        if not all(bool(row["pass"]) for row in sequences.values()):
            return False
        if disagreement["selected_threshold_classification_disagreement"]:
            return False
        if not math.isfinite(float(disagreement["selected_Q_abs_disagreement_W"])):
            return False
        if not math.isfinite(float(disagreement["selected_wall_extrema_max_abs_disagreement_K"])):
            return False
    return True


def combine_workers(py311_path: Path, py312_path: Path, output: Path) -> dict[str, Any]:
    py311 = read_json(py311_path)
    py312 = read_json(py312_path)
    for worker, key, minor in ((py311, "python311", "3.11."), (py312, "python312", "3.12.")):
        saved_hash = worker.get("canonical_hash")
        require(
            bool(saved_hash) and canonical_sha256(worker) == saved_hash,
            f"{key} worker canonical hash mismatch",
        )
        require(
            worker["runtime_key"] == key and worker["runtime"]["python"].startswith(minor),
            f"{key} runtime mismatch",
        )
        require(
            worker["authorized_predecessor_head"] == AUTHORIZED_HEAD, f"{key} predecessor mismatch"
        )
    comparison = compare_workers(py311, py312)
    selected311 = py311["qualification_prerequisites"]["selected_threshold_tuple"]
    threshold_complete = all(
        worker["mesh_threshold_sensitivity_performed"]
        and len(worker["threshold_sensitivity"]["threshold_matrix"]) == 64
        for worker in (py311, py312)
    )
    threshold_monotonic = all(
        worker["threshold_behavior_audit"]["componentwise_looser_tuple_never_loses_feasibility"]
        for worker in (py311, py312)
    )
    selected_all_pass = all(
        worker["qualification_prerequisites"]["all_selected_threshold_groups_converged"]
        for worker in (py311, py312)
    )
    independent_sequences_pass = all(
        selected_sequence_crosschecks_pass(worker) for worker in (py311, py312)
    )
    refs_pass = all(
        worker["reference_authority"]["all_six_runtime_rows_pass_R102"]
        and worker["reference_authority"]["uncertainty_propagation_required"]
        for worker in (py311, py312)
    )
    deterministic = all(
        worker["deterministic_replay"]["same_input_same_mesh_result_bytes"]
        and worker["deterministic_replay"]["same_input_same_mesh_result_hash"]
        for worker in (py311, py312)
    )
    complete = all(
        worker["full_mesh_matrix_rerun"]
        and worker["mesh_matrix_structure"]["all_local_solves_accepted"]
        and worker["mesh_matrix_structure"]["fixture_count"] == 6
        and worker["mesh_threshold_sensitivity_performed"]
        for worker in (py311, py312)
    )
    selection_contract_pass = all(
        worker["threshold_sensitivity"]["selection_status"] == "PASS_UNIQUE_LOOSEST_FEASIBLE_TUPLE"
        and worker["threshold_sensitivity"]["componentwise_maximal_feasible_tuple_count"] == 1
        and worker["qualification_prerequisites"]["selected_resource_cap_cells"]
        in worker["frozen_resource_cap_grid_cells"]
        for worker in (py311, py312)
    )
    selected_available = isinstance(selected311, dict) and selection_contract_pass
    pass_result = (
        complete
        and refs_pass
        and selected_all_pass
        and independent_sequences_pass
        and deterministic
        and comparison["classification_pass"]
        and selected_available
        and threshold_monotonic
    )
    failure_reasons: list[str] = []
    if not complete:
        failure_reasons.append("FULL_MESH_OR_THRESHOLD_MATRIX_INCOMPLETE")
    if not refs_pass:
        failure_reasons.append("R102_REFERENCE_OR_UNCERTAINTY_REPLAY_FAILED")
    if not selected_all_pass:
        failure_reasons.append("NO_UNIQUE_FEASIBLE_THRESHOLD_OR_SOME_FIXTURE_SEQUENCE_FAILED")
    if not independent_sequences_pass:
        failure_reasons.append("PRIMARY_SECONDARY_SEQUENCE_CROSSCHECK_FAILED")
    if not deterministic:
        failure_reasons.append("DETERMINISTIC_REPLAY_FAILED")
    if not comparison["classification_pass"]:
        failure_reasons.append("CROSS_RUNTIME_CLASSIFICATION_DISAGREEMENT")
    if not selected_available:
        failure_reasons.append("NO_UNIQUE_LOOSEST_THRESHOLD_OR_VALID_RESOURCE_CAP")
    if not threshold_monotonic:
        failure_reasons.append("THRESHOLD_SENSITIVITY_NONMONOTONIC_FEASIBILITY")
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_MESH_CONVERGENCE_QUALIFICATION_FINAL_R1",
        "authorized_predecessor_head": AUTHORIZED_HEAD,
        "result": "PASS_MESH_CONVERGENCE_QUALIFICATION"
        if pass_result
        else "BLOCKED_MESH_CONVERGENCE_QUALIFICATION",
        "runtime_comparison": comparison,
        "full_mesh_matrix_rerun": complete,
        "threshold_sensitivity_performed": threshold_complete,
        "threshold_monotonicity_pass": threshold_monotonic,
        "all_selected_sequence_crosschecks_pass": independent_sequences_pass,
        "unique_loosest_threshold_and_resource_cap_selection_pass": selection_contract_pass,
        "R99_historical_result_preserved": True,
        "R99_historical_blocker_reproduced": True,
        "R99_M05_historical_64_ULP_gate": "STILL_FAILS",
        "R102_SciPy_canonical_reference_authority_replayed": refs_pass,
        "selected_threshold_tuple": selected311 if isinstance(selected311, dict) else None,
        "selected_resource_cap_cells": (
            selected311.get("selected_minimum_resource_cap_cells")
            if isinstance(selected311, dict)
            else None
        ),
        "workers": {"python311": py311, "python312": py312},
        "blocking_predicates": failure_reasons,
        "blocker_ledger": {
            "mesh_convergence_canonical_blocker_removed": pass_result,
            "remaining": [] if pass_result else ["MESH-CONVERGENCE-QUALIFICATION"],
            "effective_remaining_task172_entry_blocker_count": 0 if pass_result else 1,
            "task172_entry_authority_complete": pass_result,
            "next_gate": "AUTHORIZE_TASK172_IMPLEMENTATION_START_ONLY"
            if pass_result
            else "AUTHORIZE_MINIMAL_MESH_QUALIFICATION_REMEDIATION_ONLY",
        },
        "governance": {
            "mesh_study_performed": True,
            "mesh_threshold_sensitivity_performed": True,
            "full_mesh_matrix_rerun": True,
            "mesh_policy_retuned": False,
            "precision_policy_retuned": False,
            "reference_oracle_redefined": False,
            "production_code_changed": False,
            "task172_implementation_started": False,
            "task173_solve_performed": False,
            "task174_solve_performed": False,
            "ready_authorized": False,
            "merge_authorized": False,
            "no_step_implies_the_next": True,
            "stop": True,
        },
    }
    report["canonical_hash"] = canonical_sha256(report)
    write_json(output, report)
    print(
        json.dumps(
            {
                "result": report["result"],
                "selected_threshold_tuple": (
                    None
                    if not isinstance(selected311, dict)
                    else {
                        "duty": selected311["duty_relative_threshold"],
                        "near_zero_W": selected311["near_zero_duty_absolute_threshold_W"],
                        "wall_K": selected311["wall_extrema_absolute_threshold_K"],
                    }
                ),
                "blockers": failure_reasons,
                "output": str(output),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--worker", action="store_true")
    modes.add_argument("--combine", action="store_true")
    parser.add_argument("--runtime", choices=("python311", "python312"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--py311", type=Path)
    parser.add_argument("--py312", type=Path)
    args = parser.parse_args()
    if args.worker:
        require(args.runtime is not None, "--worker requires --runtime")
        run_worker(args.runtime, args.output)
    else:
        require(
            args.py311 is not None and args.py312 is not None,
            "--combine requires both runtime workers",
        )
        combine_workers(args.py311, args.py312, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
