# TASK-015A — Deterministic Test Environment and CI Sharding: Design Contract

**Issue:** #33
**Status:** DESIGN READY_FOR_REVIEW
**Implementation Authorization:** NOT GRANTED
**TASK-015A Design Frozen Contract SHA:** Pending — to be set to the exact independently approved reviewed Head commit SHA

> Note: TASK-010 has its own frozen contract SHA: `9a1faeb92f4015a62f9d9add0739f3853a876415`.
> TASK-015A design contract SHA is distinct and pending independent approval.

---

## 1. Objective

Establish a deterministic, reproducible, and maintainable test environment for HXForge that eliminates hidden test files, provides explicit per-shard file manifests verified at pytest node-ID level, replaces ad-hoc `--ignore` with structured test partitioning, introduces typed provider test doubles conforming to the real `PropertyProvider` protocol, separates CoolProp-dependent tests from pure unit tests, adds mandatory CI telemetry (JUnit, durations, coverage, resource), and defines clear authority for PR-head, merge-ref, and main-push CI tracks — all executed exclusively through the `uv`-managed locked project environment.

## 2. Scope

1. Dependency lock via `uv.lock` with freshness gate
2. Frozen `uv` installation authority (`astral-sh/setup-uv` with pinned commit SHA)
3. Locked environment execution authority (`uv run --locked` for all commands)
4. Pytest marker taxonomy
5. Test shard manifest specification with node-ID completeness proof
6. Typed `PropertyProvider` test doubles (real protocol)
7. CoolProp test isolation
8. Mandatory test coverage with cross-job aggregation
9. JUnit, durations, coverage, resource telemetry
10. PR-head, merge-ref, main-push tri-track CI authority
11. Nightly full regression
12. Golden and benchmark test separation
13. Workflow/job naming stability
14. Rollout, migration, and rollback strategy

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

### 4.3 Known issues with current topology

- `repository-core` uses `--ignore` to exclude correction-r10 and correction-r12, creating an implicit "remainder" shard
- `test_units.py` is executed by both `repository-core` (not excluded) and `units` (explicit) — duplicate execution
- TASK-010 focused test files (`test_task010_*.py`) are also executed by `repository-core` — duplicate execution
- No formal dependency lock (`uv.lock` not committed)
- No pytest marker taxonomy
- `MagicMock` used as provider in multiple test files without typed protocol conformance
- No PR-head vs merge-ref distinction (default `pull_request` checkout is merge ref)
- All commands run from system Python, not from a locked `uv`-managed environment

### 4.4 Baseline inventory generation algorithm

To be executed and recorded before shard cutover:

```bash
set -o pipefail
uv run --locked pytest --collect-only -q > collection.stdout.txt 2> collection.stderr.txt
# Parse node IDs from stdout (exclude summary, warnings, empty lines)
# Sort and deduplicate
```

Artifact format: one text file per shard containing sorted pytest node IDs, plus stdout, stderr, and collection metadata JSON.

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

- **Action repository:** `astral-sh/setup-uv`
- **Full action commit SHA:** `fac544c07dec837d0ccb6301d7b5580bf5edae39` (v8.2.0)
- **uv version:** `0.11.25`
- **Version assertion:** `test "$(uv --version)" = "uv 0.11.25"`
- **Cache policy:** action-managed cache (default)
- **Auto-update:** NOT allowed — action SHA is pinned
- **Version upgrade process:** requires explicit governance approval, new commit SHA, new review

If `setup-uv` cannot provide the specified version, CI must FAIL. No fallback to system `uv`.

### 5.2 Lock freshness gate

```yaml
- name: Check lock freshness
  run: uv lock --check

- name: Install from lock
  run: uv sync --locked --all-extras

- name: Verify no lock drift
  run: git diff --exit-code -- uv.lock pyproject.toml
```

Failure conditions (all must fail CI):
- `pyproject.toml` changed but `uv.lock` not updated
- `uv.lock` missing
- Lock format corrupted
- Lock Python compatibility does not satisfy 3.11/3.12
- CI modifies lockfile (detected by `git diff --exit-code`)

### 5.3 Rules

- `uv.lock` must be committed to the repository
- All CI jobs must install from the lock file via `uv sync --locked --all-extras`
- Lock file updates require explicit PR review
- Lock file must be regenerated with `uv lock` and committed as a separate change
- Exact `uv` version changes require explicit governance approval

