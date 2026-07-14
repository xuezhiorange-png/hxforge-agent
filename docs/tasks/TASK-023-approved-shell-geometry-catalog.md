# TASK-023 — Approved Shell Geometry Catalog Authority Design Contract

> Binding design proposal for an independent approved shell-geometry catalog
> authority. TASK-023 defines the immutable, deterministic, source-bound catalog
> semantics required before TASK-022 Slice B2 may construct an
> `ApprovedShellGeometrySnapshot`.
>
> This document is design-only. It introduces no production code, tests, fixture,
> shell-size table, vendor data, restricted-standard content, branch, commit, push,
> pull request, TASK-016 mutation, or TASK-022 Slice B2 implementation.

## 1. Authority, allocation, and current status

| Field | Value |
|---|---|
| Authorizing Issue | #149 — `[TASK-023][source-definition] Allocate approved shell geometry catalog authority` |
| Source-definition authorization | `AUTHORIZE_TASK023_SHELL_GEOMETRY_CATALOG_SOURCE_DEFINITION_AND_ALLOCATION_ONLY` |
| Design-authoring authorization | `AUTHORIZE_TASK023_ONE_FILE_DESIGN_CONTRACT_AUTHORING_ONLY` |
| Frozen task allocation | `TASK-023 = Approved Shell Geometry Catalog Authority` |
| Authoring base | `main@39d4f66a3cb472b17db5c35f850fc7f31d9c1e28` |
| Design file | `docs/tasks/TASK-023-approved-shell-geometry-catalog.md` |
| Allowed authored file count | exactly one |
| Design branch | NOT AUTHORIZED |
| Commit / push | NOT AUTHORIZED |
| Pull request | NOT AUTHORIZED |
| Implementation | NOT AUTHORIZED |
| TASK-016 mutation | NOT AUTHORIZED |
| TASK-022 Slice B2 | NOT AUTHORIZED |
| Issue close | NOT AUTHORIZED |
| TASK-024 through TASK-039 | UNALLOCATED |
| Design status | PROPOSED until separately reviewed, committed, merged, and closed out |

This authorization permits authoring this one design contract only. It does not
authorize direct mutation of `main`, creation of a branch, a commit, a push, a
pull request, Ready transition, merge, implementation, catalog data admission,
Issue closure, branch deletion, review mutation, or allocation of a later task.

## 2. Exact TASK-023 allocation

TASK-023 owns **Approved Shell Geometry Catalog Authority**.

It owns the upstream authority required to represent and exact-select one
approved shell geometry record whose computation-authority dimension is
`shell_inside_diameter_m`.

TASK-023 must eventually provide:

1. one immutable shell geometry record model;
2. one immutable shell geometry catalog aggregate;
3. exact field-set validation;
4. canonical decimal validation for shell inside diameter;
5. explicit approval, source, license, permission, provenance, and evidence
   authority;
6. deterministic record and catalog hashing;
7. deterministic canonical ordering;
8. exact record lookup by explicit `geometry_id`;
9. fail-closed structured blockers;
10. a separately governed source-data admission path;
11. an upstream value that a later, separately authorized TASK-022 Slice B2
    adapter can project into the already-frozen TASK-022
    `ApprovedShellGeometrySnapshot`.

TASK-023 does not own shell sizing, nearest-size selection, bundle-to-shell
optimization, mechanical shell design, shell outside diameter, shell wall
thickness, pressure rating, materials, baffles, thermal rating, pressure drop,
mass, cost, procurement, APIs, persistence, CLI, reports, or TASK-022 core
geometry equations.

## 3. Source-of-truth inventory

### 3.1 Binding repository sources

TASK-023 is derived from:

1. Issue #149 and its frozen source-definition/allocation record.
2. `docs/tasks/TASK-016-approved-geometry-catalog.md`.
3. Current TASK-016 runtime under `src/hexagent/geometry_catalogs/`.
4. `docs/tasks/TASK-022-shell-and-bundle-geometry.md`.
5. Current TASK-022 runtime under
   `src/hexagent/exchangers/shell_tube/shell_bundle_geometry/`.
6. Issue #147, including the frozen TASK-022 Slice B2 blocker and unlock
   conditions.
7. PR #148 and merge commit
   `39d4f66a3cb472b17db5c35f850fc7f31d9c1e28`.
