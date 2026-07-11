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
| Design Amendment 001 | **AUTHORED** (Issue #129, see §19) |
| Design Amendment 001 S1 merge SHA | `d00d5ced3c0da065f00096f0303c0709917fc380` |
| Issue #129 status | OPEN |

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
| TASK-012 design and implementation | direct runtime/governance dependency | rule-pack source class, approval, license, evidence and canonical hash validation, exposed via the existing `load_rule_pack(root)` and `validate_rule_pack(root)` interfaces |
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
expressed strictly in terms of the existing TASK-012 runtime
interfaces, namely `load_rule_pack(root: Path) -> dict` and
`validate_rule_pack(root: Path) -> dict` (a validation report). TASK-020
does **not** introduce a parallel pack-level identity, hash, approval,
source class or license concept, and TASK-020 does **not** assume the
existence of any in-memory TASK-012 type that bundles a loaded pack
with its validation verdict. The TASK-020 contract treats the TASK-012
loader and the TASK-012 validator as two independent filesystem-path
interfaces whose plain-`dict` results must be wrapped, paired and
cross-checked at the TASK-020 boundary; it must not pretend that TASK-012
exposes any richer runtime type.

1. The pack must be loaded by the existing TASK-012 loader
   `load_rule_pack(root)`, producing a plain `dict` whose top-level keys
   are `manifest`, `rules`, `provenance_edges`, `permission_evidence`.
2. The pack must be validated by the existing TASK-012 validator
   `validate_rule_pack(root)`, which itself reloads the same filesystem
   path and returns a `dict` whose top-level keys are `status`, `manifest`,
   `rule_count`, `errors`. The TASK-020 contract treats `status` as the
   **only** pack-level authority signal it recognizes. TASK-020 does not
   interpret any `status` value other than `"ok"` as a usable pack.
3. The manifest identity triple
   `(rule_pack_id, rule_pack_version, rule_pack_canonical_hash)` declared
   by the request must match exactly the manifest identity triple
   exposed by the loaded pack. The request field
   `rule_pack_canonical_hash` is bound to the TASK-012 manifest field
   `canonical_hash`; the names `content_hash` and `rule_pack_hash` must
   not be used in the TASK-020 contract. The terminology
   `rule_pack_canonical_hash` is the **single** TASK-020-facing name for
   the TASK-012 manifest `canonical_hash`.
4. The TASK-012 validation report and the TASK-012-loaded dict must
   describe the **same** pack. The TASK-020 adapter performs the
   consistency checks frozen in §6.3.3 and emits a blocker if they
   disagree; it does **not** re-run any TASK-012 license, hash,
   provenance, canonical-hash or approval verification.
5. For **every** rule that survives the §12 selection pipeline, all of
   the following rule-level predicates must hold; if any one fails, the
   pack is rejected for TASK-020 use:
   - the rule exists in the loaded `rules` list;
   - the rule's `approval_status` direct field is exactly `approved`;
   - the rule's `canonical_hash` direct field verifies against its
     declared artifact content;
   - the rule's `license_evidence` direct field verifies under TASK-012;
   - the rule's `source_class` direct field is present and recognized;
   - the rule's TASK-012 provenance edges (referenced by edge ID) verify
     under TASK-012.

#### 6.3.1 TASK-020-owned typed view: `LoadedRulePackView`

The TASK-020 contract defines a TASK-020-owned typed view named
`LoadedRulePackView`, which is a structured wrapper around the plain
`dict` returned by TASK-012 `load_rule_pack(root)`. It is **not** a
TASK-012 type, and the TASK-020 contract does not require TASK-012 to
expose anything beyond its existing `load_rule_pack(root)` interface.

`LoadedRulePackView` has the following frozen fields, each populated by
a direct key lookup against the TASK-012 `load_rule_pack(root)` result.
The view shape is the TASK-020-owned wrapper over the TASK-012 loader
result; the underlying TASK-012 interface is unchanged.

- `manifest: object` — the TASK-012 loader `manifest` value, copied by
  reference. The TASK-020 contract reads only the three identity fields
  `rule_pack_id`, `rule_pack_version` and `canonical_hash` (the last as
  `rule_pack_canonical_hash`).
- `rules: dict[str, object]` — the TASK-012 loader `rules` re-keyed as
  a `dict` whose **key** is the rule's direct `rule_id` string and whose
  **value** is the complete TASK-012 rule artifact. The dict is built
  on view construction by keying each loader rule by its `rule_id`; the
  underlying TASK-012 rule artifact fields (`rule_id`, `rule_version`,
  `canonical_hash`, `source_class`, `license_evidence`,
  `approval_status`) are read directly from the value, never from the
  dict key. The dict exists to freeze lookup, selection, duplicate
  detection and canonical identity on the `rule_id` key.
- `provenance_edges: list[object]` — the TASK-012 loader
  `provenance_edges` list, copied by reference. TASK-020 reads
  provenance by edge ID only; it does not re-verify or relocate any
  direct rule field into provenance.
- `permission_evidence: dict[str, object]` — the TASK-012 loader
  `permission_evidence` re-keyed as a `dict` whose **key** is the
  permission's direct `permission_id` string and whose **value** is the
  complete TASK-012 permission evidence object. The dict is built on
  view construction by keying each loader entry by its `permission_id`;
  the underlying TASK-012 permission evidence fields are read directly
  from the value, never from the dict key.

**Frozen dict iteration discipline (P1-1, binding)**: the
`LoadedRulePackView.rules` and `LoadedRulePackView.permission_evidence`
dicts are the only iteration surface the TASK-020 adapter uses.
Deterministic iteration MUST be the dict's natural iteration in
**ascending Unicode code-point order on the key** (`rule_id` for rules,
`permission_id` for permission evidence); the adapter MUST NOT rely
on the TASK-012 loader's filesystem order, manifest-array order,
dict-insertion order or any other input-order surrogate. `rule_count`
is the number of dictionary entries in `LoadedRulePackView.rules`; it
is NOT `len(rules_list)` of any list, and it MUST be computed by
`len(loaded_rule_pack.rules)`. The `LoadedRulePackView` and the
`RulePackValidationReport` MUST agree on three identities before
evaluation: `rule_count` (entry count in the rules dict vs.
`RulePackValidationReport.rule_count`), `manifest` identity
(`manifest.rule_pack_id` / `manifest.rule_pack_version` /
`manifest.canonical_hash` equal in both views), and `canonical_hash`
of the loaded pack. Any disagreement emits
`STC_RULE_PACK_VALIDATION_REPORT_MISMATCH` per §6.3.3.

#### 6.3.2 TASK-020-owned typed view: `RulePackValidationReport`

The TASK-020 contract defines a TASK-020-owned typed view named
`RulePackValidationReport`, which is a structured wrapper around the
plain `dict` returned by TASK-012 `validate_rule_pack(root)`. It is
**not** a TASK-012 type and the TASK-020 contract does not require
TASK-012 to expose anything beyond its existing
`validate_rule_pack(root)` interface.

`RulePackValidationReport` has the following frozen fields, each
populated by a direct key lookup against the TASK-012
`validate_rule_pack(root)` result:

- `status: enum` — required exact value `"ok"` for TASK-020 use; any
  other value blocks the request.
- `manifest: object` — the TASK-012 validator `manifest` value, copied
  by reference. TASK-020 reads only the identity triple
  `rule_pack_id`, `rule_pack_version` and `canonical_hash`.
- `rule_count: int` — the TASK-012 validator `rule_count` value,
  copied by reference.
- `errors: list[object]` — the TASK-012 validator `errors` list, copied
  by reference. These are TASK-012 errors and are **not** re-emitted as
  TASK-020 blockers verbatim; TASK-020 emits the
  `STC_RULE_PACK_VALIDATION_FAILED` blocker code when `status != "ok"`.

#### 6.3.3 Cross-input consistency check (frozen, fail-closed)

The TASK-020 adapter does not re-verify TASK-012 license, hash,
provenance or approval status. It does, however, verify that the two
TASK-012 inputs refer to the same pack and that the request refers to
the same pack as the inputs. The frozen checks are:

- `validation_report.status == "ok"`;
- the `rule_pack_id`, `rule_pack_version` and `canonical_hash` fields
  inside `validation_report.manifest` match the corresponding fields
  inside `loaded_rule_pack.manifest` exactly;
- `validation_report.rule_count == len(loaded_rule_pack.rules)`;
- the request's `requested_rule_pack_identity.rule_pack_id`,
  `rule_pack_version` and `rule_pack_canonical_hash` match the
  corresponding fields inside `loaded_rule_pack.manifest` exactly.

If any one of these checks fails, the adapter emits
`STC_RULE_PACK_VALIDATION_REPORT_MISMATCH` and stops. The pack is not
considered usable for TASK-020 evaluation under any circumstance.

If a check fails because the TASK-012 validator itself reported
`status != "ok"`, the adapter emits
`STC_RULE_PACK_VALIDATION_FAILED` instead; the
`STC_RULE_PACK_VALIDATION_REPORT_MISMATCH` code is reserved for the
cross-input consistency case where TASK-012 itself returned `status =
"ok"` but the report disagrees with the loaded dict or the request.

#### 6.3.4 Input identity: `RequestedRulePackIdentity`

The TASK-020 request carries exactly one rule-pack identity object, named
`RequestedRulePackIdentity`, in the `APPROVED_RULE_PACK` mode. The
`RequestedRulePackIdentity` fields are:

- `rule_pack_id: str` — non-empty string.
- `rule_pack_version: str` — non-empty string.
- `rule_pack_canonical_hash: str` — lowercase 64-char SHA-256 hex
  string, bound to the TASK-012 manifest `canonical_hash`.

`RequestedRulePackIdentity` is the **only** rule-pack object the
`ShellAndTubeConfigurationRequest` carries. The previous
`RulePackAuthority` (which mixed input identity with evaluated output
fields such as `selected_rule_ids` and `selected_rule_hashes`) is
removed from the request and is not a TASK-020 request field. For
`INTERNAL_GENERIC` mode, `requested_rule_pack_identity` is `null`.

#### 6.3.5 Output authority: `EvaluatedRulePackAuthority` and `SelectedRuleAuthority`

The TASK-020 adapter produces an `EvaluatedRulePackAuthority` value
object only after a successful evaluation. This object exists in three
places:

- the `ShellAndTubeConfiguration.authority_binding` (output);
- the canonical payload of §11.2;
- the §11.5 provenance record.

`EvaluatedRulePackAuthority` MUST NOT appear on the input side of the
contract. The frozen fields are:

- `rule_pack_id: str` — copied from `RequestedRulePackIdentity`.
- `rule_pack_version: str` — copied from
  `RequestedRulePackIdentity`.
- `rule_pack_canonical_hash: str` — copied from
  `RequestedRulePackIdentity`, lowercase 64-char SHA-256 hex.
- `validation_status: enum` — required exact value `"ok"`, copied from
  `RulePackValidationReport.status`.
- `selected_rule_authorities: list[SelectedRuleAuthority]` — the
  per-selected-rule authorities, each a complete
  `SelectedRuleAuthority` value object (P1-3, binding), in the §12.4
  order. The list is the **only** source of selected rule identity
  in the evaluated authority. The previous
  `selected_rule_ids: list[str]` and
  `selected_rule_artifact_hashes: list[str]` parallel lists are
  **deleted** from the contract: every per-rule identity field lives
  inside the `SelectedRuleAuthority` value object, never as a
  parallel list. The `selected_rule_ids` and
  `selected_rule_artifact_hashes` projections, when needed for
  compatibility with external consumers, are derived from
  `[ra.rule_id for ra in selected_rule_authorities]` and
  `[ra.rule_artifact_canonical_hash for ra in selected_rule_authorities]`
  respectively; the canonical form is the
  `selected_rule_authorities` list itself.

##### 6.3.5.1 `SelectedRuleAuthority` (P1-3, binding, versioned)

`SelectedRuleAuthority` is a TASK-020-owned, versioned value object
that freezes the per-rule authority as a single typed object. The
schema is exact; any field outside this shape MUST emit
`STC_UNKNOWN_FIELD`. The frozen fields are:

- `rule_id: str` — non-empty string. Sourced **directly** from the
  TASK-012 rule artifact's `rule_id` direct field.
- `rule_version: str` — non-empty string. Sourced **directly** from
  the TASK-012 rule artifact's `rule_version` direct field.
- `rule_artifact_canonical_hash: str` — lowercase 64-char SHA-256 hex
  string. Sourced **directly** from the TASK-012 rule artifact's
  `canonical_hash` direct field. This is the TASK-012 rule artifact
  `canonical_hash`, not a separately computed rule-body hash.
- `source_class: str` — non-empty string. Sourced **directly** from
  the TASK-012 rule artifact's `source_class` direct field. This is
  a direct rule-artifact field; the TASK-020 contract MUST NOT
  relocate `source_class` into provenance or anywhere else.
- `license_evidence: object` — copied by reference from the TASK-012
  rule artifact's `license_evidence` direct field. This is a direct
  rule-artifact field; the TASK-020 contract MUST NOT collapse
  `license_evidence` into a provenance record.
- `approval_status: str` — required exact value `"approved"`. Sourced
  **directly** from the TASK-012 rule artifact's `approval_status`
  direct field. This is a direct rule-artifact field; the TASK-020
  contract MUST NOT relocate `approval_status` into a provenance
  record.
- `provenance_edge_ids: list[str]` — the TASK-012 `provenance_edges`
  edge IDs the adapter consulted for this rule. The list is
  **sorted in ascending Unicode code-point order at canonicalization
  time** and **deduplicated** at construction time. Edge IDs are
  references into the loaded `LoadedRulePackView.provenance_edges`
  list; the contract MUST NOT store the full edge content here.
- `evidence_refs: list[str]` — the rule's `evidence_refs` from the
  TASK-012 rule artifact. The list is **sorted in ascending Unicode
  code-point order at canonicalization time** and **deduplicated** at
  construction time. The list MAY be empty.

**Provenance discipline (P1-3, binding)**: `provenance_edge_ids` and
`evidence_refs` are the only fields in `SelectedRuleAuthority` that
carry provenance-like information. The direct fields `source_class`,
`license_evidence` and `approval_status` are NOT stored inside
provenance; they are stored directly on the
`SelectedRuleAuthority` value object. The TASK-020 contract MUST NOT
claim that the six direct fields above are "implicitly contained" in
`EvaluatedRulePackAuthority` or in any provenance record; the
`SelectedRuleAuthority` value object is the typed storage location,
and every direct field is present in the value object by name.

`EvaluatedRulePackAuthority` is therefore a complete schema-versioned
object whose `selected_rule_authorities` is the typed, ordered,
deduplicated list of `SelectedRuleAuthority` value objects. No
parallel list of rule IDs or rule artifact hashes is part of the
canonical `EvaluatedRulePackAuthority`; those values are
projections of the `selected_rule_authorities` list, never the
authoritative source.

#### 6.3.6 TASK-012 direct rule fields vs. provenance references

The TASK-020 contract distinguishes two categories of TASK-012 rule
information, both read by reference to the loaded rule artifact and the
loaded provenance graph, and both re-exported into the
`EvaluatedRulePackAuthority` and the §11.5 provenance record:

- **direct rule-artifact fields**: `rule_id`, `rule_version`,
  `canonical_hash`, `source_class`, `license_evidence`,
  `approval_status`. These fields live on the TASK-012 rule artifact
  itself. TASK-020 reads them directly and MUST NOT re-describe them as
  fields inside a provenance record.
- **provenance references**: edge IDs and evidence refs that point into
  the TASK-012 `provenance_edges` list of the loaded pack. TASK-020
  carries these as references (edge IDs, evidence refs), not as
  duplicated content. The TASK-020 contract MUST NOT collapse
  `source_class`, `license_evidence` or `approval_status` into the
  provenance record; those are direct fields.

The §11.5 provenance record therefore contains, per selected rule, the
rule ID, the artifact `canonical_hash`, the three direct authority
fields (`source_class`, `license_evidence`, `approval_status`) and the
list of provenance edge IDs. It does not contain a separate
"provenance-level `approval_status`" field.

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
- case authority: the complete `CaseRevisionAuthority` value object
  (§7.3), copied by reference;
- evaluated rule-pack authority: the complete
  `EvaluatedRulePackAuthority` value object (§6.3.5), copied by
  reference. For `INTERNAL_GENERIC` mode, the rule-pack slot is
  `null`. The input-side `RequestedRulePackIdentity` is **not** a
  binding field; only the evaluated authority is. The evaluated
  authority carries the typed `selected_rule_authorities` list
  (§6.3.5.1) of `SelectedRuleAuthority` value objects, NOT a
  parallel `selected_rule_ids` / `selected_rule_artifact_hashes`
  pair; per-rule identity lives in the `SelectedRuleAuthority`
  value object.
- case authority citation/evidence pointers drawn from the consumed
  TASK-014 `CaseRevision` evidence record;
- per-selected-rule direct authority fields and provenance edge IDs as
  described in §6.3.6 and re-exported by §11.5.

TASK-020 does not introduce a pack-level `approval_status`,
`source_class` or `license_evidence` field on the authority binding.
Those are direct fields of the TASK-012 rule artifact and are re-exported
per selected rule, not collapsed into a single pack-level field.

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
| `requested_rule_pack_identity` | `RequestedRulePackIdentity` or null | required for `APPROVED_RULE_PACK`; `null` for `INTERNAL_GENERIC`; §6.3.4 |
| `evidence_refs` | array of strings | required; may be empty only in `INTERNAL_GENERIC` mode |

The request MUST NOT contain any of the following fields. Their presence
on a request must produce `STC_UNKNOWN_FIELD`:

- the standalone `rule_pack_id`, `rule_pack_version` or
  `rule_pack_canonical_hash` fields previously used to carry the
  identity triple (they have been merged into
  `requested_rule_pack_identity`);
- any evaluated-authority field such as `selected_rule_ids`,
  `selected_rule_artifact_hashes` or `validation_status` (these are
  produced only by the adapter and may appear only on the output
  side, per §6.3.5);
- any `content_hash` or `rule_pack_hash` field (these are forbidden
  by §6.3 and the contract terminology).

### 8.2 Structural token normalization

When present, component tokens must:

1. be trimmed;
2. be normalized to uppercase ASCII;
3. match `^[A-Z0-9][A-Z0-9._-]{0,15}$`;
4. remain opaque to the core schema.

The core must not interpret a token as a particular external-standard symbol.
Exact allowed tokens and combinations are rule-pack concerns.

### 8.3 Authority-mode consistency

For `INTERNAL_GENERIC` (P1-2, binding):

- the only rule-pack field the request carries is
  `requested_rule_pack_identity`, and its value MUST be exactly
  `null` (binding: `requested_rule_pack_identity = null`). The
  legacy `INTERNAL_GENERIC`-null requirements on
  `rule_pack_id`, `rule_pack_version`, `rule_pack_canonical_hash`,
  `rule_pack_authority` and `evaluated_rule_pack_authority` are
  **deleted** from the contract: those names are not request fields in
  this contract revision and a request MUST NOT carry any of them
  under any authority mode;
- component tokens may be null;
- no standard compliance claim may be emitted;
- the `RequestedRulePackIdentity` is a request-side object that exists
  **only** in the `APPROVED_RULE_PACK` mode; in `INTERNAL_GENERIC` mode
  the request's `requested_rule_pack_identity` slot is `null` and the
  adapter MUST NOT treat any other name as the rule-pack slot on the
  request;
- any field whose name is `rule_pack_id`, `rule_pack_version`,
  `rule_pack_canonical_hash`, `rule_pack_authority` or
  `evaluated_rule_pack_authority` on a request is a §8.1
  `STC_UNKNOWN_FIELD` violation, regardless of the value, regardless
  of the authority mode. The contract uses the single name
  `requested_rule_pack_identity` on the request side and
  `EvaluatedRulePackAuthority` on the output side; the legacy names
  above are reserved for no usage in this contract and MUST NOT be
  re-introduced;
- the evaluated rule-pack authority is **output-only**. The request
  MUST NOT carry any evaluated result (e.g. selected rule IDs, rule
  artifact hashes, validation status); any such field on the request
  is a `STC_UNKNOWN_FIELD` violation per §8.1.

For `APPROVED_RULE_PACK`:

- the request MUST carry a non-null `requested_rule_pack_identity`
  with the three frozen fields `rule_pack_id`, `rule_pack_version`
  and `rule_pack_canonical_hash`;
- all three component tokens are required unless the approved rule
  pack explicitly declares a different structural requirement;
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
| `authority_binding` | object | normalized §7.5 authority data; for `APPROVED_RULE_PACK` this object carries the complete `EvaluatedRulePackAuthority` value object (§6.3.5), which itself carries the typed `selected_rule_authorities: list[SelectedRuleAuthority]` (§6.3.5.1) in the §12.4 order — per-rule identity (`rule_id`, `rule_version`, `rule_artifact_canonical_hash`, `source_class`, `license_evidence`, `approval_status`, `provenance_edge_ids`, `evidence_refs`) lives inside each `SelectedRuleAuthority` value object, never as a parallel list; for `INTERNAL_GENERIC` the rule-pack slot is `null` |
| `case_authority` | object | the complete `CaseRevisionAuthority` value object (§7.3), copied by reference; carries `revision_id`, `payload_hash`, `domain_snapshot_hash`, `revision_status` |
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
- `STC_RULE_PACK_REQUIRED` (transitional Slice-A blocker; superseded
  by the three codes below per Design Amendment 001 §19.G; S2
  implementation MUST stop emitting it)
- `STC_RULE_PACK_ADAPTER_INPUTS_MISSING` — `APPROVED_RULE_PACK`
  mode request reached the TASK-020 adapter with **both**
  `loaded_rule_pack` and `validation_report` absent. The adapter
  cannot evaluate rule-pack authority against an empty input
  pair and the adapter MUST emit this blocker (fail-closed).
- `STC_RULE_PACK_ADAPTER_INPUTS_INCOMPLETE` — `APPROVED_RULE_PACK`
  mode request reached the TASK-020 adapter with **exactly one**
  of `loaded_rule_pack` or `validation_report` absent. A
  partial adapter input pair cannot satisfy the §6.3.3
  cross-input consistency check and the adapter MUST emit this
  blocker (fail-closed).
- `STC_RULE_PACK_NOT_EXPECTED_IN_MODE` — request reached the
  TASK-020 adapter in `INTERNAL_GENERIC` mode with **either**
  `loaded_rule_pack` or `validation_report` present.
  Rule-pack authority is forbidden in `INTERNAL_GENERIC` mode
  and the adapter MUST emit this blocker.
- `STC_RULE_PACK_NOT_FOUND`
- `STC_RULE_PACK_VALIDATION_FAILED` — TASK-012 `validate_rule_pack(root)`
  did not return `status = "ok"`. The TASK-020 adapter does not
  re-run TASK-012 verification; this code is reserved for the case
  where TASK-012 itself reported a non-`ok` status.
- `STC_RULE_PACK_VALIDATION_REPORT_MISMATCH` — TASK-012 returned
  `status = "ok"` but the report disagrees with the loaded pack or the
  request identity (per §6.3.3). The TASK-012 report, the loaded
  `LoadedRulePackView` and the `RequestedRulePackIdentity` must
  describe the same pack; otherwise this blocker is emitted.
- `STC_REQUESTED_RULE_PACK_IDENTITY_MISSING` — `APPROVED_RULE_PACK`
  mode request did not supply a `requested_rule_pack_identity`.
- `STC_REQUESTED_RULE_PACK_IDENTITY_MISMATCH` — at least one field of
  `requested_rule_pack_identity` does not match the corresponding
  field of the loaded pack manifest.
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
- `STC_RULE_TYPE_UNRECOGNIZED` — a rule body's `rule_type` is outside
  the closed TASK-020 type set per §12.3 / §12.8. The TASK-020
  profile is uniquely identified by
  `profile_id == "task020.configuration-rule.v1"`; a rule with that
  profile_id and an unknown `rule_type` MUST emit this blocker.
- `STC_RULE_DUPLICATE_IDENTITY` — two selected rules share the same
  `(profile_id, rule_type, constraint_id)` triple; resolution is
  fail-closed per §12.5.
- `STC_RULE_APPLICABILITY_UNRESOLVED` — applicability matching could
  not determine whether a rule applies.
- `STC_RULE_CONSTRAINT_MISSING` — a constraint class required by
  the §12.9 required-constraint matrix for the current
  `(authority_mode, construction_family)` is absent from the
  selected set.
- `STC_RULE_NORMALIZATION_CONFLICT` — two
  `CONSTRUCTION_FAMILY_NORMALIZATION` rules apply to the same input
  value and produce different `normalized_value` results
  (per §12.5).
- `STC_RULE_RANGE_INTERSECTION_EMPTY` — two `PASS_COUNT_ALLOWED_RANGE`
  rules apply and their inclusive range intersection is empty
  (per §12.5).
- `STC_RULE_ORIENTATION_INTERSECTION_EMPTY` — two `ORIENTATION_ALLOWLIST`
  rules apply and their orientation intersection is empty
  (per §12.5).
- `STC_RULE_TOKEN_INTERSECTION_EMPTY` — two `COMPONENT_TOKEN_ALLOWLIST`
  rules apply to the same slot and their token intersection is empty
  (per §12.5).
- `STC_RULE_SLOT_NULLABLE_MISSING` — a `construction_family` allows a
  component slot to be `null` but no allowlist rule declares
  `nullable = true` for that slot (per §12.9).
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
- the complete evaluated rule-pack authority: the full
  `EvaluatedRulePackAuthority` value object as defined in §6.3.5,
  carrying the four pack-level fields (`rule_pack_id`,
  `rule_pack_version`, `rule_pack_canonical_hash`,
  `validation_status`) and the typed
  `selected_rule_authorities: list[SelectedRuleAuthority]` list
  (§6.3.5.1) in the §12.4 order. Per-rule identity
  (`rule_id`, `rule_version`, `rule_artifact_canonical_hash`,
  `source_class`, `license_evidence`, `approval_status`,
  `provenance_edge_ids`, `evidence_refs`) lives inside each
  `SelectedRuleAuthority` value object. The TASK-020 contract
  does NOT carry parallel `selected_rule_ids` /
  `selected_rule_artifact_hashes` lists in the canonical payload;
  the canonical form is the `selected_rule_authorities` list, and
  any external projection of rule IDs or rule artifact hashes is
  derived from that list. The input-side `RequestedRulePackIdentity`
  is **not** in the configuration hash; only the evaluated
  authority is.
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
of its own. The blocked-result identity is the SHA-256 hex of the
canonical serialization of the following **complete authority** context
tuple (P1-4, binding), in the §11.4 ordered form:

- the **complete** `CaseRevisionAuthority` value object (§7.3), with
  all four fields (`revision_id`, `payload_hash`,
  `domain_snapshot_hash`, `revision_status`). The complete case
  authority is part of the identity and MUST NOT be omitted; a
  different case revision MUST produce a different blocked identity
  even if every other element of the context tuple is identical;
- the request's `RequestedRulePackIdentity` triple, **when present**
  (i.e. when the request was in `APPROVED_RULE_PACK` mode and
  supplied a non-null identity). The triple is the full input-side
  identity; it MUST NOT be summarized or omitted when present;
- the **complete** `selected_rule_authorities` list (§6.3.5.1) — the
  full list of `SelectedRuleAuthority` value objects, in the §12.4
  sort order. The blocked-result identity MUST include every
  `SelectedRuleAuthority` field by name (`rule_id`,
  `rule_version`, `rule_artifact_canonical_hash`, `source_class`,
  `license_evidence`, `approval_status`, `provenance_edge_ids`,
  `evidence_refs`); a different rule artifact hash, a different
  source class, a different license evidence, or any other per-rule
  field change MUST produce a different blocked identity;
- the **complete** canonical blockers (§10.4) — every blocker object
  with its full five-field shape, in the §11.4 ordered form. The
  blocker subset is NOT sufficient; the identity MUST include every
  field of every blocker (`code`, `field_path`, `message_key`,
  `evidence_refs`, `details`);
- the TASK-020 schema version (`task020.configuration.v1`) and the
  output `schema_version` value, both rendered in their canonical
  string form.

The blocked-result identity MUST NOT be derived from any of the
following, on their own: a list of selected rule IDs only; a list of
selected rule artifact hashes only; the blocker code subset only; or
any other non-complete projection of the context tuple. Two
configurations that differ in case revision, in any
`SelectedRuleAuthority` field, or in any blocker field MUST produce
different blocked identities; collapsing those differences into a
shorter projection is a §11.2.1 violation.

The blocked-result identity is recorded in the surrounding run
provenance, not in the configuration hash, and is used only to
distinguish one blocked outcome from another in audit and CI
artifacts. The full authority-bound identity above guarantees that
different case revisions, different rule artifact hashes, and
different evidence records cannot collapse to the same audit
identity.

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
- `selected_rule_authorities` inside the `EvaluatedRulePackAuthority`:
  the list order is produced by the §12.4 full deterministic sort
  key on the complete `SelectedRuleAuthority` value object. The
  `provenance_edge_ids` and `evidence_refs` inside each
  `SelectedRuleAuthority` are sorted in ascending Unicode
  code-point order at canonicalization time and deduplicated at
  construction time. The TASK-020 contract does NOT maintain
  parallel `selected_rule_ids` and `selected_rule_artifact_hashes`
  lists at canonicalization time; the canonical form is the
  `selected_rule_authorities` list itself.

Input object-key, input evidence-reference order, or input warning /
blocker order MUST NOT alter the hash.

### 11.5 Provenance

The authority binding must retain, by reference to the consumed TASK-014
and TASK-012 contracts:

- the complete `CaseRevisionAuthority` value object (§7.3), carrying
  `revision_id`, `payload_hash`, `domain_snapshot_hash` and
  `revision_status`;
- the complete `EvaluatedRulePackAuthority` value object (§6.3.5),
  carrying `rule_pack_id`, `rule_pack_version`,
  `rule_pack_canonical_hash`, `validation_status = "ok"` and the
  typed `selected_rule_authorities: list[SelectedRuleAuthority]`
  (§6.3.5.1) in the §12.4 order. The per-rule fields
  (`rule_id`, `rule_version`, `rule_artifact_canonical_hash`,
  `source_class`, `license_evidence`, `approval_status`,
  `provenance_edge_ids`, `evidence_refs`) live inside each
  `SelectedRuleAuthority` value object;
- for each selected rule, the rule's direct rule-artifact fields
  (`rule_id`, `rule_version`, `canonical_hash`, `source_class`,
  `license_evidence`, `approval_status`) and the list of TASK-012
  provenance edge IDs that the adapter consulted. The direct fields
  live on the TASK-012 rule artifact; the edge IDs are references
  into the loaded `provenance_edges` list. The TASK-020 contract
  MUST NOT collapse the direct fields into the provenance edge
  contents; the per-rule identity is the §6.3.5.1
  `SelectedRuleAuthority` value object, not a per-rule section
  of the §11.5 record;
  `evidence_refs`;
- the TASK-020 schema version;
- the implementation package version and the surrounding Git commit in
  the surrounding run provenance, not in the configuration hash.

`RequestedRulePackIdentity` is the input-side identity and is **not**
re-exported by §11.5; only the post-evaluation
`EvaluatedRulePackAuthority` appears in the provenance record.

## 12. Configuration rule profile and adapter boundary

TASK-020 introduces no heat-transfer, hydraulic, mechanical or cost equation
and therefore creates no engineering correlation entry. The TASK-020
implementation provides a configuration-rule adapter over the existing
TASK-012 runtime, subject to the frozen profile, signature, selection
discipline and conflict semantics defined in this section. Every
section of this contract that uses the phrase "TASK-020 rule", "TASK-020
rule pack" or "rule pack" refers to the closed set of TASK-012 rule
artifacts whose `profile_id` is exactly
`"task020.configuration-rule.v1"` (§12.2); the TASK-020 adapter
deliberately does not see, evaluate, or block on rules whose
`profile_id` is anything else, and the adapter is not a generic
TASK-012 evaluator.

### 12.1 Adapter signature (frozen)

The TASK-020 adapter exposes exactly the following entry point. The
adapter does not expose a filesystem-path-taking overload and does
not re-implement TASK-012 license, hash, provenance or approval
verification.

```text
ConfigurationRulePackAdapter.validate(
    request: ShellAndTubeConfigurationRequest,
    loaded_rule_pack: LoadedRulePackView,
    validation_report: RulePackValidationReport,
) -> ConfigurationRuleEvaluation
```

`loaded_rule_pack` and `validation_report` are TASK-020-owned typed
views over the plain `dict` results of the existing TASK-012
`load_rule_pack(root)` and `validate_rule_pack(root)` interfaces
(§6.3.1 and §6.3.2). The §6.3.3 cross-input consistency check runs
before any rule evaluation; the adapter MUST stop with
`STC_RULE_PACK_VALIDATION_REPORT_MISMATCH` if that check fails, and
MUST stop with `STC_RULE_PACK_VALIDATION_FAILED` if
`validation_report.status != "ok"`. Once those checks have passed,
the adapter performs rule selection, evaluation and intersection per
the rest of this section.

The adapter does **not** perform any of the following: TASK-012
license verification, TASK-012 hash verification, TASK-012 provenance
verification, rule `approval_status` checking, or reloading the pack
from a filesystem path. It assumes those checks have already passed
at the call boundary and that `validation_report.status == "ok"` and
`loaded_rule_pack` is the TASK-012 loader result for the same pack.

### 12.2 TASK-020 configuration rule profile (frozen)

The TASK-020 adapter consumes only rules whose body carries the
frozen `profile_id`:

```text
profile_id = "task020.configuration-rule.v1"
```

The TASK-020 adapter treats the pack as a heterogeneous container.
During profile selection it ignores every rule whose `profile_id` is
not exactly the frozen value: those rules are **not** selected, **not**
evaluated, and **not** the source of any TASK-020 blocker or warning.
The TASK-020 contract does not emit any "unknown profile" blocker for
non-TASK-020 rules; the only profile-related blocker is
`STC_RULE_TYPE_UNRECOGNIZED`, which fires only when a rule has the
frozen TASK-020 `profile_id` but a `rule_type` outside the closed set
in §12.3.

### 12.3 Frozen rule type set

The TASK-020 adapter recognizes the following closed set of
`rule_type` values. Each rule body MUST follow the frozen JSON shape
defined in §12.8 (envelope) and §12.8.1–§12.8.5 (per-type payloads);
the adapter MUST NOT interpret any field outside these shapes, MUST
NOT discover rule types dynamically, and MUST NOT interpret a
`rule_type` that is not in the set below.

| Frozen `rule_type` | Detailed payload | Match / result predicate |
|---|---|---|
| `COMPONENT_TOKEN_ALLOWLIST` | §12.8.1 | token-in-allowlist passes; otherwise `STC_TOKEN_UNSUPPORTED_BY_RULE_PACK` |
| `CONFIGURATION_COMBINATION_BLOCKLIST` | §12.8.2 | full triple match blocks; otherwise no effect |
| `CONSTRUCTION_FAMILY_NORMALIZATION` | §12.8.3 | input value normalized; conflicts blocker per §12.5 |
| `PASS_COUNT_ALLOWED_RANGE` | §12.8.4 | inclusive range check; otherwise `STC_PASS_COUNT_INVALID` |
| `ORIENTATION_ALLOWLIST` | §12.8.5 | orientation-in-allowlist passes; otherwise `STC_ORIENTATION_INVALID` |

The TASK-020 closed `rule_type` set is exactly the five names listed
in the table above. Any `rule_type` outside that set is an unknown
`rule_type` for TASK-020 purposes and MUST emit
`STC_RULE_TYPE_UNRECOGNIZED` (when the rule body's `profile_id` is
the frozen TASK-020 profile) or be silently ignored (when the
`profile_id` is not the frozen TASK-020 profile). The TASK-020
contract does not enumerate the previously-superseded type names in
the body of this section; the table above is the single source of
valid `rule_type` values, and any `rule_type` not listed there is
unknown by definition.

### 12.4 Rule selection sort key (frozen, complete)

After profile filtering and per-type applicability, the surviving
rules are sorted by the complete deterministic key below, ascending,
with no tie-break on filesystem, manifest-array or dict iteration
order. The key uses only TASK-012 rule-artifact direct fields, so the
sort is fully determined by rule authority:

```text
(
    priority ASC,
    rule_type ASC,
    constraint_id ASC,
    rule_id ASC,
    rule_version ASC,
    rule_artifact_canonical_hash ASC
)
```

`rule_id`, `rule_version` and `rule_artifact_canonical_hash` are
TASK-012 rule-artifact direct fields (read by reference from the
`rules` list inside `loaded_rule_pack`). The TASK-020 adapter MUST
NOT use the order of rules inside the loaded pack filesystem, the
order of fields inside `manifest.json`, the iteration order of any
unordered collection, or any other input-order surrogate as a
tie-breaker. If two distinct rules still share the same full key, the
adapter MUST emit `STC_RULE_DUPLICATE_IDENTITY` and stop.

The sort key above replaces any earlier "input order" tie-break
language; the contract does not use input-order tie-breaks anywhere
in §12 and MUST NOT reintroduce them.

### 12.5 Conflict, intersection and missing-rule semantics (frozen, fail-closed)

The TASK-020 adapter applies the following fail-closed rules on the
sorted rule set. The general precedence rule from an earlier draft
(generic `ALLOW` vs `BLOCK` priority) is **removed**; the predicates
below are exhaustive and the §12.4 sort key is the only precedence
mechanism.

1. **Duplicate rule identity (P1-5, binding)**: two surviving rules
   sharing the same `(profile_id, rule_type, constraint_id)` triple
   MUST emit `STC_RULE_DUPLICATE_IDENTITY` and stop. Two surviving
   rules sharing the same full §12.4 sort key MUST also emit
   `STC_RULE_DUPLICATE_IDENTITY` and stop. The full §12.4 sort key
   `(priority, rule_type, constraint_id, rule_id, rule_version,
   rule_artifact_canonical_hash)` is the **complete comparison key**
   for exact duplicate detection. The TASK-020 adapter compares the
   complete key, not a partial key, when deciding whether two rules
   are exact duplicates:
   - if the complete keys are equal, the two rules are exact
     duplicates; the adapter MUST deduplicate silently (keep one
     instance) and MUST NOT emit any blocker, because the complete
     comparison key fully identifies them as the same logical rule
     with the same authority;
   - if the complete keys differ in any field (including
     `rule_artifact_canonical_hash`, `rule_version`, `priority`,
     `rule_type` or `constraint_id`), the two rules are distinct
     by authority. The TASK-020 adapter MUST NOT treat them as
     duplicates; the §12.4 sort key with all six fields is the only
     tie-break, and any two rules whose complete keys differ are
     semantically distinct and MUST be preserved as separate
     selected rules;
   - if two rules share the same `(profile_id, rule_type,
     constraint_id)` triple but differ in any other field of the
     full key, they are not exact duplicates but they are
     **same-logical-identity with different authority** and the
     adapter MUST emit `STC_RULE_DUPLICATE_IDENTITY` and stop. The
     dedup-by-complete-key policy above is a strict equality
     policy: equal complete keys deduplicate, different complete
     keys never deduplicate. The TASK-020 contract MUST NOT
     introduce a partial-key dedup that conflates different
     authority with the same logical identity.
   - The deterministic sort key MUST cover every authority field
     above and is the **only** tie-break used for selection. The
     adapter MUST NOT use filesystem order, manifest-array order,
     dict-iteration order, dict-insertion order, input rule-list
     order or any other input-order surrogate as a tie-break. If
     the complete key above still cannot distinguish two rules
     (a future-proofing note for arbitrary future rule fields), the
     adapter MUST fail closed: emit `STC_RULE_DUPLICATE_IDENTITY`
     and stop. The complete key in this contract revision is
     sufficient for the closed §12.3 rule_type set; the fail-closed
     fallback is a §12.5 binding rule for any future addition.
2. **Normalisation conflict**: if two
   `CONSTRUCTION_FAMILY_NORMALIZATION` rules apply to the same input
   value and produce different `normalized_value` results, the
   adapter MUST emit `STC_RULE_NORMALIZATION_CONFLICT` and stop.
3. **Range intersection**: when more than one
   `PASS_COUNT_ALLOWED_RANGE` rule applies to the current
   `construction_family`, the adapter MUST compute the inclusive
   intersection of the shell-pass-count and tube-pass-count ranges.
   If the intersection is empty on either axis, the adapter MUST
   emit `STC_RULE_RANGE_INTERSECTION_EMPTY` and stop.
4. **Orientation intersection**: when more than one
   `ORIENTATION_ALLOWLIST` rule applies, the adapter MUST compute the
   intersection of their `allowed_orientations` lists. If the
   intersection is empty, the adapter MUST emit
   `STC_RULE_ORIENTATION_INTERSECTION_EMPTY` and stop.
5. **Token intersection**: when more than one
   `COMPONENT_TOKEN_ALLOWLIST` rule applies to the same
   `component_slot` for the current `construction_family`, the
   adapter MUST compute the intersection of their `allowed_tokens`
   lists. If the intersection is empty, the adapter MUST emit
   `STC_RULE_TOKEN_INTERSECTION_EMPTY` and stop.
6. **Blocklist application**: every applicable
   `CONFIGURATION_COMBINATION_BLOCKLIST` rule is evaluated against
   the request. If **any one** rule's `blocked_combination` pattern
   matches the request's `(front_head_token, shell_token,
   rear_head_token)` triple (with the §12.8.2 OR-within-field,
   AND-across-fields match semantics), the adapter MUST emit
   `STC_CONFIGURATION_COMBINATION_BLOCKED` and stop. Matching
   multiple blocklist rules does not multiply the effect; one
   blocker is emitted.
7. **Required-constraint matrix** (per §12.9): for the current
   `(authority_mode, construction_family)`, if a required
   constraint class has no surviving rule, the adapter MUST emit
   `STC_RULE_CONSTRAINT_MISSING` and stop. The matrix in §12.9 is
   the only source of required-constraint truth.
8. **Unresolved applicability**: if applicability matching cannot
   determine whether a rule applies (for example, a rule whose
   `applies_to_construction_families` array is empty or whose
   `applies_to_authority_modes` array is empty), the adapter MUST
   emit `STC_RULE_APPLICABILITY_UNRESOLVED` and stop.
9. **Unrecognized rule type under TASK-020 profile**: any rule whose
   `profile_id` is the frozen TASK-020 value but whose `rule_type`
   is not in the closed §12.3 set MUST emit
   `STC_RULE_TYPE_UNRECOGNIZED` and stop. There is no
   "skip unknown profile" behavior; the only "skip" applies to rules
   with a different `profile_id`, and that skip emits no blocker.

**Obsolete blocker codes (P1-5, historical, removed)**: the
following codes were present in earlier contract revisions and are
**removed** from the closed §10.2 blocker set in this contract
revision. They are recorded here only as historical reference; the
contract MUST NOT re-introduce them:

- `STC_RULE_PROFILE_UNRECOGNIZED` — removed because the TASK-020
  contract treats a non-TASK-020 `profile_id` as a silent skip
  (per §12.2) and the contract MUST NOT simultaneously skip a
  rule and emit a profile-unrecognized blocker. The
  profile-mismatch path is a no-op skip, not a blocker. A rule
  with the TASK-020 `profile_id` and a bad `rule_type` is the
  only profile-related blocker, encoded as
  `STC_RULE_TYPE_UNRECOGNIZED`. A future round may add a
  profile-required blocker under separate authorization, but the
  historical `STC_RULE_PROFILE_UNRECOGNIZED` code is reserved for
  no usage and MUST NOT be re-introduced as a synonym for the
  no-op skip.
- `STC_RULE_PRIORITY_CONFLICT` — removed because the generic
  `ALLOW` vs `BLOCK` priority-precedence rule that this code
  enforced has been deleted (the §12.4 sort key is the only
  selection precedence mechanism). With the generic priority
  precedence removed, the conflict that this code resolved cannot
  occur in this contract revision, and a priority-conflict
  blocker has no remaining semantics. The `STC_RULE_DUPLICATE_IDENTITY`
  code above is the fail-closed code for any authority-based
  duplicate-detection condition. The historical
  `STC_RULE_PRIORITY_CONFLICT` code is reserved for no usage and
  MUST NOT be re-introduced.

Fail-closed means: on any of the conditions above, the adapter does
not produce a `ConfigurationRuleEvaluation`; the calling
`ConfigurationRulePackAdapter.validate` returns a
`ConfigurationValidationResult(status = BLOCKED)` carrying the
appropriate §10.2 blocker code.

### 12.6 Citation and evidence

`evidence_refs` on each rule body is preserved by the adapter into
the result's `ConfigurationRuleEvaluation` and is the basis for the
`evidence_refs` field of any §10.4 warning or blocker the
configuration later emits. The TASK-020 contract does not collapse
`source_class`, `license_evidence` or `approval_status` into
`evidence_refs`; those are direct rule-artifact fields per §6.3.6.

### 12.7 Adapter non-actions (frozen)

The adapter MUST NOT:

- embed a copied restricted-standard table in core code;
- infer rules from bibliographic metadata alone;
- execute an unapproved rule;
- treat a token match as legal certification;
- extrapolate when a rule pack lacks a required rule;
- take a filesystem path, a URL, or any other out-of-band input in
  place of `loaded_rule_pack` or `validation_report`;
- re-verify TASK-012 license, hash, provenance, canonical-hash or
  approval status;
- output any engineering value, numeric coefficient, expected output
  or standard quote;
- read the clock, network, environment, locale or unordered
  filesystem state;
- use filesystem, manifest-array or dict-iteration order as a
  selection tie-breaker;
- produce an evaluated rule-pack authority before the cross-input
  consistency check (§6.3.3) has passed.

Missing semantic authority returns a blocker, never a best-effort
result.

### 12.8 Rule type payloads and predicates (frozen)

The TASK-020 rule-body envelope is:

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "<closed type, see §12.3>",
  "constraint_id": "<opaque non-empty string>",
  "priority": 0,
  "applies_to_authority_modes": ["APPROVED_RULE_PACK"],
  "applies_to_construction_families": ["FIXED_TUBESHEET"],
  "evidence_refs": []
}
```

