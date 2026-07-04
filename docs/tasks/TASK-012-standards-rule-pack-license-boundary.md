# TASK-012 — Standards rule-pack and license boundary

## 1. Purpose and governance scope

TASK-012 establishes the **governance boundary** under which HXForge
may reference engineering standards (ASME / TEMA / API / ISO / GB / EN /
JIS / DIN / NFPA / ASTM / vendor catalogs / handbooks) when defining
the calculation rules that the engineering kernel consumes, without
incorporating the copyrighted or restricted bodies of those standards
into the repository or its deliverables.

TASK-012 freezes five interlocking governance objects:

1. A **license boundary** that defines what is allowed, what is
   forbidden, and what requires evidence.
2. A **standards source taxonomy** that classifies every rule by where
   it came from and what license posture it carries.
3. A **rule-pack artifact model** that gives every rule a stable
   identity, a version, a hash, and an audit trail.
4. A **review and approval workflow** that gates every rule before it
   may enter a runtime rule-pack.
5. A **CI validation boundary** that constrains what future CI may
   check, without authorizing CI implementation in this design.

The contract does NOT authorize any code, test, CI workflow, rule
executor, materials database, pressure-drop computation, C4 engine,
cost model, or shell-and-tube production capability.

## 2. Current authority and prerequisites

```text
TASK-011 design:                DONE / FROZEN
TASK-011 implementation:        DONE / MERGED
TASK-011 closeout docs PR:      DONE / MERGED
Issue #36:                      CLOSED
PR #38 (TASK-011 impl):         MERGED
PR #39 (TASK-011 closeout):     MERGED
Main HEAD at TASK-012 launch:   f78716e4cd348e46157a2a610c8fc4191a0c9dd9
TASK-012 design Issue:          #40 — OPEN
TASK-012 implementation:        NOT AUTHORIZED
TASK-013, TASK-014, TASK-015+:  NOT AUTHORIZED
TASK-016 through TASK-019:       NOT AUTHORIZED
TASK-020+ (shell-and-tube):     NOT AUTHORIZED
```

Frozen prerequisite contracts (binding for TASK-012 design):

- `docs/tasks/TASK-011-benchmark-case-governance.md` (frozen SHA
  `7cfdb4f0989b6d384533c7a29e9a2156c731bd0f`) — governs how benchmark
  cases cite standards and engineering assumptions.
- `docs/MASTER_DEVELOPMENT_SPEC.md` — primary engineering scope
  document.
- `docs/CORRELATION_REGISTRY.md` and `docs/CORRELATIONS.md` — define how
  calculation correlations are versioned and registered; TASK-012
  rule-pack identity MUST be compatible with the existing correlation
  registry naming and hashing.

## 3. Explicit non-goals

TASK-012 MUST NOT implement or require any of the following. The
design contract MUST explicitly enumerate them so that any later
implementation cannot quietly expand scope:

1. Pressure-drop computation (TASK-007 territory remains in scope; new
   pressure-drop rules added by TASK-012 are FORBIDDEN).
2. C4 / advanced constraint engine.
3. New heat-transfer correlations beyond the TASK-007 / TASK-008 set.
4. New equipment types beyond double-pipe.
5. Shell-and-tube logic.
6. Plate heat exchanger logic.
7. Air cooler logic.
8. Two-phase or refrigerant logic.
9. Cost model.
10. Materials database (TASK-013 territory).
11. Mechanical design checks.
12. Persistent database / ORM.
13. Authentication / authorization.
14. Report rendering engine changes.
15. TASK-013, TASK-014, TASK-015, TASK-016, TASK-017, TASK-018,
    TASK-019, TASK-020+.
16. Submission of any copyrighted standards content (see Section 6).

## 4. Standards source taxonomy

Every rule MUST declare exactly one `source_class` from the frozen set
below. The classification is binding and is the gate that determines
whether a rule may be committed, distributed, or executed.

