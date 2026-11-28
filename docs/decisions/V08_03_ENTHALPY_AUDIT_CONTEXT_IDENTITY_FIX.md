# V08-03 enthalpy audit context identity fix

## Root cause

`solve_isolated_outer_boundary()` resets the experimental thermal boundary after shooting. Prior enthalpy audits called `effective_shell_cold_inlet_enthalpy_j_kg()` and `trace_enthalpy_on_mesh_run()` **without** rebinding the 330 kW fixture, so Task173 fell back to the frozen **300 K / 298.15 K** defaults. That produced spurious ~13 MJ/kg shell inlet “authority” gaps versus the mesh faces computed under the correct case.

## Fix

All audit steps run inside `run_enthalpy_audit_body()` → `_run_with_rating_context()`. Missing or default-boundary contexts yield `AUDIT_CONTEXT_MISSING` / `AUDIT_CONTEXT_INVALID`; propagation defect is **`unresolved`**, not a confirmed enthalpy defect.

## Invariants

- **A:** Active boundary matches `HXFORGE_330KW_STRICT_DP` (310 / 295 K, 12 / 20 kg/s).
- **B:** `faces_shell[-1].enthalpy − authority` equals `observables.terminal_boundary_residual_j_kg`.
- **C:** Shell inlet TP→PH records real ΔT and ΔH (not “PH input equals output” only).

## N4 evidence rule

`AUDIT_CONTEXT_FIXED=true` does **not** imply Task173 numerical closure. If outer status remains `PRECISION_FLOOR`, set `N4_PRECISION_FLOOR_REMAINS=true`.