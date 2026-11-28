"""V08-03 live thermal rating on enumerated geometry (lightweight gates)."""

from __future__ import annotations

from prototypes.v08_thermal_rating.pipeline import run_v08_thermal_rating
from tests.prototypes.v08_thermal_rating_test_support import FIXTURE, ready_handoff


def test_v08_03_model_blocked_without_experimental_thermal_binding() -> None:
    normalized, handoff = ready_handoff(FIXTURE)
    handoff_only = handoff.model_copy(
        update={"downstream_readiness": "VALIDATED_INPUT_ONLY", "thermal_binding": None}
    )
    result = run_v08_thermal_rating(normalized, handoff_only, max_valid_geometry=1)
    assert result.status == "BLOCKED"
    assert result.blocked_reason == "MODEL_BLOCKED_THERMAL_BINDING"
    assert result.engineering_acceptance == "BLOCKED"
    assert not result.candidates_rated
