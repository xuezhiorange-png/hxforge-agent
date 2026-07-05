# TASK-016 — Approved Tube, Pipe and Hairpin Geometry Catalog Design Contract

> Design contract for TASK-016. Defines the approved geometry catalog
> for tube, pipe and hairpin geometry records before any implementation.
> This document is design-only: no production code, no public API, no
> report rendering, no database schema, no material / cost / pressure-drop
> implementation, and no catalog data file is introduced by this design PR.

## 1. Authority and status

| Field | Value |
|---|---|
| Authorizing issue | #64 |
| Backlog item | TASK-016 — Add approved tube, pipe and hairpin geometry catalog |
| Backlog status before authorization | PLANNED |
| Backlog dependency | TASK-001 |
| Design branch | `docs/task-016-approved-geometry-catalog-design` |
| Design file | `docs/tasks/TASK-016-approved-geometry-catalog.md` |
| Base authority | TASK-015 final closeout complete at PR #63 merge commit `9d4dd7e7670578dc4833913e89c5c2df340157fb` |
| Implementation status | NOT AUTHORIZED |
| Frozen contract SHA | NOT ESTABLISHED until this design PR is merged |

Implementation work is explicitly blocked until this design contract is
reviewed, merged, and closed out under Charles authorization.

## 2. Problem statement

The double-pipe vertical slice currently has thermal correlation,
fixed-geometry rating, manufacturable sizing, standards rule-pack,
material / cost governance, immutable case revisions, and CI / security /
release hardening contracts. It still lacks a formally approved geometry
catalog for commercially selectable tube, pipe, and hairpin geometries.

Without an approved catalog contract, future sizing or rating code can drift
into ad-hoc dimensions, unstable ordering, hidden unit conversions, or
untraceable geometry source assumptions. TASK-016 closes this design gap by
freezing the catalog semantics before any implementation.

## 3. Scope and non-scope

### 3.1 In scope for this design contract

1. Approved tube geometry record semantics.
2. Approved pipe geometry record semantics.
3. Approved hairpin geometry record semantics.
4. Catalog identity, deterministic ordering, and canonical hashing rules.
5. Unit discipline for all dimensional fields.
6. Source binding and provenance requirements for every approved geometry.
7. Validation blockers for malformed, duplicate, conflicting, unsupported,
   or non-approved geometry records.
8. Future implementation interface boundaries for loading and consuming the
   catalog.
9. Frozen test expectations for the future implementation PR.

### 3.2 Explicit non-scope

This design contract does not authorize:

- TASK-016 implementation.
- Any production code change.
- Any public API or report rendering change.
- Any database, ORM, Alembic migration, or persistence schema change.
- Any material, mass, or preliminary mechanical check; those belong to
  TASK-017.
- Any C0/C1 cost model or life-cycle energy estimate; those belong to
  TASK-018.
- Any Golden cases or double-pipe validation report; those belong to
  TASK-019.
- Pressure-drop implementation, pressure-drop correlations, C4 logic,
  equipment expansion, shell-and-tube, plate, air cooler, two-phase, or
  refrigerant functionality.
- Secret registration, OIDC trust, registry push, or external service
  integration.
- Mutation of TASK-015A assets or frozen TASK-011 / TASK-012 / TASK-013 /
  TASK-014 / TASK-015 contract bodies.

## 4. Catalog design goals

The catalog must be:

1. **Approved-only** — consumers may select only records whose approval state
   is explicitly approved.
2. **Deterministic** — loading, validation, ordering, and hashing must be
   stable across platforms and Python versions.
3. **Unit-explicit** — every dimensional value is stored in canonical SI units
   and may carry display metadata only as provenance, not as computation
   authority.
4. **Source-bound** — every record cites its source, revision, and approval
   authority.
5. **Composable** — tube, pipe, and hairpin records may be consumed by future
   sizing and rating logic without embedding material, cost, or mechanical
   semantics.
6. **Blocker-driven** — invalid catalog states must surface structured
   blockers, not partial best-effort loading.

## 5. Domain model

### 5.1 GeometryCatalog

A `GeometryCatalog` is the immutable validated aggregate containing approved
geometry records. The catalog has:

