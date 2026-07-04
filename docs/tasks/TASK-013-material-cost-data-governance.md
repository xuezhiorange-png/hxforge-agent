# TASK-013 — Material and cost data governance

## 1. Purpose and governance scope

TASK-013 establishes the **governance boundary** under which HXForge
may acquire, normalize, version, license, audit, and consume material
property data and cost data, without committing any restricted source
body (standard text, vendor catalog body, restricted price list,
restricted material property table, scanned page, formula image, or
copyrighted excerpt) into the repository or its deliverables.

TASK-013 freezes seven interlocking governance objects:

1. A **source-class taxonomy** that classifies every material record
   and every cost record by where it came from and what license
   posture it carries.
2. A **material data record model** that gives every material record a
   stable identity, a version, a hash, and an audit trail.
3. A **cost data record model** that gives every cost record a stable
   identity, a version, a hash, and an audit trail.
4. A **license boundary** parallel to TASK-012's rule-pack license
   boundary, but specialized for material and cost sources.
5. A **deterministic selection rule** that constrains how the future
   engineering runtime may resolve "which material record applies" and
   "which cost record applies", without authorizing the runtime
   implementation in this design.
6. A **review and approval workflow** that gates every record before it
   may enter a runtime catalog.
7. A **CI validation boundary** that constrains what future CI may
   check, without authorizing CI implementation in this design.

The contract does NOT authorize any code, test, CI workflow, runtime
material selector, runtime cost selector, material database, cost
model, pressure-drop computation, C4 engine, shell-and-tube /
plate / air-cooler / two-phase / refrigerant production capability, or
any persistence / migration / API / CLI artifact.

## 2. Current authority and prerequisites

```text
TASK-011 design:                    DONE / FROZEN
TASK-011 implementation:            DONE / MERGED
TASK-011 closeout docs PR:          DONE / MERGED
TASK-012 design:                    DONE / FROZEN
TASK-012 implementation:            DONE / MERGED / VERIFIED / CLOSED
TASK-012 closeout docs PR (#45):    MERGED
Issue #36 (TASK-011 impl):          CLOSED
Issue #43 (TASK-012 impl):          CLOSED / completed
Main HEAD at TASK-013 design:       56e7ec01d54fb938ac1c4c14b318eb34b03e3f86
TASK-013 design Issue:              #46 — OPEN
TASK-013 implementation:            NOT AUTHORIZED
TASK-014 through TASK-015A:         NOT AUTHORIZED
TASK-016 through TASK-019:          NOT AUTHORIZED
TASK-020+ (shell-and-tube/plate/air-cooler/two-phase): NOT AUTHORIZED
```

Frozen prerequisite contracts (binding for TASK-013 design):

- `docs/tasks/TASK-011-benchmark-case-governance.md` — governs how
  benchmark cases cite standards and engineering assumptions. Material
  and cost records used inside a benchmark case inherit the
  benchmark case's source-class and license posture; they may NOT
  relax it.
- `docs/tasks/TASK-012-standards-rule-pack-license-boundary.md` —
  freezes the source-class taxonomy, license boundary model,
  provenance graph model, and canonical hashing model that TASK-013
  re-uses for material and cost records. TASK-013 does NOT redefine
  those mechanisms; it specializes them for the material / cost data
  shapes and adds record-specific fields.

The TASK-013 design contract MUST be reviewed and frozen (with a
dedicated SHA) before any TASK-013 implementation may begin.

## 3. Definitions

- **Material record** — a structured engineering description of one
  material / grade / form-factor combination, including its identity,
  metadata, license posture, and (where applicable) structured
  engineering-properties metadata. Material records describe
  *availability*, *form*, *normative reference*, and (in metadata
  form only) engineering properties — they MUST NOT embed restricted
  property tables, vendor catalog bodies, or scanned pages.
- **Cost record** — a structured engineering description of one cost
  datum (unit price, cost basis, escalation assumption, etc.) attached
  to a material record, a process step, or a project input. Cost
  records describe *price posture* and *currency semantics*; they
  MUST NOT embed restricted price lists, vendor quote bodies, or
  paid-vendor catalog excerpts.
