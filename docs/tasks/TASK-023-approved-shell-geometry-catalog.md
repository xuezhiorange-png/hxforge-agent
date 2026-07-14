# TASK-023 — Approved Shell Geometry Catalog Authority Design Contract

> Design-only authority for the independent shell-geometry catalog required by
> TASK-022 Slice B2. No implementation, production catalog data, Ready, merge,
> Issue closure, TASK-016/TASK-022 mutation, or later-task allocation is authorized.

## 1. Authority and current review state

### 1.1 Historical authoring snapshot

| Field | Value |
|---|---|
| Issue | #149 |
| Source-definition gate | `AUTHORIZE_TASK023_SHELL_GEOMETRY_CATALOG_SOURCE_DEFINITION_AND_ALLOCATION_ONLY` |
| Authoring gate | `AUTHORIZE_TASK023_ONE_FILE_DESIGN_CONTRACT_AUTHORING_ONLY` |
| Allocation | `TASK-023 = Approved Shell Geometry Catalog Authority` |
| Authoring base | `main@39d4f66a3cb472b17db5c35f850fc7f31d9c1e28` |
| Authoring-time branch/commit/PR authority | NOT AUTHORIZED at that gate |

The last row is historical, not current repository state.

### 1.2 Current state

| Field | Value |
|---|---|
| Branch/commit gate | `AUTHORIZE_TASK023_DESIGN_FILE_BRANCH_COMMIT_ONLY` |
| Draft PR gate | `AUTHORIZE_TASK023_DRAFT_PR_CREATION_ONLY` |
| Audit gate | `AUTHORIZE_TASK023_PR150_DESIGN_AUDIT_AND_CI_REVIEW_ONLY` |
| Fixup gate | `AUTHORIZE_TASK023_PR150_DESIGN_FIXUP_ONLY` |
| Branch | `docs/task-023-approved-shell-geometry-catalog-design` |
| Initial head | `11a5dcba355db2f7b28251974ac00e0f29c6acee` |
| Pull request | #150 — OPEN / DRAFT |
| Allowed fixup path | `docs/tasks/TASK-023-approved-shell-geometry-catalog.md` only |
| Ready / merge / implementation / production data | NOT AUTHORIZED |
| TASK-016 / TASK-022 mutation; Issue #149 close | NOT AUTHORIZED |
| TASK-024 through TASK-039 | UNALLOCATED |

This fixup permits one commit changing this file only. It permits no PR metadata
mutation, Ready, merge, implementation, data admission, Issue closure, branch
deletion, review mutation, or later allocation.

## 2. Scope and dependency boundary

TASK-023 owns immutable approved shell records/catalogs, canonical
`shell_inside_diameter_m`, source/license/permission/provenance authority,
deterministic hashes/order, exact `geometry_id` lookup, and fail-closed blockers.

It does not own automatic sizing, nearest/next-larger/first-fit/ranking/fallback,
optimization, shell OD/wall/material/mechanical adequacy, baffles, thermal
rating, pressure drop, mass, cost, procurement, API, persistence, CLI, reports,
or TASK-022 core equations.

TASK-016 remains exactly `tube | pipe | hairpin`; TASK-023 must not widen,
reinterpret, import, or mutate it. TASK-022's frozen
`ApprovedShellGeometrySnapshot` remains unchanged:

```text
schema_version
geometry_id
geometry_type
revision
approval_state
shell_inside_diameter_m
record_hash
source_binding
snapshot_hash
```

TASK-023 does not construct that snapshot.

## 3. Anti-fabrication boundary

Forbidden: deriving shell authority from TASK-016 pipe/hairpin; inferring it
from TASK-021/TASK-022 geometry; remembered standard/vendor/project dimensions;
copied restricted tables/scans/figures; unpermissioned vendor data; synthetic
approved records; nominal-label computation; nearest/first-fit/default/ranking
or revision auto-upgrade; runtime filesystem/network/database/environment/clock/
locale/registry/dynamic-import/executable-deserialization dependence.

## 4. Closed constants and canonical rules

```text
CATALOG_SCHEMA_VERSION = task023.approved-shell-geometry-catalog.v1
RECORD_SCHEMA_VERSION = task023.approved-shell-geometry-record.v1
EVIDENCE_BUNDLE_SCHEMA_VERSION = task023.shell-authority-evidence-bundle.v1
PROFILE_ID = hxforge.shell_geometry_catalog.v1
GEOMETRY_TYPE = shell
APPROVAL_STATES = approved | pending | rejected | retired
SELECTABLE_APPROVAL_STATES = approved
```

Exact field sets apply; missing/unknown fields block. Raw types are validated
before coercion. Hash-bound values are canonical JSON only; binary floats,
runtime objects, NaN/Infinity, bytes, sets, datetime, and locale values are
forbidden.

