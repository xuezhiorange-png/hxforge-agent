# TASK173 TASK174 Canonical Reduction Parity and Enclosure Qualification Resume R1

## Disposition

```text
TASK_ID=STAGE3_TASK173_FULL_SIZING_IMPLEMENTATION_R1
CONTINUATION_MODE=TASK174_NATIVE_BELL_CANONICAL_REDUCTION_PARITY_CORRECTION_AND_ENCLOSURE_QUALIFICATION_RESUME
RESULT=PASS_CELL_ROOT_PROVIDER_QUANTIZATION_ENCLOSURE_AUTHORITY_CANDIDATE
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
REMOTE_HEAD=ebe747e7aed7199dc18b8ce3ac888b6357a975b0
AUTHORITY_PACKAGE=V07-T173-SIZING-AUTHORITY-PACKAGE-R2
AUTHORITY_PACKAGE_HASH=750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9
```

The enclosure authority is a candidate for one fresh independent review. It is
not yet accepted and has not been implemented in production. The parent
TASK173 Sizing implementation remains dirty, uncommitted, and incomplete.

## Parent implementation preservation

The tracked parent implementation diff was preserved. Its current patch hash
against the authorized checkout is
`b5408a1e7cf62456cd36e6c3cb95e52d79838103e23ab68139b8b6006de21555`; the
pre-correction implementation lineage hash remains recorded as
`71aa09b716a457f510940d9020e4d3106fd390145cad99c6d3251eefb3a179e0`. The
difference is the in-scope TASK174 canonical reduction correction and its
focused regression tests. No unrelated untracked handoff was changed.

## TASK174 canonical Bell reduction correction

Root cause: `DECIMAL_FINITE_PRECISION_REDUCTION_GROUPING_MISMATCH`. Native
TASK166 forms end-zone pressure as entrance plus exit, then forms total shell
pressure as central crossflow plus window plus the already-computed end zone.
TASK174 now checks those same two stages exactly under the existing
`engineering_context()`:

1. `entrance + exit == task166.end_zone_pressure_drop`
2. `central + window + task166.end_zone_pressure_drop == task166.total_shell_pressure_drop`

For the frozen H1 identity (`68a99368-a518-5482-b9df-4bc3357edea9`, hash
`bd0da145a592652e55a6fc8cd325a98d6f1cf349ed74b98e811d1343ce62ed54`),
TASK166 hash is
`08e783c2405569924fbcc1a32f643eae8ad0277d5fe97b32aaaf0f56b12cd9d5`.
The historical flat four-term reduction differs by `1E-47 Pa`; the grouped
end-zone and total replays differ by zero. All 19 candidate events remain
exact-once allocated (9 additive, 10 support). H1 TASK174 is `VALIDATED`.

No tolerance, rounding, pressure formula, physical semantics, event mapping,
TASK166 production code, or Decimal context changed. The reference TASK174
result identity remains
`ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419`.

Focused checks passed: TASK174 tests (10), the candidate-native TASK174
R2-binding/tampered-end-zone/tampered-total regression, Ruff check and format,
and `git diff --check`.

## Frozen candidate qualification and n=1 diagnostics

No TRAIN or HOLDOUT identity or cut was changed. The preselected holdouts remain
H1 `0.225`, H2 `0.275`, and H3 `0.350`, under rebind authority hash
`ccdf7bd85e06b00c4b73cf4a21e7236d7aa313da27ea33eb98dec260c4e686af` and
candidate-space hash
`480e3249300d4b4a0668815cd18ebb7ed6fb5cf507c073449c9a509526eea668`.
TRAIN_A/B remain the original R4 identities. All five candidate-native
pre-Rating chains passed TASK024, TASK025, TASK031, TASK166 applicability and
completeness, TASK171, C3 preflight, and TASK174. Each had 19 events, with 9
additive and 10 support events. C3 preflight was `TURBULENT`, Re `4491.2103`,
Pr `5.8559`.