| source_class                          | description                                                 |
|---------------------------------------|-------------------------------------------------------------|
| `PUBLIC_DOMAIN`                       | Government or quasi-government publication explicitly       |
|                                       | released to the public domain (NIST, OSHA, EU regulation    |
|                                       | text, etc.).                                                |
| `OPEN_LICENSE`                        | Standard or handbook released under an OSI-approved or     |
|                                       | Creative Commons license that permits redistribution and   |
|                                       | modification. License SPDX identifier MUST be recorded.    |
| `USER_PROVIDED_LICENSED_SUMMARY`      | A user-supplied rule that summarizes, paraphrases, or       |
|                                       | derives from a standard the user owns a license to. The     |
|                                       | license boundary is the user's; the summary is the user's; |
|                                       | the rule MUST be marked as user-provided and is NOT        |
|                                       | redistributable.                                            |
| `INTERNAL_ENGINEERING_RULE`           | An engineering rule authored inside the project or its      |
|                                       | licensed collaborators, with no external standard as       |
|                                       | source. The author and review chain are recorded.           |
| `DERIVED_ENGINEERING_RULE`            | An engineering rule derived from one or more external       |
|                                       | standards or rules, with the derivation logic and inputs    |
|                                       | recorded in `provenance_edges`. The derived rule is        |
|                                       | authored by the project; the inputs are cited, but their    |
|                                       | bodies are NOT redistributed.                              |
| `REFERENCE_ONLY_RESTRICTED_STANDARD`  | A restricted standard referenced for engineering decisions  |
|                                       | but whose body MUST NEVER be committed. Only               |
|                                       | bibliographic metadata and citation pointers are kept.     |
|                                       | This class is non-redistributable.                          |
| `VENDOR_PERMISSIONED`                 | A vendor document explicitly permitted by the vendor for    |
|                                       | inclusion under a recorded license scope. Vendor            |
|                                       | permission evidence MUST be recorded.                       |

A rule that does not fit one of these classes is FORBIDDEN.

## 5. License boundary model

The repository has a single global license boundary that applies to all
files. Standards rule content MUST NOT violate the project license or
the license of any source. The license boundary is enforced by the
following rules:

1. The repository's primary license is recorded in `LICENSE` and is
   the ceiling for any rule's redistribution rights.
2. Every rule MUST record its `source_class` and (where applicable)
   its `license_evidence` (see Section 10).
3. Rules whose `source_class` is `OPEN_LICENSE` MUST record the SPDX
   identifier of the open license and MUST NOT include any clause
   whose redistribution would violate that license.
4. Rules whose `source_class` is `USER_PROVIDED_LICENSED_SUMMARY`,
   `REFERENCE_ONLY_RESTRICTED_STANDARD`, or `VENDOR_PERMISSIONED`
   MUST record the permission / license evidence and MUST NOT be
   treated as redistributable.
5. The license boundary is enforced at future CI; this design
   contract does not authorize CI implementation but defines what
   the future CI checks MUST enforce.

## 6. Allowed vs forbidden content

### 6.1 Allowed content

The repository MAY contain:

- Bibliographic metadata for any standard: standard number, edition,
  publisher, publication date, jurisdiction, page / section / equation
  / table locator, DOI or stable URL.
- Paraphrased engineering rules authored inside the project
  (`INTERNAL_ENGINEERING_RULE`).
- Derived engineering rules with the derivation logic and source
  pointers fully recorded (`DERIVED_ENGINEERING_RULE`).
- User-provided summaries of standards the user is licensed to access
  (`USER_PROVIDED_LICENSED_SUMMARY`), provided the rule body itself
  contains no clause copied verbatim from the standard.
- Public-domain standard text where the public-domain status is
  evidenced (`PUBLIC_DOMAIN`).
- Open-license text where the SPDX license permits redistribution
  (`OPEN_LICENSE`), with the SPDX identifier recorded.
- Vendor-permissioned excerpts under recorded permission evidence
  (`VENDOR_PERMISSIONED`), limited to the scope of the permission.

