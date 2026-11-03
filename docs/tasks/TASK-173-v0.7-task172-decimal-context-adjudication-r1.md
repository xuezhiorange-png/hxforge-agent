# TASK173 R3 Task172 Decimal Context Adjudication R1

**Task:** `STAGE3_TASK173_R3_TASK172_DECIMAL_CONTEXT_INHERITANCE_ADJUDICATION_R1`
**PR:** #283, OPEN / Draft
**Reviewed start head:** `fe99de204b1a626455f8447d19a80783a6ed2dcb`

## Disposition

`DECIMAL_CONTEXT_CAUSALITY=CONFIRMED` and
`TASK172_AMBIENT_DECIMAL_CONTEXT_SENSITIVITY=CONFIRMED`.

The same frozen Task172 request, hash
`b2472ec62e4a9e53517cdb5cc3a3f6c8d70106cd2cf34663ed2191bdaa9ce072`,
produced the historical R2 result hash
`ea8869a56cdd300ba42631aa967958aa01daa7e462ed7e5134b10d3d19893573`
in two controlled runs at the R2 saved Decimal precision (28), and the R3
result hash
`7e0512079ac5f28765f5685ff9ba761d56e0db277698b25ae6c26dc9984b8acc`
in two controlled runs at precision 100. The full result projection repeated
identically within each context. All four calls used the same request preimage,
CoolProp 8.0.0 / HEOS::Water / DEF provider configuration and unchanged
Task172/provider runtime files.

This establishes that the R3 identity divergence was caused by the diagnostic
runner allowing its precision-100 Decimal context to flow into the native
Task172 validator. The effect is on Decimal-valued HTC/Jμ outputs and therefore
the Task172 result identity; the signed heat rate `signed_q_hot_to_cold_w`
was identical (`268.4228395792577 W`) in both contexts. Solver status,
iteration/evaluation counts and residual vector also matched.

## Context provenance and call path

R2's saved ambient snapshots immediately before and after the n=32
reconstruction both record precision 28, `ROUND_HALF_EVEN`, `Emax=999999`,
`Emin=-999999`, `clamp=0`, `capitals=1`, and the same trap configuration.
Those saved snapshots are the evidence for the R2 baseline; it is not inferred
from the number of digits in its result. R2 did not persist the exact sticky
Decimal flags at every historical Task172 call, so those per-call flags remain
`NOT_ESTABLISHED`.

In the R3 runner, `_execute_probes()` opens a precision-100 `localcontext` at
lines 1277-1278 and invokes `run_one()` at line 1281 inside it. The
`_probe_decimal_q()` precision-70 block ends before its call to
`rating.task172_validate_candidate()`, so the caller's precision-100 context is
restored and inherited by Task172. R3 did not save a direct historical
call-time context snapshot; precision 100 is established by that dynamic
scope. The R3 process's rounding/traps/exponent bounds came from the fresh
process context; historical sticky flags are not established.

In production `task173_integrated_rating.service._cell_evaluation()`, the
precision-70 context covers enthalpy propagation only (lines 1830-1835). It
ends before property reconstruction, Task172 request construction, and the
native validator call at line 1865. `_solve_cell()` likewise confines its
precision-70 block to capacity calculations (lines 1932-1935). The ordinary
production path therefore enters Task172 under its caller's ambient context.
The R3 diagnostic runner, unlike that production call path, retained its
precision-100 outer context across the native validation.

Task172 operations that are sensitive include ambient Decimal operations in
the tube-side single-phase calculations and the ambient arithmetic in
`_eval_trial()` for Prandtl/Jμ ratios and HTC multiplication. `_decimal_power()`
and several shell/Bell helpers set their own local contexts, but they do not
cover every surrounding operation. The controlled output confirms changes to
`tube_htc_w_m2_k`, `shell_htc_w_m2_k`, and `shell_j_mu`, while the solved heat
rate stayed fixed for this request.

## Controlled comparison

