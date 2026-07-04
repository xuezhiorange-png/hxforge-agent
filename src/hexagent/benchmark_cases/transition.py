"""Section 9.3 deterministic state-transition table for TASK-011 benchmark cases.

Per the TASK-011 frozen design contract
(``docs/tasks/TASK-011-benchmark-case-governance.md``, frozen SHA
``7cfdb4f0989b6d384533c7a29e9a2156c731bd0f``), Section 9.3 mandates a total
deterministic function

    transition(stage, condition, current_state) -> next_state

with the following binding properties:

* The function MUST be total: every ``(stage, condition)`` pair in the table
  MUST have exactly one ``next_state`` mapping.
* The function MUST NOT have side effects on canonical hash, manifest
  membership, or ``approval_snapshot``.
* The function MUST be reentrant: invoking it twice with identical inputs
  MUST produce identical outputs.

The implementation encodes the §9.3.1 / §9.3.2 / §9.3.3 transition tables
verbatim. Each row is a triple ``(stage, condition, next_state)`` and the
table is exposed as a tuple of triples (frozen at import time).
"""

from __future__ import annotations

from typing import Final, Literal

# Lifecycle stages per contract §9.3.
LifecycleStage = Literal[
    "pre_approval",
    "approval_attempt",
    "manifest_inclusion",
    "ci_validation",
]

# Condition identifiers per contract §9.3.1 / §9.3.2 / §9.3.3.
TransitionCondition = Literal[
    # §9.3.1 — universal mandatory source-evidence missing
    "universal_source_evidence_missing",
    "class_specific_source_evidence_missing",
    # §9.3.2 — reviewer status
    "reviewer_status_pending",
    "reviewer_status_accepted",
    "reviewer_status_accepted_with_caveats_followup",
    "reviewer_status_accepted_with_caveats_evidence",
    "reviewer_status_rejected",
    # §9.3.3 — synthetic-regression-specific
    "synthetic_marker_missing",
    "synthetic_cited_as_independent_evidence",
]

# Review workflow states per contract §16.
ReviewState = Literal[
    "draft",
    "needs_source",
    "needs_normalization",
    "needs_expected_outputs",
    "under_review",
    "approved",
    "rejected",
    "superseded",
]

