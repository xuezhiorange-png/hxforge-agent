# TASK172 v0.7 Stage 2 — TASK029 zero-component replay correction and hydraulic closeout

Task ID: `TASK172_V0_7_STAGE2_TASK029_ZERO_COMPONENT_REPLAY_CORRECTION_AND_FINAL_CLOSEOUT_R1`
PR: #283 (remains OPEN + DRAFT)
Predecessor HEAD: `6dd39fa77caab8f9a10879281021ba6bf7145c58`

## Outcome

`RESULT=STAGE2_COMPLETE`. The authorized R2 reference-case replay is valid through TASK172, TASK027, TASK028, TASK029, TASK166, and the corrected TASK174 orchestration. TASK173 and TASK175 were not run. Real-case mesh convergence and production mesh admission remain deferred to the integrated Stage-3 boundary solution.

## R2 case and TASK172 replay

The R2 case revision changes only tube-side mass flow from 10 to 12 kg/s to move the exact native tube Reynolds result out of TASK027's frozen unsupported transition interval. Shell flow remains 20 kg/s; temperatures, pressures, fluids, materials, wall, and mesh policy are unchanged. The 10 kg/s predecessor lies in the TASK027 unsupported gap; the native R2 TASK026/TASK027 replay gives `Re=4491.2103`, turbulent, and TASK172 validates the accepted Gnielinski/C3 tube branch.

Two independent TASK172 local calls produced the same native request/result identity and public result projection. The result is a local constitutive result only, not an exchanger outlet-temperature/rating solve.

## TASK028 and TASK029 compatibility correction

The TASK028 zero-component correction permits an explicitly empty `component_authorities` collection and a normally hashed `Task028SuccessResult` with `component_results=()`. It changes collection cardinality only: no formula, coefficient, source, or component schema changed; pseudo-zero components remain forbidden. TASK029's upstream replay now admits only an exact tuple (including the empty tuple) and still replays the ordinary TASK028 result hash and ID before trusting it. TASK029 continues to own modeled-path completeness and retains its non-empty bound-member rule.

The native composition has one TASK027 distributed-friction member, zero TASK028 members, and exact explicit exclusions. Its result is `COMPLETE_WITHIN_EXPLICIT_MODELED_BOUNDARY` for `TUBE_INTERNAL_FLOW_START_PLANE -> TUBE_INTERNAL_FLOW_END_PLANE`; `modeled_total_tube_side_pressure_drop_pa=436.958 Pa` is not a whole-exchanger nozzle-to-nozzle total.

## Detailed shell hydraulics and TASK174

TASK166 Bell–Delaware is the primary detailed shell model. TASK034 remains optional diagnostic-only and was not required or executed. The native Bell total is `695.60879452416523317091096373830961547685621804079 Pa`; central crossflow, window, inlet end-zone, and outlet end-zone terms reconcile exactly using native Decimal arithmetic. The 19 TASK171 physical events are allocated exactly once: 9 additive-region events and 10 correction/geometry-support events. Support events carry no standalone pressure-drop scalar.

With one-way frozen reference pressure at 101325 Pa, native TASK174 returns `VALIDATED`. Calculated outlet pressures are 100888.042 Pa on the tube path and 100629.39120547583476682908903626169038452314378196 Pa on the shell path, both within 100000–101325 Pa. FIV remains diagnostic-only; no numeric critical-velocity limit was guessed.

## Validation and boundaries

Focused TASK028/TASK029/TASK027/TASK172/TASK174 tests passed. The full shell-tube regression completed with one known environment-path-sensitive failure: `test_a01_no_upstream_repo_external_import` rejects this checkout path because it contains `/tmp`; the test was run, not deselected. Other reported skips are the repository's explicit trusted-dual-runtime/Python-version skips. Static checks, dependency checks, and exact-final-head CI are recorded in the final task receipt and PR checks.

No TASK173 solve or TASK175 release acceptance was performed. `TASK172_REAL_CASE_MESH_CONVERGENCE_EXECUTED=false`, `REAL_CASE_MESH_ADMISSIBLE=false`, reason `DEFERRED_TO_STAGE3_INTEGRATED_BOUNDARY_SOLUTION`. PR remains Draft; Ready and Merge remain unauthorized.

Machine-readable native run identities and authority bindings are in [the Stage-2 evidence record](evidence/TASK-172-stage2-task029-zero-component-replay-correction-r1.json).
