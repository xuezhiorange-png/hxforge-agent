# TASK-016 Alpha Preview v0.1 Trial Design

Status: DESIGN DRAFT  
Scope: docs-only trial design  
Implementation: NOT AUTHORIZED  
TASK-017+: NOT STARTED / NOT AUTHORIZED

## 1. Purpose

TASK-016 Alpha Preview v0.1 is an internal trial design for demonstrating the
completed TASK-016 approved tube, pipe, and hairpin geometry catalog foundation
without starting TASK-017 or productizing the agent.

The preview is intended to give engineering users a small, deterministic trial
surface for reviewing:

1. approved geometry catalog behavior;
2. structured validation blockers;
3. deterministic catalog and record hashing;
4. approved-only selection semantics;
5. traceable case fixtures and expected outputs;
6. clear limitations before TASK-017+ authorization.

This document defines the trial package shape and acceptance criteria only. It
does not authorize implementation, code, CLI entry points, public APIs, report
rendering, databases, cost logic, pressure-drop logic, material suitability
logic, or any TASK-017+ work.

## 2. Authority baseline

The trial design depends on completed TASK-016 implementation state:

- TASK-016 design FCAS: `654a2708de808c9f1518f1a69eda92f95a4d37c5`
- TASK-016 implementation PR: `#67`
- TASK-016 implementation merge commit: `ac7a4152698f039b4d6795f6a814228cb3c43def`
- TASK-016 implementation Issue: `#66`, closed as completed

This trial must remain subordinate to the frozen TASK-016 contract. It must not
modify frozen TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015 contract
bodies, and it must not mutate TASK-015A.

## 3. Trial version identity

- Name: `hxforge-agent Alpha Preview v0.1`
- Internal task name: `TASK-016 Alpha Preview v0.1`
- Audience: internal engineering reviewers and maintainers
- Maturity: alpha / internal preview
- Guarantee level: deterministic examples only, not production suitability
- Review mode: explicit case-by-case engineering verification

## 4. Intended user workflow

The eventual trial package, if separately authorized for implementation, should
support this workflow:

1. Reviewer selects a prepared trial case.
2. Trial runner validates the case inputs.
3. Trial runner loads an approved geometry catalog fixture.
4. Trial runner emits deterministic success or blocker output.
5. Reviewer compares output against expected golden artifacts.
6. Reviewer records whether the behavior is acceptable for broader internal
   testing.

This workflow is descriptive only. It does not authorize creation of the runner.

## 5. Proposed package layout

If implementation is later authorized, the trial package should be limited to
these path families:

```text
examples/task016_alpha_preview/
  README.md
  catalog/
    approved_geometry_catalog.v0.1.json
  cases/
    case_001_catalog_success.json
    case_002_hairpin_success.json
    case_003_blocker_unapproved_geometry.json
    case_004_blocker_missing_pipe_reference.json
    case_005_blocker_dimension_inconsistent.json
  expected/
    case_001_result.golden.json
    case_002_result.golden.json
    case_003_blocker.golden.json
    case_004_blocker.golden.json
    case_005_blocker.golden.json

scripts/
  run_task016_alpha_preview_case.py

docs/trials/
  TASK-016-alpha-preview-v0.1.md
```

The current design change creates only this document. The `examples/` and
`scripts/` entries above are proposed future implementation targets, not current
files.

## 6. Allowed future implementation surfaces

A future implementation authorization may allow only:

1. example JSON fixtures under `examples/task016_alpha_preview/`;
2. expected golden JSON outputs under `examples/task016_alpha_preview/expected/`;
3. a minimal preview runner under `scripts/`;
4. trial documentation under `docs/trials/`;
5. test coverage that proves the trial fixtures remain deterministic.

Any such future work must be separately authorized by Charles.

## 7. Explicit non-scope

This trial design does not authorize:

- TASK-017 material grade logic;
- TASK-017 mass or weight logic;
- TASK-017 preliminary mechanical suitability checks;
- TASK-018 cost model, C0/C1, or life-cycle energy estimate;
- pressure-drop implementation or C4 logic;
- public API changes;
- report rendering changes;
- production database, ORM, or Alembic migrations;
- user accounts, permissions, or project management features;
- web UI, desktop UI, mobile UI, or hosted service integration;
- external services, secrets, OIDC, registry push, or deployment;
- shell-and-tube, plate, air cooler, two-phase, refrigerant, or vendor catalog
  implementation;
- mutation of TASK-015A;
- mutation of frozen TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015
  contract bodies;
