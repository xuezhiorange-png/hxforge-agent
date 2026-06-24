#!/usr/bin/env python3
"""
Case 2: Parallel-flow water-water double-pipe heat exchanger rating.

Independent reference derivation — does NOT import any hexagent modules.
Uses only CoolProp and standard library.

Geometry (same as Case 1):
  D_i      = 0.020 m  (inner tube inner diameter)
  D_o      = 0.025 m  (inner tube outer diameter)
  D_outer  = 0.040 m  (outer pipe inner diameter)
  L        = 3.0 m
  k_wall   = 50.0 W/(m·K)
  fouling  = 0 on both sides

Fluids (same as Case 1):
  Hot:  Water, m = 0.5 kg/s, T_in = 350 K, P_in = 200000 Pa (in tube)
  Cold: Water, m = 1.5 kg/s, T_in = 300 K, P_in = 150000 Pa (in annulus)

Flow arrangement: Parallel
"""

from __future__ import annotations

import hashlib
import json
import math
import os

import CoolProp.CoolProp as CP

# ====================================================================
# Geometry (matching production DoublePipeGeometry)
# ====================================================================

D_i = 0.020  # inner tube inner diameter [m]
D_o = 0.025  # inner tube outer diameter [m]
D_outer = 0.040  # outer pipe inner diameter [m]
L = 3.0  # effective length [m]
k_wall = 50.0  # wall thermal conductivity [W/(m·K)]

# Surface areas (production formulas)
area_inner = math.pi * D_i * L  # π × D_i × L
area_outer = math.pi * D_o * L  # π × D_o × L

# Flow areas
flow_area_tube = math.pi / 4.0 * D_i**2
flow_area_annulus = math.pi / 4.0 * (D_outer**2 - D_o**2)

# Hydraulic diameters
dh_tube = D_i  # = inner tube inner diameter
dh_annulus = D_outer - D_o  # production: D_outer - D_o

# Wall resistance (cylindrical)
R_wall = math.log(D_o / D_i) / (2.0 * math.pi * k_wall * L)


# ====================================================================
# Fluid properties from CoolProp
# ====================================================================

FLUID = "Water"

# Hot side (in tube)
m_hot = 0.5  # mass flow rate [kg/s]
T_hot_in = 350.0  # inlet temperature [K]
P_hot_in = 200000.0  # inlet pressure [Pa]

# Cold side (in annulus)
m_cold = 1.5
T_cold_in = 300.0
P_cold_in = 150000.0


def get_properties_TP(T: float, P: float) -> dict:
    """Get h, cp, mu, k, rho at given T, P from CoolProp."""
    h = CP.PropsSI("H", "T", T, "P", P, FLUID)
    cp = CP.PropsSI("Cpmass", "T", T, "P", P, FLUID)
    mu = CP.PropsSI("viscosity", "T", T, "P", P, FLUID)
    k_f = CP.PropsSI("conductivity", "T", T, "P", P, FLUID)
    rho = CP.PropsSI("D", "T", T, "P", P, FLUID)
    return {"h": h, "cp": cp, "mu": mu, "k": k_f, "rho": rho}


def get_temperature_PH(P: float, h: float) -> float:
    """Get T from P, h from CoolProp."""
    return CP.PropsSI("T", "P", P, "H", h, FLUID)


# ====================================================================
# Gnielinski correlation (matching production code)
# ====================================================================


def petukhov_friction_factor(Re: float) -> float:
    """f = (0.790 × ln(Re) - 1.64)^{-2}"""
    return (0.790 * math.log(Re) - 1.64) ** (-2)


def gnielinski_nusselt(Re: float, Pr: float) -> float:
    """Gnielinski correlation for turbulent flow.

    Nu = (f/8)(Re - 1000)Pr / [1 + 12.7 × √(f/8) × (Pr^{2/3} - 1)]

    Valid for Re in [3000, 5e6], Pr in [0.5, 2000].
    """
    f = petukhov_friction_factor(Re)
    f8 = f / 8.0
    numerator = f8 * (Re - 1000.0) * Pr
    denominator = 1.0 + 12.7 * math.sqrt(f8) * (Pr ** (2.0 / 3.0) - 1.0)
    return numerator / denominator


