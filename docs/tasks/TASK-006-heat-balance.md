# TASK-006 — Heat-balance and specification closure

**Status:** IN_PROGRESS  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-002, TASK-003, TASK-005  
**GitHub Issue:** #13  
**Branch:** `codex/task-006-heat-balance`

## Objective

Resolve valid combinations of duty, flow and inlet/outlet states while enforcing energy conservation, phase consistency and temperature feasibility.

## In scope

- Single-phase sensible heat for v0.1.
- Known-duty, known-outlet and mixed specification modes.
- Hot/cold energy residual and tolerance.
- Terminal-temperature, minimum-approach and temperature-cross checks.
- Property-provider iteration at representative or segmented states.
- Explicit unsupported response for phase change.
- Structured warnings, blockers and run failures.
- Deterministic result hashing and provenance serialization.

## Explicitly out of scope

- LMTD and epsilon-NTU.
- Heat-transfer coefficients or new engineering correlations.
- Pressure-drop calculations.
- Geometry sizing, rating, candidate generation or optimization.
- Two-phase heat balance.
- Database, API and report implementation.

## Required engineering contracts

### Specification modes

The implementation must explicitly enumerate supported and unsupported combinations rather than infer them implicitly. At minimum:

- both inlet states, both mass flows and one outlet known;
- both inlet states, both mass flows and duty known;
- both inlet states, both mass flows and both outlets known for verification;
- one side fully specified and the other outlet unknown;
- mixed specification with one independently solvable unknown.

Under-specified and over-specified combinations must return stable structured errors.

### Energy convention

- Heat duty is positive from hot stream to cold stream.
- Hot-side enthalpy decrease and cold-side enthalpy increase are both reported as positive transferred heat.
- Residual and relative imbalance definitions must be explicit and documented.
- Approved solutions require relative imbalance below `0.001` (0.1%).
- Zero-duty cases must be handled explicitly, without division by zero.

### Property evaluation

- Use `PropertyProvider`; do not embed constant heat-capacity assumptions in public services.
- Record provider name/version, fluid identity and all evaluated states.
- Detect property failures and out-of-range states as structured blockers.
- Phase-change or unsupported phase transitions must return `NOT_IMPLEMENTED`/`UNSUPPORTED_SERVICE`, never a guessed sensible-heat result.

### Temperature feasibility

- Reject hot outlet above hot inlet for positive duty.
- Reject cold outlet below cold inlet for positive duty.
- Detect terminal temperature cross.
- Detect non-positive terminal approach where applicable.
- Use explicit tolerance for near-equality; do not rely on exact floating-point equality.

### Determinism and provenance

- Public result models are immutable and reject NaN/Inf.
- Canonical serialization and result hash are deterministic.
- Provenance includes design/case revision identity, property calls, solver/specification mode, warnings, blockers and software version.
- Same canonical input, provider result and software version yield the same result hash.

## Expected files

- `src/hexagent/core/heat_balance.py`
- `src/hexagent/domain/thermal_service.py`
- `tests/unit/test_heat_balance.py`
- `tests/integration/test_heat_balance_property_provider.py`
- `tests/golden/heat_balance/*.json`
- `docs/HEAT_BALANCE.md`

Existing unit, property, provenance and structured-message modules must be reused rather than duplicated.

## Acceptance criteria

- [ ] All supported specification combinations are enumerated and validated.
- [ ] Under- and over-specified cases return actionable structured errors.
- [ ] Energy imbalance is below 0.1% for approved cases.
- [ ] Impossible outlet temperatures are rejected.
- [ ] Terminal cross and non-positive approach violations are rejected.
- [ ] Zero flow, zero duty, negative flow and invalid state inputs are deterministic.
- [ ] Phase-change cases return explicit unsupported status in v0.1.
- [ ] Property-provider calls and versions are captured in provenance.
- [ ] Canonical result hashing is repeatable and changes with material inputs.
- [ ] No NaN/Inf escapes public result models.
- [ ] Existing tests remain green.
- [ ] Ruff, Ruff format, repository-wide mypy, pytest and pip-audit pass on Python 3.11 and 3.12.

## Test plan

- liquid-liquid nominal balance;
- gas-liquid nominal balance;
- one unknown hot outlet;
- one unknown cold outlet;
- known duty;
- both outlets known for verification;
- inconsistent duty/outlet specifications;
- under-specified and over-specified combinations;
- zero and negative flow;
- zero duty;
- temperature cross and terminal pinch;
- property-provider failure and out-of-range state;
- explicit phase-change rejection;
- hash repeatability and changed-input detection;
- provenance graph serialization;
- golden cases with documented tolerances.