- branch protection or release-gate changes;
- automatic issue closeout or next-task start.

## 8. Proposed trial cases

### 8.1 Success case: approved tube / pipe catalog load

Purpose: prove that an approved tube and pipe catalog fixture can be loaded,
ordered deterministically, and hashed deterministically.

Expected output categories:

- catalog identity;
- ordered record IDs;
- record hashes;
- catalog content hash;
- no blockers.

### 8.2 Success case: approved hairpin references

Purpose: prove that a hairpin record with approved tube and pipe references is
accepted and remains deterministic.

Expected output categories:

- hairpin geometry ID;
- referenced tube geometry ID;
- referenced pipe geometry ID;
- content hash;
- no blockers.

### 8.3 Blocker case: unapproved geometry

Purpose: prove that non-approved records are rejected through structured
blockers.

Expected blocker:

```text
geometry_record_unapproved
```

Expected context should identify the offending `geometry_id` and
`approval_state`.

### 8.4 Blocker case: missing pipe reference

Purpose: prove that a hairpin record referencing a missing pipe geometry is
rejected.

Expected blocker:

```text
geometry_reference_missing
```

Expected context should include:

```text
reference_field = pipe_geometry_id
```

### 8.5 Blocker case: inconsistent dimensions

Purpose: prove that inconsistent tube or pipe dimensions are rejected before any
consumer can treat them as approved geometry.

Expected blocker:

```text
geometry_dimension_inconsistent
```

## 9. Trial output contract

A future implementation should emit JSON-compatible outputs. The success output
shape should be intentionally small:

```json
{
  "status": "pass",
  "trial_version": "TASK-016-alpha-preview-v0.1",
  "case_id": "case_001_catalog_success",
  "catalog_content_hash": "<sha256>",
  "ordered_geometry_ids": ["..."],
  "record_hashes": {
    "<geometry_id>": "<sha256>"
  }
}
```

The blocker output shape should be:

```json
{
  "status": "blocked",
  "trial_version": "TASK-016-alpha-preview-v0.1",
  "case_id": "case_004_blocker_missing_pipe_reference",
  "error_code": "geometry_reference_missing",
  "context": {
    "reference_field": "pipe_geometry_id"
  }
}
```

No floating-point engineering calculation output is required for this preview
version unless separately authorized in a later implementation task.

## 10. Acceptance criteria

The Alpha Preview v0.1 implementation, if later authorized, must satisfy all of
these criteria:

1. all trial fixture files are deterministic and committed as repository data;
2. every success case produces stable output across Python 3.11 and 3.12;
3. every blocker case produces stable `error_code` and structured `context`;
4. catalog records are sorted by the TASK-016 deterministic ordering rule;
5. record and catalog hashes are stable and derived from canonical JSON;
6. only `approval_state == "approved"` records are selectable;
7. hairpin tube and pipe references are both validated;
8. missing pipe reference blocker is covered by fixture and test;
9. non-approved reference blocker is covered by fixture and test;
10. no TASK-017+ semantics are introduced;
11. no public API, report rendering, DB, ORM, Alembic, or deployment changes are
    introduced;
12. CI includes the preview fixtures in test-shard manifest ownership if new
    test files are added;
13. the implementation PR remains Draft until Charles explicitly authorizes
    Ready;
14. merge and closeout require separate Charles authorization.

## 11. Suggested future implementation task split

Future implementation should be split into small auditable units:

1. `TASK-016-TRIAL-001`: add docs and fixture skeletons only;
2. `TASK-016-TRIAL-002`: add deterministic catalog success fixtures;
3. `TASK-016-TRIAL-003`: add blocker fixtures;
4. `TASK-016-TRIAL-004`: add minimal runner script;
5. `TASK-016-TRIAL-005`: add golden verification tests and CI manifest ownership;
6. `TASK-016-TRIAL-006`: final closeout review.

Each implementation step requires explicit authorization.

## 12. Governance gates

This design has the following governance gates:

- implementation is not authorized by this document;
- examples are not created by this document;
- scripts are not created by this document;
- TASK-017+ remains blocked;
- Issue or PR creation for implementation requires separate authorization;
- Ready, merge, issue closeout, and next-task start all require separate
  Charles authorization.

## 13. Current design-only completion condition

This design-only task is complete when:

1. this document exists under `docs/trials/`;
2. no production code changes are present;
3. no test code changes are present;
4. no examples or scripts are created in this design-only commit;
5. no TASK-017+ files are created;
6. no frozen TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015 contract
   bodies are changed.
