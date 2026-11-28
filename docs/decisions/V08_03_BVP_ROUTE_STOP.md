# V08-03 — BVP prototype route STOP

**Decision:** `NUMERICAL_DECISION=B`, `CURRENT_BVP_ROUTE=STOP`, `BVP_PHYSICAL_INFEASIBILITY_PROVEN=false`.

The Block Gauss–Seidel joint BVP in `prototypes/v08_thermal_rating/joint_boundary_value_axial_solver.py` remains as an **unaccepted historical experiment**. It does not enter the production Task173 path.

## Frozen cell0 evidence (not re-run)

- Production gate: **VALID** on candidate `9277ebb8-5b05-5130-8b90-92ee4768606b`
- `R1_RATIO≈449.5`, `R2_RATIO≈95.0`, `R3_RATIO≈352.1` on request hash `6eb035d2…`
- This is a **solver nonconvergence** finding, not proof of physical infeasibility of the exchanger geometry.

## Preserved isolated shooting baseline

| Mesh | Status |
|------|--------|
| N1 | ACCEPTED |
| N2 | ACCEPTED |
| N4 | BLOCKED |

Duty ~395 kW (experimental); tube Δp 1105.970 Pa; shell Δp 1177.102 Pa; nozzle UNRESOLVED.

## Next architecture work (separate authorization)

`TASK173_OUTER_ENTHALPY_NUMERICAL_REPRESENTATION` — shell-side enthalpy authority, P-H vs Decimal precision, unchanged Task172/C-ULP gates, N1/N2/N4 regression + V07 Golden.

Nozzle geometry binding and second hydraulic-feasible structure remain separate engineering items.