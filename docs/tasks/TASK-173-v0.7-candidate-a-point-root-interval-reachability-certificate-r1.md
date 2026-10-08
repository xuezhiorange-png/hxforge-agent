# TASK173 Candidate A point-root interval reachability certificate R1

```text
TASK_ID=STAGE3_TASK173_CANDIDATE_A_POINT_ROOT_INTERVAL_REACHABILITY_CERTIFICATE_R1
REPOSITORY=xuezhiorange-png/hxforge-agent
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
START_HEAD=edc2dd877f98f72bf042ad348d68a07d30b34988
RESULT=CERTIFIED_NO_ORDINARY_POINT_ROOT_UNDER_FROZEN_NUMERICAL_MAPPING
PRODUCTION_CODE_CHANGED=false
TASK172_CONTRACT_CHANGED=false
R2A_AUTHORITY_CHANGED=false
NUMERICAL_TOLERANCE_CHANGED=false
FULL_N32_RECONSTRUCTION_EXECUTED=false
PUBLIC_FULL_RATING_REEXECUTED=false
PUBLIC_SIZING_REEXECUTED=false
TASK175_EXECUTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
```

## Conclusion

For the exact Candidate A n=32/support-2/subdivision-21 cell and its frozen
upstream state, the complete provider-input signature set is covered for all
three requested q coordinate definitions. With the production provider's
binary64 PH boundary and Task172's frozen precision-28, `ROUND_HALF_EVEN`
context, every reachable signature maps to one of the two replayed native
Task172 results. Every resulting residual is strictly outside the unchanged
`1e-6 W` ordinary point-root tolerance.

The classification is therefore
`CERTIFIED_NO_ORDINARY_POINT_ROOT_UNDER_FROZEN_NUMERICAL_MAPPING`. This is a
local discrete-mapping result only. It does not assert that the continuous
physical equation has no root, and it does not cover a changed provider
precision, Task172 numerical contract, or ambient Decimal context.

No new Task172 validation, provider call, cell solve, mesh reconstruction,
Candidate Rating, or Sizing call was made. The independent replay rehydrates
the saved native requests/results and verifies hashes; it does not call a
solver.

## Frozen target and identities

The exact failed cell is Candidate A
`adeab5b1-a339-5eb3-aa66-011ffe49bac0`, hash
`f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767`, rating
request hash
`1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7`, at
mesh n=32, outer iteration 24, support 2, subdivision index 21. The saved
shooting enthalpy is
`107518.9165931962933844840526580810546875 J/kg`; tube and shell cell IDs,
wall-interface ID, mesh identity, and upstream property snapshot hashes are
bound in the machine certificate.

The original binary64 endpoints are adjacent:

| Side | q passed to production | binary64 q | Task172 request / result | Native `q_TASK172` | Production F(q) |
|---|---:|---|---|---:|---:|
| LEFT | 268.4228547695099 W | `0x1.0c6c4035ce00bp+8` | `4fa675e1…c754` / `74881939…7ee9` | 268.4228600873843 W | −0.0000053178744 W |
| RIGHT | 268.42285476950997 W | `0x1.0c6c4035ce00cp+8` | `b2472ec6…e072` / `ea8869a5…3573` | 268.4228395792577 W | +0.00001519025227 W |

Both Task172 results are `VALIDATED`. The exact full hashes, the binary64
exact-decimal q values, both exact F representations, endpoint request/result
preimages, provider snapshots, and upstream identities are in the JSON
certificate. In production, `_d(float)` uses `Decimal(str(float))`; the
`F(q)` values above are the exact values used by the existing cell-root
contract. The separate `Decimal.from_float(q)` F values are recorded but are
not substituted for that production projection.

R2 captured the target endpoint control mode as `DISABLED`: these are the
accepted-trajectory trials. R2 also records an outer-search decision
certificate (`f66ddbd80ddab94d6dfe050387d376841b6a0b27976d7ea381964390523f9dde`)
from its DETECT/LEFT_BRANCH/RIGHT_BRANCH transient search. That certificate is
not an accepted-cell enclosure and does not change the accepted-path point-root
requirement. R2A still forbids an enclosure on the accepted trajectory.