### 6.2 Forbidden content

The repository MUST NOT contain any of the following
`forbidden_content_marker` values. Each marker is a hard reject:

| marker                          | description                                              |
|---------------------------------|----------------------------------------------------------|
| `standard_full_text`            | The full body of any copyrighted standard.               |
| `paid_standard_excerpt`         | Any excerpt, table, or clause from a paid / licensed      |
|                                 | standard beyond bibliographic citation.                   |
| `copied_table`                  | A table reproduced verbatim from a copyrighted standard. |
| `scanned_page`                  | A scanned page image of any standard.                    |
| `figure_reproduction`           | A figure, diagram, or chart reproduced from a copyrighted |
|                                 | standard.                                                |
| `formula_image`                 | A formula presented only as an image with no text        |
|                                 | counterpart that the project can verify.                 |
| `verbatim_clause`               | A clause reproduced verbatim from a copyrighted standard. |
| `unlicensed_vendor_catalog`     | Vendor catalog content without recorded vendor permission.|

A rule whose body contains any of these markers is rejected at the
source-evidence gate and at future CI.

## 7. Rule-pack artifact model

A **rule-pack** is the smallest governance unit that may be loaded by
the runtime engineering kernel in a future implementation. A rule-pack
contains one or more rules, each with full provenance.

Rule-pack artifacts MUST be stored under
`benchmarks/rule_packs/` (future implementation; this design
contract does not authorize creating this directory) and MUST have
the following top-level structure (informational, not normative):

```text
rule_packs/
  <rule_pack_id>/
    manifest.json           # rule-pack manifest
    rules/
      <rule_id>.json        # individual rule artifacts
    provenance/
      <edge_id>.json        # provenance edges between rules
    signatures/
      <review_id>.json      # reviewer signatures
```

The file boundary is informational; the field schemas below are
binding.

### 7.1 rule-pack manifest fields

| Field                | Required | Notes                                              |
|----------------------|----------|----------------------------------------------------|
| `rule_pack_id`       | REQUIRED | Stable, unique, immutable identifier.              |
| `rule_pack_version`  | REQUIRED | Changes on any rule addition, removal, or update. |
| `rule_count`         | REQUIRED | Integer; MUST equal `len(rules)`.                  |
| `rules`              | REQUIRED | Array of `rule_id` strings.                        |
| `target_jurisdiction`| REQUIRED | ISO 3166-1 alpha-2 country or `INTL`.             |
| `target_standard_family` | REQUIRED | E.g. ASME / TEMA / API / ISO / GB / EN / JIS / VENDOR / INTERNAL. |
| `creation_timestamp_utc` | REQUIRED | RFC 3339 UTC with `Z` suffix.                  |
| `review_id`          | REQUIRED | Reviewer sign-off reference.                       |
| `canonical_hash`     | REQUIRED | SHA-256 of the canonical serialization (Section 13). |

### 7.2 rule artifact fields

| Field                       | Required | Notes                                              |
|-----------------------------|----------|----------------------------------------------------|
| `rule_id`                   | REQUIRED | Stable, unique within the rule-pack.               |
| `rule_version`              | REQUIRED | Semver-compatible.                                  |
| `rule_title`                | REQUIRED | Human-readable title.                               |
| `source_class`              | REQUIRED | One of Section 4 classes.                           |
| `source_evidence`           | REQUIRED | Section 10 metadata.                               |
| `human_entered_evidence`    | CONDITIONAL | Required when `source_class` is `USER_PROVIDED_LICENSED_SUMMARY` or `INTERNAL_ENGINEERING_RULE`. |
| `derived_rule_evidence`     | CONDITIONAL | Required when `source_class` is `DERIVED_ENGINEERING_RULE`. |
| `license_evidence`          | CONDITIONAL | Required when redistribution scope is non-trivial. |
| `rule_body`                 | REQUIRED | The rule's authoritative textual / structural representation. |
| `forbidden_content_marker_check` | REQUIRED | Self-attested array (must be empty).             |
| `applicability_envelope`    | REQUIRED | Domain of validity (units, ranges, conditions).   |
| `uncertainty`               | REQUIRED | Stated uncertainty / precision.                    |
| `review_status`             | REQUIRED | One of `pending`, `accepted`, `accepted_with_caveats`, `rejected`. |
| `approval_status`           | REQUIRED | One of `draft`, `needs_source`, `under_review`, `approved`, `rejected`, `superseded`. |
| `canonical_hash`            | REQUIRED | SHA-256 of the canonical serialization.            |
| `provenance_edges`          | REQUIRED | Array of edge IDs pointing to provenance artifacts. |

