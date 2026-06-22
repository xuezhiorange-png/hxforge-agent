# TASK-005 Engineering Review — Round 3

**PR:** #11  
**Head reviewed:** `d263e8819bc70d0f6f66ba4350b31517f8d300e7`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27922547742` / run #94 passed.

Review-02 resolved the matrix CI failure and improved SemVer and policy handling, but five blocking contracts remain.

## 1. SemVer core-version leading zeros are still accepted

Numeric prerelease identifiers now reject leading zeros, but the core version regex still accepts values such as `01.0.0`, `1.01.0`, and `1.0.01`. Strict SemVer forbids leading zeros in major, minor, and patch identifiers except the literal `0`.

Required:

- use the same strict parser for model validation and registry ordering;
- reject leading zeros in major, minor, and patch;
- add direct model and registry ordering tests for invalid core identifiers.

## 2. `allow_explicit_opt_in` remains inconsistent for missing input and incompatible geometry/phase/flow

Boundary values correctly distinguish opt-in present vs absent. The incompatibility and missing-input branches do not:

- `missing_input=allow_explicit_opt_in` always produces a WARNING, even without opt-in;
- geometry, phase, and flow `allow_explicit_opt_in` always produce WARNING;
- `_policy_allows_evaluation()` does not support opt-in continuation for geometry, phase, flow, or missing input;
- `ApplicabilityAssessment` then overwrites `allows_evaluation` from the absence of blockers, silently turning those cases into continuable assessments.

Required:

- centralize action-to-severity-and-continuation logic in one helper;
- for `allow_explicit_opt_in`, use BLOCKER without opt-in and WARNING only with explicit opt-in;
- apply the same rule to absolute range, recommended range, missing input, geometry, phase, and flow;
- add decision-table tests for every action × violation × opt-in combination;
- prove no assessment can contain warnings-only while policy says evaluation is blocked.

## 3. Assessment construction and identity are still open

`ApplicabilityAssessment` still exposes caller-settable `allows_evaluation` and `assessment_hash`, defaults the hash to an empty string, and silently overwrites continuation instead of rejecting inconsistent public construction.

The assessment hash still omits material input identity:

- geometry;
- phase regime;
- flow regime;
- extra supplied values not represented by a bound;
- complete variable range metadata;
- geometry/phase/flow policy fields;
- full structured warning/blocker context.

Required:

- create assessments through one factory/internal constructor that derives continuation and hash;
- reject empty or invalid assessment hashes for returned/persisted assessments;
- include the complete canonical `CorrelationApplicabilityInput` and complete structured decision output in the hash;
- add collision tests proving each material input or policy change alters the hash;
- add tests proving direct inconsistent construction is rejected rather than silently corrected.

## 4. Definition identity is still only partially enforced

The registry rejects empty hashes, but `CorrelationDefinition` remains publicly constructible with an empty or arbitrary unvalidated `definition_hash`. `CorrelationDefinition.create()` temporarily constructs a model with the literal `"temp"` and uses `model_copy(update=...)`, which bypasses normal field validation.

Required:

- validate non-empty definition hashes as `sha256:<64 lowercase hex>`;
- make the public construction path explicit: either require a valid hash or expose a validated factory and make raw identityless construction internal-only;
- do not rely on `model_copy(update=...)` to install an unvalidated identity;
- add direct-construction, factory, tamper, JSON round-trip, and registry-boundary tests.

## 5. Usage, source, provenance, and supersession contracts are not closed

`CorrelationUsageRecord` was not changed in this round. Remaining issues:

- `usage_hash` omits `UncertaintySpec.source_id`;
- extrapolation consistency is only one-way;
- usage `source_id`, key, definition hash, and assessment hash are not cross-validated against a definition and assessment;
- deterministic node IDs are generated from raw truncated hash bytes without an explicit namespace/domain-separation contract;
- provenance metadata omits uncertainty source ID;
- registry registration still performs no `supersedes` existence or same-correlation-ID check.

Required:

- include the complete uncertainty model in `usage_hash`;
- require `extrapolation_used=True` if and only if status is `explicit_extrapolation`;
- create usage records through a factory accepting the registered definition and applicability assessment;
- cross-check key, definition hash, source ID, assessment hash, applicability status, and extrapolation state;
- use an injected node ID or namespaced deterministic UUID with a documented domain separator;
- include uncertainty source ID in provenance metadata;
- require `supersedes` to exist, share the same correlation ID, and be an earlier version at registration time.

## 6. Records remain stale

The PR body and task card still report head `94cb09d` and 626 tests while the reviewed head is `d263e88` and the reported local count is 632. Records must be updated only after the final corrected head is green.

## Approval gate

Before Round 4:

1. keep both Python 3.11 and 3.12 CI jobs green;
2. close strict SemVer core validation;
3. prove all policy/opt-in combinations have consistent messages and continuation;
4. make definition and assessment identities complete and validated;
5. cross-validate usage/source/provenance/supersession contracts;
6. update PR body and task card with actual final head, test count, and CI run;
7. do not add real formulas, database, API, heat balance, sizing/rating, or TASK-006 scope.