8. `docs/tasks/TASK-012-standards-rule-pack-license-boundary.md`.
9. Shared deterministic canonicalization, hash, blocker, provenance, and CI
   governance established by prior tasks.

### 3.2 TASK-016 authority retained without mutation

TASK-016 remains frozen with exactly these geometry types:

```text
tube
pipe
hairpin
```

TASK-023 must not add `shell` to the TASK-016 `GeometryType` union, modify
TASK-016 models, reinterpret a TASK-016 pipe as a shell, or widen any TASK-016
public operation.

TASK-016 is precedent for immutable approved records, source binding,
deterministic hashing, canonical ordering, and approved-only access. It is not
the runtime type authority for TASK-023 shell records.

### 3.3 TASK-022 downstream contract retained without mutation

TASK-022 already freezes this downstream projection:

```text
ApprovedShellGeometrySnapshot
- schema_version
- geometry_id
- geometry_type
- revision
- approval_state
- shell_inside_diameter_m
- record_hash
- source_binding
- snapshot_hash
```

TASK-023 must produce sufficient validated upstream authority for a future
adapter to construct that exact shape.

TASK-023 must not modify the TASK-022 snapshot, add catalog fields to it, or
implement the adapter that constructs it.

### 3.4 Runtime authority gap

At design-authoring time, no approved production shell catalog artifact exists.

There is no repository-authorized source package that supplies:

- shell record identities;
- shell inside-diameter values;
- record-level source and approval evidence;
- record hashes;
- catalog identity and catalog hash;
- repository redistribution authority where required.

This gap is binding. Implementing catalog models and validators alone does not
create approved shell data and does not by itself unblock TASK-022 Slice B2.

## 4. Frozen anti-reuse and anti-fabrication boundary

The following substitutions are forbidden:

1. treating a TASK-016 `PipeGeometryRecord` as a shell record;
2. treating a TASK-016 `HairpinGeometryRecord` as a shell record;
3. copying pipe inner or outer diameter into shell authority;
4. inferring shell diameter from TASK-021 placement envelope;
5. inferring shell diameter from TASK-022 bundle envelope or clearance;
6. choosing a shell by nearest, next-larger, first-fitting, minimum, ranking,
   fallback, default, or heuristic logic;
7. rounding to a remembered commercial or standard size series;
8. embedding remembered TEMA, API, ASME, GB, EN, JIS, DIN, vendor, handbook, or
   historical-project values;
9. reproducing paid-standard tables, vendor tables without permission, scans,
   screenshots, figures, or copied excerpts;
10. creating a synthetic record and labeling it approved without explicit
    source, review, approval, and licensing authority;
11. treating a human-readable nominal label as computation authority;
12. using runtime clock, locale, environment, database, network, filesystem
    scan, or global registry state to determine a record.

A physical pipe may sometimes serve as a shell in an engineering project. That
physical possibility does not convert a TASK-016 pipe record into TASK-023
approved shell authority. Geometry role, identity, approval scope, and
provenance must be explicit.

## 5. Design goals

The TASK-023 authority must be:

1. **Independent** — no TASK-016 type widening or frozen-contract mutation.
2. **Approved-only** — only records whose `approval_state` is exactly
   `approved` are selectable.
3. **Exact-select** — a caller supplies one explicit stable `geometry_id`.
4. **Deterministic** — parsing, validation, ordering, selection, and hashing are
   stable across platforms and executions.
5. **Canonical-decimal** — computation-authority dimensions are canonical
   decimal strings in SI metres, never binary floats.
6. **Source-bound** — every record carries complete source and approval
   evidence.
7. **License-gated** — runtime and repository use are allowed only when source
   class and permission evidence permit them.
8. **Fail-closed** — unsafe or incomplete catalogs return structured blockers,
   never partial authority.
9. **Data-separated** — runtime framework implementation does not fabricate or
   silently bundle production shell-size data.
10. **Adapter-ready** — a later TASK-022 B2 adapter can project one exact record
    without catalog scan, ranking, or semantic reinterpretation.

## 6. Closed v1 constants

```text
CATALOG_SCHEMA_VERSION = task023.approved-shell-geometry-catalog.v1
RECORD_SCHEMA_VERSION = task023.approved-shell-geometry-record.v1
PROFILE_ID = hxforge.shell_geometry_catalog.v1
GEOMETRY_TYPE = shell
APPROVAL_STATE_APPROVED = approved
DESIGN_CONTRACT_PATH = docs/tasks/TASK-023-approved-shell-geometry-catalog.md
```