### 7.3 provenance edge fields

| Field          | Required | Notes                                          |
|----------------|----------|------------------------------------------------|
| `edge_id`      | REQUIRED | Stable unique identifier.                      |
| `from_rule_id` | REQUIRED | Source rule id (or `external:<source_class>`). |
| `to_rule_id`   | REQUIRED | Derived rule id.                               |
| `relation`     | REQUIRED | E.g. `derived_from`, `summarizes`, `paraphrases`. |
| `evidence_ref` | REQUIRED | Pointer to the citation / evidence.            |

## 8. Human-entered rule governance

Rules whose `source_class` is `USER_PROVIDED_LICENSED_SUMMARY` or
`INTERNAL_ENGINEERING_RULE` MUST be entered by an authorized engineer
with a recorded identity. The following governance applies:

1. The author identity MUST be recorded in
   `human_entered_evidence.author_identity`.
2. The author's relationship to the source (license owner, internal
   engineer, licensed collaborator) MUST be recorded in
   `human_entered_evidence.author_role`.
3. The date of entry MUST be recorded in
   `human_entered_evidence.entry_timestamp_utc`.
4. The reviewer identity, review thread reference, and review
   timestamp MUST be recorded in `human_entered_evidence.review`.
5. The rule body MUST NOT contain any of the Section 6.2 forbidden
   content markers.
6. The rule MUST declare its applicability envelope and uncertainty
   (Section 7.2).

A rule whose `human_entered_evidence` is missing required fields is
rejected.

## 9. Derived rule governance

Rules whose `source_class` is `DERIVED_ENGINEERING_RULE` MUST record
the derivation logic in `derived_rule_evidence`. The following
governance applies:

1. `derived_rule_evidence.derivation_method` MUST be one of
   `formula_substitution`, `algebraic_combination`,
   `table_interpolation`, `curve_fit`, `engineering_judgment`.
2. `derived_rule_evidence.input_rules` MUST list every rule or
   external standard that contributes to the derivation.
3. `derived_rule_evidence.derivation_steps` MUST be a human-readable
   explanation that allows a reviewer to reproduce the derivation.
4. `derived_rule_evidence.validation_status` MUST be one of
   `pending`, `validated`, `rejected`.
5. The derived rule MUST NOT redistribute the input bodies. It
   records only the inputs' identities (rule_id or bibliographic
   metadata).

## 10. Citation and bibliographic metadata

Every rule MUST record citation metadata under
`source_evidence` (universal mandatory fields) and
`bibliographic_reference` (when the source is a published standard):

| Field                              | Required | Notes                                  |
|------------------------------------|----------|----------------------------------------|
| `source_class`                     | REQUIRED | One of Section 4 classes.              |
| `source_reference`                 | REQUIRED | Stable bibliographic identifier.       |
| `source_title_or_identifier`       | REQUIRED | Title or unique identifier.            |
| `source_locator_or_citation`       | REQUIRED | Page / section / equation / table.     |
| `source_version_or_publication_date` | REQUIRED if available, else `unavailable`. ||
| `source_publisher`                 | REQUIRED when the source is a published standard. ||
| `source_jurisdiction`              | REQUIRED | ISO 3166-1 alpha-2 country or `INTL`. |
| `source_access_date`               | REQUIRED if URL or web, else `n/a`.  |
| `license_evidence`                 | REQUIRED | SPDX identifier, permission evidence, or `public_domain`. |
| `license_evidence_artifact`        | CONDITIONAL | Required when `license_evidence` is not a standard SPDX. |