| Run | Validator precision | Result hash | Status | Signed heat rate |
|---|---:|---|---|---:|
| R2 baseline 1 | 28 | `ea8869a56cdd300ba42631aa967958aa01daa7e462ed7e5134b10d3d19893573` | VALIDATED | 268.4228395792577 W |
| R2 baseline 2 | 28 | same | VALIDATED | 268.4228395792577 W |
| R3 context 1 | 100 | `7e0512079ac5f28765f5685ff9ba761d56e0db277698b25ae6c26dc9984b8acc` | VALIDATED | 268.4228395792577 W |
| R3 context 2 | 100 | same | VALIDATED | 268.4228395792577 W |

| Task172 output | R2 saved context / controlled p28 | controlled p100 | Identity value changed? |
|---|---:|---:|---|
| `tube_htc_w_m2_k` | `1284.409189857944244339715589` | `1284.40918985794424433971558902184991434893026809460361181916021395943959445284221102690192` | yes |
| `shell_htc_w_m2_k` | `1433.396604198664029577749721` | `1433.396604198664029577749720822386205347310097630323602491665904883062142563471379577699277529535260` | yes |
| `shell_j_mu` | `1.0010497254643006322937466456526065865480095666270264713648517124895580298512252` | `1.0010497254643006322937466457144755173085672206745961636619929392816714419687746` | yes |
| `signed_q_hot_to_cold_w` | `268.4228395792577` | `268.4228395792577` | no |

The residual vector was identical in both context groups:
`(-2.6943780540023E-11, 1.8428636394673958E-10,
-2.2112089936854318E-11) W`; solver status was `SCIPY_TRF_STATUS_3`,
`nfev=4`, and residual callback count was 16.

The saved R2 execution, checkpoint, and trace were read-only and rehashed at
471,057,121 / 471,036,749 / 311,208,673 bytes respectively; all three SHA-256
values match their frozen receipts. The R2 execution tree matches its saved
tree. Bound Task172/provider source paths are byte-identical from the R2
execution tree through the R3 runtime and reviewed start head. R2's historical
execution commit is not asserted to be an ancestor of the R3 runtime lineage;
tree and bound-path identity are the relevant checks here.

R3's 65 saved probes all bind the same request and R3 result identity and have
65 distinct Decimal q values but one provider PH signature. Using the
baseline-native signed heat rate, the 65 F values were recalculated offline
from those saved q values (zero additional Task172 validations). They exactly
match the recorded R3 F values; minimum `|F|` remains
`0.00001519025221096600773744285107 W`, with no qualifying point root. This is
an offline derived calculation, not 65 new native calls and not proof that no
root exists outside the recorded probes.

The provider signature comparison remains distinct from the context result:
R2 LEFT and RIGHT signatures differ at one tube-midpoint enthalpy coordinate;
the R3 `Decimal.from_float` grid has one signature matching R2 RIGHT. For the
LEFT q, `Decimal.from_float(float_q)` changes the mapped provider signature
relative to `Decimal(str(float_q))`; for RIGHT, it does not. These historical
facts are preserved and are not rewritten as a root-recovery result.

## Narrow correction and boundaries

The R2/R3 historical evidence is unchanged. A new evidence-only context fence
in this adjudication runner explicitly runs the native validator under a
reconstructed R2 baseline context, even when called from an enclosing
precision-100 context. Its regression test uses a stub and performs zero
Task172 calls. The safe diagnostic pattern is: calculate Decimal q and
enthalpy inside the intended high-precision local context, exit it, then invoke
the native Task172 validator under the explicitly selected baseline context.

No production or Task172 source, contract, result schema, provider policy,
R2A authority, tolerance, full n=32 reconstruction, Candidate Full Rating,
public Sizing, or TASK175 action was changed or executed. Task172's ambient
context sensitivity is confirmed; pinning a context in Task172 production is
not part of this correction and requires a separate numerical-authority
assessment. No claim is made that Candidate A Rating is recovered.

## Evidence and replay

Machine evidence:
`docs/tasks/evidence/TASK-173-v0.7-task172-decimal-context-adjudication-r1.json`

Zero-solver independent replay:
`docs/tasks/evidence/TASK-173-v0.7-task172-decimal-context-adjudication-r1-replay.py`

Context-fence regression:
`docs/tasks/evidence/TASK-173-v0.7-task172-decimal-context-fence-regression-r1.py`

The machine evidence canonical SHA-256 is
`d4c08a11b45d7aebdda6c6402d4ec55ccd7ca7acdc5381382ba6ed440148ca31`.
