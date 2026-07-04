# TASK-011 — Benchmark Case Governance Design Contract

## 1. Status

```text
TASK-011: DESIGN CONTRACT (PRE-FREEZE REVISION)
Issue: #36
Implementation authorization: NOT GRANTED
Benchmark case implementation: NOT STARTED
Frozen contract SHA: NOT ESTABLISHED
Source evidence minimum: MANDATORY (Section 9)
Canonical hash algorithm: FROZEN (Section 17)
CI validation form: MANDATORY ACCEPTANCE CONTRACT (Section 19)
```

This document defines the freeze-ready design boundary for TASK-011. It is a
governance and schema contract for the first approved benchmark-case corpus.
It does not authorize adding benchmark data, production code, test code, CI
workflow changes, or solver features. Any "shall / must / required" clause in
this contract binds future TASK-011 implementation once the contract is
separately frozen and implementation is explicitly authorized. Until then,
every code-producing action remains NOT AUTHORIZED.

## 2. Objective

TASK-011 will collect, normalize, review and approve the first 20 benchmark
cases for the implemented HXForge v0.1 vertical slice.

A benchmark case is a governed, source-backed, machine-readable case
artifact used for later regression, validation, report traceability and
benchmark authority. It is NOT a hidden fixture, NOT an ad hoc example, and
NOT an unreviewed golden-output file.

## 3. Authority

Backlog authority:

```text
TASK-011 | Collect and approve the first 20 benchmark cases | DRAFT | TASK-001
```

Issue authority:

```text
Issue #36 — TASK-011 — Collect and approve the first 20 benchmark cases
```

Prerequisite governance already completed:

```text
TASK-010: DONE
TASK-015A: MERGED / CLOSED
PR #35: MERGED
Issue #33: CLOSED
TASK-011 implementation: NOT STARTED
```

## 4. Contract language convention

Every clause in Sections 5 through 22 uses the following language
discipline. This is binding for future freeze and implementation, not
optional editorial guidance.

| Phrase   | Meaning in this contract                                    |
|----------|-------------------------------------------------------------|
| MUST     | Required; case is rejected or contract is non-compliant otherwise. |
| REQUIRED | Synonym of MUST.                                            |
| SHALL    | Synonym of MUST.                                            |
| FORBIDDEN| Disallowed; case is rejected if present.                    |
| NOT AUTHORIZED | No action is permitted under this design contract.     |
| MAY      | Allowed but not required; cannot expand scope.              |

Draft / future-layout phrases ("proposed", "candidate", "should",
"eventual", "recommended", "may eventually") are removed from binding
sections. They are retained only in Sections 20 (future implementation
file boundary) and in labels that explicitly mark non-binding commentary.
They MUST NOT be used in Sections 5–19 or 22.

## 5. In-scope work for TASK-011 design

The design contract MUST specify:

1. Benchmark case identity model
2. Source classification and evidence requirements
3. Input schema
4. Expected output schema
5. Unit and SI normalization rules
6. Fluid and property-provider assumptions
7. Geometry assumptions
8. Boundary-condition assumptions
9. Numerical tolerance policy
10. Acceptance and rejection criteria
11. Source provenance model
12. Review and approval workflow
13. Canonical serialization rules
14. Hashing and integrity rules
15. Machine-readable manifest structure
16. Golden vs benchmark separation
17. CI validation expectations
18. Implementation authorization boundary

## 6. In-scope benchmark categories

The first 20 benchmark cases MUST be restricted to behavior already
implemented at the TASK-011 implementation baseline SHA recorded at
freeze time. A case MUST NOT be included if its required calculation path
does not already exist in the repository at that baseline. A benchmark
MUST NOT force new solver behavior.

Allowed categories:

1. Single-phase heat-balance closure
2. Tube-side correlation cases
3. Annulus-side correlation cases
4. Fixed-geometry double-pipe rating cases
5. Manufacturable sizing and selection-evaluation cases
6. API/report traceability cases already supported by TASK-010

## 7. Explicit non-goals

TASK-011 MUST NOT implement or require any of the following. Cases that
require any of these MUST be rejected at the source-evidence gate.

- Pressure-drop computation
- C4 / advanced constraint engine
- New heat-transfer correlations
- New equipment types
- Shell-and-tube logic
- Plate heat exchanger logic
- Air cooler logic
- Two-phase or refrigerant logic
- Cost model
- Materials database
- Mechanical design checks
- Persistent database / ORM
- Authentication / authorization
- Report rendering engine changes
- New API behavior beyond benchmark-case representation
- TASK-012 through TASK-019
- TASK-020+ shell-and-tube development

