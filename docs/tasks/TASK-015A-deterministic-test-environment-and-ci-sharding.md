# TASK-015A — Deterministic Test Environment and CI Sharding: Design Contract

**Issue:** #33
**Status:** DESIGN READY_FOR_REVIEW
**Implementation Authorization:** NOT GRANTED
**TASK-015A Design Frozen Contract SHA:** Pending — to be set to the exact independently approved reviewed Head commit SHA

> Note: TASK-010 has its own frozen contract SHA: `9a1faeb92f4015a62f9d9add0739f3853a876415`.
> TASK-015A design contract SHA is distinct and pending independent approval.

---

## 1. Objective

Establish a deterministic, reproducible, and maintainable test environment for HXForge that eliminates hidden test files, provides explicit per-shard file manifests verified at pytest node-ID level per Python version, replaces ad-hoc `--ignore` with structured test partitioning, introduces typed provider test doubles conforming to the real `PropertyProvider` protocol, separates CoolProp-dependent tests from pure unit tests, adds mandatory CI telemetry with rerun-safe artifact identity under full-workflow-rerun-only policy, and defines clear authority for PR-head, merge-ref, and main-push CI tracks — all executed exclusively through the `uv`-managed locked project environment.

## 2. Scope

1. Dependency lock via `uv.lock` with freshness gate
2. Frozen `uv` installation authority (`astral-sh/setup-uv` with pinned commit SHA)
3. Locked environment execution authority (`uv run --locked` for all commands)
4. Pytest marker taxonomy
5. Test shard manifest specification with per-Python-version node-ID completeness proof
6. Typed `PropertyProvider` test doubles (real protocol)
7. CoolProp test isolation
8. Mandatory test coverage with event-local aggregation
9. JUnit, durations, coverage, resource telemetry with attempt-safe identity
10. PR-head, merge-ref, main-push tri-track CI authority
11. Full-workflow-rerun-only policy
12. Nightly full regression
13. Golden and benchmark test separation
14. Structured pytest collection plugin with global/shard scope
15. Behavior-affecting environment equality contract
16. Workflow/job naming stability
17. Rollout, migration, and rollback strategy

## 3. Non-goals

- No TASK-011 benchmark implementation
- No new exchanger type
- No TASK-010 frozen contract changes
- No pressure-drop, velocity-constraints, materials, cost, or mechanical compliance features
- No database, ORM, object storage, authentication, or authorization
- No frontend changes
- No PDF engine introduction
- No minimum coverage percentage threshold in TASK-015A

## 4. Current CI and Test Topology Inventory

### 4.1 CI workflow

File: `.github/workflows/ci.yml`
Triggers: `pull_request`, `push.branches: [main]`
Python matrix: 3.11, 3.12

### 4.2 Current jobs (authoritative as of main HEAD `a3a352a2`)

| Job | Python | Actual command | Notes |
|---|---|---|---|
| `task010-focused (3.11)` | 3.11 | `ruff check .` + `ruff format --check .` + `mypy` + `pytest -x --timeout=120 tests/unit/test_task010_final.py tests/unit/test_task010_phase1.py tests/unit/test_task010_phase2.py` + `pip-audit` | Lint+mypy+tests+audit |
| `task010-focused (3.12)` | 3.12 | Same as above | Same on 3.12 |
| `integration` | 3.12 | `pytest -x --timeout=120 tests/integration/` | Integration only |
| `repository-core` | 3.12 | `pytest -x --timeout=120 --ignore=tests/unit/test_double_pipe_correction_r10.py --ignore=tests/unit/test_double_pipe_correction_r12.py -q` | Implicit remainder shard |
| `units` | 3.12 | `pytest --timeout=120 tests/unit/test_units.py -q` | Unit conversions only |
| `correction-r10` | 3.12 | `pytest --timeout=120 tests/unit/test_double_pipe_correction_r10.py -q` | Correction r10 |
| `correction-r12` | 3.12 | `pytest --timeout=120 tests/unit/test_double_pipe_correction_r12.py -q` | Correction r12 |