No alias, legacy value, case-insensitive match, prefix match, or unknown future
value is accepted in v1.

## 7. Canonical value rules

### 7.1 Exact field sets

Every public mapping has an exact field set. Missing required fields and unknown
fields block.

Raw types are validated before semantic validation:

- mappings must be mappings;
- strings must be strings;
- arrays must be arrays;
- integers must be integers;
- booleans are never accepted as integers;
- numeric strings are not silently accepted for non-decimal integer fields;
- non-string values are not stringified;
- null is accepted only where explicitly declared.

### 7.2 Canonical JSON domain

Hash-bound values may contain only:

- null;
- booleans;
- integers;
- canonical finite decimal strings;
- strings;
- arrays of permitted values;
- objects with string keys and permitted values.

Forbidden hash-domain values include:

- binary floats;
- `Decimal` objects at serialization;
- NaN or Infinity;
- bytes;
- sets;
- runtime objects;
- datetime objects;
- locale-dependent values.

### 7.3 Canonical decimal lexical form

`shell_inside_diameter_m` is a canonical decimal string that must:

- be finite;
- be strictly greater than zero;
- use SI metres;
- contain no exponent notation;
- contain no leading plus sign;
- contain no surrounding whitespace;
- contain no redundant leading zeroes;
- contain no redundant trailing fractional zeroes;
- normalize negative zero to `0`, which then fails the positive-value rule.

The parser must not perform inch-to-metre, millimetre-to-metre, NPS, schedule,
DN, gauge, nominal-size, or vendor-label conversion. Such conversions must
occur before artifact authoring and must be evidenced by the approved source
package.

### 7.4 Array normalization

Arrays declared sorted and duplicate-free use this sequence:

1. validate raw element types;
2. construct canonical element values;
3. detect duplicates;
4. block on duplicates;
5. sort by ascending Unicode code-point order.

Duplicates are never silently removed.

## 8. Frozen domain model

### 8.1 `ShellSourceBinding`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `source_id` | string | non-empty stable source identifier |
| `source_type` | string | non-empty |
| `source_revision` | string | non-empty |
| `source_location` | string | non-empty locator, not embedded restricted body |
| `evidence_ref` | string | non-empty stable evidence pointer |
| `approved_by` | string | non-empty recorded approving authority |
| `approved_at` | string | explicit recorded value, never runtime-now |

The field shape intentionally matches the source-binding projection expected by
TASK-022. It does not by itself prove license permission; license authority is
carried separately on the TASK-023 record.

### 8.2 Closed `source_class` set

Every record declares exactly one value:

```text
PUBLIC_DOMAIN
OPEN_LICENSE
USER_PROVIDED_LICENSED_SUMMARY
INTERNAL_ENGINEERING_RULE
DERIVED_ENGINEERING_RULE
REFERENCE_ONLY_RESTRICTED_STANDARD
VENDOR_PERMISSIONED
```

Unknown values block.

### 8.3 `ShellGeometryRecord`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | exact record schema version |
| `geometry_id` | string | stable, non-empty, exact lookup key |
| `geometry_type` | string | exact `shell` |
| `profile_id` | string | exact TASK-023 profile |
| `revision` | string | non-empty record revision |
| `approval_state` | string | exact `approved` for selectable records |
| `shell_inside_diameter_m` | decimal string | canonical, positive, SI metre |
| `nominal_label` | string | optional human-readable metadata; not computation authority |
| `source_class` | enum string | closed TASK-012-aligned value |
| `license_evidence` | canonical JSON object | non-null and source-class compatible |
| `source_binding` | `ShellSourceBinding` | complete |
| `permission_evidence_refs` | tuple[string] | sorted, unique; required where applicable |
| `provenance_edge_ids` | tuple[string] | sorted, unique; required where applicable |
| `evidence_refs` | tuple[string] | sorted, unique, non-empty |
| `record_hash` | lowercase SHA-256 hex | recomputable from frozen record payload |

No v1 record field represents:

- shell outside diameter;
- wall thickness;
- corrosion allowance;
- material;
- allowable stress;
- design pressure;
- temperature limit;
- code stamp;
- manufacturing tolerance;
- nominal pipe size;
- schedule;
- baffle diameter;
- flange or nozzle geometry;
- mass or cost;
- vendor availability.

### 8.4 Stable `geometry_id`

