# TASK172 Stage-3 zero-q portability CI runtime correction R1

## Scope and status

This is a test-contract and CI-runtime candidate based on `89437883ff47a3ec7915118ce0a0152636e62989`. Production code, the zero-q implementation, R3 classification, TASK172 acceptance, mesh policy, dependencies, lockfiles, workflows, and CI timeout remain unchanged.

The standard suite no longer collects the full native n=16/outer-iteration-2 trajectory as a portable test. Its historical production characterization remains in the earlier R1 evidence. The test function is retained under a non-`test_` name as a manual-only characterization harness; cross-platform assertions are instead made by deterministic zero-q and injected R3 contract tests, with one light native-provider smoke at the first n=16 support.

## Test contract

- The Linux-style deterministic provider test keeps the TMAX/TMIN enthalpy offsets and verifies exact-zero state reuse, no PH reconstruction, request construction, and unchanged thermodynamic snapshot identities.
- Positive-q tests continue to exercise the existing H_MAX guards. No epsilon or wider acceptance is introduced.
- The injected R3 endpoint-hole test remains the portable classification contract; it does not freeze native trajectory hashes, call counts, or residual values.
- The new native smoke uses `CoolPropProvider`, `build_local_support(0, 16, 0)`, the approved TMAX/TMIN inlet states, and a sentinel at `task172_validate` after a valid `Task172LocalRequest` has been built. It does not execute the expensive local TASK172 solve or a full n=16 trajectory.
- The prior full native n=16 trajectory remains historical characterization/production evidence, not a portable CI invariant.

## Validation and CI boundary

Local validation on this candidate's test change: the focused selection passed 11 tests; the complete TASK173 test module passed 53 tests in 9.28 seconds; the full shell-tube suite passed in 29.99 seconds. Ruff, formatting, mypy, manifest D==M, `uv lock --check`, and `git diff --check` passed. `pip-audit` remains a separate known failure for `urllib3==2.7.0` (CVE-2026-97687, CVE-2026-97688, CVE-2026-97689; fix version 2.8.0); dependency remediation is out of scope.

Predecessor exact-head run `36826527880` was not runtime-budget-stable: PR-head Python 3.11 exceeded the 540-second target, PR-head Python 3.12 timed out at 600 seconds, and the completed merge-ref Python 3.11/3.12 test steps were also above the 540-second target. The new exact-head CI must report all four candidate shard runtimes. The committed evidence records predecessor facts and the required candidate matrix; the exact run/head and observed runtimes are reported in the final task receipt so this commit remains the exact head tested.

No production mesh was run, no TASK173 production result was created, and TASK175 was not performed. PR #283 remains OPEN/DRAFT; Ready and Merge are unauthorized.