The envelope is **frozen** as follows:

- `priority` is a non-negative integer; smaller value sorts earlier.
- `applies_to_authority_modes` MUST be a non-empty array; the
  adapter normalizes it to the deduplicated, ascending
  Unicode-code-point-order form. An empty array after normalization
  is a `STC_RULE_APPLICABILITY_UNRESOLVED` blocker.
- `applies_to_construction_families` MUST be a non-empty array;
  same normalization as above.
- Any field outside this envelope (apart from the per-type payload
  fields below) MUST emit `STC_UNKNOWN_FIELD`.
- `profile_id` and `rule_type` are closed values; any other value is
  a `STC_RULE_TYPE_UNRECOGNIZED` blocker when the profile matches,
  or a no-op skip when the profile does not match.

The five frozen `rule_type` payloads follow.

#### 12.8.1 `COMPONENT_TOKEN_ALLOWLIST`

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "COMPONENT_TOKEN_ALLOWLIST",
  "constraint_id": "<id>",
  "priority": 0,
  "applies_to_authority_modes": ["APPROVED_RULE_PACK"],
  "applies_to_construction_families": ["FIXED_TUBESHEET"],
  "component_slot": "front_head",
  "nullable": false,
  "allowed_tokens": ["TOKEN_A"],
  "evidence_refs": []
}
```

Predicate:

- the rule applies if the request's `construction_family` is in
  `applies_to_construction_families` AND
  `applies_to_authority_modes` contains `APPROVED_RULE_PACK` AND the
  request's `authority_mode` is `APPROVED_RULE_PACK`;
- the rule targets exactly one `component_slot` (one of
  `front_head`, `shell`, `rear_head`);
- the request's token for that slot:
  - if `nullable = true` AND the request's token for the slot is
    `null`: pass;
  - else if the request's token is in `allowed_tokens`: pass;
  - else: emit `STC_TOKEN_UNSUPPORTED_BY_RULE_PACK`.
- the predicate is read by the §12.5 token-intersection rule across
  multiple applicable rules; an empty intersection emits
  `STC_RULE_TOKEN_INTERSECTION_EMPTY` and stops.
- The adapter MUST NOT use any `effect` field. The type name
  encodes the effect.

#### 12.8.2 `CONFIGURATION_COMBINATION_BLOCKLIST`

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "CONFIGURATION_COMBINATION_BLOCKLIST",
  "constraint_id": "<id>",
  "priority": 0,
  "applies_to_authority_modes": ["APPROVED_RULE_PACK"],
  "applies_to_construction_families": ["FIXED_TUBESHEET"],
  "blocked_combination": {
    "front_head_token": ["TOKEN_A"],
    "shell_token": ["TOKEN_B"],
    "rear_head_token": ["TOKEN_C"]
  },
  "evidence_refs": []
}
```

