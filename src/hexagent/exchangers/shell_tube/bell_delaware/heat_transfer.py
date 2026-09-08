"""Bell--Delaware heat-transfer relations (Gonçalves equations 36--54)."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, localcontext
from typing import Any

from .authority import (
    JS_SOURCE_LOCATION,
    PRIMARY_IMPLEMENTATION_SOURCE_ID,
    PRIMARY_SOURCE_LOCATION,
    SAIF_TARIQ_JS_SOURCE_ID,
)
from .decimal_math import ONE, ZERO, engineering_context, evaluate_exp, power
from .errors import BellDelawareFailure, BlockerCode
from .models import BellGeometry, FactorEvidence, HeatTransferCalculation
from .schema import decimal_value

_ROWS: tuple[tuple[Decimal, Decimal, str], ...] = (
    (Decimal("0"), Decimal("10"), "RE_LT_10"),
    (Decimal("10"), Decimal("100"), "RE_10_TO_LT_100"),
    (Decimal("100"), Decimal("1000"), "RE_100_TO_LT_1000"),
    (Decimal("1000"), Decimal("10000"), "RE_1000_TO_LT_10000"),
    (Decimal("10000"), Decimal("100000"), "RE_10000_TO_100000"),
)

# Table A.1 of the admitted Jamil et al. accepted manuscript.  Each tuple is
# (a1, a2, a3, a4) or (b1, b2, b3, b4), selected by the explicit layout and Re
# row.  Values are entered as Decimal lexical values, never binary floats.
_A_TABLE: dict[str, tuple[tuple[Decimal, Decimal, Decimal, Decimal], ...]] = {
    "LAYOUT_30_DEG": (
        (Decimal("1.400"), Decimal("-0.667"), Decimal("1.450"), Decimal("0.519")),
        (Decimal("1.360"), Decimal("-0.657"), Decimal("1.450"), Decimal("0.519")),
        (Decimal("0.593"), Decimal("-0.477"), Decimal("1.450"), Decimal("0.519")),
        (Decimal("0.321"), Decimal("-0.388"), Decimal("1.450"), Decimal("0.519")),
        (Decimal("0.321"), Decimal("-0.388"), Decimal("1.450"), Decimal("0.519")),
    ),
    "LAYOUT_45_DEG": (
        (Decimal("1.550"), Decimal("-0.667"), Decimal("1.930"), Decimal("0.500")),
        (Decimal("0.498"), Decimal("-0.656"), Decimal("1.930"), Decimal("0.500")),
        (Decimal("0.730"), Decimal("-0.500"), Decimal("1.930"), Decimal("0.500")),
        (Decimal("0.370"), Decimal("-0.396"), Decimal("1.930"), Decimal("0.500")),
        (Decimal("0.370"), Decimal("-0.396"), Decimal("1.930"), Decimal("0.500")),
    ),
    "LAYOUT_90_DEG": (
        (Decimal("0.970"), Decimal("-0.667"), Decimal("1.187"), Decimal("0.370")),
        (Decimal("0.900"), Decimal("-0.631"), Decimal("1.187"), Decimal("0.370")),
        (Decimal("0.408"), Decimal("-0.460"), Decimal("1.187"), Decimal("0.370")),
        (Decimal("0.107"), Decimal("-0.266"), Decimal("1.187"), Decimal("0.370")),
        (Decimal("0.370"), Decimal("-0.395"), Decimal("1.187"), Decimal("0.370")),
    ),
}


def _row_index(reynolds: Decimal) -> tuple[int, str]:
    for index, (lower, upper, name) in enumerate(_ROWS):
        if lower <= reynolds < upper or (index == len(_ROWS) - 1 and reynolds == upper):
            return index, name
    raise BellDelawareFailure(BlockerCode.REYNOLDS_OUT_OF_RANGE, "shell_side_flow_state.reynolds")


def _inputs(flow: Mapping[str, Any]) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
    snapshot = flow.get("property_snapshot")
    property_map = snapshot if type(snapshot) is dict else flow
    names = (
        (("shell_side_reynolds_number", "reynolds_number", "Re_s"), flow),
        (("shell_side_prandtl_number", "prandtl_number", "Pr_s"), flow),
        (("shell_side_mass_velocity_kg_m2_s", "mass_velocity_kg_m2_s", "G_s"), flow),
        (("density_kg_m3", "shell_side_density_kg_m3", "rho_s"), property_map),
        (("dynamic_viscosity_pa_s", "shell_side_dynamic_viscosity_pa_s", "mu_s"), property_map),
    )
    values: list[Decimal] = []
    for aliases, source in names:
        value = next((source[name] for name in aliases if name in source), None)
        if value is None:
            raise BellDelawareFailure(BlockerCode.REQUIRED_PROPERTY_MISSING, aliases[0])
        try:
            values.append(decimal_value(value, aliases[0]))
        except Exception as exc:
            raise BellDelawareFailure(BlockerCode.REQUIRED_PROPERTY_MISSING, aliases[0]) from exc
    reynolds, prandtl, mass_velocity, density, viscosity = values
    if any(value <= ZERO for value in values) or any(not value.is_finite() for value in values):
        raise BellDelawareFailure(
            BlockerCode.INVALID_GEOMETRY_DOMAIN, "shell_side_flow_state.properties"
        )
    return reynolds, prandtl, mass_velocity, density, viscosity


def _evidence(
    factor_id: str,
    source_id: str,
    location: str,
    value: Decimal,
    **inputs: Decimal,
) -> FactorEvidence:
    return FactorEvidence(
        factor_id=factor_id,
        factor_version="v1",
        source_id=source_id,
        source_location=location,
        applicability=("TASK166_FIXED_GEOMETRY_BELL_DELAWARE",),
        input_projection=tuple(sorted((key, str(item)) for key, item in inputs.items())),
        value=value,
    )


def calculate_heat_transfer(
    geometry: BellGeometry,
    flow: Mapping[str, Any],
) -> HeatTransferCalculation:
    reynolds, prandtl, mass_velocity, _density, _viscosity = _inputs(flow)
    index, row = _row_index(reynolds)
    try:
        coefficients = _A_TABLE[geometry.layout_angle][index]
    except KeyError as exc:
        raise BellDelawareFailure(BlockerCode.INVALID_PARAMETER_ROW, geometry.layout_angle) from exc
    a1, a2, a3, a4 = coefficients
    with localcontext(engineering_context()):
        pitch_ratio = geometry.tube_pitch_m / geometry.tube_outer_diameter_m
        exponent_a = a3 / (ONE + Decimal("0.14") * power(reynolds, a4))
        ji = a1 * power(Decimal("1.33") / pitch_ratio, exponent_a) * power(reynolds, a2)
        pr_exponent = -(Decimal("2") / Decimal("3"))
        ideal_h = ji * flow_specific_heat(flow) * mass_velocity * power(prandtl, pr_exponent)
        j_c = Decimal("0.55") + Decimal("0.72") * geometry.window_tube_fraction
        j_l = Decimal("0.44") * (ONE - geometry.shell_leakage_fraction) + (
            ONE - Decimal("0.44") * (ONE - geometry.shell_leakage_fraction)
        ) * evaluate_exp(Decimal("-2.2") * geometry.leakage_area_ratio)
        c_bh = Decimal("1.35") if reynolds <= Decimal("100") else Decimal("1.25")
        j_b = evaluate_exp(-c_bh * geometry.bypass_area_ratio)
        n1 = Decimal("0.6") if reynolds >= Decimal("100") else Decimal("1") / Decimal("3")
        if (
            geometry.inlet_baffle_spacing_m == geometry.central_baffle_spacing_m
            and geometry.outlet_baffle_spacing_m == geometry.central_baffle_spacing_m
        ):
            j_s = ONE
        else:
            denominator = (
                Decimal(geometry.baffle_count - 1)
                + geometry.inlet_baffle_spacing_m / geometry.central_baffle_spacing_m
                + geometry.outlet_baffle_spacing_m / geometry.central_baffle_spacing_m
            )
            if denominator <= ZERO:
                raise BellDelawareFailure(BlockerCode.INVALID_CORRECTION_FACTOR, "Js.denominator")
            numerator = (
                Decimal(geometry.baffle_count - 1)
                + power(
                    geometry.inlet_baffle_spacing_m / geometry.central_baffle_spacing_m,
                    ONE - n1,
                )
                + power(
                    geometry.outlet_baffle_spacing_m / geometry.central_baffle_spacing_m,
                    ONE - n1,
                )
            )
            j_s = numerator / denominator
        jr1 = Decimal("10") / power(geometry.central_crossflow_tube_rows, Decimal("0.18"))
        if reynolds <= Decimal("20"):
            j_r = jr1
        elif reynolds <= Decimal("100"):
            j_r = jr1 + (Decimal("20") - reynolds) / Decimal("80") * (jr1 - ONE)
        else:
            j_r = ONE
        corrected_h = ideal_h * j_c * j_l * j_b * j_s * j_r
        factors = (
            _evidence(
                "Jc",
                PRIMARY_IMPLEMENTATION_SOURCE_ID,
                PRIMARY_SOURCE_LOCATION,
                j_c,
                baffle_cut_fraction=geometry.baffle_cut_fraction,
                pure_crossflow_tube_fraction=geometry.pure_crossflow_tube_fraction,
            ),
            _evidence(
                "Jl",
                PRIMARY_IMPLEMENTATION_SOURCE_ID,
                PRIMARY_SOURCE_LOCATION,
                j_l,
                shell_leakage_fraction=geometry.shell_leakage_fraction,
                leakage_area_ratio=geometry.leakage_area_ratio,
            ),
            _evidence(
                "Jb",
                PRIMARY_IMPLEMENTATION_SOURCE_ID,
                PRIMARY_SOURCE_LOCATION,
                j_b,
                bypass_area_ratio=geometry.bypass_area_ratio,
                c_bh=c_bh,
            ),
            _evidence(
                "Js",
                SAIF_TARIQ_JS_SOURCE_ID,
                JS_SOURCE_LOCATION,
                j_s,
                baffle_count=Decimal(geometry.baffle_count),
                inlet_spacing=geometry.inlet_baffle_spacing_m,
                central_spacing=geometry.central_baffle_spacing_m,
                outlet_spacing=geometry.outlet_baffle_spacing_m,
                n1=n1,
                reynolds=reynolds,
            ),
            _evidence(
                "Jr",
                PRIMARY_IMPLEMENTATION_SOURCE_ID,
                PRIMARY_SOURCE_LOCATION,
                j_r,
                total_crossflow_tube_rows=geometry.total_crossflow_tube_rows,
                reynolds=reynolds,
            ),
        )
        values = (ideal_h, j_c, j_l, j_b, j_s, j_r, corrected_h)
        if any(not value.is_finite() or value <= ZERO for value in values):
            raise BellDelawareFailure(BlockerCode.NONFINITE_ENGINEERING_RESULT, "heat_transfer")
        return HeatTransferCalculation(
            ideal_crossflow_heat_transfer_coefficient=ideal_h,
            j_c=j_c,
            j_l=j_l,
            j_b=j_b,
            j_s=j_s,
            j_r=j_r,
            corrected_shell_side_heat_transfer_coefficient=corrected_h,
            parameter_row_identity=f"{geometry.layout_angle}:{row}",
            a1=a1,
            a2=a2,
            a3=a3,
            a4=a4,
            factor_evidence=factors,
        )


def flow_specific_heat(flow: Mapping[str, Any]) -> Decimal:
    snapshot = flow.get("property_snapshot")
    property_map = snapshot if type(snapshot) is dict else flow
    for name in (
        "specific_heat_capacity_j_kg_k",
        "shell_side_specific_heat_capacity_j_kg_k",
        "cp_j_kg_k",
        "Cp_s",
    ):
        if name in property_map:
            value = decimal_value(property_map[name], name)
            if value > ZERO:
                return value
    raise BellDelawareFailure(
        BlockerCode.REQUIRED_PROPERTY_MISSING, "specific_heat_capacity_j_kg_k"
    )


def _window_crossflow_fraction(geometry: BellGeometry) -> Decimal:
    # Fw is recoverable from the source geometry areas and tube count.  Using
    # the ratio of effective window rows is the same fixed-geometry projection
    # already exposed by equations 15 and 23.
    if geometry.tube_count <= ZERO:
        raise BellDelawareFailure(BlockerCode.INVALID_CORRECTION_FACTOR, "Fw")
    return geometry.window_tube_fraction


__all__ = ["calculate_heat_transfer", "flow_specific_heat"]