## 6. Locked Environment Execution Authority

### 6.1 Unique execution rule

Every executable used by TASK-015A CI must resolve from the `uv`-managed locked project environment via `uv run --locked`.

```bash
# Environment verification
uv run --locked python -c "import sys; print(sys.executable)"
uv run --locked pytest --version
uv run --locked coverage --version
uv run --locked mypy --version
uv run --locked ruff --version
```

### 6.2 Mandatory command form

All CI commands MUST use `uv run --locked`:

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

The following are NOT allowed unless the design explicitly selects an alternative unique form and unifies ALL commands to that form:

- `uv run pytest` (without `--locked`)
- bare `pytest` (system PATH)
- `python -m pytest`
- `.venv/bin/pytest`
- Any command not routed through `uv run --locked`

### 6.4 Acceptance gate

**Every executable used by TASK-015A CI must resolve from the uv-managed locked project environment.**

CI must not depend on runner pre-installed tool versions.

## 7. Python Version Support

- Supported: 3.11, 3.12
- CI matrix must test both versions
- No code may use features exclusive to 3.13+ without explicit approval
- Minimum version pin in `pyproject.toml` must match CI matrix

## 8. Pytest Marker Taxonomy

| Marker | Description | CoolProp required | Provider required |
|---|---|---|---|
| `pure` | Pure unit tests, no external dependencies | No | No |
| `provider` | Property provider contract tests | No | Yes (typed double) |
| `coolprop` | CoolProp backend integration | Yes | Yes (real or typed double) |
| `integration` | Multi-component integration tests | Varies | Varies |
| `golden` | Deterministic correctness regression against approved committed baseline | Varies | Varies |
| `benchmark` | Performance measurement; timing/throughput/memory observations; not correctness authority | Varies | Varies |
| `slow` | Long-running tests (>30s expected) | Varies | Varies |

### 8.1 Registration

```toml
[tool.pytest.ini_options]
markers = [
    "pure: pure unit tests, no CoolProp, no provider",
    "provider: property provider contract tests",
    "coolprop: CoolProp backend integration",
    "integration: multi-component integration tests",
    "golden: deterministic correctness regression against approved baseline",
    "benchmark: performance measurement, not correctness authority",
    "slow: long-running tests",
]
```

### 8.2 Marker combination legitimacy

| Combination | Allowed | Notes |
|---|---|---|
| `pure` only | Yes | No CoolProp, no provider |
| `provider` only | Yes | Typed double, no CoolProp |
| `coolprop` only | Yes | Real CoolProp backend |
| `golden` + `pure` | Yes | Golden correctness, no CoolProp |
| `golden` + `provider` | Yes | Golden with typed double |
| `golden` + `coolprop` | Yes | Golden with real CoolProp |
| `benchmark` + `pure` | Yes | Perf measurement, no CoolProp |
| `benchmark` + `coolprop` | Yes | Perf with CoolProp |
| `benchmark` + `slow` | Yes | Long perf tests |
| `golden` + `benchmark` | No | Mutually exclusive: correctness vs performance |
| `slow` + `pure` | Yes | Long pure tests |

### 8.3 Application rules

- Every test file must be tagged with at least one marker
- Markers classify semantics, not shard ownership
- `@pytest.mark.golden` does NOT imply `@pytest.mark.coolprop`
- `@pytest.mark.coolprop` is represented only by `@pytest.mark.coolprop`
- `@pytest.mark.slow` is represented only by `@pytest.mark.slow`
- Marker filter must not cause test nodes to silently disappear from shards

## 9. Test Shard Manifest

### 9.1 Format

```yaml
version: "1"
shards:
  - name: <shard-name>          # unique, lowercase, hyphen-separated
    job: <ci-job-name>           # unique across all shards
    python: ["3.11", "3.12"]    # subset of [3.11, 3.12]
    files:                        # explicit relative paths, no globs
      - tests/unit/test_file_a.py
    timeout: 120                 # seconds per test node
```

### 9.2 Sorting rules

- Shard names: alphabetical
- Files within shard: alphabetical
- Python versions: ascending

### 9.3 Schema validation

Reject: duplicate shard/job names, duplicate files, empty shards, non-existent paths, directories, globs, `..` traversal, paths outside repo root, symlinks outside test root, non-canonical paths, non-test files, Python versions outside `{3.11, 3.12}`, non-positive timeout, unknown fields.

### 9.4 File-level completeness