Predicate:

- the rule applies if the request's `construction_family` is in
  `applies_to_construction_families` AND
  `applies_to_authority_modes` contains `APPROVED_RULE_PACK` AND the
  request's `authority_mode` is `APPROVED_RULE_PACK`;
- the rule matches when, **simultaneously** (AND across the three
  fields):
  - the request's `front_head_token` is one of the strings in
    `blocked_combination.front_head_token`, OR the
    `blocked_combination.front_head_token` array is empty (which
    matches every value of the field, including `null`);
  - the request's `shell_token` is one of the strings in
    `blocked_combination.shell_token`, OR the array is empty;
  - the request's `rear_head_token` is one of the strings in
    `blocked_combination.rear_head_token`, OR the array is empty;
- on match, emit `STC_CONFIGURATION_COMBINATION_BLOCKED` and stop.
- The type name encodes the effect; the adapter MUST NOT use any
  `effect` field.

#### 12.8.3 `CONSTRUCTION_FAMILY_NORMALIZATION`

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "CONSTRUCTION_FAMILY_NORMALIZATION",
  "constraint_id": "<id>",
  "priority": 0,
  "applies_to_authority_modes": ["APPROVED_RULE_PACK"],
  "input_value": "FIXED_TUBESHEET",
  "normalized_value": "FIXED_TUBESHEET",
  "evidence_refs": []
}
```

Predicate:

- the rule applies if the request's `authority_mode` is in
  `applies_to_authority_modes` AND the request's
  `construction_family` equals `input_value`;
- on apply, the rule contributes its `normalized_value` as a
  candidate output. The §12.9 required-constraint matrix freezes
  this rule type as required for the
  `APPROVED_RULE_PACK` × `construction_family` rows; if no
  `CONSTRUCTION_FAMILY_NORMALIZATION` rule applies for the current
  `construction_family` in `APPROVED_RULE_PACK` mode, the adapter
  MUST emit `STC_RULE_CONSTRAINT_MISSING` and stop.
- if two applicable rules produce different `normalized_value`
  results, the adapter MUST emit `STC_RULE_NORMALIZATION_CONFLICT`
  and stop. The TASK-020 adapter MUST NOT pick a winner by
  filesystem order, manifest order, priority or any other surrogate
  when the `input_value` matches and the `normalized_value` results
  differ.

#### 12.8.4 `PASS_COUNT_ALLOWED_RANGE`

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "PASS_COUNT_ALLOWED_RANGE",
  "constraint_id": "<id>",
  "priority": 0,
  "applies_to_authority_modes": ["APPROVED_RULE_PACK"],
  "applies_to_construction_families": ["FIXED_TUBESHEET"],
  "shell_pass_count": {"min_inclusive": 1, "max_inclusive": 2},
  "tube_pass_count": {"min_inclusive": 1, "max_inclusive": 8},
  "evidence_refs": []
}
```