### 4.3 Known issues

- `repository-core` uses `--ignore` creating implicit remainder shard
- `test_units.py` executed by both `repository-core` and `units` — duplicate
- TASK-010 focused tests also in `repository-core` — duplicate
- No formal dependency lock, no pytest marker taxonomy
- `MagicMock` as provider without typed protocol conformance
- No PR-head vs merge-ref distinction
- Commands from system Python, not locked `uv` environment

## 5. uv Installation Authority

### 5.1 Frozen installation

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39  # v8.2.0
  with:
    version: "0.11.25"

- name: Verify uv version
  run: test "$(uv --version)" = "uv 0.11.25"
```

- **Action:** `astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39` (v8.2.0)
- **uv version:** `0.11.25`
- **Version assertion:** `test "$(uv --version)" = "uv 0.11.25"`
- **Auto-update:** NOT allowed — SHA pinned
- **Version upgrade:** requires governance approval, new SHA, new review

If `setup-uv` cannot provide the version, CI must FAIL. No fallback.

### 5.2 Lock freshness gate

```yaml
- name: Check lock freshness
  run: uv lock --check
- name: Install from lock
  run: uv sync --locked --all-extras
- name: Verify no lock drift
  run: git diff --exit-code -- uv.lock pyproject.toml
```

## 6. Locked Environment Execution Authority

### 6.1 Unique execution rule

Every executable MUST resolve from `uv run --locked`.

```bash
uv run --locked python -c "import sys; print(sys.executable)"
uv run --locked pytest --version
uv run --locked coverage --version
uv run --locked mypy --version
uv run --locked ruff --version
```

### 6.2 Mandatory commands

```
uv run --locked pytest ...
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked pip-audit
uv run --locked coverage combine
uv run --locked coverage xml
uv run --locked coverage report
```

### 6.3 Prohibited forms

- `uv run pytest` (without `--locked`)
- bare `pytest`, `python -m pytest`, `.venv/bin/pytest`
- Any command not via `uv run --locked`

## 7. Python Version Support

Supported: 3.11, 3.12. CI matrix tests both. No 3.13+ features without approval.

## 8. Pytest Marker Taxonomy

| Marker | Description |
|---|---|
| `pure` | Pure unit tests, no CoolProp, no provider |
| `provider` | Property provider contract tests |
| `coolprop` | CoolProp backend integration |
| `integration` | Multi-component integration tests |
| `golden` | Deterministic correctness regression against approved baseline |
| `benchmark` | Performance measurement, not correctness authority |
| `slow` | Long-running tests (>30s) |

### 8.1 Marker combination legitimacy

| Combination | Allowed |
|---|---|
| `pure` only | Yes |
| `provider` only | Yes |
| `coolprop` only | Yes |
| `golden` + `pure` / `provider` / `coolprop` | Yes |
| `benchmark` + `pure` / `coolprop` / `slow` | Yes |
| `golden` + `benchmark` | No (mutually exclusive) |

### 8.2 Rules

- Every test file tagged with at least one marker
- Markers classify semantics, not shard ownership
- Marker filter must not cause nodes to silently disappear

## 9. Test Shard Manifest

### 9.1 Format

```yaml
version: "1"
shards:
  - name: <shard-name>
    job: <ci-job-name>
    python: ["3.11", "3.12"]
    files:
      - tests/unit/test_file_a.py
    timeout: 120
```

### 9.2 Schema validation

Reject: duplicate shard/job names, duplicate files, empty shards, non-existent paths, directories, globs, `..` traversal, paths outside repo root, symlinks outside test root, non-canonical paths, non-test files, Python versions outside `{3.11, 3.12}`, non-positive timeout, unknown fields.

### 9.3 File-level completeness

File ownership is global, version-independent:

```python
def verify_file_completeness(manifest, test_root):
    D = set(discover_all_test_files(test_root))
    M = set()
    for shard in manifest["shards"]:
        for f in shard["files"]:
            assert f not in M
            M.add(f)
    assert D == M  # bidirectional