A rule whose source evidence is incomplete is rejected at the
source-evidence gate.

## 11. Provenance and audit trail

Every rule MUST carry provenance edges that allow a reviewer to trace
the rule back to its inputs and review chain. The provenance system is
binding for future audit:

1. Every rule MUST list at least one provenance edge.
2. Provenance edges MUST form a connected acyclic graph rooted at
   either an external standard (recorded as
   `external:<source_class>:<source_reference>`) or an internal
   engineering rule.
3. Provenance edges MUST be preserved across rule version bumps: a
   `rule_version` bump does NOT delete the edge history; it adds new
   edges.
4. Audit queries MUST be able to answer:
   - Which rules depend on this standard?
   - Which review chain approved this rule?
   - Which other rules were touched in the same review batch?

The implementation of audit tooling is OUT OF SCOPE for TASK-012
design; this design only freezes the data model.

## 12. Rule identity and versioning

Rule identity is composed of `(rule_pack_id, rule_id, rule_version)`.
Identity rules:

1. `rule_pack_id` is stable across versions of the rule-pack.
2. `rule_id` is stable across versions of the rule itself.
3. `rule_version` follows semver-compatible increment rules:
   - MAJOR: rule body changes that affect computed results.
   - MINOR: rule body changes that do NOT affect computed results
     (e.g., editorial clarification of citation).
   - PATCH: non-rule-body changes (e.g., provenance metadata).
4. A rule whose `rule_version` increments MUST regenerate
   `canonical_hash` and update the rule-pack manifest
   `canonical_hash`.
5. A rule that supersedes another rule MUST declare
   `approval_status = "superseded"` and link to the successor via
   a provenance edge of `relation = "supersedes"`.

## 13. Canonical serialization and hashing

Every rule and rule-pack manifest MUST have a canonical hash. The
canonical serialization is FROZEN:

