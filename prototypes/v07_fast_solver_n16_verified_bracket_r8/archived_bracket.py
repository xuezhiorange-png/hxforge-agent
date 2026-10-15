"""Load and verify R7 archived n=16 outer trial bracket (candidate only)."""

from __future__ import annotations

from typing import Any

from prototypes.v07_fast_solver_evidence_gate.r7_archived_bracket import (
    verify_r7_archived_bracket,
)


def verify_archived_bracket_inputs(
    *,
    rating_request_hash: str,
) -> dict[str, Any]:
    return verify_r7_archived_bracket(rating_request_hash=rating_request_hash)
