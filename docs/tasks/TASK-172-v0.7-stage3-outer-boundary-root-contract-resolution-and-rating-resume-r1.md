# TASK172 v0.7 Stage 3 — Outer Boundary Root Contract and Rating Resume

## Result

`RESULT=STAGE3_BLOCKED_INTEGRATED_RATING_CONTRACT`.

The one-sided feasibility-boundary bisection resolves the countercurrent outer-root contract for a target exactly at the approved property-domain lower boundary. The n=1 base-mesh rating trajectory closes and remains diagnostic only. The first refined level, n=2, stops at a native TASK172 `BLOCKED_RESIDUAL_ACCEPTANCE`; under the approved classification this is a hard blocker, not a low-side domain-infeasible shooting trial. No finer mesh was run and production mesh admission remains false.

This is not a property-domain, inlet-state, flow-orientation, TASK172-physics, or TASK174-hydraulic change. No TASK172 tolerance or equation was relaxed.

## Effective reviewed inputs

Stage 2 remains based on corrected native identities: TASK031 geometry `1dc32d501ee1ba283e4d2bb5eab2f2f5ffc81e464fd6f254ff13b02ceb01519e`; TASK032 result `58e47124f94d14ece0f1c93a0bb5510b7dda52bfbc60b9f650fbf72c1eb232d2`; TASK166 result `a42aee19a2fbb77d1666e4b7170b86e3a9e036f992ef8030a9c2ecf1928c151d`; and TASK174 result `ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419`. The complete persisted bundle is revalidated by independently rerunning native TASK031 → TASK032 → TASK166 and replaying the persisted TASK172 request/result identity. TASK172's producer is invoked for each live TASK173 support; the historical accepted reference result is not rerun as part of shell-flow authority replay. No test fixture supplied production authority, no superseded identity was used, and TASK174 hydraulics were composed rather than recalculated.

The fixed-geometry reference case is R2, with tube HOT at 300 K and 12 kg/s, shell COLD at 298.15 K and 20 kg/s, and thermal property evaluation at 101325 Pa. Sizing has no target and is not applicable.

## Outer boundary solver

The Stage-3 candidate binds `V07-T173-OUTER-BOUNDARY-FEASIBILITY-BISECTION-R1`, using `ONE_SIDED_FEASIBILITY_BOUNDARY_BISECTION` in shell-outlet specific enthalpy over the approved interval 104920.11980926784–112654.89965462626 J/kg. The exact target is the lower-bound shell-inlet enthalpy 104920.11980926784 J/kg. The low search endpoint is `LOW_SIDE_DOMAIN_INFEASIBLE`; the accepted endpoint must always be `VALID_TRAJECTORY` with a nonnegative terminal residual. The infeasible endpoint is never a physical result and no property call is made below the lower enthalpy bound.

The boundary solver does not seek a valid negative-residual trajectory: every valid admissible terminal state is at or above the target. The algorithm bisects the feasibility boundary, checks observed classification ordering, and is capped at 128 iterations. The approved property domain is enforced on returned temperature, pressure, phase, and provider identity. `H_MIN`/`H_MAX` remain hard bounds on the shooting coordinate and every PH input before backend evaluation; a TP state's returned enthalpy is retained as provider output and is not reinterpreted as a shooting input. The exact `H_MAX` endpoint is produced by a native TP query at 300 K. No PH clipping or domain expansion is used; there is no extrapolation, clipping, backend fallback, or partial-result promotion.

## Execution evidence

At n=1 (five tube cells, five shell cells, five wall interfaces), the integrated countercurrent trajectory completed with 27 outer bisection iterations. Duty was 52362.216167533693 W; tube and shell outlets were 298.9562992655767 K and 298.7761641216321 K. Hot energy loss, cold energy gain, and wall-duty sum were 52362.21616753357 W, 52362.21616753369 W, and 52362.216167533693 W; maximum energy-balance residual was 0.00000000012 W. Minimum approach was 0.80629925887034 K. This is a base-mesh diagnostic, not convergence or admission evidence.

At n=2, outer iteration 5 and shell-outlet shooting enthalpy 107578.950381109796875 J/kg, native TASK172 rejected the local constitutive result for the first numerical support in physical interval [4.8, 6.0] m. Its blocker was `BLOCKED_RESIDUAL_ACCEPTANCE`, surfaced by TASK173 as `BLOCKED_TASK172_LOCAL_CONSTITUTIVE_CLOSURE`. This is an unrelated native local-closure failure, so the outer solver stops as `HARD_BLOCKER`; it is not relabeled as low-side infeasibility. The exact identities, state values, and native residual diagnostics are in the evidence JSON.

Because n=2 did not complete, no pairwise mesh comparison exists. Levels n=4, 8, 16, 32, and 64 were not executed; no candidate or headroom level was established. Therefore `REAL_CASE_MESH_ADMISSIBLE=false` and `TASK173_REFERENCE_CASE_SOLVED=false` for the required production-mesh case, even though the n=1 diagnostic trajectory itself closed.

## Scope and lifecycle

The native TASK173 API, enthalpy face propagation, midpoint PH reconstruction, local TASK172 invocation, replay binding, and one-sided outer solver are implemented as a Stage-3 candidate. Stage-1 and Stage-2 reviewed authorities were not modified. The Stage-3 candidate is not self-approved and remains subject to one independent review after the integrated rating and mesh-admission blocker is resolved. TASK175, Ready, and Merge were not performed or authorized.

`NEXT_GATE=STAGE3_INTEGRATED_RATING_CONTRACT_RESOLUTION`

`STOP=true`

Machine-readable evidence: [TASK-172-stage3-outer-boundary-root-contract-resolution-and-rating-resume-r1.json](evidence/TASK-172-stage3-outer-boundary-root-contract-resolution-and-rating-resume-r1.json).