| Parameter                  | Frozen value                                          |
|----------------------------|-------------------------------------------------------|
| `hash_algorithm`           | SHA-256 (FIPS 180-4).                                 |
| `serialization_format`     | Canonical JSON (RFC 8785).                            |
| `field_ordering`           | Sorted keys at every object level, recursively.       |
| `unicode_normalization`    | NFC (UAX #15).                                        |
| `date_time_format`         | RFC 3339, UTC, with explicit `Z` suffix.              |
| `hash_scope`               | Per-artifact (rule or manifest).                      |
| `excluded_hash_fields`     | `canonical_hash`, `mutable_review_comments`.         |
| `numeric_representation`   | Shortest round-trippable decimal (RFC 8785 §3.3.1).   |
| `non_finite_floats`        | FORBIDDEN at hash time.                               |

Implementation MUST use the same RFC 8785 reference behavior adopted
for TASK-011 (`hexagent.benchmark_cases.canonical`) to ensure
consistent canonicalization across the project.

## 14. Review and approval workflow

Rule review follows a frozen state machine:

```text
draft
needs_source
needs_license_evidence
needs_normalization
needs_expected_outputs
under_review
approved
rejected
superseded
```

Approval requires ALL of the following gates:

1. Complete schema validation (Section 7.2 field set).
2. License boundary pass (Section 5 + Section 6).
3. Source evidence minimum (Section 10).
4. Human-entered or derived rule evidence (Section 8 or Section 9),
   conditional on `source_class`.
5. Canonical hash integrity (Section 13).
6. Reviewer sign-off recorded (identity + timestamp + review ID).
7. `forbidden_content_marker_check` is the empty array.
8. Non-goal check (Section 3): the rule's expected outputs MUST NOT
   require any of the Section 3 non-goal physics.

A rule in `draft` or any `needs_*` state MUST NOT enter a runtime
rule-pack. A rule in `rejected` MUST NOT re-enter `under_review`
without a new `rule_version` and a new reviewer sign-off.

## 15. CI validation boundary

The TASK-012 design contract freezes what future CI may check. It
does NOT authorize adding CI checks in this PR. The future CI
boundary is:

1. Schema validity: every rule artifact and rule-pack manifest MUST
   validate against the Section 7 field sets.
2. Forbidden content marker scan: every rule MUST have
   `forbidden_content_marker_check == []`.
3. Canonical hash consistency: every rule's recomputed canonical
   hash MUST equal the recorded `canonical_hash`.
4. Provenance completeness: every rule MUST have at least one
   provenance edge; provenance edges MUST reference real rules or
   recorded external sources.
5. License metadata presence: every rule MUST have a
   `license_evidence` field; the SPDX identifier (or recorded
   permission evidence) MUST be present when the source is not
   public-domain.
6. Approval state consistency: only rules with
   `approval_status == "approved"` may be referenced by an
   `approved` rule-pack manifest.

The CI boundary is defined here for design completeness; its
implementation is OUT OF SCOPE for this design contract and requires
a separate explicit authorization.

## 16. Distribution boundary

The distribution boundary defines what may be redistributed to whom:

1. The repository as a whole is distributed under the project
   primary license recorded in `LICENSE`.
2. Rules whose `source_class` is `PUBLIC_DOMAIN` or `OPEN_LICENSE`
   (with SPDX recorded) are redistributable as part of the
   repository.
3. Rules whose `source_class` is `USER_PROVIDED_LICENSED_SUMMARY`,
   `REFERENCE_ONLY_RESTRICTED_STANDARD`, or `VENDOR_PERMISSIONED`
   are NOT redistributable. They may be referenced by the local
   engineering kernel under their recorded license, but their bodies
   MUST NOT be exported, copied, or shipped.
4. Rules whose `source_class` is `INTERNAL_ENGINEERING_RULE` or
   `DERIVED_ENGINEERING_RULE` are redistributable as part of the
   repository subject to the project primary license.
5. The distribution boundary MUST be enforced at future CI by
   cross-checking `source_class` against any planned public
   artifact emission.

## 17. Implementation authorization boundary

```text
TASK-012 design contract: DRAFT (this document, not yet frozen)
TASK-012 implementation:  NOT AUTHORIZED
Production code changes:  NOT AUTHORIZED
Test changes:             NOT AUTHORIZED
CI workflow changes:      NOT AUTHORIZED
TASK-013, TASK-014, TASK-015+: NOT AUTHORIZED
TASK-016+ shell-and-tube: NOT AUTHORIZED
```

A later TASK-012 implementation is authorized to start only after
ALL of the following:

1. This design contract is independently reviewed.
2. The reviewed Head is recorded in Issue #40 (the TASK-012 design
   Issue).
3. The frozen contract SHA is established and recorded in
   Issue #40.
4. A frozen-contract-metadata file is committed (e.g.,
   `docs/tasks/TASK-012-frozen-contract-metadata.md`) following the
   same pattern as the TASK-011 frozen contract metadata.
5. Issue #40 is updated with the frozen authority and frozen-SHA
   reference.
6. Explicit implementation authorization is granted by the user.

Until then, every action listed above as NOT AUTHORIZED remains
forbidden, regardless of any preview or draft language elsewhere in
this contract.

## 18. Required future implementation deliverables

When implementation is later authorized, the following deliverables
will be required (informational, not binding for this design PR):

1. `src/hexagent/rule_packs/` runtime package for loading,
   validating, and resolving rule-pack artifacts.
2. `src/hexagent/rule_packs/license_boundary.py` enforcing the
   Section 5 / Section 6 license boundary at load time.
3. `src/hexagent/rule_packs/canonical.py` shared with the TASK-011
   canonicalization helper to ensure consistent SHA-256 over
   rule-packs and benchmark cases.
