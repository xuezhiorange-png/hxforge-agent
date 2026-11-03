# TASK172 R118-A — E-Shell Topology Binding Correction R1

## Result and scope

This append-only correction fixes one reviewed-profile binding in the still-unreviewed R118-A candidate. The projected TASK020 `shell_token` is now `E`, because the case is bound to reviewed topology profile `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1`, whose shell type is `E_SHELL`, and TASK171's native topology boundary requires `component_tokens.shell == "E"`.

The token is classified `ALREADY_BOUND_REVIEWED_PROFILE`, not an independent project engineering choice. This only expresses the already reviewed E-shell topology. It does not create or imply TEMA, ASME, vendor-equivalence, or other standard compliance. `front_head_token=T172_FRONT` and `rear_head_token=T172_REAR` are unchanged.

No engineering geometry value, authority scope, production code, native output, or lifecycle state is changed. R118-A remains `PROPOSED_AUTHORITY_REVIEW_PENDING`; independent review remains incomplete.

## Exact candidate correction

| Field | Before | After | Binding |
|---|---|---|---|
| `TASK020.shell_token` | `T172_SHELL` | `E` | `ALREADY_BOUND_REVIEWED_PROFILE` from `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1`; semantic binding `E_SHELL -> TASK020 native component_tokens.shell "E"` |

The same value is propagated into the candidate-only TASK014 revision payload and the projected future TASK020 request. The TASK014 candidate payload and domain-snapshot hashes are recomputed using the repository's `compute_payload_hash` and `compute_domain_snapshot_hash` functions. The projected TASK020 `CaseRevisionAuthority` binds those new hashes.

The matrix changes only the shell-token row's binding class and source/evidence reference. Project design input count decreases by one; reviewed-profile-bound input count increases by one. All geometry values, including the shell inside diameter, placement envelope, baffle inputs, tube lengths, and layout preflight values, are unchanged.

## Reviewed profile and native predicate linkage

Static source inspection binds the correction to:

- Reviewed profile: `docs/tasks/TASK-171-v0.7-segmented-thermal-state-topology-engine.md`, profile `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1`, reviewed document SHA256 `62d03bb1d95ee647870b62d2c5a8bafbff4df2fa215c6d282c379a4876311943`.
- Reviewed entry scope: `docs/tasks/TASK-170-v0.7-task171-entry-authority-r4.md`, review receipt `TASK170-R4-INDEPENDENT-ENTRY-REVIEW-R5`, SHA256 `ecf01cb2b019a7b43a4dd6241890893fb4238a0a11dec4a1c4e91d780c9e08ca`.
- Native required token: `src/hexagent/exchangers/shell_tube/segmented_thermal_state_topology/native.py`, SHA256 `ab2740ae9eb0f00d53f3bc5bff68dd6c15d6627872af93b6cd0fb4422934cf3e`; its replay rejects any shell component token other than `E` as `UNSUPPORTED_TOPOLOGY` at `shell_type`.
- Native profile constants: `src/hexagent/exchangers/shell_tube/segmented_thermal_state_topology/authority.py`, SHA256 `792caaaca1c70c7bc021dc211d6e2786ebcbc39d0a674700278f8aafb8da757f`.

This is `PASS_STATIC_REPLAY` only. TASK171 native replay was not executed because its required native TASK020–025 objects do not exist and their materialization is out of scope.

## Downstream hard-predicate compatibility audit

The reviewed profile scope and currently known hard predicates were compared statically across TASK020, TASK021, TASK022, TASK024, TASK025, and TASK171. The E-shell token now matches the TASK171 native precondition. The fixed-tubesheet, one-shell-pass, one-straight-through-tube-pass and countercurrent profile bindings remain consistent. The four candidate baffles exceed TASK171's two-baffle minimum. The candidate heat-transfer length and internal-flow length each remain 6 m, matching the unchanged 0–6 m active span. Existing prospective layout/bundle/baffle arithmetic remains unchanged. **Known downstream hard-predicate mismatch count: 0.** This audit does not execute any native result producer or grant downstream admission.

## TASK014 materialization boundary and next execution order

The R118-A TASK014 revision remains a candidate projection. Its `status_proposal_only="committed"` is only a future eligibility target; it is not persisted state:

```text
TASK014_REVISION_CANDIDATE_PRESENT=true
TASK014_NATIVE_CASE_REVISION_MATERIALIZED=false
TASK014_NATIVE_CASE_REVISION_COMMITTED=false
```

R118-C must first materialize and validate an accepted immutable TASK014 native case revision. Only then may TASK020 consume its `CaseRevisionAuthority`. The future order is:

```text
TASK014 native case revision
→ TASK020 configuration
→ TASK021 layout
→ TASK022 bundle geometry
→ TASK024 baffle geometry
→ TASK025 tube-side geometry
```

No stage in that chain is started by R118-A or this correction.

## Frozen boundary

R118-A remains candidate-only. TASK014, TASK020, TASK021, TASK022, TASK024, TASK025, and TASK171 native execution/materialization remain false; case/configuration/geometry identities remain `UNBOUND`; production mesh profile remains `UNBOUND`; real-case mesh admission remains false. No TASK172 runtime implementation, TASK174 solve, TASK173 solve, TASK175 release acceptance, Ready action, or Merge action is authorized.

The new receipt and registry extension append this finding without rewriting R1–R117 historical payloads, R118-A's previous correction extension, or any R115/R116 reviewed authority.

`NEXT_GATE=R118B_INPUT_AUTHORITY_INDEPENDENT_REVIEW_ONLY`
`STOP=true`
