# TASK-020 — Shell-and-Tube Configuration Schema Foundation Design Contract

> Design contract for the first M3 shell-and-tube capability.
> TASK-020 defines a deterministic, versioned and provenance-bound
> configuration schema foundation for shell-and-tube equipment. It defines
> configuration identity, normalization, rule-pack binding and fail-closed
> validation only.
>
> This document is design-only. It does not implement shell-and-tube
> selection, geometry, heat transfer, pressure drop, mechanical design,
> materials, costing, optimization, API, report rendering or Golden values.

## 1. Authority, status and authorization gate

| Field | Value |
|---|---|
| Authorizing Issue | #117 — `[TASK-020][design] Define the first M3 shell-and-tube capability contract` |
| Authorizing instruction | Charles authorized a docs-only TASK-020 design-authoring round after accepting the Issue #117 skeleton |
| Design branch | `docs/task-020-shell-and-tube-configuration-schema-design` |
| Design file | `docs/tasks/TASK-020-shell-and-tube-configuration-schema.md` |
| Allowed file for this authoring round | This design file only |
| Branch base | `main` at `a325b5e498a57ccfa882fb5b227fa68037d29f0d` |
| Predecessor handoff authority | TASK-019 §18.1–§18.7, merged by PR #116 at `daf1d824ea6e8d064604b4d0b721af2517459013` |
| Backlog authority | `docs/TASK_BACKLOG.md`, M3 collective scope for TASK-020 through TASK-039 |
| Standards/license authority | `docs/tasks/TASK-012-standards-rule-pack-license-boundary.md` |
| Product scope authority | `docs/MASTER_DEVELOPMENT_SPEC.md`, especially §§2, 7, 8.2 and 9 |
| Design PR | #118 — DRAFT / NOT READY / NOT MERGED |
| Design contract status | **DRAFT / NOT FROZEN** |
| Frozen Contract Authority SHA | NOT ESTABLISHED |
| Implementation status | **NOT AUTHORIZED** |
| Implementation Issue | NOT CREATED |
| Issue #117 status | OPEN |

The six ordinary commits between the PR #116 merge commit and this branch
base created and removed three temporary no-op files. Their net tree diff is
empty. They are traceability noise only and are not engineering or TASK-020
authority.

Implementation is blocked until this contract is reviewed, merged, closed
out and followed by separate Charles authorization.

## 2. Problem statement and M3 position

The M3 backlog names a shell-and-tube capability family but does not provide
an executable contract for its first task. Later M3 work cannot safely define
tube layout, shell diameter, rating, pressure drop, thermal expansion,
mechanical screening, materials or costing until every shell-and-tube
candidate has a stable configuration identity and a validated authority
binding.

TASK-020 therefore establishes the first M3 foundation:

1. a canonical shell-and-tube configuration request;
2. a canonical normalized configuration descriptor;
3. a distinction between generic project-defined configuration semantics
   and externally governed standard-code semantics;
4. deterministic identity, serialization, hashing and provenance;
5. structured blockers for unsupported, unapproved or unlicensed authority;
6. explicit `NOT_COMPUTABLE` boundaries for all later engineering outputs.

TASK-020 is intentionally schema-first. It supplies a stable contract for
later M3 tasks without pretending that a configuration schema is a completed
heat-exchanger design.

## 3. Exact TASK-020 allocation decision

### 3.1 Frozen allocation

TASK-020 owns **Shell-and-Tube Configuration Schema Foundation**.

The future implementation may:

- construct typed configuration requests and descriptors;
- normalize structural fields;
- bind a configuration to either project-internal generic authority or an
  approved TASK-012 rule-pack authority;
- validate structural and rule-pack-defined compatibility constraints;
- emit deterministic identifiers, hashes, provenance, warnings and blockers.

The future implementation must not choose a configuration on behalf of a
user, optimize a configuration, or calculate any engineering performance.

### 3.2 Later M3 allocation remains deliberately unassigned

The repository provides no authority for assigning the following capabilities
to exact TASK-021 through TASK-039 identifiers. TASK-020 therefore records
them as deferred and forbids invented numbering:

| Deferred capability | TASK-020 disposition |
|---|---|
| tube layout and tube count | out of scope; later M3 allocation required |
| shell diameter | out of scope; later M3 allocation required |
| tube-side rating | out of scope; later M3 allocation required |
| simplified shell-side/Kern screening | out of scope; later M3 allocation required |
| Bell–Delaware | out of scope; later M3 allocation required |
| pressure-drop decomposition | out of scope; later M3 allocation required |
| thermal-expansion screening | out of scope; later M3 allocation required |
| preliminary mechanical boundaries | out of scope; later M3 allocation required |
| shell-and-tube materials and mass | out of scope; later M3 allocation required |
| costing and life-cycle energy | out of scope; later M3 allocation required |
| optimization | out of scope; later M3 allocation required |
| API, report and Golden validation | out of scope; later M3 allocation required |

A later Charles-authorized M3 sequencing amendment must assign those exact
Task IDs before work on them begins. This contract does not silently reserve
or consume TASK-021 through TASK-039.

## 4. Dependency contract

### 4.1 Direct dependencies

| Contract | Dependency type | TASK-020 use |
|---|---|---|
| TASK-001 | direct terminology authority | equipment-family and project terminology |
| TASK-004 | direct error/provenance authority | structured error and calculation-provenance conventions |
| TASK-012 design and implementation | direct runtime/governance dependency | rule-pack source class, approval, license, evidence and canonical hash validation |
| TASK-014 design and implementation | direct case-authority dependency | caller-supplied immutable `CaseRevision` (revision_id, payload_hash, domain_snapshot_hash, status) verified under TASK-014; TASK-020 reads only the supplied value object and performs no persistence lookup |
| TASK-015A | direct implementation-governance dependency | deterministic test execution and CI shard registration |
| TASK-019 §18 | direct governance predecessor | source-definition handoff, anti-fabrication and allocation boundaries |

### 4.2 Reference-only predecessors

TASK-002, TASK-003 and TASK-005 through TASK-013, except TASK-012, plus
TASK-016 through TASK-018 are reference-only for TASK-020. They demonstrate
existing project conventions but TASK-020 does not consume their thermal,
geometry, material, cost, API or report outputs.

In particular:

- TASK-002 SI discipline remains binding project policy, but TASK-020 accepts
  no unit-bearing engineering quantity.
- TASK-005 registry and applicability conventions are reference patterns;
  TASK-020 creates no engineering correlation.
- TASK-016 is a double-pipe tube/pipe/hairpin geometry catalog and is not a
  shell-and-tube bundle or layout catalog.
- TASK-017 and TASK-018 apply to the completed double-pipe vertical slice and
  must not be reused as shell-and-tube engineering results.
- TASK-019 double-pipe deferred gaps remain separate and are not imported.

### 4.3 Required capabilities still absent

The following remain absent at TASK-020 launch and must not be simulated:

- an approved shell-and-tube configuration rule pack containing semantic
  compatibility rules;
- shell-and-tube geometry catalogs;
- shell-and-tube thermal/hydraulic calculations;
- shell-and-tube mechanical, material and cost models;
- shell-and-tube API/report/Golden integration.

## 5. Scope and non-scope

### 5.1 In scope for the future TASK-020 implementation