`shell_inside_diameter_m` is a positive canonical decimal string in SI metres:
no exponent, plus sign, whitespace, redundant zeroes, NaN/Infinity, zero, or
negative value. The parser performs no unit, DN/NPS/schedule/gauge, nominal,
or vendor-label conversion. Sorted arrays reject duplicates before Unicode
code-point sorting.

## 5. Frozen domain model

### 5.1 `ShellSourceBinding`

Exact non-empty string fields:
`source_id`, `source_type`, `source_revision`, `source_location`,
`evidence_ref`, `approved_by`, `approved_at`. `approved_at` is recorded
authority, never runtime-now. This is the TASK-022 projection shape.

### 5.2 Closed source classes

```text
PUBLIC_DOMAIN
OPEN_LICENSE
USER_PROVIDED_LICENSED_SUMMARY
INTERNAL_ENGINEERING_RULE
DERIVED_ENGINEERING_RULE
REFERENCE_ONLY_RESTRICTED_STANDARD
VENDOR_PERMISSIONED
```

### 5.3 Approval-state reachability

- non-string or unknown state -> `SGC_APPROVAL_STATE_INVALID`;
- known `pending`, `rejected`, or `retired` during parse ->
  `SGC_RECORD_UNAPPROVED`;
- parser-bypassing non-approved object during exact selection ->
  `SGC_SELECTION_NOT_APPROVED`.

A successfully parsed catalog contains approved records only.

### 5.4 `ShellGeometryRecord`

Exact fields:

```text
schema_version
geometry_id
geometry_type
profile_id
revision
approval_state
shell_inside_diameter_m
nominal_label
source_class
license_evidence
source_binding
permission_evidence_refs
provenance_edge_ids
evidence_refs
record_hash
```

`geometry_type == shell`. Reference arrays are sorted/unique;
`evidence_refs` is non-empty. Stable ID:
`<catalog_id>/shell/<record_key>/<revision>`. No field represents shell OD,
wall, material, rating, code compliance, tolerance, schedule, baffles, mass,
cost, procurement, or availability.

### 5.5 `VendorPermissionEvidenceSnapshot`

Exact fields:
`permission_id`, `permission_scope`, `usage_scope`, `evidence_ref`,
`approved_by`, `approved_at`, `permission_hash`.
`permission_scope` is a sorted unique tuple of TASK-012 permission tokens;
`usage_scope` is the complete vendor-authorized runtime constraint;
`permission_hash` covers every other field.

### 5.6 `ProvenanceEdgeSnapshot`

Exact fields:
`edge_id`, `source_id`, `target_geometry_id`, `relation_type`,
`evidence_refs`, `edge_hash`. The hash covers every other field and target ID
must equal the referencing record ID.

### 5.7 `ShellAuthorityEvidenceBundle`

Exact fields:

```text
schema_version
bundle_id
bundle_version
approval_status
permission_evidence
provenance_edges
local_kernel_usage_scope
evidence_refs
task012_validation_hash
bundle_hash
```

The complete immutable bundle is supplied in memory. Permission/provenance
arrays are canonical and ID-unique. `bundle_hash` covers every other field
using complete `permission_hash`/`edge_hash` arrays.
`task012_validation_hash` binds upstream admission review but does not replace
runtime validation.

### 5.8 `ShellGeometryCatalog`

Exact fields:

```text
schema_version
catalog_id
catalog_version
profile_id
authority
source_revision
records
evidence_bundle_hash
catalog_hash
effective_at
```

Records are canonical/ID-unique. `evidence_bundle_hash` must equal the supplied
validated bundle hash. `effective_at` is explicit metadata or null, never
runtime-generated. No preferred series/default/fallback/ranking/fit/optimization
policy exists.

## 6. Hashing and ordering

Reuse repository canonical JSON.

- `record_hash`: every record field except itself and `nominal_label`;
- `permission_hash`: every permission field except itself;
- `edge_hash`: every edge field except itself;
- `bundle_hash`: every bundle field except itself, using ordered complete
  permission/edge hashes;
- `catalog_hash`: every catalog field except itself, including bundle hash and
  ordered record hashes.

All are lowercase 64-character SHA-256 hex. Order:
records `(geometry_id, revision, record_hash)`;
permissions `(permission_id, permission_hash)`;
provenance `(edge_id, edge_hash)`.
A referenced payload change must change its own hash, bundle hash, and catalog
hash. References alone never constitute authority.

## 7. TASK-012 compatibility

