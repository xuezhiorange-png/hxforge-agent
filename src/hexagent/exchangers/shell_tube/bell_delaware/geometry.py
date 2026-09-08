"""Bell--Delaware geometry derived from accepted upstream geometry authority."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, localcontext
from typing import Any

from .decimal_math import ONE, PI, TWO, ZERO, acos, engineering_context, sin
from .errors import BellDelawareFailure, BlockerCode
from .models import BellGeometry
from .schema import decimal_value


def _raw(mapping: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    return None


def _required(mapping: Mapping[str, Any], path: str, *names: str) -> Any:
    value = _raw(mapping, *names)
    if value is None:
        raise BellDelawareFailure(BlockerCode.REQUIRED_GEOMETRY_MISSING, path)
    return value


def _decimal(mapping: Mapping[str, Any], path: str, *names: str) -> Decimal:
    value = _required(mapping, path, *names)
    try:
        return decimal_value(value, path)
    except Exception as exc:
        raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, path) from exc


def _nested_authority(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = mapping.get("design_authority")
    if type(nested) is dict:
        return nested
    return mapping


def _spacing_values(baffle: Mapping[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    central = _raw(baffle, "central_baffle_spacing_m", "central_inter_baffle_spacing_m", "Lbc")
    inlet = _raw(baffle, "inlet_baffle_spacing_m", "Lbi")
    outlet = _raw(baffle, "outlet_baffle_spacing_m", "Lbo")
    sequence = _raw(baffle, "spacing_sequence_m", "baffle_spacing_sequence_m")
    if central is None or inlet is None or outlet is None:
        if type(sequence) not in (tuple, list) or len(sequence) < 3:
            raise BellDelawareFailure(
                BlockerCode.REQUIRED_GEOMETRY_MISSING, "baffle_geometry.spacing"
            )
        if inlet is None:
            inlet = sequence[0]
        if outlet is None:
            outlet = sequence[-1]
        if central is None:
            central = sequence[1]
    try:
        return (
            decimal_value(inlet, "baffle_geometry.inlet_baffle_spacing_m"),
            decimal_value(central, "baffle_geometry.central_baffle_spacing_m"),
            decimal_value(outlet, "baffle_geometry.outlet_baffle_spacing_m"),
        )
    except Exception as exc:
        raise BellDelawareFailure(
            BlockerCode.INVALID_GEOMETRY_DOMAIN, "baffle_geometry.spacing"
        ) from exc


def _int_value(mapping: Mapping[str, Any], path: str, *names: str) -> int:
    value = _required(mapping, path, *names)
    if type(value) is int and type(value) is not bool:
        return value
    raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, path)


def derive_geometry(request: Any) -> BellGeometry:
    """Evaluate source equations 3--35 in their published dependency order."""
    bundle = request.shell_bundle_geometry
    layout = request.tube_layout
    baffle = _nested_authority(request.baffle_geometry)
    hydraulic = request.shell_side_hydraulic_geometry

    shell_diameter = _decimal(
        bundle,
        "shell_bundle_geometry.shell_inside_diameter_m",
        "shell_inside_diameter_m",
    )
    bundle_diameter = _decimal(
        bundle,
        "shell_bundle_geometry.bundle_outer_diameter_m",
        "bundle_outer_diameter_m",
        "bundle_outer_envelope_diameter_m",
        "bare_tube_bundle_diameter_m",
    )
    shell_bundle_clearance = _decimal(
        bundle,
        "shell_bundle_geometry.shell_to_bundle_diametral_clearance_m",
        "shell_to_bundle_diametral_clearance_m",
    )
    tube_od = _decimal(
        layout,
        "tube_layout.tube_outer_diameter_m",
        "tube_outer_diameter_m",
        "tube_od_m",
    )
    pitch = _decimal(layout, "tube_layout.tube_pitch_m", "tube_pitch_m", "pitch_m")
    tube_count = _decimal(
        layout,
        "tube_layout.tube_count",
        "tube_count",
        "total_tube_count",
        "Ntt",
    )
    layout_id_value = _required(layout, "tube_layout.layout_id", "layout_id", "result_id")
    if type(layout_id_value) is not str or not layout_id_value:
        raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "tube_layout.layout_id")
    layout_angle = _required(
        layout,
        "tube_layout.layout_angle",
        "layout_angle",
        "layout_angle_deg",
        "layout_family",
    )
    if type(layout_angle) is int:
        layout_angle = f"LAYOUT_{layout_angle}_DEG"
    if type(layout_angle) is not str:
        raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "tube_layout.layout_angle")
    if layout_angle in {"30", "30_DEG", "30°"}:
        layout_angle = "LAYOUT_30_DEG"
    elif layout_angle in {"45", "45_DEG", "45°"}:
        layout_angle = "LAYOUT_45_DEG"
    elif layout_angle in {"90", "90_DEG", "90°"}:
        layout_angle = "LAYOUT_90_DEG"
    elif layout_angle not in {"LAYOUT_30_DEG", "LAYOUT_45_DEG", "LAYOUT_90_DEG"}:
        raise BellDelawareFailure(BlockerCode.TUBE_LAYOUT_UNSUPPORTED, "tube_layout.layout_angle")

    baffle_cut = _decimal(
        baffle,
        "baffle_geometry.baffle_cut_fraction",
        "baffle_cut_fraction",
        "baffle_cut_ratio",
        "Bc",
    )
    baffle_count = _int_value(baffle, "baffle_geometry.baffle_count", "baffle_count", "Nb")
    inlet_spacing, central_spacing, outlet_spacing = _spacing_values(baffle)
    shell_baffle_clearance = _decimal(
        baffle,
        "baffle_geometry.shell_to_baffle_diametral_clearance_m",
        "shell_to_baffle_diametral_clearance_m",
        "shell_to_baffle_clearance_m",
        "Lsb",
    )
    tube_baffle_clearance = _decimal(
        baffle,
        "baffle_geometry.tube_to_baffle_hole_diametral_clearance_m",
        "tube_to_baffle_hole_diametral_clearance_m",
        "tube_to_baffle_clearance_m",
        "Ltb",
    )
    flow_area = _raw(hydraulic, "central_crossflow_flow_area_m2")

    values = (
        shell_diameter,
        bundle_diameter,
        shell_bundle_clearance,
        tube_od,
        pitch,
        tube_count,
        baffle_cut,
        inlet_spacing,
        central_spacing,
        outlet_spacing,
        shell_baffle_clearance,
        tube_baffle_clearance,
    )
    if any(not value.is_finite() for value in values):
        raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "geometry")
    if any(value <= ZERO for value in values[:6]) or any(value <= ZERO for value in values[7:]):
        raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "geometry")
    if pitch <= tube_od or not ZERO < baffle_cut < Decimal("0.5") or baffle_count < 2:
        raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "geometry.domain")
    if bundle_diameter >= shell_diameter or shell_bundle_clearance >= shell_diameter:
        raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "geometry.clearance")

    with localcontext(engineering_context()):
        d_ctl = shell_diameter - shell_bundle_clearance - tube_od
        d_otl = shell_diameter - shell_bundle_clearance
        if d_ctl <= ZERO or d_otl <= ZERO:
            raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "Dctl/Dotl")
        theta_ds = TWO * acos(ONE - TWO * baffle_cut)
        theta_ctl = TWO * acos((shell_diameter / d_ctl) * (ONE - TWO * baffle_cut))
        if theta_ctl <= ZERO or theta_ds <= ZERO or theta_ctl >= PI or theta_ds >= PI * TWO:
            raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "geometry.angles")
        if layout_angle == "LAYOUT_30_DEG":
            lpp = Decimal("0.866") * pitch
            effective_pitch = pitch
        elif layout_angle == "LAYOUT_45_DEG":
            lpp = Decimal("0.866") * pitch
            effective_pitch = Decimal("0.707") * pitch
        else:
            lpp = pitch
            effective_pitch = pitch
        if lpp <= ZERO:
            raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "Lpp")
        ntcc = shell_diameter / lpp * (ONE - TWO * baffle_cut)
        ntcw = Decimal("0.8") / lpp * (shell_diameter * baffle_cut - (shell_diameter - d_ctl) / TWO)
        nc = (ntcc + ntcw) * (Decimal(baffle_count) + ONE)
        fw = (theta_ctl - sin(theta_ctl)) / (TWO * PI)
        fc = ONE - TWO * fw
        sm = (central_spacing * (shell_bundle_clearance + d_ctl) / effective_pitch) * (
            pitch - tube_od
        )
        ntw = tube_count * fw
        swg = (
            PI
            / Decimal("4")
            * shell_diameter
            * shell_diameter
            * ((theta_ds - sin(theta_ds)) / (TWO * PI))
        )
        swt = ntw * PI / Decimal("4") * tube_od * tube_od
        sw = swg - swt
        ssb = PI * shell_diameter * shell_baffle_clearance / TWO * (ONE - theta_ds / (TWO * PI))
        stb = (
            tube_count
            * (ONE - fw)
            * PI
            / Decimal("4")
            * ((tube_od + tube_baffle_clearance) ** TWO - tube_od * tube_od)
        )
        # Gonçalves equation 26 sets Lpl=0 for the admitted model.
        sb = central_spacing * (shell_diameter - d_otl)
        if any(value <= ZERO for value in (ntcc, ntcw, nc, sm, sw, ssb, stb, sb, fc)):
            raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "derived_geometry")
        rs = ssb / (ssb + stb)
        rlm = (ssb + stb) / sm
        fsbp = sb / sm
        dw_denominator = PI * tube_od * ntw + PI * shell_diameter * theta_ds / (TWO * PI)
        if dw_denominator <= ZERO:
            raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "Dw")
        dw = Decimal("4") * sw / dw_denominator
        if dw <= ZERO:
            raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "Dw")
        # A supplied hydraulic-area value is evidence, not a replacement for
        # Bell equation 17.  When present it must agree within the public
        # upstream Decimal representation's declared calculation surface.
        if flow_area is not None:
            try:
                supplied = decimal_value(
                    flow_area, "shell_side_hydraulic_geometry.central_crossflow_flow_area_m2"
                )
            except Exception as exc:
                raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "flow_area") from exc
            if supplied <= ZERO:
                raise BellDelawareFailure(BlockerCode.INVALID_GEOMETRY_DOMAIN, "flow_area")
        return BellGeometry(
            shell_inside_diameter_m=shell_diameter,
            bundle_outer_diameter_m=bundle_diameter,
            tube_outer_diameter_m=tube_od,
            tube_pitch_m=pitch,
            baffle_cut_fraction=baffle_cut,
            baffle_count=baffle_count,
            central_baffle_spacing_m=central_spacing,
            inlet_baffle_spacing_m=inlet_spacing,
            outlet_baffle_spacing_m=outlet_spacing,
            shell_to_bundle_diametral_clearance_m=shell_bundle_clearance,
            shell_to_baffle_diametral_clearance_m=shell_baffle_clearance,
            tube_to_baffle_hole_diametral_clearance_m=tube_baffle_clearance,
            tube_count=tube_count,
            layout_id=layout_id_value,
            layout_angle=layout_angle,
            theta_ctl_rad=theta_ctl,
            theta_ds_rad=theta_ds,
            window_tube_fraction=fw,
            pure_crossflow_tube_fraction=fc,
            central_crossflow_tube_rows=ntcc,
            window_tube_rows=ntcw,
            total_crossflow_tube_rows=nc,
            window_tube_count=ntw,
            gross_window_flow_area_m2=swg,
            window_tube_area_m2=swt,
            central_crossflow_flow_area_m2=sm,
            window_flow_area_m2=sw,
            shell_to_baffle_leakage_area_m2=ssb,
            tube_to_baffle_leakage_area_m2=stb,
            total_leakage_area_m2=ssb + stb,
            bundle_bypass_area_m2=sb,
            shell_leakage_fraction=rs,
            leakage_area_ratio=rlm,
            bypass_area_ratio=fsbp,
            effective_tube_pitch_m=effective_pitch,
            window_hydraulic_diameter_m=dw,
            source_formula_ids=(
                "GONCALVES_2019_EQ3_EQ4",
                "GONCALVES_2019_EQ5_EQ35",
            ),
        )


__all__ = ["derive_geometry"]
