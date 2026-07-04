# TASK-011 — Benchmark Case Governance Design Contract

## 1. Status

```text
TASK-011: DESIGN DRAFT
Issue: #36
Implementation authorization: NOT GRANTED
Benchmark case implementation: NOT STARTED
Frozen contract SHA: NOT ESTABLISHED
```

This document defines the design boundary for TASK-011. It is a governance and schema contract for the first approved benchmark-case corpus. It does not authorize adding benchmark data, production code, test code, CI workflow changes, or solver features.

## 2. Objective

TASK-011 will collect, normalize, review and approve the first 20 benchmark cases for the implemented HXForge v0.1 vertical slice.

A benchmark case is a governed, source-backed, machine-readable case artifact used for later regression, validation, report traceability and benchmark authority. It is not a hidden fixture, ad hoc example, or unreviewed golden-output file.

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

## 4. In-scope work for TASK-011 design

The design contract must specify:

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

## 5. In-scope benchmark categories

The first 20 benchmark cases must be restricted to behavior already implemented before TASK-011 implementation begins.

Allowed categories:

1. Single-phase heat-balance closure
2. Tube-side correlation cases
3. Annulus-side correlation cases
4. Fixed-geometry double-pipe rating cases
5. Manufacturable sizing / candidate evaluation cases
6. API/report traceability cases already supported by TASK-010

A case may only be included if every required calculation path already exists in the repository at the authorized implementation baseline. A benchmark must not force new solver behavior.

## 6. Explicit non-goals

TASK-011 must not implement or require:

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

## 7. Benchmark case definition

One benchmark case is one independently reviewable scenario with:

1. A stable case identifier
2. A source-backed input dataset
3. A declared expected-result contract
4. Explicit unit normalization
5. Explicit fluid/property assumptions
6. Explicit geometry and boundary conditions
7. A numeric tolerance policy
8. Source provenance
9. Reviewer approval status
10. A canonical hash

A benchmark case is not approved until all mandatory fields are populated and reviewed.

## 8. Proposed case identity fields

Each case should define:

```text
case_id
case_version
case_title
category
source_type
source_reference
approval_status
schema_version
canonical_hash
```

Identity requirements:

- `case_id` must be stable and unique.
- `case_version` must change whenever input, expected output, tolerance or source evidence changes.
- `canonical_hash` must be computed from canonical serialized content, excluding mutable review comments.

## 9. Proposed source classification

Allowed source classes should be explicitly enumerated by the design. Candidate classes:

```text
published_reference
vendor_example
engineering_handbook_example
internal_reviewed_case
synthetic_regression_case
```

Synthetic cases may be allowed only when they test deterministic behavior already implemented by the system. They must be clearly labeled and must not be misrepresented as independent validation evidence.

## 10. Proposed input schema domains

The design should define input sections for:

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

All numeric values must carry units or be explicitly SI-normalized.

## 11. Proposed expected-output schema domains

Expected outputs should be separated into:

1. Required outputs
2. Optional outputs
3. Derived traceability outputs
4. Diagnostic outputs
5. Non-authoritative commentary

Expected outputs must define tolerance type:

```text
absolute
relative
exact_string
exact_enum
hash_only
```

The final design must reject any malformed tolerance type before implementation.

## 12. Unit and SI normalization rules

The design must specify:

- Allowed input units
- Canonical SI units
- Rounding before hashing
- Floating-point serialization precision
- Temperature scale handling
- Pressure absolute/gauge semantics
- Mass-flow versus volumetric-flow semantics
- Heat-duty sign convention

No benchmark case may rely on implicit unit interpretation.

## 13. Fluid and property-provider rules

Every benchmark case must specify:

1. Fluid name
2. Fluid backend or provider assumption
3. Phase expectation if applicable
4. Property-call assumptions if relevant
5. Rejection behavior for unsupported or ambiguous state points

The benchmark corpus must not silently mix provider backends without recording that difference in provenance.

## 14. Tolerance policy

The design must define a common tolerance framework.

At minimum:

- Each numeric expected output must declare an absolute or relative tolerance.
- Tolerance must be justified by source precision, property model assumptions and solver tolerance.
- Tolerance must be narrow enough to catch regressions.
- Tolerance must not be used to hide missing physics.

## 15. Golden vs benchmark distinction

Golden tests and benchmark cases must remain distinct.

Golden tests:

- are deterministic regression fixtures;
- may be repository-generated;
- primarily protect internal behavior.

Benchmark cases:

- are governed artifacts;
- require source classification and approval;
- can be used for traceable validation claims only when the source class supports that use.

A case can feed tests only through an explicit, reviewed pathway.

## 16. Review and approval workflow

The design must define states such as:

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

Approval should require:

1. Complete schema validation
2. Source evidence present
3. Unit normalization checked
4. Expected outputs and tolerances reviewed
5. Non-goals checked
6. Canonical hash generated
7. Reviewer sign-off recorded

## 17. Canonical serialization and hash rules

The design must specify:

- Canonical field ordering
- Float formatting
- Unicode normalization
- Date/time handling
- Excluded mutable fields
- Hash algorithm
- Hash scope

A recommended starting point is SHA-256 over canonical JSON with sorted keys and fixed numeric representation.

## 18. Manifest rules

The eventual manifest should list all approved cases and include:

```text
manifest_version
case_count
case_ids
case_hashes
schema_version
approval_snapshot
```

The first implementation target is exactly 20 approved cases unless the frozen design explicitly authorizes a staged subset.

## 19. CI validation expectations

The design must specify which checks are mandatory before implementation can be accepted.

Candidate checks:

1. Manifest schema validates
2. Every listed case file exists
3. Every case hash matches canonical content
4. All 20 cases have approved status
5. No duplicate case IDs
6. No benchmark case uses unsupported category
7. No benchmark case enters explicit non-goals
8. Golden and benchmark files remain separated
9. Synthetic cases are labeled as synthetic
10. All expected outputs declare tolerances

## 20. Expected implementation file boundary

Implementation is not authorized by this draft. The design may later authorize paths such as:

```text
benchmarks/
benchmarks/cases/
benchmarks/manifests/
tests/benchmark/
src/hexagent/benchmark_cases/
```

These paths are listed only as candidate implementation boundaries. They must not be created until the design contract is reviewed, frozen and implementation is separately authorized.

## 21. Acceptance criteria for this design contract

The design can be considered ready for independent review only when it clearly answers:

1. What counts as one benchmark case?
2. What source evidence is mandatory?
3. Which source classes are allowed?
4. How are units normalized?
5. How are expected outputs represented?
6. Which tolerance types are allowed?
7. How are cases reviewed and approved?
8. How is benchmark data separated from golden tests?
9. How is benchmark provenance hashed?
10. How does CI validate case integrity?
11. Which existing solver/API capabilities are in scope?
12. Which future capabilities are explicitly out of scope?
13. Which files may implementation create later?

## 22. Implementation authorization boundary

```text
TASK-011 design: DRAFT
TASK-011 implementation: NOT AUTHORIZED
Benchmark cases: NOT AUTHORIZED
Production code changes: NOT AUTHORIZED
Test changes: NOT AUTHORIZED
CI workflow changes: NOT AUTHORIZED
TASK-012+: NOT AUTHORIZED
```

A later implementation may start only after:

1. this design is reviewed;
2. the reviewed Head is recorded;
3. the frozen contract SHA is established;
4. Issue #36 is updated with the frozen authority;
5. explicit implementation authorization is granted.