- **Source class** — a closed enumeration token classifying where a
  record came from and what license posture it carries. Section 4
  freezes the source-class taxonomy for material and cost records.
- **License evidence** — REQUIRED token identifying the controlled
  form under which a record may be stored, redistributed, or
  consumed at runtime. Re-uses TASK-012 Section 7.2 evidence forms.
- **Approval state** — frozen state machine inherited from TASK-012
  Section 14. Material and cost records MUST traverse the same
  approval ladder as standards rules; the runtime may NOT consume a
  record whose `approval_state != approved`.
- **Record hash** — content-addressable SHA-256 hex digest computed
  over the record's canonical JSON form, identical to TASK-012
  Section 13. Re-uses the shared canonical JSON helper.
- **Supersession** — directed `supersedes` / `superseded_by` relation
  modeled exactly like TASK-012 Section 11 supersedes edges, applied
  to material and cost records. A record with `superseded_by`
  populated MUST NOT be selected by future runtime selectors.

## 4. Source classes and source authority hierarchy

Material records and cost records each carry ONE `source_class` token.
The taxonomy is intentionally **separate** from the seven
TASK-012 rule source classes; the rule-pack runtime may consume
material and cost records, but material and cost records are NOT
themselves rule-packs.

Frozen source-class taxonomy for TASK-013 (closed set):

| Token                        | Meaning                                                                                                                                          | License posture                                |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| `INTERNAL_ENGINEERING_ASSUMPTION` | Values chosen by HXForge engineering review (e.g. default density for an unspecified material grade) when no external source is cited.             | `project_internal_authority`                   |
| `PUBLIC_METADATA`            | Public, non-restricted metadata such as generic unit-conversion factors, public-region CPI indices, or generic engineering assumption envelopes.  | SPDX / `public_domain`                         |
| `VENDOR_PERMISSIONED`        | A vendor-provided datum where the vendor has granted explicit permission to record metadata and (where licensed) fielded summary fields.        | `permission_evidence_pointer` + scope tokens   |
| `USER_PROVIDED_PROJECT_DATA` | Project-specific values supplied by the user / engineer for this project only; not redistributed.                                                | `permission_evidence_pointer` (project-scoped) |
| `RESTRICTED_REFERENCE_METADATA_ONLY` | A restricted source (paid standard, vendor catalog, paid database) where ONLY bibliographic metadata, clause locator, source identity, and (where licensed) fielded metadata may be recorded. | `metadata_only` (body MUST be absent)          |

Source authority hierarchy (highest → lowest) — used by future
deterministic selection only:

1. `USER_PROVIDED_PROJECT_DATA` (project-scoped override wins over all
   generic sources for the same record id, region, and effective
   date).
2. `VENDOR_PERMISSIONED` (only if its `permission_scope` includes
   `usage_scope`; otherwise it MUST be treated as
   `RESTRICTED_REFERENCE_METADATA_ONLY`).
3. `INTERNAL_ENGINEERING_ASSUMPTION`.
4. `PUBLIC_METADATA`.
5. `RESTRICTED_REFERENCE_METADATA_ONLY` (metadata-only; runtime MUST
   NOT consume any numeric property value from this class).

The hierarchy is **selection priority only**. It does NOT override
license posture; a record whose license posture forbids runtime
consumption remains forbidden regardless of its priority rank.

## 5. Material data record model

A material record is a single JSON object with the following
top-level fields. All field names are fixed; future extension is a
contract revision.

