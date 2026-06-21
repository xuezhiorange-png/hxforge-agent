# TASK-005 Engineering Review — Round 1

**PR:** #11  
**Head reviewed:** `83516e673b008c053cd339d8cdde6ab494ab702a`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27920641271` / run #89 failed.

The overall module split and fixture-only scope are appropriate, but the current implementation does not yet satisfy the registry, applicability, determinism, or repository-wide quality contracts.

## 1. Repository-wide quality gate is failing

The Python 3.12 job fails in the repository-level mypy step:

```text
src/hexagent/properties/base.py:87: error: Argument "name" to "FluidIdentifier" has incompatible type "FluidIdentifier | str"; expected "str"  [arg-type]
Found 1 error in 1 file (checked 28 source files)
```

Because mypy failed, pytest and pip-audit did not run in CI. The reported local result only covered the seven new source files and is not the project quality gate.

Required:

- fix the typing error without `# type: ignore`;
- run repository-level `mypy`, not only `mypy src/hexagent/correlations`;
- require both Python 3.11 and 3.12 jobs to complete successfully;
- do not claim pytest or pip-audit CI success until those steps actually execute.

## 2. Semantic-version validation and ordering are inconsistent

`CorrelationKey` uses a prefix regex, so malformed values such as `1.0.0junk` can pass model validation, while `_parse_version()` later rejects them. Registry ordering also places stable before prerelease for the same core version in ascending order and compares prerelease identifiers lexically rather than by SemVer precedence.

Required:

- use one strict, fully anchored SemVer parser for model validation and registry ordering;
- reject leading/trailing junk and incomplete versions;
- implement SemVer prerelease precedence, including numeric identifiers;
- define deterministic behavior for build metadata;
- add tests for `1.0.0-alpha.1`, `1.0.0-alpha.2`, `1.0.0-alpha.10`, `1.0.0`, malformed suffixes, and build metadata.

## 3. Envelope and definition invariants are missing

`ApplicabilityEnvelope` has no validator enforcing:

- unique bound variables;
- every bounded variable being present in `required_inputs`;
- `recommended_minimum <= recommended_maximum`;
- a bounded maximum for `tolerance_fraction`;
- canonical bound ordering.

`CorrelationDefinition.geometry` and `.phase_regimes` can also disagree with the envelope equivalents.

Required:

- reject duplicate `NumericBound.variable` entries;
- require all bounded variables as inputs, unless an explicit optional-bound contract is designed and tested;
- validate recommended min/max against one another and absolute bounds;
- define and validate a conservative tolerance limit;
- normalize bounds by variable for canonical hashing;
- require definition geometry and phase sets to equal the envelope sets;
- define `generic` wildcard semantics explicitly and test them.

## 4. Out-of-range policy does not control the result

The implementation currently derives overall status primarily from `allow_extrapolation`, while message severity is handled separately. This creates contradictory states:

- default recommended-range warnings result in `allows_evaluation=False`;
- `absolute_violation=warn` produces a warning but still disallows evaluation;
- `allow_extrapolation=True` permits absolute extrapolation even when the definition policy is `block`;
- missing input is hardcoded to `block`, ignoring `policy.missing_input`;
- a missing non-required bounded variable can produce an `applicable` status while also generating a blocker;
- `tolerance_fraction` is not used.

Required:

- make `OutOfRangePolicy` the sole authority for continuation semantics;
- allow default recommended-range warnings to continue;
- only allow explicit extrapolation when the policy is `allow_explicit_opt_in` and the caller opts in;
- keep `block` blocked even when the caller sets `allow_extrapolation=True`;
- implement `fallback_required` as a non-continuable structured result;
- apply the configured missing-input policy;
- remove contradictory combinations of status, blockers, and `allows_evaluation`;
- apply or remove `tolerance_fraction`;
- add a policy × violation decision-table test suite.

## 5. Input and result models are not deeply immutable or self-validating

`CorrelationApplicabilityInput.values` is a mutable dict inside a frozen model. Supplied values are not checked for NaN or infinity. `ApplicabilityAssessment` permits empty hashes and caller-supplied inconsistent combinations such as `status=applicable`, blockers present, and `allows_evaluation=True`.

