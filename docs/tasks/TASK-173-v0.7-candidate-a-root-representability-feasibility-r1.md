# TASK173 Candidate A root representability feasibility R1

```text
TASK_ID=STAGE3_TASK173_CANDIDATE_A_ROOT_REPRESENTABILITY_RECOVERY_FEASIBILITY_R1
REPOSITORY=xuezhiorange-png/hxforge-agent
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
START_HEAD=94fd650aba2a3f6591c9c9eef865fa442167b328
FINAL_HEAD=<this evidence commit>
RESULT=ROOT_EXISTENCE_NOT_ESTABLISHED_FROM_COMMITTED_TARGET_CELL_EVIDENCE
RECOVERY_TECHNICALLY_PLAUSIBLE=CONDITIONAL_HIGH_PRECISION_Q_COORDINATE
PRODUCTION_NUMERICAL_BEHAVIOR_CHANGED=false
R2A_AUTHORITY_CHANGED=false
NUMERICAL_TOLERANCE_CHANGED=false
CANDIDATE_A_FULL_RATING_REEXECUTED=false
CANDIDATE_B_FULL_RATING_REEXECUTED=false
PUBLIC_SIZING_REEXECUTED=false
TASK175_EXECUTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
```

## Finding

The committed Candidate A result is internally replayable and records the
frozen request identity, `n=32`, support URI ending in `support:2`, and
`BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED`. Its q bracket
is `268.4228547695099` to `268.42285476950997 W`. Those values are adjacent
binary64 numbers, so the production binary64 midpoint rounds to the right
endpoint and no binary64 q lies strictly inside this bracket.

The ordinary point-root test remains `Task172 result.status == VALIDATED` and
`abs(F(q)) <= 1e-6 W`, with `F(q) = q - q_TASK172(q)`. The production path
reaches its accepted-path precision-floor branch only after both bracket
trials are valid and neither is eligible under that exact test. Thus the
current binary64 search did not produce an acceptable ordinary point root in
this final bracket. The exact endpoint F magnitudes were not persisted; only
their sign/eligibility is inferable from the reached production branch.

This proves q-grid midpoint collapse, not provider PH-coordinate exhaustion.
The failed result does not contain the endpoint Task172 request/result
projections or hashes, provider coordinates, upstream face states, exact F
values, selected shooting enthalpy, outer iteration, or the failed cell's
stable tube/shell cell IDs. The older Decimal cell-root diagnostic is not a
substitute: it concerns Candidate A at `n=1`, support 1, q near 12,234.63 W;
the target here is `n=32`, support 2, q near 268.42 W. Its own evidence found
no in-tolerance F among its 64 probes, but that result is limited to that
different physical state.

Therefore a valid point root for the exact failed n=32 cell is neither proved
to exist nor proved impossible. The failed production search is not a proof
that no mathematical root exists; it is a fail-closed result from the
currently implemented binary64 search with the accepted-cell tolerance
unchanged.

The failed receipt's mesh summary records 144,217 local Task172 evaluations
and 27 numerical holes at n=32, but it does not identify which of those
evaluations were the final support-2 bracket endpoints. Candidate B's
successful n=32 control records 320 cells and 155,402 local Task172
evaluations, with no n=32 enclosure/certificate and zero accepted-path
enclosures. It is not the same physical cell and does not establish
Candidate A's root feasibility.

## Numeric path inspected

In `task173_integrated_rating/service.py`, `_CellTrial.q_w` and
`_cell_evaluation(q_w)` are binary64 (`float`). `_solve_cell` bisects with a
binary64 midpoint. It converts q to `Decimal(str(q))` for local enthalpy
propagation under a 70-digit Decimal context, then `_state_from_enthalpy`
converts the propagated enthalpy to float at the existing CoolProp `state_ph`
boundary. Resulting provider states are converted into the candidate Task172
request. Task173 computes the cell residual as Decimal q minus the native
Task172 `signed_q_hot_to_cold_w`.

The Task172 runtime also uses binary64 internally: its local heat-transfer
unknowns/residuals are NumPy floats solved by SciPy `least_squares`, with the
existing evaluation cap and existing C-residual ULP-bound acceptance. Its
validated q is then represented as `Decimal(str(float_q))`. This local
constitutive residual acceptance is distinct from Task173's outer cell-root
criterion `abs(F) <= 1e-6 W`; neither contract is changed here.

This chain has two distinct precision boundaries: the binary64 q search
coordinate and the binary64 provider PH interface. Provider outputs and the
Task172 nonlinear solve may also make the composed `F(q)` staircase-like or
branch-sensitive. The committed target-cell receipt is too small to decide
whether that happened at this particular cell, whether a Task172 local-solver
residual jump dominated, or whether any provider-state transition skipped
the tolerance interval. No exact provider plateau or local residual
amplification is claimed.

## Minimal recovery route

The least invasive feasibility experiment is a diagnostic-only high-precision
q coordinate for the exact failed cell, not a relaxed acceptance rule:

1. Reconstruct the same Candidate A request, runtime/provider identity,
   `n=32` mesh, selected shooting enthalpy, support 2, and upstream face
   states. Capture every trial's exact Decimal q, binary64 encoding where
   applicable, `F`, Task172 request projection/hash, complete result
   projection/hash, local solver residuals/status, and the four propagated
   PH enthalpy coordinates both before and after the provider float boundary.
2. Search q as Decimal through enthalpy propagation while retaining the same
   CoolProp backend/version/reference state, native Task172 request/result
   contract, candidate, support, correlation branch, and resource cap. Do
   not round q back to float before computing F. The existing provider API
   boundary remains binary64 for this first feasibility test.
3. Accept no sign bracket or interpolation as a root. A trial qualifies only
   when the native Task172 result is `VALIDATED` and the exact unchanged
   `abs(q - q_TASK172) <= 1e-6 W` predicate passes. Replay the exact request,
   result, support, provider snapshots, and final trajectory identities.
4. If a qualifying Decimal q is found, it establishes a representable
   ordinary point root under the existing physical/provider/Task172
   semantics. If not found, a finite probe set alone does not prove
   nonexistence; establish a bound over the reachable provider-state plateaus
   before claiming impossibility.

Merely computing a Decimal midpoint and immediately converting it back to
float is not a recovery: it reproduces the current grid collapse. Conversely,
changing the provider/backend precision, Task172 numerical semantics,
property profile, acceptance rule, or physical state mapping is outside this
conditional arithmetic-only route and requires explicit owner numerical-
authority authorization. No such change is proposed here.

### Minimum instrumentation to restore the exact cell

The existing blocked preimage does not include enough state to replay the
target cell without recomputing its upstream trajectory. A narrowly scoped
observer for a future owner-authorized isolated diagnostic must capture:

- exact runtime head/tree, Candidate A request hash, provider identity, mesh
  identity, selected outer shooting enthalpy, and outer iteration;
- the exact accepted-trajectory upstream tube/shell face states and the
  target support/cell/wall-interface identities;
- every bracket trial's exact q, classification, F, Task172 request hash and
  full canonical request projection, Task172 result hash and complete
  projection, and any blocked-hole identity;
- tube-downstream, shell-next-face, tube-midpoint, and shell-midpoint
  enthalpies before float conversion, their binary64 encodings, returned
  property snapshots/identities, and the actual Task172 candidate request;
- confirmation that the control mode is accepted-path `DISABLED`, with no
  transient event, representative branch, interpolation, or stale state
  entering the accepted trajectory.

The observer must be passive and scoped to the target cell; it must not
change arguments, Decimal context, provider, branch decisions, resource
limits, or returned values. This task did not install it or execute the
solver.

## Authority and execution disposition

No R2A authority amendment is needed merely to investigate a higher-precision
search coordinate if the physical equation, provider interface, native
Task172 semantics, exact validity rule, and `1e-6 W` acceptance predicate
remain identical and the accepted trajectory still contains ordinary point
roots only. This is a conditional implementation-level route, not an
established Candidate A recovery. Owner authorization is still required
before any production implementation or another Candidate Rating call.

If a root can be obtained only by changing the provider's numerical contract,
Task172 acceptance/solver semantics, tolerance, or accepted-path enclosure
policy, that is a new numerical-authority request. No such authority change
is authorized by this feasibility task. There is currently no proof that
Candidate A cannot complete Rating under the frozen physical conditions;
there is also no proof that this exact failed cell has a valid point root.

## CI hygiene and evidence replay

Only the authorized completion replay script was formatted. The AST parsed
from the required start-head version is identical to the formatted version
using locked Python 3.14.5 (`AST_SHA256=d5686529c60684632f7f01f61015455f81313349a93692ce8fe53e5e26d63d75`).
The completion replay's stdout was byte-for-byte identical before and after
formatting; both runs passed. The formatter changed layout only; no replay
logic changed.

The evidence replay verifies the candidate blocked-result preimage/hash,
binary64 adjacency/midpoint collapse, source/runtime bindings, distinct
n=1/support-1 historical diagnostic boundary, and committed completion
request/candidate result replay. It does not invoke Candidate Rating, public
Sizing, or TASK175.

```text
REPLAY_SCRIPT_FORMAT_ONLY_CHANGE=true
REPLAY_SCRIPT_SEMANTICS_CHANGED=false
PRODUCTION_NUMERICAL_BEHAVIOR_CHANGED=false
R2A_AUTHORITY_CHANGED=false
NUMERICAL_TOLERANCE_CHANGED=false
CANDIDATE_A_FULL_RATING_REEXECUTED=false
CANDIDATE_B_FULL_RATING_REEXECUTED=false
PUBLIC_SIZING_REEXECUTED=false
TASK175_EXECUTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=OWNER_DIRECTION_REQUIRED_FOR_CANDIDATE_A_ROOT_REPRESENTABILITY_RECOVERY
NEXT_GATE_EXECUTED=false
STOP=true
```