Predicate:

- the rule applies if the request's `construction_family` is in
  `applies_to_construction_families` AND
  `applies_to_authority_modes` contains `APPROVED_RULE_PACK` AND
  the request's `authority_mode` is `APPROVED_RULE_PACK`;
- `min_inclusive <= max_inclusive` is required for both fields; a
  rule with `min_inclusive > max_inclusive` is malformed and MUST
  emit `STC_RULE_APPLICABILITY_UNRESOLVED`;
- the request passes if BOTH `shell_pass_count` and `tube_pass_count`
  are within their respective inclusive ranges;
- otherwise the request fails; if at least one
  `PASS_COUNT_ALLOWED_RANGE` rule applies, the request fails with
  `STC_PASS_COUNT_INVALID`;
- when more than one `PASS_COUNT_ALLOWED_RANGE` rule applies, the
  adapter computes the inclusive range intersection per axis per
  §12.5. Empty intersection on either axis emits
  `STC_RULE_RANGE_INTERSECTION_EMPTY` and stops;
- this rule type is required by the §12.9 required-constraint matrix
  for the `APPROVED_RULE_PACK` rows. If no rule applies in
  `APPROVED_RULE_PACK` mode, the adapter MUST emit
  `STC_RULE_CONSTRAINT_MISSING`.

