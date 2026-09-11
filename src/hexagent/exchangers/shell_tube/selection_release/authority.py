"""Formal TASK-169 production ranking authority.

The unit-test policy is intentionally a different identity.  Release and
Golden proposal paths must bind this source-bound policy before selection.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Final

from .canonical import ranking_policy_hash
from .models import (
    RankingDirection,
    RankingObjective,
    Task169RankingPolicy,
)

TASK169_PRODUCTION_RANKING_POLICY_ID: Final = "HXFORGE-V06-TASK169-RANKING-POLICY"
TASK169_PRODUCTION_RANKING_POLICY_VERSION: Final = "v1"
TASK169_PRODUCTION_RANKING_SOURCE_DEFINITION_ID: Final = (
    "TASK169-PRODUCTION-RANKING-SOURCE-DEFINITION-V1"
)
TASK169_PRODUCTION_RANKING_SOURCE_ID: Final = "TASK169-PRODUCTION-RANKING-AUTHORITY-V1"
TASK169_PRODUCTION_RANKING_AUTHORITY_ORIGIN: Final = "TASK169_IMPLEMENTATION_AUTHORITY_ISSUE_265"
TASK169_PRODUCTION_RANKING_TIE_BREAK_RULE: Final = "CANDIDATE_HASH_ASC_UTF8"


def _build_production_policy() -> Task169RankingPolicy:
    provisional = Task169RankingPolicy(
        policy_id=TASK169_PRODUCTION_RANKING_POLICY_ID,
        policy_version=TASK169_PRODUCTION_RANKING_POLICY_VERSION,
        source_definition_id=TASK169_PRODUCTION_RANKING_SOURCE_DEFINITION_ID,
        source_id=TASK169_PRODUCTION_RANKING_SOURCE_ID,
        authority_origin=TASK169_PRODUCTION_RANKING_AUTHORITY_ORIGIN,
        approval_status="APPROVED_FOR_IMPLEMENTATION",
        top_n=3,
        warning_penalty=Decimal("10"),
        objectives=(
            RankingObjective(
                metric="shell_dp_pa",
                direction=RankingDirection.MINIMIZE,
                weight=Decimal("1"),
                scale=Decimal("100"),
            ),
        ),
        tie_break_rule=TASK169_PRODUCTION_RANKING_TIE_BREAK_RULE,
        evidence_refs=(
            "TASK165_AUTHORITY_ISSUE_253",
            "TASK169_AUTHORITY_ISSUE_265",
            "docs/tasks/TASK-169-selection-integration-golden-release-acceptance.md",
        ),
        provenance_refs=(
            "TASK169_PRODUCTION_RANKING_AUTHORITY_V1",
            "TASK165_RANKING_ORDER_EXACT",
        ),
        canonical_hash="",
    )
    return replace(provisional, canonical_hash=ranking_policy_hash(provisional))


TASK169_PRODUCTION_RANKING_POLICY: Final[Task169RankingPolicy] = _build_production_policy()


def production_ranking_policy() -> Task169RankingPolicy:
    """Return the immutable production policy identity used by release paths."""

    return TASK169_PRODUCTION_RANKING_POLICY


__all__ = [
    "TASK169_PRODUCTION_RANKING_AUTHORITY_ORIGIN",
    "TASK169_PRODUCTION_RANKING_POLICY",
    "TASK169_PRODUCTION_RANKING_POLICY_ID",
    "TASK169_PRODUCTION_RANKING_POLICY_VERSION",
    "TASK169_PRODUCTION_RANKING_SOURCE_DEFINITION_ID",
    "TASK169_PRODUCTION_RANKING_SOURCE_ID",
    "TASK169_PRODUCTION_RANKING_TIE_BREAK_RULE",
    "production_ranking_policy",
]