`geometry_id` must be stable and globally unambiguous within TASK-023 authority.

Frozen v1 shape:

```text
<catalog_id>/shell/<record_key>/<revision>
```

Each segment is non-empty. IDs must not depend on:

- array position;
- input order;
- object memory address;
- runtime date;
- local path;
- locale;
- nominal-label parsing.

The `catalog_id` prefix preserves upstream catalog identity in the exact record
ID that is later projected into TASK-022.

### 8.5 `ShellGeometryCatalog`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | exact catalog schema version |
| `catalog_id` | string | stable, non-empty |
| `catalog_version` | string | non-empty |
| `profile_id` | string | exact TASK-023 profile |
| `authority` | string | non-empty approving authority |
| `source_revision` | string | non-empty source-package revision |
| `records` | tuple[`ShellGeometryRecord`] | canonical order, unique IDs |
| `catalog_hash` | lowercase SHA-256 hex | recomputable from frozen catalog payload |
| `effective_at` | string or null | explicit metadata; never generated at runtime |

`effective_at` is authority metadata and is included in the catalog hash when
present. Runtime code must not create or update it.

### 8.6 No catalog-global selection semantics

The catalog does not contain:

- minimum or maximum allowable diameter;
- preferred series;
- ranking;
- default record;
- fallback record;
- nearest-size policy;
- fit policy;
- optimization objective;
- bundle compatibility conclusions.

It is an approved identity-and-dimension authority only.

## 9. Hashing contract

### 9.1 Canonical serialization

Hashing uses the repository-approved canonical JSON implementation with:

- deterministic object-key ordering;
- NFC string normalization where provided by the shared helper;
- canonical decimal strings;
- no runtime-dependent values.

TASK-023 must reuse shared canonical infrastructure and must not create a
parallel incompatible JSON canonicalizer.

### 9.2 Record hash

`record_hash` covers every `ShellGeometryRecord` field except:

```text
record_hash
nominal_label
```

`nominal_label` is excluded because it is display metadata, not computation or
authority identity.

The record hash includes:

- schema and profile;
- geometry ID and type;
- revision and approval state;
- shell inside diameter;
- source class;
- complete license evidence;
- complete source binding;
- permission evidence references;
- provenance edge IDs;
- evidence references.

A change to any computation, approval, license, source, permission,
provenance, or evidence field must change the hash.

### 9.3 Catalog hash

`catalog_hash` covers every catalog field except `catalog_hash`.

The `records` contribution is the canonical ordered array of complete record
hashes. Catalog hash validation occurs only after all record hashes pass.

### 9.4 Hash syntax

Every stored hash must be:

- exactly 64 characters;
- lowercase hexadecimal;
- recomputable;
- compared by exact string equality.

No truncated hash, uppercase alias, algorithm marker, or alternate digest is
accepted in v1.

## 10. Canonical ordering and duplicate identity

Records are ordered by:

```text
geometry_id
revision
record_hash
```

Before ordering:

1. raw IDs are validated;
2. exact duplicate `geometry_id` values are detected;
3. duplicates block the catalog;
4. records are validated and hashed;
5. only then is canonical ordering applied.

Input order has no authority.

Multiple revisions of the same logical record require distinct
`geometry_id` values under the frozen v1 ID shape. TASK-023 v1 does not select
a latest revision automatically.

## 11. Source, license, permission, and provenance boundary

### 11.1 General rule

Every record must satisfy both:

```text
engineering authority
license / permission authority
```

Engineering approval does not override licensing. Licensing does not create
engineering approval.

### 11.2 Source-class dispositions

#### `PUBLIC_DOMAIN`

Permitted only when public-domain status is explicitly evidenced.

Required:

- complete license evidence;
- complete source binding;
- human approval;
- evidence references.

#### `OPEN_LICENSE`

Permitted only when:

- an SPDX or equally explicit license identifier is present;
- repository storage and redistribution are allowed;
- attribution and notice obligations are satisfied;
- human approval is recorded.

#### `INTERNAL_ENGINEERING_RULE`

Permitted only for internally authored shell records whose source package
contains:

- author identity;
- review identity;
- derivation inputs;
- explicit statement that no restricted table or vendor body was copied;
- approval evidence.

This class must not disguise remembered standard or vendor dimensions.

#### `DERIVED_ENGINEERING_RULE`

Permitted only when:

- derivation logic is recorded;
- every input source has a provenance edge;
- no forbidden source body is redistributed;
- the resulting numeric value is independently reviewed and approved;
- license evidence allows the derived artifact to be stored and used.

#### `USER_PROVIDED_LICENSED_SUMMARY`

May be runtime-selectable only in a local authorized deployment when:

- the user supplied the summary;
- the user asserts the required license;
- the record body is not redistributed publicly;
- repository/public-artifact restrictions are enforced;
- approval and provenance are complete.

A public repository production catalog must not embed a non-redistributable
record body under this class.

#### `REFERENCE_ONLY_RESTRICTED_STANDARD`

Metadata-only. It may identify a source locator but may not carry a
repository-stored shell-diameter record body derived by copying a restricted
table.

A metadata-only reference is not selectable shell geometry authority.

#### `VENDOR_PERMISSIONED`

Permitted only when explicit permission evidence covers every required scope:

```text
repository_storage
repository_redistribution
local_kernel_usage
```

If any required scope is absent, a public-repository production record is
blocked. Public artifact emission requires its own explicit scope if record
content would be emitted.

### 11.3 Forbidden content

TASK-023 artifacts must not contain:

- full standards text;
- paid-standard excerpts;
- copied restricted tables;
- scans or screenshots;
- reproduced proprietary figures;
- vendor table bodies without explicit permission;
- hidden or encrypted restricted content;
- values attributed only to memory;
- citation-free engineering numbers.

### 11.4 Provenance edges

`provenance_edge_ids` identifies approved provenance objects outside the
record body.

For derived or vendor-permissioned records, provenance edges are mandatory.

The record must not embed arbitrary provenance narratives in unstructured
fields as a substitute for stable evidence references.

## 12. Source-data admission gate

### 12.1 Framework implementation is not data approval

A future runtime implementation may add models, parser, validator, hash logic,
and exact selection without adding a production shell catalog record.

That implementation is **framework-complete but authority-incomplete**.

TASK-022 Slice B2 remains blocked until at least one actual record passes the
separate source-data admission gate.

### 12.2 Required admission package

Every production catalog-data authorization must supply:

1. proposed `catalog_id` and `catalog_version`;
2. exact record payloads;
3. source class for every record;
4. complete source bindings;
5. license evidence;
6. permission evidence where applicable;
7. provenance edges;
8. approval authority;
9. canonical record hashes;
10. canonical catalog hash;
11. evidence that repository storage, redistribution, and runtime use are
    permitted;
12. review results showing no forbidden content or fabricated dimensions.

### 12.3 No production catalog path is authorized now

This design contract does not authorize or create a production catalog path or
artifact.

A future source-data authorization must separately freeze:

- artifact location;
- serialization format;
- catalog ID;
- source package;
- records;
- license and permission evidence;
- CI coverage;
- redistribution posture.

No placeholder record, demonstration size, remembered size, empty approved
catalog, or test fixture may be relabeled as production authority.

## 13. Frozen public operations for future runtime implementation

TASK-023 v1 may expose exactly these logical operations:

```python
parse_shell_geometry_catalog(
    *,
    raw_catalog: Mapping[str, Any],
) -> ShellGeometryCatalog
```

```python
select_approved_shell_geometry(
    *,
    catalog: ShellGeometryCatalog,
    geometry_id: str,
) -> ShellGeometryRecord
```

### 13.1 Parser boundary

`parse_shell_geometry_catalog`:

- consumes one already-loaded in-memory mapping;
- performs no filesystem, network, database, environment, clock, locale, or
  registry access;
- validates the complete catalog;
- returns no partial catalog;
- raises one structured TASK-023 failure carrying deterministic blockers.

### 13.2 Exact selection boundary

`select_approved_shell_geometry`:

- requires an explicit non-empty `geometry_id`;
- performs exact ID lookup only;
- returns one complete approved record;
- blocks when not found or unapproved;
- performs no scan by diameter, nominal label, revision, source, or tags;
- performs no nearest, next-larger, first-fitting, ranking, fallback, default,
  or optimization behavior.

### 13.3 Explicit non-operation

TASK-023 does not expose an operation that constructs TASK-022
`ApprovedShellGeometrySnapshot`.

That operation belongs to a separately authorized TASK-022 Slice B2 adapter
after TASK-023 runtime and source-data authority are merged and reverified.

## 14. Frozen blocker taxonomy

The future runtime blocker set is closed at these 25 codes:

```text
SGC_RAW_TYPE_INVALID
SGC_UNKNOWN_FIELD
SGC_SCHEMA_VERSION_UNSUPPORTED
SGC_CATALOG_ID_INVALID
SGC_CATALOG_VERSION_INVALID
SGC_PROFILE_UNSUPPORTED
SGC_CATALOG_AUTHORITY_INVALID
SGC_RECORDS_INVALID
SGC_RECORD_ID_INVALID
SGC_RECORD_DUPLICATE_ID
SGC_GEOMETRY_TYPE_INVALID
SGC_REVISION_INVALID
SGC_APPROVAL_STATE_INVALID
SGC_RECORD_UNAPPROVED
SGC_SHELL_INSIDE_DIAMETER_INVALID
SGC_SOURCE_BINDING_INCOMPLETE
SGC_SOURCE_CLASS_INVALID
SGC_LICENSE_BLOCKED
SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE
SGC_PROVENANCE_INCOMPLETE
SGC_EVIDENCE_REFS_INVALID
SGC_RECORD_HASH_MISMATCH
SGC_CATALOG_HASH_MISMATCH
SGC_RECORD_NOT_FOUND
SGC_SELECTION_NOT_APPROVED
```

No generic fallback code, alias, reserved code, warning substitution, or
repurposing is permitted without a later Charles authorization.

### 14.1 Default field-path anchors

| Code | Default field path |
|---|---|
| `SGC_RAW_TYPE_INVALID` | catalog or current raw field |
| `SGC_UNKNOWN_FIELD` | exact unknown path |
| `SGC_SCHEMA_VERSION_UNSUPPORTED` | `schema_version` |
| `SGC_CATALOG_ID_INVALID` | `catalog_id` |
| `SGC_CATALOG_VERSION_INVALID` | `catalog_version` |
| `SGC_PROFILE_UNSUPPORTED` | `profile_id` |
| `SGC_CATALOG_AUTHORITY_INVALID` | `authority` or `source_revision` |
| `SGC_RECORDS_INVALID` | `records` |
| `SGC_RECORD_ID_INVALID` | `records[i].geometry_id` |
| `SGC_RECORD_DUPLICATE_ID` | `records` |
| `SGC_GEOMETRY_TYPE_INVALID` | `records[i].geometry_type` |
| `SGC_REVISION_INVALID` | `records[i].revision` |
| `SGC_APPROVAL_STATE_INVALID` | `records[i].approval_state` |
| `SGC_RECORD_UNAPPROVED` | `records[i].approval_state` |
| `SGC_SHELL_INSIDE_DIAMETER_INVALID` | `records[i].shell_inside_diameter_m` |
| `SGC_SOURCE_BINDING_INCOMPLETE` | `records[i].source_binding` |
| `SGC_SOURCE_CLASS_INVALID` | `records[i].source_class` |
| `SGC_LICENSE_BLOCKED` | `records[i].license_evidence` |
| `SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE` | `records[i].permission_evidence_refs` |
| `SGC_PROVENANCE_INCOMPLETE` | `records[i].provenance_edge_ids` |
| `SGC_EVIDENCE_REFS_INVALID` | `records[i].evidence_refs` |
| `SGC_RECORD_HASH_MISMATCH` | `records[i].record_hash` |
| `SGC_CATALOG_HASH_MISMATCH` | `catalog_hash` |
| `SGC_RECORD_NOT_FOUND` | `geometry_id` |
| `SGC_SELECTION_NOT_APPROVED` | selected record `approval_state` |

## 15. Validation pipeline and blocker ordering

### 15.1 Frozen stage order

The parser uses this exact stage order:

1. top-level raw type;
2. top-level exact field set;
3. catalog schema, profile, ID, version, authority, and source revision;
4. records-array raw type and non-empty rule;
5. per-record raw type and exact field set;
6. record identity, duplicate ID, type, profile, and revision;
7. approval-state validation;
8. canonical shell-inside-diameter validation;
9. source-binding validation;
10. source-class and license validation;
11. permission-scope and provenance validation;
12. evidence-array validation;
13. record-hash validation;
14. canonical record ordering;
15. catalog-hash validation.

Exact selection uses:

16. selection raw `geometry_id` validation;
17. exact lookup;
18. selected-record approval recheck.

A stage with blockers gates every later dependent stage.

### 15.2 Same-stage accumulation