Any expected output that requires a non-implemented physics model
(including the items above) is FORBIDDEN in TASK-011 cases.

## 8. Benchmark case definition

One benchmark case is one independently reviewable scenario. Each case
MUST populate ALL of the following mandatory fields. A case is NOT
approved if any mandatory field is missing, empty, or marked unknown.

1. `case_id` — stable, unique, immutable identifier
2. `case_version` — changes whenever input, expected output, tolerance,
   or source evidence changes
3. `case_title` — human-readable title
4. `category` — value MUST be one of Section 6 allowed categories
5. `source_evidence` — populated per Section 9
6. `input_schema` — populated per Section 10
7. `expected_output_schema` — populated per Section 11
8. `unit_normalization` — populated per Section 12
9. `fluid_and_property_assumptions` — populated per Section 13
10. `geometry_and_boundary_assumptions` — populated per Section 13
11. `tolerance_justifications` — populated per Section 14
12. `review_workflow_state` — populated per Section 16
13. `canonical_hash` — populated per Section 17
14. `approval_status` — MUST be one of: draft, needs_source,
    needs_normalization, needs_expected_outputs, under_review, approved,
    rejected, superseded

A benchmark case is NOT approved until all mandatory fields are populated
and a reviewer sign-off is recorded.

## 9. Source classification and evidence minimum (P1-1)

Every benchmark case MUST record a `source_evidence` block. The block MUST
contain the following mandatory fields regardless of source class:

| Field                                          | Required | Notes |
|------------------------------------------------|----------|-------|
| `source_type`                                  | REQUIRED | One of the five allowed classes (Section 9.2). |
| `source_reference`                             | REQUIRED | Stable bibliographic identifier, URL, document ID, or repository-relative path. |
| `source_title_or_identifier`                   | REQUIRED | Human-readable title or unique identifier of the source. |
| `source_locator_or_citation`                   | REQUIRED | Page / section / equation / figure / table locator. |
| `source_version_or_publication_date`           | REQUIRED if available, otherwise MUST be marked `unavailable`. |
| `source_access_date`                           | REQUIRED if applicable (URL or web source), otherwise MUST be marked `n/a`. |
| `extracted_input_fields`                       | REQUIRED | Explicit mapping from source to case input fields, with original units. |
| `extracted_expected_output_fields`             | REQUIRED | Explicit mapping from source to case expected output fields, with original units. |
| `unit_provenance`                              | REQUIRED | Original unit of every extracted value before SI normalization. |
| `normalization_notes`                          | REQUIRED | Conversion factors and rounding rules applied during normalization. |
| `expected_output_origin`                       | REQUIRED | Whether expected output came from: published formula, table lookup, chart reading, internal review, or synthetic computation. |
| `evidence_limitations`                         | REQUIRED | Honest statement of source precision, missing fields, rounding caveats. |
| `reviewer_evidence_check_status`               | REQUIRED | One of: pending, accepted, accepted_with_caveats, rejected. MUST be set by the reviewer, not self-asserted. |

### 9.1 Mandatory rejection rules (Section 9 — source evidence)

The state transitions in this section are deterministic. Each trigger
MUST resolve to exactly one terminal or intermediate state. The
distinction between `needs_source` and `rejected` is encoded by the
**lifecycle stage** at which the trigger fires (see Section 9.3):

- `needs_source` is reachable ONLY from `draft` or other
  pre-approval states. It signals an evidence gap that the case
  author is expected to repair before re-submission.
- `rejected` is reachable from ANY lifecycle stage that touches
  approval, manifest inclusion, or CI acceptance. It is terminal
  for the current `case_version`; re-entry into the review pipeline
  requires a new `case_version`.

Mandatory rules:

- A case in `draft` (or any other pre-approval state) whose mandatory
  source-evidence fields are missing MUST transition to `needs_source`.
  It MUST NOT transition directly to `rejected` from `draft` for a
  missing-field defect alone.
- A case that attempts to enter `approved` while any mandatory
  source-evidence field is missing MUST be rejected.
- A case that is included in a manifest while any mandatory
  source-evidence field is missing MUST be rejected at the manifest
  validation gate (Section 19.1).
