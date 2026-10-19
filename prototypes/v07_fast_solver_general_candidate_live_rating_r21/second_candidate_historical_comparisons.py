"""Rebuild pinned second-candidate comparison chain from admitted stages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_comparison_persistence as scp,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_continuation as scc,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.rolling_mesh_sequence import (
    RollingMeshState,
)

HISTORICAL_COMPARISON_PAIRS: tuple[tuple[int, int], ...] = ((1, 2), (2, 4), (4, 8))


def rebuild_historical_comparison_chain(
    repo_root: Path,
    *,
    stages_by_mesh: dict[int, dict[str, Any]],
    output_comparison_dir: Path,
    request_hash: str,
    candidate_id: str,
    snapshot_path: Path,
    compare_budget_s: float = 180.0,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], RollingMeshState]:
    """Run bounded compares for n1→2, n2→4, n4→8; persist each receipt."""
    comparisons: list[dict[str, Any]] = []
    artifacts: list[dict[str, str]] = []
    rolling = RollingMeshState()
    for mesh_n in (1, 2, 4, 8):
        rolling.record_mesh_accepted(mesh_n)
    for coarse_n, fine_n in HISTORICAL_COMPARISON_PAIRS:
        coarse = stages_by_mesh[coarse_n]
        fine = stages_by_mesh[fine_n]
        try:
            cmp_payload = scc.compare_admitted_stage_pair(
                snapshot_path,
                coarse,
                fine,
                request_hash,
                candidate_id,
                rolling,
                compare_budget_s=compare_budget_s,
            )
        except scc.ComparePairFailure as exc:
            raise RuntimeError(exc.blocked_code or exc.status) from exc
        comparisons.append(cmp_payload)
        artifacts.append(
            scp.write_comparison_receipt(
                output_comparison_dir,
                coarse_n,
                fine_n,
                cmp_payload,
                repo_root=repo_root,
            )
        )
    return comparisons, artifacts, rolling
