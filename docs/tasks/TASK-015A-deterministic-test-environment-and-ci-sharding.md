# TASK-015A — Deterministic Test Environment and CI Sharding: Design Contract

**Issue:** #33
**Status:** DESIGN READY_FOR_REVIEW
**Implementation Authorization:** NOT GRANTED
**Frozen Contract SHA:** Pending (to be established after design review and approval)

---

## 1. Objective

Establish a deterministic, reproducible, and maintainable test environment for HXForge that:

- Eliminates hidden test files
- Provides explicit per-shard file manifests
- Replaces ad-hoc `--ignore` with structured test partitioning
- Introduces typed provider test doubles to replace bare `MagicMock` usage
- Separates CoolProp-dependent tests from pure unit tests
- Adds CI telemetry (JUnit, durations, coverage)
- Defines clear authority for PR head, merge-ref, and main push CI

## 2. Scope

2.1. Dependency lock via `uv.lock`
2.2. Pytest marker taxonomy
2.3. Test shard manifest specification
2.4. Typed PropertyProvider test doubles
2.5. CoolProp test isolation
2.6. Test coverage completeness verification
2.7. JUnit, durations, coverage, resource telemetry
2.8. PR head, merge-ref, main push CI authority
2.9. Nightly full regression
2.10. Golden and benchmark test separation
2.11. Workflow/job naming stability
2.12. Rollout, migration, and rollback strategy

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
- File: `.github/workflows/ci.yml`
- Triggers: `pull_request`, `push.branches: [main]`
- Python matrix: 3.11, 3.12
- Current jobs (as of main HEAD `a3a352a2`):

| Job | Command | Scope |
|---|---|---|
| task010-focused (3.11) | ruff + format + mypy + TASK-010 tests + pip-audit | Python 3.11 |
| task010-focused (3.12) | ruff + format + mypy + TASK-010 tests + pip-audit | Python 3.12 |
| integration | `pytest tests/integration` | Integration |
| units | `pytest tests/unit/test_units.py` | Unit conversions |
| repository-core | `pytest tests/unit/ --ignore=...r10 --ignore=...r12 --ignore=test_units.py` | Repository regression |
| correction-r10 | `pytest tests/unit/test_double_pipe_correction_r10.py` | Correction r10 |
| correction-r12 | `pytest tests/unit/test_double_pipe_correction_r12.py` | Correction r12 |

### 4.2 Known issues with current topology
- `repository-core` uses `--ignore` to exclude files, creating an implicit "remainder" shard
- No formal dependency lock (`uv.lock` not committed)
- No pytest marker taxonomy
- `MagicMock` used as provider in multiple test files without typed protocol conformance

## 5. Dependency Lock

### 5.1 Authority
- Tool: `uv` (installed, version verified)
- Lock file: `uv.lock`
- Install command: `uv sync --frozen --all-extras`
- CI must use `uv sync --frozen --all-extras` instead of `pip install -e ".[dev]"`

### 5.2 Rules
- `uv.lock` must be committed to the repository
- All CI jobs must install from the lock file
- Lock file updates require explicit PR review
- Lock file must be regenerated with `uv lock` and committed as a separate change when dependencies are modified

### 5.3 Migration
- PR 1: Add `uv.lock` and update CI install commands
- No behavioral change to tests or production code

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
| `golden` | Benchmark/golden result regression | Yes | Yes (real) |
| `slow` | Long-running tests (>30s expected) | Varies | Varies |

### 7.1 Registration
Markers must be registered in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "pure: pure unit tests, no CoolProp, no provider",
    "provider: property provider contract tests",
    "coolprop: CoolProp backend integration",
    "integration: multi-component integration tests",
    "golden: benchmark/golden result regression",
    "slow: long-running tests",
]
```

### 7.2 Application
- Every test file must be tagged with at least one marker
- Tests may carry multiple markers (e.g., `@pytest.mark.coolprop` + `@pytest.mark.slow`)
- Marker assignment is reviewed as part of shard manifest maintenance

## 8. Test Shard Manifest

### 8.1 Format
Shards are defined in a YAML manifest file: `ci-shard-manifest.yml`

```yaml
shards:
  - name: <shard-name>
    job: <ci-job-name>
    python: ["3.11", "3.12"]  # or subset
    files:
      - tests/unit/test_file_a.py
      - tests/unit/test_file_b.py
    markers: []  # optional marker filter
    timeout: 120  # seconds per test node
```

### 8.2 Sorting rules
- Shard names: alphabetical
- Files within shard: alphabetical
- Python versions: ascending

### 8.3 Completeness algorithm
```python
def verify_shard_completeness(manifest, test_root):
    all_files = set()
    for shard in manifest["shards"]:
        for f in shard["files"]:
            assert f not in all_files, f"{f} belongs to multiple shards"
            all_files.add(f)
    discovered = discover_all_test_files(test_root)
    hidden = discovered - all_files
    assert not hidden, f"Hidden test files: {hidden}"
