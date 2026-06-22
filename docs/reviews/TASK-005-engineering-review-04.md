# TASK-005 Engineering Review — Round 4

**PR:** #11  
**Head reviewed:** `ad86dc57f171ebd97679979cd31cbcff12989dc1`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27923112093` / run #96 passed.

The implementation now has green CI and closes the SemVer-core and central policy-severity items. Four domain contracts remain open.

## 1. CorrelationDefinition identity can still be bypassed

`definition_hash` still defaults to an empty string and the field validator only validates non-empty values. Therefore callers can construct an identityless `CorrelationDefinition` directly. The factory itself creates such an identityless object first, then reconstructs it with a computed hash.

Required:

- make public `CorrelationDefinition` instances always carry a valid `sha256:<64 lowercase hex>` identity;
- separate an internal hash-input model/payload from the public identified definition, or implement a validated custom construction path that never exposes an identityless domain object;
- reject direct construction without a valid hash;
- keep registry recomputation and tamper detection;
- test direct construction, factory construction, JSON round trip, and tampering.

## 2. ApplicabilityAssessment remains publicly under-constrained

`allows_evaluation` and `assessment_hash` remain public caller-supplied fields with defaults. The validator silently overwrites `allows_evaluation` based on blockers instead of rejecting contradictory construction, and an empty assessment hash remains valid.

Required:

- make returned/persisted assessments always have a valid assessment hash;
- provide one engine/factory construction path that derives continuation and hash;
- reject direct inconsistent construction rather than silently correcting it;
- do not expose an arbitrary caller-settable continuation flag;
- add direct-construction and JSON-round-trip rejection tests.

## 3. Assessment hash still omits structured decision context

The hash now includes complete input identity and all six policy fields. Warning/blocker hashing includes only `(code, message, severity)`, while the domain message also contains `source_module`, structured `context`, and continuation semantics. Two decisions with different structured context can therefore share an assessment hash.

Variable results also omit the absolute and recommended range fields from the hash payload.

Required:

- hash the canonical full EngineeringMessage payload, including source module, context, severity/code, and continuation semantics;
- hash complete VariableAssessment payloads, including supplied value and all absolute/recommended limits;
- add collision tests for message-context and range-metadata changes.

## 4. Usage lifecycle and supersession ordering remain incomplete

`CorrelationUsageRecord` now includes uncertainty source ID and bidirectional extrapolation checks, but it is still independently constructible. There is no factory accepting a registered definition and assessment to cross-validate correlation key, definition hash, source ID, assessment hash, applicability status, inputs, and extrapolation state.

The provenance node ID is still produced by truncating the raw usage hash to 128 bits and constructing `UUID(...)`, without an explicit namespace/domain separator.

Supersession version ordering uses lexical string comparison:

```python
if key.version <= definition.supersedes.version:
```

This is incorrect for SemVer, e.g. `1.10.0` vs `1.9.0`.

Required:

- add a usage-record factory from `CorrelationDefinition + ApplicabilityAssessment + inputs` and cross-validate all identities;
- use an injected node ID or `uuid5` with a stable HXForge namespace and domain-separated usage hash;
- compare supersession versions using `parse_semver()` / the registry SemVer sort key, never lexical strings;
- require superseded key to exist and be strictly earlier under SemVer precedence;
- add tests for `1.9.0 → 1.10.0`, prerelease supersession, cross-ID rejection, missing target, and usage cross-validation.

## 5. Records remain stale

PR body and task card still report head `94cb09d` and 626 tests rather than the reviewed head `ad86dc5` and 666 tests. Update them only after the corrected final code head is green.

## Approval gate

Before final approval:

1. both Python matrix jobs remain green;
2. public definitions and assessments cannot exist without valid identities;
3. assessment hash covers complete structured inputs and outputs;
4. usage construction cross-validates definition and assessment;
5. provenance node identity is domain-separated and deterministic;
6. supersession uses true SemVer precedence;
7. PR body and task card match the final head, tests and CI run;
8. no real formulas, database, API, heat balance, sizing/rating, or TASK-006 scope is added.
