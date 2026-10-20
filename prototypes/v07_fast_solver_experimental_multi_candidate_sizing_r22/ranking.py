"""Task173 ranking policy replay for experimental multi-candidate sizing."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Literal, cast

from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import RankingTraceEntry
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.result_models import (
    ExperimentalCandidateSizingRecord,
)


def compute_ranking_score(
    shell_dp_pa: Decimal,
    status: Literal["PASS", "WARN"],
) -> Decimal:
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_HALF_EVEN
        score = shell_dp_pa / Decimal(100)
        if status == "WARN":
            score += Decimal(10)
    return score


def rank_experimental_candidates(
    records: list[ExperimentalCandidateSizingRecord],
) -> tuple[list[ExperimentalCandidateSizingRecord], tuple[RankingTraceEntry, ...]]:
    eligible = [item for item in records if item.status in ("PASS", "WARN") and not item.blockers]
    ranking = sorted(
        eligible,
        key=lambda item: (
            cast(Decimal, item.ranking_score),
            item.candidate_hash.encode("utf-8"),
        ),
    )
    trace: list[RankingTraceEntry] = []
    updated: dict[str, ExperimentalCandidateSizingRecord] = {r.candidate_id: r for r in records}
    for index, item in enumerate(ranking):
        with localcontext() as context:
            context.prec = 50
            context.rounding = ROUND_HALF_EVEN
            normalized_objective = cast(Decimal, item.shell_dp_pa) / Decimal(100)
        warn_penalty = Decimal(10) if item.status == "WARN" else Decimal(0)
        trace.append(
            RankingTraceEntry(
                candidate_id=item.candidate_id,
                candidate_hash=item.candidate_hash,
                source_status=cast(Literal["PASS", "WARN"], item.status),
                objective_metric="shell_dp_pa",
                objective_value=cast(Decimal, item.shell_dp_pa),
                normalized_objective=normalized_objective,
                warn_penalty=warn_penalty,
                composite_score=cast(Decimal, item.ranking_score),
                rank=index + 1,
                reason_codes=(
                    "MINIMIZE_SHELL_DP_PA",
                    "WARN_PENALTY_APPLIED" if item.status == "WARN" else "NO_WARN_PENALTY",
                    "CANDIDATE_HASH_ASC_UTF8_TIE_BREAK",
                ),
            )
        )
        updated[item.candidate_id] = item.model_copy(update={"rank": index + 1})
    ordered = [updated[r.candidate_id] for r in records]
    return ordered, tuple(trace)
