# TASK-005 — Calculation provenance and structured errors

**Status:** READY  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-001

## Objective

Make every result reproducible and every failure visible through a calculation graph, structured warnings, run metadata and stable result hashing.

## In scope

- Run ID, input snapshot and revision identity.
- Calculation nodes and parent-child relationships.
- Formula/property/provider versions.
- Warning severity and blocker rules.
- Convergence, applicability, property and input errors.
- Canonical serialization and result hash.

## Expected files

- `src/hexagent/core/provenance.py`
- `src/hexagent/core/errors.py`
- `src/hexagent/domain/results.py`
- `tests/unit/test_provenance.py`
- `docs/PROVENANCE.md`

## Acceptance criteria

- [ ] Same canonical input and software version yield the same hash.
- [ ] Every public result includes warnings and provenance.
- [ ] Blocking errors prevent recommendation/report-ready status.
- [ ] Floating-point serialization is stable and documented.
- [ ] Sensitive or licensed payloads are not embedded in trace records.

## Test plan

Hash repeatability, changed-input detection, graph serialization, blocker propagation and warning ordering.
