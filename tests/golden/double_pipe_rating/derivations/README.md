# Double-Pipe Rating Kernel — Hand-Calculation Reference Solutions

## Purpose

This directory contains **independently derived reference solutions** for the
double-pipe heat exchanger rating kernel. Each script performs a complete
rating calculation using hand-coded correlations and CoolProp for
thermophysical properties, without importing any `hexagent` modules. The
purpose is to provide a trustworthy, auditable cross-check against the
production rating kernel so that regressions or subtle algorithmic changes
can be detected.

## How to Run

```bash
# Run individual cases:
python case1_counterflow_reference.py
python case2_parallelflow_reference.py
python case3_variable_property_reference.py
```

Each script prints a structured summary (heat duty, outlet temperatures, UA,
LMTD, status) that can be compared against the golden-case JSON files in the
parent directory.

**Requirements:** Python 3.11+, CoolProp (via `pip install CoolProp`).

## Case Descriptions

### Case 1 — Counterflow Water-Water

| Parameter | Value |
|---|---|
| Inner tube inner diameter, D_i | 20 mm |
| Inner tube outer diameter, D_o | 25 mm |
| Outer pipe inner diameter, D_outer | 40 mm |
| Effective length, L | 3.0 m |
| Wall thermal conductivity | 50 W/(m·K) (carbon steel) |
| Surface roughness (inner & annulus) | 4.5 × 10⁻⁵ m |
| Inner fouling resistance | 0.0002 m²·K/W |
| Outer fouling resistance | 0.0002 m²·K/W |
| Hot fluid (tube side) | Water, 0.5 kg/s, inlet 350 K, 200 kPa |
| Cold fluid (annulus side) | Water, 1.5 kg/s, inlet 300 K, 150 kPa |
| Flow arrangement | **Counterflow** |
| Hot in tube | Yes |

### Case 2 — Parallel-Flow Water-Water

| Parameter | Value |
|---|---|
| Geometry | Identical to Case 1 |
| Hot fluid (tube side) | Water, 0.5 kg/s, inlet 350 K, 200 kPa |
| Cold fluid (annulus side) | Water, 1.5 kg/s, inlet 300 K, 150 kPa |
| Flow arrangement | **Parallel** |
| Hot in tube | Yes |

This case verifies that the kernel correctly distinguishes counterflow from
parallel-flow and produces a lower (or equal) heat duty than the
counterflow arrangement.

### Case 3 — Variable-Property Counterflow

| Parameter | Value |
|---|---|
| Inner tube inner diameter, D_i | 25 mm |
| Inner tube outer diameter, D_o | 32 mm |
| Outer pipe inner diameter, D_outer | 50 mm |
| Effective length, L | 5.0 m |
| Wall thermal conductivity | 16 W/(m·K) (stainless steel) |
| Surface roughness (inner & annulus) | 4.5 × 10⁻⁵ m |
| Inner fouling resistance | 0.0002 m²·K/W |
| Outer fouling resistance | 0.0002 m²·K/W |
| Hot fluid (tube side) | Water, 0.8 kg/s, inlet 360 K, 250 kPa |
| Cold fluid (annulus side) | Water, 2.0 kg/s, inlet 290 K, 200 kPa |
| Flow arrangement | **Counterflow** |
| Hot in tube | Yes |

This case exercises variable property evaluation across a wider temperature
range (290–360 K) with a larger LMTD, and uses stainless-steel wall
conductivity to test conduction resistance.

## Formulas Used

All reference scripts implement the same fundamental rating equations:

1. **Log-Mean Temperature Difference (LMTD)**

   For counterflow:
   ```
   ΔT_1 = T_h_in  − T_c_out
   ΔT_2 = T_h_out − T_c_in
   LMTD = (ΔT_1 − ΔT_2) / ln(ΔT_1 / ΔT_2)
   ```

   For parallel flow:
   ```
   ΔT_1 = T_h_in  − T_c_in
   ΔT_2 = T_h_out − T_c_out
   LMTD = (ΔT_1 − ΔT_2) / ln(ΔT_1 / ΔT_2)
   ```

2. **Energy Balance**

   ```
   Q = ṁ_h · Cp_h · (T_h_in − T_h_out) = ṁ_c · Cp_c · (T_c_out − T_c_in)
   ```

   Solved iteratively by bisection on `T_c_out` (or equivalently on the
   heat duty `Q`).