1. Typed domain models for case authority, configuration request, authority
   binding, normalized configuration and validation result.
2. Structural normalization for equipment family, construction family,
   authority mode, component-code tokens, pass counts and orientation.
3. Validation against a TASK-012-approved configuration rule pack when the
   request claims external-standard authority.
4. A generic internal mode that makes no external-standard compliance claim.
5. Deterministic ordering, canonical serialization, SHA-256 content hashing
   and UUIDv5 result identity.
6. Stable warning and blocker codes.
7. Provenance that binds the result to the verified TASK-014 case authority,
   input, rule-pack identity and evidence references.
8. Schema, determinism, license-boundary and negative-path tests.

### 5.2 Explicit non-scope

TASK-020 does not authorize or define:

- automatic recommendation or selection among fixed-tubesheet, U-tube or
  floating-head families;
- service-condition suitability rules;
- tube size, pitch, pattern, count, length or layout;
- shell diameter, baffle type, cut, spacing or count;
- heat balance, LMTD, epsilon-NTU, heat-transfer coefficient or area;
- tube-side or shell-side pressure drop;
- Kern, Bell–Delaware, leakage, bypass or window-zone corrections;
- fouling calculations;
- vibration, thermal expansion or detailed/preliminary mechanical design;
- material selection, mass, CAPEX, OPEX or life-cycle cost;
- optimization, ranking or Pareto behavior;
- persistence, ORM, migration, public API, user-facing CLI command or report
  rendering;
- numerical Golden vectors;
- any copied standard text, table, figure, scanned page or formula image;
- any mutation of frozen TASK-001 through TASK-019 contracts;
- assignment of later M3 capabilities to exact Task IDs;
- Ready or merge for the design PR without separate Charles authorization.

## 6. Standards, rule-pack and licensing boundary

TASK-020 inherits TASK-012 without modification.

### 6.1 Authority modes

The closed `authority_mode` set is:

- `INTERNAL_GENERIC` — project-defined generic configuration semantics. It
  may identify a construction family and structural fields but must emit
  `standard_claim_status = NO_STANDARD_CLAIM`.
- `APPROVED_RULE_PACK` — semantic validation is delegated to an approved
  TASK-012 rule pack. The result may emit
  `standard_claim_status = RULE_PACK_VALIDATED`, but it must not claim legal
  compliance or certification.

### 6.2 Restricted standards

A restricted standard reference, including TEMA when treated as restricted,
must use TASK-012 metadata/citation-only behavior unless another permitted
source class and valid evidence explicitly authorizes repository storage and
runtime use.

TASK-020 core code must not embed:

- an externally copied code list;
- an externally copied compatibility matrix;
- clause text or table content;
- a reproduced figure or formula image;
- a claim that a configuration is certified or code-compliant.

### 6.3 Rule-pack requirements

A rule pack used by TASK-020 must satisfy **all** of the following
preconditions before its rules may be evaluated. These preconditions are
expressed in terms of the existing TASK-012 `RulePack` contract and the
TASK-012 `validate_rule_pack(...)` validator; TASK-020 does **not** introduce
a parallel pack-level identity, hash, approval, source class or license
concept.

1. The pack must be loaded by the existing TASK-012 loader, producing a
   `RulePack` in-memory object that contains the manifest, the per-rule
   entries, the per-rule provenance records and the permission evidence.
2. The TASK-012 `validate_rule_pack(...)` call against the loaded object
   must return `status = ok`. This status is the **only** pack-level
   authority signal TASK-020 recognizes. TASK-020 does not interpret
   `status` values other than `ok` as a usable pack.
3. The manifest identity triple
   `(rule_pack_id, rule_pack_version, rule_pack_canonical_hash)` declared by
   the request must match exactly the manifest identity triple exposed by
   the loaded `RulePack`. The request field
   `rule_pack_canonical_hash` is bound to the TASK-012 manifest field
   `canonical_hash`; the names `content_hash` and `rule_pack_hash` must
   not be used in the TASK-020 contract. The terminology
   `rule_pack_canonical_hash` is the **single** TASK-020-facing name for
   the TASK-012 manifest `canonical_hash`.
4. For **every** rule selected by the TASK-020 adapter
   (`selected_rule_ids` per §6.3.1 below), all of the following rule-level
   predicates must hold; if any one fails, the pack is rejected for
   TASK-020 use:
   - the rule exists in the loaded `RulePack`;
   - the rule's `approval_status` is exactly `approved`;
   - the rule's `canonical_hash` verifies against its declared content;
   - the rule's license boundary verifies under TASK-012;
   - the rule's provenance records verify under TASK-012.

#### 6.3.1 TASK-020-facing `RulePackAuthority`

The TASK-020 input consumes a `RulePackAuthority` value object built from
the loaded, validated `RulePack`. `RulePackAuthority` is a TASK-020-owned
adapter value, not a TASK-012 field. Its frozen shape is:

- `rule_pack_id: str` — mapped from the TASK-012 manifest `rule_pack_id`.
- `rule_pack_version: str` — mapped from the TASK-012 manifest
  `rule_pack_version`.
- `rule_pack_canonical_hash: str` — mapped from the TASK-012 manifest
  `canonical_hash`. Required to be a lowercase 64-char SHA-256 hex string.
- `validation_status: enum` — required exact value `ok`, copied from
  `validate_rule_pack(...).status`.
- `selected_rule_ids: list[str]` — the set of rule IDs the TASK-020
  adapter has actually evaluated for this configuration, drawn from
  `rule_body.profile_id == "task020.configuration-rule.v1"`.
- `selected_rule_hashes: list[str]` — the lowercase 64-char SHA-256 hex
  canonical hash of each selected rule body, in the same order as
  `selected_rule_ids`.

TASK-020 does **not** read, infer, or carry a pack-level `approval_status`,
pack-level `source_class`, or pack-level `license_evidence`. These are
rule-level concerns and remain on the consumed rule's provenance record
under TASK-012; if a future TASK-020 audit needs the source class, license
boundary or approval status of a rule, it must be read from the rule's
provenance, not from the pack. The TASK-020 contract preserves the rule
provenance records it consumed by reference; it does not duplicate them as
a pack-level field.

If any precondition in §6.3 fails, validation fails closed. The
appropriate §10.2 blocker code is emitted and no `ShellAndTubeConfiguration`
is produced.

### 6.4 Internal engineering rules

Generic construction-family identifiers defined by this project may be stored
as `INTERNAL_ENGINEERING_RULE` content when they are authored, reviewed and
approved under TASK-012. They must not be represented as verbatim external
standard content.

## 7. Domain model and terminology

### 7.1 Frozen construction-family set

The TASK-020 core defines this closed internal set, derived from the product
scope in `docs/MASTER_DEVELOPMENT_SPEC.md`:

- `FIXED_TUBESHEET`
- `U_TUBE`
- `FLOATING_HEAD`

These are project-level construction-family labels. They are not a complete
external-standard code list and do not by themselves establish compliance.

### 7.2 Frozen orientation set

- `HORIZONTAL`
- `VERTICAL`
- `UNSPECIFIED`

`UNSPECIFIED` is a valid schema value but may be rejected by a future approved
rule pack for a particular standard-coded configuration.

### 7.3 CaseRevisionAuthority

