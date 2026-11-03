# TASK172 R118-C R9 — Clean Native Geometry Materialization

Task: `TASK172_V0_7_R118C_R9_EXPLICIT_TASK025_PROJECTION_CLEAN_NATIVE_MATERIALIZATION_REPLAY_R1`

## Result

Run A and a separate clean Run B completed TASK014 → TASK020 → TASK021 → TASK022 → TASK024 → TASK025. All 87 matrix oracles passed; deterministic native identities and engineering outputs matched.

TASK025 returned the exact native `Task025ValidResult`. Its 27 public fields were written through a closed evidence-only projector. Native raw projections and the result, result ID, and two length hashes were replayed independently; the evidence projection did not participate in native identity computation.

## Materialized identities

- Case / root: `V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R1`
- TASK014 revision: `V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-DESIGN-R1-REV-1` (`committed`)
- TASK020 configuration: `96637b2b-3583-5fdd-8645-bb2b5526996a`
- TASK021 layout: `55b3085c-6a2a-5394-8617-7102e7eb66a8`
- TASK022 bundle geometry: `cbacec31-31fa-5e14-aa1b-be05e04b96dc`
- TASK024 baffle geometry: `279ed479-378d-5ea5-b2f0-8926133bf4dd`
- TASK025 result: `6ff54552-d44e-50d2-bdf2-fe5b766c6ff9`
- Aggregate `GEOMETRY_ID`: `UNBOUND` — no reviewed native aggregate-case geometry identity contract exists.

## Gates and boundaries

- Request-shape gates: 5/5 passed in each run.
- Run A: 60 static + 7 same-run dynamic passed; 20 replay baselines bound; 0 failures.
- Run B: 60 static + 7 same-run dynamic + 20 Run-A replay comparisons passed; 0 failures.
- Run-A/Run-B engineering identities and outputs: exact match; shared native object instances: 0.
- TASK025 evidence projection: 27 fields; Run A/Run B projections match; native hash/ID/length-hash replay passed.
- TASK171, production mesh admission, TASK172 runtime, TASK174, TASK173, TASK175, Ready, and merge were not performed or authorized.
- PR #283 remains Draft. Exact-final-head GitHub CI is required after the final evidence commit.

Machine-readable evidence and native stage snapshots are in `docs/tasks/evidence/` under the `r118c-r9` prefix.
