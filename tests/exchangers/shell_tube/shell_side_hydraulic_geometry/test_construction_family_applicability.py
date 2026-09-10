from __future__ import annotations

from typing import Any

import pytest

from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    engineering_authority_snapshot as task031_snapshot,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    validate_request,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.models import ValidationStatus
from tests.exchangers.shell_tube.shell_side_hydraulic_geometry.test_validation import (
    _resync_task021_layout_identity,
    _resync_task024_geometry_identity,
    base_fixture_v1,
)


def _family_fixture(family: str) -> dict[str, Any]:
    payload = base_fixture_v1()
    payload["tube_layout"]["construction_family"] = family
    payload["baffle_geometry_result"]["geometry"]["construction_family"] = family
    _resync_task021_layout_identity(payload)
    _resync_task024_geometry_identity(payload)
    return payload


def test_v06_construction_family_overlay_is_explicit_and_hash_neutral() -> None:
    assert task031_snapshot.SUPPORTED_CONSTRUCTION_FAMILIES == (
        "FIXED_TUBESHEET",
        "U_TUBE",
        "FLOATING_HEAD",
    )
    # This is the pre-correction projection digest.  The correction adds an
    # applicability gate outside that legacy formula projection.
    assert task031_snapshot.recompute_engineering_authority_hash() == (
        "50c829a3b12a0e2082de4255e7b81b921759b0f2e393e57ada561c50b58a105d"
    )


@pytest.mark.parametrize("family", task031_snapshot.SUPPORTED_CONSTRUCTION_FAMILIES)
def test_v06_families_are_admitted_without_formula_branch(
    family: str,
) -> None:
    baseline = validate_request(base_fixture_v1())
    candidate = validate_request(_family_fixture(family))

    assert baseline.status is ValidationStatus.VALID
    assert candidate.status is ValidationStatus.VALID
    assert baseline.geometry is not None
    assert candidate.geometry is not None
    assert candidate.geometry.formula_a_id == baseline.geometry.formula_a_id
    assert candidate.geometry.formula_b_id == baseline.geometry.formula_b_id
    assert (
        candidate.geometry.central_crossflow_flow_area_m2
        == baseline.geometry.central_crossflow_flow_area_m2
    )
    assert (
        candidate.geometry.shell_side_equivalent_hydraulic_diameter_m
        == baseline.geometry.shell_side_equivalent_hydraulic_diameter_m
    )
    assert (
        candidate.geometry.engineering_authority_hash == task031_snapshot.ENGINEERING_AUTHORITY_HASH
    )
    assert candidate.geometry.geometry_hash != baseline.geometry.geometry_hash or (
        family == "FIXED_TUBESHEET"
    )


def test_fixed_tubesheet_result_identity_remains_pinned() -> None:
    result = validate_request(base_fixture_v1())
    assert result.status is ValidationStatus.VALID
    assert result.geometry is not None
    assert result.geometry.geometry_id == "631386ca-b24a-5b60-84d6-6e84f900d81e"
    assert result.geometry.geometry_hash == (
        "167965c6df70818388ae72a284a621e13ffe9ccb4304d07d1c695cf518d81e27"
    )
    assert result.geometry.request_hash == (
        "7356f56f532f2edb54c5855f0af8b77df88e3c4c5d40b507397698fd277f56bf"
    )
    assert result.geometry.engineering_authority_hash == task031_snapshot.ENGINEERING_AUTHORITY_HASH


def test_unknown_construction_family_remains_fail_closed() -> None:
    payload = _family_fixture("UNSUPPORTED")
    result = validate_request(payload)

    assert result.status is ValidationStatus.BLOCKED
    assert [item.code for item in result.blockers] == ["SSHG_CONSTRUCTION_FAMILY_UNSUPPORTED"]