TASK-020 consumes a TASK-020-owned adapter value, `CaseRevisionAuthority`,
which is derived from the frozen TASK-014 `CaseRevision` contract. The
adapter value is **not** a field of TASK-014 itself and is **not** an
extension of the TASK-014 schema; the TASK-014 `CaseRevision` exposes only
its own frozen fields, and TASK-020 must speak only via the mapping below.

The frozen TASK-014 `CaseRevision` exposes:

- `revision_id`;
- `payload_hash` (lowercase 64-char SHA-256 hex);
- `domain_snapshot_hash` (lowercase 64-char SHA-256 hex);
- `status` drawn from the TASK-014 lifecycle set.

`CaseRevisionAuthority` is a TASK-020 value object with the following frozen
shape and the following 1-to-1 mapping from TASK-014:

- `revision_id: str` — mapped from TASK-014 `CaseRevision.revision_id`.
- `payload_hash: str` — mapped from TASK-014
  `CaseRevision.payload_hash`. Required to be a lowercase 64-char SHA-256 hex
  string when present.
- `domain_snapshot_hash: str` — mapped from TASK-014
  `CaseRevision.domain_snapshot_hash`. Required to be a lowercase 64-char
  SHA-256 hex string when present.
- `revision_status: enum` — mapped from TASK-014 `CaseRevision.status`, then
  filtered to the **frozen** TASK-020 acceptance subset
  `{committed, superseded, archived}`.

The TASK-020 acceptance subset is justified as follows:

- `committed` — accepted because a committed TASK-014 revision is the
  authoritative, content-stable state intended to be consumed by downstream
  configuration schemas.
- `superseded` — accepted because a superseded revision is still
  content-stable and may be referenced by historical or audit-bound
  configurations; identity and hashes remain trustworthy.
- `archived` — accepted because an archived revision is still
  content-stable and may be referenced by read-only or compliance-bound
  configurations; identity and hashes remain trustworthy.
- TASK-014 lifecycle values outside this frozen subset are **not** accepted
  and must produce a blocker. Mutable or non-authoritative TASK-014
  lifecycle values must not flow into a TASK-020 configuration identity.

TASK-020 does not perform any persistence query. The calling application is
responsible for loading the TASK-014 `CaseRevision`, performing any
TASK-014-level verification, and supplying the resulting immutable value
object to TASK-020. TASK-020 treats the supplied value as read-only and
emits a blocker if the value is absent, malformed, or carries a
non-accepted lifecycle value.

### 7.4 ShellAndTubeConfigurationRequest

The request is an immutable value object containing the fields frozen in §8.
It represents an explicitly supplied configuration. It is not a selection or
optimization request.

### 7.5 ConfigurationAuthorityBinding

The authority binding records:

- authority mode;
- standard system identifier, when applicable;
- rule-pack identity triple `(rule_pack_id, rule_pack_version,
  rule_pack_canonical_hash)` and the TASK-012 `validation_status = ok`
  signal, when applicable;
- citation/evidence pointers drawn from the consumed rule provenance;
- rule-level approval, source class and license boundary carried by
  reference to the consumed rule provenance, **not** as a pack-level
  field on the binding itself.

TASK-020 does not introduce a pack-level `approval_status`,
`source_class` or `license_evidence` field on the authority binding. Those
attributes live on the consumed rule's provenance record under TASK-012.

### 7.6 ShellAndTubeConfiguration

The normalized configuration is the stable output descriptor containing the
fields frozen in §9. It is safe for later M3 consumers to reference by ID, but
it carries no geometry or performance claim.

### 7.7 ConfigurationValidationResult

The validation result contains:

- `status` from `VALID` or `BLOCKED`;
- normalized configuration when valid;
- deterministic warnings and blockers;
- deferred-capability declarations for unsupported engineering outputs.

## 8. Input schema contract

### 8.1 ShellAndTubeConfigurationRequest fields

| Field | Type | Requirement |
|---|---|---|
| `schema_version` | string | required; exact initial value `task020.configuration-request.v1` |
| `case_authority` | `CaseRevisionAuthority` | required; §7.3 |
| `rule_pack_authority` | `RulePackAuthority` or null | required for `APPROVED_RULE_PACK`; absent for `INTERNAL_GENERIC`; §6.3.1 |
| `equipment_family` | string | required; exact value `SHELL_AND_TUBE` |
| `authority_mode` | enum | required; §6.1 closed set |
| `construction_family` | enum | required; §7.1 closed set |
| `orientation` | enum | required; §7.2 closed set |
| `shell_pass_count` | integer | required; `>= 1` |
| `tube_pass_count` | integer | required; `>= 1` |
| `front_head_token` | string or null | structural token; semantic authority comes from rule pack |
| `shell_token` | string or null | structural token; semantic authority comes from rule pack |
| `rear_head_token` | string or null | structural token; semantic authority comes from rule pack |
| `standard_system_id` | string or null | required for `APPROVED_RULE_PACK`; absent for `INTERNAL_GENERIC` |
| `rule_pack_id` | string or null | required for `APPROVED_RULE_PACK`; absent for `INTERNAL_GENERIC` |
| `rule_pack_version` | string or null | required for `APPROVED_RULE_PACK`; absent for `INTERNAL_GENERIC` |
| `rule_pack_canonical_hash` | lowercase 64-char hex string or null | required for `APPROVED_RULE_PACK`; absent for `INTERNAL_GENERIC`; bound to TASK-012 manifest `canonical_hash` |
| `evidence_refs` | array of strings | required; may be empty only in `INTERNAL_GENERIC` mode |

### 8.2 Structural token normalization

When present, component tokens must:

1. be trimmed;
2. be normalized to uppercase ASCII;
3. match `^[A-Z0-9][A-Z0-9._-]{0,15}$`;
4. remain opaque to the core schema.

The core must not interpret a token as a particular external-standard symbol.
Exact allowed tokens and combinations are rule-pack concerns.

### 8.3 Authority-mode consistency

For `INTERNAL_GENERIC`:

- `standard_system_id`, `rule_pack_id`, `rule_pack_version`,
  `rule_pack_canonical_hash` and `rule_pack_authority` must be null;
- component tokens may be null;
- no standard compliance claim may be emitted.

For `APPROVED_RULE_PACK`:

- all rule-pack identity fields are required;
- all three component tokens are required unless the approved rule pack
  explicitly declares a different structural requirement;
- the referenced rule pack must load and validate under TASK-012.

### 8.4 No unit-bearing geometry inputs

TASK-020 accepts no diameters, lengths, areas, temperatures, pressures, flow
rates or fouling values. Any such field is an unknown-field schema blocker,
not a silently ignored extension.

## 9. Output schema contract