| Field                          | Type                | Required | Notes                                                                                                                          |
|--------------------------------|---------------------|----------|--------------------------------------------------------------------------------------------------------------------------------|
| `material_record_id`           | string              | yes      | Stable opaque identifier. MUST be unique across the entire project.                                                            |
| `material_record_version`      | semver string       | yes      | Semver-compatible.                                                                                                             |
| `material_family`              | enum string         | yes      | Frozen closed set; see Section 5.1.                                                                                            |
| `material_grade_or_designation`| string              | yes      | Vendor / standard / internal designation, e.g. `"SA-106-B"`, `"316L"`, `"INTERNAL-default-CS"`.                                |
| `form_factor`                  | enum string         | yes      | Frozen closed set; see Section 5.2.                                                                                            |
| `standard_or_spec_reference`   | object              | no       | Metadata only; see Section 5.3. NEVER stores standard body text.                                                               |
| `region`                       | string              | yes      | ISO 3166-1 alpha-2 or `"INTL"`.                                                                                               |
| `effective_date`               | RFC 3339 UTC string | yes      | When this record became authoritative.                                                                                         |
| `retirement_date`              | RFC 3339 UTC string | no       | If present, record MUST NOT be selected after this date.                                                                       |
| `source_class`                 | enum string         | yes      | One of Section 4 tokens.                                                                                                       |
| `source_reference`             | string              | yes      | Metadata pointer (URI or internal pointer). NEVER stores source body.                                                          |
| `license_evidence`             | string              | yes      | One of the four TASK-012 Section 7.2 evidence forms.                                                                          |
| `engineering_properties`       | object              | no       | Metadata-only property schema; see Section 5.4. NEVER stores restricted property tables.                                       |
| `dimensional_units`            | object              | yes      | Maps every numeric metadata field in this record to its declared unit. See Section 10.                                          |
| `quality_flags`                | array of strings    | yes      | Frozen enum; see Section 12.                                                                                                   |
| `uncertainty`                  | object              | no       | See Section 12.                                                                                                               |
| `approval_state`               | enum string         | yes      | Frozen TASK-012 Section 14 ladder. Runtime may only consume `approved`.                                                        |
| `supersedes`                   | array of strings    | no       | Material record ids this record replaces.                                                                                      |
| `superseded_by`                | string              | no       | Material record id that replaces this record. If populated, runtime MUST NOT select this record.                               |
| `provenance_edges`             | array of strings    | yes      | Edge ids into the shared provenance graph (TASK-012 Section 11).                                                               |
| `human_entered_evidence`       | object              | no       | Required when `source_class` is `USER_PROVIDED_PROJECT_DATA`, `INTERNAL_ENGINEERING_ASSUMPTION`, or `VENDOR_PERMISSIONED`.     |
| `record_hash`                  | 64-char hex string  | yes      | SHA-256 of the canonical JSON form with `record_hash` field excluded. See Section 16.                                          |

### 5.1 `material_family` closed set

`carbon_steel`, `low_alloy_steel`, `stainless_steel`, `duplex_stainless`,
`nickel_alloy`, `copper_alloy`, `aluminium_alloy`, `titanium_alloy`,
`plastic`, `elastomer`, `ceramic`, `graphite`, `glass`, `composite`,
`refrigerant`, `process_fluid`, `utility_fluid`, `other`.

### 5.2 `form_factor` closed set

`plate`, `sheet`, `bar`, `billett`, `tube`, `pipe`, `fitting`,
`flange`, `forging`, `casting`, `brazed_assembly`, `welded_assembly`,
`gasket`, `fastener`, `fluid_bulk`, `fluid_charge`, `other`.

The `form_factor` enum is **metadata only**. It does NOT authorize any
specific geometry-corpus work. Geometry catalogs for tubes, pipes,
plates, gaskets, etc. are TASK-016 work and are NOT authorized by
TASK-013.

### 5.3 `standard_or_spec_reference` metadata schema

```text
standard_or_spec_reference: {
  issuing_body:           <enum, see Section 5.3.1>,
  designation:            <string, e.g. "ASME SA-106">,
  edition_year:           <int | null>,
  clause_locator:         <string | null>,    // e.g. "Section II Part A"
  bibliographic_metadata: <object, free-form metadata>
}
```

The field MAY carry bibliographic pointers (issuing body,
designation, edition year, clause locator). It MUST NOT carry any
text body, table body, figure reproduction, or scanned page.

#### 5.3.1 `issuing_body` closed set

