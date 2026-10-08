# TASK172 Stage-3 TMAX exact-zero state-identity portability correction R1

## Scope and result

This correction preserves an already-authorized thermodynamic state when, and only when, the cell heat-rate input is exactly `Decimal(0)`. A validated upstream TP state is unchanged at zero duty, so it is reused for the corresponding downstream and midpoint state. This avoids interpreting provider-output enthalpy as a new PH input coordinate.

The reconstruction authority is now `V07-T173-ENTHALPY-MIDPOINT-LOCAL-STATE-R2`, with the separate `V07-T173-ZERO-Q-STATE-IDENTITY-PORTABILITY-R1` authority. The cell-root solver remains R3 and the endpoint-hole classification authority is unchanged. This is a candidate pending exact-head CI; no production mesh was run.

## Boundary preserved

- The branch condition is exact `q == Decimal(0)`; no tolerance, epsilon, clipping, rounding, or platform-specific production value was introduced.
- At exact zero, tube downstream/local reuse the validated tube upstream `_ThermoState`; shell next/local reuse the validated shell physical-left `_ThermoState`. Snapshot and thermodynamic identities remain the same.
- For every nonzero `q`, including small positive values, the existing enthalpy propagation, H_MIN/H_MAX coordinate guards, and PH reconstruction path remain in force.
- PH inputs above frozen H_MAX remain rejected before the provider backend. H_MIN, H_MAX, T_MIN, and T_MAX are unchanged.
- Face IDs/hashes remain contextual: side, face index, coordinate, face count, producer authority, and thermodynamic identity are still part of the face projection. Reusing a thermo state does not reuse a distinct face identity.
- TASK172 acceptance, R98 (`C_round=1.0`), R3 classification, TASK171/TASK174, mesh policy, dependencies, lockfiles, and workflows are unchanged.

## Regression coverage and local replay

Tests cover the exact-zero TP state above H_MAX, absence of PH reconstruction, snapshot/state identity preservation, distinct face identities, strict above-H_MAX PH rejection, and unchanged small-positive-q blockers. R3's portable injected classification tests remain separate from native runtime characterization; historical native q/call/hash values are not frozen as cross-platform invariants.

The focused n=16 / outer-iteration-2 replay on local macOS/Python 3.14.5 records a valid first-support q=0 evaluation with the TMAX/H_MAX blocker removed. It reaches the target support; the target cell, isolated target replay, and outer trial classify `LOW_SIDE_DOMAIN_INFEASIBLE`. This is local runtime characterization, not a portability assertion. Four Linux PR-head/merge-ref Python 3.11/3.12 shards are evaluated by exact-head CI and their JUnit properties are the matrix evidence.

## Validation and lifecycle

Local focused TASK173 tests and the full shell-tube suite pass. Ruff, formatting, mypy, manifest D==M, `uv lock --check`, and `git diff --check` pass. `pip-audit` remains a separately reported known failure for `urllib3==2.7.0` (CVE-2026-97687, CVE-2026-97688, CVE-2026-97689; fixed in 2.8.0); no dependency or lockfile change is authorized here.

No full production mesh, mesh admission, TASK173 production result, or TASK175 release acceptance was performed. PR #283 remains OPEN/DRAFT; Ready and Merge are unauthorized. Exact-head CI run identity and final CI totals are recorded in the post-commit task receipt, because they cannot be included in the commit whose head they validate.