# ====================================================================
# Thermal resistance (matching production build_thermal_resistance)
# ====================================================================


def compute_thermal_resistance(
    h_inner: float,
    h_outer: float,
    area_inner_m2: float,
    area_outer_m2: float,
    R_wall_kw: float,
    fouling_inner_m2kw: float = 0.0,
    fouling_outer_m2kw: float = 0.0,
) -> dict:
    """Build thermal resistance network."""
    r_conv_inner = 1.0 / (h_inner * area_inner_m2)
    r_foul_inner = 0.0 if fouling_inner_m2kw == 0 else fouling_inner_m2kw / area_inner_m2
    r_conv_outer = 1.0 / (h_outer * area_outer_m2)
    r_foul_outer = 0.0 if fouling_outer_m2kw == 0 else fouling_outer_m2kw / area_outer_m2

    r_total = r_conv_inner + r_foul_inner + R_wall_kw + r_foul_outer + r_conv_outer
    ua = 1.0 / r_total

    return {
        "r_conv_inner": r_conv_inner,
        "r_foul_inner": r_foul_inner,
        "r_wall": R_wall_kw,
        "r_foul_outer": r_foul_outer,
        "r_conv_outer": r_conv_outer,
        "total_resistance": r_total,
        "ua_w_k": ua,
    }


# ====================================================================
# LMTD (matching production thermal.py)
# ====================================================================


def lmtd_counterflow(th_in: float, th_out: float, tc_in: float, tc_out: float) -> float:
    """Counterflow LMTD."""
    dt1 = th_in - tc_out
    dt2 = th_out - tc_in
    if dt1 <= 1e-10 or dt2 <= 1e-10:
        return float("nan")
    if abs(dt1 - dt2) < 1e-10:
        return (dt1 + dt2) / 2.0
    return (dt1 - dt2) / math.log(dt1 / dt2)


def lmtd_parallel(th_in: float, th_out: float, tc_in: float, tc_out: float) -> float:
    """Parallel-flow LMTD.

    ΔT1 = T_h,in - T_c,in
    ΔT2 = T_h,out - T_c,out
    """
    dt1 = th_in - tc_in
    dt2 = th_out - tc_out
    if dt1 <= 1e-10 or dt2 <= 1e-10:
        return float("nan")
    if abs(dt1 - dt2) < 1e-10:
        return (dt1 + dt2) / 2.0
    return (dt1 - dt2) / math.log(dt1 / dt2)


# ====================================================================
# Residual evaluation for a trial Q
# ====================================================================