#### 12.8.5 `ORIENTATION_ALLOWLIST`

```json
{
  "profile_id": "task020.configuration-rule.v1",
  "rule_type": "ORIENTATION_ALLOWLIST",
  "constraint_id": "<id>",
  "priority": 0,
  "applies_to_authority_modes": ["APPROVED_RULE_PACK"],
  "applies_to_construction_families": ["FIXED_TUBESHEET"],
  "allowed_orientations": ["HORIZONTAL", "VERTICAL"],
  "evidence_refs": []
}
```

Predicate:

- the rule applies if the request's `construction_family` is in
  `applies_to_construction_families` AND
  `applies_to_authority_modes` contains `APPROVED_RULE_PACK` AND
  the request's `authority_mode` is `APPROVED_RULE_PACK`;
- the request passes if its `orientation` is in
  `allowed_orientations`;
- otherwise fails with `STC_ORIENTATION_INVALID`;
- when more than one rule applies, the adapter computes the
  intersection per §12.5. Empty intersection emits
  `STC_RULE_ORIENTATION_INTERSECTION_EMPTY` and stops;
- required by the §12.9 matrix for the `APPROVED_RULE_PACK` rows.
  No applicable rule in `APPROVED_RULE_PACK` mode emits
  `STC_RULE_CONSTRAINT_MISSING`.

### 12.9 Required-constraint matrix (frozen)

The TASK-020 contract freezes the following required-constraint
matrix, keyed by `(authority_mode, construction_family)`. The
matrix is exhaustive; rows not listed below have no required
constraint classes.

