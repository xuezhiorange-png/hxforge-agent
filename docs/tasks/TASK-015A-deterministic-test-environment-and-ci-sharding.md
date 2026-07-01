# TASK-015A — Deterministic Test Environment and CI Sharding: Design Contract

**Issue:** #33
**Status:** DESIGN READY_FOR_REVIEW
**Implementation Authorization:** NOT GRANTED
**TASK-015A Design Frozen Contract SHA:** Pending — to be set to the exact independently approved reviewed Head commit SHA

> Note: TASK-010 has its own frozen contract SHA: `9a1faeb92f4015a62f9d9add0739f3853a876415`.
> TASK-015A design contract SHA is distinct and pending independent approval.

---

## 1. Objective

Establish a deterministic, reproducible, and maintainable test environment for HXForge that eliminates hidden test files, provides explicit per-shard file manifests verified at pytest node-ID level per Python version, replaces ad-hoc `--ignore` with structured test partitioning, introduces typed provider test doubles conforming to the real `PropertyProvider` protocol, separates CoolProp-dependent tests from pure unit tests, adds mandatory CI telemetry with rerun-safe artifact identity, and defines clear authority for PR-head, merge-ref, and main-push CI tracks — all executed exclusively through the `uv`-managed locked project environment.

## 2. Scope

1. Dependency lock via `uv.lock` with freshness gate
2. Frozen `uv` installation authority (`astral-sh/setup-uv` with pinned commit SHA)
3. Locked environment execution authority (`uv run --locked` for all commands)
4. Pytest marker taxonomy
5. Test shard manifest specification with per-Python-version node-ID completeness proof
6. Typed `PropertyProvider` test doubles (real protocol)
7. CoolProp test isolation
8. Mandatory test coverage with event-local aggregation
9. JUnit, durations, coverage, resource telemetry with run_attempt-safe identity
10. PR-head, merge-ref, main-push tri-track CI authority
11. Nightly full regression
12. Golden and benchmark test separation
13. Structured pytest collection plugin
14. Workflow/job naming stability
15. Rollout, migration, and rollback strategy

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

To be executed per Python version before shard cutover:

```bash
# Per-version global collection via structured plugin
uv run --locked pytest --collect-only \
  -p tests.ci.collect_nodes_plugin \
  --hx-node-output global-nodes.py311.json \
  tests/
```

Artifact format: structured JSON per version per shard (see Section 18).

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

File ownership is determined globally by the manifest, independent of Python version:

```python
def verify_file_completeness(manifest: dict, test_root: str) -> None:
    """Verify D == M bidirectionally (global, version-independent)."""
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
    for shard in manifest["shards"]:
        assert shard["files"], f"Empty shard: {shard['name']}"
```

### 9.5 Per-Python-version node-ID completeness

Node collection completeness is verified separately for each supported Python version:

```python
from typing import Literal

PythonVersion = Literal["3.11", "3.12"]
ShardName = str
NodeId = str

def verify_per_version_node_completeness(
    manifest: dict,
    G_v: dict[PythonVersion, set[NodeId]],
    S_v_i: dict[tuple[PythonVersion, ShardName], set[NodeId]],
) -> None:
    """For each Python version, prove union equality and pairwise disjointness."""
    for version in ("3.11", "3.12"):
        applicable_shards = [
            shard for shard in manifest["shards"]
            if version in shard["python"]
        ]
        omitted_shards = [
            shard for shard in manifest["shards"]
            if version not in shard["python"]
        ]

        shard_union = set()
        for shard in applicable_shards:
            shard_union |= S_v_i[(version, shard["name"])]

        missing = G_v[version] - shard_union
        extra = shard_union - G_v[version]

        assert not missing, (
            f"Python {version}: missing node IDs: {missing}"
            f"\n  applicable shards: {[s['name'] for s in applicable_shards]}"
            f"\n  omitted shards: {[s['name'] for s in omitted_shards]}"
        )
        assert not extra, (
            f"Python {version}: extra node IDs: {extra}"
        )

        # Pairwise disjointness
        for i, shard_a in enumerate(applicable_shards):
            for shard_b in applicable_shards[i+1:]:
                overlap = (
                    S_v_i[(version, shard_a["name"])]
                    & S_v_i[(version, shard_b["name"])]
                )
                assert not overlap, (
                    f"Python {version}: overlap between "
                    f"{shard_a['name']} and {shard_b['name']}: {overlap}"
                )
```