### 9.1 ShellAndTubeConfiguration fields

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | exact initial value `task020.configuration.v1` |
| `configuration_id` | UUID string | deterministic UUIDv5 per §11 |
| `configuration_hash` | lowercase 64-char hex string | SHA-256 per §11 |
| `equipment_family` | string | `SHELL_AND_TUBE` |
| `authority_mode` | enum | normalized request value |
| `standard_claim_status` | enum | `NO_STANDARD_CLAIM` or `RULE_PACK_VALIDATED` |
| `construction_family` | enum | normalized §7.1 value |
| `orientation` | enum | normalized §7.2 value |
| `shell_pass_count` | integer | normalized request value |
| `tube_pass_count` | integer | normalized request value |
| `component_tokens` | object | normalized front/shell/rear tokens or null values |
| `authority_binding` | object | normalized §7.5 authority data |
| `case_authority` | object | copied from verified TASK-014 input |
| `warnings` | array of §10.4 warning objects | stable ordered warning objects; each entry is the complete §10.4 five-field shape (`code`, `field_path`, `message_key`, sorted `evidence_refs`, canonical `details`) and is included in the canonical hash per §11.2 |
| `blockers` | array of §10.4 blocker objects | empty for a valid configuration; when non-empty, the array is the §11.2.1 `validation_result` identity source |
| `deferred_capabilities` | array | stable closed entries from §9.3 |

### 9.2 Computable TASK-020 outputs

TASK-020 computes only:

- normalized structural configuration values;
- structural and approved-rule-pack validation status;
- configuration hash and deterministic ID;
- authority/provenance binding;
- warnings, blockers and deferred-capability declarations.

### 9.3 Explicitly non-computable outputs

The closed initial `deferred_capabilities` set is:

- `TUBE_LAYOUT_NOT_COMPUTABLE`
- `SHELL_DIAMETER_NOT_COMPUTABLE`
- `THERMAL_RATING_NOT_COMPUTABLE`
- `PRESSURE_DROP_NOT_COMPUTABLE`
- `THERMAL_EXPANSION_NOT_COMPUTABLE`
- `MECHANICAL_BOUNDARY_NOT_COMPUTABLE`
- `MATERIAL_SELECTION_NOT_COMPUTABLE`
- `COST_NOT_COMPUTABLE`
- `OPTIMIZATION_NOT_COMPUTABLE`
- `REPORT_NOT_COMPUTABLE`

These entries are capability declarations, not warnings that may be ignored.
No numeric placeholder or fabricated fallback may accompany them.

## 10. Validation, blocker and warning model

### 10.1 Fail-closed behavior

A blocked validation returns no `ShellAndTubeConfiguration`. It returns a
`ConfigurationValidationResult(status = BLOCKED)` with stable blockers.
Partial normalized outputs must not be exposed as valid configurations.

### 10.2 Frozen blocker-code set

- `STC_SCHEMA_VERSION_UNSUPPORTED`
- `STC_UNKNOWN_FIELD`
- `STC_CASE_AUTHORITY_MISSING` — TASK-020 input did not supply a
  `CaseRevisionAuthority`.
- `STC_CASE_REVISION_STATUS_BLOCKED` — supplied `CaseRevisionAuthority`
  carries a TASK-014 `status` outside the TASK-020 acceptance subset
  `{committed, superseded, archived}`.
- `STC_CASE_PAYLOAD_HASH_INVALID` — supplied `payload_hash` is not a
  lowercase 64-char SHA-256 hex string.
- `STC_CASE_DOMAIN_SNAPSHOT_HASH_INVALID` — supplied `domain_snapshot_hash`
  is not a lowercase 64-char SHA-256 hex string.
- `STC_CASE_REVISION_ID_MISSING` — supplied `revision_id` is empty or
  absent.
- `STC_EQUIPMENT_FAMILY_INVALID`
- `STC_AUTHORITY_MODE_INVALID`
- `STC_CONSTRUCTION_FAMILY_INVALID`
- `STC_ORIENTATION_INVALID`
- `STC_PASS_COUNT_INVALID`
- `STC_TOKEN_MALFORMED`
- `STC_AUTHORITY_FIELDS_INCONSISTENT`
- `STC_RULE_PACK_REQUIRED`
- `STC_RULE_PACK_NOT_FOUND`
- `STC_RULE_PACK_VALIDATION_FAILED` — TASK-012 `validate_rule_pack(...)`
  did not return `status = ok`, or the manifest identity triple
  `(rule_pack_id, rule_pack_version, rule_pack_canonical_hash)` does not
  match the loaded `RulePack`.
- `STC_RULE_PACK_CANONICAL_HASH_MISMATCH` — manifest canonical hash
  declared by the request does not match the loaded `RulePack`.
- `STC_REQUIRED_RULE_MISSING` — a `task020.configuration-rule.v1` rule
  required for the current `construction_family` /
  `authority_mode` combination was not found in the selected set.
- `STC_RULE_UNAPPROVED` — a selected rule's `approval_status` is not
  exactly `approved`.
- `STC_RULE_CANONICAL_HASH_MISMATCH` — a selected rule's `canonical_hash`
  does not verify against its declared content.
- `STC_RULE_LICENSE_BLOCKED` — a selected rule's license boundary does
  not verify under TASK-012.
- `STC_RULE_PROVENANCE_BLOCKED` — a selected rule's provenance records
  do not verify under TASK-012.
- `STC_RULE_PROFILE_UNRECOGNIZED` — a rule body's `profile_id` is not
  exactly `"task020.configuration-rule.v1"`.
- `STC_RULE_TYPE_UNRECOGNIZED` — a rule body's `rule_type` is outside
  the frozen TASK-020 type set per §12.3.
- `STC_RULE_DUPLICATE_IDENTITY` — two selected rules share the same
  `(profile_id, rule_type, constraint_id)` triple; resolution is
  fail-closed per §12.5.
- `STC_RULE_PRIORITY_CONFLICT` — two selected rules of conflicting
  `effect` share the same priority for the same `constraint_id` per
  §12.5.
- `STC_RULE_APPLICABILITY_UNRESOLVED` — applicability matching could
  not determine whether a rule applies.
- `STC_RULE_CONSTRAINT_MISSING` — a constraint class required by
  §12.3 for the current `construction_family` is absent from the
  selected set.
- `STC_TOKEN_UNSUPPORTED_BY_RULE_PACK`
- `STC_CONFIGURATION_COMBINATION_BLOCKED`
- `STC_PROVENANCE_INCOMPLETE`
- `STC_CANONICALIZATION_FAILED`

### 10.3 Frozen warning-code set

- `STC_GENERIC_CONFIGURATION_NO_STANDARD_CLAIM`
- `STC_RESTRICTED_STANDARD_METADATA_ONLY`
- `STC_ORIENTATION_UNSPECIFIED`

Warnings cannot override blockers and cannot create a compliance claim.

### 10.4 Error object shape

Every warning or blocker is a frozen object containing the following five
fields. Each field is computation authority; localized prose is not.

- `code: str` — the frozen §10.2 / §10.3 code.
- `field_path: str | null` — dotted JSON-pointer-style path, or null when
  the error is not bound to a single field.
- `message_key: str` — opaque, stable key used to look up a localized
  message. **The `message_key` is computation authority and is included
  in the canonical hash; localized prose derived from `message_key` is
  not.**
- `evidence_refs: list[str]` — the rule or pack evidence pointers
  relevant to this error. The list is sorted in **ascending Unicode
  code-point order** at canonicalization time.
- `details: object` — additional structured context. The value MUST be
  one of:

  - a JSON primitive (`string`, `number`, `boolean`, `null`);
  - a JSON array of values recursively satisfying this constraint;
  - a JSON object whose keys are sorted in **canonical key sort order**
    (lexicographic Unicode code-point order on the keys) and whose
    values recursively satisfy this constraint.

