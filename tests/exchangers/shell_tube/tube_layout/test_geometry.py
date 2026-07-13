from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_layout.enumeration import Candidate, EnumerationPlan
from hexagent.exchangers.shell_tube.tube_layout.geometry import evaluate_geometry
from hexagent.exchangers.shell_tube.tube_layout.schema import parse_request
from tests.exchangers.shell_tube.tube_layout._builders import make_request


def test_envelope_boundary_equality_is_accepted() -> None:
    request = parse_request(make_request())
    plan = EnumerationPlan(
        a_x=Decimal(1), a_y=Decimal(0), b_x=Decimal(0), b_y=Decimal(1),
        offset_x=Decimal(0), offset_y=Decimal(0), rho=Decimal("0.05"),
        u_bound=1, v_bound=1, candidate_count=1,
    )
    candidate = Candidate(u=1, v=0, x=Decimal("0.05"), y=Decimal(0))
    result = evaluate_geometry((candidate,), plan, request.tube_geometry, ())
    assert len(result.accepted) == 1
    assert result.boundary_rejection_count == 0