### 9.6 Version-conditioned node behavior

If a file is in the manifest but produces zero nodes under a specific Python version:
- This is a **legal version condition** (e.g., `skipIf(sys.version_info < (3, 12))`)
- The file is still part of the shard's file ownership
- Zero nodes from that file under that version is valid
- Must be documented in collection metadata JSON
- NOT treated as collection error unless pytest itself fails

If a file produces nodes under one version but not another:
- Record in collection metadata: `{"file": "...", "python_version": "3.11", "node_count": 0, "reason": "skip_marker"}`
- Do not fail the completeness check for that version's shard

### 9.7 Node-ID parser requirements

Uses the structured pytest collection plugin (see Section 18), NOT stdout parsing.

### 9.8 Collection failure semantics

- `pytest --collect-only` exit code != 0 → FAIL
- Import errors → FAIL, plugin errors → FAIL
- `collection.stderr.txt` always preserved and uploaded
- Warnings during collection: recorded but do not fail
- Schema validation failure → FAIL
- `node_count` mismatch → FAIL
- Duplicate node ID → FAIL
- Wrong Python version in output → FAIL
- Wrong commit SHA → FAIL

### 9.9 Marker authority

- Manifest owns file ownership; markers own semantics only
- Markers do NOT change shard node ownership

## 10. "--ignore" Elimination

Replace `--ignore` with explicit file lists. Verify no test file lost (file-level + node-ID completeness per version). Completeness check job validates atomically.

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
    """Return the canonical cache identity for a fluid."""
    return FluidIdentifier.from_value(fluid).cache_identity
```

### 12.4 Query key types

All keys created via `from_request()` factory. Direct construction with hand-built identity strings prohibited.

```python
@dataclass(frozen=True)
class TPQueryKey:
    fluid_identity: str
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

### 12.5 StubPropertyProvider

Returns fixed typed results. Unconfigured input → deterministic error. `cache_info()` → fixed zeros. `clear_cache()` → no-op.

### 12.6 ReplayPropertyProvider

Replays ordered sequences. Sequence exhausted → error. Supports `assert_fully_consumed()`. Call log as immutable tuple.

**Cache semantics (frozen):**
- `cache_info()` → `PropertyCacheInfo(hits=0, misses=0, size=0, max_size=0)`
- `clear_cache()` → no-op; does NOT clear queues, reset positions, refill sequences, clear call log, or reset call index
- Optional `reset_replay()` → test-only, explicitly called; resets queues and call log

### 12.7 SelectiveFailurePropertyProvider

Wraps real `PropertyProvider`. Failure map: `dict[tuple[PropertyQueryType, int], Callable[[], Exception]]`. Call index starts at 1. Failure BEFORE delegation. All four query types supported. `cache_info()`/`clear_cache()` delegate to inner. Identity from inner.

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

### 16.1 Naming convention

GitHub artifact name: `<track>-<shard>-py<version>-attempt<run_attempt>-<artifact-kind>`

Internal file name: `<artifact-kind>.<track>.<shard>.py<version>.attempt<run_attempt>.<ext>`

### 16.2 Run attempt authority

- `run_id`: `github.run_id`
- `run_attempt`: `github.run_attempt`

### 16.3 Track values

`pr-head`, `merge-ref`, `main`, `nightly` (exactly these four)

### 16.4 Artifact kind values

| Kind | GitHub name suffix | Internal file |
|---|---|---|
| JUnit | `-junit` | `junit.<track>.<shard>.py<ver>.attempt<N>.xml` |
| pytest output | `-pytest-output` | `pytest-output.<track>.<shard>.py<ver>.attempt<N>.txt` |
| coverage data | `-coverage-data` | `coverage.<track>.<shard>.py<ver>.attempt<N>.xml` |
| coverage raw | `-coverage-raw` | `.coverage.<track>.<shard>.py<ver>.attempt<N>` |
| resource | `-resource` | `resource.<track>.<shard>.py<ver>.attempt<N>.json` |
| node inventory | `-node-inventory` | `nodes.<track>.<shard>.py<ver>.attempt<N>.json` |
| collection stderr | `-collection-stderr` | `collection-stderr.<track>.<shard>.py<ver>.attempt<N>.txt` |