`ASME`, `ASTM`, `ISO`, `EN`, `GB`, `JIS`, `DIN`, `NFPA`, `TEMA`, `API`,
`AWS`, `ASHRAE`, `IIAR`, `EIGA`, `INTERNAL`, `OTHER`.

`OTHER` requires a free-text justification in
`standard_or_spec_reference.bibliographic_metadata.justification`.

### 5.4 `engineering_properties` metadata schema

`engineering_properties` is a metadata dictionary keyed by canonical
property names. Each value is a metadata descriptor, NOT a numeric
quantity:

```text
engineering_properties: {
  "<canonical_property_name>": {
    declared_unit:           <string, see Section 10>,
    declared_envelope:       <object | null>,  // applicability envelope metadata
    declared_source_pointer: <string | null>,  // bibliographic pointer only
    declared_quality_flags:  <array of strings, see Section 12>,
    declared_uncertainty:     <object | null>
  },
  ...
}
```

Engineering property **values themselves** (e.g. `yield_strength =
250 MPa`) MUST NOT be stored when the source posture is
`RESTRICTED_REFERENCE_METADATA_ONLY`. The runtime may consume
property values only from records whose `source_class` is in
{`INTERNAL_ENGINEERING_ASSUMPTION`, `PUBLIC_METADATA`,
`VENDOR_PERMISSIONED` (with `usage_scope`),
`USER_PROVIDED_PROJECT_DATA`}.

## 6. Cost data record model

A cost record is a single JSON object with the following top-level
fields. All field names are fixed.

| Field                  | Type                | Required | Notes                                                                                                                                       |
|------------------------|---------------------|----------|---------------------------------------------------------------------------------------------------------------------------------------------|
| `cost_record_id`       | string              | yes      | Stable opaque identifier.                                                                                                                  |
| `cost_record_version`  | semver string       | yes      | Semver-compatible.                                                                                                                          |
| `cost_category`        | enum string         | yes      | Frozen closed set; see Section 6.1.                                                                                                         |
| `cost_basis`           | enum string         | yes      | Frozen closed set; see Section 6.2.                                                                                                         |
| `currency`             | string              | yes      | ISO 4217 alphabetic code (`USD`, `EUR`, `CNY`, …).                                                                                          |
| `region`               | string              | yes      | ISO 3166-1 alpha-2 or `"INTL"`.                                                                                                             |
| `effective_date`       | RFC 3339 UTC string | yes      | When this record became authoritative.                                                                                                       |
| `escalation_date`      | RFC 3339 UTC string | no       | Reference date used for escalation index computation. See Section 11.                                                                       |
| `quantity_basis`       | enum string         | yes      | What the unit price is normalized to. See Section 6.3.                                                                                       |
| `unit_basis`           | string              | yes      | SI unit string for the quantity basis, e.g. `"kg"`, `"m"`, `"m2"`, `"ea"`, `"kWh"`. See Section 10.                                          |
| `source_class`         | enum string         | yes      | One of Section 4 tokens.                                                                                                                   |
| `source_reference`     | string              | yes      | Metadata pointer (URI or internal pointer). NEVER stores restricted price-list body.                                                       |
| `license_evidence`     | string              | yes      | One of the four TASK-012 Section 7.2 evidence forms.                                                                                       |
| `uncertainty_band`     | object              | no       | See Section 12.                                                                                                                            |
| `quality_flags`        | array of strings    | yes      | Frozen enum; see Section 12.                                                                                                                |
| `approval_state`       | enum string         | yes      | Frozen TASK-012 Section 14 ladder. Runtime may only consume `approved`.                                                                     |
| `supersedes`           | array of strings    | no       | Cost record ids this record replaces.                                                                                                       |
| `superseded_by`        | string              | no       | Cost record id that replaces this record. If populated, runtime MUST NOT select this record.                                                |
| `provenance_edges`     | array of strings    | yes      | Edge ids into the shared provenance graph.                                                                                                  |
| `human_entered_evidence`| object             | no       | Required when `source_class` is `USER_PROVIDED_PROJECT_DATA` or `VENDOR_PERMISSIONED`.                                                       |
| `record_hash`          | 64-char hex string  | yes      | SHA-256 of the canonical JSON form with `record_hash` field excluded. See Section 16.                                                       |