- A case whose canonical-hash recomputation (Section 17) reveals a
  missing mandatory source-evidence field at CI validation MUST be
  rejected at the CI acceptance gate (Section 19.1).
- A case whose `reviewer_evidence_check_status` is `pending` MUST NOT
  enter `approved`. It MUST remain in `under_review` until the
  reviewer check resolves.
- A case whose `reviewer_evidence_check_status` is `accepted_with_caveats`
  MUST NOT enter `approved`. It MUST transition to `under_review`
  if there is a reviewer follow-up, or to `needs_source` if the
  caveat identifies a missing or corrected evidence field. It MUST
  NOT be silently approved.
- A case whose `reviewer_evidence_check_status` is `rejected` MUST
  transition directly to `rejected` and MUST NOT be re-entered as
  `under_review` without a new reviewer sign-off and a new
  `case_version`.
- A case whose `reviewer_evidence_check_status` is `accepted` AND
  whose all other Section 16 approval gates pass is eligible to
  transition to `approved`.
- A `synthetic_regression_case` whose source evidence is missing or
  whose reviewer sign-off is missing MUST be rejected at the
  manifest or CI validation gate that first observes the defect,
  not silently transitioned to `needs_source`.
- A `synthetic_regression_case` is FORBIDDEN from being treated as
  `independent validation evidence`. The case file MUST contain an
  explicit `is_synthetic: true` marker, AND the manifest MUST list it
  under a `synthetic_case_ids` array.

### 9.2 Allowed source classes and minimum additional evidence

In addition to the universal mandatory fields, each source class
MUST satisfy the additional minimum evidence requirements listed below.
A case failing its class-specific minimum follows the deterministic
state-transition rules of Section 9.3 (lifecycle-stage aware): from a
pre-approval state it transitions to `needs_source`; from any
approval-, manifest-, or CI-touched stage it transitions to `rejected`.

#### 9.2.1 `published_reference`

- Peer-reviewed paper, standard, textbook chapter, or other publicly
  citable published reference.
- MUST provide: full bibliographic citation, DOI or stable URL where
  applicable, page / equation / table locator.
- MUST declare the precision / uncertainty bounds stated by the source.

#### 9.2.2 `vendor_example`

- Vendor catalog example, vendor-supplied worked example, or vendor
  software output trace.
- MUST provide: vendor name, document / software version, locator.
- MUST declare: whether the example is public or under license, and the
  license boundary that allows redistribution.

#### 9.2.3 `engineering_handbook_example`

- Recognized engineering handbook example (e.g. Perry's, Kern, Heat
  Exchanger Design Handbook).
- MUST provide: handbook edition, chapter / page / equation locator.
- MUST declare: edition revision date.

#### 9.2.4 `internal_reviewed_case`

- Case originating inside the project or its licensed collaborators,
  reviewed by an authorized engineer.
- MUST provide: author identity, review thread reference (Issue / PR /
  review ID), date of review.
- MUST declare: scope of internal review (only this case, or family).

#### 9.2.5 `synthetic_regression_case`

- Case generated to exercise an already-implemented deterministic path.
- MUST be explicitly labeled with `is_synthetic: true` in the case file
  AND listed in the manifest's `synthetic_case_ids` array.
- MUST record in `expected_output_origin` that the expected output was
  computed by the same code path being exercised (round-trip or
  regression-only).
- MUST NOT be cited as independent validation evidence.
- MUST NOT be the only kind of case used to claim TASK-011 corpus
  validation; the corpus MUST contain non-synthetic cases for any
  validation claim.

### 9.3 State transitions triggered by source evidence

The transition table below is the binding authority for any
implementation. Each row encodes exactly one `(lifecycle_stage,
condition)` pair and resolves to exactly one target state.
Implementation MUST encode the table verbatim; no alternative
grouping of conditions into states is permitted.

The lifecycle stages used in the condition column are:

- `pre_approval` — the case is in `draft`, `needs_source`,
  `needs_normalization`, `needs_expected_outputs`, or any other state
  that has not yet reached `under_review`.
- `approval_attempt` — a reviewer attempts to transition the case to
  `approved` (Section 16 gate).
- `manifest_inclusion` — the case is added to or scanned as part of a
  manifest (Section 18).
- `ci_validation` — CI recomputes canonical hash and runs the
  Section 19.1 validation forms on the case.

