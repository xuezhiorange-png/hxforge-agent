# TASK-004 Engineering Review — Round 1

**PR:** #9  
**Head reviewed:** `b11037678f8a003fc224c214bc33d4ab512b55bb`  
**Decision:** CHANGES REQUIRED  
**CI:** Python 3.11 and 3.12 quality jobs passed.

The implementation establishes a useful skeleton, but the core immutability, audit and provenance contracts can still be bypassed. The following items are blocking.

## 1. Canonical JSON destroys ordered tuple semantics

`canonical._preprocess()` sorts every tuple before serialization. Two different ordered values such as `(hot, cold)` and `(cold, hot)` therefore produce the same canonical JSON and hash. Tuples are not sets and must preserve order unless a specific field is explicitly unordered.

Required:

- preserve list and tuple order;
- sort only set/frozenset or explicitly declared unordered collections;
- add tests proving reversed tuples produce different JSON and hashes;
- document which collections are ordered and unordered.

## 2. Revision and provenance models are only shallowly immutable

`DesignCaseRevision` is frozen, but contains a mutable `canonical_payload` dict and a nested `DesignCase`. `EngineeringMessage`, `ProvenanceNode`, `ProvenanceEdge` and `ProvenanceGraph` are frozen Pydantic models but contain mutable dicts and lists. The in-memory repositories return the same object references.

A caller can mutate `revision.canonical_payload`, `graph.nodes`, `graph.edges` or metadata after validation and silently invalidate hashes or DAG guarantees.

Required:

- use deeply immutable representations or defensive canonical copies;
- use tuples for graph nodes/edges and immutable mappings for stored metadata/payloads;
- make repositories store and return detached immutable snapshots;
- add nested-mutation tests, not only field-reassignment tests;
- prove post-storage mutation cannot change repository history.

## 3. Revision chain integrity and actor audit are incomplete

The repository only checks that a parent ID exists. It does not enforce that the parent belongs to the same case or that `child.revision_number == parent.revision_number + 1`.

`create_revision_from_parent()` copies `created_by` from the parent instead of accepting the actor creating the new revision. It also accepts caller-supplied `changed_fields`, so the audit record can omit or falsify changes.

Required:

- enforce same-case parentage and exact consecutive numbering in the repository;
- require `created_by` for every new revision;
- compute changed fields internally and never trust caller-supplied audit data;
- reject an identical child revision unless an explicit no-op revision policy is approved;
- verify the full parent chain during integrity checks.

## 4. Revision diff is not field-level

The current helper compares only top-level dictionary keys. `RevisionDiff` records only a tuple of field names and two hashes; it does not record stable nested paths, before values and after values.

Required:

- implement recursive diffs with paths such as `hot_stream.inlet_temperature`;
- include canonical before/after values;
- sort paths deterministically;
- handle additions, removals and nested list/tuple changes explicitly;
- add tests for multiple nested changes.

## 5. Unit-equivalent input hashing is not complete

Canonical quantity serialization records the current `value` and `unit`. The task card itself still lists `test_unit_equivalence_hash` as pending. TASK-004 requires physically equivalent inputs expressed in different display units to produce the same design content hash.

Required:

- hash quantities from canonical SI value and dimension/kind, not display representation;
- either exclude display unit from content identity or store it outside the engineering-content hash;
- add Celsius/Kelvin, bar/Pa, mm/m and mass-flow equivalence tests;
- document the rule in `DESIGN_CASE_REVISIONS.md`.

## 6. CalculationRun invariants are not enforced by the model

The model permits invalid terminal records. Tests explicitly demonstrate that `FAILED` can be constructed without `failure`. `BLOCKED` can be created without blockers, and `SUCCEEDED` can retain the zero placeholder result hash. `completed_at` ordering is only checked later by `verify_run_integrity()`.

`model_copy(update=...)` does not provide a reliable validation boundary, and `schema_version` and hash fields are unconstrained strings.

Required:

- enforce status-dependent invariants with model validation;
- use `result_hash: str | None = None`, not a zero sentinel;
- validate `sha256:<64 hex>` format;
- require failure/blockers/result hash for the applicable terminal states;
- reject terminal records with missing or contradictory fields at construction/deserialization;
- use `Literal["1.0"]` for schema versions.

## 7. Run repository updates can alter immutable identity fields

`InMemoryCalculationRunRepository.update()` checks only the status transition. A replacement record may also change `case_id`, `case_revision_id`, `run_type`, `input_hash`, `git_commit`, `software_version` or `started_at`.

The transition table is duplicated in both domain and repository modules, creating drift risk.

Required:

- centralize the transition policy;
- reject changes to immutable run identity and input fields;
- enforce run-model integrity before storage;
- ensure `add()` only accepts a valid initial PENDING record;
- add tests attempting to change revision ID, input hash and run type during a transition.

## 8. Provenance graph does not yet satisfy traceability requirements

The graph allows an empty graph, has no RESULT node type, does not require a result node for successful runs, and provenance nodes do not carry a `payload_hash`. Graph hash also depends on insertion order because nodes and edges are stored as lists without canonical graph ordering.

Required:

- add explicit `INTERMEDIATE`, `RESULT`, `WARNING` and `BLOCKER` node types or an equivalent approved model;
- include payload hash on every traceable node;
- require a CASE_REVISION node for every persisted run graph;
- require at least one RESULT node for a successful run;
- canonicalize node/edge ordering before serialization and hashing;
- validate blocker lineage to an input or calculation node;
- add same-graph/different-insertion-order hash tests.

## 9. Engineering-message semantics are under-constrained

The severity enum has no `BLOCKER` value and uses `CRITICAL` instead. There is no rule connecting severity to `allows_continuation`; a critical message may allow continuation and a warning may block it. `code` accepts any arbitrary string despite the stable-code policy.

Required:

- define an explicit blocker severity or formally map blocker semantics;
- validate continuation behavior by severity/category;
- use a controlled code enum/registry while retaining an extension mechanism if needed;
- deep-freeze context;
- add invalid semantic-combination tests.

## 10. Task record is not synchronized with the implementation

The task card still marks CI pending and lists three pending tests, including unit-equivalence hashing. Several referenced test paths do not match the actual files.

Required:

- complete the pending acceptance tests;
- update the task card with the actual 327-test count and CI run;
- keep status `IN_PROGRESS` and PR #9 Draft until this review is resolved.

## Approval gate

After correction:

1. rerun Ruff, mypy, pytest and pip-audit on Python 3.11 and 3.12;
2. demonstrate deep immutability and detached repository snapshots;
3. demonstrate ordered canonical serialization and SI-equivalent hashing;
4. demonstrate enforced revision-chain and run-state invariants;
5. demonstrate canonical, payload-hashed provenance DAGs with successful-run result nodes;
6. update documentation and task records.

Do not add PostgreSQL, FastAPI persistence, heat-balance equations, correlations, sizing/rating or TASK-005 scope in this PR.
