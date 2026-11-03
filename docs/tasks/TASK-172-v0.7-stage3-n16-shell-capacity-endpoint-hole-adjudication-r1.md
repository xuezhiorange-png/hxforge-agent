# TASK172 Stage-3 N16 shell-capacity endpoint-hole adjudication R1

Task ID: `TASK172_V0_7_STAGE3_N16_SHELL_CAPACITY_ENDPOINT_HOLE_ADJUDICATION_R1`
Mode: `STAGE3_TARGETED_BOUNDARY_ADJUDICATION_ONLY`
Predecessor HEAD: `487bafe10257863ae9e6f3815748ad6ada62413e`

## Finding

The exact target was replayed through the corrected native shell-flow authority and production TASK173 trajectory: mesh `n=16`, outer iteration `2`, shell shooting enthalpy `106853.814770607445 J/kg`, support index `(3,16,0)`, axial interval `[3.600,3.675] m`.

The upper heat-rate bound is provably shell-capacity-bound. Recomputed from the target support's actual upstream face states:

| Quantity | Value |
| --- | ---: |
| `H_MIN` | `104920.11980926784 J/kg` |
| Tube upstream enthalpy | `109441.3576290475 J/kg` |
| Shell physical-left enthalpy | `104925.68955526012 J/kg` |
| Tube capacity | `54254.85383735592 W` |
| Shell capacity | `111.39491984560 W` |
| Raw minimum capacity | `111.39491984560 W` |
| Production `float(cap)` | `111.3949198456 W` |
| `nextafter` inward steps | `0` |

At that exact production `q_upper`, the propagated shell enthalpy is `104920.11980926784 J/kg`, exactly `H_MIN`; its distance to the lower domain boundary is zero. The tube downstream enthalpy remains `4511.9549097925266666666667 J/kg` above `H_MIN`. Thus `SHELL_CAPACITY_BINDING=true` is established by the production capacity arithmetic, not by visual temperature proximity.

TASK172 at the endpoint is a replay-valid `BLOCKED_RESIDUAL_ACCEPTANCE` hole (request hash `22be7911da59d0cfd54d922142570ad9f15b2dca2aeb36f415a9d3859ab16970`; blocked-result hash `16b34aac7500e1b661a520f6df5a30858b1d3b64b0ec27fcf346172e5e202ad5`). It contributes no `F(q)`, sign, or physical result.

## One-sided trajectory

The original 12 production recovery levels were replayed with matching request/result identities and retained unchanged in the predecessor evidence. All 12 were valid TASK172 results and all had negative `F(q)`; the level-12 value remains `F=-592.31714789397702 W` at `q=111.36772382024708 W`.

Diagnostic-only probes extended the same sequence through levels 13–24. All 12 additional points were valid native TASK172 results, with no new holes or other blockers. Every `F(q)` remained negative. At level 24, `q=111.39491320594539 W`, only `6.63965461e-6 W` below the endpoint, `F=-592.28988571763151 W`.

Ordinary least-squares one-sided intercept estimates, using only the latest valid points and `x=q_hole-q`, were:

| Fit points | Estimated intercept `L` (W) |
| ---: | ---: |
| 2 | `-592.28987903230860013756227558480703686842217574801778507566740711632466341099432` |
| 3 | `-592.28987908796365001781626661850288783125197840943379653726700798936843840884279` |
| 4 | `-592.28987907037435221746370053090495186481264836249603176305179491594704540672249` |
| 5 | `-592.28987906287654171242592323706193927811681468251293081598241176674026836765067` |
| 6 | `-592.28987906504704679469489814652294834867442274851813635497435625077264001064706` |

The estimate spread is approximately `5.5655049880253991e-8 W`. The adjudicated observed trend is `APPROACHING_FINITE_NEGATIVE_LIMIT`; the predecessor's derived label `APPROACHING_ZERO_SAME_SIGN` is superseded, while its raw samples remain valid and unchanged. These fits are diagnostic only: they are not TASK172 results, are not used as residual signs, and are not physical results. No global mathematical nonexistence theorem is claimed.

## Existing low-side semantics

With a valid upper TASK172 evaluation and `F(q_upper)<0`, the existing `_solve_cell()` branch observes the same shell-binding capacity and classifies `_LowSideDomainInfeasible`. For this target, the replayed valid interior points are all negative and no sign pair or eligible root was observed. The current trajectory instead cannot evaluate TASK172 at the upper endpoint and therefore ends as `BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED`.

The two paths differ in endpoint evaluability: `VALID_TASK172_RESULT` versus a residual-acceptance hole. The available discrete evidence supports equivalence with the existing low-side classification for this target. It does not authorize production classification changes in this task. A future correction, if separately authorized, must rely only on auditable discrete conditions: shell capacity binding; replay-valid residual-acceptance hole at the endpoint; exhaustion of the bounded authorized valid-point recovery; all valid recovery samples strictly negative; no adjacent valid sign pair; and no eligible valid root. It must never use blocked diagnostics or an extrapolated `F` value to classify the state.

## Wall-interface identity

The frozen target support was rebuilt using the native `build_local_support(3,16,0)` path. Its complete public projection and exact refined-ID input are recorded in the JSON evidence. Recomputing `canonical_sha256` over

```json
{"schema_version":"task172.real-case-refined-support-id.v1","kind":"wall-interface","mesh_level_identity":"c7cf7f75ccc837e8d375ff78242e6a7e51c74d463be0d0be51488c99ecbfa44a","physical_segment_id":"urn:hxforge:r119a:physical-segment:45e63641026ad06bba7d2ab1c7220b6f24d9d54d894eec3837f0188d70cbaf20","subdivision_index":0}
```

uniquely gives suffix `a0a32e756da8310ad90ab25f6483c6a31f052809b5c83917b44004bf644710a9`. The physical-support, tube-cell, and shell-cell identities also match the frozen target. Repository search found `a0a32a...` only in the predecessor failed-mesh evidence and subsequent historical discrepancy/supersession mentions; no native/authority producer or code emits it. Classification: `HISTORICAL_EVIDENCE_TRANSCRIPTION_DEFECT`. Historical files are not rewritten.

## Boundary and lifecycle

This is an adjudication only. Production solver decisions, probe order/depth/resource caps, TASK172 acceptance, R98 (`C_round=1.0`), TASK171, TASK174, and mesh policy are unchanged. The full production mesh was not run; `REAL_CASE_MESH_ADMISSIBLE=false`; no TASK173 result was created; TASK175 was not run. No self-approval is claimed.

The machine-readable evidence contains every diagnostic level and identity, capacity replay, semantic matrix, identity derivation, lifecycle flags, and canonical hash. Candidate exact-head CI and final-gate details will be recorded in PR metadata after the evidence-only candidate is pushed; the committed evidence itself is not modified after that exact-head CI run.

Next gate, contingent on evidence validation and exact-head CI: `STAGE3_ENDPOINT_HOLE_LOW_SIDE_CLASSIFICATION_AUTHORITY_AND_R3_CORRECTION`.
