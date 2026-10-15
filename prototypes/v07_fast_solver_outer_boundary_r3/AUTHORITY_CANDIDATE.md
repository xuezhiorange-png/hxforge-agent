# V07-FAST-SOLVER-OUTER-BOUNDARY-R3

Experimental outer shooting-enthalpy solve using production
`_solve_outer_boundary_from_trial` state machine and `_terminal_tolerance_pass`,
with **R2** `fast_valid_trajectory` mesh marches inside each trial.

Does **not** emit production R2A certificates or Candidate Rating result hashes.
Does not replace `OUTER_BOUNDARY_SOLVER_AUTHORITY_ID` or Candidate transient R2A path.