| `authority_mode` | `construction_family` | required rule classes |
|---|---|---|
| `INTERNAL_GENERIC` | `FIXED_TUBESHEET` | none |
| `INTERNAL_GENERIC` | `U_TUBE` | none |
| `INTERNAL_GENERIC` | `FLOATING_HEAD` | none |
| `APPROVED_RULE_PACK` | `FIXED_TUBESHEET` | `CONSTRUCTION_FAMILY_NORMALIZATION`, the three `COMPONENT_TOKEN_ALLOWLIST` slot rules (`front_head`, `shell`, `rear_head`), `PASS_COUNT_ALLOWED_RANGE`, `ORIENTATION_ALLOWLIST` |
| `APPROVED_RULE_PACK` | `U_TUBE` | `CONSTRUCTION_FAMILY_NORMALIZATION`, the three `COMPONENT_TOKEN_ALLOWLIST` slot rules, `PASS_COUNT_ALLOWED_RANGE`, `ORIENTATION_ALLOWLIST` |
| `APPROVED_RULE_PACK` | `FLOATING_HEAD` | `CONSTRUCTION_FAMILY_NORMALIZATION`, the three `COMPONENT_TOKEN_ALLOWLIST` slot rules, `PASS_COUNT_ALLOWED_RANGE`, `ORIENTATION_ALLOWLIST` |

`CONFIGURATION_COMBINATION_BLOCKLIST` is not a required class for
any row; the pack may contain zero or more blocklist rules, and any
applicable blocklist rule that matches the request triggers
`STC_CONFIGURATION_COMBINATION_BLOCKED`.

When the matrix requires a `COMPONENT_TOKEN_ALLOWLIST` rule for a
slot but the rule declares `nullable = false` and the request's
token for the slot is `null`, the adapter MUST emit
`STC_TOKEN_UNSUPPORTED_BY_RULE_PACK` (the request is asking for
"required" but supplying nothing). A construction family permits
`null` for a slot **only** if an applicable
`COMPONENT_TOKEN_ALLOWLIST` rule for that slot declares
`nullable = true`; otherwise the slot is required to be a non-null
member of the rule's `allowed_tokens`. The TASK-020 contract does
not allow "the rule pack may declare otherwise" outside this exact
mechanism.

### 12.10 Unknown profile / unknown type behavior (frozen, single behavior)

The TASK-020 contract freezes a single, consistent behavior for
profile and type mismatches:

- A TASK-012 pack may contain rules with any `profile_id`; rules
  whose `profile_id` is not exactly
  `"task020.configuration-rule.v1"` are **ignored** by the TASK-020
  adapter during selection. They do not produce a TASK-020
  blocker or warning.
- A rule with the TASK-020 `profile_id` but a `rule_type` outside
  the closed §12.3 set MUST produce `STC_RULE_TYPE_UNRECOGNIZED`
  and stop.

The TASK-020 contract MUST NOT specify both "skip unknown profile"
and "block unknown profile" anywhere; the only skip-without-block
behavior is the cross-profile case above, and the only
profile-must-match blocker is the TASK-020-profile-but-unknown-type
case. The historical `STC_RULE_PROFILE_UNRECOGNIZED` code (see
§12.5) is reserved for no usage in this contract revision and
MUST NOT be re-introduced; the profile-mismatch path is the
silent-skip above, not a blocker.

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

### 14.2 Future implementation allowlist (Design Amendment 001 §19.C)