| Case | Cut | n=1 trajectory | Outer-search enclosure uses | Recovered Task172 holes | Hard blockers |
|---|---:|---|---:|---:|---:|
| TRAIN_A | 0.215 | Complete | 1 | 0 | 0 |
| TRAIN_B | 0.220 | Complete | 3 | 0 | 0 |
| H1 | 0.225 | Complete | 3 | 0 | 0 |
| H2 | 0.275 | Complete | 1 | 1 | 0 |
| H3 | 0.350 | Complete | 0 | 0 | 0 |

The H2 numerical hole was recovered through the existing hole handling and
was not promoted as an enclosure endpoint. All eight actual precision-floor
events independently passed Q1–Q15, including exact Task172 request/result
replay, adjacent binary64 provider coordinates, same property/model branch,
and candidate-native TASK166 version `1.0` binding. Each event has its own
canonical enclosure hash.

The five final n=1 mesh results each contain five ordinary point-root cells
and zero enclosed cells. Enclosure representatives were used only in the
outer-boundary trial trajectories shown above; those transient uses and hashes
are explicitly retained in the evidence and included in the proposed result
identity aggregation semantics, so they cannot disappear from a final result.

The full observed uncertainty span across all eight uses is:

```text
SUM_PROVIDER_DUTY_UNCERTAINTY_W=0.000026550124
MAX_PROVIDER_DUTY_UNCERTAINTY_W=0.000008420022
MAX_PROVIDER_WALL_UNCERTAINTY_K=4.9526E-10
UNCERTAINTY_FORMULA_REPLAY=PASS
```

The uncertainty formula and local roundoff-floor combination were replayed
for every trigger with the existing 50-digit `engineering_context()` and
`ROUND_HALF_EVEN`. The existing mesh classification and whole-exchanger
energy-balance rules remain unchanged. The focused reference n=1 diagnostic
observed zero enclosure triggers; this is not a full reference Rating replay
or proof of the frozen Rating result identity.

## Enclosure authority candidate

```text
AUTHORITY_ID=V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R1
AUTHORITY_HASH=c95b5bf23b15a9c93b6ef47c3ad2043708bef9ae66429116855a4306f8102ab2
AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
AUTHORITY_ACCEPTED=false
```

This candidate preserves the ordinary `abs(F(q)) <= 1e-6 W` point-root rule,
TASK172 acceptance, property backend, R94/R98, mesh thresholds, and all
iteration/evaluation caps. It defines a distinct set-valued closure only when
all Q1–Q15 predicates hold; the representative is an actual valid endpoint,
not an exact root, interpolation, or synthetic state. It propagates the full
provider duty span and wall span into the existing local precision bounds.

The complete projection, five-case diagnostic matrix, eight cell-level Q
proofs, endpoint property/result identities, and canonical replay values are
in [the machine evidence](../evidence/TASK-173-v0.7-task174-native-bell-canonical-reduction-parity-and-enclosure-qualification-resume-r1.json).

## Change boundary and next gate

```text
PRODUCTION_CODE_CHANGED_BY_THIS_GATE=false
TASK174_CORRECTION_REMAINS_DIRTY_PARENT_IMPLEMENTATION=true
TASK173_SIZING_PUBLIC_API_EXECUTED=false
FULL_CANDIDATE_RATING_EXECUTED=false
PRODUCTION_MESH_EXECUTED=false
REFERENCE_FULL_RATING_REPLAYED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
TASK173_RATING_COMPLETE=true
TASK173_SIZING_COMPLETE=false
TASK173_COMPLETE=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=STAGE3_TASK173_CELL_ROOT_PROVIDER_QUANTIZATION_ENCLOSURE_INDEPENDENT_REVIEW_R1
NEXT_GATE_EXECUTED=false
```

No enclosure production code, parent implementation commit, TASK175 work,
Ready, or Merge action occurred in this continuation.