```

### 9.4 Per-Python-version node-ID completeness

```python
PythonVersion = Literal["3.11", "3.12"]

def verify_per_version(G_v, S_v_i, manifest):
    for version in ("3.11", "3.12"):
        applicable = [s for s in manifest["shards"] if version in s["python"]]
        union = set()
        for s in applicable:
            union |= S_v_i[(version, s["name"])]
        assert union == G_v[version]
        for a, b in pairwise(applicable):
            assert S_v_i[(version, a["name"])] & S_v_i[(version, b["name"])] == set()
```

Shards not supporting a version are excluded from that version's union and do not generate artifacts. Zero-node files under a version are a legal version condition (see Section 17).

## 10. "--ignore" Elimination

Replace `--ignore` with explicit file lists. Completeness verifier + plugin required in same PR as shard cutover.

## 11. CoolProp Test Isolation

- `@pytest.mark.coolprop` required
- Dedicated shards, timeout 180s
- Do not share shard with pure unit tests

## 12. Typed PropertyProvider Test Doubles

### 12.1 Real protocol

Source: `src/hexagent/properties/base.py`

```python
class PropertyProvider(Protocol):
    name: str
    version: str
    git_revision: str
    reference_state_policy: ReferenceStatePolicy
    def state_tp(self, fluid, temperature_k, pressure_pa) -> FluidState: ...
    def state_ph(self, fluid, pressure_pa, enthalpy_j_kg, *, reference_state) -> FluidState: ...
    def saturation_at_pressure(self, fluid, pressure_pa) -> SaturationState: ...
    def saturation_at_temperature(self, fluid, temperature_k) -> SaturationState: ...
    def cache_info(self) -> PropertyCacheInfo: ...
    def clear_cache(self) -> None: ...
```

### 12.2 Canonical fluid identity

```python
def canonical_fluid_identity(fluid: FluidIdentifier | str) -> str:
    return FluidIdentifier.from_value(fluid).cache_identity
