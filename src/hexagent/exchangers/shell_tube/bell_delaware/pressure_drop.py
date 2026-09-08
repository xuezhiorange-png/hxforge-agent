"""Bell--Delaware pressure-drop relations (Gonçalves equations 55--73)."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, localcontext
from typing import Any

from .authority import PRIMARY_IMPLEMENTATION_SOURCE_ID, PRIMARY_SOURCE_LOCATION
from .decimal_math import ONE, ZERO, engineering_context, evaluate_exp, power, sqrt
from .errors import BellDelawareFailure, BlockerCode
from .heat_transfer import _row_index
from .models import BellGeometry, FactorEvidence, PressureDropCalculation
from .schema import decimal_value

_B_TABLE: dict[str, tuple[tuple[Decimal, Decimal, Decimal, Decimal], ...]] = {
    "LAYOUT_30_DEG": (
        (Decimal("48.000"), Decimal("-1.000"), Decimal("7.00"), Decimal("0.500")),
        (Decimal("45.100"), Decimal("-0.973"), Decimal("7.00"), Decimal("0.500")),
        (Decimal("4.570"), Decimal("-0.476"), Decimal("7.00"), Decimal("0.500")),
        (Decimal("0.486"), Decimal("-0.152"), Decimal("7.00"), Decimal("0.500")),
        (Decimal("0.372"), Decimal("-0.123"), Decimal("7.00"), Decimal("0.500")),
    ),
    "LAYOUT_45_DEG": (
        (Decimal("32.000"), Decimal("-1.000"), Decimal("6.59"), Decimal("0.520")),
        (Decimal("26.200"), Decimal("-0.913"), Decimal("6.59"), Decimal("0.520")),
        (Decimal("3.500"), Decimal("-0.476"), Decimal("6.59"), Decimal("0.520")),
        (Decimal("0.333"), Decimal("-0.136"), Decimal("6.59"), Decimal("0.520")),
        (Decimal("0.303"), Decimal("-0.126"), Decimal("6.59"), Decimal("0.520")),
    ),
    "LAYOUT_90_DEG": (
        (Decimal("35.000"), Decimal("-1.000"), Decimal("6.30"), Decimal("0.378")),
        (Decimal("32.100"), Decimal("-0.963"), Decimal("6.30"), Decimal("0.378")),
        (Decimal("6.090"), Decimal("-0.602"), Decimal("6.30"), Decimal("0.378")),
        (Decimal("0.0815"), Decimal("0.022"), Decimal("6.30"), Decimal("0.378")),
        (Decimal("0.391"), Decimal("-0.148"), Decimal("6.30"), Decimal("0.378")),
    ),
}


def _value(flow: Mapping[str, Any], *names: str) -> Decimal:
    for name in names:
        if name in flow:
            try:
                return decimal_value(flow[name], name)
            except Exception as exc:
                raise BellDelawareFailure(BlockerCode.REQUIRED_PROPERTY_MISSING, name) from exc
    raise BellDelawareFailure(BlockerCode.REQUIRED_PROPERTY_MISSING, names[0])


def _evidence(
    factor_id: str,
    value: Decimal,
    source_id: str,
    location: str,
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


def calculate_pressure_drop(
    geometry: BellGeometry,
    flow: Mapping[str, Any],
) -> PressureDropCalculation:
    reynolds = _value(flow, "shell_side_reynolds_number", "reynolds_number", "Re_s")
    row_index, row = _row_index(reynolds)
    mass_flow = _value(flow, "shell_side_mass_flow_rate_kg_s", "mass_flow_rate_kg_s", "m_c")
    density = _value(flow, "density_kg_m3", "shell_side_density_kg_m3", "rho_s")
    viscosity = _value(flow, "dynamic_viscosity_pa_s", "shell_side_dynamic_viscosity_pa_s", "mu_s")
    try:
        b1, b2, b3, b4 = _B_TABLE[geometry.layout_angle][row_index]
    except (KeyError, IndexError) as exc:
        raise BellDelawareFailure(BlockerCode.INVALID_PARAMETER_ROW, geometry.layout_angle) from exc
    if any(value <= ZERO or not value.is_finite() for value in (mass_flow, density, viscosity)):
        raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "pressure_drop.flow")
    with localcontext(engineering_context()):
        reynolds = _value(flow, "shell_side_reynolds_number", "reynolds_number", "Re_s")
        pitch_ratio = geometry.tube_pitch_m / geometry.tube_outer_diameter_m
        exponent_b = b3 / (ONE + Decimal("0.14") * power(reynolds, b4))
        friction_factor = (
            b1 * power(Decimal("1.33") / pitch_ratio, exponent_b) * power(reynolds, b2)
        )
        ideal_dp = (
            Decimal("2")
            * friction_factor
            * geometry.central_crossflow_tube_rows
            * (_value(flow, "shell_side_mass_velocity_kg_m2_s", "mass_velocity_kg_m2_s", "G_s"))
            ** Decimal("2")
            / density
        )
        c_bp = Decimal("4.5") if reynolds <= Decimal("100") else Decimal("3.7")
        r_b = evaluate_exp(-c_bp * geometry.bypass_area_ratio)
        exponent_p = -Decimal("0.15") * (ONE + geometry.shell_leakage_fraction) + Decimal("0.8")
        r_l = evaluate_exp(
            -Decimal("1.33")
            * (ONE + geometry.shell_leakage_fraction)
            * power(geometry.leakage_area_ratio, exponent_p)
        )
        n_spacing = ONE if reynolds < Decimal("100") else Decimal("0.2")
        r_s = power(
            geometry.central_baffle_spacing_m / geometry.outlet_baffle_spacing_m,
            Decimal("2") - n_spacing,
        ) + power(
            geometry.central_baffle_spacing_m / geometry.inlet_baffle_spacing_m,
            Decimal("2") - n_spacing,
        )
        crossflow_dp = ideal_dp * Decimal(geometry.baffle_count - 1) * r_b * r_l
        window_mass_velocity = mass_flow / sqrt(
            geometry.central_crossflow_flow_area_m2 * geometry.window_flow_area_m2
        )
        if reynolds < Decimal("100"):
            window_dp = (
                Decimal(geometry.baffle_count)
                * r_l
                * (
                    Decimal("26")
                    * window_mass_velocity
                    * viscosity
                    / density
                    * geometry.window_tube_rows
                    * (
                        geometry.tube_pitch_m
                        - geometry.tube_outer_diameter_m
                        + geometry.central_baffle_spacing_m
                    )
                    / (geometry.window_hydraulic_diameter_m ** Decimal("2"))
                    + Decimal("2") * window_mass_velocity * window_mass_velocity / density
                )
            )
        else:
            window_dp = (
                Decimal(geometry.baffle_count)
                * r_l
                * (Decimal("2") + Decimal("0.6") * geometry.window_tube_rows)
                * window_mass_velocity
                * window_mass_velocity
                / (Decimal("2") * density)
            )
        end_zone_dp = (
            ideal_dp
            * (ONE + geometry.window_tube_rows / geometry.central_crossflow_tube_rows)
            * r_b
            * r_s
        )
        total_dp = crossflow_dp + window_dp + end_zone_dp
        values = (ideal_dp, crossflow_dp, window_dp, end_zone_dp, r_l, r_b, r_s, total_dp)
        if any(not value.is_finite() or value < ZERO for value in values):
            raise BellDelawareFailure(BlockerCode.NONFINITE_ENGINEERING_RESULT, "pressure_drop")
        factors = (
            _evidence(
                "Rl",
                r_l,
                PRIMARY_IMPLEMENTATION_SOURCE_ID,
                PRIMARY_SOURCE_LOCATION,
                shell_leakage_fraction=geometry.shell_leakage_fraction,
                leakage_area_ratio=geometry.leakage_area_ratio,
            ),
            _evidence(
                "Rb",
                r_b,
                PRIMARY_IMPLEMENTATION_SOURCE_ID,
                PRIMARY_SOURCE_LOCATION,
                bypass_area_ratio=geometry.bypass_area_ratio,
                c_bp=c_bp,
            ),
            _evidence(
                "Rs",
                r_s,
                PRIMARY_IMPLEMENTATION_SOURCE_ID,
                PRIMARY_SOURCE_LOCATION,
                central_spacing=geometry.central_baffle_spacing_m,
                inlet_spacing=geometry.inlet_baffle_spacing_m,
                outlet_spacing=geometry.outlet_baffle_spacing_m,
                n=n_spacing,
                reynolds=reynolds,
            ),
        )
        return PressureDropCalculation(
            ideal_crossflow_pressure_drop=ideal_dp,
            crossflow_pressure_drop=crossflow_dp,
            window_pressure_drop=window_dp,
            end_zone_pressure_drop=end_zone_dp,
            r_l=r_l,
            r_b=r_b,
            r_s=r_s,
            total_shell_pressure_drop=total_dp,
            central_crossflow_contribution=crossflow_dp,
            window_contribution=window_dp,
            entrance_zone_contribution=end_zone_dp / Decimal("2"),
            exit_zone_contribution=end_zone_dp / Decimal("2"),
            parameter_row_identity=f"{geometry.layout_angle}:{row}",
            b1=b1,
            b2=b2,
            b3=b3,
            b4=b4,
            factor_evidence=factors,
        )


__all__ = ["calculate_pressure_drop"]