### 6.1 `cost_category` closed set

`material_unit_price`, `material_total_cost`,
`fabrication_labor`, `fabrication_overhead`, `installation_labor`,
`engineering_hours`, `transportation`, `taxes_and_duties`,
`operating_energy`, `operating_utility`, `maintenance`, `insurance`,
`decommissioning`, `compliance_permit`, `other`.

### 6.2 `cost_basis` closed set

`vendor_quote` (single vendor), `vendor_catalog_listing` (catalog
list price, NOT the full catalog body), `internal_assumption`,
`public_index` (e.g. CPI), `project_specific_input`,
`engineering_estimate` (engineering-judgement estimate), `other`.

### 6.3 `quantity_basis` closed set

`per_mass`, `per_length`, `per_area`, `per_volume`, `per_unit`,
`per_energy`, `per_time`, `lump_sum`, `other`.

Cost record **fielded body** (e.g. `unit_price = 4.20 USD/kg`,
`escalation_index_reference = BLS-WPU-101700`) MAY be recorded only
when the source posture is in {`INTERNAL_ENGINEERING_ASSUMPTION`,
`PUBLIC_METADATA`, `VENDOR_PERMISSIONED` (with `usage_scope`),
`USER_PROVIDED_PROJECT_DATA`}. For
`RESTRICTED_REFERENCE_METADATA_ONLY`, only the metadata fields above
are permitted; numeric unit-price values MUST be absent.

## 7. Identity, versioning, supersession and retirement

Identity:

- `material_record_id` and `cost_record_id` are stable opaque strings
  allocated by engineering review. Once allocated, they are never
  reused.
- The same `material_record_id` MUST NOT appear under two distinct
  `material_record_version` simultaneously in any approved set.

Versioning:

- `material_record_version` and `cost_record_version` are
  semver-compatible.
- Backwards-incompatible metadata changes (new mandatory fields,
  tightened enum values, license posture tightening) require a major
  version bump and MUST be linked to a `supersedes` edge.
- Backwards-compatible additions (new optional fields, looser
  approvals) require a minor version bump.

Supersession:

- A new record may declare `supersedes: [<old_record_id>, ...]`. The
  old records MUST set `superseded_by: <new_record_id>`.
- The provenance graph MUST contain a `supersedes` edge (TASK-012
  Section 11 model) between the two records.

Retirement:

- A record whose `retirement_date` is in the past MUST NOT be selected
  by future runtime selectors.
- A retired record remains in the catalog for audit; it carries
  `superseded_by` populated.

## 8. Provenance and evidence requirements

Every material record and every cost record MUST carry at least one
`provenance_edges` entry pointing into the shared provenance graph
defined in TASK-012 Section 11.

- For `INTERNAL_ENGINEERING_ASSUMPTION` records: at least one
  `derived_from` edge into an internal handbook entry.
- For `PUBLIC_METADATA` records: at least one `paraphrases` edge into
  the public source identity.
- For `VENDOR_PERMISSIONED` records: at least one `licensed_from` edge
  into the permission-evidence pointer.
- For `USER_PROVIDED_PROJECT_DATA` records: at least one `entered_by`
  edge into the user / engineer identity and project id.
- For `RESTRICTED_REFERENCE_METADATA_ONLY` records: at least one
  `references` edge into the bibliographic identity. The edge body
  MUST NOT contain any restricted content.

The provenance graph itself is governed by TASK-012 Section 11 and
SHOULD NOT be re-frozen here.

## 9. License, redistribution and attribution boundaries

The TASK-012 Section 5 license boundary model applies verbatim to
material and cost records. The four controlled `license_evidence`
forms from TASK-012 Section 7.2 are the only allowed forms.

Additional TASK-013-specific boundary rules:

- **Standard bodies, vendor catalog bodies, paid price lists,
  restricted property tables, scanned pages, and copyrighted
  formula images MUST NOT be embedded** in any material or cost
  record field.
