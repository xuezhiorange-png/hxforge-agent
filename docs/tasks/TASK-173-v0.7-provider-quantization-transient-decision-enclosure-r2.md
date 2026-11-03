# TASK173 Provider-Quantization Transient Decision Enclosure R2

## Disposition

```text
TASK_ID=STAGE3_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2_QUALIFICATION_R1
RESULT=PASS_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2_AUTHORITY_CANDIDATE
AUTHORITY_ID=V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R2
AUTHORITY_CANONICAL_HASH=a388f3ed8a59bc408f53f35a50f3741e44a0c5399b27ad5bf75234f0036981fa
AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
AUTHORITY_ACCEPTED=false
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
RUNTIME_SOURCE_HEAD=b1b9d676c693e09d740c47b642198b5e4f543409
RUNTIME_SOURCE_TREE=b0cfbdb7c4a9c3136fda317723fb5eab30c40e1e
RUNTIME_REBASELINE_V3_PROVENANCE_HASH=1f65fd736f4d5565d2f4a9037fabe8d9c48a7b0770ccb4414d86c7d82bb47574
```

R2 is a transient outer-boundary decision candidate only. It does not accept a
provider-quantized cell as a final physical solution. Ordinary point-root
acceptance remains `abs(F(q)) <= 1e-6 W`; accepted trajectories use exact valid
point roots only. Enclosure spans remain decision diagnostics/provenance and
are not added to accepted-cell floors, mesh floors, energy tolerance, or final
physical uncertainty. The R1 candidate and its independent-review failure are
unchanged historical records.

## Runtime baseline and validation repair

The runtime baseline was re-established at `b1b9d676c693e09d740c47b642198b5e4f543409`,
parented by the preserved snapshot `a655248bdd12b4790bab6c638e616ed502252f89`.
The validation-repair commit fixes only the two pre-existing sizing mypy sites
and registers the missing TASK173 sizing test in the shard manifest:

```text
VALIDATION_REPAIR_COMMIT=b1b9d676c693e09d740c47b642198b5e4f543409
MYPY_ERROR_COUNT_BEFORE=25
MYPY_ERROR_COUNT_AFTER=0
MANIFEST_D_EQ_M=PASS
MANIFEST_NEWLY_REGISTERED_PATH_COUNT=1
QUALIFICATION_RUNNER_SHA256=9b12f7fc83ecfa83a8fb47258cf97ca45c8d3f3261bbe5404929e17e405f3781
PREVIOUS_PASS_AUTHORITY_HASH=766c3cdd886f25b9e48d06bc5ae67cffcd5a67f8f6f1d2954735f9a94407ec6c
QUALIFICATION_MATRIX_HASH=f659ef3be2e2e0766af9a004dc131e468433ae46e94a0470fb49509ff675ef6d
HISTORICAL_BYTE_EQUIVALENCE=NOT_ESTABLISHED_AND_NOT_REQUIRED
```

The repair changed no runtime schema/canonical projection behavior. The frozen
R2 Sizing authority identities, TASK168/TASK169 identities, TASK174 grouped
reduction behavior, and reference TASK174 result identity remained unchanged.
The exact reference TASK174 result hash is
`ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419`.

After the first full R2 PASS, Ruff identified formatting-only changes needed in
the evidence qualification runner. Its raw-byte hash is authority-bound, so
the runner was formatted, the candidate canonical hash was recomputed, and all
five cases plus reference n=1 were rerun. The prior PASS is retained in the
machine evidence history; the fresh matrix hash remained identical. No R2
numerical predicate, candidate, or production source changed.

## Frozen cases and accepted n=1 trajectories

The five cases were not reselected. Each accepted trajectory was rerun with
provider enclosure disabled and has five `EXACT_VALID_POINT_ROOT` cells; no
accepted trajectory contains an enclosure. The full faces, cell/RatedCell
payloads, Task172 request/result projections, mesh projection, outer search,
terminal values, energy closure, wall extrema, and minimum approach are in the
machine evidence.

| Case | Cut | Candidate ID | Candidate hash | n=1 duty (W) | Transient events / certificates | Accepted enclosure count | Trajectory hash |
|---|---:|---|---|---:|---:|---:|---|
| TRAIN_A | 0.215 | `adeab5b1-a339-5eb3-aa66-011ffe49bac0` | `f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767` | 51992.108449169418 | 2 / 1 | 0 | `c865fabcd42658368fa3eb10a4e6edbd1124a1ba649dfc7cd650ae7bc7358843` |
| TRAIN_B | 0.220 | `e152cca9-fd5d-59ca-9b46-1df574eee841` | `53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489` | 51917.490892674400 | 6 / 3 | 0 | `b2e579624aae8a1a09a89c6236e3dc4ee40bf8aa952681ef884ee5f8ff179cfc` |
| H1 | 0.225 | `68a99368-a518-5482-b9df-4bc3357edea9` | `bd0da145a592652e55a6fc8cd325a98d6f1cf349ed74b98e811d1343ce62ed54` | 51840.916860226334 | 6 / 3 | 0 | `c76b049b491235066ed8ea8ae005c3e125b359b8fd8fc1dd91938c8ff1d1bf50` |
| H2 | 0.275 | `aa70248a-9f76-542d-bc77-1e935b9c32d4` | `a30d1b0c01dcd0607bdd46e720a3a278e6b90b265b6bd4f109eb2c1cae58d8c5` | 50962.180300173039 | 2 / 1 | 0 | `52b93a79a30693a843fab7cb7575560ecebc3051512fdf987d6eef040aa839d0` |
| H3 | 0.350 | `f3e14759-e05b-5088-bfb5-b6e16e918267` | `b5bcf9258ff1cd455eab071a55cbdce7d8708391d1737e44d3dae2bccdaedb7e` | 49197.902092283937 | 0 / 0 | 0 | `73a0e5e199d452ba7e8a6dc7239c43f1f9bd857028c9722a6db9e9a1a444698a` |