Localized prose is presentation metadata and is **excluded** from the
identity hash. The `message_key`, not the localized text, is the
computation authority for warning and blocker identity.

## 11. Determinism, identity, serialization, hashing and provenance

### 11.1 Purity

Validation must be deterministic for the same request and the same verified
rule-pack content. It must not read the clock, network, environment variables,
locale or unordered filesystem state.

### 11.2 Canonical payload

The configuration hash covers the **complete canonical payload** listed
below. Every field is computation authority; the hash MUST change if and
only if one of these canonical fields changes.

- the output `schema_version` (frozen as `task020.configuration.v1` for
  this contract; a future schema version change is itself a change of
  this field and therefore changes the hash);
- normalized structural fields (§9.1: `equipment_family`,
  `authority_mode`, `standard_claim_status`, `construction_family`,
  `orientation`, `shell_pass_count`, `tube_pass_count`,
  `component_tokens`);
- the complete case authority: the full `CaseRevisionAuthority` value
  object as defined in §7.3, with all four fields
  (`revision_id`, `payload_hash`, `domain_snapshot_hash`,
  `revision_status`) and the `payload_hash` and
  `domain_snapshot_hash` rendered as lowercase 64-char hex;
- the complete rule-pack authority: the full `RulePackAuthority` value
  object as defined in §6.3.1, with all six fields (`rule_pack_id`,
  `rule_pack_version`, `rule_pack_canonical_hash`, `validation_status`,
  `selected_rule_ids`, `selected_rule_hashes`);
- the `selected_rule_ids` and `selected_rule_hashes` in the order
  produced by §12.4;
- the **complete canonical warning objects** (per §10.4), each rendered
  with its full five-field shape and ordered by the §11.4 composite key;
- the **complete canonical blocker objects** (per §10.4), in the same
  ordered shape, even though a `BLOCKED` result does not produce a
  `ShellAndTubeConfiguration`; the §10.4 ordering and the
  `validation_result` identity boundary in §11.2.1 are the only
  references a `BLOCKED` result carries for its own identity;
- the frozen `deferred_capabilities` list in the §9.3 order;
- the frozen `authority_binding` object as defined in §7.5.

The hash **excludes**:

- `configuration_id`;
- `configuration_hash` (the hash does not contain itself);
- the localized prose rendered from any `message_key`;
- Git commit, runtime timestamp, host name, process ID, environment
  variable, locale and any other host or process metadata;
- the implementation package version (it appears in the surrounding run
  provenance, not in the configuration hash).

Canonical serialization must reuse the repository canonical-JSON
discipline: UTF-8, lexicographically sorted object keys, stable array
ordering, no NaN or Infinity, no platform-dependent representation, and
the §10.4 canonical forms for `evidence_refs` (ascending Unicode
code-point order) and `details` (canonical key sort order, JSON
primitives/arrays/objects only).

#### 11.2.1 `BLOCKED` result identity boundary

A `ConfigurationValidationResult(status = BLOCKED)` does not produce a
`ShellAndTubeConfiguration`, but it does produce a deterministic identity
of its own. That identity is the SHA-256 hex of the canonical
serialization of the ordered, complete blocker list (per §10.4 and
§11.4). The `validation_result` identity is recorded in the surrounding
run provenance, not in the configuration hash, and is used only to
distinguish one blocked outcome from another in audit and CI artifacts.

### 11.3 Hash and ID algorithm

1. Serialize the canonical payload.
2. Compute lowercase SHA-256 hex as `configuration_hash`.
3. Compute:

```text
configuration_id = UUIDv5(
  UUID_NAMESPACE_URL,
  "urn:hxforge:task020:shell-and-tube-configuration:v1:" + configuration_hash
)
```

The exact namespace seed above is frozen.

### 11.4 Ordering

The canonical payload applies the following orderings; these are the
orderings used in the SHA-256 canonical serialization of §11.2:

- evidence references inside any single warning or blocker
  `evidence_refs` list: ascending Unicode code-point order on the
  string elements;
- the `details` object of any warning or blocker: canonical key sort
  order on the keys (lexicographic Unicode code-point order);
- the warning array: stable ascending sort on the composite key
  `(code, field_path or "", message_key, canonical_details_hash)`,
  where `canonical_details_hash` is the lowercase hex SHA-256 of the
  canonical serialization of the `details` object;
- the blocker array: the same composite key
  `(code, field_path or "", message_key, canonical_details_hash)` in
  ascending order, applied to the §10.4 blocker objects;
- `deferred_capabilities`: the order in §9.3;
- `selected_rule_ids` and `selected_rule_hashes`: the order produced
  by the §12.4 selection sort key, with `selected_rule_hashes`
  matching the `selected_rule_ids` index-by-index.

Input object-key, input evidence-reference order, or input warning /
blocker order MUST NOT alter the hash.

### 11.5 Provenance

The authority binding must retain, by reference to the consumed TASK-014
and TASK-012 contracts:

- the complete `CaseRevisionAuthority` value object (§7.3), carrying
  `revision_id`, `payload_hash`, `domain_snapshot_hash` and
  `revision_status`;
- the complete `RulePackAuthority` value object (§6.3.1), carrying
  `rule_pack_id`, `rule_pack_version`, `rule_pack_canonical_hash`,
  `validation_status = ok`, `selected_rule_ids` and
  `selected_rule_hashes`;
- for each selected rule, the rule's `source_class`,
  `license_evidence` boundary and `approval_status = approved` carried
  by reference to the rule's TASK-012 provenance record (not as a
  pack-level field on the binding);
- citation/evidence pointers drawn from the rule's `evidence_refs`;
- the TASK-020 schema version;
- the implementation package version and the surrounding Git commit in
  the surrounding run provenance, not in the configuration hash.

## 12. Configuration rule profile and adapter boundary

TASK-020 introduces no heat-transfer, hydraulic, mechanical or cost equation
and therefore creates no engineering correlation entry. The TASK-020
implementation may provide a configuration-rule adapter over the existing
TASK-012 runtime, subject to the frozen profile, signature and selection
discipline defined in this section.

### 12.1 Adapter signature (frozen)

The TASK-020 adapter exposes exactly the following entry point. It does not
expose an alternative filesystem-path-taking overload and does not
re-implement TASK-012 license, hash or provenance checks.

```text
ConfigurationRulePackAdapter.validate(
    request: ShellAndTubeConfigurationRequest,
    validated_rule_pack: ValidatedRulePack,
) -> ConfigurationRuleEvaluation
```

`validated_rule_pack` is an in-memory object that has been:

- loaded by the existing TASK-012 loader, producing a `RulePack` whose
  manifest, per-rule entries, per-rule provenance records and permission
  evidence are present;
- validated by TASK-012 `validate_rule_pack(...)`, returning
  `status = ok`.

The TASK-020 adapter does **not** perform any of the following: TASK-012
license verification, TASK-012 hash verification, TASK-012 provenance
verification, or rule `approval_status` checking. It assumes those checks
have already passed at the call boundary and that `validated_rule_pack`
carries the TASK-012 verdict by construction.

### 12.2 TASK-020 configuration rule profile (frozen)

The TASK-020 adapter consumes only rules whose `rule_body.profile_id` is
exactly the frozen string:

```text
profile_id = "task020.configuration-rule.v1"
```

