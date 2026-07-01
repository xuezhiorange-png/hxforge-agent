# TASK-015A — Deterministic Test Environment and CI Sharding: Design Contract

**Issue:** #33
**Status:** DESIGN READY_FOR_REVIEW
**Implementation Authorization:** NOT GRANTED
**Frozen Contract SHA:** Pending (to be established after design review — = exact reviewed Head commit SHA)

---

## 1. Objective

Establish a deterministic, reproducible, and maintainable test environment for HXForge that eliminates hidden test files, provides explicit per-shard file manifests verified at pytest node-ID level, replaces ad-hoc `--ignore` with structured test partitioning, introduces typed provider test doubles conforming to the real `PropertyProvider` protocol, separates CoolProp-dependent tests from pure unit tests, adds CI telemetry (JUnit, durations, coverage), and defines clear authority for PR-head, merge-ref, and main-push CI tracks.

## 2. Scope

1. Dependency lock via `uv.lock` with freshness gate
2. Pytest marker taxonomy
3. Test shard manifest specification with node-ID completeness proof
4. Typed `PropertyProvider` test doubles (real protocol)
5. CoolProp test isolation
6. Test coverage completeness verification
7. JUnit, durations, coverage, resource telemetry
8. PR-head, merge-ref, main-push tri-track CI authority
9. Nightly full regression
10. Golden and benchmark test separation
11. Workflow/job naming stability
12. Rollout, migration, and rollback strategy

## 3. Non-goals

- No TASK-011 benchmark implementation
- No new exchanger type
- No TASK-010 frozen contract changes
- No pressure-drop, velocity-constraints, materials, cost, or mechanical compliance features
- No database, ORM, object storage, authentication, or authorization
- No frontend changes
- No PDF engine introduction

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

### 4.4 Baseline inventory generation algorithm

To be executed and recorded before shard cutover:

```bash
# Global collection
pytest --collect-only -q 2>/dev/null | sort > /tmp/global-nodes.txt

# Per-job collection (replicate exact CI arguments)
pytest --collect-only -q --ignore=... -q 2>/dev/null | sort > /tmp/shard-repository-core.txt
pytest --collect-only -q tests/unit/test_units.py -q 2>/dev/null | sort > /tmp/shard-units.txt
# ... etc for each shard
```

Artifact format: one text file per shard containing sorted pytest node IDs.

## 5. Dependency Lock

### 5.1 uv authority

- Tool: `uv`
- Exact version: `0.11.25` (as of design date; version changes require explicit governance approval)
- Installation source: system package manager or official installer
- Version verification: `uv --version` must be printed in CI before any uv command

### 5.2 Lock freshness gate

CI must enforce:

```yaml
- name: Verify uv version
  run: uv --version

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
- Exact `uv` version变更需要显式治理审批

## 6. Python Version Support

- Supported: 3.11, 3.12
- CI matrix must test both versions
- No code may use features exclusive to 3.13+ without explicit approval
- Minimum version pin in `pyproject.toml` must match CI matrix

## 7. Pytest Marker Taxonomy

| Marker | Description | CoolProp required | Provider required |
|---|---|---|---|
| `pure` | Pure unit tests, no external dependencies | No | No |
| `provider` | Property provider contract tests | No | Yes (typed double) |
| `coolprop` | CoolProp backend integration | Yes | Yes (real or typed double) |
| `integration` | Multi-component integration tests | Varies | Varies |
| `golden` | Deterministic correctness regression against approved committed baseline | Varies | Varies |
| `benchmark` | Performance measurement; timing/throughput/memory observations; not correctness authority | Varies | Varies |
| `slow` | Long-running tests (>30s expected) | Varies | Varies |

### 7.1 Registration

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

### 7.2 Marker combination legitimacy

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

### 7.3 Application rules

- Every test file must be tagged with at least one marker
- Markers classify semantics, not shard ownership
- `@pytest.mark.golden` does NOT imply `@pytest.mark.coolprop`
- `@pytest.mark.coolprop` is represented only by `@pytest.mark.coolprop`
- `@pytest.mark.slow` is represented only by `@pytest.mark.slow`
- Marker filter must not cause test nodes to silently disappear from shards

## 8. Test Shard Manifest

### 8.1 Format

Shards are defined in `ci-shard-manifest.yml`:

```yaml
version: "1"
shards:
  - name: <shard-name>          # unique, lowercase, hyphen-separated
    job: <ci-job-name>           # unique across all shards
    python: ["3.11", "3.12"]    # subset of [3.11, 3.12]
    files:                        # explicit relative paths, no globs
      - tests/unit/test_file_a.py
      - tests/unit/test_file_b.py
    timeout: 120                 # seconds per test node