```python
def verify_file_completeness(manifest: dict, test_root: str) -> None:
    """Verify D == M bidirectionally."""
    D = set(discover_all_test_files(test_root))
    M = set()
    for shard in manifest["shards"]:
        for f in shard["files"]:
            assert f not in M, f"Duplicate file: {f}"
            M.add(f)
    missing = D - M
    extra = M - D
    assert not missing, f"Missing from manifest: {missing}"
    assert not extra, f"Stale manifest paths: {extra}"
    assert M, "No files in manifest"
    for shard in manifest["shards"]:
        assert shard["files"], f"Empty shard: {shard['name']}"
```

### 9.5 pytest node-ID completeness

```python
def verify_node_completeness(manifest: dict, test_root: str) -> None:
    """Verify union(S_i) == G and S_i intersect S_j == empty."""
    G = set(collect_node_ids(test_root))
    S = {}
    for shard in manifest["shards"]:
        cmd = build_pytest_command(shard)
        S[shard["name"]] = set(collect_node_ids(cmd))
    union = set()
    for nodes in S.values():
        union |= nodes
    missing = G - union
    extra = union - G
    assert not missing, f"Missing node IDs: {missing}"
    assert not extra, f"Extra node IDs: {extra}"
    names = list(S.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            overlap = S[names[i]] & S[names[j]]
            assert not overlap, f"Overlap between {names[i]} and {names[j]}: {overlap}"
```

### 9.6 Node-ID parser requirements

- Only accept lines matching pytest node-ID syntax
- Exclude summary, warning, empty lines, collected-count lines
- UTF-8 encoding, normalize path separators, sort and deduplicate
- Discover duplicate raw node IDs → FAIL
- Global and shard collection must use identical: locked environment, Python version, pytest version, plugins, pyproject.toml, working directory, environment variables

### 9.7 Collection failure semantics

- `pytest --collect-only` exit code != 0 → FAIL
- Import errors → FAIL, plugin errors → FAIL
- `collection.stderr.txt` always preserved and uploaded
- Warnings during collection: recorded but do not fail

### 9.8 Marker authority

- Manifest owns file ownership; markers own semantics only
- Markers do NOT change shard node ownership

## 10. "--ignore" Elimination

Replace `--ignore` with explicit file lists. Verify no test file lost (file-level + node-ID completeness). Completeness check job validates atomically.

## 11. CoolProp Test Isolation

- CoolProp-dependent tests carry `@pytest.mark.coolprop`
- Dedicated shards with timeout 180s
- Do not share shard with pure unit tests

## 12. Typed PropertyProvider Test Doubles

### 12.1 Context

TASK-010 exposed unsafe dynamic `MagicMock` attributes at the provider-identity boundary. Production extraction was hardened, while strict typed provider test doubles remain a follow-up improvement.

### 12.2 Real PropertyProvider protocol

Source: `src/hexagent/properties/base.py`

```python
class PropertyProvider(Protocol):
    name: str
    version: str
    git_revision: str
    reference_state_policy: ReferenceStatePolicy

    def state_tp(self, fluid: FluidIdentifier | str, temperature_k: float, pressure_pa: float) -> FluidState: ...
    def state_ph(self, fluid: FluidIdentifier | str, pressure_pa: float, enthalpy_j_kg: float, *, reference_state: ReferenceStatePolicy) -> FluidState: ...
    def saturation_at_pressure(self, fluid: FluidIdentifier | str, pressure_pa: float) -> SaturationState: ...
    def saturation_at_temperature(self, fluid: FluidIdentifier | str, temperature_k: float) -> SaturationState: ...
    def cache_info(self) -> PropertyCacheInfo: ...
    def clear_cache(self) -> None: ...
```

### 12.3 Canonical fluid identity

```python
def canonical_fluid_identity(fluid: FluidIdentifier | str) -> str:
    """Return the canonical cache identity for a fluid.

    Uses FluidIdentifier.cache_identity which delegates to coolprop_fluid,
    producing strings like "HEOS::Water" or "HEOS::Ethanol[0.5]&Water[0.5]".
    """
    return FluidIdentifier.from_value(fluid).cache_identity
```

Ensures: same fluid + same backend → same key; same name + different backend → different key; same mixture + different composition → different key; same mixture + different component order → same key; string `"Water"` and `FluidIdentifier("Water")` → same key.

### 12.4 Query key types