- A material or cost record MAY carry a `source_reference` URI
  pointing to the *identity* of a restricted source. It MUST NOT
  carry the body.
- `RESTRICTED_REFERENCE_METADATA_ONLY` records MUST NOT carry any
  numeric property value, any numeric unit price, or any quoted text
  beyond bibliographic metadata. The body slot is either absent or
  restricted to bibliographic keys (`issuing_body`, `designation`,
  `edition_year`, `clause_locator`, `bibliographic_metadata`).
- `VENDOR_PERMISSIONED` cost records MUST record
  `permission_scope` exactly as TASK-012 Section 4.2 / Section 16.3a
  demand (the same scope token vocabulary applies).
- Material and cost records that would otherwise be exported into a
  public artifact (e.g. a public report) MUST have
  `public_artifact_allowed` in their permission scope or MUST be
  filtered out before emission. This applies to
  `VENDOR_PERMISSIONED` records; other source classes either carry no
  scope requirement or are project-scoped and therefore not exportable.

## 10. Unit normalization and dimensional validation

- Every numeric metadata field in a material record MUST appear in
  `dimensional_units` with a declared SI unit string.
- Every numeric metadata field in a cost record MUST appear in the
  declared `unit_basis` SI string.
- Future CI (NOT this contract) SHALL reject any record whose numeric
  metadata carries a unit that is not in the project's SI unit set, or
  whose `dimensional_units` declares a unit that the record does not
  use.
- Records MUST NOT embed alternate-unit numerics ("MPa" vs "ksi"). The
  runtime stores SI; alternate-unit conversions are a presentation
  concern handled outside the catalog.

## 11. Currency, region, date and escalation semantics

- `currency` MUST be a valid ISO 4217 alphabetic code at the time of
  record creation. Future CI MAY reject records whose currency is not
  recognized.
- `region` MUST be ISO 3166-1 alpha-2 or `"INTL"`.
- `effective_date` is the date when the record became authoritative.
  It MUST be RFC 3339 UTC with `Z` suffix.
- `escalation_date` is OPTIONAL. When present, it represents the
  reference date used for cost escalation index computation; the
  escalation index itself is a separate `PUBLIC_METADATA` cost record
  (`cost_category=operating_energy` or
  `cost_category=operating_utility`, `cost_basis=public_index`).
- Records with `escalation_date` MUST declare
  `escalation_index_reference` as a `source_reference` pointer to the
  public index record. The runtime MUST NOT embed escalation math in
  the cost record itself.

## 12. Uncertainty, confidence and quality flags

- `quality_flags` is REQUIRED. Frozen enum:
  `assumed_value`, `engineering_estimate`, `field_measured`,
  `vendor_certified`, `third_party_tested`, `stale_>5y`,
  `pending_review`, `metadata_only_no_value`,
  `escalation_uncertain`, `currency_conversion_inferred`,
  `region_proxy_used`.
- `uncertainty` and `uncertainty_band` are OPTIONAL objects. When
  present, they follow the same schema conventions as TASK-012
  Section 12 (envelope metadata + notes), not numeric confidence
  intervals that would require restricted source body.
- A record whose only quality flag is `metadata_only_no_value` is
  classified as `RESTRICTED_REFERENCE_METADATA_ONLY` regardless of
  what other metadata says.

## 13. Review and approval workflow

The TASK-012 Section 14 frozen approval ladder applies verbatim:

`draft` → `needs_source` → `needs_license_evidence` →
`needs_normalization` → `needs_expected_outputs` → `under_review` →
`approved` / `rejected` / `superseded`.

Additional TASK-013-specific requirements:

- A material or cost record MUST NOT enter `under_review` unless its
  `provenance_edges` is non-empty and `dimensional_units` /
  `unit_basis` are present.
- An approver MUST verify that no restricted content is embedded in
  any field. CI (future, NOT this contract) MAY support this with a
  forbidden-token / fingerprint scanner; the contract specifies the
  intent, not the implementation.

## 14. Deterministic selection rules