```

### 8.4 Integrity rule
Every test file must belong to exactly one shard. No test file may be hidden by `--ignore`. The completeness check runs in a dedicated CI job.

## 9. "--ignore" Elimination

### 9.1 Current state
`repository-core` uses `--ignore` to exclude correction-r10, correction-r12, and units test files.

### 9.2 Target state
All shards use explicit file lists. `--ignore` is not used in any CI job.

### 9.3 Migration
- Replace `--ignore` patterns with explicit file lists in shard manifest
- Verify no test file is lost during migration
- Completeness check job validates the transition

## 10. CoolProp Test Isolation

### 10.1 Rules
- CoolProp-dependent tests carry `@pytest.mark.coolprop`
- CoolProp tests run in dedicated shards with explicit timeout
- CoolProp tests do not share shard with pure unit tests
- CoolProp test shards may use extended timeout (180s)

### 10.2 Rationale
CoolProp C extension can cause resource contention when mixed with other test processes. Isolation prevents cascading failures.

## 11. Typed PropertyProvider Test Doubles

### 11.1 Context
TASK-010 exposed unsafe dynamic `MagicMock` attributes at the provider-identity boundary. Production extraction was hardened, while strict typed provider test doubles remain a follow-up improvement.

### 11.2 Required test doubles

#### StubPropertyProvider
```python
class StubPropertyProvider:
    """Returns fixed values for all property queries."""
    def __init__(self, *, fixed_values: dict[str, float] | None = None):
        ...
    def get_property(self, fluid: str, prop: str, **kw) -> float:
        return self._fixed_values[(fluid, prop)]
```

#### ReplayPropertyProvider
```python
class ReplayPropertyProvider:
    """Replays recorded sequences of property values for deterministic testing."""
    def __init__(self, sequences: dict[str, list[float]]):
        ...
    def get_property(self, fluid: str, prop: str, **kw) -> float:
        return next(self._sequences[(fluid, prop)])
```

#### SelectiveFailurePropertyProvider
```python
class SelectiveFailurePropertyProvider:
    """Injects failures at configurable call indices."""
    def __init__(self, failure_indices: dict[str, int], error_factory: Callable):
        ...
    def get_property(self, fluid: str, prop: str, **kw) -> float:
        self._counts[(fluid, prop)] += 1
        if self._counts[(fluid, prop)] == self._failure_indices.get((fluid, prop)):
            raise self._error_factory()
        return self._real_provider.get_property(fluid, prop, **kw)
```

#### CountingPropertyProvider
```python
class CountingPropertyProvider:
    """Wraps a real provider and counts calls for assertion."""
    def __init__(self, inner: PropertyProvider):
        self._inner = inner
        self._call_count = 0
    def get_property(self, fluid: str, prop: str, **kw) -> float:
        self._call_count += 1
        return self._inner.get_property(fluid, prop, **kw)
```

### 11.3 Rules
- All test doubles must implement the `PropertyProvider` protocol
- Test doubles must not use bare `MagicMock()` as a provider success path
- Test doubles may use `MagicMock` only for isolated attribute testing (e.g., `_provider_snapshot` tests)
- Real provider test doubles must return typed domain artifacts

## 12. CI Authority

### 12.1 Three CI authority tracks

| Track | Trigger | SHA used | Purpose |
|---|---|---|---|
| PR head | `pull_request` | PR head SHA | Validate PR changes |
| Merge-ref | `pull_request` | Merge commit SHA | Validate merge outcome |
| Main push | `push.branches: [main]` | Merge SHA on main | Validate mainline |

### 12.2 Rules
- All three tracks must use the same workflow file (`.github/workflows/ci.yml`)
- PR head CI must pass before merge
- Main push CI must pass post-merge; failure triggers investigation
- Merge-ref CI is optional but recommended for large PRs

## 13. Nightly Full Regression

### 13.1 Boundary
- Nightly runs the full test suite including `golden` and `slow` markers
- Nightly is separate from PR-blocking CI
- Nightly failures do not block PR merges
- Nightly failures create issues for investigation

### 13.2 Schedule
- Daily at a fixed time (e.g., 03:00 UTC)
- Triggered by `schedule` event in workflow

### 13.3 Telemetry
- Upload JUnit XML, durations, and coverage report as artifacts
- Retain artifacts for 30 days

## 14. Timeout, Cancellation, and Retry Rules

### 14.1 Timeout
- Each shard defines a per-test timeout (default: 120s)
- CoolProp shards: 180s
- Golden shards: 300s
- Total shard timeout: sum of per-test timeouts × 1.5 safety margin

### 14.2 Cancellation
- GitHub Actions runner cancellation (e.g., resource exhaustion) is recorded but not retried automatically
- Failed shards are investigated before re-run

### 14.3 Retry
- No automatic retry for test failures (determinism requirement)
- CI-level retry for infrastructure failures (runner unavailable) is acceptable

## 15. JUnit, Durations, Coverage, and Resource Telemetry

### 15.1 Required arguments
```
pytest --timeout=<shard_timeout> \
       --durations=20 \
       --junitxml=test-results.xml \
       ...