```

### 12.3 Query key types

All keys via `from_request()` factory. Hand-built identity prohibited.

### 12.4 Doubles

- **StubPropertyProvider:** Fixed typed results. Unconfigured → error. `cache_info()` zeros. `clear_cache()` no-op.
- **ReplayPropertyProvider:** Ordered sequences. Exhausted → error. `assert_fully_consumed()`. `cache_info()` zeros. `clear_cache()` no-op (does NOT clear queues/positions/log/index). Optional `reset_replay()`.
- **SelectiveFailurePropertyProvider:** Wraps real provider. Failure map `(query_type, int)` indexed from 1. Failure BEFORE delegation. All four query types. Identity/cache from inner.
- **CountingPropertyProvider:** Per-query-type counters. Records tuples. Failed calls counted. `reset_counts()`. Identity/cache from inner.

### 12.5 Acceptance

mypy proves protocol satisfaction. All return `FluidState`/`SaturationState`. No bare MagicMock success path.

## 13. CI Tri-Track Authority

- **Track A (PR Head):** Checkout `ref: head.sha`, assert SHA match. Jobs: `pr-head / <shard>`.
- **Track B (Merge Ref):** Checkout `refs/pull/N/merge`, assert SHA. Jobs: `merge-ref / <shard>`.
- **Track C (Main Push):** Checkout `ref: github.sha`, assert SHA. Jobs: `main / <shard>`.

Both PR-head and merge-ref required for merge. Merge-ref NOT optional. `pull_request_target` prohibited. Fork PRs must not use secrets.

## 14. Full-Workflow-Rerun-Only Policy

### 14.1 Rerun policy

**Allowed:**
- Initial full workflow run
- Re-run all jobs (full workflow rerun)

**Prohibited:**
- Re-run failed jobs only
- Re-run one individual job
- Aggregate current-attempt artifacts with previous-attempt producer artifacts

### 14.2 Same-attempt invariant

Let `A = github.run_attempt`. For every required job in the workflow:

- `producer_job.run_attempt == A`
- `aggregate_job.run_attempt == A`
- `artifact_metadata.run_attempt == A`
- `artifact_name.attempt == A`

If any required producer job did not execute in current attempt: overall workflow acceptance = FAIL.

### 14.3 Attempt completeness manifest

Each aggregate job generates expected identity set:

```python
ExpectedIdentity = NamedTuple("ExpectedIdentity", [
    ("run_id", str),
    ("run_attempt", int),
    ("track", str),
    ("shard", str),
    ("python_version", str),
    ("commit_sha", str),
    ("artifact_kind", str),
])
```

Proves: `downloaded identities == expected identities`. Fails if any artifact from old attempt, any required producer missing, any identity missing/duplicated, SHA/track mismatch.

### 14.4 UI operation governance

Operators must use "Re-run all jobs". "Re-run failed jobs" and individual-job rerun do not produce an authoritative TASK-015A CI result. If a prohibited partial rerun occurs, that attempt cannot serve as PR blocking CI authority; a full workflow rerun is required. This contract cannot technically prevent the GitHub UI button — it governs acceptance and authority rules.

## 15. Nightly Full Regression

Separate from PR-blocking. Full suite including golden, benchmark, slow. Failures create issues. Artifacts retained 30 days.

## 16. Timeout, Cancellation, and Retry

| Type | Timeout |
|---|---|
| Default | 120s |
| CoolProp | 180s |
| Golden | 300s |

Infrastructure retry is acceptable only as a full workflow rerun. No automatic test retry (determinism). Runner-side cancellation recorded.

## 17. Zero-Node Version Semantics

### 17.1 Frozen reason-code enum

```python
ZeroNodeReason = Literal[
    "conditional-definition",
    "module-collection-skip",
    "hook-deselection",
    "unsupported-version",
]
```

### 17.2 Reason definitions

- **conditional-definition:** Test definition is inside a Python/version conditional branch; no pytest item created under that version.
- **module-collection-skip:** Module uses `pytest.skip(..., allow_module_level=True)` during collection, preventing node creation. Distinct from execution-time skip.
- **hook-deselection:** An approved collection hook explicitly deselects items. Must record: hook authority, deselected node IDs, deselection count, reason code.
- **unsupported-version:** Manifest or approved version contract explicitly states the file does not apply under that Python version. Cannot be inferred.

### 17.3 Prohibited as zero-node reason

- Execution-time skip, `@pytest.mark.skip`, `@pytest.mark.skipif`, `xfail`
- Test failure, import error, plugin error, collection crash
- Free text, "unknown", "other"

Import/plugin/collection errors must FAIL the collection, not produce zero-node records.

### 17.4 Zero-node metadata

```json
{
  "file": "tests/unit/test_example.py",
  "python_version": "3.11",
  "node_count": 0,
  "zero_node_reason": "conditional-definition",
  "reason_authority": "approved manifest or collection metadata",
  "evidence": "stable identifier"
}
```

Rules: `node_count > 0` → `zero_node_reason` must be `null`. `node_count == 0` → reason must be in frozen enum, `reason_authority` must exist, `evidence` non-empty. Unknown reason → FAIL.

### 17.5 Acceptance fixtures

- Execution-time skip still appears in node inventory (node_count > 0)
- `skipif` still appears in node inventory
- Conditional test definition may produce zero nodes
- Module-level collection skip produces approved zero-node record
- Hook deselection records deselected node IDs
- Unsupported-version requires explicit authority
- Unknown zero-node reason fails

## 18. Structured Pytest Collection Plugin

### 18.1 Implementation location

Frozen: `tests/ci/collect_nodes_plugin.py`

### 18.2 Collection scope

```python
CollectionScope = Literal["global", "shard"]
```

### 18.3 Global inventory

```json
{
  "schema_version": "1",
  "collection_scope": "global",
  "python_version": "3.11",
  "pytest_version": "9.1.1",
  "commit_sha": "string",
  "track": "pr-head",
  "shard": null,
  "run_id": "string",
  "run_attempt": 1,
  "behavior_fingerprint_sha256": "string",
  "node_count": 10,
  "node_ids": ["tests/unit/test_a.py::test_1"],
  "file_records": [
    {"file": "tests/unit/test_a.py", "node_count": 5, "zero_node_reason": null, "reason_authority": null, "evidence": null}
  ]
}
```

Global rules: `collection_scope == "global"`, `shard is null`, command targets `tests/`, no file subset.

### 18.4 Shard inventory

```json
{
  "schema_version": "1",
  "collection_scope": "shard",
  "python_version": "3.11",
  "pytest_version": "9.1.1",
  "commit_sha": "string",
  "track": "pr-head",
  "shard": "api-reporting",
  "run_id": "string",
  "run_attempt": 1,
  "behavior_fingerprint_sha256": "string",
  "node_count": 2,
  "node_ids": ["tests/unit/test_a.py::test_1"],
  "file_records": []
}
```

Shard rules: `collection_scope == "shard"`, `shard` is non-empty canonical manifest name, explicit files required.

### 18.5 Invalid combinations

Reject: global + shard non-null, shard + shard null, unknown `collection_scope`, empty shard string, shard not in manifest, global using explicit subset, shard targeting whole `tests/`.

### 18.6 Artifact names

- Global: `<track>-global-py<version>-attempt<attempt>-node-inventory`
- Internal: `nodes.<track>.global.py<version>.attempt<attempt>.json`
- Shard: `<track>-<shard>-py<version>-attempt<attempt>-node-inventory`

### 18.7 Plugin interface

```bash
# Global
uv run --locked pytest --collect-only \
  -p tests.ci.collect_nodes_plugin \
  --hx-collection-scope global \
  --hx-node-output nodes.${TRACK}.global.py${PYVER}.attempt${ATTEMPT}.json \
  tests/