```python
@dataclass(frozen=True)
class TPQueryKey:
    fluid_identity: str   # from canonical_fluid_identity()
    temperature_k: float
    pressure_pa: float
    @classmethod
    def from_request(cls, fluid, temperature_k, pressure_pa) -> TPQueryKey: ...

@dataclass(frozen=True)
class PHQueryKey:
    fluid_identity: str
    pressure_pa: float
    enthalpy_j_kg: float
    reference_state: ReferenceStatePolicy
    @classmethod
    def from_request(cls, fluid, pressure_pa, enthalpy_j_kg, reference_state) -> PHQueryKey: ...

@dataclass(frozen=True)
class SatPQueryKey:
    fluid_identity: str
    pressure_pa: float
    @classmethod
    def from_request(cls, fluid, pressure_pa) -> SatPQueryKey: ...

@dataclass(frozen=True)
class SatTQueryKey:
    fluid_identity: str
    temperature_k: float
    @classmethod
    def from_request(cls, fluid, temperature_k) -> SatTQueryKey: ...
```

All keys created via `from_request()` factory. Direct construction with hand-built identity strings prohibited.

### 12.5 StubPropertyProvider

Returns fixed typed results. Configuration: `tp_results: dict[TPQueryKey, FluidState]`, `ph_results: dict[PHQueryKey, FluidState]`, `sat_p_results: dict[SatPQueryKey, SaturationState]`, `sat_t_results: dict[SatTQueryKey, SaturationState]`, identity fields. Unconfigured input → deterministic error. `cache_info()` → fixed zeros. `clear_cache()` → no-op.

### 12.6 ReplayPropertyProvider

Replays ordered sequences. Configuration: per-query-type `deque` of typed results. Sequence exhausted → error. Supports `assert_fully_consumed()`. Call log as immutable tuple. **Cache semantics (frozen):** `cache_info()` → fixed zeros; `clear_cache()` → no-op (does NOT clear queues, reset positions, refill sequences, clear call log, or reset call index). Optional `reset_replay()` for test-only explicit reset.

### 12.7 SelectiveFailurePropertyProvider

Wraps real `PropertyProvider`. Failure map: `dict[tuple[PropertyQueryType, int], Callable[[], Exception]]`. Call index starts at 1. Failure triggered BEFORE delegation. All four query types supported. `cache_info()`/`clear_cache()` delegate to inner. Identity from inner.

### 12.8 CountingPropertyProvider

Wraps real or typed provider. Per-query-type counters. Records normalized request tuples. Failed calls counted. `reset_counts()` available. `cache_info()`/`clear_cache()` delegate. Identity from inner.

### 12.9 Acceptance checks

- mypy proves each double satisfies `PropertyProvider`
- All methods return `FluidState` or `SaturationState`
- PH calls preserve explicit `reference_state`
- Identity fields concrete, never dynamic MagicMock values
- No bare MagicMock as provider success path
- `canonical_fluid_identity()` consistency tests pass

## 13. CI Tri-Track Authority

### 13.1 Track A — PR Head

Checkout `ref: ${{ github.event.pull_request.head.sha }}`. Assert: `test "$(git rev-parse HEAD)" = "${{ github.event.pull_request.head.sha }}"`. Job naming: `pr-head / <shard-name>`.

### 13.2 Track B — PR Merge Ref

Checkout `refs/pull/${{ github.event.pull_request.number }}/merge`. Assert SHA matches `merge_commit_sha`. Job naming: `merge-ref / <shard-name>`.

### 13.3 Track C — Main Push

Checkout `ref: ${{ github.sha }}`. Assert SHA matches. Job naming: `main / <shard-name>`.

### 13.4 Rules

PR-head and merge-ref both required for merge. Head success + merge-ref failure → block. Test-node inventory must match. Fork PRs must not use secrets. `pull_request_target` prohibited. Merge-ref NOT optional.

## 14. Nightly Full Regression

Runs full suite including golden, benchmark, slow. Separate from PR-blocking. Failures create issues. Schedule: daily. Artifacts retained 30 days.

## 15. Timeout, Cancellation, and Retry

| Type | Timeout |
|---|---|
| Default | 120s |
| CoolProp | 180s |
| Golden | 300s |

Runner-side cancellation recorded, not auto-retried. No automatic test retry (determinism). Infrastructure retry acceptable.

## 16. Globally Unique Artifact Identity

### 16.1 Naming

