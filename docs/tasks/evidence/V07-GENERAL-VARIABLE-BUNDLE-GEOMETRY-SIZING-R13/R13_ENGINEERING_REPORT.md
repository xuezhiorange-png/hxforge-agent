# R13 Variable bundle geometry sizing — mvp-variable-bundle-r13

## Geometry freedom

- Dimension: **shell inside diameter** → Task021 tube count and Task025 flow area
- C3 reference binding: **False**
- Applicability: **NOT_C3_REFERENCE**

## P0 — R12 2.5 m / 0.5 m Task174 blocker (C3 reference case)

- Task174 status: **BLOCKED**
- Physical tube count at blocker: **253**
- Interpretation: Task174 reference hydraulic preview blocked because candidate outlet pressures left the CoolProp water-property domain (100000–101325 Pa). This is not a silent override of Task174 validation.

## Search policy

- Selection mode: **VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13**
- Selection reason: `VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13`
- Task174-ready in space: **14**
- Live n=1 ratings this run: **2**

## Live-rated candidates (this run)

- `ce66b1a2-1f75-5901-bd7f-6a9ee5cd3cfe`: shell ID 0.54 m, N=313, L=3.0 m, area 56.196652307781537694350 m², duty 32328.8461907676175 W, mesh NUMERIC_VALID, Task025 A_flow 0.0609811114 m²
  - constraints: duty SATISFIED, tube Δp SATISFIED, shell Δp NOT_SATISFIED
- `a409a550-4d1d-5b71-b3f5-0f1b665e2fe5`: shell ID 0.56 m, N=337, L=3.0 m, area 60.505660791445297773150 m², duty 32528.427903428549 W, mesh NUMERIC_VALID, Task025 A_flow 0.0656569794 m²
  - constraints: duty SATISFIED, tube Δp SATISFIED, shell Δp SATISFIED

## Evaluated-set sizing decision

- Target constraint status: **PRELIMINARY_CONSTRAINT_SATISFIED_IN_EVALUATED_SET**
- Best evaluated candidate: `a409a550-4d1d-5b71-b3f5-0f1b665e2fe5`
- Target duty: 9500 W
- Duty overshoot ratio: 3.424045042466163052631578947
- Hydraulic scope: **HYDRAULIC_REFERENCE_MODEL_PREVIEW**

## Engineering conclusion

Variable shell diameter changed physical tube count and hydraulic inputs, but the lowest live-rated duty (32328.8461907676175 W) remains far above the 9500 W target under current single-phase Bell–Delaware / Task172 closure without C3 reference scaling. Further reduction likely needs additional discrete freedoms (e.g. fewer tubes via smaller shell within layout rules, different tube OD/pitch authority, or partial duty / multi-pass strategies) rather than duty scaling.

## Not production approved

- full_rating_converged: false
- production_sizing_verified: false