## Full interval mapping

The exact production propagation at precision 70 is:

```text
tube downstream = h_tube_upstream - q / 12
shell next      = h_shell_left   - q / 20
tube midpoint   = h_tube_upstream - q / 24
shell midpoint  = h_shell_left   - q / 40
```

Every expression is monotone nonincreasing in q. Decimal division and the
subsequent round-half-even operations are monotone; conversion to binary64 is
also monotone. Thus endpoint coordinate floats bound every intermediate
coordinate. The endpoints show the first, second, and fourth coordinates are
constant; the third is either constant or crosses one boundary between a
single pair of adjacent binary64 values. There is no unexamined intermediate
float signature. The 65 R3 samples are corroborating evidence only and are
not used as interval coverage.

| q definition | Complete reachable provider signatures | Task172 mapping under p28 baseline | Conservative minimum `abs(F)` |
|---|---:|---|---:|
| A. Production binary64 q values, converted by `Decimal(str(float))` | 2 (the two adjacent float points) | LEFT and RIGHT saved native results | 0.0000053178744 W |
| B. Closed interval between `Decimal.from_float(left/right)` | 1 (RIGHT signature throughout) | RIGHT request/result | 0.00001519025221096600773744285106658935546875 W |
| C. Closed decimal-string interval [`268.4228547695099`, `268.42285476950997`] | 2 (LEFT then RIGHT; only tube midpoint changes) | LEFT and RIGHT saved native results | 0.00000531787433 W |

For case C the exact real-affine rounding boundary for the tube-midpoint
coordinate is
`q = 268.4228547695099019348621368408203125 W`. It lies strictly inside the
string interval. The two float values are adjacent, and the lower value has an
even significand, so a tie in the exact affine map rounds to that lower value.
This ideal-affine boundary is explanatory; interval coverage does not assume
the rounded p70 implementation switches at that exact q. Instead, replay runs
the same p70 Decimal operations at both closed-interval endpoints. Their tube-
midpoint binary64 outputs are adjacent and the other three outputs are equal.
Since every operation and float conversion is monotone, every actual p70
intermediate output lies between those endpoints; adjacency proves that only
the two saved signatures are reachable, regardless of a sub-ULP shift in the
transition location.

The Task172 request has no independent q field. The request projection does
change between endpoints only at `tube_bulk_state.temperature_k`; replay binds
that value exactly to the temperature output in the third (tube-midpoint) PH
snapshot. All other native request projection fields are identical. Thus this
additional Task172 input is a deterministic provider-output component of the
same PH signature, not an untracked q coordinate. Across the committed R2
target-cell ledger, 727 provider-bearing trials contain 719 distinct full PH
signatures; repeated signatures have no provider-snapshot, Task172-request, or
Task172-result identity conflicts. This is run evidence for stable mapping,
not a claim about other contexts or changed runtime/provider state. For each
reachable interval signature, the complete native request projection/hash
and validated result preimage/hash replay to the R2 endpoint. The provider
identity is fixed to CoolProp HEOS::Water 8.0.0, revision
`ae81610e7d23efc57f9d051c8e70a4d66e87537f`, reference state DEF, and the saved
configuration fingerprint. Equal PH inputs replay equal saved property
snapshot hashes. The controlled right-request repeats also establish the p28
Task172 result hash twice.

Task172 is Decimal-context-sensitive: the controlled precision-100 context
produces a different result identity for the same RIGHT request. Those p100
results are deliberately excluded from the frozen production map. This
certificate binds Task172 to the R2 production baseline context, precision 28
and `ROUND_HALF_EVEN`, as supported by the R2 context evidence and production
call path. The context receipt says actual per-call Decimal flags were not
captured; the runtime does not use sticky flags as calculation inputs.

For case C, a conservative superset bound applies the full q interval to each
of the two fixed Task172 outputs:

