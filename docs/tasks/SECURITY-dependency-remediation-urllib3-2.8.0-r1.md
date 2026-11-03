# Security dependency remediation: urllib3 2.8.0 R1

## Scope and status

This is a targeted transitive lockfile remediation based on predecessor HEAD `c0193c2e4d77caea13d763b7fb1b13900a9b49fa`. `urllib3` is not declared in `pyproject.toml`; the existing `requests==2.34.2` lock entry depends on it. Only `uv.lock` was changed by the package resolution: `urllib3` moved from 2.7.0 to 2.8.0, with its source and wheel metadata refreshed. `requests` remained 2.34.2. No project dependency declaration was added.

The predecessor exact-head CI run `36846190581` matched the pinned head and failed only at `lint` (`pip-audit`) and its dependent `final-gate`. The reported findings were CVE-2026-97687, CVE-2026-97688, and CVE-2026-97689 for `urllib3==2.7.0`, with 2.8.0 identified as the fix version.

## Local verification

The targeted command `uv lock --upgrade-package urllib3==2.8.0` resolved 75 packages and reported only `urllib3 v2.7.0 -> v2.8.0`. The lock diff changes that package's version, sdist URL/hash/metadata, and wheel URL/hash/metadata. `pyproject.toml` is unchanged and contains no `urllib3` declaration.

`uv lock --check` and `uv sync --locked --all-extras` passed. The locked environment reports `urllib3==2.8.0` and `requests==2.34.2`; the resolved dependency tree still shows `requests -> urllib3`. `uv run --locked pip-audit` reported no known vulnerabilities. It skipped the local `heat-exchanger-design-agent==0.6.0` distribution because it is not available on PyPI for audit; this is not a vulnerability finding.

Focused TASK173 tests passed (53 tests); the full shell-tube suite passed (2,250 passed, 4 skipped); HTTP/API regression passed (21 tests). Ruff, formatting, the CI-scope mypy check (450 source files), manifest D==M (259 discovered and 259 manifested), lock validation, and `git diff --check` passed.

## Authority and change boundary

The Stage-3 authority IDs and canonical hashes are unchanged from the predecessor. No Stage-3 source, tests, numerical policy, workflow, or project dependency declaration changed. No production mesh was run, no TASK173 result was created, and TASK175 was not performed.

The candidate exact-head CI and its four Python/Linux shard runtimes are required after the candidate commit. This record intentionally identifies those measurements as pending at commit time; the final exact-head run, shard results, and runtime-budget decision are recorded in the PR metadata and final task receipt so the tested repository head remains exact.

PR #283 remains OPEN/DRAFT. Ready and Merge are unauthorized. After successful exact-head CI, the next gate is `STAGE3_PRODUCTION_MESH_REEXECUTION_FROM_N1_AFTER_R3_ZERO_Q_AND_SECURITY_CLOSURE`; this remediation does not itself authorize that mesh execution.