- `catalog_id`: stable identifier, e.g. `approved-geometry-catalog`.
- `catalog_version`: semantic catalog version.
- `authority`: approving authority string.
- `source_revision`: source package or document revision.
- `generated_at` or `effective_at`: timestamp metadata.
- `records`: canonical sequence of geometry records.
- `content_hash`: deterministic SHA-256 hash of canonical content.

The content hash covers the normalized record payload and catalog metadata
required for reproducibility. It must not include volatile runtime fields.

### 5.2 GeometryRecord common fields

Every approved geometry record must expose:

| Field | Requirement |
|---|---|
| `geometry_id` | Unique stable identifier within the catalog |
| `geometry_type` | One of `tube`, `pipe`, `hairpin` |
| `approval_state` | Must be `approved` for selectable records |
| `nominal_label` | Human-readable label, not computation authority |
| `dimension_set` | Canonical SI dimensional fields |
| `source_binding` | Source identity and evidence reference |
| `revision` | Record-level revision or source edition marker |
| `tags` | Optional deterministic tags for grouping |
| `record_hash` | Deterministic SHA-256 hash of normalized record content |

### 5.3 Tube geometry record

Tube geometry records describe tube dimensions only. Required dimensional
fields:

- `outer_diameter_m`
- `inner_diameter_m`
- `wall_thickness_m`
- `cross_section_area_m2`
- `flow_area_m2`
- `hydraulic_diameter_m`

Validation must ensure positive dimensions and algebraic consistency:

- `outer_diameter_m > inner_diameter_m > 0`
- `wall_thickness_m == (outer_diameter_m - inner_diameter_m) / 2`
- areas and hydraulic diameter are positive
- computed values match canonical tolerance policy

Tube records do not encode material grade, allowable stress, corrosion
allowance, fouling, pressure rating, or cost.

### 5.4 Pipe geometry record

Pipe geometry records describe pipe dimensions only. Required dimensional
fields:

- `nominal_pipe_size_label`
- `schedule_label` or approved equivalent
- `outer_diameter_m`
- `inner_diameter_m`
- `wall_thickness_m`
- `flow_area_m2`
- `hydraulic_diameter_m`

Validation must ensure schedule and nominal labels are deterministic labels,
not computation authority. Computation uses canonical SI dimensional fields.

Pipe records do not encode material grade, flange rating, code compliance,
mechanical pressure rating, or cost.

### 5.5 Hairpin geometry record

Hairpin geometry records describe bundle-level geometry sufficient to select
an approved hairpin geometry family. Required fields:

- `hairpin_id`
- `tube_geometry_id` or embedded approved tube reference
- `pipe_geometry_id` or embedded approved pipe reference
- `number_of_tubes`
- `effective_length_m`
- `bend_radius_m`
- `centerline_spacing_m`
- `flow_path_descriptor`

Validation must ensure referenced tube and pipe geometries exist and are
approved. The hairpin record must not introduce pressure-drop, mechanical,
material, or cost conclusions.

## 6. Unit and tolerance policy

All computation-authority dimensions are stored in SI base units:

| Quantity | Unit |
|---|---|
| Diameter | m |
| Thickness | m |
| Length | m |
| Area | m² |
| Count | dimensionless integer |

Display labels such as NPS, schedule, BWG, inch labels, or vendor names may
be preserved as metadata but cannot be the sole authority for computation.

The implementation contract must define a single tolerance profile for
consistency checks. Tolerance must be strict enough to reject inconsistent
records while allowing deterministic decimal-to-SI conversions. Tolerance
values must be documented and covered by tests before implementation can be
accepted.

## 7. Identity, ordering, and hashing

### 7.1 Stable identity

`geometry_id` must be stable across catalog loads. It must not depend on row
number, input file ordering, object memory address, or runtime locale.

Recommended ID shape:

```text
<geometry_type>/<normalized-family>/<normalized-size>/<revision>
```

Examples are illustrative only and are not frozen data records.

### 7.2 Canonical ordering

The catalog must sort records by:

1. `geometry_type`
2. `geometry_id`
3. `revision`
4. `record_hash`

Consumers must not depend on input file order.