Engineering approval and license/permission authority both must pass.
Public-domain/open-license/internal/derived/user-provided/restricted-reference/
vendor-permissioned dispositions follow TASK-012; restricted references are
metadata-only, non-redistributable user content cannot enter a public production
catalog, and vendor records require complete permission evidence.

Normative terms:

```text
vendor_permission_evidence.permission_scope
vendor_permission_evidence.usage_scope
local_kernel_usage_scope
```

For public repository records, `permission_scope` must include
`repository_storage` and `repository_redistribution`. Runtime verifies complete
`usage_scope` against bundle `local_kernel_usage_scope`.
`local_kernel_usage` is not a permission token. Public record-body emission
requires separate permission; TASK-023 v1 emits none.

The parser receives the complete evidence bundle in memory, resolves every
permission/provenance reference exactly once, verifies hashes and targets, and
applies TASK-012 permission/usage gates without external lookup.

## 8. Source-data admission

Framework code without production records is authority-incomplete and does not
unblock TASK-022 B2. Production admission separately freezes artifact path/
format, catalog identity, exact records, sources, bindings, licenses, complete
permission/provenance snapshots, local usage policy, approval, hashes,
TASK-012 validation, forbidden-content review, CI, storage, redistribution, and
runtime use. Placeholder/demo/remembered/test data cannot become production
authority.

## 9. Frozen operations

```python
parse_shell_geometry_catalog(
    *, raw_catalog: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any],
) -> ShellGeometryCatalog

select_approved_shell_geometry(
    *, catalog: ShellGeometryCatalog,
    geometry_id: str,
) -> ShellGeometryRecord
```

The parser validates both in-memory mappings and returns no partial catalog.
Selection is exact ID only; no scan, nearest, first-fit, fallback, default,
ranking, optimization, or TASK-022 snapshot construction.

## 10. Closed blocker taxonomy

Exactly these 25 codes exist:

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

No alias/fallback/reserved/warning repurposing. Malformed or class-incompatible
license -> `SGC_LICENSE_BLOCKED`; missing permission/scope or usage/local-scope
mismatch -> `SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE`; unresolved/hash/target
provenance failure -> `SGC_PROVENANCE_INCOMPLETE`.

## 11. Validation order

Parser stages: raw types; exact top fields; schemas/profiles/IDs/versions/
authority; bundle approval/TASK-012 hash/bundle hash; permission snapshots;
provenance snapshots; records array; record fields; identity/duplicates/type/
profile/revision; approval lexical check; known non-approved rejection; decimal;
source binding; source class/license; permission/provenance resolution and local
usage gate; evidence arrays; record hashes; record ordering; catalog-bundle
binding; catalog hash.

Selection stages: raw ID; exact lookup; defensive approval recheck.

Blocked stages gate dependents; independent same-stage blockers accumulate.
Order:
`(stage_rank, code, field_path or "", message_key,
sha256(canonical_json(details)), sha256(canonical_json(evidence_refs)))`.
Any blocker returns no catalog, selection, trusted hash, or TASK-022 snapshot.
There is no warning channel.

## 12. Future implementation and tests

Maximum paths:

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

CI manifest delta exactly `+3/-0`; no workflow change. Package exports only:
`ShellGeometryCatalog`, `ShellGeometryRecord`,
`ShellGeometryCatalogFailure`, `ShellGeometryCatalogBlockerCode`,
`SHELL_GEOMETRY_CATALOG_BLOCKER_CODES`,
`parse_shell_geometry_catalog`, `select_approved_shell_geometry`.

Tests must cover exact schemas; canonical decimals; four approval states and
three-blocker reachability; all source classes; exact TASK-012 permission/
usage/local-scope semantics; evidence resolution/targets/duplicates/hashes;
record/permission/edge/bundle/catalog hashes; deterministic ordering; exact
selection and prohibited alternatives; closed 25-code/stage/blocker order;
same-stage accumulation/no partial result; architecture restrictions; exports,
path allowlist, CI delta; and absence of production/restricted/vendor data.
All dimensions are synthetic non-production test data.

## 13. TASK-022 B2 unlock and next gate

B2 requires: this design merged; separately authorized TASK-023 framework
merged with post-merge CI; separately admitted production catalog plus complete
evidence bundle; all authority reviews passed; production artifact explicitly
merged; runtime exact-selection reverified; TASK-022 snapshot unchanged; new B2
source-definition; and separate Charles implementation authorization.

A PASS re-audit must confirm the four audit corrections, one-file scope,
TASK-016/022 non-mutation, unchanged 25-code taxonomy, deterministic contract,
adequate tests, no production dimensions, and no implied later authorization.

Next gate:

```text
AUTHORIZE_TASK023_PR150_FIXUP_REAUDIT_ONLY
```

Only after PASS may PR metadata sync, Ready, or merge be separately authorized.
