# TASK172 R117 — Runtime Authority Materialization and Project Engineering Case Design

## Outcome

R117 materializes the exact R116-reviewed tube geometry, tube-layout rule, and shell/bundle rule as native-schema runtime snapshots, and defines a machine-readable project engineering case-design contract. It does not materialize or execute the case.

`CASE_DESIGN_ID=V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-DESIGN-R1` is a design-contract identity, not a `CASE_ID`. All case/configuration/geometry/topology/path/ownership identities remain unbound. Production mesh and reference-policy applicability remain unresolved.

## Predecessor and authority binding

The authorized predecessor was PR #283, OPEN + Draft, head `48eaf88d57830719d1ce851dbbe33b96fb1454cb`. R116's receipt identity and the R115 authority identities were independently replayed before materialization. R116 records an external independent PASS and freezes the exact R115 values under `REVIEWED_AUTHORITY`; R117 does not change those values or claim a new engineering approval.

The native runtime approval provenance is the R116 receipt `V07-T172-INTERNAL-GEOMETRY-AUTHORITY-REVIEW-R116`, timestamp `2026-09-26T07:07:31Z`. Tube geometry embeds that provenance in the TASK016 source binding. TASK021 and TASK022 rule snapshot schemas do not expose `approved_by` / `approved_at`; their unchanged native snapshots therefore remain schema-pure, while [the R117 provenance sidecar](evidence/TASK-172-r117-runtime-authority-approval-provenance-r1.json) binds each native snapshot hash to the R116 receipt and timestamp.

The reviewed values remain exactly those in R115/R116: tube OD `0.01905 m`, ID `0.01575 m`, wall `0.00165 m`, cross-section area `0.00009019512508456295703 m2`, flow area `0.000194827831907779506515625 m2`, hydraulic diameter `0.01575 m`; triangular layout pitch `0.0254 m`, edge clearance `0.003175 m`, center-on-lattice origin, primary axis X, and candidate limit 10000; bundle peripheral allowance and radial clearance minima `0.00635 m`, caller-supplied explicit shell authority, and position limit 10000. Internal-project source semantics and `NO_STANDARD_CLAIM` are preserved.

The TASK016 catalog contract stores dimensional fields as binary floating-point values. The catalog artifact preserves the exact reviewed decimal lexemes; when loaded by TASK016, the existing native model represents the two area fields as binary64 (`9.019512508456296e-05` and `0.00019482783190777952`). R117 neither changes those source lexemes nor describes the native float representation as decimal-exact. No production code was changed.

## Native validation boundary

- TASK016 loaded the approved geometry catalog and selected exactly one approved tube record; the TASK021 adapter built the approved tube snapshot and its native authority verifier passed.
- TASK021 parsed the approved layout-rule snapshot and its native snapshot hash was independently replayed. The full profile-to-configuration cross-binding requires a TASK020 configuration, which R117 is expressly forbidden to materialize; that consumer binding remains for the future native case stage.
- TASK022 parsed and verified the approved bundle-rule authority snapshot, including `INTERNAL_GENERIC`, `NO_STANDARD_CLAIM`, caller-supplied explicit shell mode, and the frozen numerical limits. No shell/bundle geometry request or geometry calculation was executed.
- The shared `hexagent.canonical_json.canonical_sha256` and native TASK016/TASK021/TASK022 hash functions are reused; no parallel canonicalization was introduced.

## Case design contract

The payload `evidence/TASK-172-project-engineering-reference-case-design-r1.json` fixes only the reviewed TASK171 scope: fixed tubesheet, E-shell, one shell pass, one declared straight-through tube pass, countercurrent, steady, single-phase, Newtonian, using `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1`. It marks every future input as authority-bound, profile-bound, explicit project design input, or required-but-unbound. No test, golden, benchmark, or external as-built case value is reused.

The future producer DAG is recorded as TASK020 configuration → TASK021 layout → TASK022 shell/bundle geometry → TASK024 baffle geometry → TASK025 area/active-tube/length geometry → TASK171 topology binding → case-bound TASK172 authority binding → production mesh admission → TASK172 runtime closure. R117 defines this order only; it does not execute any node after creating the three authority snapshots.

Inputs not established by R116—including case orientation/revision evidence, layout placement envelope and selected placement, shell inside diameter, case clearances, baffle design, accepted tube length/area request, operating streams/states, and case-bound material/property/correlation/numerical authorities—remain `UNBOUND`. Consequently there is no `CASE_ID`, configuration, case geometry, topology instance, flow-path mapping, compartment/ownership map, or production mesh profile.

## Non-actions and lifecycle

R117 establishes runtime authority snapshots and a case-design contract only. It does not execute TASK020, TASK021 layout enumeration, TASK022 geometry, TASK024 baffle geometry, TASK025 area/length geometry, TASK172 solve, TASK174 hydraulics, TASK173 rating/sizing, or TASK175 release acceptance. It creates no production mesh or reference policy and does not enable mesh admission. `READY_AUTHORIZED=false`, `MERGE_AUTHORIZED=false`, and `NO_STEP_IMPLIES_THE_NEXT=true`.

The local full-regression outcomes for R115, R116 final head, and R117 final head are recorded separately in the evidence. Exact-head GitHub CI is also a separate result and is bound only after the final R117 commit.

## Artifacts

- Approved TASK016 tube geometry catalog: `evidence/TASK-172-r117-approved-tube-geometry-catalog-r1.json`
- Approved TASK021 tube snapshot: `evidence/TASK-172-r117-approved-tube-geometry-runtime-snapshot-r1.json`
- Approved TASK021 layout snapshot: `evidence/TASK-172-r117-approved-tube-layout-rule-runtime-snapshot-r1.json`
- Approved TASK022 bundle-rule snapshot: `evidence/TASK-172-r117-approved-shell-bundle-rule-runtime-snapshot-r1.json`
- R116 approval provenance sidecar: `evidence/TASK-172-r117-runtime-authority-approval-provenance-r1.json`
- Case design input contract: `evidence/TASK-172-project-engineering-reference-case-design-r1.json`
- R117 receipt: `evidence/TASK-172-runtime-authority-materialization-and-project-engineering-case-design-r1.json`

Next gate, if every required validation succeeds: `R118_PROJECT_ENGINEERING_CASE_NATIVE_GEOMETRY_MATERIALIZATION_ONLY`. R117 stops here; it does not start R118.
