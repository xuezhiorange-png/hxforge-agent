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
| TASK-014 design and implementation | direct case-authority dependency | immutable case-revision identity and verified case content hash supplied to TASK-020 |
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

A rule pack used by TASK-020 must expose, through the existing TASK-012
runtime model:

- `rule_pack_id`;
- `rule_pack_version`;
- `content_hash`;
- `approval_status = approved`;
- source class and license evidence;
- citation/provenance metadata;
- configuration-token and compatibility rules permitted by that source
  class.

If approval, evidence, source class or hash verification fails, validation
fails closed.

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

TASK-020 consumes an immutable TASK-014 authority value containing:

- `case_revision_id`;
- `case_revision_hash`;
- `authority_status`, exact value `VERIFIED`.

TASK-020 does not query persistence. The calling application must obtain and
verify this value through the TASK-014 contract before invocation.

### 7.4 ShellAndTubeConfigurationRequest

The request is an immutable value object containing the fields frozen in §8.
It represents an explicitly supplied configuration. It is not a selection or
optimization request.

### 7.5 ConfigurationAuthorityBinding

The authority binding records:

- authority mode;
- standard system identifier, when applicable;
- rule-pack identity and hash, when applicable;
- citation/evidence pointers;
- approval status observed by TASK-020.

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
| `rule_pack_id` | string or null | required for `APPROVED_RULE_PACK`; absent for `INTERNAL_GENERIC` |
| `rule_pack_version` | string or null | required for `APPROVED_RULE_PACK`; absent for `INTERNAL_GENERIC` |
| `rule_pack_hash` | lowercase 64-char hex string or null | required for `APPROVED_RULE_PACK`; absent for `INTERNAL_GENERIC` |
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

- `standard_system_id`, `rule_pack_id`, `rule_pack_version` and
  `rule_pack_hash` must be null;
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
| `warnings` | array | stable ordered warning objects |
| `blockers` | array | empty for a valid configuration |
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
- `STC_CASE_AUTHORITY_MISSING`
- `STC_CASE_AUTHORITY_UNVERIFIED`
- `STC_CASE_HASH_INVALID`
- `STC_EQUIPMENT_FAMILY_INVALID`
- `STC_AUTHORITY_MODE_INVALID`
- `STC_CONSTRUCTION_FAMILY_INVALID`
- `STC_ORIENTATION_INVALID`
- `STC_PASS_COUNT_INVALID`
- `STC_TOKEN_MALFORMED`
- `STC_AUTHORITY_FIELDS_INCONSISTENT`
- `STC_RULE_PACK_REQUIRED`
- `STC_RULE_PACK_NOT_FOUND`
- `STC_RULE_PACK_UNAPPROVED`
- `STC_RULE_PACK_HASH_MISMATCH`
- `STC_RULE_PACK_LICENSE_BLOCKED`
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

Every warning or blocker contains:

- `code`;
- `field_path` or null;
- `message_key`;
- `evidence_refs` as a deterministically sorted array;
- `details` containing JSON primitives only.

Human-readable prose is presentation metadata and is excluded from identity
hashes. `message_key`, not localized text, is computation authority.

## 11. Determinism, identity, serialization, hashing and provenance

### 11.1 Purity

Validation must be deterministic for the same request and the same verified
rule-pack content. It must not read the clock, network, environment variables,
locale or unordered filesystem state.

### 11.2 Canonical payload

The configuration hash covers:

- normalized request structural fields;
- verified case authority;
- normalized authority binding;
- rule-pack ID, version and verified content hash when applicable;
- sorted evidence references;
- sorted warning codes and field paths;
- the frozen deferred-capability set.

The hash excludes:

- `configuration_id`;
- `configuration_hash`;
- localized messages;
- timestamps;
- process or host metadata.

Canonical serialization must reuse the repository canonical-JSON discipline:
UTF-8, lexicographically sorted object keys, stable array ordering, no NaN or
Infinity and no platform-dependent representation.

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

- evidence references: ascending Unicode code-point order;
- warnings: `(code, field_path or "")` ascending;
- blockers: `(code, field_path or "")` ascending;
- deferred capabilities: the order in §9.3.

Input object-key or evidence-reference order must not alter the hash.