Required:

- replace mutable input dict storage with a canonical immutable representation, while retaining ergonomic construction;
- reject duplicate variables, NaN, and infinity;
- derive `allows_evaluation` rather than accepting an independent caller value;
- validate assessment hashes as `sha256:<64 lowercase hex>`;
- enforce warning/blocker/status consistency at model construction and JSON round trip;
- add nested mutation and invalid-construction tests.

## 6. Definition and assessment hash contracts are incomplete

`CorrelationDefinition.definition_hash` defaults to an empty string, and the registry skips verification when it is empty. Therefore unidentifiable definitions can be registered.

The assessment hash omits material identity and decision inputs, including the definition hash, geometry, phase, flow regime, policy, range values, extrapolation request, warnings, and blockers. Two materially different assessments can therefore share a hash.

Required:

- make `definition_hash` mandatory and format-validated;
- provide one canonical helper that computes a definition hash excluding only the hash field itself;
- always recompute and verify it during registration;
- include `definition_hash` and the complete canonical applicability input and output in `assessment_hash`;
- prove semantically identical set/bound orderings hash identically;
- prove material definition, policy, input, or range changes alter the hash.

## 7. Registry lifecycle and error contracts need consolidation

The module defines `CorrelationErrorCode` while also adding the same codes to the global `ErrorCode`, creating two authorities. Exact-version lookup raises the generic not-found error rather than the existing version-not-found error.

The registry also allows definitions marked `implemented` or `validated` without an implementation reference or adequately verified source.

Required:

- use one stable error-code authority across HXForge;
- return `correlation_version_not_found` for a missing version of an existing ID;
- preserve immutable structured error context;
- require `implementation_ref` for `implemented` and `validated` definitions;
- require an approved source-verification level before `validated` status;
- reject self-supersession and define whether `supersedes` must already exist and share the same correlation ID;
- define whether default search excludes deprecated and withdrawn definitions, then test the safety policy.

## 8. Usage records and provenance conversion are not deterministic enough

`CorrelationUsageRecord.input_values` uses arbitrary strings rather than `ApplicabilityVariable`, is not normalized, permits duplicates through tuple input, and does not validate finite values or hashes. `source_id` is used as a run-like identifier in tests although the contract identifies the bibliographic source.

`to_provenance_node()` calls `uuid4()` internally, so identical usage records produce different provenance nodes. The payload hash also omits uncertainty, and provenance metadata omits the definition and assessment hashes.

Required:

- type input variables as `ApplicabilityVariable`;
- sort and de-duplicate input values and reject NaN/infinity;
- validate definition and assessment hash formats;
- enforce consistency between `explicit_extrapolation` and `extrapolation_used`;
- clarify `source_id` as the bibliographic source ID and test it against the definition;
- expose a stable `usage_hash` over the complete record, including uncertainty;
- inject `node_id` or derive a deterministic UUID from the usage hash; do not call `uuid4()` internally;
- include definition hash, assessment hash, usage hash, source ID, applicability status, and extrapolation state in provenance metadata;
- replace the test that requires different node IDs with deterministic/reproducible provenance tests.

## 9. Fixture and documentation accuracy

Tests should use clearly fictional source titles and uncertainty bases rather than real correlation names with fabricated bibliographic details. The task card head SHA is stale (`408293e` instead of the reviewed head), and CI is recorded as successful even though run #89 failed before pytest and pip-audit.

Required:

- rename all fixture-only bibliographic data to unmistakably fictional values;
- update the task card and PR body with the actual head, repository-wide mypy scope, CI run, and true executed gate results;
- keep TASK-005 `IN_PROGRESS` and PR #11 Draft until all review items close.

## Approval gate

Before the next review:

1. repository-level Ruff and format checks pass;
2. repository-level mypy passes on Python 3.11 and 3.12;
3. all existing and new tests pass in CI;
4. pip-audit executes and passes;
5. policy decision-table, hash identity, deep immutability, SemVer, registry lifecycle, and deterministic provenance tests are present;
6. no actual engineering formula, database, API, heat-balance, sizing/rating, or TASK-006 scope is added.
