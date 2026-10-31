"""CLI exit code policy for experimental live-rating."""

from __future__ import annotations

from prototypes.v07_general_rating_sizing_mvp.experimental_live_workflow import (
    ExperimentalLiveRatingOutcome,
)


def experimental_live_rating_exit_code(outcome: ExperimentalLiveRatingOutcome) -> int:
    """Return 0 only when the workflow reports CLI success (NUMERIC_VALID rating path)."""
    if outcome.status == "INPUT_OUT_OF_SUPPORTED_SCOPE":
        return 1
    if outcome.status in {
        "BLOCKED_PREFLIGHT",
        "BLOCKED_CANDIDATE_SELECTION",
        "EXPERIMENTAL_BLOCKED",
    }:
        return 1
    if outcome.status == "EXPERIMENTAL_COMPLETE" and outcome.cli_success:
        return 0
    return 1
