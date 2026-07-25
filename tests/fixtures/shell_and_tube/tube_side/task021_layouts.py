"""TASK-021 identity fixtures (LAYOUT-A / LAYOUT-B)."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.models import (
    ConstructionFamily,
    Orientation,
)
from hexagent.exchangers.shell_tube.tube_layout.models import (
    ApprovedTubeGeometrySnapshot,
    TubeLayout,
    TubePosition,
)

_DEFAULT_CONFIG_A_ID = "config-a-001"
_DEFAULT_CONFIG_A_HASH = "a" * 64
_DEFAULT_CONFIG_B_ID = "config-b-002"
_DEFAULT_CONFIG_B_HASH = "f" * 64


def _build_layout(
    layout_id: str,
    layout_hash: str,
    position_ids: tuple[str, ...],
    config_id: str,
    config_hash: str,
    inner_diameter_m: str = "0.016",
) -> TubeLayout:
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
        inner_diameter_m=inner_diameter_m,
        wall_thickness_m="0.004",
        record_hash="c" * 64,
        snapshot_hash="d" * 64,
        source_binding=None,  # type: ignore[arg-type]
    )
    return TubeLayout(
        schema_version="task021.tube-layout.v1",
        layout_id=layout_id,
        layout_hash=layout_hash,
        request_hash="e" * 64,
        task020_configuration_id=config_id,
        task020_configuration_hash=config_hash,
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


def layout_a(position_ids: tuple[str, ...] = tuple(f"P{i:03d}" for i in range(8))) -> TubeLayout:
    """LAYOUT-A — paired with CONFIG-A."""
    return _build_layout(
        layout_id="layout-a-001",
        layout_hash="b" * 64,
        position_ids=position_ids,
        config_id=_DEFAULT_CONFIG_A_ID,
        config_hash=_DEFAULT_CONFIG_A_HASH,
    )


def layout_b(position_ids: tuple[str, ...] = tuple(f"Q{i:03d}" for i in range(8))) -> TubeLayout:
    """LAYOUT-B — paired with CONFIG-B."""
    return _build_layout(
        layout_id="layout-b-002",
        layout_hash="0" * 63 + "1",
        position_ids=position_ids,
        config_id=_DEFAULT_CONFIG_B_ID,
        config_hash=_DEFAULT_CONFIG_B_HASH,
    )


__all__ = ["layout_a", "layout_b"]