#### 9.3.1 Mandatory source-evidence missing — terminal rules

| Lifecycle stage      | Condition                                                        | Target state   |
|----------------------|------------------------------------------------------------------|----------------|
| `pre_approval`       | One or more universal mandatory source-evidence fields missing   | `needs_source` |
| `pre_approval`       | One or more class-specific source-evidence fields missing        | `needs_source` |
| `approval_attempt`   | Any mandatory source-evidence field missing                     | `rejected`     |
| `manifest_inclusion` | Any mandatory source-evidence field missing                     | `rejected`     |
| `ci_validation`      | Any mandatory source-evidence field missing                     | `rejected`     |

#### 9.3.2 `reviewer_evidence_check_status` resolution

The status field is REQUIRED to take one of four values: `pending`,
`accepted`, `accepted_with_caveats`, `rejected`. Each value has a
single target state at every lifecycle stage. The status is set by the
reviewer; self-asserted values are FORBIDDEN.

| Lifecycle stage      | `reviewer_evidence_check_status`     | Target state                                            |
|----------------------|--------------------------------------|---------------------------------------------------------|
| any                  | `pending`                            | `under_review` (MUST NOT enter `approved`)              |
| `pre_approval`       | `accepted`                           | eligible to advance to `under_review`                   |
| `approval_attempt`   | `accepted`                           | eligible for `approved` (all other Section 16 gates MUST also pass) |
| any                  | `accepted_with_caveats`              | `under_review` if reviewer follow-up needed; `needs_source` if caveat identifies missing or corrected evidence field; MUST NOT enter `approved` |
| any                  | `rejected`                           | `rejected` (terminal for current `case_version`)        |

#### 9.3.3 Synthetic regression cases

For `synthetic_regression_case`, the following additional rules
apply on top of Sections 9.3.1 and 9.3.2:

| Lifecycle stage      | Condition                                              | Target state   |
|----------------------|--------------------------------------------------------|----------------|
| `pre_approval`       | `is_synthetic: true` missing or manifest listing absent | `needs_source` |
| `approval_attempt`   | `is_synthetic: true` missing or manifest listing absent | `rejected`     |
| `manifest_inclusion` | `is_synthetic: true` missing or manifest listing absent | `rejected`     |
| `ci_validation`      | `is_synthetic: true` missing or manifest listing absent | `rejected`     |
| any                  | cited as `independent validation evidence`             | `rejected`     |

The corpus MUST contain at least one non-synthetic approved case
for any validation claim. A corpus consisting solely of
`synthetic_regression_case` cases MUST be rejected at the
`manifest_inclusion` and `ci_validation` stages.

#### 9.3.4 Encoding requirements

Implementation MUST encode the table above as a deterministic
function. The signature is informational, not normative:

```text
transition(stage, condition, current_state) -> next_state
```

- The function MUST be total: every `(stage, condition)` pair in the
  table MUST have exactly one `next_state` mapping.
- The function MUST NOT have side effects on canonical hash, manifest
  membership, or approval_snapshot.
- The function MUST be reentrant: invoking it twice with identical
  inputs MUST produce identical outputs.
- The CI gate (Section 19.1, source-evidence validation form) MUST
  call this function for every case at every lifecycle stage and
  MUST reject any case whose actual transition diverges from the
  table.

## 10. Input schema domains

The design MUST define input sections for:

1. Fluid identities
2. Inlet states
3. Flow rates
4. Thermal specifications
5. Geometry
6. Correlation assumptions
7. Provider assumptions
8. Solver assumptions
9. Boundary conditions
10. Metadata and provenance

All numeric values MUST carry units OR MUST be explicitly marked
`SI_normalized: true` with the normalization rule recorded under
`normalization_notes` (Section 9). Implicit unit interpretation is
FORBIDDEN.

## 11. Expected output schema domains

Expected outputs MUST be separated into:

1. Required outputs
2. Optional outputs
3. Derived traceability outputs
4. Diagnostic outputs
5. Non-authoritative commentary

For every required and derived expected output, the case MUST populate
the `tolerance_justifications` block per Section 14. Optional and
diagnostic outputs MUST omit tolerances only if they are not used as
regression targets; otherwise the same rule applies.

`expected_output_origin` (Section 9) MUST NOT be `synthetic_computation`
for any required output unless the case's `source_type` is
`synthetic_regression_case`.

