from __future__ import annotations

import dataclasses
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_layout.enumeration import (
    build_plan,
    enumerate_candidates,
)
from hexagent.exchangers.shell_tube.tube_layout.schema import parse_request
from tests.exchangers.shell_tube.tube_layout._builders import make_request


def test_square_enumeration_is_deterministic() -> None:
    request = parse_request(make_request())
    plan = build_plan(
        request.layout_rule_authority,
        request.tube_geometry,
        request.placement_envelope,
        request.origin_mode,
        request.axis_orientation,
    )
    first = enumerate_candidates(plan)
    second = enumerate_candidates(plan)
    assert first == second
    assert plan.candidate_count == len(first)


def test_triangular_inverse_basis_regression_candidate_is_enumerated() -> None:
    request = parse_request(make_request(pattern_family="TRIANGULAR"))
    rule = dataclasses.replace(
        request.layout_rule_authority,
        pitch_m="1",
        maximum_candidate_positions=100000,
    )
    envelope = dataclasses.replace(
        request.placement_envelope,
        tube_center_envelope_diameter_m="200.02",
    )
    plan = build_plan(
        rule,
        request.tube_geometry,
        envelope,
        request.origin_mode,
        request.axis_orientation,
    )
    candidates = {(item.u, item.v): item for item in enumerate_candidates(plan)}
    assert (-57, 115) in candidates
    candidate = candidates[(-57, 115)]
    assert candidate.x == Decimal("0.5")
