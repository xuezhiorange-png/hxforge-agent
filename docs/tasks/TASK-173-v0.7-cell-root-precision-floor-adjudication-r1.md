# TASK173 cell-root precision-floor adjudication R1

```text
TASK_ID=STAGE3_TASK173_CELL_ROOT_PRECISION_FLOOR_ADJUDICATION_R1
RESULT=BLOCKED_CELL_ROOT_PROPERTY_PROVIDER_QUANTIZATION_GAP
BASE_HEAD=b1f89c9df9c06ee7d7f513cfad7f0ba8f65e0768
IMPLEMENTATION_WORKTREE_PATCH_SHA256=71aa09b716a457f510940d9020e4d3106fd390145cad99c6d3251eefb3a179e0
ATTEMPT_4_CANDIDATE_SPACE_CHANGED=false
CANDIDATE_A=adeab5b1-a339-5eb3-aa66-011ffe49bac0 / cut=0.215
CANDIDATE_B=e152cca9-fd5d-59ca-9b46-1df574eee841 / cut=0.220
CANDIDATE_A_Q_BRACKET=12234.634520032956..12234.634520032958 W
CANDIDATE_A_Q_ULP=1.8189894035458565e-12 W
CANDIDATE_A_ADJACENT_BINARY64=true
CANDIDATE_A_F_LEFT=-0.000001027091 W
CANDIDATE_A_F_RIGHT=0.000001594071 W
CANDIDATE_A_MIN_ABS_F_DECIMAL_DIAGNOSTIC=0.0000010270908410460948944091796875 W
CANDIDATE_B_Q_BRACKET=12277.427019616665..12277.427019616667 W
CANDIDATE_B_Q_ULP=1.8189894035458565e-12 W
CANDIDATE_B_ADJACENT_BINARY64=true
CANDIDATE_B_F_LEFT=-0.000001063978 W
CANDIDATE_B_F_RIGHT=0.000001550765 W
CANDIDATE_B_MIN_ABS_F_DECIMAL_DIAGNOSTIC=0.0000010639779709212779998779296875 W
DECIMAL_EVALUATIONS=64 per candidate
CELL_RESIDUAL_ACCEPTANCE=1e-6 W (unchanged)
NUMERICAL_CLASSIFICATION=OUTCOME_B_PROPERTY_PROVIDER_QUANTIZATION_GAP
PRODUCTION_CODE_CHANGED_BY_ADJUDICATION=false
REFERENCE_RATING_REPLAY_RECOVERY=NOT_ESTABLISHED_NO_COMPLETE_CAPTURED_RESULT
TASK173_RATING_COMPLETE=true
TASK173_SIZING_COMPLETE=false
TASK173_COMPLETE=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
NEXT_GATE=OWNER_DIRECTION_REQUIRED_FOR_CELL_ROOT_PROPERTY_PRECISION_GAP
```

## Finding

Both frozen Attempt 4 candidates reached valid candidate Task174 results, then failed the first mesh level's cell-root solve at a precision floor. The binary64 q endpoints are adjacent (one ULP apart), with no representable float strictly between them. At the unchanged CoolProp 8.0.0 HEOS::Water DEF provider boundary, the shell-local enthalpy inputs also resolve to two adjacent binary64 values; the tube-local state is unchanged. Each endpoint maps to a different shell property snapshot and a different valid Task172 request/result identity.

The diagnostic propagated q and enthalpy coordinates in Decimal (precision 80, HALF_EVEN) through the thermodynamic propagation and converted to float only at the existing property-provider boundary. It ran 64 real Task172 evaluations per candidate, with the production ambient Decimal context restored for Task172. No trial satisfied the unchanged `abs(F(q)) <= 1e-6 W` condition. The closest residuals were still outside tolerance, so a Decimal q coordinate alone does not resolve the provider-state quantization gap.

This is Outcome B, not evidence for a Decimal-continuation authority. No tolerance, sign-bracket acceptance, Task172 acceptance, property backend, R94/R98, or resource limit is changed. The narrow disposition is blocked for owner direction on the property precision gap.

## Frozen inputs and endpoint evidence

The two candidate identities and R4 candidate-space hash are preserved in the machine receipt. It records both precision-floor events, local support/cell/wall identities, shooting enthalpies, Task172 hashes and signed duties, tube/shell property snapshot hashes and identities, temperatures, enthalpies, ULP/adjacency analysis, and the per-trial Decimal ledger with each trial bound to the exact endpoint Task172 identity it reached.

No candidate selection was rerun or changed. The diagnostic did not run candidate Rating beyond the already blocked production-path attempts, did not rerun Sizing, and did not execute a production mesh sequence.

The required reference Rating recovery ended without a complete captured request/result/ID tuple. Its frozen identity therefore remains unverified in this adjudication; no second concurrent replay was started. This receipt does not claim Sizing or TASK173 completion.

## Preservation and changes

The pre-existing TASK173 implementation diff was snapshotted at `/tmp/task173-sizing-impl-r1-attempt4.patch` (SHA256 above) and remains uncommitted. This adjudication changes only its own evidence/receipt files; those implementation files must remain unstaged and untouched.
