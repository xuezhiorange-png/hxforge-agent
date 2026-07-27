"""TASK-025 pytest fixtures for hydraulic geometry tests.

Provides:
  - task020_configuration: a fixed CONFIG-A ShellAndTubeConfiguration.
  - task021_layout: a fixed LAYOUT-A TubeLayout with 8 positions.
  - tube_inner_diameter_m / internal_flow_length_m / heat_transfer_length_m.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    ConstructionFamily,
    EquipmentFamily,
    Orientation,
    ShellAndTubeConfiguration,
    StandardClaimStatus,
)
from hexagent.exchangers.shell_tube.tube_layout.models import (
    ApprovedTubeGeometrySnapshot,
    TubeLayout,
    TubePosition,
)

_TASK020_CONFIG_A_ID = "config-a-001"
_TASK020_CONFIG_A_HASH = "a" * 64
_TASK021_LAYOUT_A_ID = "layout-a-001"
_TASK021_LAYOUT_A_HASH = "b" * 64


def _build_task020_configuration() -> ShellAndTubeConfiguration:
    return ShellAndTubeConfiguration(
        schema_version="task020.configuration.v1",
        configuration_id=_TASK020_CONFIG_A_ID,
        configuration_hash=_TASK020_CONFIG_A_HASH,
        equipment_family=EquipmentFamily.SHELL_AND_TUBE,
        authority_mode=AuthorityMode.INTERNAL_GENERIC,
        standard_claim_status=StandardClaimStatus.NO_STANDARD_CLAIM,
        construction_family=ConstructionFamily.FIXED_TUBESHEET,
        orientation=Orientation.HORIZONTAL,
        shell_pass_count=1,
        tube_pass_count=1,
        component_tokens=None,  # type: ignore[arg-type]
        authority_binding=None,  # type: ignore[arg-type]
        case_authority=None,  # type: ignore[arg-type]
    )


def _build_task021_layout(position_ids: tuple[str, ...]) -> TubeLayout:
    positions = tuple(
        TubePosition(position_id=pid, u=idx, v=0, x_m="0.0", y_m="0.0")
        for idx, pid in enumerate(position_ids)
    )
    geometry = ApprovedTubeGeometrySnapshot(
        geometry_id="geom-a-001",
        geometry_type="round",
        revision="1",
        approval_state="approved",
        outer_diameter_m="0.020",
        inner_diameter_m="0.016",
        wall_thickness_m="0.004",
        record_hash="c" * 64,
        snapshot_hash="d" * 64,
        source_binding=None,  # type: ignore[arg-type]
    )
    return TubeLayout(
        schema_version="task021.tube-layout.v1",
        layout_id=_TASK021_LAYOUT_A_ID,
        layout_hash=_TASK021_LAYOUT_A_HASH,
        request_hash="e" * 64,
        task020_configuration_id=_TASK020_CONFIG_A_ID,
        task020_configuration_hash=_TASK020_CONFIG_A_HASH,
        case_authority={},  # type: ignore[arg-type]
        construction_family=ConstructionFamily.FIXED_TUBESHEET.value,
        equipment_orientation=Orientation.HORIZONTAL,
        shell_pass_count=1,
        tube_pass_count=1,
        tube_geometry=geometry,
        layout_rule_authority=None,  # type: ignore[arg-type]
        placement_envelope=None,  # type: ignore[arg-type]
        origin_mode=None,  # type: ignore[arg-type]
        axis_orientation=None,  # type: ignore[arg-type]
        exclusion_zones=(),
        positions=positions,
        tube_hole_count=len(positions),
        physical_tube_count=len(positions),
        boundary_rejection_count=0,
        exclusion_rejection_count=0,
        exclusion_audit=(),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance={},  # type: ignore[arg-type]
    )


DEFAULT_POSITION_IDS: tuple[str, ...] = tuple(f"P{i:03d}" for i in range(8))


@pytest.fixture
def task020_configuration() -> ShellAndTubeConfiguration:
    return _build_task020_configuration()


@pytest.fixture
def task021_layout() -> TubeLayout:
    return _build_task021_layout(DEFAULT_POSITION_IDS)


@pytest.fixture
def tube_inner_diameter_m() -> Decimal:
    return Decimal("0.016")


@pytest.fixture
def internal_flow_length_m() -> Decimal:
    return Decimal("4.85000000")


@pytest.fixture
def heat_transfer_length_m() -> Decimal:
    return Decimal("4.85000000")
