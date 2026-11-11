"""Nozzle velocity binding for V08-03 (no guessed diameters)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from hexagent.exchangers.shell_tube.engineering_screening.models import (
    NozzleGeometryAuthority,
    ScreeningPropertySnapshot,
)
from hexagent.exchangers.shell_tube.engineering_screening.velocity import _nozzle_velocity
from hexagent.properties.base import PropertyProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import CandidateRatingBindings

NozzleVelocityStatus = Literal["VERIFIED", "PARTIAL", "UNRESOLVED"]
Side = Literal["TUBE", "SHELL"]


@dataclass(frozen=True)
class NozzleVelocitySide:
    side: Side
    velocity_m_s: str | None
    in_range_1_3: bool | None
    effective_flow_area_m2: str | None
    mass_flow_kg_s: str | None
    density_kg_m3: str | None
    data_source: str
    missing_fields: tuple[str, ...]


@dataclass(frozen=True)
class NozzleVelocityReport:
    status: NozzleVelocityStatus
    sides: tuple[NozzleVelocitySide, ...]
    note: str


def _in_range(value: Decimal) -> bool:
    return Decimal("1") <= value <= Decimal("3")


def _side_from_task167_shell(bindings: CandidateRatingBindings) -> NozzleVelocitySide:
    raw = bindings.bundle.bundle
    geom = getattr(raw, "task167_nozzle_geometry", None)
    snap = getattr(raw, "task167_screening_property_snapshot", None)
    missing: list[str] = []
    if geom is None:
        missing.append("manufacturable_bundle.task167_nozzle_geometry")
    if snap is None:
        missing.append("manufacturable_bundle.task167_screening_property_snapshot")
    if geom is None or snap is None:
        return NozzleVelocitySide(
            side="SHELL",
            velocity_m_s=None,
            in_range_1_3=None,
            effective_flow_area_m2=None,
            mass_flow_kg_s=None,
            density_kg_m3=None,
            data_source="TASK167_CHAIN_NOT_MATERIALIZED_IN_V08_168",
            missing_fields=tuple(missing),
        )
    if not isinstance(geom, NozzleGeometryAuthority) or not isinstance(
        snap, ScreeningPropertySnapshot
    ):
        return NozzleVelocitySide(
            side="SHELL",
            velocity_m_s=None,
            in_range_1_3=None,
            effective_flow_area_m2=str(getattr(geom, "flow_area_m2", None)),
            mass_flow_kg_s=None,
            density_kg_m3=None,
            data_source="TASK167_TYPE_MISMATCH",
            missing_fields=("typed NozzleGeometryAuthority + ScreeningPropertySnapshot",),
        )
    vel, err = _nozzle_velocity(geom, snap)
    if vel is None:
        return NozzleVelocitySide(
            side="SHELL",
            velocity_m_s=None,
            in_range_1_3=None,
            effective_flow_area_m2=str(geom.flow_area_m2),
            mass_flow_kg_s=str(snap.nozzle_mass_flow_rate_kg_s),
            density_kg_m3=str(snap.nozzle_density_kg_m3),
            data_source="TASK167_VELOCITY_SCREEN",
            missing_fields=(str(err[1]) if err else "nozzle_velocity",),
        )
    return NozzleVelocitySide(
        side="SHELL",
        velocity_m_s=str(vel),
        in_range_1_3=_in_range(vel),
        effective_flow_area_m2=str(geom.flow_area_m2),
        mass_flow_kg_s=str(snap.nozzle_mass_flow_rate_kg_s),
        density_kg_m3=str(snap.nozzle_density_kg_m3),
        data_source="TASK167_VELOCITY_SCREEN",
        missing_fields=(),
    )


def _side_tube_nozzle(
    bindings: CandidateRatingBindings, provider: PropertyProvider
) -> NozzleVelocitySide:
    """Tube-side connection nozzle — requires explicit nozzle area, not tube-bundle bulk area."""
    _ = provider
    raw = bindings.bundle.bundle
    t025 = getattr(raw, "task025_result", None)
    tube_bulk = getattr(t025, "bulk_velocity_m_s", None) if t025 is not None else None
    missing = (
        "tube_nozzle_inner_diameter_m or nozzle_flow_area_m2 from Task020 connection tokens",
        "Task168 chain sets include_legacy paths without Task167 nozzle authority",
    )
    return NozzleVelocitySide(
        side="TUBE",
        velocity_m_s=str(tube_bulk) if tube_bulk is not None else None,
        in_range_1_3=_in_range(tube_bulk) if tube_bulk is not None else None,
        effective_flow_area_m2=None,
        mass_flow_kg_s=str(bindings.normalized.tube_side.mass_flow_kg_s),
        density_kg_m3=None,
        data_source=(
            "TASK025_BULK_VELOCITY_NOT_NOZZLE"
            if tube_bulk is not None
            else "TASK020_NOZZLE_AREA_MISSING"
        ),
        missing_fields=missing,
    )


def assess_nozzle_velocities(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
) -> NozzleVelocityReport:
    shell = _side_from_task167_shell(bindings)
    tube = _side_tube_nozzle(bindings, provider)
    sides = (tube, shell)
    verified = [s for s in sides if s.velocity_m_s is not None and not s.missing_fields]
    if len(verified) == 2 and all(s.in_range_1_3 for s in verified):
        status: NozzleVelocityStatus = "VERIFIED"
        note = "Both sides computed from bound engineering authorities."
    elif verified:
        status = "PARTIAL"
        note = "At least one side lacks authoritative nozzle flow area."
    else:
        status = "UNRESOLVED"
        note = (
            "Run Task167 nozzle_geometry + screening_property_snapshot on the V08 bundle chain, "
            "or bind Task020 connection nozzle inner diameter to an effective_flow_area_m2."
        )
    return NozzleVelocityReport(status=status, sides=sides, note=note)


__all__ = ["NozzleVelocityReport", "NozzleVelocitySide", "assess_nozzle_velocities"]