```

### 8.2 Sorting rules

- Shard names: alphabetical
- Files within shard: alphabetical
- Python versions: ascending

### 8.3 Schema validation

Reject:
- Duplicate shard names
- Duplicate job names
- Duplicate files across shards
- Empty shards
- Non-existent paths
- Directories instead of files
- Glob patterns
- `..` path traversal
- Paths outside repository root
- Symlinks pointing outside test root
- Non-canonical paths (e.g., `./tests/` vs `tests/`)
- Non-test files (files not matching `test_*.py`)
- Python version values outside frozen set `{3.11, 3.12}`
- Non-positive integer timeout
- Unknown schema fields

### 8.4 File-level completeness

```python
def verify_file_completeness(manifest: dict, test_root: str) -> None:
    """Verify D == M bidirectionally."""
    D = set(discover_all_test_files(test_root))  # all test_*.py in tests/
    M = set()
    for shard in manifest["shards"]:
        for f in shard["files"]:
            assert f not in M, f"Duplicate file: {f}"
            M.add(f)
    missing = D - M  # files in repo but not in manifest
    extra = M - D    # files in manifest but not in repo
    assert not missing, f"Missing from manifest: {missing}"
    assert not extra, f"Stale manifest paths: {extra}"
    assert M, "No files in manifest"
    for shard in manifest["shards"]:
        assert shard["files"], f"Empty shard: {shard['name']}"
```

### 8.5 pytest node-ID completeness

```python
def verify_node_completeness(manifest: dict, test_root: str) -> None:
    """Verify union(S_i) == G and S_i ∩ S_j == ∅."""
    # Global collection
    G = set(collect_node_ids(test_root))  # pytest --collect-only -q

    # Per-shard collection
    S = {}
    for shard in manifest["shards"]:
        cmd = build_pytest_command(shard)  # replicate exact CI args
        S[shard["name"]] = set(collect_node_ids(cmd))

    # Union check
    union = set()
    for name, nodes in S.items():
        union |= nodes
    missing = G - union
    extra = union - G
    assert not missing, f"Missing node IDs: {missing}"
    assert not extra, f"Extra node IDs: {extra}"

    # Pairwise disjointness
    for i, (name_i, nodes_i) in enumerate(S.items()):
        for name_j, nodes_j in list(S.items())[i+1:]:
            overlap = nodes_i & nodes_j
            assert not overlap, f"Overlap between {name_i} and {name_j}: {overlap}"
