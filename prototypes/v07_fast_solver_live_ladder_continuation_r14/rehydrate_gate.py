"""Fail-closed validation of bounded rehydrate worker receipts."""

from __future__ import annotations

from typing import Any


class RehydrateGateError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


def require_bounded_rehydrate_ok(
    result: dict[str, Any],
    *,
    mesh_n: int,
    expected_request_hash: str,
    expected_mesh_hash: str | None,
) -> None:
    status = result.get("status")
    if status != "OK":
        raise RehydrateGateError(
            str(result.get("blocked_code") or f"REHYDRATE_{status}"),
            f"mesh_n={mesh_n}",
            f"status={status}",
            *(str(d) for d in result.get("blocked_diagnostics") or ()),
        )
    if int(result.get("subdivisions", mesh_n)) != mesh_n:
        raise RehydrateGateError("REHYDRATE_MESH_N_MISMATCH", f"expected={mesh_n}")
    if expected_mesh_hash is not None and result.get("mesh_result_hash") != expected_mesh_hash:
        raise RehydrateGateError(
            "REHYDRATE_MESH_HASH_MISMATCH",
            f"expected={expected_mesh_hash}",
            f"actual={result.get('mesh_result_hash')}",
        )
    if not result.get("terminal_tolerance_pass"):
        raise RehydrateGateError("REHYDRATE_TERMINAL_TOLERANCE_FAIL", f"mesh_n={mesh_n}")
    if not result.get("cell_closure_pass"):
        raise RehydrateGateError("REHYDRATE_CELL_CLOSURE_FAIL", f"mesh_n={mesh_n}")
    if not result.get("energy_balance_pass"):
        raise RehydrateGateError("REHYDRATE_ENERGY_BALANCE_FAIL", f"mesh_n={mesh_n}")
    replay_hash = result.get("rating_request_hash")
    if replay_hash is not None and replay_hash != expected_request_hash:
        raise RehydrateGateError(
            "REHYDRATE_REQUEST_HASH_MISMATCH",
            f"expected={expected_request_hash}",
            f"actual={replay_hash}",
        )