# Shard
uv run --locked pytest --collect-only \
  -p tests.ci.collect_nodes_plugin \
  --hx-collection-scope shard \
  --hx-shard "${SHARD}" \
  --hx-node-output nodes.${TRACK}.${SHARD}.py${PYVER}.attempt${ATTEMPT}.json \
  <explicit files>
```

Plugin validates scope/shard parameter combinations.

### 18.8 Node ID rules

UTF-8, exact `item.nodeid`, slash normalized to `/`, sorted lexicographically, duplicates prohibited, no trimming inside parameters, supports parameterized IDs, spaces, Unicode, brackets, nested classes, multiple `::`.

### 18.9 Collection failure semantics

Exit != 0 → FAIL. Import/plugin errors → FAIL. Schema validation → FAIL. Duplicate node ID → FAIL. `node_count` mismatch → FAIL. Missing JSON → FAIL. Wrong version/SHA/track/attempt → FAIL. Stderr preserved as independent artifact.

### 18.10 Acceptance fixtures

Simple function, class method, parameterized with spaces/Unicode/brackets, multiple `::`, path normalization, duplicate rejection, empty collection, import failure, plugin failure, schema mismatch.

## 19. Behavior-Affecting Environment Equality

### 19.1 Behavior-affecting variables

Must be identical between global and shard collection:

- Python version, pytest version, plugin versions
- Dependency lock, `pyproject.toml`
- Working directory, locale, timezone, hash seed
- Backend configuration, feature flags
- Provider configuration, warning configuration
- `PYTEST_ADDOPTS`
- Environment variables affecting imports or collection

Frozen variables: `PYTHONHASHSEED`, `TZ`, `LC_ALL`/`LANG` policy, `PYTEST_ADDOPTS`.

### 19.2 Allowed identity differences

```python
ALLOWED_IDENTITY_DIFFERENCES = {
    "collection_scope",
    "shard",
    "output_path",
}
```

These fields may differ between global and shard. Everything else in behavior must be identical.

### 19.3 Behavior fingerprint

```json
{
  "python_version": "3.11",
  "pytest_version": "9.1.1",
  "plugin_versions": {},
  "lock_digest": "sha256:...",
  "pyproject_digest": "sha256:...",
  "working_directory": ".",
  "python_hash_seed": "0",
  "timezone": "UTC",
  "locale": "C.UTF-8",
  "pytest_addopts": ""
}
```

Canonical JSON → `behavior_fingerprint_sha256`. Same track, Python version, commit SHA, attempt: global fingerprint == every shard fingerprint. Otherwise → FAIL.

### 19.4 Not in fingerprint

`collection_scope`, `shard`, output path, node count, node IDs, artifact name.

## 20. Golden and Benchmark Separation

- **golden:** Correctness authority. PR-blocking. Dedicated golden correctness shards.
- **benchmark:** Performance observation authority. Nightly/non-blocking.
- Golden shards: no non-golden correctness nodes, no benchmark nodes.
- Benchmark shards: no golden nodes, no PR-blocking correctness nodes.
- `golden` + `benchmark` mutually exclusive on single test.
- Acceptance: every golden node in exactly one golden shard. No non-golden node in golden shard. Every benchmark in exactly one nightly benchmark shard. No benchmark in PR-blocking shard.

## 21. Workflow/Job Naming Stability

Job names stable, unique, match manifest. Renaming requires manifest update.

## 22. Rollout Order

| Phase | Action | Gate |
|---|---|---|
| 1 | Freeze uv authority + `uv.lock` + freshness + `uv run --locked` | `uv lock --check`; `git diff --exit-code` |
| 2 | Add marker registration | `pytest --markers` |
| 3 | Add manifest schema, parser, file+node-ID verifiers (shadow) | Verifier runs |
| 4 | Implement `tests/ci/collect_nodes_plugin.py` | Plugin produces valid JSON |
| 5 | Generate baseline topology per Python version | Per-version documented |
| 6 | Add typed `PropertyProvider` doubles | mypy proof |
| 7 | Introduce shards, remove `--ignore` atomically | Completeness + plugin in same PR |
| 8 | Add PR-head and merge-ref tracks | SHA assertions pass |
| 9 | Add JUnit, durations, coverage, telemetry + event-local aggregates | Artifacts + aggregates pass |
| 10 | Add nightly workflow | Manual trigger passes |

Rollback: each phase revertible. Bare MagicMock NOT recommended long-term state.

## 23. Implementation Acceptance Tests

1. `uv sync --locked --all-extras` succeeds
2. `uv lock --check` passes
3. `git diff --exit-code -- uv.lock pyproject.toml` passes
4. `uv run --locked python -c "import sys; print(sys.executable)"` valid
5. `uv run --locked pytest --version` succeeds
6. `uv run --locked ruff --version` succeeds
7. `uv run --locked mypy --version` succeeds
8. `uv run --locked coverage --version` succeeds
9. All CI jobs pass with `uv run --locked`
10. File-level completeness: `D == M`
11. Python 3.11 file completeness: PASS
12. Python 3.11 node union equality: PASS
13. Python 3.11 node pairwise disjointness: PASS
14. Python 3.12 file completeness: PASS
15. Python 3.12 node union equality: PASS
16. Python 3.12 node pairwise disjointness: PASS
17. No `--ignore` in any CI job
18. All test doubles implement `PropertyProvider` (mypy)
19. No bare MagicMock provider success path
20. CoolProp tests isolated
21. JUnit XML per shard with attempt-safe name
22. Coverage raw + XML per shard (mandatory) with attempt-safe name
23. Event-local combined coverage by aggregate jobs
24. Resource telemetry JSON per shard
25. PR-head SHA assertion passes
26. Merge-ref SHA assertion passes
27. Main-push SHA assertion passes
28. Full-workflow-rerun-only policy documented
29. Partial failed-job rerun non-authoritative
30. All producers and aggregates share one attempt
31. No cross-attempt artifact reuse
32. Zero-node reason enum validated
33. Execution-time skip still collected
34. Unknown zero-node reason rejected
35. Global `collection_scope` schema valid
36. Shard `collection_scope` schema valid
37. Global `shard` field is null
38. Shard field matches manifest
39. Behavior fingerprint equality across global/shard
40. Only approved identity fields differ
41. Every golden node in exactly one golden shard
42. No non-golden node in golden shard
43. Every benchmark in nightly benchmark shard
44. No benchmark in PR-blocking shard
45. No node carries both `golden` and `benchmark`

## 24. TASK-010 Frozen Contract Preservation

Must not alter TASK-010 frozen contract SHA `9a1faeb92f4015a62f9d9add0739f3853a876415` or any TASK-010 behavior.

## 25. TASK-011 Dependency

TASK-011 must not start until TASK-015A implementation complete and CI stable.

## 26. Design Freeze Process

- **TASK-015A Design Frozen Contract SHA** = exact reviewed Head commit SHA
- Additional hashes for traceability: Reviewed Head Commit SHA, Design Document Git Blob SHA-1, Design Document Content SHA-256
- Only Reviewed Head Commit SHA is frozen authority
- Modification requires: new commit → new review → new frozen authority

---

## Appendix A: Gate Table

| Gate | Required |
|---|---|
| Exact uv version authority (pinned action SHA) | YES |
| uv lock freshness check | YES |
| `uv run --locked` for all executables | YES |
| Python 3.11 locked sync | YES |
| Python 3.12 locked sync | YES |
| Manifest schema validation | YES |
| File set equality (D == M) | YES |
| Python 3.11 global node inventory | YES |
| Python 3.11 shard node union equality | YES |
| Python 3.11 shard pairwise disjointness | YES |
| Python 3.12 global node inventory | YES |
| Python 3.12 shard node union equality | YES |
| Python 3.12 shard pairwise disjointness | YES |
| No stale manifest paths | YES |
| No empty shards | YES |
| PR-head exact SHA assertion | YES |
| Merge-ref exact SHA assertion | YES |
| Main-push exact SHA assertion | YES |
| Full-workflow-rerun-only policy | YES |
| Partial failed-job rerun non-authoritative | YES |
| All producers and aggregates share one attempt | YES |
| No cross-attempt artifact reuse | YES |
| Attempt completeness manifest exact equality | YES |
| Typed PropertyProvider protocol check (mypy) | YES |
| No bare MagicMock provider success path | YES |
| JUnit artifact per shard | YES |
| Coverage raw data per shard (mandatory) | YES |
| Coverage XML per shard (mandatory) | YES |
| Event-local combined coverage | YES |
| Artifact identity includes run_attempt | YES |
| Durations/log artifact per shard | YES |
| Resource telemetry artifact per shard | YES |
| Zero-node reason enum validation | YES |
| Execution-time skip remains collected | YES |
| Unknown zero-node reason rejected | YES |
| Global `collection_scope` schema | YES |
| Shard `collection_scope` schema | YES |
| Global `shard` field is null | YES |
| Shard field matches manifest | YES |
| Behavior fingerprint equality | YES |
| Only approved identity fields may differ | YES |
| Golden dedicated correctness shards | YES |
| Benchmark nightly-only shards | YES |
| Structured pytest collection plugin | YES |
| Node inventory schema validation | YES |
| Collection stderr preserved | YES |
| TASK-010 frozen behavior unchanged | YES |
| TASK-011 not started | YES |

---

**Design Status:** READY_FOR_REVIEW
**Implementation Authorization:** NOT GRANTED
**TASK-015A Design Frozen Contract SHA:** Pending