Rules whose `profile_id` is missing or different are skipped with a
`STC_RULE_PROFILE_UNRECOGNIZED` blocker per §12.5.

### 12.3 Frozen rule type set and required JSON shapes

The TASK-020 adapter recognizes the following closed set of `rule_type`
values. Each rule body MUST follow the frozen JSON shape below; the adapter
MUST NOT interpret any field outside this shape, and the adapter MUST NOT
discover rule types dynamically.

#### 12.3.1 `ALLOWED_COMPONENT_TOKEN`

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "ALLOWED_COMPONENT_TOKEN",
  "constraint_id": "<opaque-string-id>",
  "priority": <non-negative integer>,
  "construction_family": ["<FIXED_TUBESHEET|U_TUBE|FLOATING_HEAD>", "..."],
  "component_slot": "<front_head|shell|rear_head>",
  "allowed_tokens": ["<uppercase ASCII token>", "..."],
  "effect": "ALLOW",
  "blocker_code": "STC_TOKEN_UNSUPPORTED_BY_RULE_PACK",
  "evidence_refs": ["<string>", "..."]
}
```

#### 12.3.2 `ALLOWED_CONFIGURATION_COMBINATION`

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "ALLOWED_CONFIGURATION_COMBINATION",
  "constraint_id": "<opaque-string-id>",
  "priority": <non-negative integer>,
  "construction_family": ["<...>", "..."],
  "required_components": {
    "front_head_token": ["<token>", "..."],
    "shell_token": ["<token>", "..."],
    "rear_head_token": ["<token>", "..."]
  },
  "effect": "BLOCK",
  "blocker_code": "STC_CONFIGURATION_COMBINATION_BLOCKED",
  "evidence_refs": ["<string>", "..."]
}
```

#### 12.3.3 `CONSTRUCTION_FAMILY_MAPPING`

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "CONSTRUCTION_FAMILY_MAPPING",
  "constraint_id": "<opaque-string-id>",
  "priority": <non-negative integer>,
  "applies_to_authority_mode": ["<INTERNAL_GENERIC|APPROVED_RULE_PACK>", "..."],
  "construction_family_input": "<FIXED_TUBESHEET|U_TUBE|FLOATING_HEAD>",
  "construction_family_normalized": "<FIXED_TUBESHEET|U_TUBE|FLOATING_HEAD>",
  "effect": "ALLOW",
  "blocker_code": "STC_CONSTRUCTION_FAMILY_INVALID",
  "evidence_refs": ["<string>", "..."]
}
```

#### 12.3.4 `PASS_COUNT_CONSTRAINT`

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "PASS_COUNT_CONSTRAINT",
  "constraint_id": "<opaque-string-id>",
  "priority": <non-negative integer>,
  "construction_family": ["<...>", "..."],
  "shell_pass_count": {"min": <int>, "max": <int>},
  "tube_pass_count": {"min": <int>, "max": <int>},
  "effect": "BLOCK",
  "blocker_code": "STC_PASS_COUNT_INVALID",
  "evidence_refs": ["<string>", "..."]
}
```

