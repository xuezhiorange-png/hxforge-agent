"""TASK-038's narrow composition arithmetic.

Upstream engineering values are read from accepted public result objects.  No
geometry, heat-transfer coefficient, or wall value is re-derived here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .decimal_math import compose_resistances, public_outer_area, public_u, public_ua
from .models import ThermalResistanceLedgerRow
from .schema import (
    GV01_GAMMA,
    GV01_H_I,
    GV01_H_O,
    GV01_PUBLIC_A_O,
    GV01_PUBLIC_UA,
    GV01_R_FI_I,
    GV01_R_FO_O,
    GV01_R_W_O,
    OVERALL_U_REFERENCE_SURFACE,
    ROUNDING_MODE,
    TASK038_OUTER_AREA_QUANTUM_M2,
    TASK038_OVERALL_U_QUANTUM_W_M2_K,
    TASK038_UA_QUANTUM_W_K,
)


@dataclass(frozen=True)
class ResistanceComposition:
    r01: Decimal
    r02: Decimal
    r03: Decimal
    r04: Decimal
    r05: Decimal
    total: Decimal
    overall_u_raw: Decimal
    overall_u: Decimal


@dataclass(frozen=True)
class AreaComposition:
    raw_outer_area: Decimal
    outer_area: Decimal


@dataclass(frozen=True)
class UAComposition:
    raw_ua: Decimal
    ua: Decimal


def compute_resistance_composition(
    *,
    gamma: Decimal,
    h_i: Decimal,
    h_o: Decimal,
    inside_fouling: Decimal,
    wall_resistance: Decimal,
    outside_fouling: Decimal,
) -> ResistanceComposition:
    r01, r02, r03, r04, r05, total, raw_u = compose_resistances(
        gamma, h_i, h_o, inside_fouling, wall_resistance, outside_fouling
    )
    return ResistanceComposition(r01, r02, r03, r04, r05, total, raw_u, public_u(raw_u))


def compute_outer_area(*, published_inner_area: Decimal, gamma: Decimal) -> AreaComposition:
    raw = published_inner_area * gamma
    return AreaComposition(raw, public_outer_area(raw))


def compute_ua(*, public_overall_u: Decimal, public_outer_area_value: Decimal) -> UAComposition:
    raw = public_overall_u * public_outer_area_value
    return UAComposition(raw, public_ua(raw))


def build_thermal_resistance_ledger(
    *,
    task026_transform_hash: str,
    task037_transform_hash: str,
    r01: Decimal,
    r02: Decimal,
    r03: Decimal,
    r04: Decimal,
    r05: Decimal,
) -> tuple[ThermalResistanceLedgerRow, ...]:
    status = "PRESENT_APPLICABLE_COMPATIBLE"
    return (
        ThermalResistanceLedgerRow(
            "R01_TUBE_SIDE_FILM_OUTER_REFERENCE",
            "TASK026",
            "TASK026.tube_side_heat_transfer_coefficient_w_m2_k",
            "INNER_TUBE_SURFACE",
            OVERALL_U_REFERENCE_SURFACE,
            task026_transform_hash,
            r01,
            status,
        ),
        ThermalResistanceLedgerRow(
            "R02_INSIDE_FOULING_OUTER_REFERENCE",
            "TASK037",
            "TASK037.inside_fouling_authority.fouling_resistance_m2_k_w",
            "INNER_TUBE_SURFACE",
            OVERALL_U_REFERENCE_SURFACE,
            task037_transform_hash,
            r02,
            status,
        ),
        ThermalResistanceLedgerRow(
            "R03_TUBE_WALL_CONDUCTION_OUTER_REFERENCE",
            "TASK037",
            "TASK037.wall_resistance_outer_surface_m2_k_w",
            OVERALL_U_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            None,
            r03,
            status,
        ),
        ThermalResistanceLedgerRow(
            "R04_OUTSIDE_FOULING_OUTER_REFERENCE",
            "TASK037",
            "TASK037.outside_fouling_authority.fouling_resistance_m2_k_w",
            OVERALL_U_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            None,
            r04,
            status,
        ),
        ThermalResistanceLedgerRow(
            "R05_SHELL_SIDE_FILM_OUTER_REFERENCE",
            "TASK035",
            "TASK035.modeled_shell_side_heat_transfer_coefficient_w_m2_k",
            OVERALL_U_REFERENCE_SURFACE,
            OVERALL_U_REFERENCE_SURFACE,
            None,
            r05,
            status,
        ),
    )


def gv01() -> tuple[ResistanceComposition, AreaComposition, UAComposition]:
    resistance = compute_resistance_composition(
        gamma=GV01_GAMMA,
        h_i=GV01_H_I,
        h_o=GV01_H_O,
        inside_fouling=GV01_R_FI_I,
        wall_resistance=GV01_R_W_O,
        outside_fouling=GV01_R_FO_O,
    )
    area = AreaComposition(GV01_PUBLIC_A_O, GV01_PUBLIC_A_O)
    ua = UAComposition(GV01_PUBLIC_UA, GV01_PUBLIC_UA)
    return resistance, area, ua


__all__ = [
    "AreaComposition",
    "ResistanceComposition",
    "UAComposition",
    "build_thermal_resistance_ledger",
    "compute_outer_area",
    "compute_resistance_composition",
    "compute_ua",
    "gv01",
    "TASK038_OUTER_AREA_QUANTUM_M2",
    "TASK038_OVERALL_U_QUANTUM_W_M2_K",
    "TASK038_UA_QUANTUM_W_K",
    "ROUNDING_MODE",
]