Expected outputs MUST declare a `tolerance_type` drawn from the frozen
set:

```text
absolute
relative
exact_string
exact_enum
hash_only
```

Any tolerance type outside this set is FORBIDDEN. The contract MUST
reject the case at validation.

## 12. Unit and SI normalization rules

The design MUST specify:

- Allowed input units
- Canonical SI units
- Rounding before hashing
- Floating-point serialization precision
- Temperature scale handling
- Pressure absolute / gauge semantics
- Mass-flow vs volumetric-flow semantics
- Heat-duty sign convention

No benchmark case is permitted to rely on implicit unit interpretation.
A case whose unit provenance is not fully traceable MUST be rejected.

## 13. Fluid, property-provider, geometry and boundary assumptions

Every benchmark case MUST specify:

1. Fluid name
2. Fluid backend or provider assumption
3. Phase expectation if applicable
4. Property-call assumptions if relevant
5. Rejection behavior for unsupported or ambiguous state points
6. Geometry description (lengths, diameters, layout) with units
7. Boundary conditions (inlet / outlet / wall) with units

The benchmark corpus MUST NOT silently mix provider backends. If a case
uses a different backend than the corpus default, the difference MUST be
recorded in `source_evidence.normalization_notes`.

## 14. Tolerance policy (P2-2)

Every numeric expected output (required or derived traceability) MUST
populate the `tolerance_justifications` block with ALL of the following
mandatory fields:

| Field                          | Required | Notes |
|--------------------------------|----------|-------|
| `output_name`                  | REQUIRED | Unique within the case. |
| `tolerance_type`               | REQUIRED | Drawn from the frozen set in Section 11. |
| `tolerance_value`              | REQUIRED | Numeric magnitude (or string for `exact_string` / `exact_enum` / `hash_only`). |
| `tolerance_unit_if_absolute`   | REQUIRED when `tolerance_type` is `absolute`; otherwise MUST be `n/a`. |
| `source_precision_basis`       | REQUIRED | Stated source precision, e.g. "3 significant figures per Table 4.2 of <source>". |
| `property_model_basis`         | REQUIRED | Property model uncertainty contribution, e.g. "CoolProp water at 1 bar: ±0.05%". |
| `solver_tolerance_basis`       | REQUIRED | Solver convergence tolerance used to compute the expected value. |
| `rounding_basis`               | REQUIRED | Rounding rule applied before hashing (Section 17). |
| `reviewer_tolerance_approval`  | REQUIRED | Reviewer assertion that the tolerance is consistent with the listed bases. |

Mandatory rejection rules:

- Tolerance MUST NOT be used to hide missing physics.
- Cases that would require unsupported physics (Section 7) MUST be
  rejected at the source-evidence gate. Tolerance widening as a
  workaround is FORBIDDEN.
- Pressure-drop / C4 / materials / cost expected outputs are FORBIDDEN
  in TASK-011 cases. Any expected output whose required physics is not
  yet implemented MUST be rejected or excluded; widening tolerance is
  not an acceptable substitute.
- A case whose `reviewer_tolerance_approval` is missing or `pending`
  MUST NOT enter `approved`.

## 15. Golden vs benchmark separation

Golden tests and benchmark cases MUST remain distinct.

Golden tests:

- are deterministic regression fixtures;
- ARE permitted to be repository-generated;
- primarily protect internal behavior.

Benchmark cases:

- are governed artifacts;
- REQUIRE source classification and approval;
- ARE permitted to be used for traceable validation claims only when the
  source class supports that use. In particular, `synthetic_regression_case`
  cases MUST NOT be cited as validation evidence.

A case can feed tests only through an explicit, reviewed pathway
recorded in the manifest.

## 16. Review and approval workflow

The review workflow MUST use the frozen state machine:

```text
draft
needs_source
needs_normalization
needs_expected_outputs
under_review
approved
rejected
superseded
```

Approval MUST require ALL of the following gates:

1. Complete schema validation (Section 17 hash matches)
2. Source-evidence minimum satisfied (Section 9)
3. Unit normalization checked (Section 12)
4. Expected outputs and tolerances reviewed (Section 14)
5. Non-goals checked (Section 7)
6. Canonical hash generated (Section 17)
7. Reviewer sign-off recorded (identity + timestamp + review ID)

A case in `draft` or any `needs_*` state MUST NOT be used as validation
evidence. A case in `rejected` MUST NOT re-enter `under_review` without
a new `case_version` and new reviewer sign-off.

