# V08-06 P3 — Pre-registered kernel acceptance case (R1)

Status: `FROZEN_PRE_IMPLEMENTATION`  
Authority: V08 Charter §5 (P1–P3 independent non-reference cases)  
Date frozen: 2026-11-26 (UTC+8)

## Distinction from P1 and P2

| Case | Duty | Tube mdot (kg/s) | Shell mdot (kg/s) | Tin tube / shell (°C) | Δp tube / shell (kPa) |
|------|------|------------------|-------------------|------------------------|------------------------|
| P1 | 250 | **12** | **20** | 45 / 22 | 40 / 35 |
| P2 | 220 | **12** | **20** | 46 / 21 | 40 / 35 |
| **P3** | **275** | **11** | **19** | **44 / 23** | **40 / 35** |

P3 varies **duty**, **both mass flows**, and **temperature driving force** relative to P1/P2.

## Thermodynamic feasibility (independent justification)

Hot tube (44 °C, within V08 thermal-binding 290–320 K) vs cold shell (23 °C); positive driving force at declared flows. Target 275 kW is below single-phase enthalpy caps at 10/18 kg/s (order 1.0 MJ/s heat capacity).

## Geometry envelope

Same approved catalog envelope as P1/P2: `max_shell_inside_diameter_m=1.2`, `max_tube_length_m=6.0`.

## Expected physical behavior (qualitative)

Lowering shell flow and raising duty vs P2 increases approach temperature sensitivity and shell-side nozzle density span; ranking may differ from P1/P2 without reusing fixed candidate IDs.

## Tolerance basis

Kernel contract `V08_KERNEL_RATING_ACCEPTANCE_V1` (not retrofitted from Task173 failures).

## Catalog note (pre-run mesh check)

Initial pre-registration used 10 / 18 kg/s; Task168 manufacturable mesh under the approved envelope returned **zero** structural candidates (not OUT_OF_ENVELOPE ingestion). Spec amended to **11 / 19 kg/s** as the nearest distinct-flow pair still outside P1/P2 (12 / 20) with non-empty catalog enumeration — frozen before kernel matrix execution.

## Fixture

`tests/fixtures/v08_user_case_p3_kernel_acceptance_v1.json`  
Engineering case ID: `V08_06_P3_KERNEL_ACCEPTANCE_V1`