Independent blockers discovered in the same stage may accumulate.

Examples:

- several unknown fields in one mapping;
- several duplicate IDs;
- several records with invalid diameters;
- several incomplete source bindings.

The implementation must not stop after the first independent same-stage error
when the remaining checks are safe and deterministic.

### 15.3 Deterministic blocker order

Blockers are ordered by:

```text
(
  stage_rank,
  code,
  field_path or "",
  message_key,
  sha256(canonical_json(details)),
  sha256(canonical_json(evidence_refs))
)
```

Blocker details and evidence references must be deep-frozen canonical values.

### 15.4 No partial success

Any blocker means:

- no `ShellGeometryCatalog` is returned;
- no record is selected;
- no hash is trusted;
- no TASK-022 snapshot can be constructed.

## 16. Warnings

TASK-023 v1 has no warning channel.

Every violation of identity, schema, approval, source, license, permission,
provenance, dimension, or hash authority is a blocker.

Human-readable nominal labels may be empty without a warning because they are
optional metadata and not computation authority.

## 17. Future implementation repository boundary

A later implementation authorization may modify only the following paths:

```text
src/hexagent/shell_geometry_catalogs/__init__.py
src/hexagent/shell_geometry_catalogs/models.py
src/hexagent/shell_geometry_catalogs/blockers.py
src/hexagent/shell_geometry_catalogs/catalog.py
tests/shell_geometry_catalogs/_builders.py
tests/shell_geometry_catalogs/test_models.py
tests/shell_geometry_catalogs/test_catalog.py
tests/shell_geometry_catalogs/test_architecture.py
ci-shard-manifest.yml
```

This is a maximum allowlist, not authorization to modify every path.

The implementation must not modify:

- `src/hexagent/geometry_catalogs/**`;
- `tests/geometry_catalogs/**`;
- TASK-016 design or closed Issues;
- TASK-022 models, authority, validation, adapters, or tests;
- TASK-012 runtime or design;
- workflows;
- dependencies or lockfiles;
- public API;
- persistence;
- CLI;
- reports;
- production catalog artifacts.

### 17.1 Package-root exports

The future package root may export only:

```text
ShellGeometryCatalog
ShellGeometryRecord
ShellGeometryCatalogFailure
ShellGeometryCatalogBlockerCode
SHELL_GEOMETRY_CATALOG_BLOCKER_CODES
parse_shell_geometry_catalog
select_approved_shell_geometry
```

Internal constructors, hash helpers, ordering helpers, blocker builders, and
stage maps must not become package-root public API.

### 17.2 CI manifest boundary

A future implementation may append only these test modules to one existing
appropriate CI shard:

```text
tests/shell_geometry_catalogs/test_models.py
tests/shell_geometry_catalogs/test_catalog.py
tests/shell_geometry_catalogs/test_architecture.py
```

Expected manifest delta:

```text
+3
-0
```

No workflow change is authorized by the implementation boundary.

## 18. Frozen test expectations

The future implementation must test at least:

1. valid in-memory catalog parsing;
2. exact top-level field set;
3. exact record field set;
4. unsupported catalog schema;
5. unsupported record schema;
6. unsupported profile;
7. missing or invalid catalog ID/version/authority/source revision;
8. empty or invalid records array;
9. duplicate exact `geometry_id`;
10. exact `geometry_type == shell`;
11. exact `approval_state == approved`;
12. canonical positive `shell_inside_diameter_m`;
13. exponent, whitespace, plus sign, redundant zero, NaN, Infinity, zero, and
    negative rejection;
14. complete seven-field source binding;
15. closed source-class validation;
16. public-domain evidence validation;
17. open-license evidence validation;
18. internal-rule anti-disguise evidence;
19. derived-rule provenance requirement;
20. restricted-standard metadata-only rejection as selectable authority;
21. user-provided non-redistribution boundary;
22. vendor permission scope validation;
23. sorted unique permission references;
24. sorted unique provenance edge IDs;
25. sorted unique evidence references;
26. record hash recomputation;
27. record hash changes on diameter/source/approval/license changes;
28. record hash stability under input object key reordering;
29. nominal-label-only change does not change record hash;
30. canonical record ordering independent of input order;
31. catalog hash recomputation;
32. catalog hash changes when a record hash or catalog authority changes;
33. exact selection success;
34. unknown ID blocker;
35. unapproved selected-record blocker;
36. no nearest-size selection;
37. no first-fitting selection;
38. no revision auto-upgrade;
39. no filesystem, network, database, environment, clock, locale, or global
    registry access;