### 11.5 Provenance

The authority binding must retain:

- verified case revision ID and hash;
- rule-pack ID, version and content hash when applicable;
- source class;
- approval status;
- citation/evidence pointers;
- TASK-020 schema version;
- implementation package version and Git commit in the surrounding run
  provenance, not in the configuration hash.

## 12. Correlation and rule-pack registration boundary

TASK-020 introduces no heat-transfer, hydraulic, mechanical or cost equation
and therefore creates no engineering correlation entry.

The future implementation may provide a configuration-rule adapter over the
existing TASK-012 runtime. The adapter may consume approved rule content for:

- allowed structural tokens;
- allowed token combinations;
- allowed construction-family mappings;
- pass-count constraints;
- orientation constraints;
- citation and evidence metadata.

The adapter must not:

- embed a copied restricted-standard table in core code;
- infer rules from bibliographic metadata alone;
- execute an unapproved rule;
- treat a token match as legal certification;
- extrapolate when a rule pack lacks a required rule.

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
- `tests/fixtures/task020/configuration/internal_generic_valid.json`
- `tests/fixtures/task020/configuration/approved_rule_pack_valid.json`
- `tests/fixtures/task020/configuration/rule_pack_unapproved.json`
- `tests/fixtures/task020/configuration/rule_pack_license_blocked.json`
- `tests/fixtures/task020/configuration/configuration_combination_blocked.json`
- `ci-shard-manifest.yml`, only to register the exact new test files

Any additional path requires a design amendment and separate Charles
authorization before mutation.

Test fixtures must be synthetic project-internal data. They must not copy
restricted standard content.

## 15. Test and CI contract

The future implementation must include:

1. schema-version acceptance and rejection tests;
2. unknown-field rejection tests;
3. verified and unverified case-authority tests;
4. construction-family, orientation and pass-count validation tests;
5. internal-generic mode tests proving no standard claim is emitted;
6. approved-rule-pack mode success tests using synthetic approved internal
   rule content;
7. missing, unapproved, hash-mismatched and license-blocked rule-pack tests;
8. token normalization and malformed-token tests;
9. unsupported-token and incompatible-combination blocker tests;
10. canonical ordering tests for evidence, warnings and blockers;
11. hash stability under object-key and input evidence-order changes;
12. hash mutation tests for every computation-authority field;
13. exact UUIDv5 identity tests;
14. tests proving no geometry, thermal, pressure-drop, mechanical, material,
    cost or report output is produced;
15. restricted-content marker rejection tests inherited from TASK-012;
16. a frozen-contract integrity test for this document after design freeze.

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
- [ ] TASK-014 case authority is a direct dependency and no persistence lookup
      is hidden inside TASK-020.
- [ ] Input and output schemas are complete and versioned.
- [ ] Computable and `NOT_COMPUTABLE` outputs are explicit.
- [ ] Warning and blocker codes are closed sets.
- [ ] Canonical hash and UUIDv5 rules are exact.
- [ ] Persistence, API, CLI and report boundaries are explicit.
- [ ] The future implementation allowlist contains exact paths only.
- [ ] Tests and CI expectations are complete.
- [ ] Implementation remains separately authorized.

### 18.2 Resolution of TASK-019 §18.4 questions

| Question | TASK-020 answer |
|---|---|
| Is TASK-020 the TEMA configuration/schema foundation or another capability? | It is the shell-and-tube configuration schema foundation. Standard-specific semantics are rule-pack-bound; TASK-020 is not a TEMA calculation engine. |
| Which later Task IDs own layout, diameter, rating, Kern, Bell–Delaware, pressure drop and thermal expansion? | The repository does not authorize exact IDs. They remain unassigned pending a separate Charles-authorized M3 sequencing amendment. |
| Which predecessors are direct vs. reference-only? | Frozen in §4. |
| What standards content may be represented? | Frozen in §6: internal generic rules or TASK-012-permitted approved rule-pack content; restricted bodies remain metadata/citation-only. |
| Which outputs are computable? | Frozen in §9: normalized configuration, validation, identity and provenance only; engineering outputs are explicitly not computable. |
| What is the design-document path? | `docs/tasks/TASK-020-shell-and-tube-configuration-schema.md`. |

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
