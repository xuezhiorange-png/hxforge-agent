"""Replay the exact local q-to-provider/Task172 interval certificate.

This script rehydrates saved native request/results and performs Decimal,
Fraction, and binary64 mapping checks only. It never calls a property provider,
Task172 validator, cell/mesh solver, Candidate Rating, or Sizing API.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    recompute_task172_request_hash,
    recompute_task172_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    ReferencePlanePair,
    ReferencePlaneToken,
)

ROOT = Path(__file__).resolve().parents[3]
START_HEAD = "edc2dd877f98f72bf042ad348d68a07d30b34988"
RUNTIME_HEAD = "21386a88f8290538172e9389ed46f50c3697a426"
RUNTIME_TREE = "ce61a818b82f908729d2bdf4553cc27012354952"
RATING_SERVICE = "src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py"
TASK172_SERVICE = "src/hexagent/exchangers/shell_tube/task172_local_runtime/service.py"
SUMMARY_PATH = Path(
    "docs/tasks/evidence/"
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2-"
    "execution-summary.json"
)
R3_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-candidate-a-r2-snapshot-decimal-q-probe-only-r1.json"
)
CONTEXT_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-task172-decimal-context-adjudication-r1.json"
)
CERTIFICATE_PATH = Path(
    "docs/tasks/evidence/"
    "TASK-173-v0.7-candidate-a-point-root-interval-reachability-certificate-r1.json"
)
TOLERANCE = Decimal("0.000001")
LEFT_Q_TEXT = "268.4228547695099"
RIGHT_Q_TEXT = "268.42285476950997"
LEFT_REQUEST_HASH = "4fa675e1a36bd49c67957d2ed0a9dbef808529ffef7f2bdc6b51153da421c754"
LEFT_RESULT_HASH = "748819390174c8a2fa88f980b5073366817cce9d158c8bf9c56c52dd66e07ee9"
RIGHT_REQUEST_HASH = "b2472ec62e4a9e53517cdb5cc3a3f6c8d70106cd2cf34663ed2191bdaa9ce072"
RIGHT_RESULT_HASH = "ea8869a56cdd300ba42631aa967958aa01daa7e462ed7e5134b10d3d19893573"
R3_RESULT_HASH = "7e0512079ac5f28765f5685ff9ba761d56e0db277698b25ae6c26dc9984b8acc"
EXPECTED_CLASSIFICATION = "CERTIFIED_NO_ORDINARY_POINT_ROOT_UNDER_FROZEN_NUMERICAL_MAPPING"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if completed.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _read_bound_json(
    relative_path: Path,
    *,
    expected_sha256: str,
    expected_blob: str,
) -> tuple[dict[str, Any], bytes]:
    raw = (ROOT / relative_path).read_bytes()
    if _sha256(raw) != expected_sha256:
        raise RuntimeError(f"raw SHA-256 mismatch: {relative_path}")
    if _git("rev-parse", f"{START_HEAD}:{relative_path.as_posix()}") != expected_blob:
        raise RuntimeError(f"source-head Git blob mismatch: {relative_path}")
    if _git("rev-parse", f"HEAD:{relative_path.as_posix()}") != expected_blob:
        raise RuntimeError(f"current-head Git blob mismatch: {relative_path}")
    return json.loads(raw), raw


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


def _coordinates(q: Decimal, tube_upstream_h: Decimal, shell_left_h: Decimal) -> dict[str, Any]:
    with localcontext() as context:
        context.prec = 70
        context.rounding = ROUND_HALF_EVEN
        tube_downstream = tube_upstream_h - q / Decimal(12)
        shell_next = shell_left_h - q / Decimal(20)
        tube_midpoint = (tube_upstream_h + tube_downstream) / Decimal(2)
        shell_midpoint = (shell_left_h + shell_next) / Decimal(2)
    enthalpies = (tube_downstream, shell_next, tube_midpoint, shell_midpoint)
    return {
        "enthalpies": [str(value) for value in enthalpies],
        "input_hex": [float(value).hex() for value in enthalpies],
    }


def _subtract_exact(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 110
        context.rounding = ROUND_HALF_EVEN
        return left - right


def _certificate_replay() -> dict[str, Any]:
    current_head = _git("rev-parse", "HEAD")
    _git("merge-base", "--is-ancestor", START_HEAD, current_head)
    if _git("rev-parse", f"{RUNTIME_HEAD}^{{tree}}") != RUNTIME_TREE:
        raise RuntimeError("frozen runtime tree mismatch")
    _git("merge-base", "--is-ancestor", RUNTIME_HEAD, current_head)
    for path, expected_blob in (
        (RATING_SERVICE, "21f0eea0ceab099237ebc6af140858e65ab0fdf9"),
        (TASK172_SERVICE, "b6a1cfab5ca2c083c9ad8b39925934574b957b29"),
    ):
        if _git("rev-parse", f"{RUNTIME_HEAD}:{path}") != expected_blob:
            raise RuntimeError(f"frozen runtime source blob mismatch: {path}")
        if _git("rev-parse", f"HEAD:{path}") != expected_blob:
            raise RuntimeError(f"bound runtime changed at evidence head: {path}")
    path_diff = subprocess.run(
        [
            "git",
            "diff",
            "--exit-code",
            RUNTIME_HEAD,
            current_head,
            "--",
            RATING_SERVICE,
            TASK172_SERVICE,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if path_diff.returncode:
        raise RuntimeError("runtime source paths differ from frozen R2 source")

    summary, _ = _read_bound_json(
        SUMMARY_PATH,
        expected_sha256=("a38eeabe19758e6bc851756b636d8046cdcecd0cb493a1abad1aa45807cf1d81"),
        expected_blob="7a4f1c9099b65aa479cd5fd5d1ce7726f268fc35",
    )
    summary_hash = summary.pop("canonical_summary_hash", None)
    if canonical_sha256(summary) != summary_hash:
        raise RuntimeError("R2 compact summary canonical hash mismatch")
    summary["canonical_summary_hash"] = summary_hash
    failed = summary["failed_cell"]
    if (
        canonical_sha256(failed["target_trial_ledger"])
        != failed["target_trial_ledger_canonical_hash"]
    ):
        raise RuntimeError("R2 target-cell trial ledger hash mismatch")
    if len(failed["target_trial_ledger"]) != 749:
        raise RuntimeError("R2 target-cell trial count mismatch")
    signature_bindings: dict[tuple[tuple[str, str], ...], tuple[set[str], set[str]]] = {}
    provider_snapshot_bindings: dict[tuple[str, str], set[str]] = {}
    provider_trial_count = 0
    for trial in failed["target_trial_ledger"]:
        calls = trial["provider_ph_inputs"]
        if not calls:
            continue
        provider_trial_count += 1
        signature = tuple((call["role"], call["provider_enthalpy_float_hex"]) for call in calls)
        request_hashes, result_hashes = signature_bindings.setdefault(signature, (set(), set()))
        request_hashes.add(trial["task172_request_hash"])
        result_hashes.add(trial["task172_result_hash"])
        for call in calls:
            provider_snapshot_bindings.setdefault(
                (call["role"], call["provider_enthalpy_float_hex"]), set()
            ).add(call["provider_snapshot_hash"])
    if (
        provider_trial_count != 727
        or len(signature_bindings) != 719
        or any(
            len(request_hashes) != 1 or len(result_hashes) != 1
            for request_hashes, result_hashes in signature_bindings.values()
        )
        or any(len(snapshot_hashes) != 1 for snapshot_hashes in provider_snapshot_bindings.values())
    ):
        raise RuntimeError("observed provider-signature determinism binding failed")
    if (
        failed["mesh_subdivisions"] != 32
        or failed["outer_iteration"] != 24
        or failed["support_projection"]["subdivision_index"] != 21
        or failed["support_id"]
        != "urn:hxforge:task171:candidate:"
        "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767:support:2"
    ):
        raise RuntimeError("R2 failed-cell identity mismatch")

    r3, _ = _read_bound_json(
        R3_PATH,
        expected_sha256=("1c325d57ddbd30282851d84a87aac358beae38fb146989d1d10c62119ebde8ac"),
        expected_blob="8bdf02995df72d41da44c350ba6b50ac3c7246f0",
    )
    r3_hash = r3.pop("canonical_evidence_hash", None)
    if canonical_sha256(r3) != r3_hash:
        raise RuntimeError("R3 probe evidence canonical hash mismatch")
    r3["canonical_evidence_hash"] = r3_hash

    context_evidence, _ = _read_bound_json(
        CONTEXT_PATH,
        expected_sha256=("ad333f383431be03683f55b8ad2f78dcd6ff116572e4fe8bccf8aabe1aa77b15"),
        expected_blob="ba89e015d7331f9b40c82114ee78a3ce9249ef13",
    )
    context_hash = context_evidence.pop("canonical_evidence_hash", None)
    if canonical_sha256(context_evidence) != context_hash:
        raise RuntimeError("Decimal-context evidence canonical hash mismatch")
    context_evidence["canonical_evidence_hash"] = context_hash

    r2_context = context_evidence["decimal_context_r2"]
    if (
        r2_context["before_n32_reconstruction"]["prec"] != 28
        or r2_context["before_n32_reconstruction"]["rounding"] != "ROUND_HALF_EVEN"
        or r2_context["after_n32_reconstruction"]["prec"] != 28
        or r2_context["after_n32_reconstruction"]["rounding"] != "ROUND_HALF_EVEN"
        or r2_context["call_precision_inferred_from_saved_context_and_production_call_path"] != 28
        or context_evidence["decimal_context_causality"] != "CONFIRMED"
    ):
        raise RuntimeError("frozen Task172 baseline context is not bound")
    if context_evidence["controlled_baseline_result_hashes"] != [
        RIGHT_RESULT_HASH,
        RIGHT_RESULT_HASH,
    ]:
        raise RuntimeError("controlled p28 right-endpoint result replay mismatch")

    left = failed["left_endpoint"]
    right = failed["right_endpoint"]
    endpoints = {"left": left, "right": right}
    expected_endpoint_ids = {
        "left": (LEFT_REQUEST_HASH, LEFT_RESULT_HASH),
        "right": (RIGHT_REQUEST_HASH, RIGHT_RESULT_HASH),
    }
    for side, endpoint in endpoints.items():
        request = CandidateTask172LocalRequest.model_validate(
            _restore_pairs(endpoint["task172_request_projection"]), strict=False
        )
        result = Task172LocalResult.model_validate(
            _restore_pairs(endpoint["task172_result_projection"]), strict=False
        )
        request_hash, result_hash = expected_endpoint_ids[side]
        if (
            recompute_task172_request_hash(request) != request_hash
            or recompute_task172_result_hash(result) != result_hash
            or endpoint["task172_request_hash"] != request_hash
            or endpoint["task172_result_hash"] != result_hash
            or result.status != "VALIDATED"
            or result.request_hash != request_hash
        ):
            raise RuntimeError(f"{side} native Task172 identity replay failed")
        for record in endpoint["provider_ph_calls"]:
            snapshot = record["state_after_provider"]["property_snapshot"]
            if (
                canonical_sha256(snapshot)
                != record["state_after_provider"]["property_snapshot_hash"]
            ):
                raise RuntimeError(f"{side} provider snapshot hash mismatch")
            provider_float = float(Decimal(record["enthalpy_decimal_before_float"]))
            if provider_float.hex() != record["provider_enthalpy_float_hex"]:
                raise RuntimeError(f"{side} provider PH binary64 input mismatch")
        production_f = _subtract_exact(
            Decimal(endpoint["production_q_decimal"]),
            result.signed_q_hot_to_cold_w,
        )
        if str(production_f) != endpoint["f_production_decimal_context"]:
            raise RuntimeError(f"{side} production cell F replay failed")
        if endpoint["control_mode"] != "DISABLED":
            raise RuntimeError(f"{side} endpoint was not accepted-path DISABLED")
        midpoint_call = endpoint["provider_ph_calls"][2]
        request_temperature = endpoint["task172_request_projection"]["tube_bulk_state"][
            "temperature_k"
        ]
        snapshot_temperature = midpoint_call["state_after_provider"]["property_snapshot"][
            "temperature_k"
        ]
        if request_temperature != snapshot_temperature:
            raise RuntimeError(
                f"{side} request tube temperature is not bound to midpoint PH output"
            )

    left_projection = json.loads(json.dumps(left["task172_request_projection"]))
    right_projection = json.loads(json.dumps(right["task172_request_projection"]))
    left_projection["tube_bulk_state"]["temperature_k"] = "<midpoint_PH_output>"
    right_projection["tube_bulk_state"]["temperature_k"] = "<midpoint_PH_output>"
    if left_projection != right_projection:
        raise RuntimeError("Task172 endpoint requests differ beyond derived midpoint T")

    left_float = float(LEFT_Q_TEXT)
    right_float = float(RIGHT_Q_TEXT)
    if (
        left_float.hex() != left["q_w_binary64_hex"]
        or right_float.hex() != right["q_w_binary64_hex"]
        or math.nextafter(left_float, math.inf) != right_float
    ):
        raise RuntimeError("original binary64 q endpoints are not adjacent")

    tube_upstream_h = Decimal(failed["tube_upstream_state"]["property_snapshot"]["enthalpy_j_kg"])
    shell_left_h = Decimal(
        failed["shell_physical_left_state"]["property_snapshot"]["enthalpy_j_kg"]
    )
    q_domains = {
        "A": (Decimal(LEFT_Q_TEXT), Decimal(RIGHT_Q_TEXT)),
        "B": (Decimal.from_float(left_float), Decimal.from_float(right_float)),
        "C": (Decimal(LEFT_Q_TEXT), Decimal(RIGHT_Q_TEXT)),
    }
    endpoint_calculations: dict[str, list[dict[str, Any]]] = {}
    for label, bounds in q_domains.items():
        endpoint_calculations[label] = [
            _coordinates(q, tube_upstream_h, shell_left_h) for q in bounds
        ]

    captured_signature = {
        side: [record["provider_enthalpy_float_hex"] for record in endpoint["provider_ph_calls"]]
        for side, endpoint in endpoints.items()
    }
    if [item["input_hex"] for item in endpoint_calculations["A"]] != [
        captured_signature["left"],
        captured_signature["right"],
    ]:
        raise RuntimeError("p70 production-float endpoint PH mapping mismatch")
    from_float_signatures = context_evidence["provider_signature_comparison"][
        "r3_decimal_from_float_vs_decimal_str"
    ]
    expected_b_left = from_float_signatures["left"]["from_float_provider_input_signature"]
    expected_b_right = from_float_signatures["right"]["from_float_provider_input_signature"]
    if (
        endpoint_calculations["B"][0]["input_hex"] != expected_b_left
        or endpoint_calculations["B"][1]["input_hex"] != expected_b_right
        or expected_b_left != expected_b_right
        or expected_b_right != captured_signature["right"]
    ):
        raise RuntimeError("Decimal.from_float endpoint signature mismatch")
    if [item["input_hex"] for item in endpoint_calculations["C"]] != [
        captured_signature["left"],
        captured_signature["right"],
    ]:
        raise RuntimeError("Decimal-string endpoint signature mismatch")

    sig_left = tuple(captured_signature["left"])
    sig_right = tuple(captured_signature["right"])
    if sum(a != b for a, b in zip(sig_left, sig_right, strict=True)) != 1:
        raise RuntimeError("endpoint PH signatures differ in more than one coordinate")
    if sig_left[:2] != sig_right[:2] or sig_left[3] != sig_right[3]:
        raise RuntimeError("unexpected PH coordinate differs across endpoints")
    high_mid = float.fromhex(sig_left[2])
    low_mid = float.fromhex(sig_right[2])
    if not (high_mid > low_mid and math.nextafter(low_mid, math.inf) == high_mid):
        raise RuntimeError("tube midpoint PH coordinates are not adjacent binary64")

    # Exact affine threshold for h_tube_mid = h_tube_upstream - q/24.
    threshold_midpoint = (Fraction.from_float(high_mid) + Fraction.from_float(low_mid)) / 2
    q_threshold = 24 * (Fraction(tube_upstream_h) - threshold_midpoint)
    with localcontext() as context:
        context.prec = 110
        threshold_decimal = Decimal(q_threshold.numerator) / Decimal(q_threshold.denominator)
    if str(threshold_decimal) != "268.4228547695099019348621368408203125":
        raise RuntimeError("tube midpoint rounding threshold changed")
    if (q_threshold.numerator, q_threshold.denominator) != (
        45033882138046978389,
        167772160000000000,
    ):
        raise RuntimeError("unexpected exact threshold denominator")
    if not Decimal(LEFT_Q_TEXT) < threshold_decimal < Decimal(RIGHT_Q_TEXT):
        raise RuntimeError("tube midpoint threshold is outside string interval")
    if Decimal.from_float(left_float) <= threshold_decimal:
        raise RuntimeError("Decimal.from_float left endpoint should map to low midpoint")
    if not (
        Decimal(threshold_decimal - Decimal(LEFT_Q_TEXT)) > Decimal("1e-60")
        and Decimal(Decimal(RIGHT_Q_TEXT) - threshold_decimal) > Decimal("1e-60")
    ):
        raise RuntimeError("p70 arithmetic error bound could affect threshold coverage")

    probes = r3["execution"]["probes"]
    r3_signature = tuple(
        item["provider_enthalpy_float_hex"] for item in probes[0]["provider_ph_inputs_outputs"]
    )
    if len(probes) != 65 or r3["execution"]["provider_ph_signature_count"] != 1:
        raise RuntimeError("R3 historical probe metadata mismatch")
    for index, probe in enumerate(probes, start=1):
        signature = tuple(
            item["provider_enthalpy_float_hex"] for item in probe["provider_ph_inputs_outputs"]
        )
        if (
            signature != sig_right
            or probe["task172_request_hash"] != RIGHT_REQUEST_HASH
            or probe["task172_result_hash"] != R3_RESULT_HASH
            or probe["task172_status"] != "VALIDATED"
            or probe["probe_index"] != index
        ):
            raise RuntimeError("R3 probe does not bind to its single historical signature")
    if r3_signature != sig_right:
        raise RuntimeError("R3 signature is not the R2 right endpoint signature")

    q_left_float_exact = Decimal.from_float(left_float)
    q_right_float_exact = Decimal.from_float(right_float)
    right_q = Decimal(right["task172_signed_q_hot_to_cold_w"])
    left_q = Decimal(left["task172_signed_q_hot_to_cold_w"])
    b_f_bounds = (
        _subtract_exact(q_left_float_exact, right_q),
        _subtract_exact(q_right_float_exact, right_q),
    )
    c_left_f_bounds = (
        _subtract_exact(Decimal(LEFT_Q_TEXT), left_q),
        _subtract_exact(Decimal(RIGHT_Q_TEXT), left_q),
    )
    c_right_f_bounds = (
        _subtract_exact(Decimal(LEFT_Q_TEXT), right_q),
        _subtract_exact(Decimal(RIGHT_Q_TEXT), right_q),
    )
    a_f = (
        Decimal(left["f_production_decimal_context"]),
        Decimal(right["f_production_decimal_context"]),
    )
    minimum_abs_by_domain = {
        "A": min(abs(value) for value in a_f),
        "B": min(abs(value) for value in b_f_bounds),
        "C": min(abs(c_left_f_bounds[1]), abs(c_right_f_bounds[0])),
    }
    if any(value <= TOLERANCE for value in minimum_abs_by_domain.values()):
        raise RuntimeError("an ordinary root can be reachable within tolerance")
    if str(minimum_abs_by_domain["C"]) != "0.00000531787433":
        raise RuntimeError("conservative global residual lower bound changed")

    certificate = json.loads((ROOT / CERTIFICATE_PATH).read_text(encoding="utf-8"))
    recorded_hash = certificate.pop("canonical_certificate_hash", None)
    if canonical_sha256(certificate) != recorded_hash:
        raise RuntimeError("interval certificate canonical hash mismatch")
    if (
        certificate["classification"] != EXPECTED_CLASSIFICATION
        or certificate["scope"]["point_root_tolerance_w"] != str(TOLERANCE)
        or certificate["coordinate_domains"]["B_decimal_from_float_interval"][
            "reachable_task172_signature"
        ]
        != "right"
        or certificate["coordinate_domains"]["C_decimal_string_interval"][
            "minimum_abs_f_lower_bound_w"
        ]
        != str(minimum_abs_by_domain["C"])
        or certificate["provider_mapping"]["tube_midpoint_transition"][
            "exact_affine_rounding_boundary_q"
        ]
        != str(threshold_decimal)
        or certificate["provider_mapping"]["tube_midpoint_transition"][
            "coverage_uses_endpoint_monotonicity_and_adjacency_not_ideal_threshold_location"
        ]
        is not True
        or certificate["provider_mapping"]["task172_q_dependent_request_projection_binding"]
        != {
            "only_endpoint_projection_delta": "tube_bulk_state.temperature_k",
            "delta_is_exact_tube_midpoint_ph_snapshot_output": True,
            "no_independent_q_field": True,
        }
        or certificate["coverage_and_replay"]["target_trial_provider_mapping_audit"]
        != {
            "provider_trial_count": provider_trial_count,
            "unique_provider_signature_count": len(signature_bindings),
            "repeated_signature_snapshot_conflicts": 0,
            "repeated_signature_task172_request_conflicts": 0,
            "repeated_signature_task172_result_conflicts": 0,
        }
    ):
        raise RuntimeError("machine certificate differs from replayed interval facts")

    return {
        "certificate_hash": recorded_hash,
        "endpoint_signatures": {"left": list(sig_left), "right": list(sig_right)},
        "minimum_abs_f_by_domain_w": {
            key: str(value) for key, value in minimum_abs_by_domain.items()
        },
        "provider_trial_count": provider_trial_count,
        "unique_provider_signature_count": len(signature_bindings),
        "q_threshold": str(threshold_decimal),
        "r3_historical_probe_count": len(probes),
    }


def main() -> None:
    result = _certificate_replay()
    print("R2_COMPACT_SUMMARY_AND_LEDGER_REPLAY=PASS")
    print("LEFT_RIGHT_NATIVE_TASK172_PREIMAGE_REPLAY=PASS")
    print("R3_65_PROBE_EVIDENCE_REPLAY=PASS")
    print("DECIMAL_CONTEXT_P28_BINDING=PASS")
    print("Q_TO_PH_MONOTONIC_INTERVAL_COVERAGE=PASS")
    print("BINARY64_ROUNDING_THRESHOLD_REPLAY=PASS")
    print("REACHABLE_PROVIDER_SIGNATURE_COUNTS=A:2,B:1,C:2")
    print("ALL_REACHABLE_TASK172_SIGNATURES_COVERED=PASS")
    print(
        "OBSERVED_SIGNATURE_DETERMINISM="
        f"{result['provider_trial_count']} provider trials/"
        f"{result['unique_provider_signature_count']} signatures;"
        "no snapshot/request/result conflicts"
    )
    print("NO_SOLVER_OR_PROVIDER_CALLS=PASS")
    print("NATIVE_TASK172_VALIDATIONS_THIS_REPLAY=0")
    print(f"A_MIN_ABS_F_W={result['minimum_abs_f_by_domain_w']['A']}")
    print(f"B_MIN_ABS_F_LOWER_BOUND_W={result['minimum_abs_f_by_domain_w']['B']}")
    print(f"C_MIN_ABS_F_LOWER_BOUND_W={result['minimum_abs_f_by_domain_w']['C']}")
    print(f"TUBE_MIDPOINT_SWITCH_Q={result['q_threshold']}")
    print(f"CERTIFICATE_CANONICAL_HASH={result['certificate_hash']}")
    print(f"RESULT={EXPECTED_CLASSIFICATION}")


if __name__ == "__main__":
    main()
