# TASK172 R119-A — Case-Bound TASK171 Definition Authority Candidate

Lifecycle: `PROPOSED_AUTHORITY_REVIEW_PENDING`. Candidate only; no self-approval.

R118-D independently accepted the native geometry materialization (receipt canonical hash `3a35df823adc4cfc2d6be8c1f56704d5b835e670f2848f6c380f5e368410353d`). Case/revision are `V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R1` / `V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-DESIGN-R1-REV-1`. Accepted TASK020–TASK025 identities are carried forward unchanged. `GEOMETRY_ID` remains `UNBOUND` because no reviewed aggregate identity contract exists.

The candidate binds `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1`, implementation `task171.v1`, receipt `TASK170-R4-INDEPENDENT-ENTRY-REVIEW-R5`, and the three reviewed authority IDs. The envelope is steady-state, single-phase, Newtonian, fixed-tubesheet, E-shell, one shell/tube pass, straight-through and countercurrent.

TASK024 boundaries are 0, 1.2, 2.4, 3.6, 4.8 and 6 m, yielding five physical intervals. Deterministic segment and compartment IDs bind CASE_ID and the accepted TASK024 geometry hash. Endpoint-derived lengths close exactly to 6 m. R9 TASK025 inside area is `75.1107679584 m²`; TASK037 `compute_outer_to_inner_area_ratio(Decimal("0.01575000"), Decimal("0.01905"))` returns `1.209523809523810`; derived outside area is `90.848262197302892909889504 m²`. Both area partitions close exactly. The area mapping is project-internal with `NO_STANDARD_CLAIM`.

The explicit mesh candidate has 5 tube cells, 5 shell cells, 10 total, and 5 wall interfaces. It is not a TASK171 default, standard requirement, or production mesh admission. Nineteen structural-reference events derive from the native four baffle planes; all events and state records remain unresolved. No Bell factors, leakage fractions, bypass flow, local row estimator, or thermodynamic state values are created.

Variant A maps tube hot/shell cold; Variant B maps tube cold/shell hot. Both preserve side-based path/stream IDs, tube 0→6 m and shell 6→0 m directions, 253 active tube positions, intervals, cells, area ownership, and event identities/support. They differ only in role labels and hot/cold wall-cell references. Neither is selected; hot/cold governance IDs and fluid identity remain unbound.

Strict public-model validation passes for both candidates. Static checks confirm 5 intervals, 2 paths, 253 positions, 10 cells, 5 walls, 19 events, exact area/length closure, and zero known hard-predicate mismatches. TASK171 native producer invocation count is 0. Independent R119-B review is required.

Next gate: `R119B_CASE_BOUND_TASK171_DEFINITION_AUTHORITY_INDEPENDENT_REVIEW_ONLY`.