3. **Reynolds Number**

   Tube side:
   ```
   Re_tube = 4 · ṁ_h / (π · D_i · μ_h)
   ```

   Annulus side (hydraulic diameter):
   ```
   D_h_annulus = D_outer − D_o
   Re_annulus = ρ_c · V_c · D_h_annulus / μ_c
   ```

4. **Nusselt Number — Gnielinski Correlation**

   ```
   f = (0.790 · ln(Re) − 1.64)⁻²
   Nu = (f / 8) · (Re − 1000) · Pr / [1 + 12.7 · (f/8)^(1/2) · (Pr^(2/3) − 1)]
   ```

   Valid for `3000 ≤ Re ≤ 5 × 10⁶` and `0.5 ≤ Pr ≤ 2000`.

   For the annulus, the Nusselt number is computed on the outer (wetted)
   surface with the hydraulic diameter.

5. **Convective Heat Transfer Coefficient**

   ```
   h = Nu · k_fluid / D_h
   ```

   where `D_h = D_i` for tube flow and `D_h = D_outer − D_o` for annulus flow.

6. **Overall Heat Transfer Coefficient (UA)**

   ```
   1/U = 1/h_i · (D_o / D_i) + D_o · ln(D_o / D_i) / (2 · k_wall)
         + 1/h_o + R_f,i · (D_o / D_i) + R_f,o
   ```

   where `R_f,i` and `R_f,o` are inner and outer fouling resistances.

7. **Heat Duty**

   ```
   Q = U · A_s · F · LMTD
   ```

   where `A_s = π · D_o · L` is the outer-tube surface area and `F = 1.0`
   (single-pass counterflow or parallel flow — no correction factor).

8. **Bulk Temperature Approximation**

   ```
   T_bulk = (T_in + T_out) / 2
   ```

   Properties (`μ`, `k`, `ρ`, `Cp`, `Pr`) are evaluated at the bulk
   temperature of each stream via CoolProp.

## Error Sources

The following sources of discrepancy between these reference scripts and the
production kernel are **known and documented**:

| # | Source | Effect |
|---|---|---|
| 1 | **CoolProp backend differences** | Different CoolProp backends (HEOS vs TTSE) or reference-state conventions can yield slightly different property values at the same state point. This is typically < 0.5 % in density, viscosity, and thermal conductivity for water. |
| 2 | **Bisection convergence tolerance** | The reference scripts use a bisection solver with a tolerance of 1 × 10⁻⁶ K on outlet temperature. The production kernel may use a different tolerance or solver, causing small differences in the converged result. |
| 3 | **Bulk temperature approximation** | The reference computes `T_bulk = (T_in + T_out) / 2` and evaluates properties at this single point. The production kernel may iterate on local or film temperatures, or use a multi-zone approach, leading to different property evaluations. |
| 4 | **Gnielinski correlation valid range** | The Gnielinski correlation is recommended for `3000 ≤ Re ≤ 5 × 10⁶`. If flow conditions approach the transition regime (`Re ≈ 2300`), extrapolation beyond the correlation's valid range may occur. The reference does not add a separate transition-regime model. |
| 5 | **Fouling resistance consistency** | Both reference scripts and production kernel now use the same fouling resistances from the geometry specification (`R_f,i = R_f,o = 0.0002 m²·K/W`). Any remaining differences come from property evaluation or correlation selection, not fouling. |
| 6 | **Wall conduction model** | The reference uses a simple steady-state cylindrical conduction formula. The production kernel may include additional wall thermal capacitance effects or non-ideal contact resistance. |
| 7 | **Annulus heat transfer coefficient** | The reference computes the annulus Nusselt number using the standard hydraulic-diameter approach. The production kernel may apply Gnielinski with annulus-specific correction factors or use a different hydraulic diameter definition. |

## Independence Statement

**These scripts do NOT import any `hexagent` modules.** They are
deliberately self-contained: all geometry handling, correlation
implementations, and solver logic are written from scratch using only
`CoolProp` for thermophysical properties. This ensures a truly independent
verification path.

The only external dependency is `CoolProp` (via `import CoolProp`), which is
also used by the production kernel but through the `hexagent` property
provider layer.