```

### 8.6 Marker authority

- Manifest is responsible for file ownership (which files belong to which shard)
- Markers are responsible for semantic classification (what kind of test)
- Markers do NOT change shard node ownership
- A test file in shard A stays in shard A regardless of its markers

## 9. "--ignore" Elimination

### 9.1 Current state

`repository-core` uses `--ignore` to exclude correction-r10 and correction-r12 files. This creates an implicit "remainder" shard that also executes `test_units.py` and TASK-010 focused tests (duplicating other shards).

### 9.2 Target state

All shards use explicit file lists. `--ignore` is not used in any CI job.

### 9.3 Migration

- Replace `--ignore` patterns with explicit file lists in shard manifest
- Verify no test file is lost during migration (file-level + node-ID completeness)
- Verify all intentional prior duplicate execution is removed or explicitly justified
- Completeness check job validates the transition atomically

## 10. CoolProp Test Isolation

### 10.1 Rules

- CoolProp-dependent tests carry `@pytest.mark.coolprop`
- CoolProp tests run in dedicated shards with explicit timeout (180s)
- CoolProp tests do not share shard with pure unit tests
- CoolProp C extension resource contention is mitigated by isolation

## 11. Typed PropertyProvider Test Doubles

### 11.1 Context

TASK-010 exposed unsafe dynamic `MagicMock` attributes at the provider-identity boundary. Production extraction was hardened, while strict typed provider test doubles remain a follow-up improvement.

### 11.2 Real PropertyProvider protocol

Source: `src/hexagent/properties/base.py`

```python
class PropertyProvider(Protocol):
    name: str
    version: str
    git_revision: str
    reference_state_policy: ReferenceStatePolicy

    def state_tp(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState: ...

    def state_ph(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        enthalpy_j_kg: float,
        *,
        reference_state: ReferenceStatePolicy,
    ) -> FluidState: ...

    def saturation_at_pressure(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
    ) -> SaturationState: ...

    def saturation_at_temperature(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
    ) -> SaturationState: ...

    def cache_info(self) -> PropertyCacheInfo: ...

    def clear_cache(self) -> None: ...
```

### 11.3 Query key types

```python
@dataclass(frozen=True)
class TPQueryKey:
    fluid_identity: str          # FluidIdentifier.name or str
    temperature_k: float
    pressure_pa: float

@dataclass(frozen=True)
class PHQueryKey:
    fluid_identity: str
    pressure_pa: float
    enthalpy_j_kg: float
    reference_state: ReferenceStatePolicy

@dataclass(frozen=True)
class SatPQueryKey:
    fluid_identity: str
    pressure_pa: float

@dataclass(frozen=True)
class SatTQueryKey:
    fluid_identity: str
    temperature_k: float
```

### 11.4 StubPropertyProvider

Returns fixed typed results for all four query types.

```python
@dataclass(frozen=True)
class StubPropertyProvider:
    """Fixed-value provider implementing PropertyProvider protocol.

    Configuration:
    - tp_results: dict[TPQueryKey, FluidState]
    - ph_results: dict[PHQueryKey, FluidState]
    - sat_p_results: dict[SatPQueryKey, SaturationState]
    - sat_t_results: dict[SatTQueryKey, SaturationState]
    - name/version/git_revision/reference_state_policy: identity fields

    Behavior:
    - Configured input → return fixed typed FluidState or SaturationState
    - Unconfigured input → raise PropertyServiceError with deterministic message
    - cache_info() → return PropertyCacheInfo(hits=0, misses=0, size=0, max_size=0)
    - clear_cache() → no-op (no internal cache)
    """
    name: str
    version: str
    git_revision: str
    reference_state_policy: ReferenceStatePolicy
    tp_results: dict[TPQueryKey, FluidState]
    ph_results: dict[PHQueryKey, FluidState]
    sat_p_results: dict[SatPQueryKey, SaturationState]
    sat_t_results: dict[SatTQueryKey, SaturationState]

    def state_tp(self, fluid, temperature_k, pressure_pa) -> FluidState: ...
    def state_ph(self, fluid, pressure_pa, enthalpy_j_kg, *, reference_state) -> FluidState: ...
    def saturation_at_pressure(self, fluid, pressure_pa) -> SaturationState: ...
    def saturation_at_temperature(self, fluid, temperature_k) -> SaturationState: ...
    def cache_info(self) -> PropertyCacheInfo: ...
    def clear_cache(self) -> None: ...
```

### 11.5 ReplayPropertyProvider

Replays recorded sequences of typed results for deterministic testing.

```python
@dataclass
class ReplayPropertyProvider:
    """Replay provider implementing PropertyProvider protocol.

    Configuration:
    - tp_sequence: dict[TPQueryKey, deque[FluidState]]
    - ph_sequence: dict[PHQueryKey, deque[FluidState]]
    - sat_p_sequence: dict[SatPQueryKey, deque[SaturationState]]
    - sat_t_sequence: dict[SatTQueryKey, deque[SaturationState]]

    Behavior:
    - Each call pops the next value from the corresponding deque
    - Sequence exhausted → raise PropertyServiceError
    - Request type mismatch → raise PropertyServiceError immediately
    - Supports final assertion: all deques must be empty after test
    - Call log: immutable tuple of (query_type, key, call_index)
    - Identity fields: concrete strings/enums from configuration
    """
    # ... (fields as described)

    def state_tp(self, fluid, temperature_k, pressure_pa) -> FluidState: ...
    def state_ph(self, fluid, pressure_pa, enthalpy_j_kg, *, reference_state) -> FluidState: ...
    def saturation_at_pressure(self, fluid, pressure_pa) -> SaturationState: ...
    def saturation_at_temperature(self, fluid, temperature_k) -> SaturationState: ...
    def cache_info(self) -> PropertyCacheInfo: ...
    def clear_cache(self) -> None: ...
    def assert_fully_consumed(self) -> None: ...
    @property
    def call_log(self) -> tuple[tuple[str, object, int], ...]: ...
```

### 11.6 SelectiveFailurePropertyProvider

Wraps a real `PropertyProvider` and injects failures at configurable call indices.

```python
@dataclass
class SelectiveFailurePropertyProvider:
    """Failure injection provider implementing PropertyProvider protocol.

    Configuration:
    - inner: PropertyProvider (real or typed)
    - failure_map: dict[tuple[PropertyQueryType, int], Callable[[], Exception]]
      Call index starts at 1 (first call = index 1).

    Behavior:
    - On each call, increment per-query-type counter
    - If (query_type, counter) ∈ failure_map → raise failure BEFORE delegating to inner
    - Otherwise → delegate to inner provider
    - Identity attributes: delegate to inner provider
    - cache_info(): delegate to inner
    - clear_cache(): delegate to inner
    """
    inner: PropertyProvider
    failure_map: dict[tuple[PropertyQueryType, int], Callable[[], Exception]]
    # ... (counters as internal mutable state)

    def state_tp(self, fluid, temperature_k, pressure_pa) -> FluidState: ...
    def state_ph(self, fluid, pressure_pa, enthalpy_j_kg, *, reference_state) -> FluidState: ...
    def saturation_at_pressure(self, fluid, pressure_pa) -> SaturationState: ...
    def saturation_at_temperature(self, fluid, temperature_k) -> SaturationState: ...
    def cache_info(self) -> PropertyCacheInfo: ...
    def clear_cache(self) -> None: ...
    @property
    def name(self) -> str: ...
    @property
    def version(self) -> str: ...
    @property
    def git_revision(self) -> str: ...
    @property
    def reference_state_policy(self) -> ReferenceStatePolicy: ...
```

### 11.7 CountingPropertyProvider

Wraps a real or typed provider and counts calls per query type.

```python
@dataclass
class CountingPropertyProvider:
    """Counting wrapper implementing PropertyProvider protocol.

    Configuration:
    - inner: PropertyProvider

    Behavior:
    - Per-query-type call counter (TP, PH, SATURATION_P, SATURATION_T)
    - Records normalized request records: tuple of (query_type, key, call_index)
    - Failed calls ARE recorded (counted before delegation, failure does not prevent recording)
    - reset_counts(): resets all counters and call log
    - cache_info(): delegate to inner
    - clear_cache(): delegate to inner
    - Identity attributes: delegate to inner (safe, stable)
    """
    inner: PropertyProvider

    def state_tp(self, fluid, temperature_k, pressure_pa) -> FluidState: ...
    def state_ph(self, fluid, pressure_pa, enthalpy_j_kg, *, reference_state) -> FluidState: ...
    def saturation_at_pressure(self, fluid, pressure_pa) -> SaturationState: ...
    def saturation_at_temperature(self, fluid, temperature_k) -> SaturationState: ...
    def cache_info(self) -> PropertyCacheInfo: ...
    def clear_cache(self) -> None: ...
    def reset_counts(self) -> None: ...
    @property
    def tp_call_count(self) -> int: ...
    @property
    def ph_call_count(self) -> int: ...
    @property
    def sat_p_call_count(self) -> int: ...
    @property
    def sat_t_call_count(self) -> int: ...
    @property
    def call_records(self) -> tuple[tuple[str, object, int], ...]: ...
    @property
    def name(self) -> str: ...
    @property
    def version(self) -> str: ...
    @property
    def git_revision(self) -> str: ...
    @property
    def reference_state_policy(self) -> ReferenceStatePolicy: ...
```

### 11.8 Design-level acceptance checks

- mypy proves each double satisfies `PropertyProvider`
- All methods return typed domain artifacts (`FluidState` or `SaturationState`)
- PH calls preserve explicit `reference_state` parameter
- Saturation calls are independently configurable
- Identity fields are concrete strings/enums, never dynamic `MagicMock` values
- No bare `MagicMock` is accepted as a successful provider path

## 12. CI Tri-Track Authority

### 12.1 Track A — PR Head

```yaml
- uses: actions/checkout@v4
  with:
    ref: ${{ github.event.pull_request.head.sha }}
- name: Assert PR head SHA
  run: |
    test "$(git rev-parse HEAD)" = "${{ github.event.pull_request.head.sha }}"
```

Job naming: `pr-head / <shard-name>` (e.g., `pr-head / task010-focused (3.11)`)

### 12.2 Track B — PR Merge Ref

```yaml
- uses: actions/checkout@v4
  with:
    ref: refs/pull/${{ github.event.pull_request.number }}/merge
- name: Assert merge-ref SHA
  run: |
    test "$(git rev-parse HEAD)" = "${{ github.event.pull_request.merge_commit_sha }}"
```

Job naming: `merge-ref / <shard-name>`

### 12.3 Track C — Main Push

```yaml
- uses: actions/checkout@v4
  with:
    ref: ${{ github.sha }}
- name: Assert main-push SHA
  run: |
    test "$(git rev-parse HEAD)" = "${{ github.sha }}"
```

Job naming: `main / <shard-name>`

### 12.4 Authority rules

| Rule | Enforced |
|---|---|
| PR-head success required for merge | YES |
| Merge-ref success required for merge | YES |
| Head success but merge-ref failure → block merge | YES |
| Head and merge-ref test-node inventory must match | YES |
| Fork PR must not use repository secrets | YES |
| `pull_request_target` must NOT be used | YES |
| Merge-ref is NOT optional | YES |

### 12.5 Required checks

Required status checks on PR:
- All `pr-head / *` jobs: SUCCESS
- All `merge-ref / *` jobs: SUCCESS

Required status checks on main:
- All `main / *` jobs: SUCCESS

## 13. Nightly Full Regression

### 13.1 Boundary

- Nightly runs the full test suite including `golden`, `benchmark`, and `slow` markers
- Nightly is separate from PR-blocking CI
- Nightly failures do not block PR merges
- Nightly failures create issues for investigation

### 13.2 Schedule

Daily at fixed time (e.g., 03:00 UTC), triggered by `schedule` event.

### 13.3 Telemetry

Upload JUnit XML, durations, and coverage report as artifacts. Retain for 30 days.

## 14. Timeout, Cancellation, and Retry Rules

### 14.1 Timeout

| Shard type | Per-node timeout |
|---|---|
| Default | 120s |
| CoolProp | 180s |
| Golden | 300s |

### 14.2 Cancellation

GitHub Actions runner-side cancellation is recorded but not retried automatically. The exact termination cause is investigated before re-run.

### 14.3 Retry

No automatic retry for test failures (determinism requirement). CI-level retry for infrastructure failures (runner unavailable) is acceptable.

## 15. Telemetry Contracts

### 15.1 JUnit artifact

```bash
pytest --junitxml=test-results.xml --timeout=<timeout> <args>
```

Artifact name: `<shard-name>-junit.xml`

### 15.2 Durations artifact

`pytest --durations=20` prints slow-test summary to stdout/stderr. To capture:

```bash
pytest --durations=20 --timeout=<timeout> <args> 2>&1 | tee pytest-output.txt
```

Artifact name: `<shard-name>-output.txt` (contains durations section in stdout)

### 15.3 Coverage artifact

```bash
pytest --cov=hexagent \
       --cov-report=xml:<shard-name>-coverage.xml \
       --cov-append \
       --timeout=<timeout> \
       <args>
```

Per-shard coverage data file: `.coverage.<shard-name>` (via `COVERAGE_FILE` env var)
Combined report: `coverage combine` then `coverage xml` then `coverage report`
Artifact names: `<shard-name>-coverage.xml`, `combined-coverage.xml`

No minimum percentage gate in TASK-015A. Branch coverage: enabled. Subprocess coverage: not in scope.

### 15.4 Resource telemetry schema

```json
{
  "job_name": "string",
  "shard_name": "string",
  "track": "pr-head | merge-ref | main",
  "python_version": "3.11 | 3.12",
  "uv_version": "string",
  "commit_sha": "string",
  "runner_os": "string",
  "job_start": "ISO-8601",
  "job_end": "ISO-8601",
  "wall_clock_seconds": "number",
  "install_duration_seconds": "number",
  "test_duration_seconds": "number",
  "exit_status": "number"
}
```

Artifact name: `<shard-name>-resource.json`

## 16. Golden and Benchmark Separation

### 16.1 Definitions

- **golden**: Deterministic correctness regression against approved committed baseline. PR-blocking.
- **benchmark**: Performance measurement (timing/throughput/memory). Not correctness authority. Nightly/non-blocking unless separately approved.

### 16.2 Rules

- Golden tests carry `@pytest.mark.golden`
- Benchmark tests carry `@pytest.mark.benchmark`
- `golden` and `benchmark` are mutually exclusive on a single test
- Golden may be PR-blocking
- Benchmark is nightly/non-blocking unless separately approved
- `@pytest.mark.benchmark` must not automatically imply `@pytest.mark.golden`
- `@pytest.mark.golden` must not automatically imply `@pytest.mark.coolprop`
- Benchmark must not be mixed with correctness shards
- Golden result updates require explicit PR approval

## 17. Workflow/Job Naming Stability

- Job names must be stable across PRs (no dynamic names)
- Job names must be unique within a workflow run
- Job names must match shard manifest `job` field
- Renaming a job requires updating the manifest and all references

## 18. Shard Input/Output/Failure Semantics

### 18.1 Input

- Git checkout of the verified SHA (per track)
- Python version from matrix
- Dependencies installed from `uv.lock` via `uv sync --locked --all-extras`

### 18.2 Output

- JUnit XML artifact
- Durations/log artifact
- Coverage artifact (if coverage enabled)
- Exit code 0 (success) or non-zero (failure)

### 18.3 Failure semantics

- Any test failure in a shard fails the shard job
- Shard failures are independent (no cross-shard dependencies)
- All required shards must pass for overall CI success

## 19. Rollout Order

Each phase is independently revertible with explicit acceptance gates.

| Phase | Action | Acceptance gate |
|---|---|---|
| 1 | Freeze uv version authority + add `uv.lock` + freshness gate | `uv lock --check` passes; `git diff --exit-code -- uv.lock pyproject.toml` after install |
| 2 | Add marker registration to `pyproject.toml` only | `pytest --markers` shows all registered markers |
| 3 | Add manifest schema, parser, file-level verifier, node-ID verifier | Verifier runs in shadow mode (report only, no routing) |
| 4 | Generate and review current topology inventory | Baseline node union and overlaps documented |
| 5 | Add typed `PropertyProvider` doubles and migrate tests | mypy proves protocol satisfaction; no CI routing change |
| 6 | Introduce explicit shards and remove `--ignore` atomically | Completeness verifier required in same PR; `new_union == current_global` |
| 7 | Add independent PR-head and merge-ref tracks | SHA assertions pass on test PR |
| 8 | Add JUnit, durations, coverage, resource telemetry | Artifacts uploaded for every shard |
| 9 | Add nightly benchmark/full regression workflow | Nightly runs successfully (manual trigger test) |

### 19.1 Rollback

- Each phase is revertible via `git revert`
- `uv.lock` removal: revert commit, restore `pip install` in CI
- Shard manifest rollback: restore previous `--ignore` commands
- Typed doubles rollback: restore previous test implementations (bare `MagicMock` is NOT a recommended long-term state; rollback restores last approved implementation, maintaining provider boundary safety)
- Nightly workflow rollback: disable or delete workflow file

## 20. Implementation Acceptance Tests

Before TASK-015A implementation is considered complete:

1. `uv sync --locked --all-extras` succeeds on fresh clone
2. `uv lock --check` passes
3. `git diff --exit-code -- uv.lock pyproject.toml` passes after install
4. All CI jobs pass with `uv sync --locked` installation
5. File-level completeness: `D == M`
6. Node-ID completeness: `union(S_i) == G`
7. Node-ID pairwise disjointness: `S_i ∩ S_j == ∅`
8. No `--ignore` used in any CI job
9. All test doubles implement `PropertyProvider` protocol (mypy)
10. No bare `MagicMock()` as provider success path in production tests
11. CoolProp tests isolated in dedicated shard
12. JUnit XML uploaded for every shard
13. Coverage artifact uploaded for every shard
14. Combined coverage report generated
15. Resource telemetry JSON uploaded for every shard
16. PR-head SHA assertion passes
17. Merge-ref SHA assertion passes
18. Main-push SHA assertion passes
19. Nightly workflow runs successfully (manual trigger)
20. Golden tests separated from correctness tests
21. Benchmark tests separated from correctness tests

## 21. TASK-010 Frozen Contract Preservation

This design contract must not alter:
- TASK-010 frozen contract SHA: `9a1faeb92f4015a62f9d9add0739f3853a876415`
- TASK-010 API behavior, DTOs, envelopes, artifact bundles, or report model
- TASK-010 repository state machine or CAS semantics
- TASK-010 ranking, formatter authority, or verifier logic

Any change that affects TASK-010 behavior requires a separate design contract and approval.

## 22. TASK-011 Dependency

TASK-011 (benchmark cases) must not be started until TASK-015A implementation is complete and CI environment is stable. This is a hard dependency.

## 23. Design Freeze Process

- **Frozen Contract SHA** = exact reviewed Head commit SHA containing the approved design contract
- Additional recorded hashes (for traceability, not authority):
  - `Reviewed Head Commit SHA`: the commit SHA of the reviewed HEAD
  - `Design Document Git Blob SHA-1`: SHA-1 of the design document blob in Git
  - `Design Document Content SHA-256`: SHA-256 of the design document content
- Only the Reviewed Head Commit SHA serves as the frozen authority
- Any modification to the design contract requires: new commit → new review → new frozen authority
- In-place modification of a frozen document without updating the SHA is prohibited

---

## Appendix A: Gate Table

| Gate | Required |
|---|---|
| Exact uv version authority | YES |
| uv lock freshness check | YES |
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
| Typed PropertyProvider protocol check | YES |
| No bare MagicMock provider success path | YES |
| JUnit artifact per shard | YES |
| Coverage artifact per shard | YES |
| Combined coverage artifact | YES |
| Durations/log artifact per shard | YES |
| Resource telemetry artifact per shard | YES |
| Golden/benchmark separation | YES |
| TASK-010 frozen behavior unchanged | YES |
| TASK-011 not started | YES |

---

**Design Status:** READY_FOR_REVIEW
**Implementation Authorization:** NOT GRANTED
**Frozen Contract SHA:** Pending