### 16.5 Character rules

Lowercase ASCII, hyphen or dot separators, no spaces/slash/dynamic labels. Globally unique within workflow run.

### 16.6 Examples

```
pr-head-api-reporting-py311-attempt1-junit
pr-head-api-reporting-py311-attempt1-coverage-raw
pr-head-api-reporting-py311-attempt2-coverage-raw
merge-ref-units-py312-attempt2-resource
main-repository-core-py312-attempt1-junit
nightly-benchmark-py312-attempt1-resource
```

### 16.7 Rerun safety

- `actions/upload-artifact` overwrite mode is NOT the authority
- Artifacts are append-only per run attempt, distinguished by `run_attempt`
- Aggregate jobs MUST only consume artifacts matching current `github.run_attempt`
- Must reject: old attempt artifacts mixed with current, duplicate raw coverage for same identity, missing current attempt artifact, metadata `run_attempt` mismatch, different commit SHA for same identity

### 16.8 Artifact metadata

Each uploaded artifact includes metadata:

```json
{
  "run_id": "github.run_id",
  "run_attempt": "github.run_attempt",
  "track": "pr-head",
  "shard": "api-reporting",
  "python_version": "3.11",
  "commit_sha": "string",
  "artifact_kind": "coverage-raw"
}
```

Must not rely solely on filename — must validate metadata.

## 17. Telemetry Contracts

### 17.1 JUnit

```bash
uv run --locked pytest --junitxml=junit.${TRACK}.${SHARD}.py${PYVER}.attempt${ATTEMPT}.xml --timeout=<timeout> <args>
```

### 17.2 Durations

```bash
uv run --locked pytest --durations=20 --timeout=<timeout> <args> 2>&1 | tee pytest-output.${TRACK}.${SHARD}.py${PYVER}.attempt${ATTEMPT}.txt
```

### 17.3 Coverage (mandatory)

Every required test shard must emit raw coverage data and per-shard coverage XML.

```bash
export COVERAGE_FILE=".coverage.${TRACK}.${SHARD}.py${PYVER}.attempt${ATTEMPT}"
uv run --locked pytest --cov=hexagent --cov-branch \
  --cov-report=xml:coverage.${TRACK}.${SHARD}.py${PYVER}.attempt${ATTEMPT}.xml \
  --timeout=<timeout> <files>
test -s "$COVERAGE_FILE"
```

No minimum percentage threshold. Branch coverage enabled. Subprocess coverage out of scope.

### 17.4 Event-local coverage aggregation

Coverage aggregation is per-workflow-event, NOT across event types.

#### 17.4.1 Pull request workflow run

Two separate aggregate jobs:

```yaml
coverage-aggregate-pr-head:
  needs: [<all pr-head test jobs>]
  # Consumes only: track=pr-head, current run_attempt
  # Output: combined-coverage.pr-head.py-all.attempt<N>.xml

coverage-aggregate-merge-ref:
  needs: [<all merge-ref test jobs>]
  # Consumes only: track=merge-ref, current run_attempt
  # Output: combined-coverage.merge-ref.py-all.attempt<N>.xml
```

PR-head and merge-ref raw coverage MUST NOT be combined into a single correctness report (different commit SHA authority). An optional comparison report may be generated but must not be coverage combine input.

#### 17.4.2 Main push workflow run

```yaml
coverage-aggregate-main:
  needs: [<all main test jobs>]
  # Consumes only: track=main, current push SHA, current run_attempt
  # Output: combined-coverage.main.attempt<N>.xml
```

#### 17.4.3 Nightly workflow run

```yaml
coverage-aggregate-nightly:
  needs: [<all nightly test jobs>]
  # Consumes only: track=nightly, current checkout SHA, current run_attempt
  # Output: combined-coverage.nightly.attempt<N>.xml
```

#### 17.4.4 Aggregate completeness

