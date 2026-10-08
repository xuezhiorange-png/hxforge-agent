# TASK173 v0.7 Supplemental Functional Acceptance R2

```text
TASK_ID=V07_TASK173_SUPPLEMENTAL_FUNCTIONAL_ACCEPTANCE_R2
SUPPLEMENTAL_ACCEPTANCE_ID=V07-T173-SUPPLEMENTAL-FUNCTIONAL-ACCEPTANCE-R2
STATUS=FROZEN_INPUT_PROPOSAL_PENDING_INDEPENDENT_REVIEW
PUBLIC_RATING_OR_SIZING_EXECUTED=false
GOLDEN_G05_AUTHORIZED=false
TASK175_AUTHORIZED=false
```

## Scope and separation

This is a new, implementation-validation-only TASK173 functional test identity.
It does not replace or revise Completion R1, its frozen request, its Candidate A/B,
or its blocked result. It does not claim engineering-design, business, release,
or Golden authority. TASK175 / Golden V07-G05 remains a separate acceptance with
its own independent numerical oracle and approval requirements; this package
does not assert G05 pass.

The requirement values are explicitly supplied by the R2 task directive:
required duty `10000 W`, maximum tube pressure drop `1200 Pa`, and maximum shell
pressure drop `1200 Pa`. They are copied as test inputs under a new source,
requirement, and request identity. No Completion R1 requirement hash is reused.
The Owner direction is recorded in the machine evidence; the independent
applicability review remains a required pre-execution gate.

## Frozen candidate-space source

The candidate space is the exact existing TASK168 validation-only holdout space,
not the two-candidate R4 space and not a newly invented geometry set:

| Identity | Value |
| --- | --- |
| TASK168 candidate-space ID | `94acffe4-8346-5015-b020-60fbbcea3dfd` |
| TASK168 candidate-space hash | `480e3249300d4b4a0668815cd18ebb7ed6fb5cf507c073449c9a509526eea668` |
| Native TASK168 request hash | `f62cc16652d10d504678b2ed9248ee2f3a71b810af577f75f82903fcc7191187` |
| Baffle-cut authority | `V07-T173-PROVIDER-QUANTIZATION-HOLDOUT-REBIND-R1` |
| Baffle-cut authority hash | `ccdf7bd85e06b00c4b73cf4a21e7236d7aa313da27ea33eb98dec260c4e686af` |
| Frozen holdout selection hash | `f2de04ae8ca31a0f42c3cbfa57a135416d5607c5e6963442576c6e6da50450da` |

The approved discrete-set source is scoped to implementation validation only,
not Golden, release, or business requirements. The frozen selection is H1, H2,
H3 in that order; the selection record states that performance output was not
used. The exact native candidate IDs and hashes are reused unchanged. Candidate
A/B from Completion R1 are not altered or rebound; Candidate B is not needed as
a fourth member or a Golden comparator in this three-member space.

All three candidates share the same recorded geometry except baffle cut:

| Field | Frozen value |
| --- | --- |
| Case source | `task039-release-demo-001` |
| Shell catalog member | `shell-1` (`task023-test-catalog`) |
| Shell inside diameter | `0.500 m` |
| Construction / shell | `FIXED_TUBESHEET` / `E_SHELL` |
| Tube OD / wall / length | `0.01905 m` / `0.00165 m` / `6.0 m` |
| Tube pitch / layout / passes | `0.0254 m` / `LAYOUT_30_DEG` / 1 |
| Baffle type / count / spacing | `SINGLE_SEGMENTAL` / 4 / `1.2 m` |

| Frozen order | Prior label | Baffle cut | Candidate ID | Candidate hash |
| --- | --- | ---: | --- | --- |
| SUPP-01 | H1 | 0.225 | `68a99368-a518-5482-b9df-4bc3357edea9` | `bd0da145a592652e55a6fc8cd325a98d6f1cf349ed74b98e811d1343ce62ed54` |
| SUPP-02 | H2 | 0.275 | `aa70248a-9f76-542d-bc77-1e935b9c32d4` | `a30d1b0c01dcd0607bdd46e720a3a278e6b90b265b6bd4f109eb2c1cae58d8c5` |
| SUPP-03 | H3 | 0.350 | `f3e14759-e05b-5088-bfb5-b6e16e918267` | `b5bcf9258ff1cd455eab071a55cbdce7d8708391d1737e44d3dae2bccdaedb7e` |

The committed R2A qualification records all three candidate-native pre-Rating
chains as passing through TASK024, TASK025, TASK031, TASK166 applicability and
completeness, TASK171, C3 preflight, and validated TASK174. That evidence is a
structural/applicability preflight and an n=1 R2A qualification; it is not a
full-mesh Rating or a hard-constraint result. The earlier holdout-rebind receipt
that recorded the pre-fix H1 TASK174 reduction blocker remains historical and
unchanged; the later reviewed R2A evidence binds the corrected runtime and the
same H1/H2/H3 candidate identities.