Future runtime selectors (NOT this contract) MUST follow this
deterministic algorithm when resolving "which material record applies"
or "which cost record applies" for a given (record id, region, time):

1. Reject any candidate whose `approval_state != approved`.
2. Reject any candidate whose `superseded_by` is populated.
3. Reject any candidate whose `retirement_date` (if present) is in
   the past.
4. Reject any candidate whose `source_class` is
   `RESTRICTED_REFERENCE_METADATA_ONLY`.
5. Reject any candidate whose license posture forbids runtime
   consumption.
6. Rank remaining candidates by source-authority priority (Section 4)
   — user > vendor (with `usage_scope`) > internal > public.
7. Within the same priority rank, rank by `effective_date` DESC
   (newest first).
8. Within the same priority and date, rank by `record_version` DESC.
9. Within the same priority, date, and version, rank by
   `material_record_id` / `cost_record_id` lexicographic ASC.
10. If zero candidates remain, the selection MUST fail closed with a
    structured `MaterialNotFound` or `CostNotFound` error referencing
    the record id, region, and time.

The deterministic tie-breaker chain (priority → date → version →
record id) guarantees bit-identical output across replays and across
machines, provided the underlying catalog and selectors are bit-
identical.

## 15. Validation failures, blockers and warnings

Validation failures (blockers):

- Missing required field.
- Unknown enum value for any closed-set field.
- `record_hash` mismatch.
- Mismatch between record identity and provenance edge endpoints.
- Numeric metadata declared in `dimensional_units` / `unit_basis`
  but not present in record.
- Restricted content detected by future scanner (NOT this contract).

Warnings (non-blocking):

- `quality_flags` contains `assumed_value` or `engineering_estimate`.
- `effective_date` older than five years AND no `supersedes` edge.
- Currency code present but `escalation_index_reference` is absent
  while `escalation_date` is present.

The implementation SHALL distinguish blockers from warnings
structurally. Future CI SHALL NOT downgrade a blocker to a warning.

## 16. Canonical serialization and hashing

- Material records and cost records are serialized using the same
  canonical JSON helper frozen by TASK-012 Section 13 and used by
  TASK-011 benchmark cases.
- `record_hash` is `sha256_hex(canonical_json(record_without_hash))`
  where `record_without_hash` is the record dict with the
  `record_hash` field removed before canonicalization.
- Hashing is content-addressable: identical record bodies MUST yield
  identical `record_hash` across machines and replays.

## 17. Audit trail and revision history

Every state transition of a material or cost record (`approval_state`
change, `superseded_by` population, license posture change, retirement)
MUST be captured in an immutable audit log keyed by `record_id` and
`record_version`. The audit log is a separate artifact from the
record itself; it is governed by TASK-012 Section 11 provenance
model.

## 18. Internal seed examples policy

The TASK-013 design contract does NOT commit any seed records in this
PR. If a future implementation seeds the catalog, the seed MUST obey:

- Every seeded record's `source_class` MUST be in
  {`INTERNAL_ENGINEERING_ASSUMPTION`, `PUBLIC_METADATA`,
  `USER_PROVIDED_PROJECT_DATA`}.
- Seeded records MUST carry `forbidden_content_marker_check = []`.
- Seeded records MUST carry `license_evidence =
  project_internal_authority` or a public-domain / SPDX form.
- No standard body, vendor catalog body, restricted price list, or
  restricted material property table MAY appear in any seed.

## 19. Future implementation file boundary

If and only if a future TASK-013 implementation is separately
authorized, it MAY create the following paths. This contract does NOT
authorize creating them now:

```text
src/hexagent/material_costs/
src/hexagent/material_costs/__init__.py
src/hexagent/material_costs/models.py
src/hexagent/material_costs/schema.py
src/hexagent/material_costs/loader.py
src/hexagent/material_costs/selection.py
src/hexagent/material_costs/license_boundary.py
src/hexagent/material_costs/validation.py
src/hexagent/material_costs/validate.py
tests/material_costs/
tests/material_costs/test_material_record_schema.py
tests/material_costs/test_cost_record_schema.py
tests/material_costs/test_license_boundary.py
tests/material_costs/test_selection.py
tests/material_costs/test_validation.py
rule_packs/material_cost_seed/         # only permitted seed paths
benchmarks/material_cost_cases/        # only if future TASK covers it
ci/material_costs/                     # only if future CI is authorized
```

