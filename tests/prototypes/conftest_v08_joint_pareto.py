"""Session-scoped FIXTURE_330 Pareto joint search for joint-recovered CI shard."""

from __future__ import annotations

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.recovered_shell_052_pareto_joint_v08 import (
    Shell052ParetoJointReport,
    run_recovered_shell_052_pareto_joint_optimization,
)


@pytest.fixture(scope="session")
def pareto_joint_report_330() -> Shell052ParetoJointReport:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    return run_recovered_shell_052_pareto_joint_optimization(normalized, handoff, provider=provider)