```

### 15.2 Artifacts
- `test-results.xml`: JUnit XML per shard
- `durations.txt`: Per-test timing (from `--durations=20`)
- `coverage.xml`: Coverage report (if coverage enabled)

### 15.3 Upload
All artifacts uploaded via `actions/upload-artifact@v4` with shard-specific names.

## 16. Golden and Benchmark Test Separation

### 16.1 Golden tests
- Carry `@pytest.mark.golden`
- Run in dedicated shard with strict determinism checks
- Golden result updates require explicit PR approval
- Golden tests verify against committed baseline values

### 16.2 Benchmark tests
- Carry `@pytest.mark.slow` (and optionally `@pytest.mark.golden`)
- Run in nightly, not in PR CI
- Benchmark results are recorded but do not block merges

### 16.3 Isolation rule
Golden and benchmark tests must not share shard with correctness tests.

## 17. Workflow/Job Naming Stability

### 17.1 Rules
- Job names must be stable across PRs (no dynamic names)
- Job names must be unique within a workflow run
- Job names must match shard manifest `job` field
- Renaming a job requires updating the manifest and all references

### 17.2 Current stable names
- `task010-focused (3.11)`
- `task010-focused (3.12)`
- `integration`
- `units`
- `repository-core`
- `correction-r10`
- `correction-r12`

## 18. Shard Input/Output/Failure Semantics

### 18.1 Input
- Git checkout of the commit SHA
- Python version from matrix
- Dependencies installed from `uv.lock`

### 18.2 Output
- JUnit XML artifact
- Durations artifact
- Exit code 0 (success) or non-zero (failure)

### 18.3 Failure semantics
- Any test failure in a shard fails the shard job
- Shard failures are independent (no cross-shard dependencies)
- All shards must pass for overall CI success

## 19. Rollout and Migration Order

| Phase | Action | Risk |
|---|---|---|
| 1 | Add `uv.lock` to repository | Low — lock file only |
| 2 | Update CI install to use `uv sync --frozen` | Low — same deps, different installer |
| 3 | Add pytest markers to `pyproject.toml` | Low — metadata only |
| 4 | Create shard manifest | Medium — must verify completeness |
| 5 | Replace `--ignore` with explicit file lists | Medium — must not lose test files |
| 6 | Add completeness check CI job | Low — new job |
| 7 | Add typed provider test doubles | Medium — test refactoring |
| 8 | Migrate tests from bare MagicMock to typed doubles | High — requires per-file review |
| 9 | Add CoolProp isolation | Low — marker + shard separation |
| 10 | Add JUnit/durations telemetry | Low — new arguments + artifacts |
| 11 | Add nightly workflow | Low — new workflow, non-blocking |

## 20. Rollback Strategy

- Each phase is independently revertible via git revert
- `uv.lock` removal: revert commit, restore `pip install` in CI
- Shard manifest rollback: restore previous `--ignore` commands
- Typed doubles rollback: restore bare `MagicMock` usage (not recommended)
- Nightly workflow rollback: disable workflow via GitHub UI or delete workflow file

## 21. Implementation Acceptance Tests

Before TASK-015A implementation is considered complete:

1. `uv sync --frozen --all-extras` succeeds on fresh clone
2. All CI jobs pass with `uv sync --frozen` installation
3. Shard completeness check passes (no hidden files)
4. No `--ignore` used in any CI job
5. All test doubles implement `PropertyProvider` protocol
6. No bare `MagicMock()` as provider success path in production tests
7. CoolProp tests isolated in dedicated shard
8. JUnit XML uploaded for every shard
9. Nightly workflow runs successfully (manual trigger)
10. Golden tests separated from correctness tests

## 22. TASK-010 Frozen Contract Preservation

This design contract must not alter:
- TASK-010 frozen contract SHA: `9a1faeb92f4015a62f9d9add0739f3853a876415`
- TASK-010 API behavior, DTOs, envelopes, artifact bundles, or report model
- TASK-010 repository state machine or CAS semantics
- TASK-010 ranking, formatter authority, or verifier logic

Any change that affects TASK-010 behavior requires a separate design contract and approval.

## 23. TASK-011 Dependency

TASK-011 (benchmark cases) must not be started until TASK-015A implementation is complete and CI environment is stable. This is a hard dependency.

## 24. Design Freeze Process

1. Design contract reviewed and approved by independent reviewer
2. Frozen Contract SHA established: hash of the approved design document
3. Any modification to the design contract requires a new review cycle
4. Implementation must match the frozen design exactly

---

**Design Status:** READY_FOR_REVIEW
**Implementation Authorization:** NOT GRANTED
**Frozen Contract SHA:** Pending
