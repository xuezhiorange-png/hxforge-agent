# Design C — Experimental Prescreen Evidence (not manufacturing acceptance)

**Scheme C nozzles:** tube 123.80 mm, shell 159.00 mm (trial IDs, not standard series).

## Thermal (indicative ε-NTU)

- CLEAN Q = 330961.9 W; margin vs target = 961.9 W (~0.29% computational slack only — **not** verified thermal design margin).
- T039_DEMO fouling Q = 304206.3 W — **does not meet** 330 kW target.
- Task037 material/fouling authorities remain **experimental**.
- Task173 production thermal acceptance: **BLOCKED**.

## Hydraulics (R27B assumption full path + outlet COOLPROP_TP)

- Mid tube/shell Δp: 1084.785 / 972.4756310236445099858111598 Pa.
- High tube/shell Δp: 1198.676 / 1081.465631023644509985811160 Pa.
- Three K scenarios are **not** owner-verified; sensitivity only.

## High-K tube bound

NOZZLE_ONLY_HIGH_K_FEASIBILITY=INFEASIBLE_UNDER_ASSUMED_K

## Manufacturing gaps

- Standard nozzle effective ID, strength, and reinforcement: **UNRESOLVED**.
- Licensed plant fouling factors: **not approved**.

## Validator summary

- OUTLET_PROPERTY_CONSISTENCY: PASS
- FIXED_NOZZLE_OVERRIDE_CHECK: PASS
- FOUR_PORT_STRICT_VELOCITY: PASS