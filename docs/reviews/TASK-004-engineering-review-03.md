# TASK-004 Engineering Review — Round 3

**PR:** #9  
**Head reviewed:** `cbbd3d2d04cb9ae49972533689c28d70afdac834`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27911538102` passed.

Review-02 is partially resolved. Input-hash validation, PENDING-only run creation, mandatory provenance payload hashes, terminal-run graph checks, and record synchronization improved. Five contract gaps remain.

## 1. The real revision repository still does not enforce chain invariants

`InMemoryDesignCaseRevisionRepository.add()` still checks only duplicate IDs, revision-number conflicts and parent existence. It does not verify:

- `parent.case_id == child.case_id`;
- `child.revision_number == parent.revision_number + 1`;
- the parent is the immediately preceding revision.

The new tests use a private `_DirectRevisionRepo` and call `RevisionService.verify_revision_integrity()`. That does not prove the public repository rejects an invalid insert.

Required:

- implement the three checks directly in `InMemoryDesignCaseRevisionRepository.add()`;
- add tests that insert cross-case, numbering-gap and non-immediate-parent revisions directly into the real repository and assert rejection.

## 2. Full DesignCase unit-equivalent hashing is still not implemented or tested

`canonicalize_design_case()` still calls `case.model_dump()` before `_preprocess()`. Quantity objects are therefore converted to ordinary dictionaries before the SI-aware Quantity branch can run.

The new tests still hash isolated Quantity objects directly rather than creating complete DesignCase revisions in equivalent units.

Required:

- canonicalize the DesignCase while Quantity objects still retain their type semantics, or perform strict field-aware normalization of dumped quantity structures;
- create complete equivalent DesignCase objects using °C/K, bar/Pa, mm/m and kg/h/kg/s and prove identical revision canonical payloads and hashes;
- prove a true physical-value change changes the revision hash.

## 3. Recursive immutability is still bypassable

`FieldChange.before` and `FieldChange.after` remain unconstrained `Any` values and are not recursively frozen. `EngineeringMessage.context`, `RunFailure.context`, `ProvenanceNode.metadata` and `ProvenanceEdge.metadata` remain tuple containers whose nested `Any` values may contain mutable dicts/lists.

`deep_freeze()` also returns unknown objects unchanged, even though its documentation states unsupported mutable values should be rejected. The new tests use scalar metadata and verify only the outer container.

Required:

- recursively freeze `FieldChange.before/after` during construction and JSON round trip;
- recursively freeze message/failure/provenance metadata values;
- reject unsupported mutable/custom values rather than returning them unchanged, or define an explicit immutable-value protocol;
- add tests using nested dict/list values and attempt real mutation after construction and after JSON round trip.

## 4. The persistence-boundary provenance contract is incomplete

The repository rejects an empty graph only for terminal updates. It still accepts a newly persisted PENDING run with the default empty graph, although Review-02 requires every persisted run graph to contain CASE_REVISION and CALCULATION_RUN nodes.

WARNING/BLOCKER lineage is also not validated. The graph checks node presence and DAG structure but does not prove that warning/blocker nodes are reachable from an input, property or calculation node.

Required:

- make `InMemoryCalculationRunRepository.add()` reject empty or unanchored graphs;
- require CASE_REVISION and CALCULATION_RUN for every persisted run;
- validate WARNING/BLOCKER incoming lineage from an approved upstream node type;
- add real repository tests for empty graph, unanchored graph and orphan warning/blocker nodes.

## 5. Git commit identity remains under-constrained

`CalculationRun.git_commit` defaults to `"no-git"` and accepts any arbitrary string. Review-02 required either a validated git identity or a documented and validated sentinel policy.

Required:

- make `git_commit` explicit and validate either a 7–40 character hexadecimal git SHA or the exact approved sentinel `no-git`;
- reject empty strings and arbitrary text;
- document when `no-git` is allowed;
- add construction and JSON round-trip tests.

## Approval gate

After correction:

1. run Ruff, Ruff format check, mypy, pytest and pip-audit;
2. prove the real repositories enforce chain and provenance contracts;
3. prove complete DesignCase SI-equivalent revision hashing;
4. prove recursive immutability with nested mutation attempts;
5. synchronize the task card and PR description with the final test count and CI run.

Keep TASK-004 IN_PROGRESS and PR #9 Draft. Do not add PostgreSQL, FastAPI persistence, heat-balance equations, correlations, sizing/rating, or TASK-005 scope.