### 7.3 Hashing

Hash computation must use canonical JSON serialization with deterministic key
ordering and normalized numeric representation. Hashes must be stable under
non-semantic field ordering changes and must change when computation-authority
fields change.

## 8. Source binding and provenance

Every record must have a source binding that includes:

- `source_id`
- `source_type`
- `source_revision`
- `source_location`
- `evidence_ref`
- `approved_by`
- `approved_at`

The catalog must distinguish source evidence from approval authority. A record
can be derived from a standard, vendor table, or internal approved list, but
it is selectable only when explicitly approved in the catalog.

Source binding validation blockers must fire when source evidence is missing,
ambiguous, duplicated, or inconsistent with record revision metadata.

## 9. Validation blockers

The future implementation must expose structured blockers for at least these
cases:

| Code | Meaning |
|---|---|
| `geometry_catalog_missing` | Catalog payload is absent |
| `geometry_record_missing_id` | Record has no stable `geometry_id` |
| `geometry_record_duplicate_id` | Duplicate `geometry_id` after normalization |
| `geometry_record_unapproved` | Record is not explicitly approved |
| `geometry_type_unsupported` | Record type is not tube, pipe, or hairpin |
| `geometry_dimension_non_positive` | Diameter, length, area, or count is invalid |
| `geometry_dimension_inconsistent` | Derived dimensions do not match canonical fields |
| `geometry_source_missing` | Source binding is absent or incomplete |
| `geometry_hash_mismatch` | Stored hash differs from canonical hash |
| `geometry_reference_missing` | Hairpin references a missing tube or pipe record |
| `geometry_reference_unapproved` | Hairpin references a non-approved record |

Blockers must be deterministic and must not be converted to warnings when the
catalog cannot safely be consumed.

## 10. Consumer boundary

The approved geometry catalog may be consumed by future sizing and rating
logic as a read-only source of dimensions. It must not be used to infer:

- material properties
- allowable pressure
- corrosion allowance
- mechanical suitability
- cost
- pressure drop
- fouling
- vendor availability
- procurement status

Those concerns belong to later tasks and must bind to the geometry catalog
through explicit, separately approved contracts.

## 11. Future implementation contract

The future implementation PR, if authorized, must add only the minimum
production and test surface needed to implement this contract. Expected
implementation surfaces may include:

- immutable data models for catalog and geometry records
- deterministic loader and validator
- canonical hash helper integration
- approved-only accessor functions
- structured validation blockers
- unit tests and golden validation fixtures for catalog semantics

Implementation must not introduce public API, report rendering, database
persistence, materials, mass, mechanical checks, cost, pressure-drop, or
external integrations unless Charles explicitly expands TASK-016 scope.

## 12. Frozen test expectations

The future implementation must include tests for:

1. Loading a valid approved catalog succeeds.
2. Duplicate IDs are rejected after canonical normalization.
3. Non-approved records are not selectable.
4. Unsupported geometry types are blockers.
5. Negative or zero dimensions are blockers.
6. Tube wall thickness consistency is enforced.
7. Pipe schedule labels are metadata, not computation authority.
8. Hairpin references must point to approved tube and pipe records.
9. Canonical ordering is independent of input file order.
10. Record hash changes when computation-authority dimensions change.
11. Record hash remains stable under non-semantic key ordering changes.
12. Missing source binding is a blocker.
13. Catalog-level content hash is deterministic.
14. Consumers receive approved records only.
15. TASK-017 material / mass / mechanical concerns remain absent.
16. TASK-018 cost concerns remain absent.

These tests are specification expectations only. This design PR must not add
implementation tests unless Charles explicitly authorizes frozen-test assets
inside the design review.

## 13. Acceptance and closeout criteria

The TASK-016 design PR can be considered ready for review when:

- this design contract is present and internally consistent;
- Issue #64 remains open;
- the PR remains Draft until Charles authorizes Ready;
- no implementation code is introduced;
- no frozen TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015 contract
  body is mutated;
- no TASK-017+ scope is introduced;
- no TASK-015A asset is mutated.

The design issue may close only after the design PR is merged, post-merge
evidence is recorded, and Charles explicitly authorizes closeout.