40. no import from TASK-016 runtime;
41. no import from TASK-022 runtime;
42. exact package-root exports;
43. exact closed 25-code blocker taxonomy;
44. deterministic blocker ordering;
45. same-stage multi-blocker accumulation;
46. no partial catalog return;
47. no production catalog artifact;
48. no restricted or vendor data in test builders;
49. CI manifest exact `+3/-0`;
50. repository changed-path allowlist.

All tests use in-memory synthetic values clearly marked as non-production test
data. Synthetic test values must never be described as approved engineering
sizes or reused as runtime catalog authority.

## 19. Architecture and security boundary

Future TASK-023 production modules must not:

- open files;
- scan directories;
- access network or database;
- read environment variables;
- call runtime clock;
- use locale-dependent parsing;
- mutate global registries;
- import optional external engineering packages;
- perform dynamic imports;
- execute code from catalog payloads;
- deserialize pickle or executable formats;
- evaluate expressions;
- log restricted source bodies;
- expose secrets or permission artifacts.

The pure parser consumes one already-loaded mapping. File loading and source
package acquisition remain outside this v1 runtime boundary and require
separate authority.

## 20. TASK-022 Slice B2 unlock conditions

TASK-022 Slice B2 remains blocked until all conditions are true:

1. this TASK-023 design contract is reviewed and merged;
2. TASK-023 runtime implementation is separately authorized, reviewed, merged,
   and post-merge CI succeeds;
3. at least one production shell catalog is separately source-defined;
4. every production record passes source, licensing, permission, provenance,
   approval, hash, and forbidden-content review;
5. the production catalog artifact is merged under explicit authorization;
6. runtime reverification confirms exact selection returns one approved record;
7. TASK-022 `ApprovedShellGeometrySnapshot` remains unchanged;
8. a new TASK-022 Slice B2 source-definition freezes the adapter input,
   projection, blockers, repository boundary, and tests;
9. Charles separately authorizes TASK-022 Slice B2 implementation.

No earlier step implies a later authorization.

## 21. Explicit non-scope

This design contract does not authorize:

- TASK-023 implementation;
- branch creation;
- commit or push;
- pull-request creation;
- production shell catalog data;
- fixture or golden authoring;
- source-package ingestion;
- restricted-standard or vendor content;
- TASK-016 mutation;
- TASK-022 mutation;
- TASK-022 Slice B2;
- automatic shell sizing or selection;
- shell outside diameter or wall thickness;
- pressure-vessel or mechanical adequacy;
- materials or corrosion allowance;
- baffle, pass partition, nozzle, or channel geometry;
- thermal rating;
- pressure drop;
- vibration or thermal expansion;
- mass, cost, optimization, procurement, or vendor availability;
- API, persistence, CLI, report, or user-interface work;
- workflow, dependency, or lockfile changes;
- TASK-024 through TASK-039 allocation;
- Issue #149 closure.

## 22. Design acceptance criteria

The design contract is eligible for later repository commit only when review
confirms:

1. exactly one design file is proposed;
2. TASK-023 remains independent from TASK-016;
3. TASK-022 frozen runtime is not modified;
4. exact schema and field sets are complete;
5. exact canonical decimal and hash rules are complete;
6. source, licensing, permission, provenance, and forbidden-content boundaries
   are complete;
7. source-data admission is separate from runtime framework implementation;
8. blocker taxonomy is closed and exact;
9. validation stages and ordering are exact;
10. future repository path allowlist is exact;
11. future tests are sufficient to enforce anti-fabrication and deterministic
    behavior;
12. no production shell-size value appears in the document;
13. no branch, commit, PR, implementation, or Issue closure is implied.

## 23. Next independent gates

The immediate next gate after Charles reviews this authored file is:

```text
AUTHORIZE_TASK023_DESIGN_FILE_BRANCH_COMMIT_ONLY
```

That gate may authorize:

- creation of one design branch from the reverified current `main`;
- addition of exactly
  `docs/tasks/TASK-023-approved-shell-geometry-catalog.md`;
- one design-only commit;
- no push and no pull request unless separately stated.

A later independent gate may authorize push and Draft PR creation.

Implementation, production source-data admission, TASK-022 Slice B2, Ready,
merge, and Issue close each require separate Charles authorization.
