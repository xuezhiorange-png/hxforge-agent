# TASK-015 — CI, Security and Release Automation Design Contract

> Design contract for TASK-015. Defines the CI, security and release
> automation hardening surfaces prior to any implementation. This
> document is design-only; no workflow, no workflow change, no CI
> secret, no release automation, no security gate implementation,
> and no production code is introduced by this design PR.

## 1. Problem statement

The hxforge-agent repository currently relies on a baseline GitHub
Actions CI matrix (lint / format / mypy / pytest / acceptance /
manifest verification / nightly dispatch) established by TASK-015A
("deterministic test environment and CI sharding", Issue #33,
PR #35). Since TASK-015A was merged on 2026-07-04 the engineering
workstream has completed four additional major task contracts
(TASK-011 benchmark governance, TASK-012 standards rule-pack, TASK-013
material / cost governance, TASK-014 immutable case revisions) — each
with its own design contract, implementation PR, and closeout PR — but
no additional CI / security / release automation hardening has been
added since.

TASK-015 closes that gap. It introduces a **design-only contract** for
hardening three surfaces:

1. **CI boundary hardening** — pre-flight governance gates, branch
   protection, nightly dispatch policy, concurrency / merge-group /
   required-status policy.
2. **Security boundary hardening (design only)** — `pip-audit` /
   dependency-vulnerability gating, secret-scan placement, restricted-
   source / license-boundary scan placement, SBOM generation and
   retention interface, dependency-supply-chain boundary.
3. **Release automation boundary hardening (design only)** — tagged-
   release workflow contract, artifact retention / attestation
   contract, internal dependency-version bump contract, backport /
   hotfix branch policy.

This document freezes the contract. Implementation requires a separate
explicit authorization after this design PR is reviewed, merged, and
closed out.

TASK-015 is **distinct** from TASK-015A. TASK-015A is the historical
"deterministic test environment and CI sharding" track (Issues
#33 / #34 / #35; PRs #34 / #35) and remains CLOSED / MERGED. TASK-015
does not modify, reopen, or supersede any TASK-015A artifact. The two
tasks share the `TASK-015` prefix because TASK-015A was scoped out of
the parent TASK-015 at the M1 stage; the parent task is now being
opened to address the remaining CI / security / release workstreams.

## 2. Scope and non-scope

### In-scope (this design contract)

1. **CI boundary hardening (design-only).**
   - Pre-flight governance gates — contract for the frozen-contract
     guard, ci-shard manifest ownership, optional secret-scan / SBOM
     gating. (Existing CI jobs are NOT modified by this design PR;
     the contract specifies the boundary for a future implementation
     PR.)
   - Branch protection model on `main` — required reviewers,
     required status checks, dismiss-stale-review semantics,
     required-linear-history semantics.
   - Nightly dispatch policy — which branches / tags receive
     scheduled runs, how `cancel-in-progress` is governed, retention
     policy for nightly artifacts.
   - Concurrency / merge-group policy for PRs (cancel-in-progress on
     push updates, isolation across unrelated PRs).
   - Required-status-check naming convention — stable, machine-
     readable names that future PRs can rely on.

2. **Security boundary hardening (design-only).**
   - `pip-audit` / dependency-vulnerability gate placement (push /
     PR / nightly / pre-release).
   - Secret-scan placement (push / PR / nightly), including
     detection scope and rotation policy for any false-positive
     suppression list.
   - Restricted-source / license-boundary scan placement — carries
     TASK-012 / TASK-013 / TASK-014 discipline into CI.
   - SBOM generation + retention — format (SPDX / CycloneDX),
     storage-neutral interface, retention window.
   - Dependency-supply-chain boundary — lockfile (`uv.lock` /
     `poetry.lock` / equivalent), hash pin, optional sigstore
     verification — design only, no implementation.

3. **Release automation boundary hardening (design-only).**
   - Tagged-release workflow contract — inputs, triggers, post-
     conditions, version-source-of-truth.
   - Artifact retention / attestation contract — storage-neutral
     interface.
   - Internal dependency-version bump contract for in-repo consumers
     (backport policy, version-source-of-truth).
   - Backport / hotfix branch policy — naming convention, protection,
     merge-into rule.

4. **Cross-cutting governance (design-only).**
   - Failure mode taxonomy for CI / security / release steps —
     transient / non-transient / manual-intervention classification.
   - CI job naming / status-check naming convention (so downstream
     PRs can rely on stable check names).
   - Failure-broadcast contract (Slack / webhook / issue-template
     stub — design only; no integration secrets are added).

### Out-of-scope (explicit non-goals — see also Section 14)

1. Any production code under `src/hexagent/**`.
2. Any test under `tests/**`.
3. Any modification of `.github/workflows/**` files (this design
   contract freezes the boundary only; the future implementation
   PR may introduce new workflows but MUST NOT touch unrelated
   existing ones).
4. Any modification of `ci-shard-manifest.yml` (existing manifest is
   preserved as-is; the contract specifies how a future manifest
   update would be reviewed).
5. Any TASK-015A historical asset (Issue #33 / #34 / #35; PR #34 /
   #35; branch `codex/task-015a-...` / `docs/task-015a-...`).
6. Any frozen TASK-011 / TASK-012 / TASK-013 / TASK-014 design
   contract body.
7. Any public HTTP / RPC / API behavior.
8. Any report rendering.
9. Any pressure-drop / C4 / advanced constraint engine.
10. Any shell-and-tube / plate / air-cooler / two-phase / refrigerant
    / microchannel logic.
11. Any restricted standard / vendor catalog / paid price-list /
    restricted material property table / scanned page / formula
    image / copied table content.
12. Any new TASK-016+ issue / branch / PR.
13. Any CI secret registration, OIDC trust setup, or registry push.
14. Any new external service integration (Slack, sigstore, etc.).
    The contract is storage-neutral and external-service-neutral.

## 3. Contract authority model

This design PR is authorized by Issue #57.

```text
TASK-014 design Issue:        #52 — CLOSED / completed
TASK-014 design PR:           #53 — MERGED
TASK-014 design closeout PR:  #54 — MERGED
TASK-014 implementation Issue: #55 — CLOSED / completed
TASK-014 implementation PR:    #56 — MERGED
TASK-014 implementation closeout docs PR: NOT YET CREATED
                              (Charles opens a separate closeout docs
                              PR after this TASK-015 design track is
                              either merged or abandoned)
TASK-014 implementation status recorded on main: DONE / MERGED /
                              MAIN-CI-VERIFIED / CLOSED
TASK-015 design Issue:         #57 — OPEN (this issue is the authority)
TASK-015 design PR:            IN DRAFT (not yet created)
TASK-015 design status:        AUTHORIZED BY Issue #57 / IN DRAFT PR
TASK-015 implementation:       NOT AUTHORIZED
TASK-015A historical:          CLOSED / MERGED (Issue #33 / #34 /
                               #35; PR #34 / #35; branches
                               codex/task-015a-... and
                               docs/task-015a-...)
TASK-016+:                     PLANNED / NOT STARTED unless separately
                               authorized
```

`docs/TASK_BACKLOG.md` on main records TASK-015 as `PLANNED` prior
to this design PR. This PR advances the row to `DESIGN IN DRAFT`.

The Frozen Contract Authority SHA for TASK-015 design is **NOT
ESTABLISHED** in this design PR. It will be set when:

1. The design PR is reviewed (must receive a `PASS / READY` review).
2. The design PR is merged into `main`.
3. The closeout docs PR is created and merged.

At that point the authority SHA (= the design PR's merge commit) MUST
be recorded in three places atomically:

1. The TASK-015 row of `docs/TASK_BACKLOG.md`.
2. The TASK-015 design PR body (after merge).
3. The TASK-015 design closeout docs PR body.

The TASK-015 implementation PR (which would be created after the
design is frozen) MUST cite this Frozen Contract Authority SHA
exactly.

## 4. Domain model / data model

TASK-015 does not introduce a new runtime domain. It introduces a
**governance configuration model** for CI / security / release
automation. The configuration is stored as **versioned YAML / JSON
files in the repository** (NOT in a database). The model is
intentionally minimal so that it can be reviewed by humans without
tooling.

### 4.1 Governance configuration entities (design)

| Entity | Purpose | Storage | Mutability |
|---|---|---|---|
| `CIPipelineSpec` | Declarative CI pipeline contract (job names, triggers, required-status names). | `docs/governance/ci_pipeline_spec.yaml` | Append-only via design + impl PRs. |
| `SecurityGateSpec` | Declarative security boundary (scan types, severity thresholds, retention). | `docs/governance/security_gate_spec.yaml` | Append-only via design + impl PRs. |
| `ReleaseSpec` | Declarative release contract (tag pattern, artifact pattern, attestation requirement). | `docs/governance/release_spec.yaml` | Append-only via design + impl PRs. |
| `FailureTaxonomy` | Closed set of failure-mode categories with classification. | `docs/governance/failure_taxonomy.yaml` | Append-only via design + impl PRs. |

Each entity is a **schema-validated** YAML / JSON document. The
schema is defined in this design contract (Section 4.2) and frozen
by it; the schema is the source of truth.

### 4.2 Schema rules

1. Every spec file MUST be valid YAML 1.2 AND valid JSON (round-trip
   parsable). YAML is the canonical form; JSON is the executable
   form (future implementation may compile YAML → JSON for workflow
   inputs).
2. Every spec file MUST declare a top-level `schema_version` integer.
   Schemas are forward-only; bumping `schema_version` is permitted
   only via a design contract amendment (a new TASK-015X design PR
   that explicitly authorizes the bump).
3. Every spec file MUST declare an `owner` string (the GitHub
   username of the responsible party) and an `updated_at` ISO-8601
   timestamp.
4. Every spec file MUST list a closed `failure_modes` enum drawn
   from the `FailureTaxonomy`. Adding a new failure mode is a
   taxonomy amendment, not a spec edit.
5. Spec files MUST NOT embed secrets, tokens, OIDC subject IDs,
   registry URLs, webhook URLs, or any other infrastructure-binding
   data. All infrastructure binding is supplied by environment
   variables / repository secrets at workflow runtime.

### 4.3 Identity guarantees

- `CIPipelineSpec.canonical_name` is a stable, repository-wide
  identifier (lowercase kebab-case, e.g. `lint`, `pytest`,
  `merge-ref`).
- `SecurityGateSpec.gate_id` is a stable, repository-wide identifier.
- `ReleaseSpec.release_channel` is a stable, repository-wide
  identifier (e.g. `nightly`, `prerelease`, `stable`).
- All identifiers are unique within their respective spec file and
  MUST NOT be reused after deprecation. Deprecation is signaled by
  moving the identifier to a `deprecated:` block in the same file;
  the identifier MUST remain queryable but new workflows MUST NOT
  reference it.

## 5. Public API boundary

**TASK-015 introduces no new public API.** This task is a
**CI / governance configuration** contract only. It defines how
existing CI / security / release jobs are described and gated; it
does not expose new product functionality.

Existing public APIs (`hexagent` package surface, TASK-010 API
contract, TASK-011 benchmark governance API, TASK-012 standards rule-
pack API, TASK-013 material / cost API, TASK-014 case revisions
API) are unaffected by this design contract.

A future implementation PR for TASK-015 MUST NOT add a new public
API; it adds CI configuration and governance files only.

## 6. Persistence / migration boundary

TASK-015 is **storage-neutral** for product data. It does not
introduce:

- Any new database table.
- Any new ORM model.
- Any new migration.
- Any new repository / persistence adapter.

The only "persistence" introduced by TASK-015 is the **governance
configuration** itself, stored as versioned YAML / JSON files
under `docs/governance/`. This is a code repository concern, not a
runtime persistence concern.

Migration boundary:

- Adding a new spec field is allowed only via a design contract
  amendment (Section 4.2 schema_version bump).
- Removing a spec field is **forbidden** until at least one release
  cycle after the field has been marked `deprecated:`. Removing a
  non-deprecated field is a breaking change and requires explicit
  Charles authorization.
- Renaming a spec field is **forbidden** without a transition
  period during which both names are accepted by the schema
  validator.

## 7. Validation / blocker model

The TASK-015 spec validator (a future implementation component) MUST
classify validation findings into two disjoint lists:

- `blockers` — schema violations that prevent the spec from being
  consumed by the CI / security / release pipeline. The pipeline
  refuses to start when any blocker is present.
- `warnings` — non-fatal advisories (e.g., a spec field that is
  recommended but optional). Warnings do NOT block pipeline start.

CI status-check naming convention (Section 9 cross-cutting
governance) MUST encode the blocker status: a status-check named
`task-015/<spec-name>/blockers` MUST be RED whenever any blocker is
present, GREEN otherwise.

The forbidden-pattern taxonomy (Section 10 restricted-content
boundary) raises BLOCKERS, never warnings — it carries the
discipline from TASK-012 / TASK-013 / TASK-014.

The failure-mode taxonomy (Section 4.1) classifies each CI / security
/ release step's failure as one of:

- `transient` — re-run likely to succeed (network blip, registry
  hiccup). Surface as a warning with auto-retry budget.
- `non_transient` — re-run unlikely to succeed (schema violation,
  hash mismatch, signature failure). Surface as a BLOCKER with
  explicit remediation message.
- `manual_intervention` — human action required (secret rotation,
  OIDC trust renewal, registry quota). Surface as a BLOCKER with an
  attached issue-template stub.

## 8. Error model

TASK-015 introduces a structured error model for spec validation
failures. The model mirrors the pattern from TASK-012 / TASK-013 /
TASK-014 — a closed enum of error classes with machine-readable
context.

### 8.1 Error classes

| Error class | error_code | context fields | Trigger |
|---|---|---|---|
| `SpecSchemaError` | `spec_schema_error` | `spec_path`, `field_path`, `reason`, `schema_version` | Spec file fails schema validation. |
| `SpecIdentifierCollision` | `spec_identifier_collision` | `spec_path`, `identifier`, `collision_with` | Two specs declare the same identifier. |
| `SpecDeprecatedReference` | `spec_deprecated_reference` | `spec_path`, `identifier`, `deprecated_at` | Spec references a deprecated identifier. |
| `SpecForwardIncompatible` | `spec_forward_incompatible` | `spec_path`, `schema_version`, `expected_schema_version` | Spec schema_version is ahead of the validator's supported version. |
| `FailureTaxonomyError` | `failure_taxonomy_error` | `spec_path`, `failure_mode`, `known_failure_modes` | Spec references an unknown failure mode. |
| `RestrictedContentViolation` | `restricted_content_violation` | `spec_path`, `violation_kind`, `offending_excerpt`, `path` | Spec file contains restricted-source content (Section 10). |
| `GovernanceAuthorityError` | `governance_authority_error` | `spec_path`, `missing_authority` | Spec attempts to reference a frozen contract that is not yet established. |

`RestrictedContentViolation.error_code` = `restricted_content_violation`
in ALL cases. CI MUST NOT downgrade `restricted_content_violation` to
a warning under any failure mode.

`GovernanceAuthorityError.missing_authority` is a closed enum:
`{task_011_frozen_contract, task_012_frozen_contract,
task_013_frozen_contract, task_014_frozen_contract,
task_015_frozen_contract, task_015a_frozen_contract}`.

### 8.2 Disambiguation rule (Section 16.2 carry-over)

A failure to find a referenced frozen contract MUST raise
`GovernanceAuthorityError`; it MUST NOT be conflated with
`SpecIdentifierCollision`. The two errors have different remediation
paths and CI tooling relies on the disambiguation.

### 8.3 Error emission contract

- Every blocker MUST emit exactly one error from Section 8.1.
- Every error MUST include `spec_path` (the file that triggered it)
  unless the error originates in cross-file governance (e.g.,
  identifier collision between two spec files).
- Error context MUST be JSON-serializable.

## 9. Determinism / hashing / provenance requirements

### 9.1 Determinism

- Spec files MUST be parseable into a canonical in-memory
  representation that is byte-identical across runs given the same
  file content.
- YAML / JSON parsing MUST use a deterministic parser
  (`ruamel.yaml` in round-trip mode is the recommended canonical
  implementation; design-only, no implementation in this PR).
- Field ordering MUST NOT affect the canonical representation
  (sorted-key normalization).

### 9.2 Hashing

- Every spec file MUST have a `sha256` hash field computed over the
  canonical in-memory representation (Section 9.1).
- The hash MUST be regenerated on every change and committed to
  the file as a top-level `content_hash` field. The hash is the
  primary identity of the spec at a given moment; the file path is
  the secondary identity.
- Two spec files MUST NOT share a `content_hash` (collision
  indicates an unintended duplication; raise
  `SpecIdentifierCollision`).

### 9.3 Provenance

- Every spec file MUST declare an `owner` (GitHub username) and an
  `updated_at` ISO-8601 timestamp (Section 4.2).
- Every change to a spec file MUST go through a PR. The PR body
  MUST cite the prior `content_hash` and the new `content_hash`,
  plus a one-paragraph rationale.
- Branch protection (Section 9 cross-cutting) MUST require the PR
  to be reviewed by a CODEOWNER from `.github/CODEOWNERS` before
  merge.

## 10. Restricted-content boundary

TASK-015 carries forward the restricted-content discipline from
TASK-012 / TASK-013 / TASK-014. The contract surfaces
`RestrictedContentViolation` (Section 8.1) when any spec file
contains:

- Standards-body text from ASME / ASTM / ISO / EN / GB / JIS / DIN /
  NFPA / TEMA / API / AWS / ASHRAE / IIAR / EIGA.
- Vendor catalog body text.
- Paid price list content.
- Restricted material property table content.
- Scanned page references / formula image embeds with numeric
  content.
- Copied standard tables.

The restricted-source scan is invoked at **CI lint time** (push /
PR / nightly) and at **release-gate time** (pre-merge to a release
channel). A finding raises `RestrictedContentViolation` as a
BLOCKER; the pipeline does NOT proceed.

The restricted-content boundary is **storage-neutral** and
**external-service-neutral**. The scan uses a metadata-driven marker
list (similar to `hexagent.case_revisions.restricted`) that is
maintained in this contract. New marker categories require a
design contract amendment.

## 11. Test contract

A future TASK-015 implementation PR MUST add the following test
coverage. The contract is recorded here so that the implementation
PR has a stable target.

### 11.1 Required tests for spec validation

1. `CIPipelineSpec` schema validation: valid / invalid / missing
   required fields / wrong types / unknown identifiers.
2. `SecurityGateSpec` schema validation: same as above.
3. `ReleaseSpec` schema validation: same as above.
4. `FailureTaxonomy` membership test: every spec's `failure_modes`
   field lists only known failure modes.
5. Identifier uniqueness test within a single spec and across the
   set of all specs.
6. `content_hash` regeneration test: changing a field recomputes
   the hash; leaving it untouched leaves the hash untouched.
7. Deprecated-reference test: a spec referencing a `deprecated:`
   identifier surfaces `SpecDeprecatedReference` as a warning
   (not a blocker).

### 11.2 Required tests for governance integration

8. Frozen-contract reference test: a spec referencing a frozen
   contract (TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015A)
   that is not yet established raises `GovernanceAuthorityError`.
9. Restricted-content scan test: a spec containing a restricted
   marker raises `RestrictedContentViolation` and the test harness
   asserts that no workflow side-effect was triggered.
10. Cross-spec identifier collision test: two specs declaring the
    same `canonical_name` / `gate_id` / `release_channel` raise
    `SpecIdentifierCollision`.
11. `schema_version` forward-incompatibility test: a spec with
    `schema_version` ahead of the validator raises
    `SpecForwardIncompatible` as a BLOCKER.
12. Failure-mode classification test: a CI failure classified as
    `transient` surfaces as a warning; `non_transient` /
    `manual_intervention` surface as BLOCKERs.

### 11.3 Required tests for branch protection / release gate

13. Branch protection assertion test: a PR targeting `main` MUST
    fail CI if the head SHA's `content_hash` does not match the
    spec file's current `content_hash`.
14. Release-gate assertion test: a tag matching `ReleaseSpec`'s
    tag pattern triggers a release-gate check; the gate requires
    `content_hash` stability and a frozen-contract reference
    declaration.

### 11.4 Test storage / format

- Tests live under `tests/governance/` (future implementation).
- Each test is a pytest test (no custom harness).
- Restricted-content test fixtures MUST use synthetic / metadata-only
  placeholders (e.g., `internal://handbook/<id>`); literal
  restricted markers MUST NOT appear in source code, exactly as in
  TASK-014 (Section 18.9 carry-over).

## 12. Implementation authorization gate

The TASK-015 implementation PR (a separate, future PR) MUST NOT be
opened until ALL of the following are true:

1. This design PR has been reviewed with verdict `PASS / READY`
   (no CHANGES REQUIRED follow-up open).
2. This design PR has been merged into `main`.
3. The TASK-015 design closeout docs PR has been opened and merged,
   recording the Frozen Contract Authority SHA in three places
   (Section 3).
4. Charles has explicitly authorized the implementation track in a
   new Issue or in writing on the design closeout PR.

The implementation PR MUST cite the Frozen Contract Authority SHA
in its PR body and MUST satisfy the test contract (Section 11).

The implementation PR MUST NOT introduce any item in the
explicit non-scope list (Section 14) without a separate design
amendment PR.

## 13. Closeout requirements

The TASK-015 design track closes out when:

1. The design PR has been merged into `main`.
2. The TASK-015 design closeout docs PR has been opened (Draft)
   with body containing:
   - Frozen Contract Authority SHA (the design PR's merge commit).
   - PR number / merge SHA / mergedAt.
   - main post-merge CI run ID + status + conclusion.
   - Three-place sync evidence (Issue body / PR body / backlog
     row all record the same Frozen Contract Authority SHA).
   - TASK-015 implementation status: NOT AUTHORIZED.
   - TASK-015A historical status: CLOSED / MERGED (unchanged).
   - TASK-016+ status: PLANNED / NOT STARTED.
   - TASK-014 governance chain: intact.
3. The closeout docs PR has been reviewed and merged.
4. The TASK-015 implementation Issue has NOT yet been opened
   (it is opened only after explicit Charles authorization per
   Section 12).
5. The Issue #57 body has been updated with a final reference to
   the Frozen Contract Authority SHA.

A successful closeout leaves the repository in this state:

- `docs/tasks/TASK-015-ci-security-and-release-automation.md`
  merged on main, frozen as the authoritative design contract.
- `docs/governance/ci_pipeline_spec.yaml`,
  `security_gate_spec.yaml`, `release_spec.yaml`,
  `failure_taxonomy.yaml` present on main (added by the
  implementation PR, not this design PR).
- `docs/TASK_BACKLOG.md` TASK-015 row shows `DONE / DESIGN FROZEN`
  and points at the Frozen Contract Authority SHA.
- No TASK-015A asset mutated.
- No TASK-016+ asset created.
- No TASK-014 governance chain item mutated.

## 14. Explicit forbidden scope (Section 14)

This design PR does NOT introduce — and a future implementation PR
MUST NOT introduce without a separate design amendment:

1. Any production code under `src/hexagent/**`.
2. Any test under `tests/**` (other than what the implementation
   PR adds per Section 11).
3. Any modification of `.github/workflows/**` files (the existing
   workflows MUST remain unchanged in this design PR; a future
   implementation PR may add new workflows but MUST NOT touch
   unrelated existing ones).
4. Any modification of `ci-shard-manifest.yml` (existing manifest
   preserved as-is in this design PR).
5. Any modification of TASK-015A historical assets:
   - Issue #33, Issue #34, Issue #35.
   - PR #34, PR #35.
   - Branch `codex/task-015a-deterministic-test-environment-implementation`
   - Branch `docs/task-015a-deterministic-test-environment-design`
   - File `docs/tasks/TASK-015A-deterministic-test-environment-and-ci-sharding.md`
6. Any modification of frozen TASK-011 / TASK-012 / TASK-013 /
   TASK-014 design contract body.
7. Any public HTTP / RPC / API behavior.
8. Any report rendering.
9. Any pressure-drop computation.
10. Any C4 / advanced constraint engine.
11. Any shell-and-tube / plate / air-cooler / two-phase / refrigerant
    / microchannel logic.
12. Any new TASK-016+ issue / branch / PR.
13. Any restricted standard / vendor catalog / paid price-list /
    restricted material property table / scanned page / formula
    image / copied table content committed to the repository.
14. Any CI secret registration, OIDC trust setup, or registry push.
15. Any new external service integration (Slack, sigstore, etc.).
16. Any production database / ORM / migration.
17. Any modification of `pyproject.toml` dependencies (a future
    implementation PR may add a dev dependency for the spec
    validator; that PR's body MUST list the added dependency and
    cite the spec contract section that requires it).
18. Any TASK-020+ work.

---

> End of design contract. Sections 1-14 are the minimum required
> by Issue #57. Sections 15-22 (acceptance checklist / frozen
> contract checksum placeholder) follow the TASK-014 pattern and
> are appended for symmetry.

## 15. Acceptance checklist

This design PR satisfies the TASK-015 design authorization when:

- [x] Sections 1-14 of this document are present and reflect the
      minimum required by Issue #57.
- [x] Scope and non-scope are explicit (Sections 2 + 14).
- [x] Contract authority model is explicit (Section 3).
- [x] Domain model / data model is storage-neutral (Section 4 +
      Section 6).
- [x] Public API boundary is explicitly declared as `no public
      API in this task` (Section 5).
- [x] Persistence / migration boundary is explicitly declared as
      `storage-neutral` (Section 6).
- [x] Validation / blocker model separates blockers from warnings
      (Section 7).
- [x] Error model is structured and machine-readable (Section 8).
- [x] Determinism / hashing / provenance requirements are
      documented (Section 9).
- [x] Restricted-content boundary carries forward from TASK-012 /
      TASK-013 / TASK-014 (Section 10).
- [x] Test contract is documented (Section 11).
- [x] Implementation authorization gate is explicit (Section 12).
- [x] Closeout requirements are explicit (Section 13).
- [x] Explicit forbidden scope is listed (Section 14).

## 16. Frozen contract checksum placeholder

The Frozen Contract Authority SHA for TASK-015 design is **NOT
ESTABLISHED** in this design PR. It will be set when the design PR
is merged and the closeout docs PR is created. The authority SHA
will be recorded in:

1. The TASK-015 row of `docs/TASK_BACKLOG.md`.
2. The TASK-015 design PR body (after merge).
3. The TASK-015 design closeout docs PR body.

Until then, the TASK-015 design contract is in **DRAFT** status and
is not yet authoritative.