Each aggregate job builds expected manifest from event matrix:
- expected track
- expected shard
- expected Python version
- expected run attempt
- expected commit SHA

Then proves: `downloaded identities == expected identities`

Failure conditions: missing identity → FAIL, extra identity → FAIL, duplicate identity → FAIL, wrong track → FAIL, wrong attempt → FAIL, wrong SHA → FAIL, zero-byte data → FAIL, `coverage combine` failure → FAIL, combined XML missing → FAIL, aggregate job not executed → overall CI FAIL.

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

## 18. Structured Pytest Collection Plugin

### 18.1 Implementation location

Frozen: `tests/ci/collect_nodes_plugin.py`

### 18.2 Pytest hook authority

```python
def pytest_collection_finish(session):
    """Emit structured JSON node inventory after collection."""
    nodes = sorted(item.nodeid for item in session.items)
    # Validate: no duplicates, UTF-8, slash-normalized
    output = {
        "schema_version": "1",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "pytest_version": pytest.__version__,
        "commit_sha": os.environ.get("COMMIT_SHA", ""),
        "track": os.environ.get("CI_TRACK", ""),
        "shard": os.environ.get("CI_SHARD", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
        "node_count": len(nodes),
        "node_ids": nodes,
    }
    # Write to --hx-node-output path
```

### 18.3 Node inventory schema

```json
{
  "schema_version": "1",
  "python_version": "3.11",
  "pytest_version": "9.1.1",
  "commit_sha": "string",
  "track": "pr-head",
  "shard": "api-reporting",
  "run_id": "string",
  "run_attempt": 1,
  "node_count": 2,
  "node_ids": [
    "tests/unit/test_example.py::test_a",
    "tests/unit/test_example.py::test_b[param value]"
  ]
}
```

### 18.4 Node ID rules

- UTF-8 strings
- Exact `pytest item.nodeid` values
- Slash normalized to `/`
- Sorted lexicographically
- Duplicates prohibited
- No trimming inside parameter values
- No modification of `::` or `[]`
- Supports: parameterized IDs, spaces in parameters, Unicode parameters, nested classes, multiple `::` components, bracket content, platform-specific path separators

### 18.5 Collection command

```bash
uv run --locked pytest --collect-only \
  -p tests.ci.collect_nodes_plugin \
  --hx-node-output nodes.${TRACK}.${SHARD}.py${PYVER}.attempt${ATTEMPT}.json \
  <args>
```

Global collection:

```bash
uv run --locked pytest --collect-only \
  -p tests.ci.collect_nodes_plugin \
  --hx-node-output global-nodes.py${PYVER}.attempt${ATTEMPT}.json \
  tests/
```

### 18.6 Failure semantics

- pytest collection exit != 0 → FAIL
- Plugin import error → FAIL
- Schema validation failure → FAIL
- Duplicate node ID → FAIL
- `node_count` mismatch → FAIL
- Missing output JSON → FAIL
- Wrong Python version → FAIL
- Wrong commit SHA → FAIL
- Wrong track/shard/attempt → FAIL
- `collection.stderr.txt` preserved as independent artifact
- stdout preserved for diagnostics, but NOT node authority

### 18.7 Acceptance fixtures

At minimum:
- Simple function node
- Class method node
- Parameterized node with spaces
- Parameterized node with Unicode
- Parameterized node with brackets
- Node with multiple `::` components
- Windows-style input path normalization
- Duplicate node rejection
- Empty collection handling
- Collection import failure
- Plugin failure
- Schema mismatch

### 18.8 Global and shard collection consistency

Global and shard collection MUST use the same plugin, same schema, same locked environment, same Python version, same pytest version, same `pyproject.toml`, same working directory, same environment variables.

## 19. Golden and Benchmark Separation

### 19.1 Definitions

- **golden**: Correctness authority — deterministic regression against approved baseline. PR-blocking.
- **benchmark**: Performance observation authority — timing/throughput/memory. Not correctness authority. Nightly/non-blocking.

### 19.2 Rules

