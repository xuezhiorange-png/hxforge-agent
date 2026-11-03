# R12 Experimental Numerical Authority Admission (CANDIDATE)

## Verified physics and conservation

- Countercurrent enthalpy march with per-cell Task172 `VALIDATED` closure and F(q) residual ≤ 1e-6 W.
- Whole-exchanger energy balance within `max(ENERGY_ACCEPTANCE_FLOOR_W, duty_roundoff_floor_w)`.
- Terminal boundary predicates via production `_terminal_tolerance_pass`.
- Task174 pressures taken only from bound `Task174SuccessResult` hashes (no estimation).

## Cell root numerical method gap

- **Production:** `CELL_ROOT_SOLVER_AUTHORITY_ID` + R2A provider enclosure certificates.
- **Experimental:** R2 coupled-cell fast path (`V07-FAST-SOLVER-COUPLED-CELL-R2`) with production F(q) acceptance tolerances but without R2A determinism replay parity.

## Outer bracket algorithm scope

- Narrow-bracket / continuation outer solve (R7–R10) is **CANDIDATE** only; requires archived bracket evidence for high-n admission.
- R3 `solve_fast_outer_boundary` bisection + R2 trials is used for **live n=1** samples only in R12.

## R2A provider enclosure certificate gap

- No production R2A transient decision enclosure bundle on experimental fast paths.
- Frozen replay uses strict mesh hash parity at pinned shooting enthalpy, not production determinism replay gate.

## Frozen replay vs live solve evidence

| Mode | Evidence | Authority |
|------|----------|-----------|
| `FROZEN_EVIDENCE_REPLAY` | R8/R9/R10 pinned JSON + strict n=32/n=64 replay | CANDIDATE_UNAPPROVED |
| `LIVE_NUMERICAL_SOLVE` | Fresh outer boundary worker output | CANDIDATE; not a full mesh ladder |

## Acceptable numerical deviation criteria

- Mesh compare thresholds: production `_compare_meshes` predicates (duty, wall, terminal bands).
- Cell F(q): absolute residual ≤ 1e-6 W vs Task172 signed duty.
- Terminal: production `TERMINAL_TOLERANCE_K` acceptance.

## Production authority (not granted)

- Status remains **CANDIDATE** / **CANDIDATE_UNAPPROVED**; not `VALIDATED`.
- `PRODUCTION_INTEGRATION=false`; no merge to main / PR #283 / TASK175.

## Arbitrary new candidates

- Not verified beyond explicit live n=1 smoke for bound `CandidateRatingRequest`.
- Full mesh rating ladder for unknown candidates: **out of scope** (`ARBITRARY_CANDIDATE_FULL_RATING_VERIFIED=false`).
