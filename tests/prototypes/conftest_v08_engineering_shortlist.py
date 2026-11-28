"""Session-scoped FIXTURE_330 engineering shortlist live report."""

from __future__ import annotations

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    EngineeringShortlistRobustnessReport,
    run_engineering_shortlist_robustness,
)


@pytest.fixture(scope="session")
def engineering_shortlist_report_330() -> EngineeringShortlistRobustnessReport:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    return run_engineering_shortlist_robustness(normalized, handoff, provider=provider)