GitHub artifact: `<track>-<shard>-py<version>-<artifact-kind>`
Internal file: `<artifact-kind>.<track>.<shard>.py<version>.<ext>`

### 16.2 Tracks

`pr-head`, `merge-ref`, `main`, `nightly` (exactly these four)

### 16.3 Kinds

| Kind | GitHub name suffix | Internal file |
|---|---|---|
| JUnit | `-junit` | `junit.<track>.<shard>.py<ver>.xml` |
| pytest output | `-pytest-output` | `pytest-output.<track>.<shard>.py<ver>.txt` |
| coverage data | `-coverage-data` | `coverage.<track>.<shard>.py<ver>.xml` |
| coverage raw | `-coverage-raw` | `.coverage.<track>.<shard>.py<ver>` |
| resource | `-resource` | `resource.<track>.<shard>.py<ver>.json` |
| node inventory | `-node-inventory` | `nodes.<track>.<shard>.py<ver>.txt` |
| collection stderr | `-collection-stderr` | `collection-stderr.<track>.<shard>.py<ver>.txt` |

### 16.4 Character rules

Lowercase ASCII, hyphen or dot separators, no spaces/slash/dynamic labels. Globally unique within workflow run.

## 17. Telemetry Contracts

### 17.1 JUnit

```bash
uv run --locked pytest --junitxml=junit.${TRACK}.${SHARD}.py${PYVER}.xml --timeout=<timeout> <args>
```

### 17.2 Durations

```bash
uv run --locked pytest --durations=20 --timeout=<timeout> <args> 2>&1 | tee pytest-output.${TRACK}.${SHARD}.py${PYVER}.txt
```

### 17.3 Coverage (mandatory)

Every required test shard must emit raw coverage data and per-shard coverage XML.

```bash
export COVERAGE_FILE=".coverage.${TRACK}.${SHARD}.py${PYVER}"
uv run --locked pytest --cov=hexagent --cov-branch --cov-report=xml:coverage.${TRACK}.${SHARD}.py${PYVER}.xml --timeout=<timeout> <files>
test -s "$COVERAGE_FILE"
```

No minimum percentage threshold. Branch coverage enabled. Subprocess coverage out of scope.

### 17.4 Cross-job coverage aggregation

Dedicated `coverage-aggregate` job depends on all test jobs. Downloads `*-coverage-raw` artifacts, validates count/uniqueness/completeness, rejects zero-byte/unknown/duplicate files, runs `uv run --locked coverage combine`, generates `combined-coverage.xml`, uploads. Failure: missing file → FAIL, duplicate → FAIL, combine fails → FAIL, aggregate not executed → overall FAIL.

### 17.5 Resource telemetry schema

```json
{
  "schema_version": "1",
  "job_name": "string",
  "shard_name": "string",
  "track": "pr-head | merge-ref | main | nightly",
  "python_version": "3.11 | 3.12",
  "uv_version": "0.11.25",
  "commit_sha": "string (must equal asserted SHA)",
  "runner_os": "string",
  "run_id": "string",
  "run_attempt": "number",
  "job_start": "ISO-8601",
  "job_end": "ISO-8601",
  "wall_clock_seconds": "number (finite, non-negative)",
  "install_duration_seconds": "number (finite, non-negative)",
  "collection_duration_seconds": "number (finite, non-negative)",
  "test_duration_seconds": "number (finite, non-negative)",
  "peak_rss_bytes": "number | null",
  "cpu_user_seconds": "number | null",
  "cpu_system_seconds": "number | null",
  "disk_bytes_before": "number | null",
  "disk_bytes_after": "number | null",
  "exit_status": "number",
  "telemetry_availability": {
    "peak_rss": "boolean",
    "cpu": "boolean",
    "disk": "boolean"
  }
}
```

Unobtainable values: `null` (never `0`). Availability flags consistent with null. All durations finite non-negative. `commit_sha` equals track asserted SHA. `schema_version` fixed. `extra=forbid`.

## 18. Golden and Benchmark Separation

- **golden**: Correctness regression, PR-blocking. `@pytest.mark.golden`.
- **benchmark**: Performance measurement, nightly/non-blocking. `@pytest.mark.benchmark`.
- Mutually exclusive on single test.
- `@pytest.mark.benchmark` does NOT imply `@pytest.mark.golden`.
- `@pytest.mark.golden` does NOT imply `@pytest.mark.coolprop`.
- Golden/benchmark not mixed with correctness shards.
- Golden result updates require explicit PR approval.