#### 12.3.5 `ORIENTATION_CONSTRAINT`

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "ORIENTATION_CONSTRAINT",
  "constraint_id": "<opaque-string-id>",
  "priority": <non-negative integer>,
  "construction_family": ["<...>", "..."],
  "allowed_orientations": ["<HORIZONTAL|VERTICAL|UNSPECIFIED>", "..."],
  "effect": "BLOCK",
  "blocker_code": "STC_ORIENTATION_INVALID",
  "evidence_refs": ["<string>", "..."]
}
```

### 12.4 Rule selection (frozen)

For a given `request`, the TASK-020 adapter selects rules as follows:

1. Filter to rules with `rule_body.profile_id == "task020.configuration-rule.v1"`.
2. Filter to rules whose `rule_body.construction_family` contains the
   request's `construction_family`, or whose `rule_type` is
   `CONSTRUCTION_FAMILY_MAPPING` and whose
   `applies_to_authority_mode` contains the request's `authority_mode`.
3. Apply the type-specific applicability predicate for the request's
   `authority_mode` and selected `component_tokens`.
4. Sort the surviving rules by the key
   `(priority ASC, rule_type ASC, constraint_id ASC)` and stable input
   order on ties.

The adapter MUST NOT use the order of rules inside the loaded `RulePack`
file system, the order of fields inside `manifest.json`, or the iteration
order of any unordered collection as the selection ranking key. The
adapter MUST compute ranking from the rule body itself.

### 12.5 Conflict and missing-rule behavior (frozen, fail-closed)

The TASK-020 adapter applies the following fail-closed rules in selection
order:

1. **Duplicate identity**: if two surviving rules share the same
   `(profile_id, rule_type, constraint_id)` triple, the adapter MUST
   emit `STC_RULE_DUPLICATE_IDENTITY` and stop.
2. **Same-priority conflict**: if two surviving rules share the same
   `constraint_id` and the same `priority` and have conflicting
   `effect` values (`ALLOW` vs `BLOCK`), the adapter MUST emit
   `STC_RULE_PRIORITY_CONFLICT` and stop.
3. **ALLOW vs BLOCK precedence**: across distinct priorities, a
   `BLOCK` effect at any priority dominates an `ALLOW` effect at lower
   priority; ties on priority are resolved by the duplicate-identity
   rule above.
4. **Missing required constraint class**: for the current
   `(construction_family, authority_mode)`, if a constraint class
   required by §12.3 has no surviving rule, the adapter MUST emit
   `STC_RULE_CONSTRAINT_MISSING` and stop.
5. **Unresolved applicability**: if applicability matching cannot
   determine whether a rule applies (for example, a rule whose
   `applies_to_authority_mode` is empty), the adapter MUST emit
   `STC_RULE_APPLICABILITY_UNRESOLVED` and stop.
6. **Unrecognized profile or rule type**: any rule whose `profile_id`
   is not the frozen value or whose `rule_type` is not in the §12.3
   closed set MUST cause `STC_RULE_PROFILE_UNRECOGNIZED` or
   `STC_RULE_TYPE_UNRECOGNIZED` and stop.

Fail-closed means: on any of the conditions above, no
`ConfigurationRuleEvaluation` is produced; the calling
`ConfigurationRulePackAdapter.validate` returns a
`ConfigurationValidationResult(status = BLOCKED)` carrying the appropriate
§10.2 blocker code.

### 12.6 Citation and evidence

`evidence_refs` on each rule body is preserved by the adapter into the
result's `ConfigurationRuleEvaluation` and is the basis for the
`evidence_refs` field of any §10.4 warning or blocker the configuration
later emits. Adapter-level citation, evidence and license handling is
fully delegated to the consumed rule's provenance record.

### 12.7 Adapter non-actions (frozen)

The adapter MUST NOT:

- embed a copied restricted-standard table in core code;
- infer rules from bibliographic metadata alone;
- execute an unapproved rule;
- treat a token match as legal certification;
- extrapolate when a rule pack lacks a required rule;
- take a filesystem path, a URL, or any other out-of-band input in
  place of `validated_rule_pack`;
- re-verify TASK-012 license, hash, provenance or approval status;
- output any engineering value, numeric coefficient, expected output or
  standard quote;
- read the clock, network, environment, locale or unordered filesystem
  state.

Missing semantic authority returns a blocker, never a best-effort result.

## 13. Persistence, API, CLI and report boundaries

### 13.1 Persistence

TASK-020 introduces no database table, ORM record, migration or mutable
catalog. Configuration objects are immutable in-memory/domain values. A later
task may persist them by reference to `configuration_id` and
`configuration_hash` after separate design authorization.

### 13.2 API and CLI

TASK-020 introduces no FastAPI endpoint and no user-facing CLI command. The
future implementation surface is a Python domain/application API only.

### 13.3 Reports

TASK-020 introduces no report section or rendered compliance statement. A
later report task may display the normalized configuration and authority
binding but must preserve the standard-claim boundary.

## 14. Allowed production, test and documentation files

### 14.1 This design-authoring round

Exactly one file is allowed:

- `docs/tasks/TASK-020-shell-and-tube-configuration-schema.md`

No backlog, workflow, source, test, fixture or manifest mutation is allowed in
this design PR.

### 14.2 Future implementation allowlist

A separately authorized implementation may modify only:

- `src/hexagent/shell_and_tube/__init__.py`
- `src/hexagent/shell_and_tube/configuration.py`
- `src/hexagent/shell_and_tube/errors.py`
- `src/hexagent/shell_and_tube/models.py`
- `src/hexagent/shell_and_tube/rule_pack_adapter.py`
- `src/hexagent/shell_and_tube/schema.py`
- `src/hexagent/shell_and_tube/validation.py`
- `tests/shell_and_tube/test_task020_configuration_models.py`
- `tests/shell_and_tube/test_task020_configuration_validation.py`
- `tests/shell_and_tube/test_task020_configuration_identity.py`
- `tests/shell_and_tube/test_task020_license_boundary.py`
- `tests/shell_and_tube/test_task020_rule_profile_adapter.py`
- `tests/fixtures/task020/case_revision/case_revision_committed.json`
- `tests/fixtures/task020/case_revision/case_revision_superseded.json`
- `tests/fixtures/task020/case_revision/case_revision_archived.json`
- `tests/fixtures/task020/case_revision/case_revision_draft_blocked.json`
- `tests/fixtures/task020/rule_packs/valid_configuration_pack/manifest.json`
- `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/allowed_tokens.json`
- `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/allowed_combination.json`
- `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/construction_family_mapping.json`
- `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/pass_count_constraint.json`
- `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/orientation_constraint.json`
- `tests/fixtures/task020/rule_packs/valid_configuration_pack/provenance/allowed_tokens_edge.json`
- `tests/fixtures/task020/rule_packs/valid_configuration_pack/provenance/allowed_combination_edge.json`
- `tests/fixtures/task020/rule_packs/conflicting_configuration_pack/manifest.json`
- `tests/fixtures/task020/rule_packs/conflicting_configuration_pack/rules/conflict_a.json`
- `tests/fixtures/task020/rule_packs/conflicting_configuration_pack/rules/conflict_b.json`
- `tests/fixtures/task020/rule_packs/conflicting_configuration_pack/provenance/conflict_a_edge.json`
- `tests/fixtures/task020/rule_packs/conflicting_configuration_pack/provenance/conflict_b_edge.json`
- `tests/fixtures/task020/rule_packs/unapproved_rule_pack/manifest.json`
- `tests/fixtures/task020/rule_packs/unapproved_rule_pack/rules/allowed_tokens.json`
- `tests/fixtures/task020/rule_packs/unapproved_rule_pack/provenance/allowed_tokens_edge.json`
- `tests/fixtures/task020/rule_packs/license_blocked_rule_pack/manifest.json`
- `tests/fixtures/task020/rule_packs/license_blocked_rule_pack/rules/allowed_tokens.json`
- `tests/fixtures/task020/rule_packs/license_blocked_rule_pack/provenance/allowed_tokens_edge.json`
- `ci-shard-manifest.yml`, only to register the exact new test files

The fixture paths above are exact file paths. The implementation MUST NOT
use glob patterns, recursive wildcards, or any other form of bulk fixture
discovery. Each fixture file is named, audited, and listed in this
section by hand.

All rule-pack fixtures are `INTERNAL_ENGINEERING_RULE` content authored
under TASK-012 governance; they MUST NOT contain verbatim copies of TEMA
or any other restricted standard text, table, figure or formula. Token
identifiers in the fixtures are synthetic project-internal strings and
carry no external-standard semantics.

The exact TASK-014 `CaseRevision` fixture shape is defined by TASK-014;
this contract only enumerates the four task020-specific fixture files
covering the four TASK-020 acceptance scenarios (committed, superseded,
archived, blocked).

Any additional path requires a design amendment and separate Charles
authorization before mutation.

## 15. Test and CI contract

The future implementation must include:

1. schema-version acceptance and rejection tests;
2. unknown-field rejection tests;
3. case-authority adapter tests covering the `CaseRevisionAuthority`
   mapping for each accepted TASK-014 lifecycle value
   (`committed`, `superseded`, `archived`) and each blocked lifecycle
   value (e.g. `draft`);
4. case-authority payload-hash and domain-snapshot-hash shape tests
   (lowercase 64-char SHA-256 hex);
5. construction-family, orientation and pass-count validation tests;
6. internal-generic mode tests proving no standard claim is emitted;
7. approved-rule-pack mode success tests using the synthetic
   `valid_configuration_pack` fixture set in
   `tests/fixtures/task020/rule_packs/valid_configuration_pack/`;
8. missing rule (`STC_REQUIRED_RULE_MISSING`), unapproved rule
   (`STC_RULE_UNAPPROVED`), canonical-hash-mismatched rule
   (`STC_RULE_CANONICAL_HASH_MISMATCH`), license-blocked rule
   (`STC_RULE_LICENSE_BLOCKED`) and provenance-blocked rule
   (`STC_RULE_PROVENANCE_BLOCKED`) tests using the corresponding
   `unapproved_rule_pack` and `license_blocked_rule_pack` fixtures;
9. conflicting-rule fixture tests
   (`STC_RULE_DUPLICATE_IDENTITY`,
   `STC_RULE_PRIORITY_CONFLICT`) using the
   `conflicting_configuration_pack` fixture set;
10. token normalization and malformed-token tests;
11. unsupported-token and incompatible-combination blocker tests;
12. canonical ordering tests for evidence, warnings and blockers
    (including the new `details` and `message_key` ordering rules in
    §11.4);
13. hash stability under object-key and input evidence-order changes;
14. hash mutation tests for every computation-authority field,
    including the complete canonical warning object per §11.2;
15. exact UUIDv5 identity tests;
16. tests proving no geometry, thermal, pressure-drop, mechanical,
    material, cost or report output is produced;
17. TASK-020 configuration-rule-profile adapter tests confirming
    `profile_id == "task020.configuration-rule.v1"`, the closed
    `rule_type` set in §12.3, and the fail-closed selection rules in
    §12.5;
18. restricted-content marker rejection tests inherited from TASK-012;
19. a frozen-contract integrity test for this document after design
    freeze.

CI requirements:

- existing lint/type/test checks must pass;
- new tests must be registered in the existing CI shard manifest;
- no workflow file change is authorized;
- no network or external-standard access is allowed in tests;
- all tests must pass on every Python version already required by repository
  CI.

No numerical engineering Golden vector is required or permitted by TASK-020.
Structural JSON fixtures may be used for canonicalization and blocker tests.

## 16. Implementation slicing and authorization gates

A future implementation should be divided into two reviewable slices.

### 16.1 Slice A — core schema and identity

- domain models and enums;
- strict schema validation;
- verified case-authority binding;
- normalization;
- warning/blocker objects;
- canonical serialization, hash and UUIDv5 identity;
- internal-generic mode;
- corresponding tests and CI registration.

Slice A must not load or evaluate a rule pack.

### 16.2 Slice B — approved rule-pack adapter

- TASK-012 runtime adapter;
- approved-rule-pack authority validation;
- token and combination validation;
- license/evidence fail-closed behavior;
- exact synthetic rule-pack fixtures and tests from §14.2.

Slice B depends on Slice A and must not add engineering calculations.

### 16.3 Authorization sequence

1. Design PR reviewed.
2. Charles separately authorizes Ready.
3. Charles separately authorizes design merge.
4. Post-merge design authority and closeout evidence verified.
5. Charles separately authorizes an implementation Issue and the first slice.

No step implies the next.

## 17. Explicit non-actions and anti-fabrication guard

This design contract does not authorize:

- production code, tests, fixtures or CI-manifest mutation in the design PR;
- any TASK-020 implementation Issue, branch, commit or PR;
- any automatic shell-and-tube configuration recommendation;
- any external-standard token list or compatibility matrix without valid
  TASK-012 authority;
- any engineering equation, coefficient or numerical expected output;
- any claim that a generic or rule-pack-validated configuration is legally
  compliant, certified or safe for fabrication;
- any use of TASK-019 double-pipe deferred gaps as TASK-020 scope;
- any assignment of later M3 capabilities to exact Task IDs;
- any mutation of TASK-001 through TASK-019 frozen contracts;
- Ready or merge for the design PR without separate Charles authorization;
- Feishu outbound.

When authority is absent or ambiguous, implementation must block and preserve
the missing-authority evidence. It must not substitute common practice,
model memory or a guessed standard rule.

## 18. Acceptance checklist and closeout evidence

### 18.1 Design acceptance checklist

The design may be frozen only when review confirms all of the following:

- [ ] TASK-020 is limited to configuration schema foundation.
- [ ] Later M3 Task IDs remain explicitly unassigned rather than invented.
- [ ] Direct and reference-only dependencies are distinguished.
- [ ] TASK-012 license and restricted-content boundaries are preserved.
- [ ] TASK-014 case authority is consumed via the TASK-020-owned
      `CaseRevisionAuthority` adapter value (§7.3) and no persistence
      lookup is hidden inside TASK-020.
- [ ] `CaseRevisionAuthority.revision_status` accepts only
      `committed`, `superseded`, `archived` from the TASK-014 lifecycle.
- [ ] The TASK-020 rule-pack authority uses the TASK-012 manifest
      `canonical_hash` under the single name
      `rule_pack_canonical_hash`; no `content_hash` or `rule_pack_hash`
      appears as a TASK-020 contract field.
- [ ] No pack-level `approval_status`, `source_class` or
      `license_evidence` is defined on the TASK-020 authority binding;
      those attributes live on the consumed rule's provenance record.
- [ ] The TASK-020 configuration-rule profile
      (`task020.configuration-rule.v1`) and the closed `rule_type` set
      in §12.3 are frozen with complete JSON shapes.
- [ ] The `ConfigurationRulePackAdapter.validate(request,
      validated_rule_pack)` signature is frozen and the adapter does
      not re-implement TASK-012 license, hash, provenance or approval
      checks.
- [ ] The fixture allowlist (§14.2) lists exact file paths, with
      `valid_configuration_pack`, `conflicting_configuration_pack`,
      `unapproved_rule_pack` and `license_blocked_rule_pack` fixture
      sets; no glob or wildcard fixture discovery is permitted.
- [ ] The canonical hash (§11.2) covers the complete §10.4 warning and
      blocker objects, the complete `CaseRevisionAuthority`, the
      complete `RulePackAuthority`, the `selected_rule_ids` and
      `selected_rule_hashes` in §12.4 order, the `schema_version` and
      the frozen `deferred_capabilities` list.
- [ ] `BLOCKED` result identity is defined via §11.2.1 without
      producing a `ShellAndTubeConfiguration`.
- [ ] Input and output schemas are complete and versioned.
- [ ] Computable and `NOT_COMPUTABLE` outputs are explicit.
- [ ] Warning and blocker codes are closed sets.
- [ ] Canonical hash and UUIDv5 rules are exact.
- [ ] Persistence, API, CLI and report boundaries are explicit.
- [ ] The future implementation allowlist contains exact paths only.
- [ ] Tests and CI expectations are complete.
- [ ] Implementation remains separately authorized.
- [ ] No engineering formula, numeric expected output, TEMA content or
      any other restricted standard text has been added.

### 18.2 Resolution of TASK-019 §18.4 questions

| Question | TASK-020 answer |
|---|---|
| Is TASK-020 the TEMA configuration/schema foundation or another capability? | It is the shell-and-tube configuration schema foundation. Standard-specific semantics are rule-pack-bound; TASK-020 is not a TEMA calculation engine. |
| Which later Task IDs own layout, diameter, rating, Kern, Bell–Delaware, pressure drop and thermal expansion? | The repository does not authorize exact IDs. They remain unassigned pending a separate Charles-authorized M3 sequencing amendment. |
| Which predecessors are direct vs. reference-only? | Frozen in §4. |
| What standards content may be represented? | Frozen in §6: internal generic rules or TASK-012-permitted approved rule-pack content; restricted bodies remain metadata/citation-only. |
| Which outputs are computable? | Frozen in §9: normalized configuration, validation, identity and provenance only; engineering outputs are explicitly not computable. |
| What is the design-document path? | `docs/tasks/TASK-020-shell-and-tube-configuration-schema.md`. |
| Which TASK-014 fields are authoritative for `CaseRevisionAuthority`? | `revision_id`, `payload_hash`, `domain_snapshot_hash` and `status` are mapped 1-to-1 per §7.3. `revision_status` accepts only the TASK-020 subset `{committed, superseded, archived}`. |
| What is the TASK-020 rule-pack hash field name? | The single TASK-020-facing name is `rule_pack_canonical_hash`, bound to the TASK-012 manifest `canonical_hash` per §6.3. |
| Which adapter boundary does TASK-020 freeze? | `ConfigurationRulePackAdapter.validate(request, validated_rule_pack)` per §12.1; `validated_rule_pack` is a TASK-012-loaded and TASK-012-`status = ok`-validated in-memory object. |
| Which fixture paths are exact? | The four `case_revision/*` files and the four `rule_packs/*` directories in §14.2, each listing its `manifest.json` and per-rule files. |

### 18.3 Required closeout evidence

After any future authorized merge, closeout must record:

- reviewed design head SHA;
- merge commit SHA;
- exact changed-file set;
- PR CI result;
- main post-merge CI result or an explicit statement that no run was visible;
- confirmation that this document is present on main;
- confirmation that Issue #117 is closed only after Charles authorization;
- confirmation that implementation remains not authorized unless separately
  granted.