## New requirement and request identities

| Identity | Value |
| --- | --- |
| Requirement ID | `TASK173-SIZING-SUPPLEMENTAL-FUNCTIONAL-ACCEPTANCE-R2` |
| Requirement source ID | `V07-T173-SUPPLEMENTAL-FUNCTIONAL-ACCEPTANCE-R2-INPUT-SOURCE` |
| Requirement source-record hash | `be6fc9a2e705264fb252ffc4956c58f25ee4d6820b9a12c0519de0693196c1db` |
| Requirement authority hash | `8dd46475acbdfd46caf3e6a6bddc89a74ba707beb21735f713d482e7bd19696e` |
| New Sizing request hash | `e5b085d238b2b1d9d7bcf23873c3ef04650135785fa4e6be1598aed3b8a9ab1e` |

The request binds the reviewed Sizing package R2
(`750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9`), the
R2A reviewed numerical authority
(`25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e`), the
existing v0.7 Ranking Policy R1
(`0d9f6c410414f5a556e92dad15b86fabc4c28c07416513a71645160a0349fba6`), and the
newly computed requirement identity. The request passes strict native
`Task173SizingRequest` validation and is independently reconstructible by the
companion replay script. These identities are a pre-execution freeze proposal;
no production Sizing call has been made.

The inherited numerical contract is unchanged: R2/R2A production mesh profile,
allowed mesh sequence `1,2,4,8,16,32,64`, existing mesh convergence/headroom criteria,
ordinary cell root `F(q)=q-q_TASK172(q)` with `abs(F)<=1e-6 W`, accepted cells
must be exact valid point roots, and accepted-trajectory enclosure count must
be zero. Transient R2A enclosure remains restricted to reviewed outer-search
decision diagnostics and is not accepted-trajectory authority.

Ranking is unchanged: `V07-T173-SIZING-RANKING-POLICY-R1`, Top-N 3, WARN penalty
10, minimize shell DP with weight 1 / scale 100, Decimal precision 50 with
ROUND_HALF_EVEN, then candidate-hash UTF-8 ascending tie-break.

## Conditional acceptance contract

No candidate is frozen as PASS, WARN, BLOCKED, hard-constraint pass, or
hard-constraint fail. Those are execution observations, not input authority.
Each of the three frozen candidates is processed exactly once in the eventual
authorized controlled run:

1. A successful Full Rating must preserve every mesh actually executed as the
   production solver's ordered prefix of the allowed sequence, and prove the
   unchanged production stopping rule: two consecutive passing mesh pairs plus
   the required later headroom comparison. It need not execute unused finer
   levels after the production solver accepts its headroom. It must also prove
   terminal and energy closure, exact accepted-cell roots, complete Task172
   identities, R2A event and outer-decision-certificate replay, and deterministic
   Rating result replay. Accepted-trajectory enclosure count must be zero.
2. A blocked Rating remains blocked with its original failure stage/code and
   complete result identity. It receives no hard-constraint evaluation and is
   excluded from ranking.
3. Only successful Ratings are checked against exact R2 Decimal predicates:
   duty `>= 10000 W`; tube DP `<= 1200 Pa`; shell DP `<= 1200 Pa`. No rounding or
   epsilon is introduced. Every candidate and each predicate remains in the
   ledger.
4. Only complete PASS/WARN candidates without blockers enter the existing
   deterministic ranking. Recommendation, alternatives, exclusions, ranking
   trace, provenance DAG, and final result ID/hash must replay from committed
   preimages.
5. Functional core coverage requires at least one recommendable candidate,
   at least one successfully rated candidate excluded by a Duty/DP hard
   constraint, and valid ranking/recommendation/exclusion/provenance replay.
   Non-empty Alternatives is an additional coverage target requiring at least
   two recommendable candidates. If core coverage is absent, report PARTIAL or
   BLOCKED according to the actual outcomes; do not reselect or mutate inputs.

This is conditional software-functional acceptance, not an independent
numerical oracle. It cannot pass TASK175 G05. G05 still requires independent
expected classes/order and Golden approval.

## Gates and disposition

The non-solving input reconstruction and canonical replay pass. The source
values, candidate source scope, R2/R2A bindings, geometry, selection order, and
conditional assertions are now auditable. Independent review of the new source
record, applicability, and complete freeze is still required before the
pre-execution gate is complete. No Rating/Sizing execution is authorized in
this package. After review, the next step requires a separate explicit
execution authorization.

```text
OWNER_DIRECTION_PRESENT=true
INDEPENDENT_REVIEW_STATUS=PENDING
PREEXECUTION_INPUT_IDENTITIES_FROZEN=true
PREEXECUTION_FREEZE_COMPLETE=false
CONTROLLED_PRODUCTION_EXECUTION_ELIGIBLE=false
RATING_EXECUTED=false
SIZING_EXECUTED=false
TASK175_EXECUTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
```
