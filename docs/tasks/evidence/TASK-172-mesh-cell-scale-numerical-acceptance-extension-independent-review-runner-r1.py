"""Independent R98 replay of the frozen R96A numerical holdout.

This evidence-only runner reads immutable TASK172 artifacts, replays the R96/R97
hash and independence records, and executes only the frozen 30-case, one-support
holdout. It never runs R95, selects a profile, changes solver controls, performs
mesh refinement, or writes anywhere except the explicit output path.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import math
import platform
import subprocess
import sys
import unicodedata
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import CoolProp
import numpy as np
import rfc8785
import scipy
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "docs/tasks/TASK-172-v0.7-authority-registry-r1.json"
R94_HOLDOUT_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-quantitative-numerical-profile-independent-review-holdout-r1.json"
)
R94_RUNNER_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-quantitative-numerical-profile-independent-review-runner-r1.py"
)
R95_DOCUMENT_PATH = ROOT / "docs/tasks/TASK-172-v0.7-mesh-convergence-qualification-r1.md"
R95_EVIDENCE_PATH = ROOT / ("docs/tasks/evidence/TASK-172-mesh-convergence-qualification-r1.json")
R95_RUNNER_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-runner-r1.py"
)
R95_RESULTS_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-results-r1.json"
)
R96_DOCUMENT_PATH = ROOT / (
    "docs/tasks/TASK-172-v0.7-mesh-cell-scale-numerical-acceptance-extension-r1.md"
)
R96_EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-cell-scale-numerical-acceptance-extension-r1.json"
)
R96_RUNNER_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-cell-scale-numerical-acceptance-runner-r1.py"
)
R96_RESULTS_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-cell-scale-numerical-acceptance-results-r1.json"
)
R96_ORIGINAL_HOLDOUT_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-cell-scale-numerical-acceptance-holdout-input-r1.json"
)
R96A_DOCUMENT_PATH = ROOT / (
    "docs/tasks/TASK-172-v0.7-mesh-cell-scale-holdout-independence-correction-r96a.md"
)
R96A_EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-cell-scale-holdout-independence-correction-r96a.json"
)
R96A_HOLDOUT_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-cell-scale-numerical-acceptance-holdout-input-r96a.json"
)

EXPECTED_PREDECESSOR_HEAD = "1d98b6a990d564f546214fd2f5801b91990dd955"
EXPECTED_REGISTRY_ROOT_HASH = "774497dbe02a6228f306e3615a36bc3bddc1340cbd4c996dfa5f8b8c30b227f6"
EXPECTED_R96_RESULTS_HASH = "091ba119c4f1fd99d12b2484bd295aff7640ce8ab5432cc4fe54e0e805a16cc9"
EXPECTED_R96_P1_MATRIX_HASH = "f8cdc67fd28aac5baf85ca21a3b4eb1edc02401aef522eebcf66b9c53faa00d1"
EXPECTED_R96A_HOLDOUT_HASH = "5efc368eedee738d507fbf15bf592539d4c68b8017b4d254b6cc4c27ccfbd3e0"
EXPECTED_R96A_BASE_MATRIX_HASH = "8bfa38ae0c28a047000782b2dc484ddf62797ccbf6d55faa1034f8ddc2fa06d0"
EXPECTED_R97_DUPLICATE_AUDIT_HASH = (
    "a8a18e1003f4ed09ed198a5a0bee90247408d07e9d1e6215aec80679109c697a"
)
EXPECTED_PROFILE_HASH = "029b641b796c2feb699fb1fcc70386de716b7ac820684e507a3a6c0dc0b1eeb6"
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
EXPECTED_SCALES = ("1/3", "1/6", "1/12", "1/24", "1/48", "1/96")
REPRESENTATIVE_SCALAR_ORACLE_SCALES = ("1/3", "1/24", "1/96")
REFERENCE_AREA_I_M2 = 0.04
REFERENCE_AREA_O_M2 = 0.055
R94_BASE_C_ROUND = 0.5
PROPERTY_DOMAIN_K = (298.15, 300.0)


def clean_for_hash(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(key)): clean_for_hash(item)
            for key, item in value.items()
            if key not in {"canonical_hash", "mutable_review_comments"}
        }
    if isinstance(value, list):
        return [clean_for_hash(item) for item in value]
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    return value


def canonical_bytes(value: Any) -> bytes:
    return rfc8785.dumps(clean_for_hash(value))


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )
    path.write_text(f"{payload}\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_evidence_module(path: Path, module_name: str) -> Any:
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen evidence module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def get_assignment_literal(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and node.value is not None
        ):
            return ast.literal_eval(node.value)
    raise RuntimeError(f"frozen source assignment not found: {name}")


def check_extension_file(
    root: Path,
    extension: dict[str, Any],
    path_key: str,
    file_hash_key: str,
) -> str:
    relative = str(extension["artifacts"][path_key])
    expected = str(extension["artifacts"][file_hash_key])
    observed = file_sha256(root / relative)
    require(observed == expected, f"historical artifact hash mismatch: {relative}")
    return observed


def normalized_number(value: Any) -> Decimal:
    return Decimal(str(value))


def corrected_case_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    fractions = row["resistance_fractions"]
    case_class = str(row["case_class"])
    return (
        normalized_number(row["tube_bulk_K"]),
        normalized_number(row["shell_bulk_K"]),
        int(row["s_ts"]),
        normalized_number(row["pressure_Pa"]),
        normalized_number(row["reynolds"]),
        normalized_number(row["total_resistance_base_K_W"]),
        normalized_number(fractions["tube_film"]),
        normalized_number(fractions["wall"]),
        normalized_number(fractions["shell_film"]),
        True,
        case_class.startswith("DUAL_ACTIVE"),
    )


def r94_case_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    fractions = row["resistance_fractions"]
    case_type = str(row["type"])
    return (
        normalized_number(row["tube_bulk_K"]),
        normalized_number(row["shell_bulk_K"]),
        int(row["s_ts"]),
        normalized_number(row["pressure_Pa"]),
        normalized_number(row["reynolds"]),
        normalized_number(row["total_resistance_base_K_W"]),
        normalized_number(fractions["tube_film"]),
        normalized_number(fractions["wall"]),
        normalized_number(fractions["shell_film"]),
        True,
        case_type.startswith("DUAL_ACTIVE"),
    )


def r95_profile_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    tube_formula = str(row["tube_temperature_formula"])
    shell_formula = str(row["shell_temperature_formula"])
    for formula in (tube_formula, shell_formula):
        expression = ast.parse(formula, mode="eval")
        require(
            any(isinstance(node, ast.Name) and node.id == "x" for node in ast.walk(expression)),
            "R95 temperature profile unexpectedly lacks its support coordinate",
        )
    fractions = row["resistance_fractions"]
    return (
        ("SUPPORT_PROFILE", tube_formula),
        ("SUPPORT_PROFILE", shell_formula),
        int(row["s_ts"]),
        normalized_number(row["pressure_tube_formula_Pa"]),
        normalized_number(row["reynolds_tube"]),
        normalized_number(row["total_resistance_K_W"]),
        normalized_number(fractions["tube_film"]),
        normalized_number(fractions["wall"]),
        normalized_number(fractions["shell_film"]),
        bool(row["tube_c3_active"]),
        bool(row["shell_jmu_active"]),
    )


def verify_predecessor_head() -> str:
    observed = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(observed == EXPECTED_PREDECESSOR_HEAD, "authorized predecessor HEAD changed")
    return observed


def verify_duplicate_audit(
    registry: dict[str, Any],
    corrected_holdout: dict[str, Any],
    r96a_evidence: dict[str, Any],
    r94_holdout: dict[str, Any],
    r95_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    corrected_rows = cast(list[dict[str, Any]], corrected_holdout["future_cases"])
    original_holdout = read_json(R96_ORIGINAL_HOLDOUT_PATH)
    original_rows = cast(list[dict[str, Any]], original_holdout["future_cases"])
    h_rows = cast(list[dict[str, Any]], r94_holdout["holdout_matrix"]["fixtures"])
    prior_ids = [f"R94:{row['case_id']}" for row in h_rows]
    prior_ids.extend(f"R95:{row['fixture_id']}" for row in r95_rows)
    recorded_audit = cast(dict[str, Any], r96a_evidence["duplicate_audit"])
    require(prior_ids == recorded_audit["prior_case_ids"], "R97 prior-case ordering changed")

    def compare(row: dict[str, Any]) -> list[bool]:
        signature = corrected_case_signature(row)
        results = [signature == r94_case_signature(prior) for prior in h_rows]
        results.extend(signature == r95_profile_signature(prior) for prior in r95_rows)
        return results

    pairwise = [
        {"case_id": str(row["case_id"]), "exact_duplicate_by_prior_case": compare(row)}
        for row in corrected_rows
    ]
    recorded_pairwise = recorded_audit["corrected_pairwise_exact_duplicate_matrix"]
    require(pairwise == recorded_pairwise, "R97 pairwise duplicate matrix replay differs")
    corrected_duplicate_count = sum(any(item["exact_duplicate_by_prior_case"]) for item in pairwise)
    require(corrected_duplicate_count == 0, "corrected holdout contains a prior exact duplicate")

    original_duplicate_pairs: list[tuple[str, str]] = []
    for original in original_rows:
        signature = corrected_case_signature(original)
        for prior in h_rows:
            if signature == r94_case_signature(prior):
                original_duplicate_pairs.append((str(original["case_id"]), str(prior["case_id"])))
    require(
        original_duplicate_pairs == [("K04", "H05"), ("K05", "H04")],
        "R96 original holdout contamination replay differs",
    )

    require(
        len({corrected_case_signature(row) for row in corrected_rows}) == 5,
        "corrected K cases are not mutually distinct",
    )
    return {
        "prior_case_count": len(prior_ids),
        "pairwise_comparison_count": len(pairwise) * len(prior_ids),
        "corrected_exact_duplicate_count": corrected_duplicate_count,
        "corrected_pairwise_exact_duplicate_matrix": pairwise,
        "original_holdout_exact_duplicate_pairs": [
            {"holdout_case_id": left, "prior_case_id": right}
            for left, right in original_duplicate_pairs
        ],
        "all_r95_temperature_profiles_support_dependent": all(
            "x" in str(row["tube_temperature_formula"])
            and "x" in str(row["shell_temperature_formula"])
            for row in r95_rows
        ),
        "independence_replay_pass": True,
        "r97_recorded_duplicate_audit_canonical_hash": canonical_hash(recorded_audit),
        "r97_duplicate_audit_canonical_hash_match": (
            canonical_hash(recorded_audit) == EXPECTED_R97_DUPLICATE_AUDIT_HASH
        ),
    }


def verify_static_artifacts() -> tuple[dict[str, Any], Any, dict[str, Any]]:
    predecessor = verify_predecessor_head()
    registry_payload = subprocess.check_output(
        [
            "git",
            "show",
            f"{EXPECTED_PREDECESSOR_HEAD}:docs/tasks/TASK-172-v0.7-authority-registry-r1.json",
        ],
        cwd=ROOT,
        text=True,
    )
    registry = cast(dict[str, Any], json.loads(registry_payload))
    require(
        canonical_hash(registry) == EXPECTED_REGISTRY_ROOT_HASH,
        "predecessor registry root canonical hash mismatch",
    )
    require(
        registry["canonical_hash"] == EXPECTED_REGISTRY_ROOT_HASH,
        "registry top-level canonical hash field mismatch",
    )
    extension_keys = sorted(
        (key for key in registry if key.startswith("r") and key.endswith("_extension")),
        key=lambda key: int(key[1 : -len("_extension")]),
    )
    expected_extension_keys = [f"r{index}_extension" for index in range(2, 98)]
    require(
        extension_keys == expected_extension_keys,
        "historical registry extension layout differs from r2 through r97",
    )

    r94_ext = cast(dict[str, Any], registry["r94_extension"])
    r95_ext = cast(dict[str, Any], registry["r95_extension"])
    r96_ext = cast(dict[str, Any], registry["r96_extension"])
    r97_ext = cast(dict[str, Any], registry["r97_extension"])
    require(canonical_hash(r96_ext) == r96_ext["canonical_hash"], "R96 extension hash mismatch")
    require(canonical_hash(r97_ext) == r97_ext["canonical_hash"], "R97 extension hash mismatch")

    check_extension_file(ROOT, r94_ext, "holdout_path", "holdout_file_sha256")
    check_extension_file(ROOT, r94_ext, "runner_path", "runner_sha256")
    check_extension_file(ROOT, r94_ext, "evidence_path", "evidence_file_sha256")
    r94_holdout = read_json(R94_HOLDOUT_PATH)
    require(
        canonical_hash(r94_holdout) == r94_ext["artifacts"]["holdout_canonical_hash"],
        "R94 holdout canonical hash mismatch",
    )
    r94_evidence = read_json(ROOT / str(r94_ext["artifacts"]["evidence_path"]))
    require(
        canonical_hash(r94_evidence) == r94_ext["artifacts"]["evidence_canonical_hash"],
        "R94 evidence canonical hash mismatch",
    )

    for path_key, hash_key in (
        ("document_path", "document_sha256"),
        ("evidence_path", "evidence_file_sha256"),
        ("runner_path", "runner_sha256"),
        ("results_path", "results_file_sha256"),
    ):
        check_extension_file(ROOT, r95_ext, path_key, hash_key)
    r95_evidence = read_json(R95_EVIDENCE_PATH)
    r95_results = read_json(R95_RESULTS_PATH)
    require(
        canonical_hash(r95_evidence) == r95_ext["artifacts"]["evidence_canonical_hash"],
        "R95 evidence canonical hash mismatch",
    )
    require(
        canonical_hash(r95_results) == r95_ext["artifacts"]["results_canonical_hash"],
        "R95 result canonical hash mismatch",
    )
    require(
        r95_evidence["frozen_input_matrix"]["canonical_hash"]
        == "b13d4306f3a2a60f248fbd1b222a6069599ec08a3c094996b17019ac315ae2d8",
        "R95 frozen input matrix identity mismatch",
    )
    r95_rows = cast(list[dict[str, Any]], get_assignment_literal(R95_RUNNER_PATH, "FIXTURE_ROWS"))
    require(len(r95_rows) == 6, "R95 fixture source identity/count mismatch")

    for path_key, hash_key in (
        ("document_path", "document_sha256"),
        ("evidence_path", "evidence_file_sha256"),
        ("runner_path", "runner_sha256"),
        ("results_path", "results_file_sha256"),
        ("holdout_path", "holdout_file_sha256"),
    ):
        check_extension_file(ROOT, r96_ext, path_key, hash_key)
    r96_evidence = read_json(R96_EVIDENCE_PATH)
    r96_results = read_json(R96_RESULTS_PATH)
    require(
        canonical_hash(r96_evidence) == r96_ext["artifacts"]["evidence_canonical_hash"],
        "R96 evidence canonical hash mismatch",
    )
    require(
        canonical_hash(r96_results) == EXPECTED_R96_RESULTS_HASH,
        "R96 result canonical hash mismatch",
    )
    require(
        r96_ext["artifacts"]["results_canonical_hash"] == EXPECTED_R96_RESULTS_HASH,
        "R96 registry result canonical hash mismatch",
    )
    require(
        r96_results["canonical_hash"] == EXPECTED_R96_RESULTS_HASH,
        "R96 result embedded canonical hash mismatch",
    )

    for path_key, hash_key in (
        ("document_path", "document_sha256"),
        ("evidence_path", "evidence_file_sha256"),
        ("corrected_holdout_path", "corrected_holdout_file_sha256"),
    ):
        check_extension_file(ROOT, r97_ext, path_key, hash_key)
    r96a_evidence = read_json(R96A_EVIDENCE_PATH)
    corrected_holdout = read_json(R96A_HOLDOUT_PATH)
    require(
        canonical_hash(r96a_evidence) == r97_ext["artifacts"]["evidence_canonical_hash"],
        "R97 evidence canonical hash mismatch",
    )
    require(
        canonical_hash(corrected_holdout) == EXPECTED_R96A_HOLDOUT_HASH,
        "corrected R96A holdout canonical hash mismatch",
    )
    require(
        corrected_holdout["canonical_hash"] == EXPECTED_R96A_HOLDOUT_HASH,
        "corrected holdout embedded canonical hash mismatch",
    )
    require(
        r97_ext["artifacts"]["corrected_holdout_canonical_hash"] == EXPECTED_R96A_HOLDOUT_HASH,
        "R97 corrected holdout linkage mismatch",
    )
    require(
        canonical_hash(corrected_holdout["selected_candidate_profile"]) == EXPECTED_PROFILE_HASH,
        "selected P1 profile hash mismatch",
    )
    require(
        corrected_holdout["selected_candidate_profile"] == EXPECTED_PROFILE,
        "frozen P1 profile fields changed",
    )
    require(
        corrected_holdout["scale_fractions_exact"] == list(EXPECTED_SCALES),
        "frozen holdout fractions changed",
    )
    require(len(corrected_holdout["future_cases"]) == 5, "frozen K case count changed")
    require(
        corrected_holdout["expected_future_case_count"] == 30,
        "frozen holdout execution count changed",
    )
    corrected_rows = cast(list[dict[str, Any]], corrected_holdout["future_cases"])
    require(
        canonical_hash({"cases": corrected_rows})
        == EXPECTED_R96A_BASE_MATRIX_HASH
        == corrected_holdout["corrected_base_case_matrix_canonical_hash"],
        "corrected R96A base-case matrix hash mismatch",
    )
    expected_case_classes = {
        "K01": "DUAL_ACTIVE_TUBE_HOT",
        "K02": "DUAL_ACTIVE_SHELL_HOT",
        "K03": "DUAL_ACTIVE_NEAR_ZERO",
        "K04": "TUBE_C3_ONLY",
        "K05": "DUAL_ACTIVE_NEGATIVE_Q",
    }
    require(
        {str(row["case_id"]): str(row["case_class"]) for row in corrected_rows}
        == expected_case_classes,
        "corrected K case class matrix changed",
    )
    case_by_id = {str(row["case_id"]): row for row in corrected_rows}
    require(
        float(case_by_id["K03"]["tube_bulk_K"]) != float(case_by_id["K03"]["shell_bulk_K"]),
        "K03 must remain a genuine nonzero-driving-force case",
    )
    require(
        int(case_by_id["K05"]["s_ts"]) == 1
        and float(case_by_id["K05"]["tube_bulk_K"]) < float(case_by_id["K05"]["shell_bulk_K"]),
        "K05 signed negative-q identity changed",
    )

    policy_by_id = {
        str(row["candidate_id"]): row for row in r96_results["scale_training"]["candidate_policies"]
    }
    diagnostic = cast(dict[str, Any], r96_results["r95_known_failure_diagnostic"])
    diagnostic_by_id = {
        str(row["candidate_id"]): row for row in diagnostic["candidate_evaluations"]
    }
    expected_selection = {
        "R96_P0_SCALE_TRAINING_PASS": policy_by_id["P0_FROZEN_R94"]["summary"]["all_pass"],
        "R96_P0_KNOWN_R95_DIAGNOSTIC_PASS": diagnostic_by_id["P0_FROZEN_R94"]["accepted"],
        "R96_P1_SCALE_TRAINING_PASS": policy_by_id["P1_ACCEPTANCE_EXTENSION"]["summary"][
            "all_pass"
        ],
        "R96_P1_KNOWN_R95_DIAGNOSTIC_PASS": diagnostic_by_id["P1_ACCEPTANCE_EXTENSION"]["accepted"],
        "R96_P2_KNOWN_R95_DIAGNOSTIC_PASS": diagnostic_by_id["P2_TIGHTER_XTOL_1E13"]["accepted"],
        "R96_P3_KNOWN_R95_DIAGNOSTIC_PASS": diagnostic_by_id["P3_TIGHTER_XTOL_1E14"]["accepted"],
    }
    require(
        expected_selection
        == {
            "R96_P0_SCALE_TRAINING_PASS": True,
            "R96_P0_KNOWN_R95_DIAGNOSTIC_PASS": False,
            "R96_P1_SCALE_TRAINING_PASS": True,
            "R96_P1_KNOWN_R95_DIAGNOSTIC_PASS": True,
            "R96_P2_KNOWN_R95_DIAGNOSTIC_PASS": False,
            "R96_P3_KNOWN_R95_DIAGNOSTIC_PASS": False,
        },
        "independent P1 selection replay did not match frozen decision facts",
    )
    p1_rows = cast(list[dict[str, Any]], policy_by_id["P1_ACCEPTANCE_EXTENSION"]["rows"])
    p1_matrix_hash = canonical_hash({"rows": p1_rows})
    require(
        p1_matrix_hash == EXPECTED_R96_P1_MATRIX_HASH, "R96 P1 selected result-matrix hash mismatch"
    )
    require(
        len(p1_rows) == 72 and all(bool(row["accepted"]) for row in p1_rows),
        "R96 P1 dyadic training replay is incomplete or failed",
    )
    require(
        diagnostic["exact_p0_diagnostic_reproduced"],
        "R96 known R95 diagnostic did not record exact P0 replay",
    )

    r95_trial = cast(dict[str, Any], r95_evidence["first_blocking_local_trial"])
    p0_diagnostic = diagnostic_by_id["P0_FROZEN_R94"]
    require(
        p0_diagnostic["initial_seed"] == r95_trial["initial_seed"]
        and p0_diagnostic["solution"] == r95_trial["solution"]
        and p0_diagnostic["physical_residuals_W"] == r95_trial["physical_residuals_W"]
        and p0_diagnostic["candidate_c_bounds_W"] == r95_trial["candidate_roundoff_bounds_W"]
        and p0_diagnostic["nfev"] == r95_trial["nfev"]
        and p0_diagnostic["residual_callback_count"] == r95_trial["residual_callback_count"]
        and p0_diagnostic["solver_status"] == r95_trial["solver_status"],
        "R96 P0 known diagnostic no longer matches frozen R95 M01/N=8 row",
    )
    require(
        r95_trial["fixture_id"] == "M01"
        and int(r95_trial["cell_count"]) == 8
        and r95_trial["cell_interval_exact"] == ["1/4", "3/8"]
        and r95_trial["cell_fraction_exact"] == "1/8",
        "R95 diagnostic identity changed",
    )

    duplicate_replay = verify_duplicate_audit(
        registry, corrected_holdout, r96a_evidence, r94_holdout, r95_rows
    )
    require(
        duplicate_replay["r97_duplicate_audit_canonical_hash_match"],
        "R97 duplicate audit canonical hash mismatch",
    )

    r94_module = load_evidence_module(R94_RUNNER_PATH, "task172_r98_frozen_r94_kernel")
    require(float(r94_module.C_ROUND) == R94_BASE_C_ROUND, "R94 base residual policy changed")
    r94_profile = cast(dict[str, Any], r94_module.FROZEN_PROFILE)
    for key, value in r94_profile.items():
        if key == "c_round":
            continue
        require(EXPECTED_PROFILE[key] == value, f"P1 changed R94 solver control: {key}")

    static_replay = {
        "predecessor_head": predecessor,
        "registry_root_canonical_hash": canonical_hash(registry),
        "r94_holdout_hash_and_identity": True,
        "r95_artifact_and_known_diagnostic_identity": True,
        "r95_frozen_input_matrix_canonical_hash": r95_evidence["frozen_input_matrix"][
            "canonical_hash"
        ],
        "r96_results_canonical_hash": canonical_hash(r96_results),
        "r96_selected_result_matrix_canonical_hash": p1_matrix_hash,
        "r96_p1_selection_review_facts": expected_selection,
        "r96a_corrected_holdout_canonical_hash": canonical_hash(corrected_holdout),
        "r97_duplicate_audit_replay": duplicate_replay,
        "static_replay_pass": True,
    }
    return static_replay, r94_module, corrected_holdout


def scaled_case(r94: Any, base: Any, scale_text: str) -> Any:
    factor = float(Fraction(scale_text))
    return replace(
        base,
        case_id=f"{base.case_id}@{scale_text}",
        family="R98_NON_DYADIC_INDEPENDENT_HOLDOUT",
        area_i_m2=base.area_i_m2 * factor,
        area_o_m2=base.area_o_m2 * factor,
        wall_resistance_K_W=base.wall_resistance_K_W / factor,
    )


def finite_solution(solution: dict[str, Any]) -> bool:
    values = [solution.get(key) for key in ("q_hc_W", "T_wall_inner_K", "T_wall_outer_K")]
    return all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in values)


def scalar_oracle_record(r94: Any, case: Any) -> dict[str, Any]:
    try:
        oracle = cast(dict[str, Any], r94.scalar_oracle(case, grid_count=4097))
        finite = finite_solution(oracle)
        passed = bool(
            finite
            and oracle["brentq_converged"]
            and oracle["strict_sign_change"]
            and oracle["strict_monotonicity"] in {"INCREASING", "DECREASING"}
        )
        residuals = r94.physical_residual(
            case,
            np.asarray(
                [oracle["q_hc_W"], oracle["T_wall_inner_K"], oracle["T_wall_outer_K"]],
                dtype=float,
            ),
        )
        return {
            "case_id": str(case.case_id),
            "grid_count": 4097,
            "q_hc_W": float(oracle["q_hc_W"]),
            "T_wall_inner_K": float(oracle["T_wall_inner_K"]),
            "T_wall_outer_K": float(oracle["T_wall_outer_K"]),
            "bracket_K": [float(value) for value in oracle["bracket_K"]],
            "brentq_converged": bool(oracle["brentq_converged"]),
            "strict_sign_change": bool(oracle["strict_sign_change"]),
            "strict_monotonicity": str(oracle["strict_monotonicity"]),
            "physical_residuals_W": [float(value) for value in residuals],
            "finite": finite and all(math.isfinite(float(value)) for value in residuals),
            "oracle_pass": passed,
            "production_scalar_reduction_selected": False,
        }
    except (r94.ReviewFailure, ValueError, RuntimeError, FloatingPointError) as exc:
        return {
            "case_id": str(case.case_id),
            "grid_count": 4097,
            "finite": False,
            "oracle_pass": False,
            "failure_class": f"{type(exc).__name__}:{exc}",
            "production_scalar_reduction_selected": False,
        }


def solve_frozen_profile(r94: Any, case: Any, profile: dict[str, Any]) -> dict[str, Any]:
    seed = np.asarray(r94.direct_seed(case), dtype=float)
    q_scale = abs(float(seed[0]))
    delta_t = abs(float(case.delta_t_K))
    callback_cap = int(profile["residual_callback_cap"])
    max_nfev = int(profile["max_nfev"])
    callback_count = 0
    if q_scale == 0.0 or delta_t == 0.0:
        return {
            "case_id": str(case.case_id),
            "accepted": False,
            "failure_class": "ZERO_DUTY_OR_ZERO_DRIVING_FORCE_NOT_ADMISSIBLE_IN_HOLDOUT",
            "initial_seed": [float(value) for value in seed],
            "residual_callback_count": callback_count,
        }

    def residual(values: np.ndarray) -> np.ndarray:
        nonlocal callback_count
        callback_count += 1
        if callback_count > callback_cap:
            raise r94.ReviewFailure("SOLVER_RESOURCE_EXHAUSTION_CALLBACK_CAP")
        return np.asarray(r94.physical_residual(case, values), dtype=float) / q_scale

    lower = np.asarray([-np.inf, *([PROPERTY_DOMAIN_K[0]] * 2)], dtype=float)
    upper = np.asarray([np.inf, *([PROPERTY_DOMAIN_K[1]] * 2)], dtype=float)
    options: dict[str, Any] = {
        "method": str(profile["method"]),
        "loss": str(profile["loss"]),
        "ftol": float(profile["ftol"]),
        "xtol": float(profile["xtol"]),
        "gtol": float(profile["gtol"]),
        "jac": str(profile["jacobian"]),
        "diff_step": float(profile["diff_step"]),
        "x_scale": [q_scale, delta_t, delta_t],
        "max_nfev": max_nfev,
        "bounds": (lower, upper),
        "tr_solver": str(profile["tr_solver"]),
        "tr_options": dict(profile["tr_options"]),
        "f_scale": float(profile["f_scale"]),
        "jac_sparsity": profile["jac_sparsity"],
    }
    try:
        output = least_squares(residual, seed, **options)
        x = np.asarray(output.x, dtype=float)
        physical = np.asarray(r94.physical_residual(case, x), dtype=float)
        base_bounds, _ = r94.candidate_c_bounds(case, x)
        scale_multiplier = float(profile["c_round"]) / float(r94.C_ROUND)
        bounds = [float(value) * scale_multiplier for value in base_bounds]
        ratios = [
            abs(float(value)) / float(bound) if float(bound) > 0.0 else math.inf
            for value, bound in zip(physical, bounds, strict=True)
        ]
        domain_valid = bool(
            np.all(np.isfinite(x))
            and np.all(np.isfinite(physical))
            and PROPERTY_DOMAIN_K[0] <= float(x[1]) <= PROPERTY_DOMAIN_K[1]
            and PROPERTY_DOMAIN_K[0] <= float(x[2]) <= PROPERTY_DOMAIN_K[1]
        )
        if domain_valid:
            r94.terms(case, float(x[1]), float(x[2]))
        resource_cap_hit = bool(int(output.status) == 0 or callback_count > callback_cap)
        termination_admissible = bool(output.success and int(output.status) > 0)
        residual_acceptance = bool(all(value <= 1.0 for value in ratios))
        accepted = bool(
            termination_admissible
            and int(output.nfev) <= max_nfev
            and not resource_cap_hit
            and domain_valid
            and residual_acceptance
        )
        failure_class = (
            "NONE"
            if accepted
            else "SOLVER_RESOURCE_EXHAUSTION"
            if resource_cap_hit
            else "SOLVER_TERMINATED_RESIDUAL_UNACCEPTED"
            if termination_admissible and not residual_acceptance
            else "FINAL_STATE_DOMAIN_INVALID"
            if not domain_valid
            else "NOT_CONVERGED"
        )
        return {
            "case_id": str(case.case_id),
            "initial_seed": [float(value) for value in seed],
            "solution": [float(value) for value in x],
            "q_hc_W": float(x[0]),
            "q_ts_W": float(case.s_ts * float(x[0])),
            "T_wall_inner_K": float(x[1]),
            "T_wall_outer_K": float(x[2]),
            "physical_residuals_W": [float(value) for value in physical],
            "candidate_c_bounds_W": bounds,
            "residual_to_bound_ratios": ratios,
            "max_residual_to_bound_ratio": max(ratios),
            "solver_success": bool(output.success),
            "solver_status": int(output.status),
            "solver_message": str(output.message),
            "nfev": int(output.nfev),
            "njev": None if output.njev is None else int(output.njev),
            "residual_callback_count": callback_count,
            "resource_cap_hit": resource_cap_hit,
            "domain_valid": domain_valid,
            "solver_termination_admissible": termination_admissible,
            "residual_acceptance_pass": residual_acceptance,
            "accepted": accepted,
            "failure_class": failure_class,
            "profile_canonical_hash": EXPECTED_PROFILE_HASH,
        }
    except r94.ReviewFailure as exc:
        return {
            "case_id": str(case.case_id),
            "initial_seed": [float(value) for value in seed],
            "accepted": False,
            "failure_class": str(exc),
            "resource_cap_hit": "RESOURCE_EXHAUSTION" in str(exc),
            "domain_valid": False,
            "residual_callback_count": callback_count,
            "profile_canonical_hash": EXPECTED_PROFILE_HASH,
        }
    except (ValueError, FloatingPointError, OverflowError) as exc:
        return {
            "case_id": str(case.case_id),
            "initial_seed": [float(value) for value in seed],
            "accepted": False,
            "failure_class": f"SOLVER_NUMERICAL_FAILURE:{type(exc).__name__}:{exc}",
            "resource_cap_hit": False,
            "domain_valid": False,
            "residual_callback_count": callback_count,
            "profile_canonical_hash": EXPECTED_PROFILE_HASH,
        }


def nearest_rank(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return float(ordered[max(0, math.ceil(quantile * len(ordered)) - 1)])


def evaluate_runtime_matrix(
    r94: Any, holdout: dict[str, Any], runtime_repeats: int = 2
) -> dict[str, Any]:
    profile = cast(dict[str, Any], holdout["selected_candidate_profile"])
    require(profile == EXPECTED_PROFILE, "holdout profile differs from frozen P1")
    base_rows = cast(list[dict[str, Any]], holdout["future_cases"])
    base_by_id: dict[str, Any] = {}
    base_oracles: dict[str, dict[str, Any]] = {}
    for row in base_rows:
        constructor_row = dict(row)
        constructor_row["type"] = constructor_row["case_class"]
        base = r94.make_holdout_case(
            constructor_row,
            float(holdout["base_area_i_m2"]),
            float(holdout["base_area_o_m2"]),
        )
        base_by_id[str(row["case_id"])] = base
        base_oracles[str(row["case_id"])] = scalar_oracle_record(r94, base)

    scalar_replays: list[dict[str, Any]] = []
    for row in base_rows:
        case_id = str(row["case_id"])
        base_oracle = base_oracles[case_id]
        for scale_text in REPRESENTATIVE_SCALAR_ORACLE_SCALES:
            case = scaled_case(r94, base_by_id[case_id], scale_text)
            replay = scalar_oracle_record(r94, case)
            factor = float(Fraction(scale_text))
            if base_oracle.get("oracle_pass") and replay.get("oracle_pass"):
                errors = {
                    "q_hc_W": abs(float(replay["q_hc_W"]) - factor * float(base_oracle["q_hc_W"])),
                    "T_wall_inner_K": abs(
                        float(replay["T_wall_inner_K"]) - float(base_oracle["T_wall_inner_K"])
                    ),
                    "T_wall_outer_K": abs(
                        float(replay["T_wall_outer_K"]) - float(base_oracle["T_wall_outer_K"])
                    ),
                }
                replay["exact_scale_identity_absolute_discrepancy"] = errors
                replay["discrepancy_is_finite"] = all(
                    math.isfinite(value) for value in errors.values()
                )
            else:
                replay["exact_scale_identity_absolute_discrepancy"] = None
                replay["discrepancy_is_finite"] = False
            replay["base_case_id"] = case_id
            replay["scale_fraction_exact"] = scale_text
            replay["production_scalar_reduction_selected"] = False
            scalar_replays.append(replay)

    def solve_pass() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for base_row in base_rows:
            base_case_id = str(base_row["case_id"])
            base_case = base_by_id[base_case_id]
            base_oracle = base_oracles[base_case_id]
            for scale_text in cast(list[str], holdout["scale_fractions_exact"]):
                case = scaled_case(r94, base_case, scale_text)
                solution = solve_frozen_profile(r94, case, profile)
                factor = float(Fraction(scale_text))
                scale_oracle: dict[str, float] | None = None
                scale_errors: dict[str, float] | None = None
                scale_oracle_finite = False
                if base_oracle.get("oracle_pass"):
                    scale_oracle = {
                        "q_hc_W": factor * float(base_oracle["q_hc_W"]),
                        "T_wall_inner_K": float(base_oracle["T_wall_inner_K"]),
                        "T_wall_outer_K": float(base_oracle["T_wall_outer_K"]),
                    }
                    if finite_solution(scale_oracle) and all(
                        key in solution for key in ("q_hc_W", "T_wall_inner_K", "T_wall_outer_K")
                    ):
                        scale_errors = {
                            key: abs(float(solution[key]) - scale_oracle[key])
                            for key in scale_oracle
                        }
                        scale_oracle_finite = all(
                            math.isfinite(value) for value in scale_errors.values()
                        )
                representative = next(
                    (
                        item
                        for item in scalar_replays
                        if item["base_case_id"] == base_case_id
                        and item["scale_fraction_exact"] == scale_text
                    ),
                    None,
                )
                no_typed_failure = solution.get("failure_class") == "NONE"
                accepted = bool(
                    solution.get("solver_termination_admissible")
                    and solution.get("residual_acceptance_pass")
                    and solution.get("domain_valid")
                    and not solution.get("resource_cap_hit")
                    and scale_oracle_finite
                    and no_typed_failure
                )
                row = {
                    **solution,
                    "case_id": f"{base_case_id}@{scale_text}",
                    "base_case_id": base_case_id,
                    "scale_fraction_exact": scale_text,
                    "scale_factor": factor,
                    "scale_oracle": scale_oracle,
                    "scale_oracle_absolute_errors": scale_errors,
                    "scale_oracle_comparison_finite": scale_oracle_finite,
                    "representative_direct_scalar_oracle_replayed": representative is not None,
                    "representative_direct_scalar_oracle_pass": (
                        None if representative is None else bool(representative["oracle_pass"])
                    ),
                    "no_typed_failure_active": no_typed_failure,
                    "accepted": accepted,
                }
                if not accepted and row.get("failure_class") == "NONE":
                    row["failure_class"] = "SCALE_ORACLE_OR_ACCEPTANCE_GATE_FAILED"
                rows.append(row)
        return rows

    first_rows = solve_pass()
    second_rows = solve_pass() if runtime_repeats >= 2 else []
    first_matrix_bytes = canonical_bytes({"rows": first_rows})
    second_matrix_bytes = canonical_bytes({"rows": second_rows}) if second_rows else b""
    deterministic = bool(second_rows and first_matrix_bytes == second_matrix_bytes)
    accepted_count = sum(bool(row["accepted"]) for row in first_rows)
    ratios = [
        float(row["max_residual_to_bound_ratio"])
        for row in first_rows
        if row.get("max_residual_to_bound_ratio") is not None
        and math.isfinite(float(row["max_residual_to_bound_ratio"]))
    ]
    q_errors = [
        float(row["scale_oracle_absolute_errors"]["q_hc_W"])
        for row in first_rows
        if row.get("scale_oracle_absolute_errors") is not None
    ]
    twi_errors = [
        float(row["scale_oracle_absolute_errors"]["T_wall_inner_K"])
        for row in first_rows
        if row.get("scale_oracle_absolute_errors") is not None
    ]
    two_errors = [
        float(row["scale_oracle_absolute_errors"]["T_wall_outer_K"])
        for row in first_rows
        if row.get("scale_oracle_absolute_errors") is not None
    ]
    nfev_values = [int(row["nfev"]) for row in first_rows if row.get("nfev") is not None]
    callback_values = [
        int(row["residual_callback_count"])
        for row in first_rows
        if row.get("residual_callback_count") is not None
    ]
    k03_rows = [row for row in first_rows if row["base_case_id"] == "K03"]
    k05_rows = [row for row in first_rows if row["base_case_id"] == "K05"]
    direct_oracle_count = len(scalar_replays)
    direct_oracles_pass = bool(
        len(base_oracles) == 5
        and all(row.get("oracle_pass") for row in base_oracles.values())
        and direct_oracle_count == 15
        and all(
            row.get("oracle_pass") and row.get("discrepancy_is_finite") for row in scalar_replays
        )
    )
    holdout_all_pass = bool(
        len(first_rows) == 30 and accepted_count == 30 and direct_oracles_pass and deterministic
    )
    return {
        "runtime": {
            "python": sys.version.split()[0],
            "python_implementation": platform.python_implementation(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "coolprop": CoolProp.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "runner_sha256": file_sha256(Path(__file__).resolve()),
        "candidate_profile": profile,
        "candidate_profile_canonical_hash": canonical_hash(profile),
        "base_case_count": len(base_rows),
        "scale_count": len(holdout["scale_fractions_exact"]),
        "unique_case_count": len(first_rows),
        "solver_case_evaluations": len(first_rows) * (2 if runtime_repeats >= 2 else 1),
        "same_runtime_replay_count": runtime_repeats,
        "same_input_same_result_bytes": deterministic,
        "same_input_same_result_hash": (
            hashlib.sha256(first_matrix_bytes).hexdigest()
            == hashlib.sha256(second_matrix_bytes).hexdigest()
            if second_rows
            else False
        ),
        "result_matrix_canonical_hash": canonical_hash({"rows": first_rows}),
        "repeat_result_matrix_canonical_hash": (
            canonical_hash({"rows": second_rows}) if second_rows else None
        ),
        "base_case_scalar_oracles": base_oracles,
        "representative_scalar_oracle_scales_exact": list(REPRESENTATIVE_SCALAR_ORACLE_SCALES),
        "representative_scalar_oracle_replay_count": direct_oracle_count,
        "representative_scalar_oracle_replays": scalar_replays,
        "representative_scalar_oracle_replay_pass": direct_oracles_pass,
        "summary": {
            "accepted_count": accepted_count,
            "all_pass": holdout_all_pass,
            "max_residual_to_bound_ratio": max(ratios) if ratios else None,
            "p95_residual_to_bound_ratio_nearest_rank": nearest_rank(ratios, 0.95),
            "max_q_oracle_error_W": max(q_errors) if q_errors else None,
            "max_twi_oracle_error_K": max(twi_errors) if twi_errors else None,
            "max_two_oracle_error_K": max(two_errors) if two_errors else None,
            "max_observed_nfev": max(nfev_values) if nfev_values else None,
            "p95_nfev_nearest_rank": nearest_rank([float(v) for v in nfev_values], 0.95),
            "max_observed_callback_count": max(callback_values) if callback_values else None,
            "max_nfev_cap": int(profile["max_nfev"]),
            "max_nfev_headroom": (
                int(profile["max_nfev"]) - max(nfev_values) if nfev_values else None
            ),
            "callback_cap": int(profile["residual_callback_cap"]),
            "callback_cap_headroom": (
                int(profile["residual_callback_cap"]) - max(callback_values)
                if callback_values
                else None
            ),
            "resource_cap_hit_count": sum(bool(row.get("resource_cap_hit")) for row in first_rows),
            "k03_near_zero_nonzero_solve_pass": len(k03_rows) == 6
            and all(
                bool(row["accepted"])
                and float(row["q_hc_W"]) != 0.0
                and float(row["scale_factor"]) > 0.0
                for row in k03_rows
            ),
            "k05_negative_q_no_clamp_pass": len(k05_rows) == 6
            and all(bool(row["accepted"]) and float(row["q_hc_W"]) < 0.0 for row in k05_rows),
            "nonfinite_scale_oracle_count": sum(
                not bool(row["scale_oracle_comparison_finite"]) for row in first_rows
            ),
            "failure_rows": [
                {
                    "case_id": row["case_id"],
                    "failure_class": row.get("failure_class"),
                    "physical_residuals_W": row.get("physical_residuals_W"),
                    "candidate_c_bounds_W": row.get("candidate_c_bounds_W"),
                    "residual_to_bound_ratios": row.get("residual_to_bound_ratios"),
                    "solver_status": row.get("solver_status"),
                    "nfev": row.get("nfev"),
                    "residual_callback_count": row.get("residual_callback_count"),
                    "scale_oracle_absolute_errors": row.get("scale_oracle_absolute_errors"),
                }
                for row in first_rows
                if not row["accepted"]
            ],
        },
        "rows": first_rows,
        "governance": {
            "holdout_used_for_parameter_selection": False,
            "holdout_parameter_retuning": False,
            "c_round_retuned": False,
            "profile_changed_during_review": False,
            "r95_rerun_performed": False,
            "mesh_study_performed": False,
            "mesh_threshold_sensitivity_performed": False,
            "task173_solve_performed": False,
            "task174_solve_performed": False,
            "production_solver_execution": False,
            "production_code_changed": False,
            "task172_implementation_started": False,
        },
    }


def run_mode(output_path: Path) -> int:
    static_replay, r94, holdout = verify_static_artifacts()
    runtime_result = evaluate_runtime_matrix(r94, holdout, runtime_repeats=2)
    result = {
        "schema_version": "TASK172_MESH_CELL_SCALE_EXTENSION_INDEPENDENT_REVIEW_RUNTIME_R1",
        "task_id": (
            "TASK172_V0_7_MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION_INDEPENDENT_REVIEW_R1"
        ),
        "predecessor_head": EXPECTED_PREDECESSOR_HEAD,
        "holdout_input_canonical_hash": EXPECTED_R96A_HOLDOUT_HASH,
        "static_replay": static_replay,
        "runtime_result": runtime_result,
    }
    result["canonical_hash"] = canonical_hash(result)
    write_json(output_path, result)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "runtime": runtime_result["runtime"],
                "accepted": runtime_result["summary"]["accepted_count"],
                "case_count": runtime_result["unique_case_count"],
                "same_run_deterministic": runtime_result["same_input_same_result_bytes"],
                "all_pass": runtime_result["summary"]["all_pass"],
                "canonical_hash": result["canonical_hash"],
            },
            sort_keys=True,
        )
    )
    return 0 if runtime_result["summary"]["all_pass"] else 2


def aggregate_mode(input_paths: list[Path], output_path: Path) -> int:
    runs = [read_json(path) for path in input_paths]
    require(len(runs) == 2, "aggregate requires exactly two runtime results")
    runtime_map = {
        str(run["runtime_result"]["runtime"]["python"]).rsplit(".", 1)[0]: run for run in runs
    }
    require(set(runtime_map) == {"3.11", "3.12"}, "aggregate needs Python 3.11 and 3.12")
    ordered_runs = [runtime_map["3.11"], runtime_map["3.12"]]
    for run in ordered_runs:
        runtime_result = run["runtime_result"]
        require(run["static_replay"]["static_replay_pass"], "static replay did not pass")
        require(
            runtime_result["candidate_profile_canonical_hash"] == EXPECTED_PROFILE_HASH,
            "runtime selected profile hash differs",
        )
        require(
            runtime_result["summary"]["all_pass"],
            f"holdout failed on Python {runtime_result['runtime']['python']}",
        )
        require(
            runtime_result["same_input_same_result_bytes"],
            "same-runtime result bytes are not deterministic",
        )
        require(
            runtime_result["same_input_same_result_hash"],
            "same-runtime result hashes are not deterministic",
        )

    left = {str(row["case_id"]): row for row in ordered_runs[0]["runtime_result"]["rows"]}
    right = {str(row["case_id"]): row for row in ordered_runs[1]["runtime_result"]["rows"]}
    require(set(left) == set(right) and len(left) == 30, "dual-runtime case identities differ")
    per_case_differences: list[dict[str, Any]] = []
    for case_id in sorted(left):
        a = left[case_id]
        b = right[case_id]
        metrics = ("q_hc_W", "T_wall_inner_K", "T_wall_outer_K")
        diffs = {metric: abs(float(a[metric]) - float(b[metric])) for metric in metrics}
        per_case_differences.append(
            {
                "case_id": case_id,
                "exact_numeric_solution_equal": all(float(a[m]) == float(b[m]) for m in metrics),
                "absolute_difference": diffs,
            }
        )
    all_exact = all(row["exact_numeric_solution_equal"] for row in per_case_differences)
    max_differences = {
        metric: max(float(row["absolute_difference"][metric]) for row in per_case_differences)
        for metric in ("q_hc_W", "T_wall_inner_K", "T_wall_outer_K")
    }
    all_rows = [row for run in ordered_runs for row in run["runtime_result"]["rows"]]
    all_ratios = [float(row["max_residual_to_bound_ratio"]) for row in all_rows]
    all_q_errors = [float(row["scale_oracle_absolute_errors"]["q_hc_W"]) for row in all_rows]
    all_twi_errors = [
        float(row["scale_oracle_absolute_errors"]["T_wall_inner_K"]) for row in all_rows
    ]
    all_two_errors = [
        float(row["scale_oracle_absolute_errors"]["T_wall_outer_K"]) for row in all_rows
    ]
    all_nfev = [float(row["nfev"]) for row in all_rows]
    all_callbacks = [int(row["residual_callback_count"]) for row in all_rows]
    base = {
        "schema_version": "TASK172_MESH_CELL_SCALE_EXTENSION_INDEPENDENT_REVIEW_RESULTS_R1",
        "task_id": (
            "TASK172_V0_7_MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION_INDEPENDENT_REVIEW_R1"
        ),
        "predecessor_head": EXPECTED_PREDECESSOR_HEAD,
        "selected_candidate_id": "P1_ACCEPTANCE_EXTENSION",
        "selected_profile_canonical_hash": EXPECTED_PROFILE_HASH,
        "corrected_holdout_canonical_hash": EXPECTED_R96A_HOLDOUT_HASH,
        "corrected_base_case_matrix_canonical_hash": EXPECTED_R96A_BASE_MATRIX_HASH,
        "duplicate_audit_canonical_hash": EXPECTED_R97_DUPLICATE_AUDIT_HASH,
        "unique_holdout_case_count": 30,
        "holdout_scale_fraction_count": 6,
        "holdout_base_case_count": 5,
        "runtime_count": 2,
        "runtime_results": ordered_runs,
        "cross_runtime_numeric_equality": {
            "exact_solution_equality": all_exact,
            "exactly_equal_case_count": sum(
                bool(row["exact_numeric_solution_equal"]) for row in per_case_differences
            ),
            "case_count": len(per_case_differences),
            "max_absolute_difference": max_differences,
            "per_case": per_case_differences,
            "equality_is_a_pass_requirement": False,
        },
        "combined_summary": {
            "accepted_unique_case_executions": sum(
                int(run["runtime_result"]["summary"]["accepted_count"]) for run in ordered_runs
            ),
            "all_30_pass_on_both_runtimes": all(
                bool(run["runtime_result"]["summary"]["all_pass"]) for run in ordered_runs
            ),
            "holdout_max_residual_to_bound_ratio": max(all_ratios),
            "holdout_p95_residual_to_bound_ratio_nearest_rank": nearest_rank(all_ratios, 0.95),
            "holdout_max_q_oracle_error_W": max(all_q_errors),
            "holdout_max_twi_oracle_error_K": max(all_twi_errors),
            "holdout_max_two_oracle_error_K": max(all_two_errors),
            "max_observed_nfev": int(max(all_nfev)),
            "p95_nfev_nearest_rank": nearest_rank(all_nfev, 0.95),
            "max_observed_callback_count": max(all_callbacks),
            "max_nfev_cap": EXPECTED_PROFILE["max_nfev"],
            "max_nfev_headroom": EXPECTED_PROFILE["max_nfev"] - int(max(all_nfev)),
            "callback_cap": EXPECTED_PROFILE["residual_callback_cap"],
            "callback_cap_headroom": EXPECTED_PROFILE["residual_callback_cap"] - max(all_callbacks),
            "resource_cap_hit_count": sum(
                int(run["runtime_result"]["summary"]["resource_cap_hit_count"])
                for run in ordered_runs
            ),
            "k03_near_zero_nonzero_solve_pass_both_runtimes": all(
                bool(run["runtime_result"]["summary"]["k03_near_zero_nonzero_solve_pass"])
                for run in ordered_runs
            ),
            "k05_negative_q_no_clamp_pass_both_runtimes": all(
                bool(run["runtime_result"]["summary"]["k05_negative_q_no_clamp_pass"])
                for run in ordered_runs
            ),
            "representative_scalar_oracle_replay_count_per_runtime": 15,
            "representative_scalar_oracle_replay_pass_both_runtimes": all(
                bool(run["runtime_result"]["representative_scalar_oracle_replay_pass"])
                for run in ordered_runs
            ),
        },
        "review_result": "PASS"
        if all(bool(run["runtime_result"]["summary"]["all_pass"]) for run in ordered_runs)
        else "FAIL",
        "candidate_profile_changed": False,
        "c_round_retuned": False,
        "holdout_used_for_parameter_selection": False,
        "r95_rerun_performed": False,
        "mesh_study_performed": False,
        "mesh_threshold_sensitivity_performed": False,
        "canonical_hash": "",
    }
    base["canonical_hash"] = canonical_hash(base)
    write_json(output_path, base)
    combined_summary = cast(dict[str, Any], base["combined_summary"])
    print(
        json.dumps(
            {
                "output": str(output_path),
                "review_result": base["review_result"],
                "accepted": combined_summary["accepted_unique_case_executions"],
                "unique_cases": base["unique_holdout_case_count"],
                "cross_runtime_exact_solution_equality": all_exact,
                "canonical_hash": base["canonical_hash"],
            },
            sort_keys=True,
        )
    )
    return 0 if base["review_result"] == "PASS" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output", type=Path, required=True)
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--input", type=Path, action="append", required=True)
    aggregate_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "run":
        return run_mode(args.output)
    return aggregate_mode(args.input, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