## 17. Canonical serialization and hash rules (P1-2)

The canonical hash is the binding integrity mechanism for every
benchmark case. The algorithm is FROZEN — implementation MUST use these
exact rules. Any previous "starting point" wording is removed; deviation
is FORBIDDEN.

### 17.1 Hash algorithm

| Parameter             | Frozen value                                  |
|-----------------------|-----------------------------------------------|
| `hash_algorithm`      | SHA-256 (FIPS 180-4).                         |
| `serialization_format`| Canonical JSON (RFC 8785).                    |
| `field_ordering`      | Sorted keys at every object level, recursively. |
| `unicode_normalization` | NFC (UAX #15).                              |
| `date_time_format`    | RFC 3339, UTC, with explicit `Z` suffix.     |
| `mutable_review_comments` | Excluded from hash input.                |
| `approval_comments`   | Excluded unless explicitly part of `approval_snapshot`. |
| `hash_scope`          | Case-level. One canonical hash per case.      |

### 17.2 Mandatory hashed fields

The canonical serialization MUST include, at minimum, the following
fields. Missing or empty values are FORBIDDEN at hash time:

- `case_id`
- `case_version`
- `case_title`
- `category`
- `source_type`
- `source_evidence` (per Section 9 — all mandatory fields)
- `input_schema` (per Section 10)
- `expected_output_schema` (per Section 11)
- `unit_normalization` (per Section 12)
- `fluid_and_property_assumptions` (per Section 13)
- `geometry_and_boundary_assumptions` (per Section 13)
- `tolerance_justifications` (per Section 14)
- `assumptions` (any additional solver / correlation / provider assumptions)
- `approval_status`

### 17.3 Deterministic numeric representation

Numeric representation is FROZEN. Implementation MUST follow these rules:

- All decimal values MUST be serialized as canonical decimal strings.
  Use of `repr()` or platform-dependent float-to-string conversion is
  FORBIDDEN.
- Floats MUST be serialized through a deterministic decimal codec that
  emits the shortest decimal that round-trips to the original IEEE-754
  binary value (round-trippable shortest-decimal).
- `NaN`, `+Infinity`, and `-Infinity` are FORBIDDEN in any hashed
  field. Cases containing these values MUST be rejected at schema
  validation.
- `rounding_before_hashing` MUST be defined per numeric field by the
  schema, e.g. `round_to: 12 significant digits`. Field-level rounding
  basis is recorded under `tolerance_justifications[*].rounding_basis`
  and MUST be applied before hashing.
- Integers MUST be serialized without a decimal point.
- Booleans MUST be serialized as `true` / `false` (lowercase).

### 17.4 Verification

The manifest MUST record each case's canonical hash. CI MUST recompute
the hash and reject any case whose recomputed hash does not equal the
recorded `canonical_hash` (Section 19).

## 18. Manifest rules

The manifest MUST list all approved cases and MUST contain the
following mandatory fields:

```text
manifest_version
schema_version
case_count
case_ids
case_hashes
approval_snapshot
synthetic_case_ids
reviewer_sign_off
```

Field requirements:

- `manifest_version` — semantic version of the manifest format.
- `schema_version` — semantic version of the case schema.
- `case_count` — integer. MUST equal `len(case_ids)`.
- `case_ids` — array, MUST be sorted ascending, MUST NOT contain duplicates.
- `case_hashes` — map from `case_id` to canonical hash. Length MUST equal `case_count`.
- `approval_snapshot` — list of `{case_id, approver_id, approval_timestamp_utc, review_id}` records, one per approved case.
- `synthetic_case_ids` — array of `case_id`s whose `is_synthetic` is true. MUST be a subset of `case_ids`. Length MUST equal the number of cases with `is_synthetic: true` in the corpus.
- `reviewer_sign_off` — array of `{reviewer_id, review_id, scope}` records.

The first implementation target is exactly 20 approved cases unless the
frozen contract explicitly authorizes a staged subset.

## 19. CI validation expectations (P2-3)

TASK-011 implementation acceptance is gated by mandatory CI integrity
checks. The following validation forms are REQUIRED and MUST be in
place before any case is treated as approved.

### 19.1 Mandatory validation forms

1. **Schema validation** — every case file MUST validate against the frozen JSON schema. Cases that fail validation are rejected.
2. **Manifest validation** — every manifest MUST validate against the frozen manifest schema.
3. **Canonical hash verification** — every case's recomputed canonical hash MUST equal its recorded `canonical_hash`. Mismatch is rejection.
4. **Case-count validation** — `case_count` MUST equal `len(case_ids)` and MUST equal `len(case_hashes)`.
5. **Approval-status validation** — only cases with `approval_status == "approved"` are listed in the approved set. Any non-approved case in the approved set is rejection.
6. **Source-evidence validation** — every approved case MUST have a complete `source_evidence` block satisfying Section 9 minimum, including per-class minimum.
7. **Golden-vs-benchmark path separation validation** — `tests/` MUST NOT contain files under `benchmarks/` and `benchmarks/` MUST NOT contain files under `tests/`. The two trees MUST be disjoint.
8. **Synthetic-case labeling validation** — every case with `is_synthetic: true` MUST be listed in `synthetic_case_ids`, and the manifest count MUST equal the corpus count.
9. **Unsupported category rejection** — every case's `category` MUST be one of the Section 6 allowed categories.
10. **Non-goal leakage rejection** — every case's `expected_output_schema` MUST NOT require any non-goal physics from Section 7. Detection uses an explicit allow-list of forbidden output name prefixes (e.g. `pressure_drop_*`, `c4_*`, `material_*`, `cost_*`).

### 19.2 Required implementation surface

The validation forms MUST be exposed through at least one of the
following mechanisms:

- A benchmark manifest validation CLI (e.g. `python -m hexagent.benchmarks.validate`) that exits non-zero on any failure listed above.
- Pytest integrity tests that fail on any of the above failures.
- A CI gate that invokes the validation command on every push that
  touches the benchmark corpus.

The CI gate is REQUIRED for any PR that adds or modifies case files,
manifest files, or the validation tooling itself.

### 19.3 Authorization boundary for this section

This section defines the acceptance contract. It does NOT authorize
creating the CLI, the pytest tests, or the CI workflow file in this PR.
The actual validation tooling is part of the implementation work, which
remains NOT AUTHORIZED until the design contract is separately frozen
and implementation is explicitly authorized.

## 20. Expected implementation file boundary

Implementation is NOT AUTHORIZED by this contract. The paths below are
listed only as candidate boundaries for a future implementation PR.
They MUST NOT be created until the design contract is reviewed, frozen,
and implementation is separately authorized.

```text
benchmarks/
benchmarks/cases/
benchmarks/manifests/
tests/benchmark/
src/hexagent/benchmark_cases/
```

## 21. Acceptance criteria for this design contract

This contract can be considered ready for independent engineering
review when it clearly answers:

1. What counts as one benchmark case? (Section 8)
2. What source evidence is mandatory? (Section 9)
3. Which source classes are allowed? (Section 9.2)
4. How are units normalized? (Section 12)
5. How are expected outputs represented? (Section 11)
6. Which tolerance types are allowed? (Sections 11, 14)
7. How are cases reviewed and approved? (Section 16)
8. How is benchmark data separated from golden tests? (Section 15)
9. How is benchmark provenance hashed? (Section 17)
10. How does CI validate case integrity? (Section 19)
11. Which existing solver/API capabilities are in scope? (Section 6)
12. Which future capabilities are explicitly out of scope? (Section 7)
13. Which files is implementation authorized to create later? (Section 20)
14. What per-output tolerance justifications are mandatory? (Section 14)
15. What mandatory source-evidence fields are required? (Section 9)

## 22. Implementation authorization boundary

```text
TASK-011 design contract: PRE-FREEZE REVISION (NOT FROZEN)
TASK-011 implementation: NOT AUTHORIZED
Benchmark cases: NOT AUTHORIZED
Production code changes: NOT AUTHORIZED
Test changes: NOT AUTHORIZED
CI workflow changes: NOT AUTHORIZED
TASK-012+: NOT AUTHORIZED
```

A later implementation is authorized to start only after ALL of the
following:

1. This design contract is independently reviewed;
2. The reviewed Head is recorded in Issue #36;
3. The frozen contract SHA is established and recorded in Issue #36;
4. Issue #36 is updated with the frozen authority and frozen-SHA
   reference;
5. Explicit implementation authorization is granted by the user.

Until then, every action listed above as `NOT AUTHORIZED` remains
forbidden, regardless of any preview or draft language elsewhere in
this document.