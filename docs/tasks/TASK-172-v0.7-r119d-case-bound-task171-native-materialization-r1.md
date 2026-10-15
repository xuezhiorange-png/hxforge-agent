# TASK172 R119-D — Case-Bound TASK171 Native Materialization

**Task ID:** TASK172_V0_7_R119D_CASE_BOUND_TASK171_NATIVE_MATERIALIZATION_R1
**Result:** CASE_BOUND_TASK171_NATIVE_MATERIALIZATION_COMPLETE
**Predecessor:** 3df4df347933688e38a27861916f15845ede0bbe
**Mode:** R119D_CASE_BOUND_TASK171_NATIVE_MATERIALIZATION_ONLY

R119-C explicitly selected Variant A (TUBE_HOT_SHELL_COLD): tube side HOT and shell side COLD. The selected definition source is docs/tasks/evidence/TASK-172-r119a-task171-definition-variant-a-r1.json, canonical hash 062f7110f5a9ac14ff0a5f9272008cef2682ba244d40ce9c7656863b44c0ffcc. Variant B remains REVIEWED_SELECTABLE_VARIANT_NOT_EFFECTIVE.

## Native materialization and replay

The existing native entry point hexagent.exchangers.shell_tube.segmented_thermal_state_topology.validate_request was invoked once in each of two independent Python processes. Both returned status=VALIDATED. Each run used the same effective Definition, R118-D-accepted TASK020/TASK021/TASK022/TASK024/TASK025 native identities, and typed request inputs reconstructed from the committed R9 snapshots. The native TASK171 implementation performs its own TASK024/TASK025 input replay; no separate direct TASK014–TASK025 execution was used to create these inputs.

- TASK171 topology_id: urn:hxforge:task171:98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7
- result_hash: 98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7
- mesh_identity: ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607
- physical_ownership_hash: 63ea9cb1d10037dde273fc40746d6cf98604a40e41d91705f640031e5b6ec7fe
- Native request projection canonical hash, Run A = Run B: 2acbbfe7f7d27bc1166f1220e081abcd38651bba5b94dae59ba0d8e4185acdb1
- Run A and Run B native Result projections are identical.
- Existing TASK171 canonical hash replay independently reproduced the returned topology, mesh, and physical-ownership identities in both runs.

The native result contains two path identities, five physical segments, ten numerical-cell identities, five wall-interface identities, nineteen physical-event identities and nineteen compartment identities. Its tube path references the accepted 253-position membership; shell membership is empty. The returned Definition is the native canonical projection of effective Variant A. The event inventory and source bindings match the reviewed TASK024 geometry.

The native Result emits topology_id, result_hash, mesh_identity and physical_ownership_hash. It does not emit a separate scalar topology_authority_id, request_hash or aggregate geometry_id. The returned Definition retains the reviewed TASK171 authority_ids tuple. No absent identity was fabricated. Thus TASK171 topology is now materially bound by the emitted native topology_id, while TOPOLOGY_AUTHORITY_ID is not a separate native output.

## Reused authorities and boundaries

The reviewed flow-path mapping, physical-compartment mapping, area ownership, length ownership and TASK171 structural-mesh authority IDs are unchanged. Canonical project-internal directions remain tube 0_TO_6 and shell 6_TO_0; they do not make a plant nozzle, nozzle-location or piping-arrangement claim.

Fluid identity remains unbound and PROPERTY_PROFILE_AUTHORITY_ID=UNBOUND. GEOMETRY_ID=UNBOUND because no reviewed native aggregate case-geometry identity contract exists. The TASK171 structural mesh identity is not production-mesh admission: PRODUCTION_MESH_PROFILE_AUTHORITY_ID=UNBOUND, reference-policy resolution is invalid, and REAL_CASE_MESH_ADMISSIBLE=false.

TASK172 runtime, TASK174, TASK173 and TASK175 were not invoked. No production code, existing tests, dependencies, workflows, engineering values, or R119-A/B/C artifacts were changed.

## Evidence and governance

Machine-readable replay evidence: docs/tasks/evidence/TASK-172-r119d-case-bound-task171-native-materialization-r1.json
Evidence file SHA-256: 03f2082284d7f56b0f3b1ec5661084427bbe02dd44c419b9be3fec67f7746dda
Evidence canonical hash: 7a76c7cc118c88a5ef7d1e40add66915e6b93190bfae15a31aee4687ab01e1af
Pre-R119-D registry root: 346cc4e29e1fb42bcb4e89cc5f27679f7eb4f16b7ec6d90b35563a35356a7d7d

The R119-D registry extension is append-only. Exact-final-head CI is required after commit and push; completion is not reported as PASS until that CI succeeds.

**Next gate:** R119E_CASE_BOUND_TASK171_NATIVE_MATERIALIZATION_INDEPENDENT_REVIEW_ONLY
**STOP=true**