Across the five cases: 8 outer-decision certificates, 16 transient endpoint
event records, zero nested enclosures, and zero final accepted-trajectory
enclosures. Every enclosure had completed left/right continuations, identical
outer classifications, identical terminal-tolerance decisions when applicable,
and identical outer actions. The representative endpoint did not decide the
outer action. Reference n=1 had zero transient and zero accepted enclosures.

## H2 numerical-hole trace addendum

H2 outer iteration 11 at shooting enthalpy
`107469.424689940170810546875 J/kg` contains one interior
`BLOCKED_RESIDUAL_ACCEPTANCE` trial at support 4 and
`q=8600.8670719301 W`. It is not an enclosure event and its blocked result is
not promoted. The left/right valid neighbors are:

```text
LEFT q=8600.866943237208 W
LEFT F=-0.000090940275 W
LEFT Task172 result=722284bf5379d897de288a2e8aa46798871a0b2f76e58a1d531b83e5aedda92d
HOLE blocked result=56a9eb129c971e9c7dfed9766494d934069a471f2beca8210eac54c69d97c4eb
HOLE request=6f4d89289c045d822285aa9b46d1ae07bff8c524d51b73ac4efe0177847982d1
RIGHT q=8600.867200622995 W
RIGHT F=+0.000177409965 W
RIGHT Task172 result=18c2ab5de834d8bcb5c5a160cef0f8d2a24e5c4d2184521367a1630e1620817d
```

The original transient receipt reports zero endpoint-recovery probes for this
interior hole; it preserves the neighboring valid points. The evidence-only
capture reran the exact H2 trial and retained complete native request/result
projections for the blocked point and both neighbors. All three request/result
identities replay, and the reproduced H2 branch classification, mesh hash, and
continuation hash match the original qualification record. The final accepted
H2 trajectory is separately retained and has five exact point roots.

```text
H2_HOLE_EVIDENCE_HASH=968e50038a558af7f28d57364082c356b4a1c26aa90d40a5e65463a3c7a18afe
H2_HOLE_ENDPOINT_IDENTITY_REPLAY_COUNT=3
H2_BLOCKED_REQUEST_RESULT_REPLAY=PASS
H2_LEFT_RIGHT_VALID_NEIGHBOR_REPLAY=PASS
H2_OUTER_TRIAL_CROSS_BINDING=PASS
```

## Replay contract and qualification evidence

The original self-contained replay reports:

```text
QUALIFICATION_MATRIX_HASH=f659ef3be2e2e0766af9a004dc131e468433ae46e94a0470fb49509ff675ef6d
EVENT_HASH_REPLAY_COUNT=16
ENDPOINT_REQUEST_RESULT_REPLAY_COUNT=57
CONTINUATION_HASH_REPLAY_COUNT=16
OUTER_DECISION_CERTIFICATE_HASH_REPLAY_COUNT=8
TRAJECTORY_HASH_REPLAY_COUNT=5
QUALIFICATION_STATUS=PASS
ALL_REPLAY_PASS=true
```

The separate H2 addendum replay verifies the complete blocked/neighbor
Task172 preimages and cross-binds them to the frozen H2 qualification matrix.
The authority remains proposed and unaccepted pending fresh independent review.

| Artifact | Purpose |
|---|---|
| `evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2.json` | Canonical authority, full five-case qualification matrix and trajectories |
| `evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-qualification.py` | Actual production-runtime qualification runner |
| `evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-replay.py` | Authority, matrix, event, endpoint, continuation, certificate and trajectory replay |
| `evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-h2-hole.json` | Full H2 hole and valid-neighbor Task172 preimages |
| `evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-h2-hole-capture.py` | Fixed H2 trial capture/reproduction using committed production runtime |
| `evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-h2-hole-replay.py` | Independent replay of H2 blocked and neighbor identities |

The qualification runner (`9b12f7fc…f3781`) and its replay runner are bound
into the canonical R2 authority projection. The H2 addendum has its own canonical evidence hash
and replay contract. All were run against the committed runtime baseline; no
production source or numerical policy was changed by the addendum.

## Scope and next gate

```text
PRODUCTION_R2_ENCLOSURE_IMPLEMENTED=false
TASK173_RATING_COMPLETE=true
TASK173_SIZING_COMPLETE=false
TASK173_COMPLETE=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=STAGE3_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2_INDEPENDENT_REVIEW_R1
NEXT_GATE_EXECUTED=false
```

This qualification does not implement the R2 enclosure in production and does
not complete Task173 Sizing. No release or PR readiness action is authorized.
