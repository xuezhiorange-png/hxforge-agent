# TASK-004 Engineering Review — Round 2

**PR:** #9  
**Head reviewed:** `0941d1b1e1a54c973db01c1fa65a40cc29c97de6`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27909358908` passed on the reviewed head.

Round 1 is partially resolved, but several core contracts remain bypassable. Passing tests do not close these gaps because the current tests assert weaker behavior than the approved requirements.

## 1. Domain models are still only shallowly immutable

`DesignCaseRevision` remains a frozen dataclass containing mutable `canonical_payload: dict[str, Any]`. `RevisionDiff.field_changes` remains `tuple[dict[str, Any], ...]`. These nested dictionaries can be mutated after construction, invalidating hashes and audit records without assigning to a frozen field.

`ProvenanceNode.metadata`, `ProvenanceEdge.metadata`, `EngineeringMessage.context` and `RunFailure.context` use tuples, but their `Any` values may still contain mutable dictionaries/lists. A tuple containing a mutable object is not deeply immutable.

Required:

- convert canonical payloads and diff entries to recursively immutable structures, or expose only detached canonical snapshots and never retain caller-owned mutable containers;
- recursively freeze metadata/context values, not only the outer collection;
- add tests that actually mutate nested dictionaries/lists and prove mutation is rejected or cannot alter the object/hash;
- verify JSON round trips reconstruct the same immutable representation.

## 2. Revision repository does not enforce the claimed chain invariants

`InMemoryDesignCaseRevisionRepository.add()` currently checks duplicate IDs, revision-number conflicts and parent existence only. It does not check that the parent belongs to the same `case_id`, and it does not enforce `child.revision_number == parent.revision_number + 1`.

The service verifies these rules when it creates a normal child, but the repository is a public persistence boundary and must reject manually constructed invalid revisions too.

Required:

- enforce same-case parentage and exact consecutive numbering inside repository `add()`;
- reject a non-root revision whose parent is not the immediately preceding revision;
- add repository-level tests that bypass `RevisionService` and attempt cross-case and numbering-gap inserts;
- keep full-chain integrity verification in the service as a separate audit function.

## 3. Unit-equivalent hashing is not proven for actual DesignCase revisions

The new tests hash `Quantity` objects directly. However `RevisionService._canonical_payload()` first calls `case.model_dump()` and then only sorts dictionaries. At that point quantities have already become normal dictionaries containing their display `value` and `unit`, so the quantity-specific SI canonicalization path is bypassed.

Therefore the tests do not prove that two complete `DesignCase` objects expressed in equivalent units produce the same revision content hash.

Required:

- build revision payloads through the approved canonicalizer before model dumping destroys quantity type semantics, or add field-aware SI normalization of dumped quantity dictionaries;
- add end-to-end tests creating two complete DesignCase revisions with equivalent °C/K, bar/Pa, mm/m and kg/h/kg/s inputs and assert identical canonical payloads and hashes;
- remove the broad `contextlib.suppress(Exception)` fallback around SI conversion so conversion failures fail closed instead of silently hashing display values.

## 4. CalculationRun integrity remains under-constrained

`CalculationRun.input_hash` and `git_commit` still default to empty strings, and only `result_hash` is format-validated. A PENDING or RUNNING record with an empty input hash can be constructed and persisted.

`InMemoryCalculationRunRepository.add()` also accepts both PENDING and RUNNING, although Round 1 required a persisted run to begin as a valid PENDING record.

Required:

- require a valid `sha256:<64-hex>` input hash at model construction;
- define and validate the git-commit identity format or an explicit non-git sentinel policy;
- permit repository `add()` only for PENDING records;
- require transition to RUNNING through the centralized transition service/repository update path;
- add direct-construction and repository-bypass tests.

## 5. Provenance requirements are still optional

`ProvenanceNode.payload_hash` is optional, despite the requirement that every traceable node carry a payload hash. `ProvenanceGraph` still accepts an empty graph. A SUCCEEDED `CalculationRun` requires only `result_hash`; it does not require a RESULT node in its provenance graph.

Blocker lineage is not validated. The graph validates DAG structure and a CASE_REVISION node when nodes exist, but does not prove a BLOCKER traces back to an input/calculation node.

Required:

- make payload hash mandatory for every persisted provenance node and validate hash format;
- require every persisted run graph to contain CASE_REVISION and CALCULATION_RUN nodes;
- require at least one RESULT node for SUCCEEDED runs;
- validate WARNING/BLOCKER lineage to a case, input, property or calculation node;
- reject empty provenance graphs at the persistence boundary, while allowing a separate draft/builder type if needed;
- add tests for missing payload hash, succeeded-without-result-node, orphan blocker and empty persisted graph.

## 6. Tests and records overstate closure

The “deep immutability” tests currently check object identity and deep-copy return values but do not attempt nested mutation. Unit-equivalence tests cover isolated quantities rather than actual DesignCase revision hashes. Provenance tests explicitly accept empty graphs and construct nodes without payload hashes.

The PR body still says tuples are serialized as sorted arrays and reports 327 tests, while the task card reports tuple order preservation and 389 tests.

Required:

- strengthen tests to exercise the approved contracts, not only the implementation's current behavior;
- update the PR description to the actual canonical rules and current test count;
- leave TASK-004 `IN_PROGRESS` and PR #9 Draft until Round 2 is resolved.

## Approval gate

After correction:

1. rerun Ruff, mypy, pytest and pip-audit on Python 3.11 and 3.12;
2. demonstrate recursive immutability of revision, diff, message and provenance payloads;
3. demonstrate repository-level chain enforcement without using RevisionService;
4. demonstrate full DesignCase SI-equivalent hashes;
5. demonstrate valid PENDING-only run creation with required input identity;
6. demonstrate mandatory payload-hashed provenance and successful-run RESULT lineage;
7. synchronize the task card and PR description.

Do not add PostgreSQL, FastAPI persistence, heat-balance equations, correlations, sizing/rating or TASK-005 scope in this PR.