4. `src/hexagent/rule_packs/provenance.py` exposing provenance
   queries for audit.
5. CLI: `python -m hexagent.rule_packs.validate` for the rule-pack
   CI validation boundary (Section 15).
6. Pytest integrity suite under `tests/rule_packs/`.
7. Initial rule-pack seed: an `INTERNAL_ENGINEERING_RULE`-class
   seed rule-pack that does NOT require any external standard body.
8. Documentation update in `docs/CORRELATION_REGISTRY.md` to
   clarify the relationship between correlation registry and rule-
   pack registry.

Implementation deliverables are NOT part of this design PR.

## 19. Frozen contract criteria

This contract is ready to be considered for freezing when ALL of the
following are answered:

1. What is the standards source taxonomy? (Section 4)
2. What content is allowed vs forbidden? (Section 6)
3. How is the license boundary defined? (Section 5)
4. What is the rule-pack identity model? (Section 12)
5. How are human-entered rules governed? (Section 8)
6. How are derived rules governed? (Section 9)
7. What citation metadata is required? (Section 10)
8. What provenance edges are required? (Section 11)
9. How are rules canonicalized and hashed? (Section 13)
10. What is the review and approval state machine? (Section 14)
11. What does future CI check? (Section 15)
12. What is the distribution boundary? (Section 16)
13. What implementation authorization is required? (Section 17)
14. What is out of scope? (Section 3)
15. What implementation deliverables are required? (Section 18)

## 20. Review checklist

A reviewer evaluating this contract MUST verify:

### A. License boundary
- [ ] No copyrighted standards full text, excerpts, tables, figures,
      formulas, or scanned pages are present in the contract body
      or its examples.
- [ ] Bibliographic metadata is sufficient for an engineer to locate
      the cited standard.
- [ ] SPDX identifiers or permission evidence are recorded for any
      redistributable content.

### B. Source taxonomy
- [ ] Every `source_class` in Section 4 has clear
      repository-allowed / distribution-allowed / CI-allowed
      / human-review-required / license-evidence-required /
      runtime-rulepack-allowed / public-artifact-allowed rules.

### C. Forbidden content
- [ ] All eight forbidden content markers in Section 6.2 are
      enumerated and explained.
- [ ] Each marker has a clear reject criterion.

### D. Rule identity
- [ ] `rule_pack_id`, `rule_id`, `rule_version`, `source_class`,
      `jurisdiction`, `standard_family`, `bibliographic_reference`,
      `license_evidence`, `review_status`, `approval_status`,
      `canonical_hash`, and `provenance_edges` are all defined.
- [ ] Semver-compatible version increment rules are present.

### E. Implementation boundary
- [ ] The contract explicitly states that implementation is NOT
      AUTHORIZED.
- [ ] The contract lists every forbidden implementation action.
- [ ] The frozen contract criteria and review checklist are
      present.

### F. CI boundary
- [ ] The contract enumerates the six CI checks (schema validity,
      forbidden content marker scan, canonical hash consistency,
      provenance completeness, license metadata presence, approval
      state consistency).
- [ ] The contract does NOT require CI implementation in this PR.

### G. Non-goals
- [ ] Section 3 enumerates every non-goal.
- [ ] No non-goal is silently treated as in-scope.

### H. Review and approval workflow
- [ ] The frozen state machine is enumerated.
- [ ] The eight approval gates are present.
- [ ] The supersession rule is present.

### I. Provenance
- [ ] The connected acyclic graph property is stated.
- [ ] Audit queries are enumerated.

### J. Cross-document consistency
- [ ] The contract is consistent with
      `docs/tasks/TASK-011-benchmark-case-governance.md` (TASK-011
      frozen contract).
- [ ] The contract is consistent with
      `docs/CORRELATION_REGISTRY.md` and `docs/CORRELATIONS.md`.
- [ ] The contract is consistent with
      `docs/MASTER_DEVELOPMENT_SPEC.md`.