def evaluate_residual(
    Q: float,
    h_hot_in: float,
    h_cold_in: float,
) -> dict:
    """Evaluate residual = Q - UA(Q) × LMTD(Q) for a trial Q."""
    # --- Trial outlet enthalpies ---
    h_hot_out = h_hot_in - Q / m_hot
    h_cold_out = h_cold_in + Q / m_cold

    # --- Outlet states from CoolProp (P, H) ---
    T_hot_out = get_temperature_PH(P_hot_in, h_hot_out)
    T_cold_out = get_temperature_PH(P_cold_in, h_cold_out)

    # --- Bulk temperatures ---
    T_bulk_hot = (T_hot_in + T_hot_out) / 2.0
    T_bulk_cold = (T_cold_in + T_cold_out) / 2.0

    # --- Bulk properties ---
    props_hot = get_properties_TP(T_bulk_hot, P_hot_in)
    props_cold = get_properties_TP(T_bulk_cold, P_cold_in)

    # --- Tube side (hot fluid in tube) ---
    v_tube = m_hot / (props_hot["rho"] * flow_area_tube)
    Re_tube = props_hot["rho"] * v_tube * dh_tube / props_hot["mu"]
    Pr_tube = props_hot["cp"] * props_hot["mu"] / props_hot["k"]
    Nu_tube = gnielinski_nusselt(Re_tube, Pr_tube)
    h_tube = Nu_tube * props_hot["k"] / dh_tube  # D_char = D_i

    # --- Annulus side (cold fluid in annulus) ---
    v_annulus = m_cold / (props_cold["rho"] * flow_area_annulus)
    Re_annulus = props_cold["rho"] * v_annulus * dh_annulus / props_cold["mu"]
    Pr_annulus = props_cold["cp"] * props_cold["mu"] / props_cold["k"]
    Nu_annulus = gnielinski_nusselt(Re_annulus, Pr_annulus)
    h_annulus = Nu_annulus * props_cold["k"] / dh_annulus  # D_char = D_h

    # --- Thermal resistance and UA ---
    R = compute_thermal_resistance(
        h_inner=h_tube,
        h_outer=h_annulus,
        area_inner_m2=area_inner,
        area_outer_m2=area_outer,
        R_wall_kw=R_wall,
    )
    UA = R["ua_w_k"]

    # --- LMTD (parallel) ---
    lmtd = lmtd_parallel(T_hot_in, T_hot_out, T_cold_in, T_cold_out)

    # --- Residual ---
    residual = Q - UA * lmtd

    return {
        "Q": Q,
        "T_hot_out": T_hot_out,
        "T_cold_out": T_cold_out,
        "T_bulk_hot": T_bulk_hot,
        "T_bulk_cold": T_bulk_cold,
        "UA": UA,
        "LMTD": lmtd,
        "residual": residual,
        "h_tube": h_tube,
        "h_annulus": h_annulus,
        "Re_tube": Re_tube,
        "Re_annulus": Re_annulus,
        "Pr_tube": Pr_tube,
        "Pr_annulus": Pr_annulus,
        "Nu_tube": Nu_tube,
        "Nu_annulus": Nu_annulus,
        "R": R,
    }


# ====================================================================
# Bisection solver
# ====================================================================


def bisect_solve(
    h_hot_in: float,
    h_cold_in: float,
    q_max: float,
    abs_tol: float = 1e-6,
    bracket_tol: float = 1e-6,
    max_iter: int = 100,
) -> dict:
    """Bisection solver for Q."""
    q_low = 0.0
    q_high = q_max

    r_low = evaluate_residual(q_low, h_hot_in, h_cold_in)["residual"]

    if abs(r_low) <= abs_tol:
        return evaluate_residual(0.0, h_hot_in, h_cold_in)

    # Probe to find bracket
    n_probes = 20
    step = q_high / n_probes
    r_prev = r_low
    q_prev = q_low

    for i in range(1, n_probes + 1):
        q_try = min(q_low + i * step, q_high)
        result = evaluate_residual(q_try, h_hot_in, h_cold_in)
        r_try = result["residual"]

        if r_prev * r_try < 0:
            q_low = q_prev
            q_high = q_try
            break
        r_prev = r_try
        q_prev = q_try
    else:
        raise RuntimeError("Could not find bracket for bisection")

    best_result = None
    best_residual = float("inf")

    for _ in range(max_iter):
        q_mid = (q_low + q_high) / 2.0
        result = evaluate_residual(q_mid, h_hot_in, h_cold_in)
        r_mid = result["residual"]

        if abs(r_mid) < abs(best_residual):
            best_residual = abs(r_mid)
            best_result = result

        if abs(r_mid) <= abs_tol and (q_high - q_low) <= bracket_tol:
            return result

        if r_mid * evaluate_residual(q_low, h_hot_in, h_cold_in)["residual"] < 0:
            q_high = q_mid
        else:
            q_low = q_mid

    return best_result


# ====================================================================
# Main
# ====================================================================