# Frozen transition table per contract §9.3.1 / §9.3.2 / §9.3.3.
#
# Each row is exactly (stage, condition, next_state). Implementation MUST
# encode the table verbatim; no alternative grouping of conditions into
# states is permitted (contract §9.3.4).
_TRANSITION_TABLE: Final[tuple[tuple[LifecycleStage, TransitionCondition, ReviewState], ...]] = (
    # §9.3.1 — universal mandatory source-evidence missing
    ("pre_approval", "universal_source_evidence_missing", "needs_source"),
    ("approval_attempt", "universal_source_evidence_missing", "rejected"),
    ("manifest_inclusion", "universal_source_evidence_missing", "rejected"),
    ("ci_validation", "universal_source_evidence_missing", "rejected"),
    # §9.3.1 — class-specific mandatory source-evidence missing
    ("pre_approval", "class_specific_source_evidence_missing", "needs_source"),
    ("approval_attempt", "class_specific_source_evidence_missing", "rejected"),
    ("manifest_inclusion", "class_specific_source_evidence_missing", "rejected"),
    ("ci_validation", "class_specific_source_evidence_missing", "rejected"),
    # §9.3.2 — reviewer status: pending
    ("pre_approval", "reviewer_status_pending", "under_review"),
    ("approval_attempt", "reviewer_status_pending", "under_review"),
    ("manifest_inclusion", "reviewer_status_pending", "under_review"),
    ("ci_validation", "reviewer_status_pending", "under_review"),
    # §9.3.2 — reviewer status: accepted at pre_approval
    ("pre_approval", "reviewer_status_accepted", "under_review"),
    # §9.3.2 — reviewer status: accepted at approval_attempt
    ("approval_attempt", "reviewer_status_accepted", "approved"),
    # §9.3.2 — reviewer status: accepted_with_caveats with reviewer follow-up
    ("pre_approval", "reviewer_status_accepted_with_caveats_followup", "under_review"),
    ("approval_attempt", "reviewer_status_accepted_with_caveats_followup", "under_review"),
    (
        "manifest_inclusion",
        "reviewer_status_accepted_with_caveats_followup",
        "under_review",
    ),
    ("ci_validation", "reviewer_status_accepted_with_caveats_followup", "under_review"),
    # §9.3.2 — reviewer status: accepted_with_caveats with evidence caveat
    ("pre_approval", "reviewer_status_accepted_with_caveats_evidence", "needs_source"),
    (
        "approval_attempt",
        "reviewer_status_accepted_with_caveats_evidence",
        "needs_source",
    ),
    (
        "manifest_inclusion",
        "reviewer_status_accepted_with_caveats_evidence",
        "needs_source",
    ),
    ("ci_validation", "reviewer_status_accepted_with_caveats_evidence", "needs_source"),
    # §9.3.2 — reviewer status: rejected (terminal)
    ("pre_approval", "reviewer_status_rejected", "rejected"),
    ("approval_attempt", "reviewer_status_rejected", "rejected"),
    ("manifest_inclusion", "reviewer_status_rejected", "rejected"),
    ("ci_validation", "reviewer_status_rejected", "rejected"),
    # §9.3.3 — synthetic marker missing or manifest listing absent
    ("pre_approval", "synthetic_marker_missing", "needs_source"),
    ("approval_attempt", "synthetic_marker_missing", "rejected"),
    ("manifest_inclusion", "synthetic_marker_missing", "rejected"),
    ("ci_validation", "synthetic_marker_missing", "rejected"),
    # §9.3.3 — synthetic cited as independent validation evidence (any stage → rejected)
    ("pre_approval", "synthetic_cited_as_independent_evidence", "rejected"),
    ("approval_attempt", "synthetic_cited_as_independent_evidence", "rejected"),
    ("manifest_inclusion", "synthetic_cited_as_independent_evidence", "rejected"),
    ("ci_validation", "synthetic_cited_as_independent_evidence", "rejected"),
)


# Lookup index for O(1) access.
_LOOKUP: Final[dict[tuple[LifecycleStage, TransitionCondition], ReviewState]] = {
    (stage, condition): next_state for stage, condition, next_state in _TRANSITION_TABLE
}


def transition(
    stage: LifecycleStage,
    condition: TransitionCondition,
    current_state: ReviewState,
) -> ReviewState:
    """Return the deterministic ``next_state`` for ``(stage, condition)``.

    Per contract §9.3.4 the function is total over the **frozen table's**
    (stage, condition) pairs. The ``current_state`` argument is part of the
    signature for forward compatibility with §9.3.4 ("the function MAY
    depend on current_state"); in the frozen table, the next state is
    determined purely by ``(stage, condition)`` and the current_state
    argument is accepted but unused.

    Raises ``KeyError`` if the caller passes a ``(stage, condition)`` pair
    that is NOT part of the frozen table — which is valid usage of the
    function: the frozen table does not enumerate every (stage, condition)
    Cartesian product, only the rows explicitly listed in §9.3.1 / §9.3.2
    / §9.3.3. Callers should guard with :func:`has_transition` first.
    """
    del current_state  # frozen table does not depend on current_state
    return _LOOKUP[(stage, condition)]


def has_transition(stage: LifecycleStage, condition: TransitionCondition) -> bool:
    """Return ``True`` iff ``(stage, condition)`` is a row of the frozen table."""
    return (stage, condition) in _LOOKUP


def all_transitions() -> tuple[tuple[LifecycleStage, TransitionCondition, ReviewState], ...]:
    """Return the full frozen transition table (read-only snapshot)."""
    return _TRANSITION_TABLE


__all__ = [
    "LifecycleStage",
    "TransitionCondition",
    "ReviewState",
    "transition",
    "has_transition",
    "all_transitions",
]