- Golden tests run in dedicated golden correctness shards
- Golden shards do not contain: non-golden correctness nodes, benchmark nodes
- Benchmark shards do not contain: golden nodes, PR-blocking correctness nodes
- `golden` and `benchmark` are mutually exclusive on a single test
- `@pytest.mark.benchmark` does NOT imply `@pytest.mark.golden`
- `@pytest.mark.golden` does NOT imply `@pytest.mark.coolprop`
- Golden result updates require explicit PR approval

### 19.3 Acceptance gates

- Every golden node belongs to exactly one dedicated golden shard
- No non-golden correctness node belongs to a golden shard
- Every benchmark node belongs to exactly one nightly benchmark shard
- No benchmark node belongs to a PR-blocking shard
- No node carries both `golden` and `benchmark` markers

## 20. Workflow/Job Naming Stability

Job names stable, unique within run, match manifest `job` field. Renaming requires manifest update.

## 21. Shard Input/Output/Failure Semantics

**Input:** Git checkout, Python version, `uv sync --locked --all-extras`.
**Output:** JUnit, durations, coverage raw + XML (mandatory), resource telemetry, node inventory JSON.
**Failure:** Any test failure fails shard. Shards independent. All required shards must pass.

## 22. Rollout Order

| Phase | Action | Gate |
|---|---|---|
| 1 | Freeze uv authority + `uv.lock` + freshness gate + `uv run --locked` for all | `uv lock --check`; `git diff --exit-code`; all commands `uv run --locked` |
| 2 | Add marker registration only | `uv run --locked pytest --markers` |
| 3 | Add manifest schema, parser, file+node-ID verifiers (shadow mode) | Verifier runs, no routing |
| 4 | Implement `tests/ci/collect_nodes_plugin.py` | Plugin produces valid schema JSON |
| 5 | Generate baseline topology inventory per Python version | Per-version node union and overlaps documented |
| 6 | Add typed `PropertyProvider` doubles, migrate tests | mypy protocol proof; no routing change |
| 7 | Introduce explicit shards, remove `--ignore` atomically | Completeness verifier + plugin required in same PR |
| 8 | Add PR-head and merge-ref tracks | SHA assertions pass |
| 9 | Add JUnit, durations, coverage, telemetry + event-local `coverage-aggregate` | Artifacts uploaded; aggregates pass |
| 10 | Add nightly workflow | Manual trigger test passes |

Rollback: each phase revertible via `git revert`. Bare MagicMock NOT a recommended long-term rollback state.

## 23. Implementation Acceptance Tests

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
11. Python 3.11 file completeness: PASS
12. Python 3.11 node union equality: PASS
13. Python 3.11 node pairwise disjointness: PASS
14. Python 3.12 file completeness: PASS
15. Python 3.12 node union equality: PASS
16. Python 3.12 node pairwise disjointness: PASS
17. No `--ignore` in any CI job
18. All test doubles implement `PropertyProvider` (mypy)
19. No bare MagicMock provider success path
20. CoolProp tests isolated in dedicated shard
21. JUnit XML uploaded per shard with attempt-safe name
22. Coverage raw + XML uploaded per shard (mandatory) with attempt-safe name
23. Event-local combined coverage by `coverage-aggregate` jobs
24. Resource telemetry JSON per shard with attempt-safe name
25. PR-head SHA assertion passes
26. Merge-ref SHA assertion passes
27. Main-push SHA assertion passes
28. Nightly workflow runs
29. Every golden node in exactly one dedicated golden shard
30. No non-golden correctness node in golden shard
31. Every benchmark node in exactly one nightly benchmark shard
32. No benchmark node in PR-blocking shard
33. No node carries both `golden` and `benchmark`
34. Structured collection plugin produces valid JSON for every shard
35. Collection stderr preserved for every shard

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
| Typed PropertyProvider protocol check (mypy) | YES |
| No bare MagicMock provider success path | YES |
| JUnit artifact per shard | YES |
| Coverage raw data per shard (mandatory) | YES |
| Coverage XML per shard (mandatory) | YES |
| Event-local combined coverage | YES |
| Artifact identity includes run_attempt | YES |
| Aggregate consumes current attempt only | YES |
| Old/new attempt mixing rejected | YES |
| Durations/log artifact per shard | YES |
| Resource telemetry artifact per shard | YES |
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
