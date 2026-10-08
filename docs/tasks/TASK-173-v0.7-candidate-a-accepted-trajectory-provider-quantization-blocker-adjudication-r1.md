# TASK173 Candidate A accepted-trajectory provider-quantization blocker adjudication R1

**Task:** `STAGE3_TASK173_CANDIDATE_A_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_BLOCKER_ADJUDICATION_R1`
**PR:** #283, OPEN / Draft
**Start head:** `e2969fe98bdabee2a72ea478a868bece4cd34216`
**Final head:** the commit containing this receipt; see the task response for its resolved SHA.

## Disposition

`ROOT_CAUSE_CLASSIFICATION=CONFIRMED_REVIEWED_AUTHORITY_FAIL_CLOSED`

Candidate A's committed blocked result replays to
`daf0f61109676d50e9dac2c1d5ceb9afb206b232bc039fc0253f5b1ecdba774c`.
At mesh `n=32`, the cell-root bracket for support 2 ended at adjacent binary64
heat-rate values. The midpoint operation cannot produce an interior `q`. The
solver first checks both valid endpoints against the frozen ordinary root
criterion `abs(F) <= 1e-6 W`; neither endpoint is eligible. In the accepted
trajectory reconstruction, transient fallback is explicitly `DISABLED`, so
the reviewed accepted-path prohibition produces
`BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED`.

This is the reviewed fail-closed outcome, not evidence that an accepted cell
passed its root tolerance and was rejected because of `q` equality. The exact
endpoint residual values and Task172 identities are absent from the committed
blocked-result preimage. The source control flow proves that the endpoint
tolerance predicate was false for both endpoints; it does not recover their
numeric residual magnitudes. The receipt therefore marks the cell
reconstruction partial and does not invent those values.

The adjacent `q` values establish a binary64 `q`-grid midpoint collapse. They
do **not** establish that the underlying provider PH coordinates were equal,
adjacent, or exhausted. Those coordinates were not persisted. No provider
plateau is claimed.

## Evidence and production path

The source-of-record candidate receipt is
`docs/tasks/evidence/TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-ratings-r1.json`
(raw SHA-256 `80e4648a91d1da2798dc608252a1a67111f1248711b8595343ab8c0739705b42`).
The completion replay reconstructs the frozen requests and replays both
Candidate A's blocked preimage and Candidate B's success preimage without
invoking Rating or Sizing.

The relevant production sequence is:

1. `_eligible_trial` requires a valid evaluation, a residual, and
   `abs(residual) <= Decimal("1e-6")` (`service.py:509-515`).
2. `_solve_cell` verifies valid bracket endpoints and sign, computes the
   binary64 midpoint, and, when it collapses to an endpoint, returns an
   eligible endpoint if one exists before asking the transient controller
   (`service.py:2210-2221, 2422-2456`).
3. `_candidate_provider_floor_evaluation` immediately raises the recorded
   accepted-trajectory blocker when mode is `DISABLED`; it does not invoke the
   transient Q-predicate/event path (`service.py:1174-1217`).
4. `_candidate_transient_outer_boundary` obtains the shooting solution from
   the shared production outer helper, creates a new `DISABLED` control, and
   calls `_valid_trajectory` from the beginning. It attaches transient event
   and certificate provenance only after that fresh accepted run succeeds
   (`service.py:3177-3403`).
5. `_run_mesh_sequence` adds `mesh_subdivisions=32` while propagating the
   failure; `validate_candidate_rating` converts the `_Stage3Failure` into the
   committed blocked-result projection (`service.py:3602-3645, 4166-4179`).

Thus the physical failure is in the fresh accepted trajectory, not in a
transient branch. It does not reuse the representative transient branch or
stale ContextVar state. The accepted trajectory did not produce a successful
cell projection, so there is no accepted cell whose closure mode or Task172
request/result can be audited for this failed support/cell.

The reviewed R2A qualification similarly invokes the shared outer state
machine and then runs a separate accepted path with zero enclosure count.
Current production follows that policy: transient-only continuation does not
relax accepted-cell root closure. No semantic difference affecting this
blocker was found. The R2A evidence replay passed on its exact reviewed head;
its runtime guard correctly rejects replay against this later production
runtime because the bound runtime paths have changed since review.

## Cell evidence boundary

Known from the committed result:

- Candidate A ID/hash and Rating request hash as listed in the machine receipt.
- Failed mesh `32`; physical support URI ending in `support:2`.
- `left_q_w=268.4228547695099`, `right_q_w=268.42285476950997`.
- The values are adjacent binary64 numbers; the production midpoint formula
  rounds to the right endpoint.
- By the code path reaching the provider-floor handler, both endpoints were
  valid evaluations with non-null residuals, bracket signs were valid, and
  neither met `abs(F) <= 1e-6 W`. Consequently the left residual was below
  `-1e-6 W` and the right residual above `+1e-6 W`; exact magnitudes are not
  persisted.

Not present in committed Candidate A failure evidence: numerical-cell ID or
subdivision index, exact endpoint `F` values, left/right Task172 request or
result hashes/preimages, midpoint Task172 identity, provider PH coordinates,
selected shooting enthalpy, outer iteration, or a transient certificate bound
to the accepted physical trajectory. Old `n=1`/support-1 diagnostics are not
substituted for this `n=32`/support-2 failure.

Candidate B is only a control: its `n=32` mesh record is validated with 320
cells and 155402 Task172 evaluations. Its recorded decision-certificate set
for `n=32` is empty; its transient enclosure events occur at other mesh
states. It is not an equivalent support-2 endpoint pair and is not used to
derive policy.

## Authority and scope

The reviewed authority remains
`V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R2A`, hash
`25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e`.
Transient enclosure may only support invariant outer decisions. The accepted
trajectory must be rerun without enclosure and retain exact valid point-root
cells. This failure is the explicit accepted-path fail-closed condition in
the authority. No authority or tolerance change is proposed.

No production code, authority, candidate space, request, tolerance, or mesh
policy was changed. The only non-receipt edit is the authorized formatting-only
line wrap at line 254 of the prior completion replay script. No Rating, public
Sizing, or TASK175 execution occurred.

The evidence replay is
`docs/tasks/evidence/TASK-173-v0.7-candidate-a-accepted-trajectory-provider-quantization-blocker-adjudication-r1-replay.py`.
It verifies the blocked result hash, source binding, binary64 adjacency, and
the existing completion identity replay without invoking the solver.

`SECOND_COMPLETION_PUBLIC_SIZING_INVOCATION_AUTHORIZED=false`
`TASK175_RELEASE_ACCEPTANCE_PERFORMED=false`
`READY_AUTHORIZED=false`
`MERGE_AUTHORIZED=false`
`NEXT_GATE=OWNER_DIRECTION_REQUIRED_AFTER_CANDIDATE_A_PROVIDER_QUANTIZATION_ADJUDICATION`
`NEXT_GATE_EXECUTED=false`
