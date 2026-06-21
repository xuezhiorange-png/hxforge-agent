# TASK-001 Engineering Review — Round 3

**PR:** #2  
**Decision:** CHANGES REQUIRED  
**CI:** Latest Python 3.11 and 3.12 quality jobs passed.

The Round 2 revision resolves most prior findings. TASK-001 is still not approved because the following contract issues remain and affect downstream schemas.

## 1. Tighten `requires_review`

Current logic allows `requires_review = false` when `verification_level = BENCHMARK_VALIDATED` and no warnings are open. That is too permissive for engineering use.

Required revision:

- `requires_review = false` only when:
  - `verification_level = ENGINEERING_APPROVED`;
  - no open warnings;
  - no blockers;
  - no unresolved assumptions or deviations.
- `BENCHMARK_VALIDATED` still requires project-specific engineering review.
- Update DEC-006, PRODUCT_REQUIREMENTS, INPUT_OUTPUT_DICTIONARY, WORKFLOW_MATRIX and baseline cases consistently.

## 2. Resolve DEC-017 enum mismatch

DEC-017 allows the following `source_type` values:

- `STANDARD`
- `VENDOR`
- `USER`
- `ASSUMED`

Baseline cases currently use `PLACEHOLDER`, which is not defined in the contract.

Required revision:

- Either add a documented reference-verification status/field while keeping `source_type` valid;
- Or replace `PLACEHOLDER` with a valid `source_type` and explicitly mark the reference as unverified in a separate field.

Recommended structure:

```yaml
source_type: STANDARD
reference_id: TEMA-RGP-T-2.4
edition: TBD
table_or_clause: TBD
verification_status: UNVERIFIED_REFERENCE
note: Placeholder reference pending licensed rule-pack verification
```

Do not introduce an enum value in examples that is absent from the schema.

## 3. Make CASE-005 representable by the public I/O contract

CASE-005 uses `inlet_quality`, but the current public I/O dictionary does not define vapor quality, enthalpy-based state specification or a state-specification union.

Required revision:

Add a documentation-level versioned state specification, for example:

- `TP`: temperature + pressure;
- `PH`: pressure + specific enthalpy;
- `PQ`: pressure + vapor quality.

Suggested shape:

```yaml
state_spec:
  schema_version: "1.0"
  type: PQ
  pressure: {value: 300000, unit: Pa}
  quality: 0.3
```

The two-phase service must still return `NOT_IMPLEMENTED`, but its request must be validly representable before capability evaluation.

## 4. Separate deterministic calculation identity from mutable approval metadata

The current result hash includes `verification_level`. `ENGINEERING_APPROVED` is a mutable human-review outcome and must not change the identity of the underlying deterministic calculation.

Required revision:

Define two distinct hashes:

### `calculation_hash`

Include only deterministic calculation identity:

- input schema version;
- case/input revision;
- resolved SI inputs;
- deterministic outputs;
- geometry/catalog revision;
- correlation IDs and versions;
- property backend and version;
- software version and Git commit;
- structured warning/blocker codes and deterministic context.

Exclude:

- approval state;
- reviewer identity;
- review timestamps;
- signatures;
- mutable comments;
- random run IDs.

### `audit_record_hash`

Optionally protect the immutable review/audit record, including approval state, reviewer identity and timestamps.

Update terminology in INPUT_OUTPUT_DICTIONARY and provenance documentation.

## 5. Correct the DEC-014 temperature scaling example

The current example uses:

```text
scaling_quantity = |T_in| + 273.15
```

This is ambiguous or wrong after inputs have already been normalized to kelvin.

Required revision:

- Use an absolute-temperature scaling quantity already expressed in kelvin;
- Or define another explicit solver-specific scale;
- Do not add 273.15 to a value that is already SI-normalized.

Example:

```text
scaling_quantity = max(|T_in_K|, |T_out_K|, 1 K)
```

## 6. Add catalog provenance to CASE-002 geometry

CASE-002 currently states nominal size, Schedule and dimensions directly in the case. Those values must be resolved from a versioned geometry catalog rather than asserted manually.

Required revision:

Add at least:

- `catalog_id`;
- `catalog_revision`;
- `catalog_source`;
- inner-tube material;
- outer-tube material;
- side-specific roughness values;
- roughness source/provenance;
- geometry entry ID.

The case dimensions must reconcile with the referenced catalog entry.

## Final approval gate

After these corrections:

1. rerun CI on Python 3.11 and 3.12;
2. report the final five-case representation review;
3. confirm all example values conform to declared enums and schemas;
4. confirm DEC-005 and DEC-006 are ready for owner approval;
5. keep PR #2 as Draft until owner approval is explicitly recorded.

## Current decision state

- DEC-005: technically ready for owner approval.
- DEC-006: pending correction to `requires_review`.
- TASK-001: remains `IN_PROGRESS`.
- TASK-002: remains blocked until DEC-005 and stable quantity/result contracts are approved.

No unit-system, property, heat-balance or exchanger calculation code should be added in this PR.