## 19. Workflow/Job Naming Stability

Job names stable, unique within run, match manifest `job` field. Renaming requires manifest update.

## 20. Shard I/O/Failure Semantics

**Input:** Git checkout, Python version, `uv sync --locked --all-extras`.
**Output:** JUnit, durations, coverage raw + XML (mandatory), resource telemetry, node inventory.
**Failure:** Any test failure fails shard. Shards independent. All required shards must pass.

## 21. Rollout Order

| Phase | Action | Gate |
|---|---|---|
| 1 | Freeze uv authority + `uv.lock` + freshness gate + `uv run --locked` for all | `uv lock --check`; `git diff --exit-code`; all commands `uv run --locked` |
| 2 | Add marker registration only | `uv run --locked pytest --markers` |
| 3 | Add manifest schema, parser, file+node-ID verifiers (shadow mode) | Verifier runs, no routing |
| 4 | Generate baseline topology inventory | Documented node union and overlaps |
| 5 | Add typed `PropertyProvider` doubles, migrate tests | mypy protocol proof; no routing change |
| 6 | Introduce explicit shards, remove `--ignore` atomically | Completeness verifier required in same PR |
| 7 | Add PR-head and merge-ref tracks | SHA assertions pass |
| 8 | Add JUnit, durations, coverage, telemetry + `coverage-aggregate` | Artifacts uploaded; aggregate passes |
| 9 | Add nightly workflow | Manual trigger test passes |

Rollback: each phase revertible via `git revert`. Typed doubles rollback restores last approved implementation (bare MagicMock NOT a recommended long-term state).

## 22. Implementation Acceptance Tests

1. `uv sync --locked --all-extras` succeeds on fresh clone
2. `uv lock --check` passes
3. `git diff --exit-code -- uv.lock pyproject.toml` passes
4. `uv run --locked python -c "import sys; print(sys.executable)"` prints valid path
5. `uv run --locked pytest --version` succeeds
6. `uv run --locked ruff --version` succeeds
7. `uv run --locked mypy --version` succeeds
8. `uv run --locked coverage --version` succeeds
9. All CI jobs pass with `uv run --locked`
10. File-level completeness: `D == M`
11. Node-ID completeness: `union(S_i) == G`
12. Node-ID pairwise disjointness
13. No `--ignore` in any CI job
14. All test doubles implement `PropertyProvider` (mypy)
15. No bare MagicMock provider success path
16. CoolProp tests isolated in dedicated shard
17. JUnit XML uploaded per shard
18. Coverage raw + XML uploaded per shard (mandatory)
19. Combined coverage by `coverage-aggregate`
20. Resource telemetry JSON per shard
21. PR-head SHA assertion passes
22. Merge-ref SHA assertion passes
23. Main-push SHA assertion passes
24. Nightly workflow runs
25. Golden node IDs only in golden shards; no non-golden node in golden shard
26. Benchmark node IDs only in nightly benchmark shards; no benchmark in PR-blocking shards

## 23. TASK-010 Frozen Contract Preservation

Must not alter TASK-010 frozen contract SHA `9a1faeb92f4015a62f9d9add0739f3853a876415` or any TASK-010 behavior.

## 24. TASK-011 Dependency

TASK-011 must not start until TASK-015A implementation complete and CI stable.

## 25. Design Freeze Process

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
| Node-ID union equality | YES |
| Node-ID pairwise disjointness | YES |
| No stale manifest paths | YES |
| No empty shards | YES |
| PR-head exact SHA assertion | YES |
| Merge-ref exact SHA assertion | YES |
| Main-push exact SHA assertion | YES |
| Typed PropertyProvider protocol check (mypy) | YES |
| No bare MagicMock provider success path | YES |
| JUnit artifact per shard | YES |
| Coverage raw data per shard (mandatory) | YES |
| Coverage XML per shard (mandatory) | YES |
| Combined coverage artifact | YES |
| Durations/log artifact per shard | YES |
| Resource telemetry artifact per shard | YES |
| Golden/benchmark separation | YES |
| TASK-010 frozen behavior unchanged | YES |
| TASK-011 not started | YES |

---

**Design Status:** READY_FOR_REVIEW
**Implementation Authorization:** NOT GRANTED
**TASK-015A Design Frozen Contract SHA:** Pending
