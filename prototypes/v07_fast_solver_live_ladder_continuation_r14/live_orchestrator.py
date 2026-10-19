"""R14/R15 live rating continuation (delegates to continuation_engine)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.continuation_engine import (
    LadderContinuationDeps,
    LiveContinuationOutcome,
    run_live_ladder_continuation,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    DEFAULT_PRIOR_PINS,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalRatingBlocked,
)

LIVE_RATING_ORCHESTRATOR_ID = "V07-FAST-SOLVER-LIVE-LADDER-CONTINUATION-R14"


def experimental_rate_candidate_live_continuation(
    request: CandidateRatingRequest,
    *,
    root: Path,
    source_commit: str,
    snapshot_dir: Path,
    stage_dir: Path | None = None,
    live_mesh_levels: tuple[int, ...] = (4,),
    prior_pins: tuple[Any, ...] = DEFAULT_PRIOR_PINS,
    mesh_budgets_s: dict[int, float] | None = None,
    total_budget_s: float = 600.0,
    rehydrate_budget_s: float = 120.0,
    compare_budget_s: float = 60.0,
    deps: LadderContinuationDeps | None = None,
) -> LiveContinuationOutcome | ExperimentalRatingBlocked:
    return run_live_ladder_continuation(
        request,
        root=root,
        source_commit=source_commit,
        snapshot_dir=snapshot_dir,
        stage_dir=stage_dir,
        prior_pins=prior_pins,
        live_mesh_levels=live_mesh_levels,
        mesh_budgets_s=mesh_budgets_s or {4: 450.0},
        total_budget_s=total_budget_s,
        rehydrate_budget_s=rehydrate_budget_s,
        compare_budget_s=compare_budget_s,
        deps=deps,
    )
