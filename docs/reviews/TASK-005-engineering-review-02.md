# TASK-005 Engineering Review — Round 2

**PR:** #11  
**Head reviewed:** `36f2dbfb5e356f0b7e712fbc4381693872d91737`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27921555231` / run #92 failed.

Review-01 materially improved the correlation domain, but six blocking contracts remain.

## 1. Python 3.12 repository-wide mypy still fails

The current CI failure is unchanged:

```text
src/hexagent/properties/base.py:87: error: Argument "name" to "FluidIdentifier" has incompatible type "FluidIdentifier | str"; expected "str"  [arg-type]
Found 1 error in 1 file (checked 28 source files)
```

The report only confirms Python 3.11 locally. The project gate requires both Python 3.11 and 3.12. Because mypy failed, pytest and pip-audit did not execute in CI.

Required:

- narrow the `FluidSpec.name` / `FluidIdentifier | str` union explicitly before passing it as `name`;
- do not use `# type: ignore` or an unsafe cast that bypasses runtime semantics;
- require both matrix jobs to reach pytest and pip-audit.

## 2. SemVer ordering still breaks for mixed numeric/alphanumeric identifiers

The version sort key stores prerelease identifiers as `tuple[int | str, ...]`. Python cannot order an `int` against a `str`, so sorting versions such as `1.0.0-1` and `1.0.0-alpha` can raise `TypeError` even though SemVer defines numeric identifiers as lower precedence than alphanumeric identifiers.

The parser also accepts leading zeros in core and numeric prerelease identifiers, which strict SemVer forbids.

Required:

- encode each prerelease identifier as a typed sortable token, e.g. `(0, integer)` for numeric and `(1, string)` for alphanumeric;
- reject leading zeros except the literal `0`;
- keep the documented build-metadata policy consistent across parser, model and tests;
- add mixed numeric/alphanumeric ordering tests, not only `alpha.1`, `alpha.2`, `alpha.10`.

## 3. Policy-controlled incompatibility still produces contradictory results

`_policy_allows_evaluation()` permits `incompatible_geometry` or `incompatible_phase` to continue when the corresponding policy is `warn`. However the generated messages are still hardcoded as `BLOCKER`. This yields blockers together with `allows_evaluation=True`, which the assessment model rejects at runtime.

Additional gaps:

- `missing_input=allow_explicit_opt_in` is represented as a warning but cannot be enabled by caller opt-in;
- flow-regime incompatibility is hardcoded blocked and has no explicit documented policy contract;
- `allow_explicit_opt_in` without opt-in can produce a warning while still blocking, conflicting with the global message continuation semantics.

Required:

- generate incompatibility message severity from the same policy used to derive continuation;
- define an explicit policy for flow-regime incompatibility, or document it as an unconditional blocker and remove claims that all continuation is policy-driven;
- define opt-in-required messages as non-continuable until opt-in is present;
- add direct tests for geometry warn, phase warn, missing-input opt-in, flow incompatibility and fallback-required paths;
- prove every assessment satisfies `bool(blockers) == (not allows_evaluation)` unless a separately documented nonblocking error class exists.

## 4. Hashes and assessment identity remain optional/incomplete

`CorrelationDefinition.definition_hash` still defaults to an empty string. The registry silently computes and inserts a hash instead of rejecting an unidentified definition. This contradicts the claimed mandatory hash contract and makes the object supplied by the caller differ from the persisted object.

`ApplicabilityAssessment.assessment_hash` also defaults to empty and accepts empty values.

The assessment hash does not include the full applicability input. Geometry, phase, flow regime and extra supplied variables can change without necessarily changing the hash. It also stores only warning/blocker code and severity, not full structured context.

Required:

- make `definition_hash` mandatory and format-validated at model construction, or provide a single explicit factory that always returns a fully identified definition before registration;
- reject empty definition hashes at registry boundaries;
- make `assessment_hash` mandatory for persisted/returned assessments;
- include complete canonical input identity: geometry, phase, flow regime, all supplied values and extrapolation request;
- include complete structured decision output or a canonical hash of warnings/blockers;
- add collision-oriented tests showing each material input change alters the assessment hash.

## 5. Assessment consistency is not fully model-enforced

`allows_evaluation` remains a caller-set field. The model validator only rejects blockers with `allows_evaluation=True` and blockers on `applicable`; it still accepts inconsistent constructions such as:

- `status=applicable`, no blockers, `allows_evaluation=False`;
- non-applicable blocking status, no blockers, `allows_evaluation=True`;
- warning-only status with arbitrary continuation value;
- empty `assessment_hash`.

Required:

- derive `allows_evaluation` from structured decision data rather than accepting an independent public value;
- enforce status/message/continuation consistency for every status;
- reject direct construction of incomplete assessments, or expose a private/internal construction path used only by the engine;
- test invalid direct construction and JSON round trip.

## 6. Usage/provenance lifecycle is still under-constrained

The usage record is now deterministic, but:

- `usage_hash` omits `UncertaintySpec.source_id`;
- consistency is one-way: explicit extrapolation requires `extrapolation_used=True`, but `extrapolation_used=True` is still accepted for non-extrapolated statuses;
- `source_id` is not checked against the registered definition source;
- raw UUID creation from the first 128 hash bits is deterministic but does not use a namespaced UUID scheme or document collision/domain separation.

Registry lifecycle also remains incomplete:

- `supersedes` is only checked against exact self-reference;
- the registry does not require the superseded key to exist or share the same correlation ID.

Required:

- include the complete uncertainty object, including `source_id`, in `usage_hash`;
- enforce extrapolation consistency in both directions;
- construct usage records through a factory accepting the definition and assessment so source ID, key and hashes can be cross-validated;
- use an injected node ID or namespaced deterministic UUID derived from a domain-separated usage hash;
- define and enforce supersession rules at registration time.

## 7. Records are stale

The PR body and task card report head `94cb09d`, while the reviewed remote head is `36f2dbf`. The task card marks all Review-01 items complete even though CI run #92 fails before pytest and pip-audit.

Required:

- update the PR body and task card only after the corrected head has completed both matrix jobs;
- report actual executed CI gates, not local-only results;
- keep TASK-005 `IN_PROGRESS` and PR #11 Draft.

## Approval gate

Before Round 3:

1. both Python 3.11 and 3.12 CI jobs pass repository-wide mypy;
2. pytest and pip-audit execute and pass in both jobs;
3. mixed-type SemVer ordering is correct and fully tested;
4. policy, messages and continuation cannot contradict;
5. definition and assessment identities are mandatory and complete;
6. usage/source/supersession contracts are cross-validated;
7. no actual formulas, database, API, heat balance, sizing/rating or TASK-006 scope is added.