Design Amendment 001 (Issue #129) supersedes the original
§14.2 implementation allowlist. The future TASK-020 S2
implementation may modify only the **exact 42 files** enumerated
below. No third file is authorized. Any additional path
requires a further design amendment and separate Charles
authorization before mutation.

**Established architecture (Design Amendment 001 §19.B — frozen):**

- production: `src/hexagent/exchangers/shell_tube/`
- tests: `tests/exchangers/shell_tube/`
- fixtures: `tests/fixtures/task020/`

The following paths from the original §14.2 are explicitly
**forbidden** and superseded for TASK-020 implementation:

- `src/hexagent/shell_and_tube/` (any subpath) — forbidden
- `tests/shell_and_tube/` (any subpath) — forbidden
- `src/hexagent/shell_and_tube/configuration.py` — forbidden
- `src/hexagent/shell_and_tube/schema.py` — forbidden
- `tests/shell_and_tube/test_task020_configuration_models.py` — forbidden
- `tests/shell_and_tube/test_task020_configuration_validation.py` — forbidden
- `tests/shell_and_tube/test_task020_configuration_identity.py` — forbidden
- `tests/shell_and_tube/test_task020_license_boundary.py` — forbidden
- `tests/shell_and_tube/test_task020_rule_profile_adapter.py` — replaced by
  `tests/exchangers/shell_tube/test_task020_rule_profile_adapter.py` per §19.H

**Binding count: production 6 + tests 5 + fixtures 30 + manifest 1 = 42 files.**

#### 14.2.1 Production — 6 files

1. `src/hexagent/exchangers/shell_tube/__init__.py`
2. `src/hexagent/exchangers/shell_tube/errors.py`
3. `src/hexagent/exchangers/shell_tube/models.py`
4. `src/hexagent/exchangers/shell_tube/rule_pack_adapter.py`
5. `src/hexagent/exchangers/shell_tube/validation.py`
6. `src/hexagent/exchangers/shell_tube/canonical.py`

#### 14.2.2 Tests — 5 files (all accepted, none renamed)

1. `tests/exchangers/shell_tube/test_task020_rule_profile_adapter.py`
2. `tests/exchangers/shell_tube/test_task020_rule_pack_adapter.py`
3. `tests/exchangers/shell_tube/test_task020_rule_pack_fixtures.py`
4. `tests/exchangers/shell_tube/test_task020_rule_pack_hash_integration.py`
5. `tests/exchangers/shell_tube/test_task020_rule_pack_canonical.py`

Disposition:

- all five filenames are **ACCEPTED**;
- no test is renamed;
- no proposed test is folded into an existing S1 test;
- `test_task020_rule_profile_adapter.py` changes directory only from
  the old frozen path (`tests/shell_and_tube/`) to
  `tests/exchangers/shell_tube/`;
- **no** TASK-020 contract defines
  `test_task020_configuration_rule_pack_adapter.py` (this filename is
  not part of any allowlist and must not be created).

#### 14.2.3 Fixtures — 30 exact files

The complete 30-file fixture enumeration below is preserved
**exactly**. The fixture paths are file paths, not globs. The
implementation MUST NOT use glob patterns, recursive wildcards,
or any other form of bulk fixture discovery. Each fixture file
is named, audited, and listed in this section by hand.

All rule-pack fixtures are `INTERNAL_ENGINEERING_RULE` content
authored under TASK-012 governance; they MUST NOT contain
verbatim copies of TEMA or any other restricted standard text,
table, figure or formula. Token identifiers in the fixtures are
synthetic project-internal strings and carry no
external-standard semantics.

**Case revision — 4 files:**

1. `tests/fixtures/task020/case_revision/case_revision_committed.json`
2. `tests/fixtures/task020/case_revision/case_revision_superseded.json`
3. `tests/fixtures/task020/case_revision/case_revision_archived.json`
4. `tests/fixtures/task020/case_revision/case_revision_draft_blocked.json`

**Valid configuration pack — 15 files:**

1. `tests/fixtures/task020/rule_packs/valid_configuration_pack/manifest.json`
2. `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/component_token_allowlist_front.json`
3. `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/component_token_allowlist_shell.json`
4. `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/component_token_allowlist_rear.json`
5. `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/construction_family_normalization.json`
6. `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/pass_count_allowed_range.json`
7. `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/orientation_allowlist.json`
8. `tests/fixtures/task020/rule_packs/valid_configuration_pack/rules/configuration_combination_blocklist.json`
9. `tests/fixtures/task020/rule_packs/valid_configuration_pack/provenance/component_token_allowlist_front_edge.json`
10. `tests/fixtures/task020/rule_packs/valid_configuration_pack/provenance/component_token_allowlist_shell_edge.json`
11. `tests/fixtures/task020/rule_packs/valid_configuration_pack/provenance/component_token_allowlist_rear_edge.json`
12. `tests/fixtures/task020/rule_packs/valid_configuration_pack/provenance/construction_family_normalization_edge.json`
13. `tests/fixtures/task020/rule_packs/valid_configuration_pack/provenance/pass_count_allowed_range_edge.json`
14. `tests/fixtures/task020/rule_packs/valid_configuration_pack/provenance/orientation_allowlist_edge.json`
15. `tests/fixtures/task020/rule_packs/valid_configuration_pack/provenance/configuration_combination_blocklist_edge.json`

**Conflicting configuration pack — 5 files:**

1. `tests/fixtures/task020/rule_packs/conflicting_configuration_pack/manifest.json`
2. `tests/fixtures/task020/rule_packs/conflicting_configuration_pack/rules/conflict_a.json`
3. `tests/fixtures/task020/rule_packs/conflicting_configuration_pack/rules/conflict_b.json`
4. `tests/fixtures/task020/rule_packs/conflicting_configuration_pack/provenance/conflict_a_edge.json`
5. `tests/fixtures/task020/rule_packs/conflicting_configuration_pack/provenance/conflict_b_edge.json`

**Unapproved pack — 3 files:**

1. `tests/fixtures/task020/rule_packs/unapproved_rule_pack/manifest.json`
2. `tests/fixtures/task020/rule_packs/unapproved_rule_pack/rules/allowed_tokens.json`
3. `tests/fixtures/task020/rule_packs/unapproved_rule_pack/provenance/allowed_tokens_edge.json`

**License-blocked pack — 3 files:**

1. `tests/fixtures/task020/rule_packs/license_blocked_rule_pack/manifest.json`
2. `tests/fixtures/task020/rule_packs/license_blocked_rule_pack/rules/allowed_tokens.json`
3. `tests/fixtures/task020/rule_packs/license_blocked_rule_pack/provenance/allowed_tokens_edge.json`

The fixture allowlist above is the **complete** list of
fixture paths the future TASK-020 S2 implementation may add or
modify. The implementation MUST NOT use glob, wildcard,
recursive discovery, or any unlisted directory-level
authorization. Any additional path requires a design amendment
and separate Charles authorization before mutation.

#### 14.2.4 CI manifest — 1 file

1. `ci-shard-manifest.yml`

Authorized only to register the five new S2 test files in
`tests/exchangers/shell_tube/` (see §14.2.2) into the existing
shard during the later S2 implementation round. The amendment's
own frozen-contract integrity test
(`tests/exchangers/shell_tube/test_task020_frozen_contract_unchanged.py`)
is **not** part of this later 42-file S2 implementation
boundary; it is part of the design-amendment authoring round.

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
   (`STC_RULE_DUPLICATE_IDENTITY` covering both the same
   `(profile_id, rule_type, constraint_id)` triple and the
   same full §12.4 sort key, with same-authority duplicate dedup
   and different-authority same-logical-identity block per §12.5)
   using the `conflicting_configuration_pack` fixture set;
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
- [ ] The TASK-020 adapter freezes the
      `ConfigurationRulePackAdapter.validate(request, loaded_rule_pack:
      LoadedRulePackView, validation_report: RulePackValidationReport)`
      signature; the adapter does not re-implement TASK-012 license,
      hash, provenance or approval verification, and does not pretend
      that TASK-012 exposes any in-memory type that bundles a loaded
      pack with its validation verdict.
- [ ] The cross-input consistency check (§6.3.3) freezes the four
      identity-equality predicates and the two distinct mismatch
      blockers (`STC_RULE_PACK_VALIDATION_REPORT_MISMATCH` for cross-
      input disagreement, `STC_RULE_PACK_VALIDATION_FAILED` for TASK-012
      itself reporting `status != "ok"`).
- [ ] The request carries exactly one rule-pack object, the
      `RequestedRulePackIdentity` (§6.3.4). No standalone
      `rule_pack_id`, `rule_pack_version` or
      `rule_pack_canonical_hash` field remains on the request, and no
      evaluated-authority field (`selected_rule_ids`,
      `selected_rule_artifact_hashes`, `validation_status`) appears
      on the request.
- [ ] The output carries exactly one rule-pack object, the
      `EvaluatedRulePackAuthority` (§6.3.5), containing
      `selected_rule_authorities: list[SelectedRuleAuthority]`. Each
      `SelectedRuleAuthority` carries the complete per-rule authority,
      including `rule_id`, `rule_version`,
      `rule_artifact_canonical_hash` (bound to the TASK-012 rule
      artifact `canonical_hash`, not a separately computed rule-body
      hash), `source_class`, `license_evidence`, `approval_status`,
      `provenance_edge_ids` and `evidence_refs`. No parallel
      `selected_rule_ids` or `selected_rule_artifact_hashes` list is
      part of the authoritative or canonical schema.
- [ ] The TASK-020 rule-pack authority uses the TASK-012 manifest
      `canonical_hash` under the single name
      `rule_pack_canonical_hash`; no `content_hash` or `rule_pack_hash`
      appears as a TASK-020 contract field.
- [ ] No pack-level `approval_status`, `source_class` or
      `license_evidence` is defined on the TASK-020 authority binding;
      those are direct rule-artifact fields under TASK-012 and are
      re-exported per selected rule, not collapsed into a single
      pack-level field.
- [ ] The TASK-020 configuration-rule profile
      (`task020.configuration-rule.v1`) and the closed `rule_type` set
      in §12.3 are frozen with complete JSON shapes; the previous
      five type names are not in the closed set and any rule body
      using one is `STC_RULE_TYPE_UNRECOGNIZED`.
- [ ] The closed `rule_type` set is
      `COMPONENT_TOKEN_ALLOWLIST`,
      `CONFIGURATION_COMBINATION_BLOCKLIST`,
      `CONSTRUCTION_FAMILY_NORMALIZATION`,
      `PASS_COUNT_ALLOWED_RANGE`,
      `ORIENTATION_ALLOWLIST`. None of the per-type payloads uses
      a generic `effect` field; the type name encodes the effect.
- [ ] The full deterministic §12.4 sort key
      `(priority ASC, rule_type ASC, constraint_id ASC, rule_id ASC,
      rule_version ASC, rule_artifact_canonical_hash ASC)` is frozen
      and is the only selection precedence mechanism; no input-order
      tie-break is permitted.
- [ ] The required-constraint matrix (§12.9) is frozen and is the
      only source of required-constraint truth; the matrix rows for
      `INTERNAL_GENERIC` × all families are empty, and the rows for
      `APPROVED_RULE_PACK` × all families require
      `CONSTRUCTION_FAMILY_NORMALIZATION`, the three
      `COMPONENT_TOKEN_ALLOWLIST` slot rules, `PASS_COUNT_ALLOWED_RANGE`
      and `ORIENTATION_ALLOWLIST`.
- [ ] The fixture allowlist (§14.2) lists exact file paths, with
      `valid_configuration_pack`, `conflicting_configuration_pack`,
      `unapproved_rule_pack` and `license_blocked_rule_pack` fixture
      sets; no glob or wildcard fixture discovery is permitted.
- [ ] The canonical hash (§11.2) covers the complete §10.4 warning and
      blocker objects, the complete `CaseRevisionAuthority`, the
      complete `EvaluatedRulePackAuthority` (including the complete
      ordered `selected_rule_authorities: list[SelectedRuleAuthority]`
      in the §12.4 order), the `schema_version` and the frozen
      `deferred_capabilities` list. The canonical payload does not
      contain parallel `selected_rule_ids` or
      `selected_rule_artifact_hashes` lists; any such projections are
      derived views only and are not computation authority. The
      input-side `RequestedRulePackIdentity` is **not** in the
      configuration hash; only the evaluated authority is.
- [ ] `BLOCKED` result identity (§11.2.1) covers the complete authority
      context tuple: the complete `CaseRevisionAuthority`; the
      request's `RequestedRulePackIdentity` when present; the
      complete `selected_rule_authorities: list[SelectedRuleAuthority]`
      in the §12.4 sort order; the ordered, complete §10.4 blocker
      list; the TASK-020 schema version and the output `schema_version`.
      `CaseRevisionAuthority` MUST NOT be excluded. Different case
      revisions, different `SelectedRuleAuthority` fields, or
      different complete blocker objects MUST produce different
      blocked-result identities. The identity MUST NOT be derived from
      any partial projection (rule IDs only, rule artifact hashes
      only, blocker code subset only).
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
| Which adapter boundary does TASK-020 freeze? | `ConfigurationRulePackAdapter.validate(request, loaded_rule_pack: LoadedRulePackView, validation_report: RulePackValidationReport)` per §12.1; the two TASK-020-owned typed views wrap the existing TASK-012 `load_rule_pack(root)` and `validate_rule_pack(root)` interfaces. |
| How does the contract split input identity from evaluated authority? | The request carries `RequestedRulePackIdentity` (§6.3.4); the adapter produces `EvaluatedRulePackAuthority` (§6.3.5) with the typed `selected_rule_authorities: list[SelectedRuleAuthority]` (§6.3.5.1). Each per-rule identity field — `rule_id`, `rule_version`, `rule_artifact_canonical_hash`, `source_class`, `license_evidence`, `approval_status`, `provenance_edge_ids`, `evidence_refs` — lives inside the `SelectedRuleAuthority` value object, never as a parallel list. Only the evaluated authority is in the configuration hash and the §11.5 provenance record. |
| Which rule types are accepted and what are their predicates? | The closed set is `COMPONENT_TOKEN_ALLOWLIST`, `CONFIGURATION_COMBINATION_BLOCKLIST`, `CONSTRUCTION_FAMILY_NORMALIZATION`, `PASS_COUNT_ALLOWED_RANGE`, `ORIENTATION_ALLOWLIST` per §12.3 / §12.8.1–§12.8.5. |
| What is the selection sort key? | The full §12.4 key `(priority ASC, rule_type ASC, constraint_id ASC, rule_id ASC, rule_version ASC, rule_artifact_canonical_hash ASC)`. |
| Which fixture paths are exact? | The four `case_revision/*` files and the four `rule_packs/*` directories in §14.2, each listing its `manifest.json` and per-rule files. |

### 18.3 Authority-resolution synchronization record (post-PR-#123 / post-PR-#125)

This contract revision records the current post-merge governance state
so that PR #118 review can disambiguate the historical TASK-020
authority-collision concern from the current M3 / TASK-020 scope
discipline. The record is informational; it does not retroactively
authorize any TASK-020 implementation.

- The TASK-020 identity collision with the cost-stack governance line
  has been resolved by the **TASK-019 Amendment 002-K** governance
  chain: **PR #123** merged the corrective re-home of the
  cost-stack contract under TASK-019 Amendment 002-K, and **PR #125**
  recorded the post-merge governance closeout. The TASK-020 design
  contract no longer overlaps with the TASK-019 cost-stack scope.
- TASK-019 Amendment 002-K is owned by TASK-019; the
  case_02 cost-stack coverage, fixture-authority, derivation
  protocol, business-source availability gate, R1–R25 status
  distribution and §17A.x amendment-internal numbering are TASK-019
  Amendment 002-K authority and are out of scope for TASK-020.
- TASK-020 remains reserved for the M3 shell-and-tube configuration
  schema foundation. The TASK-020 number is not frozen to any
  specific M3 capability; TASK-020 capability allocation is a
  separate Charles-authorized M3 sequencing round.
- PR #118 is the TASK-020 specific capability allocation **Draft
  proposal** for the shell-and-tube configuration schema
  foundation. PR #118 is NOT the backlog's frozen allocation; the
  Draft proposal is pending independent re-review, Ready
  authorization, and merge authorization.
- PR #125 merge commit: `80f042e51bd5eb3783b1461f4ff1cabe1948109f`
  (= current `origin/main` at the authoring of this §18.3
  record). PR #123 merge commit (the cost-stack re-home):
  `905b46753c33603ebdc61148871e40ffb0481c4f`.
- Issue #122 (`[TASK-019][Amendment 002-K][governance] Re-home
  PR #119 cost-stack contract and restore TASK-020 authority`)
  is **closed / completed** in the repository at the time of
  authoring this §18.3 record. The closure removes the P0
  authority-collision barrier on the TASK-020 review thread;
  closing Issue #122 does not waive any of the P1 design findings
  on PR #118 and does not, on its own, mark PR #118 as Ready,
  approved, or merge-authorized.
- TASK-021 through TASK-039 remain unallocated to any specific
  M3 capability. They remain PLANNED / NOT STARTED unless a separate
  Charles-authorized M3 sequencing amendment round is opened.
- IMPLEMENTATION NOT AUTHORIZED in this design PR. The
  TASK-020 implementation is gated on §16 (Slice A / Slice B) and
  §12.9 (required-constraint matrix) and on a separate
  Charles-authorized implementation Issue. No fixture, expected
  output, cost formula, pressure-drop, thermal-rating, Kern,
  Bell–Delaware, TEMA, mechanical, material, cost, optimization,
  API, report, golden validation or other engineering output is
  introduced by this design PR.
- PR #118 remains Draft, with the previous reviewed head
  `9a24b58c30dde7b008648f60be27a65a4eecc867` superseded by the new
  head in this round after the current-main ancestry sync. PR #118
  Ready, approval and merge each require separate Charles
  authorization.

**Anti-fabrication guard (binding)**: this §18.3 record is the only
place in the TASK-020 contract that references the post-merge main
state. The TASK-020 contract MUST NOT characterize Issue #122
closure as PR #118 Ready, approved, design-frozen or otherwise
authorized. The TASK-020 contract MUST NOT use the post-merge
governance chain to waive P1 design findings, and the TASK-020
contract MUST NOT allocate TASK-021–TASK-039 to specific M3
capabilities. The TASK-020 contract MUST NOT introduce any
engineering equation, coefficient, fixture, expected output, or
restricted-standard text under any round, including any round
that documents the post-merge governance state.

### 18.4 Required closeout evidence

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

## 19. Design Amendment 001 — Issue #129 (S2 integration surface and paths)

Design Amendment 001 (Issue #129) reconciles the original
§14.2 implementation allowlist with the established S1
architecture. It is **design-only** — it does not authorize any
S2 implementation work. S2 implementation remains separately
authorized through Issue #128, which this amendment leaves
unchanged.

### 19.A Amendment authority record

- Authorizing Issue: **#129** — `[TASK-020][design amendment 001] Reconcile S2 integration surface and implementation paths`.
- Branch base (S1 merge): `d00d5ced3c0da065f00096f0303c0709917fc380` (PR #127 merge).
- Branch name (this amendment): `docs/task-020-amendment-001-s2-integration-surface-and-paths`.
- Established S1 architecture (frozen at `d00d5ced`): production under `src/hexagent/exchangers/`, tests under `tests/exchangers/`, fixtures under `tests/fixtures/task020/`.
- This amendment authorizes **design reconciliation only**:
  the design contract's §10.2, §14.2 and a new §19 record are
  edited. No production code, no test, no fixture, no manifest,
  no workflow, no TASK-001 through TASK-019 contract is modified
  by this amendment.
- **S2 implementation remains separately authorized through Issue #128**. Issue #128 is unchanged by this amendment and remains OPEN.
- **TASK-021 through TASK-039 remain unallocated** by this amendment and by TASK-020.

### 19.B Established architecture (frozen)

Design Amendment 001 freezes the following locations as the
only places the future TASK-020 S2 implementation may write
code or place tests:

- production: `src/hexagent/exchangers/shell_tube/`
- tests: `tests/exchangers/shell_tube/`
- fixtures: `tests/fixtures/task020/`

The amendment explicitly forbids creating or duplicating any
path under:

- `src/hexagent/shell_and_tube/` — superseded
- `tests/shell_and_tube/` — superseded

The original §14.2 paths under those two forbidden roots are
**not** valid TASK-020 implementation paths. The amendment
records that those paths are superseded for TASK-020
implementation. Any continuation of work under the forbidden
roots is a §17 anti-fabrication violation.

### 19.C Exact S2 implementation allowlist (42 files)

The future TASK-020 S2 implementation may modify only the
**exact 42 files** enumerated in §14.2.1–§14.2.4, summarized:

- production: **6 files** under `src/hexagent/exchangers/shell_tube/`
- tests: **5 files** under `tests/exchangers/shell_tube/`
- fixtures: **30 files** under `tests/fixtures/task020/`
  - case revision: 4
  - valid configuration pack: 15
  - conflicting configuration pack: 5
  - unapproved pack: 3
  - license-blocked pack: 3
- CI manifest: **1 file** (`ci-shard-manifest.yml`, S2 registration only)

**Binding count: 6 + 5 + 30 + 1 = 42 files.** The amendment's
own frozen-contract integrity test
(`tests/exchangers/shell_tube/test_task020_frozen_contract_unchanged.py`)
is **not** part of this later 42-file S2 implementation
boundary; it is part of the design-amendment authoring round.

All five test filenames are **ACCEPTED** without rename. No
proposed test is folded into an existing S1 test. The path
`test_task020_rule_profile_adapter.py` changes directory only
from `tests/shell_and_tube/` to `tests/exchangers/shell_tube/`.
**No** TASK-020 contract defines
`test_task020_configuration_rule_pack_adapter.py`; that filename
must not be created.

Fixtures are exact file paths. No glob, no wildcard, no
recursive discovery, no project-authored synthetic token list
beyond the listed set, no copied TEMA or restricted-standard
content.

The CI manifest is authorized only to register the five new
S2 test files in the existing shard during the later S2
implementation round.

### 19.D Frozen top-level S2 entry point

The future TASK-020 S2 implementation MUST provide a top-level
entry point with this exact frozen signature:

```python
def validate_request(
    payload: Mapping[str, Any],
    *,
    loaded_rule_pack: LoadedRulePackView | None = None,
    validation_report: RulePackValidationReport | None = None,
) -> ConfigurationValidationResult:
    ...
```

Explicit rules:

- the existing `validate_request(payload)` call (no adapter
  arguments) remains compatible and MUST NOT break;
- `loaded_rule_pack` and `validation_report` are supplied by
  the **caller** — never by `validate_request`;
- `validate_request` MUST NOT construct them from a filesystem
  path;
- `validate_request` MUST NOT accept a filesystem path, an
  environment variable, a clock, a locale, or an unordered
  filesystem traversal as an implicit input;
- `validate_request` MUST NOT call into TASK-012
  verification routines to re-implement them;
- no network lookup, no clock, no environment, no locale, no
  unordered filesystem dependence is allowed in
  `validate_request`.

### 19.E Frozen adapter signature (unchanged)

The TASK-020 adapter signature is preserved unchanged from §12.1:

```python
ConfigurationRulePackAdapter.validate(
    request: ShellAndTubeConfigurationRequest,
    loaded_rule_pack: LoadedRulePackView,
    validation_report: RulePackValidationReport,
) -> ConfigurationRuleEvaluation
```

### 19.F Frozen top-level input-presence semantics

`validate_request` MUST apply the following exact rules.

**`INTERNAL_GENERIC` mode**:

- if **either** `loaded_rule_pack` is present **or**
  `validation_report` is present, return `BLOCKED` with code
  `STC_RULE_PACK_NOT_EXPECTED_IN_MODE`. Both arguments must
  be absent in `INTERNAL_GENERIC` mode.

**`APPROVED_RULE_PACK` mode — both adapter arguments absent**:

- if **both** `loaded_rule_pack is None` and
  `validation_report is None`, return `BLOCKED` with code
  `STC_RULE_PACK_ADAPTER_INPUTS_MISSING`.

**`APPROVED_RULE_PACK` mode — partial presence**:

- if **exactly one** of `loaded_rule_pack` or
  `validation_report` is absent, return `BLOCKED` with code
  `STC_RULE_PACK_ADAPTER_INPUTS_INCOMPLETE`.

**`APPROVED_RULE_PACK` mode — both present**:

- delegate to
  `ConfigurationRulePackAdapter.validate(request, loaded_rule_pack, validation_report)`.

The existing cross-input codes from §6.3.3 remain authoritative
inside the adapter:

- TASK-012 report status is not `"ok"` →
  `STC_RULE_PACK_VALIDATION_FAILED`;
- report, loaded pack and request do not describe the same
  pack → `STC_RULE_PACK_VALIDATION_REPORT_MISMATCH`;
- requested identity absent →
  `STC_REQUESTED_RULE_PACK_IDENTITY_MISSING`;
- requested identity field mismatch →
  `STC_REQUESTED_RULE_PACK_IDENTITY_MISMATCH`;
- canonical hash mismatch →
  `STC_RULE_PACK_CANONICAL_HASH_MISMATCH`.

### 19.G Disposition of `STC_RULE_PACK_REQUIRED`

- `STC_RULE_PACK_REQUIRED` was the transitional Slice-A
  blocker.
- Design Amendment 001 supersedes it for S2.
- The S2 implementation MUST stop emitting
  `STC_RULE_PACK_REQUIRED`.
- It is replaced by three codes (added to §10.2 above):
  - `STC_RULE_PACK_ADAPTER_INPUTS_MISSING`
  - `STC_RULE_PACK_ADAPTER_INPUTS_INCOMPLETE`
  - `STC_RULE_PACK_NOT_EXPECTED_IN_MODE`
- The S2 implementation MUST NOT alias multiple new
  conditions back to `STC_RULE_PACK_REQUIRED`.

### 19.H Test-contract reconciliation

The five accepted S2 tests supplement (not replace) the existing
S1 tests under `tests/exchangers/shell_tube/`. Minimum coverage
mapping:

- `tests/exchangers/shell_tube/test_task020_rule_profile_adapter.py`
  - closed profile ID;
  - five frozen rule types (§12.3);
  - deterministic selection (§12.4);
  - duplicate/conflict/intersection behavior (§12.5).
- `tests/exchangers/shell_tube/test_task020_rule_pack_adapter.py`
  - top-level presence matrix (§19.F);
  - TASK-012 report status (`STC_RULE_PACK_VALIDATION_FAILED`);
  - cross-input consistency (§6.3.3);
  - approved-pack success;
  - `ConfigurationRuleEvaluation` shape.
- `tests/exchangers/shell_tube/test_task020_rule_pack_fixtures.py`
  - all four rule-pack fixture sets
    (`valid_configuration_pack`, `conflicting_configuration_pack`,
    `unapproved_rule_pack`, `license_blocked_rule_pack`);
  - required-rule missing;
  - unapproved/license/provenance blocked;
  - conflict fixtures;
  - unsupported token;
  - incompatible combination;
  - no restricted content (TASK-012 inherited marker).
- `tests/exchangers/shell_tube/test_task020_rule_pack_hash_integration.py`
  - full evaluated authority in canonical payload (§11.2);
  - hash stability;
  - mutation of every computation-authority field;
  - UUIDv5 identity;
  - blocked-result identity (§11.2.1).
- `tests/exchangers/shell_tube/test_task020_rule_pack_canonical.py`
  - selected-rule composite sort (§12.4);
  - per-rule evidence/provenance ordering (§11.4);
  - warning/blocker full-object ordering (§11.4);
  - canonical JSON behavior (§11.2).

The existing S1 tests continue to cover schema, case authority,
generic mode and non-computable output boundaries and remain
authoritative.

### 19.I Preserved exclusions

Design Amendment 001 does NOT authorize, and the S2
implementation MUST NOT introduce:

- geometry;
- heat-transfer calculations;
- pressure-drop calculations;
- Kern;
- Bell–Delaware;
- TEMA calculations or copied content;
- mechanical calculations;
- materials;
- mass;
- cost;
- optimization;
- API;
- CLI;
- report rendering;
- persistence;
- TASK-021 through TASK-039 allocation.

### 19.J Anti-fabrication guard

This amendment itself is design-only. The amendment MUST NOT:

- write production code under `src/hexagent/exchangers/shell_tube/`;
- write or rename test files other than the single amendment's
  frozen-contract integrity test
  (`tests/exchangers/shell_tube/test_task020_frozen_contract_unchanged.py`);
- create or modify any fixture file in
  `tests/fixtures/task020/`;
- modify `ci-shard-manifest.yml`;
- modify any workflow file;
- modify any TASK-001 through TASK-019 contract;
- modify Issue #128;
- create the S2 implementation branch
  `codex/task-020-s2-rule-pack-adapter-impl`.

This amendment's only allowed file mutations are:

1. `docs/tasks/TASK-020-shell-and-tube-configuration-schema.md`;
2. `tests/exchangers/shell_tube/test_task020_frozen_contract_unchanged.py`.

No third file is authorized.

### 19.K Amendment change log

- **001** (this amendment, Issue #129) — Reconcile §14.2
  implementation allowlist from `shell_and_tube/` roots to
  `exchangers/shell_tube/` roots; freeze 42-file S2
  implementation boundary; freeze `validate_request` top-level
  signature with `loaded_rule_pack` / `validation_report`
  keyword-only inputs; replace `STC_RULE_PACK_REQUIRED` with
  three input-presence codes; record five accepted S2 test
  filenames and minimum coverage mapping; preserve all
  §19.I exclusions; preserve Issue #128 unchanged; preserve
  TASK-021 through TASK-039 unallocated.
