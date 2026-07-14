from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    BlockerCode,
    ValidationStatus,
    validate_request,
)

from ._builders import make_request


def test_valid_geometry_satisfies_exact_clearance_identities() -> None:
    result = validate_request(
        make_request(), software_version="tests", git_commit="abc"
    )
    assert result.status is ValidationStatus.VALID
    assert result.geometry is not None
    geometry = result.geometry
    assert Decimal(geometry.bare_tube_bundle_diameter_m) == (
        Decimal(geometry.bare_tube_bundle_radius_m) * 2
    )
    assert Decimal(geometry.bundle_outer_envelope_radius_m) == (
        Decimal(geometry.bare_tube_bundle_radius_m)
        + Decimal(geometry.bundle_peripheral_allowance_m)
    )
    assert Decimal(geometry.shell_to_bundle_diametral_clearance_m) == (
        Decimal(geometry.shell_inside_diameter_m)
        - Decimal(geometry.bundle_outer_envelope_diameter_m)
    )
    assert Decimal(geometry.radial_clearance_margin_m) == (
        Decimal(geometry.shell_to_bundle_radial_clearance_m)
        - Decimal(geometry.required_minimum_radial_clearance_m)
    )


def test_shell_not_larger_than_bundle_blocks_without_partial_geometry() -> None:
    result = validate_request(
        make_request(shell_diameter="0.01"),
        software_version="tests",
        git_commit="abc",
    )
    assert result.geometry is None
    assert result.blocked_result_hash is not None
    assert BlockerCode.SBG_SHELL_NOT_LARGER_THAN_BUNDLE.value in {
        item.code for item in result.blockers
    }


def test_clearance_equality_is_accepted() -> None:
    first = validate_request(
        make_request(minimum_clearance="0"),
        software_version="tests",
        git_commit="abc",
    )
    assert first.geometry is not None
    exact = first.geometry.shell_to_bundle_radial_clearance_m
    second = validate_request(
        make_request(minimum_clearance=exact),
        software_version="tests",
        git_commit="abc",
    )
    assert second.geometry is not None
    assert second.geometry.radial_clearance_margin_m == "0"