def main():
    print("=" * 70)
    print("Case 2: Parallel-flow water-water double-pipe rating")
    print("=" * 70)

    # Get inlet enthalpies
    props_hot_in = get_properties_TP(T_hot_in, P_hot_in)
    props_cold_in = get_properties_TP(T_cold_in, P_cold_in)
    h_hot_in = props_hot_in["h"]
    h_cold_in = props_cold_in["h"]

    print(f"\nHot inlet:  T = {T_hot_in} K, P = {P_hot_in} Pa, h = {h_hot_in:.2f} J/kg")
    print(f"Cold inlet: T = {T_cold_in} K, P = {P_cold_in} Pa, h = {h_cold_in:.2f} J/kg")

    # Estimate Q_max for parallel flow
    # For parallel flow, Q_max is limited by the exit pinch:
    # T_hot_out(Q) - T_cold_out(Q) >= minimum_terminal_delta_t
    # Use a conservative estimate based on independent limits
    T_hot_out_min = T_cold_in + 0.5
    h_hot_out_min = CP.PropsSI("H", "T", T_hot_out_min, "P", P_hot_in, FLUID)
    Q_hot_limit = m_hot * (h_hot_in - h_hot_out_min)

    T_cold_out_max = T_hot_in - 0.5
    h_cold_out_max = CP.PropsSI("H", "T", T_cold_out_max, "P", P_cold_in, FLUID)
    Q_cold_limit = m_cold * (h_cold_out_max - h_cold_in)

    # For parallel flow, the exit pinch is the binding constraint
    # but as a practical upper bound, use min of independent limits
    q_max = min(Q_hot_limit, Q_cold_limit)
    print(f"\nQ_hot_limit = {Q_hot_limit:.2f} W")
    print(f"Q_cold_limit = {Q_cold_limit:.2f} W")
    print(f"Q_max = {q_max:.2f} W")

    # Solve
    result = bisect_solve(h_hot_in, h_cold_in, q_max)

    print(f"\n{'=' * 70}")
    print("RESULTS")
    print(f"{'=' * 70}")
    print(f"  Q           = {result['Q']:.6f} W")
    print(f"  T_hot_out   = {result['T_hot_out']:.6f} K")
    print(f"  T_cold_out  = {result['T_cold_out']:.6f} K")
    print(f"  UA          = {result['UA']:.6f} W/K")
    print(f"  LMTD        = {result['LMTD']:.6f} K")
    print(f"  Residual    = {result['residual']:.6e} W")
    print(f"  h_inner     = {result['h_tube']:.6f} W/(m²·K)")
    print(f"  h_outer     = {result['h_annulus']:.6f} W/(m²·K)")
    print(f"  Re_inner    = {result['Re_tube']:.2f}")
    print(f"  Re_outer    = {result['Re_annulus']:.2f}")
    print(f"  Pr_inner    = {result['Pr_tube']:.6f}")
    print(f"  Pr_outer    = {result['Pr_annulus']:.6f}")
    print(f"  Nu_inner    = {result['Nu_tube']:.6f}")
    print(f"  Nu_outer    = {result['Nu_annulus']:.6f}")
    print(f"  R_conv_inner = {result['R']['r_conv_inner']:.6e} K/W")
    print(f"  R_wall       = {result['R']['r_wall']:.6e} K/W")
    print(f"  R_conv_outer = {result['R']['r_conv_outer']:.6e} K/W")
    print(f"  R_total      = {result['R']['total_resistance']:.6e} K/W")

    # Energy check
    Q_hot = m_hot * (h_hot_in - get_properties_TP(result["T_hot_out"], P_hot_in)["h"])
    Q_cold = m_cold * (get_properties_TP(result["T_cold_out"], P_cold_in)["h"] - h_cold_in)
    energy_residual = Q_hot - Q_cold
    print(f"\n  Energy check: Q_hot = {Q_hot:.6f} W, Q_cold = {Q_cold:.6f} W")
    print(f"  Energy residual = {energy_residual:.6e} W")

    # Build reference JSON
    reference_data = {
        "case": "case2_parallelflow",
        "description": "Parallel-flow water-water double-pipe heat exchanger",
        "geometry": {
            "D_i_m": D_i,
            "D_o_m": D_o,
            "D_outer_m": D_outer,
            "L_m": L,
            "k_wall_W_m_K": k_wall,
            "area_inner_m2": area_inner,
            "area_outer_m2": area_outer,
            "flow_area_tube_m2": flow_area_tube,
            "flow_area_annulus_m2": flow_area_annulus,
            "dh_tube_m": dh_tube,
            "dh_annulus_m": dh_annulus,
            "R_wall_K_W": R_wall,
        },
        "fluids": {
            "fluid": FLUID,
            "hot": {
                "side": "tube",
                "m_dot_kg_s": m_hot,
                "T_in_K": T_hot_in,
                "P_in_Pa": P_hot_in,
                "h_in_J_kg": h_hot_in,
            },
            "cold": {
                "side": "annulus",
                "m_dot_kg_s": m_cold,
                "T_in_K": T_cold_in,
                "P_in_Pa": P_cold_in,
                "h_in_J_kg": h_cold_in,
            },
        },
        "flow_arrangement": "parallel",
        "tube_in_hot": True,
        "results": {
            "Q_W": result["Q"],
            "T_hot_out_K": result["T_hot_out"],
            "T_cold_out_K": result["T_cold_out"],
            "UA_W_K": result["UA"],
            "LMTD_K": result["LMTD"],
            "ua_lmtd_residual_W": result["residual"],
            "energy_residual_W": energy_residual,
            "h_inner_W_m2_K": result["h_tube"],
            "h_outer_W_m2_K": result["h_annulus"],
            "Re_inner": result["Re_tube"],
            "Re_outer": result["Re_annulus"],
            "Pr_inner": result["Pr_tube"],
            "Pr_outer": result["Pr_annulus"],
            "Nu_inner": result["Nu_tube"],
            "Nu_outer": result["Nu_annulus"],
            "R_conv_inner_K_W": result["R"]["r_conv_inner"],
            "R_foul_inner_K_W": result["R"]["r_foul_inner"],
            "R_wall_K_W": result["R"]["r_wall"],
            "R_foul_outer_K_W": result["R"]["r_foul_outer"],
            "R_conv_outer_K_W": result["R"]["r_conv_outer"],
            "R_total_K_W": result["R"]["total_resistance"],
        },
        "reference": {
            "method": "Gnielinski correlation (Petukhov friction factor), bisection Q-solver",
            "source": "Independent derivation, independent of production kernel",
            "source_references": [
                "Gnielinski, V., Int. Chem. Eng., Vol. 16, No. 2, pp. 359-368, 1976",
                "Petukhov, B.S., Advances in Heat Transfer, Vol. 6, 1970",
            ],
            "derivation_file": "case2_parallelflow_reference.py",
            "independent_from_production_kernel": True,
        },
        "input_parameters": {
            "D_i_m": D_i,
            "D_o_m": D_o,
            "D_outer_m": D_outer,
            "L_m": L,
            "k_wall_W_m_K": k_wall,
            "m_hot_kg_s": m_hot,
            "T_hot_in_K": T_hot_in,
            "P_hot_in_Pa": P_hot_in,
            "m_cold_kg_s": m_cold,
            "T_cold_in_K": T_cold_in,
            "P_cold_in_Pa": P_cold_in,
        },
    }

    # Compute reference result hash
    result_str = json.dumps(reference_data["results"], sort_keys=True, default=str)
    ref_hash = hashlib.sha256(result_str.encode()).hexdigest()
    reference_data["reference"]["reference_result_hash"] = ref_hash

    # Write JSON
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "case2_reference_result.json")
    with open(json_path, "w") as f:
        json.dump(reference_data, f, indent=2, default=str)

    print(f"\nReference JSON written to: {json_path}")
    print(f"Reference result hash: {ref_hash}")


if __name__ == "__main__":
    main()
