# TASK-003 Engineering Review — Round 4

**PR:** #7  
**Head reviewed:** `77de9bdbb0b7f8d9b6ed2030b7237192aee4aef7`  
**Decision:** CHANGES REQUIRED  
**CI:** Python 3.11 and 3.12 quality jobs passed.

Review-03 is substantially resolved. The DEF baseline guard, process-level atomic lock, FluidSpec adapter, fixture matching, strict state serialization and mixture rejection are acceptable. Four concrete contract gaps remain.

## 1. `PHStateSpec.reference_state` is still optional in the public schema

The field is declared as:

```python
reference_state: ReferenceStatePolicy = ReferenceStatePolicy.DEF
```

This gives it a default and means public JSON can omit the reference-state identifier, contrary to the requirement that the enthalpy convention be explicit.

Required revision:

- remove the default so `reference_state` is schema-required;
- assert that `PHStateSpec.model_json_schema()["required"]` contains `reference_state`;
- add model and API validation tests showing omission is rejected;
- keep `to_provider_args()` as the deterministic adapter.

## 2. Error serialization version is not literal and uses a mutable default

`PropertyServiceErrorModel.schema_version` is still a free `str`, not `Literal["1.0"]`. Its `context` field uses `{}` directly rather than a default factory.

Required revision:

- declare `schema_version: Literal["1.0"] = "1.0"`;
- use `Field(default_factory=dict)` for `context`;
- test rejection of schema version `2.0`;
- prove canonical JSON equality after `PropertyServiceError -> JSON -> PropertyServiceError -> JSON`.

## 3. Ordinary Tier-1 provenance does not record its validation basis

Fixture matches correctly record dataset ID, revision and `backend_regression`. However non-matching Tier-1 states currently return `validation_basis=None`. The approved contract requires the support claim itself to remain traceable.

Required revision:

- for ordinary Tier-1 states, set `validation_basis="support_allowlist"` with no dataset ID;
- for fixture matches, retain `validation_basis="backend_regression"` and populate dataset ID/revision;
- for explicitly allowed unvalidated pure fluids, set an explicit basis such as `unvalidated_opt_in`;
- add exact tests for all three cases;
- keep `validation_level=SUPPORTED_TIER_1` for both support-allowlist and backend-regression cases; do not upgrade to benchmark validation.

## 4. General backend error classification still depends on English message tokens

`_classify_backend_error()` still searches CoolProp exception strings such as `out of range`, `triple` and `critical`. The current test named `different_messages_same_code` does not inject different messages; it performs only one real query and repeats the same assertion.

Required revision:

- remove message-token classification from the public error-code decision path;
- perform explicit input-domain prechecks for boundary cases that HXForge promises to classify, including TP temperature/pressure limits and saturation critical limits;
- after explicit prechecks, classify an unexpected CoolProp exception as `property_backend_failure` regardless of its message text;
- replace the current test with monkeypatched backend exceptions carrying different messages and assert the same `BACKEND_FAILURE` code;
- use an explicit TP below-minimum-temperature test for `STATE_OUT_OF_RANGE` rather than inferring PH enthalpy range from an English backend error.

## Records

After the four corrections pass CI:

- mark Round-03 findings resolved;
- update `docs/PROPERTY_BACKENDS.md` so PH reference state is described as schema-required;
- update TASK-003 task card with the latest CI and final test count;
- update PR #7 description with the final validation-basis and error-classification policies;
- keep PR #7 Draft until final engineering approval is recorded.

No heat balance, exchanger correlations, geometry selection, costing, mechanical design or downstream two-phase solvers may be added in this PR.
