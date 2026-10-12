# Authority candidate: V07-FAST-SOLVER-COUPLED-CELL-R1

## Scope

Experimental mesh march that replaces production **cell-root bracketing × Task172
validate** with a **single coupled TRF solve** on `(q, T_wall_inner, T_wall_outer)` per
cell, using production `task172_local_runtime._eval_trial` residuals and production
`_cell_evaluation` for enthalpy propagation.

## Not production

- Does not replace `CELL_ROOT_SOLVER_AUTHORITY_ID` or Task172 R94/R98 Authority.
- `mesh_result_hash` and per-cell `task172_result_hash` may differ from production even
  when duty and outlet temperatures match within numerical noise (solver trajectory /
  metadata).
- Falls back to production `_solve_cell` on coupled failure.

## Promotion requirements

Independent numerical review, full Candidate B Rating replay, mesh-hash or documented
equivalence envelope, and explicit Authority adoption task.