```text
LEFT signature:  F(q) in [-0.0000053178744, -0.00000531787433] W
RIGHT signature: F(q) in [+0.0000151902522, +0.00001519025227] W
```

The actual signature subintervals are narrower. Even these conservative
bounds remain outside `[-0.000001, +0.000001] W`. Case B has the single
positive F interval shown above; case A has only the two out-of-tolerance
endpoint F values.

## R2/R3/context evidence replay

The R2 compact summary and its 749-trial ledger replay; both endpoint native
request and result preimages, all four provider snapshots per endpoint, and
the frozen binary64 adjacency replay. The R3 evidence replays all 65 historical
probe identities and confirms its one signature is the RIGHT signature, but
does not supply this certificate's interval proof. The Decimal-context
adjudication replays the two p28 result hashes, the two p100 result hashes,
and confirms context causality. The exact R2 runtime tree and Rating/Task172
source blobs are unchanged through the evidence head.

The machine certificate's canonical hash and independent replay bind the
formulas, endpoint identities, all reachable signatures, threshold, residual
bounds, evidence sources, and scope flags. Replay output includes
`ALL_REACHABLE_TASK172_SIGNATURES_COVERED=PASS` and
`NO_SOLVER_OR_PROVIDER_CALLS=PASS`.

## Owner decision package

The local failure mechanism is a deterministic mapping step, not a sign test:
over the decimal-string interval, the tube-midpoint provider coordinate steps
by one binary64 ULP. The corresponding p28 Task172 signed heat rate jumps from
`268.4228600873843 W` to `268.4228395792577 W`; `F(q)` jumps from the negative
side to the positive side while skipping the frozen tolerance band. Under the
exact `Decimal.from_float` interval the provider signature stays on the RIGHT
state and F remains positive. The raw production float grid contains only its
two endpoints, both outside tolerance.

R2A cannot rescue this accepted trajectory: its reviewed scope allows an
enclosure only as a transient outer-search decision diagnostic, requires both
real endpoint continuations and decision invariance there, and explicitly
prohibits accepted-path enclosure. It does not turn a provider span into an
ordinary valid cell root.

Any recovery that changes the reachable numerical map needs owner numerical-
authority authorization before implementation. Options for a separately
reviewed decision are:

1. A higher-resolution provider PH input/solver boundary. This can expose
   additional property states but changes Task172 request identities and
   requires provider-state, physical-domain, conservation, result-hash, and
   deterministic replay evidence.
2. A reviewed Task172 numerical-method/context correction. This can change
   constitutive HTC/Jmu and the result projection/hash even for the same
   request, so it must retain native acceptance, residual and conservation
   guarantees and be requalified for deterministic identity.
3. A different accepted-path decision rule (for example an enclosure or a
   relaxed tolerance) is not a permissible implementation-only fix; it would
   contradict the reviewed point-root boundary and requires an explicit new
   authority.

Merely increasing q precision is insufficient: cases B and C cover exact
Decimal q intervals and still have no accepted root under the current binary64
provider interface and p28 Task172 map. This is not permission to change
tolerance or to introduce accepted-path enclosure. No option is implemented
here.

```text
PRODUCTION_CODE_CHANGED=false
TASK172_CONTRACT_CHANGED=false
R2A_AUTHORITY_CHANGED=false
NUMERICAL_TOLERANCE_CHANGED=false
CANDIDATE_SPACE_CHANGED=false
FULL_N32_RECONSTRUCTION_EXECUTED=false
PUBLIC_FULL_RATING_REEXECUTED=false
PUBLIC_SIZING_REEXECUTED=false
TASK175_EXECUTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=OWNER_NUMERICAL_DIRECTION_AFTER_INTERVAL_REACHABILITY_CERTIFICATE
NEXT_GATE_EXECUTED=false
STOP=true
```

The evidence-only commit SHA is the final evidence head; it is reported in the
task receipt rather than embedded in this file, avoiding a self-referential
commit identity.
