"""Fail-closed request and stage identity gates for live workers."""

from __future__ import annotations

from typing import Any


class IdentityGateError(ValueError):
    def __init__(self, blocked_code: str, *diagnostics: str) -> None:
        super().__init__(blocked_code)
        self.blocked_code = blocked_code
        self.diagnostics = diagnostics


def assert_request_hash_triple(
    expected_request_hash: str,
    snapshot_declared_hash: str,
    reconstructed_hash: str,
) -> None:
    if expected_request_hash != snapshot_declared_hash:
        raise IdentityGateError(
            "LIVE_REQUEST_HASH_SNAPSHOT_MISMATCH",
            f"expected={expected_request_hash}",
            f"snapshot={snapshot_declared_hash}",
        )
    if expected_request_hash != reconstructed_hash:
        raise IdentityGateError(
            "LIVE_REQUEST_HASH_RECONSTRUCT_MISMATCH",
            f"expected={expected_request_hash}",
            f"reconstructed={reconstructed_hash}",
        )


def assert_candidate_identity(
    expected_candidate_id: str,
    snapshot_candidate_id: str,
    receipt_candidate_id: str | None = None,
) -> None:
    if expected_candidate_id != snapshot_candidate_id:
        raise IdentityGateError(
            "LIVE_CANDIDATE_ID_SNAPSHOT_MISMATCH",
            f"expected={expected_candidate_id}",
            f"snapshot={snapshot_candidate_id}",
        )
    if receipt_candidate_id is not None and receipt_candidate_id != expected_candidate_id:
        raise IdentityGateError(
            "LIVE_CANDIDATE_ID_RECEIPT_MISMATCH",
            f"expected={expected_candidate_id}",
            f"receipt={receipt_candidate_id}",
        )


def assert_compare_stage_spec(
    spec: dict[str, Any],
    *,
    label: str,
) -> None:
    if not spec.get("terminal_tolerance_pass"):
        raise IdentityGateError(
            f"COMPARE_{label}_TERMINAL_NOT_ACCEPTED",
            f"mesh_n={spec.get('mesh_n')}",
        )
    if not spec.get("cell_closure_pass"):
        raise IdentityGateError(f"COMPARE_{label}_CELL_CLOSURE_FAIL")
    if not spec.get("energy_balance_pass"):
        raise IdentityGateError(f"COMPARE_{label}_ENERGY_BALANCE_FAIL")
    expected_hash = spec.get("expected_mesh_hash")
    if not expected_hash:
        raise IdentityGateError(f"COMPARE_{label}_MISSING_STAGE_MESH_HASH")