The actual implementation PR MUST list its own file additions
explicitly; the paths above are an upper-bound envelope, not a
guaranteed minimum.

This contract does NOT create any of these paths. The current PR
touches only `docs/tasks/TASK-013-material-cost-data-governance.md`
and `docs/TASK_BACKLOG.md`.

## 20. Required test strategy for later implementation

A future TASK-013 implementation MUST add (at minimum):

- Schema tests asserting every required field of a material record
  and a cost record is present and valid.
- License-boundary tests mirroring TASK-012 tests, specialized for
  `RESTRICTED_REFERENCE_METADATA_ONLY` body rejection and for
  numeric-value rejection in metadata-only records.
- Hash determinism tests asserting
  `sha256_hex(canonical_json(record_without_hash))` is identical
  across replays, and across machines.
- Selection determinism tests asserting the priority → date →
  version → record-id tie-break chain yields bit-identical output.
- Provenance tests asserting each record has at least one valid edge
  into the shared graph.
- Audit-trail tests asserting every state transition is captured.
- End-to-end validator tests analogous to TASK-012's `validate.py`
  CLI tests, but specialized for material and cost records.

Tests MUST NOT embed restricted content as fixtures.

## 21. Explicit non-goals

The TASK-013 design contract does NOT cover:

- Any persistence layer, database migration, ORM, or schema snapshot.
- Any HTTP / RPC / CLI / API surface.
- Any material database content beyond the metadata schema.
- Any cost model beyond the metadata schema.
- Any pressure-drop computation, C4 engine, shell-and-tube /
  plate / air-cooler / two-phase / refrigerant logic.
- Any engineering equation, correlation, or constant value.
- Any runtime selection code (only the deterministic algorithm is
  frozen here).
- Any future CI workflow beyond the validation intent.
- Any vendor catalog body, restricted price list, or restricted
  material property table, in any form.
- Any TASK-014+ work.

## 22. Acceptance checklist

A future implementation PR that claims TASK-013 implementation MUST
demonstrate, at minimum:

1. Every file under `src/hexagent/material_costs/` and
   `tests/material_costs/` is listed in the PR body.
2. `docs/tasks/TASK-013-material-cost-data-governance.md` is
   unchanged from the SHA recorded in this contract's freeze marker.
3. `docs/tasks/TASK-011-benchmark-case-governance.md` is unchanged.
4. `docs/tasks/TASK-012-standards-rule-pack-license-boundary.md` is
   unchanged.
5. `benchmarks/cases/` and `benchmarks/manifests/` are unchanged.
6. `.github/workflows/` is unchanged (or limited to a new workflow
   explicitly authorized separately).
7. CI run (PR-head + merge-ref + main post-merge) is green.
8. Review verdict is `PASS` with no open P0 or P1 blockers.
9. Issue #46 (TASK-013 design) closeout comment is posted before any
   implementation Issue / PR is opened.
10. TASK-013 implementation Issue is created with explicit user
    authorization scope; TASK-013 implementation PR is opened only
    after that Issue is opened and the design SHA is referenced.
11. No seeded record violates the Section 18 seed policy.
12. No restricted content is committed in any form, anywhere.

## 23. Implementation authorization boundary

This design contract freezes governance. It does NOT authorize
implementation. Implementation requires:

1. This contract merged and frozen with a recorded SHA on main.
2. A separate user authorization for TASK-013 implementation.
3. A new GitHub Issue (separate from #46) explicitly authorizing the
   implementation scope.
4. The implementation PR MUST reference the frozen design SHA in its
   body under a "Frozen Contract Authority SHA" section.
5. The implementation PR MUST NOT modify TASK-011, TASK-012, or
   TASK-013 frozen contract bodies.

Until all five conditions hold, TASK-013 implementation MUST NOT
begin.