# TASK-014 — Immutable Case Revisions and Persistence Contract

> Design contract for TASK-014. Defines immutable case revision and
> persistence semantics prior to any implementation. This document is
> design-only; no code, no DB, no migration, no test, no API, and no
> report rendering is introduced by this design PR.

## 1. Purpose and governance scope

TASK-014 introduces the first persistence boundary in the project:
immutable, append-only case revisions with deterministic identity,
provenance integration, and structured conflict handling. This design
contract freezes the domain model, the persistence boundary, the
revision lifecycle, the canonicalization and hashing strategy, the
concurrency contract, the validation/blocker model, the error model,
the audit integration, and the future-implementation test contract
required before any code may be written.

The contract is intentionally **storage-neutral**. The logical schema
and migration strategy in this document are database-agnostic;
database-specific choices (PostgreSQL / SQLite / file-system journal /
etc.) are deferred to the future implementation PR and MUST NOT be
introduced in the design PR.

This design PR also does not implement the contract. It only freezes
the design. Implementation requires a separate explicit authorization
after this design PR is reviewed, merged, and closed out.

Inherited from upstream tasks:

- TASK-002 (units and quantities) — quantity model, SI semantics,
  dimensional analysis rules.
- TASK-003 (fluid property service) — property provider boundaries,
  applicability envelopes, uncertainty bands.
- TASK-004 (design case revisions, provenance, structured errors) —
  prior concepts of case revisions and provenance DAG. TASK-014
  generalizes and hardens the immutability contract.
- TASK-005 (correlation registry) — applicability envelopes and
  authority boundaries for correlations referenced by a case
  revision.
- TASK-011 (benchmark governance) — license boundary for any
  benchmark payload referenced inside a case revision.
- TASK-012 (standards rule pack + license boundary) — restricted-source
  restrictions carry over to any rule-pack evidence referenced by a
  case revision.
- TASK-013 (material/cost governance) — restricted-source and source-
  class restrictions carry over to any material/cost record referenced
  by a case revision.

## 2. Current authority and prerequisites

This design PR is authorized by Issue #52.

```text
TASK-013 design Issue:        #46 — CLOSED / completed
TASK-013 design PR:           #47 — MERGED
TASK-013 design closeout PR:  #48 — MERGED
TASK-013 implementation Issue: #49 — CLOSED / completed
TASK-013 implementation PR:    #50 — MERGED
TASK-013 implementation closeout docs PR: #51 — MERGED
TASK-013 implementation status recorded on main: DONE / MERGED /
                              MAIN-CI-VERIFIED / CLOSED
TASK-014 design status:       AUTHORIZED BY Issue #52 / IN DRAFT PR
TASK-014 implementation:      NOT AUTHORIZED
TASK-015+:                    PLANNED / NOT STARTED unless separately
                              authorized
```

`docs/TASK_BACKLOG.md` on main records TASK-014 as PLANNED prior to
this design PR.

## 3. Definitions

| Term | Definition |
|---|---|
| `CaseId` | Opaque, project-wide stable identifier for a logical case (a thermal/equipment design problem statement). |
| `CaseRevisionId` | Opaque, project-wide stable identifier for one immutable revision of a case. |
| `RootCaseId` | The CaseId under which a revision chain lives. Stable for the lifetime of the case; never reused across distinct cases. |
| `RevisionNumber` | A monotonically increasing integer that strictly orders revisions within one `RootCaseId`. |
| `ParentRevisionId` | The `CaseRevisionId` of the revision this revision was branched from. `None` for the initial revision of a `RootCaseId`. |
| `PayloadHash` | SHA-256 hex of the canonicalized semantic payload of a revision. |
| `DomainSnapshotHash` | SHA-256 hex of the canonicalized domain snapshot of a revision (payload + parent_chain + identity + provenance edges). |
| `ParentChainHash` | Optional SHA-256 hex of the canonicalized parent-chain link records of a revision. |
| `ActorId` | Stable identifier of the human/system that authored or committed the revision. |
| `created_at` | UTC RFC-3339 timestamp when the draft proposal was first recorded. |
| `committed_at` | UTC RFC-3339 timestamp when the revision transitioned from draft → committed. Immutable thereafter. |
| `superseded_by` | `CaseRevisionId` of the successor committed revision, if any. |
| `archived_at` | UTC RFC-3339 timestamp when the revision was archived (metadata transition). The revision content remains immutable. |
| `tombstone_at` | UTC RFC-3339 timestamp when the revision was tombstoned (metadata transition). The revision content remains immutable. |
| `IdempotencyKey` | Optional caller-supplied string used to deduplicate create-revision requests. |

## 4. Source classes and source authority hierarchy

TASK-014 does NOT introduce new source classes. It inherits the
source-class discipline established by TASK-012 (rule source classes)
and TASK-013 (material/cost source classes). Any rule-pack evidence,
material/cost record, property value, correlation identifier, or
benchmark payload referenced by a case revision MUST carry a source
class identifier that is valid in its respective upstream closed set.

Revision chain authority is established by the following rules:

1. **Source-bound discipline carries over.** A revision that
   references a TASK-013 `RESTRICTED_REFERENCE_METADATA_ONLY`
   material record MUST NOT contain a numeric property value
   payload (the license boundary is enforced upstream; the
   revision merely persists the reference).
2. **Provider-bound discipline carries over.** A revision that
   references a property value obtained from a TASK-003 provider
   MUST carry the provider identifier, the applicability envelope,
   and the uncertainty band upstream of the revision commit.
3. **Correlation-bound discipline carries over.** A revision that
   references a correlation identifier MUST carry a TASK-005
   correlation version and applicability envelope.

The revision itself does NOT authorize any source class; it only
persists references that were authorized upstream.

## 5. Core entities and identities

The TASK-014 domain model defines the following entities:

```text
Case
    case_id: CaseId (opaque, project-unique)
    root_case_id: RootCaseId == case_id (initial) or a prior case_id
    first_revision_id: CaseRevisionId (initial revision)
    status: one of {active, archived, tombstoned}
    created_at, created_by: ActorId, RFC-3339 UTC
    archived_at: optional RFC-3339 UTC
    tombstone_at: optional RFC-3339 UTC

CaseRevision
    revision_id: CaseRevisionId (opaque, project-unique)
    case_id: CaseId
    root_case_id: RootCaseId
    revision_number: int >= 1 (monotonically increasing per root_case_id)
    parent_revision_id: CaseRevisionId | None
    parent_chain_hash: Optional[ParentChainHash]
    payload_hash: PayloadHash
    domain_snapshot_hash: DomainSnapshotHash
    payload: dict (semantic case payload; content see Section 9)
    identity: dict (identity metadata; content see Section 9)
    provenance: dict (provenance edges; see Section 11)
    created_at, created_by: ActorId, RFC-3339 UTC
    committed_at, committed_by: ActorId, RFC-3339 UTC
    status: one of {draft, validated, committed, superseded,
                    archived, tombstoned, rejected}
    superseded_by: CaseRevisionId | None
    archived_at, tombstone_at: optional RFC-3339 UTC
    expected_parent_revision_id: CaseRevisionId | None (concurrency)
    idempotency_key: IdempotencyKey | None

CaseRevisionAuditEvent
    event_id: opaque
    revision_id: CaseRevisionId
    root_case_id: RootCaseId
    event_type: one of {revision_created, revision_validated,
                        revision_committed, revision_superseded,
                        revision_archived, revision_tombstoned,
                        revision_rejected}
    actor_id: ActorId
    source: str (free-text classification of the actor system)
    occurred_at: RFC-3339 UTC
    payload: dict (event-type-specific; see Section 14)
```

Identity guarantees:

- `revision_id` is opaque, immutable, project-unique, and NEVER
  reused.
- `(root_case_id, revision_number)` is unique.
- `(root_case_id, idempotency_key)` is unique when
  `idempotency_key` is present.

## 6. Immutable revision contract

TASK-014 enforces the following immutability rules. Any violation is a
`RevisionPersistenceFailure` blocker.

1. **Append-only.** New revisions are appended. Existing committed
   revisions are NEVER mutated, patched, or rewritten. There is no
   `update_revision` operation.
2. **No in-place fix.** Any correction of a committed revision MUST
   be done by creating a successor revision with the corrected
   payload and a `parent_revision_id` pointing at the prior revision.
3. **No destructive delete.** Archival and tombstone are metadata
   transitions on a committed revision. The revision content and
   payload_hash are immutable regardless of status.
4. **Supersession is non-destructive.** Setting `superseded_by` on a
   prior revision is a metadata update that records the successor
   identity. It does NOT alter the prior revision's payload.
5. **Hash immutability.** `payload_hash` and `domain_snapshot_hash`
   are computed at commit time and stored. They are NEVER
   recomputed and MUST match the canonicalized payload at any later
   validation.
6. **Identity immutability.** `revision_id`, `root_case_id`,
   `revision_number`, `created_at`, `created_by`, `committed_at`,
   `committed_by`, `payload_hash`, and `domain_snapshot_hash` are
   immutable from commit time onward.
7. **No silent mutation.** Every status transition writes an audit
   event. There is no `silent` path.
8. **No partial commit.** A revision transition either commits
   fully or fails with no partial state.

## 7. Revision lifecycle

### 7.1 Allowed states

A `CaseRevision.status` MUST be one of:

```text
draft
validated
committed
superseded
archived
tombstoned
rejected
```

### 7.2 Allowed transitions

The following transitions are allowed:

```text
draft        -> validated | rejected
validated    -> committed | rejected
committed    -> superseded | archived | tombstoned
superseded   -> archived | tombstoned
archived     -> tombstoned
tombstoned   -> (terminal)
rejected     -> (terminal)
```

### 7.3 Forbidden transitions

The following transitions are forbidden:

```text
draft         -> committed       (must go through validated)
draft         -> superseded      (must commit first)
validated     -> superseded      (must commit first)
validated     -> archived        (must commit first)
committed     -> draft           (no rollback to draft)
committed     -> validated       (no rollback to validated)
committed     -> rejected        (rejection only applies pre-commit)
superseded    -> draft | validated | committed | rejected
archived      -> draft | validated | committed | superseded | rejected
tombstoned    -> ANY             (terminal)
rejected      -> ANY             (terminal)
```

A forbidden transition request is a `RevisionPersistenceFailure`
blocker.

## 8. Persistence boundary

### 8.1 What TASK-014 persists

The TASK-014 persistence boundary persists ONLY:

- The `Case` envelope (case_id, root_case_id, first_revision_id,
  status, timestamps).
- The `CaseRevision` records (semantic payload, identity, hashes,
  parent relation, timestamps, status).
- The `CaseRevisionAuditEvent` records.
- Optional `idempotency_keys` per `(root_case_id, key)`.
- Optional revision-level `optimistic_concurrency_token` per
  committed revision.

### 8.2 What TASK-014 does NOT persist

The TASK-014 persistence boundary explicitly does NOT persist:

- Execution result artifacts (intermediate numerical results,
  convergence traces, solver step traces).
- Optimization candidate evaluations.
- Report renderings (HTML, PDF, JSON-for-render payloads).
- Benchmark artifacts (TASK-011 catalog data).
- Material/cost catalog data copies (TASK-013 catalog data).
- Restricted source bodies (TASK-012 / TASK-013 restrictions).
- Pressure-drop / C4 / equipment-type results (TASK-018 / M3+ /
  M4+ / M5+ / M6+ / M7+ future work, NOT in this design PR).
- Public-API surface or RPC schema.

These are persisted, if at all, by future tasks; their persistence
is OUT of scope for the TASK-014 logical schema.

### 8.3 Storage-neutrality rule

The TASK-014 logical model is database-agnostic. The design does NOT
commit to:

- A specific RDBMS vendor (PostgreSQL, MySQL, SQLite, etc.).
- A specific key-value or document store.
- A specific file-system journal format.
- A specific ORM.
- A specific migration tool.

These are deferred to the future implementation PR.

## 9. Logical schema contract

The TASK-014 logical schema is described using storage-neutral
relations. The future implementation PR will translate these into a
DB-specific DDL.

### 9.1 Relations

```text
case_roots
    case_id                    PK (opaque, project-unique)
    first_revision_id          FK -> case_revisions.revision_id
    status                     {active, archived, tombstoned}
    created_at                 RFC-3339 UTC
    created_by                 ActorId
    archived_at                RFC-3339 UTC, nullable
    tombstone_at               RFC-3339 UTC, nullable

case_revisions
    revision_id                PK (opaque, project-unique)
    root_case_id               FK -> case_roots.case_id
    revision_number            int >= 1
    parent_revision_id         FK -> case_revisions.revision_id,
                               nullable (only first revision is null)
    parent_chain_hash          hex(64), nullable
    payload_hash               hex(64) NOT NULL
    domain_snapshot_hash       hex(64) NOT NULL
    payload                    canonical JSON
    identity                   canonical JSON
    provenance                 canonical JSON
    created_at                 RFC-3339 UTC
    created_by                 ActorId
    committed_at               RFC-3339 UTC, nullable (null in draft)
    committed_by               ActorId, nullable
    status                     {draft, validated, committed,
                               superseded, archived, tombstoned,
                               rejected}
    superseded_by              FK -> case_revisions.revision_id,
                               nullable
    archived_at                RFC-3339 UTC, nullable
    tombstone_at               RFC-3339 UTC, nullable
    expected_parent_revision_id FK -> case_revisions.revision_id,
                               nullable
    idempotency_key            string, nullable
    optimistic_concurrency_token string, nullable

case_revision_parents
    revision_id                FK -> case_revisions.revision_id
    parent_revision_id         FK -> case_revisions.revision_id
    link_order                 int >= 0
    PRIMARY KEY (revision_id, link_order)

case_revision_audit_events
    event_id                   PK (opaque, project-unique)
    revision_id                FK -> case_revisions.revision_id
    root_case_id               FK -> case_roots.case_id
    event_type                 {revision_created, revision_validated,
                               revision_committed, revision_superseded,
                               revision_archived, revision_tombstoned,
                               revision_rejected}
    actor_id                   ActorId
    source                     string
    occurred_at                RFC-3339 UTC
    payload                    canonical JSON

idempotency_keys  (optional)
    root_case_id               FK -> case_roots.case_id
    idempotency_key            string
    revision_id                FK -> case_revisions.revision_id
    created_at                 RFC-3339 UTC
    PRIMARY KEY (root_case_id, idempotency_key)
```

### 9.2 Uniqueness and referential integrity

- `revision_id` is unique across the entire system.
- `(root_case_id, revision_number)` is unique.
- `(root_case_id, idempotency_key)` is unique when present.
- `parent_revision_id` MUST resolve to a committed revision of the
  same `root_case_id`, or be NULL.
- `superseded_by` MUST resolve to a committed revision of the same
  `root_case_id` with a strictly greater `revision_number`, or be
  NULL.
- `first_revision_id` MUST equal the `revision_id` of the
  `(root_case_id, revision_number=1)` row.
- `case_revisions.payload_hash` MUST equal the SHA-256 of the
  canonicalized `payload` field at any validation.

### 9.3 Index requirements

Recommended indexes (deferred to implementation):

- `case_revisions (root_case_id, revision_number)` unique.
- `case_revisions (root_case_id, status)`.
- `case_revisions (parent_revision_id)`.
- `case_revisions (superseded_by)`.
- `case_revisions (idempotency_key)` (when present).
- `case_revision_audit_events (revision_id, occurred_at)`.
- `case_revision_audit_events (root_case_id, event_type, occurred_at)`.

### 9.4 Required fields per record type

`CaseRevision` required fields at commit time:

- revision_id, root_case_id, revision_number, parent_revision_id,
  payload_hash, domain_snapshot_hash, payload, identity, provenance,
  created_at, created_by, committed_at, committed_by, status.

`CaseRevisionAuditEvent` required fields at insert time:

- event_id, revision_id, root_case_id, event_type, actor_id,
  source, occurred_at, payload.

## 10. Migration strategy

The TASK-014 design does NOT ship a DB-specific migration in this PR.
The future implementation PR will introduce migrations, but the
following rules apply to any future migration:

1. **Forward-only committed content.** Once a revision is committed,
   its `payload`, `identity`, `provenance`, `payload_hash`, and
   `domain_snapshot_hash` MUST NOT be rewritten by any migration.
2. **Append-only migrations.** Migrations MAY add columns, indexes,
   or relations. Migrations MUST NOT modify or delete existing
   committed revision content.
3. **Backward-compatible transitions.** Adding a column MUST be
   backward-compatible (default value or nullable). Removing a
   column MUST be deferred to a major version boundary.
4. **Rollback expectations.** A migration that introduces a
   required column MUST have a documented rollback path. The
   rollback path MUST NOT corrupt committed revision content.
5. **Database-agnostic contract first.** This design does not
   commit to a specific migration tool. The future implementation
   PR will pick a tool and document the choice.
6. **Migration tests.** Any future migration MUST ship with a
   migration test that exercises the up and down paths against a
   seeded fixture database.

## 11. Canonicalization and hashes

### 11.1 Canonical JSON helper

TASK-014 REUSES the existing canonical JSON helper
(`hexagent.canonical_json.canonical_sha256`) used by TASK-004 and
TASK-013. The future implementation MUST NOT introduce a parallel
canonicalization helper.

Canonical JSON rules (inherited):

- Stable key ordering (sorted by key).
- Deterministic number serialization.
- Excluded volatile fields (timestamps, transient IDs, request
  metadata) at the boundary layer.
- Included semantic payload fields (see Section 11.3).

### 11.2 Hash inputs

| Hash | Input |
|---|---|
| `payload_hash` | canonical JSON of `case_revisions.payload` (with `record_hash` field excluded if present) |
| `domain_snapshot_hash` | canonical JSON of `{identity, payload, provenance, parent_chain}` joined into a single canonical object (excluding volatile fields like `created_at`, `created_by`, `committed_at`, `committed_by`, `expected_parent_revision_id`, `idempotency_key`, `optimistic_concurrency_token`) |
| `parent_chain_hash` (optional) | canonical JSON of `case_revision_parents` rows for the revision, ordered by `link_order` ascending |

### 11.3 Excluded volatile fields

The following fields are EXCLUDED from hash inputs and DO NOT affect
the hash:

- `created_at`, `created_by` (audit metadata only).
- `committed_at`, `committed_by` (audit metadata only).
- `expected_parent_revision_id` (concurrency intent, not semantic
  content).
- `idempotency_key` (request-deduplication, not semantic content).
- `optimistic_concurrency_token` (concurrency metadata).
- `archived_at`, `tombstone_at`, `superseded_by` (lifecycle
  metadata; tracked via audit events).

### 11.4 Golden vectors

The future implementation MUST ship golden hash vectors for the
following fixtures:

1. Minimal empty-payload revision (only `case_id` set).
2. Revision with a single property reference.
3. Revision with a single correlation reference.
4. Revision with parent-chain = `None`.
5. Revision with parent-chain = single prior revision.
6. Revision with full provenance edges.
7. Revision with idempotency_key set.
8. Revision with rule-pack evidence reference (TASK-012).
9. Revision with material/cost reference (TASK-013).
10. Revision whose payload ordering is randomized (must produce the
    same hash).

## 12. Validation and blocker model

The TASK-014 validator separates structural validation from
content-level validation.

### 12.1 Structural blockers

The following are structural blockers:

- Missing required identity field (revision_id, root_case_id,
  revision_number, payload_hash, etc.).
- Non-unique `(root_case_id, revision_number)`.
- Non-unique `(root_case_id, idempotency_key)` when idempotency_key
  is present.
- Non-canonical JSON in payload / identity / provenance.
- Missing `created_at` / `created_by` / `committed_at` /
  `committed_by` (when status is committed).
- Invalid status enum value.
- Invalid `revision_number` (not an integer, less than 1, or
  non-monotonic).
- `parent_revision_id` present but does not resolve to a committed
  revision of the same `root_case_id`.
- `superseded_by` present but does not resolve to a committed
  revision of the same `root_case_id` with strictly greater
  `revision_number`.

### 12.2 Hash blockers

The following are hash blockers:

- `payload_hash` does not match the SHA-256 of the canonicalized
  `payload` field.
- `domain_snapshot_hash` does not match the SHA-256 of the
  canonicalized domain snapshot.
- `parent_chain_hash` present but does not match the SHA-256 of
  the canonicalized parent-chain rows.

### 12.3 Unit / provider / authority blockers

- Quantity fields reference a unit not in the TASK-002 dimensional
  unit registry.
- Property reference does not resolve to a TASK-003 provider.
- Correlation reference does not resolve to a TASK-005 correlation
  registry entry.
- Material/cost reference does not resolve to a TASK-013 record
  with valid `approval_state` and license posture.
- Rule-pack evidence reference does not satisfy TASK-012 license
  posture for runtime consumption.

### 12.4 Restricted-content blockers

- Payload contains a restricted standard body.
- Payload contains a vendor catalog body.
- Payload contains a paid price list.
- Payload contains a restricted material property table.
- Payload contains a scanned page reference or formula image
  reference with embedded numeric content.
- Payload contains a copied standard table.

### 12.5 Concurrency blockers

The following are concurrency blockers:

- `expected_parent_revision_id` is present but does not equal the
  current head revision of the same `root_case_id`.
- A request attempts to commit a duplicate
  `(root_case_id, revision_number)`.
- A request attempts to create a concurrent sibling revision
  without satisfying the expected-parent contract.
- An `optimistic_concurrency_token` is present but stale.

A stale `expected_parent_revision_id` MUST raise
`StaleParentRevision`, MUST be treated as a hard rejection, and
MUST NOT appear in warnings.

### 12.6 Warnings (non-blocking)

- `effective_date` older than 5 years.
- `escalation_date` present without `escalation_index_reference`
  but with documented justification.
- `engineering_estimate` quality flag set.
- Tombstone chain length greater than 5.

### 12.7 Structural separation

`blockers` and `warnings` are kept in disjoint lists per Section 15
of TASK-013. A blocker MUST NOT be downgraded to a warning. A stale
`expected_parent_revision_id` is a blocker and MUST NOT be emitted as
a warning.

## 13. Concurrency and transaction semantics

### 13.1 Expected-parent revision

A revision create-request MAY include `expected_parent_revision_id`.
If present, the create-request is rejected with
`StaleParentRevision` if the actual current head revision of the
`root_case_id` does not equal `expected_parent_revision_id`.

If absent, the create-request uses the actual current head revision
of the `root_case_id` as the parent. The parent is recorded in
`parent_revision_id` at commit time.

### 13.2 Optimistic concurrency

Each committed revision carries an `optimistic_concurrency_token`.
A request that attempts to act on a revision MUST present the
expected token. A token mismatch surfaces as
`CaseRevisionConflict`.

### 13.3 Idempotency

A revision create-request MAY include `idempotency_key`. Two
create-requests with the same `(root_case_id, idempotency_key)` MUST
be deduplicated: the second request returns the existing revision
without creating a duplicate. The dedup is recorded in the
`idempotency_keys` relation.

### 13.4 Atomic commit

A revision commit is atomic: the revision record, the parent-chain
link rows, the audit event, and any idempotency-key row MUST be
written in a single atomic transaction. There is no partial commit.

### 13.5 Concurrent sibling creation

Two concurrent create-requests on the same `root_case_id` that
both compute `revision_number = N+1` MUST NOT both succeed. The
loser is rejected with `CaseRevisionConflict` and may retry with a
fresh `revision_number`.

### 13.6 Conflict error contract

`CaseRevisionConflict` MUST include machine-readable fields:

- `revision_id`
- `root_case_id`
- `expected_parent_revision_id`
- `actual_parent_revision_id`
- `attempted_revision_number`
- `conflict_reason` (one of `{token_mismatch,
   duplicate_idempotency_key, concurrent_sibling}`)

Stale expected-parent conflicts are represented by
`StaleParentRevision`, not by `CaseRevisionConflict`.

## 14. Provenance and audit integration

### 14.1 Audit event types

The following audit event types are emitted:

- `revision_created` — emitted when a draft proposal is recorded.
- `revision_validated` — emitted when a draft transitions to
  validated.
- `revision_committed` — emitted at commit time.
- `revision_superseded` — emitted when a successor revision sets
  `superseded_by` on a prior revision.
- `revision_archived` — emitted when a revision is archived.
- `revision_tombstoned` — emitted when a revision is tombstoned.
- `revision_rejected` — emitted when a draft / validated proposal is
  rejected.

### 14.2 Audit immutability

Audit events are immutable. Once inserted, an audit event MUST NOT
be updated or deleted. Audit events are append-only.

### 14.3 Actor and source metadata

Every audit event carries `actor_id` (a stable identifier of the
human/system that performed the action) and `source` (a free-text
classification string such as `engineering-review`,
`ci-shard-prod-3.12`, `migration-tool-v1`).

### 14.4 Provenance DAG linkage

The TASK-014 audit events form a chronological DAG that downstream
tasks can join with TASK-004 / TASK-005 / TASK-013 provenance
edges. The DAG is intentionally append-only; there is no
back-dating.

### 14.5 No silent mutation rule

Every state transition MUST emit an audit event. A transition that
lacks a corresponding audit event is a `RevisionPersistenceFailure`
blocker.

## 15. License and restricted-content boundary

TASK-014 inherits the TASK-012 / TASK-013 restricted-source
discipline. Specifically:

1. **No standards body text.** Payload MUST NOT contain any
   standard body text from ASME / ASTM / ISO / EN / GB / JIS / DIN /
   NFPA / TEMA / API / AWS / ASHRAE / IIAR / EIGA, whether literal,
   excerpt, or paraphrased.
2. **No vendor catalog body.** Payload MUST NOT contain any vendor
   catalog body, whether from a permissioned vendor or not.
3. **No paid price list.** Payload MUST NOT contain any paid price
   list body, even when permissioned by a vendor.
4. **No restricted material property table.** Payload MUST NOT
   contain a restricted material property table body.
5. **No scanned pages / formula images.** Payload MUST NOT embed
   scanned-page or formula-image content with embedded numeric
   values.
6. **Synthetic / metadata-only fixtures.** All fixtures and
   examples used in tests or in the design itself MUST be synthetic
   or metadata-only. Use placeholders like
   `internal://handbook/<id>` for references.
7. **Boundary carries forward.** Any future revision that
   references a TASK-013 `RESTRICTED_REFERENCE_METADATA_ONLY`
   record MUST persist only the bibliographic metadata block
   (`issuing_body`, `designation`, `edition_year`,
   `clause_locator`, `bibliographic_metadata`). Numeric property
   values MUST NOT be persisted alongside a restricted reference.

A restricted-content violation is a `RestrictedContentViolation`
blocker.

## 16. Error model

All TASK-014 errors are structured, machine-readable, and
inherit from a common base.

### 16.1 Common base

```text
Task014Error (base)
    error_code: str (machine-readable)
    message: str (human-readable)
    root_case_id: str | None
    revision_id: str | None
    context: dict (event-specific structured payload)
```

### 16.2 Defined errors

- **`CaseRevisionConflict`**
  - `error_code = "case_revision_conflict"`
  - `context.conflict_reason` ∈
    `{token_mismatch, duplicate_idempotency_key, concurrent_sibling}`
  - `context.expected_parent_revision_id`
  - `context.actual_parent_revision_id`
  - `context.attempted_revision_number`

A stale expected-parent condition MUST be represented by
`StaleParentRevision` with `error_code = "stale_parent_revision"`.
It MUST NOT be represented as `CaseRevisionConflict`.

- **`StaleParentRevision`**
  - `error_code = "stale_parent_revision"`
  - `context.expected_parent_revision_id`
  - `context.actual_parent_revision_id`

- **`InvalidRevisionPayload`**
  - `error_code = "invalid_revision_payload"`
  - `context.path` (JSON path inside the payload)
  - `context.reason` (free-text description)

- **`RevisionHashMismatch`**
  - `error_code = "revision_hash_mismatch"`
  - `context.expected_payload_hash`
  - `context.actual_payload_hash`
  - `context.hash_field` ∈
    `{payload_hash, domain_snapshot_hash, parent_chain_hash}`

- **`MissingRevisionAuthority`**
  - `error_code = "missing_revision_authority"`
  - `context.missing_authority` ∈
    `{property_provider, correlation, material, cost, rule_pack,
     benchmark}`

- **`RevisionPersistenceFailure`**
  - `error_code = "revision_persistence_failure"`
  - `context.failure_reason` (free-text)
  - `context.partial_state` (boolean — MUST always be False at
    raise time per Section 6.8)

- **`RestrictedContentViolation`**
  - `error_code = "restricted_content_violation"`
  - `context.violation_kind` ∈
    `{standard_body, vendor_catalog_body, paid_price_list,
     restricted_property_table, scanned_page, formula_image,
     copied_standard_table}`

Each error class carries `root_case_id`, `revision_id` (if
applicable), and a structured `context` dict. CI MUST NOT
downgrade these errors to warnings.

## 17. Future implementation file boundary

The following envelope is EXPECTED for the future implementation PR
but is **NOT AUTHORIZED** in this design PR:

```text
src/hexagent/case_revisions/
src/hexagent/case_revisions/__init__.py
src/hexagent/case_revisions/models.py
src/hexagent/case_revisions/canonical.py
src/hexagent/case_revisions/validation.py
src/hexagent/case_revisions/errors.py
src/hexagent/case_revisions/lifecycle.py
src/hexagent/case_revisions/audit.py
src/hexagent/case_revisions/optimistic.py
src/hexagent/case_revisions/persistence.py
src/hexagent/case_revisions/idempotency.py
src/hexagent/case_revisions/migration.py  (only when DB is
                                            introduced)

tests/case_revisions/
tests/case_revisions/test_identity.py
tests/case_revisions/test_immutability.py
tests/case_revisions/test_canonical.py
tests/case_revisions/test_lifecycle.py
tests/case_revisions/test_concurrency.py
tests/case_revisions/test_audit.py
tests/case_revisions/test_validation.py
tests/case_revisions/test_errors.py
tests/case_revisions/test_idempotency.py
tests/case_revisions/test_restricted_content.py
tests/case_revisions/golden_hashes/
tests/case_revisions/golden_hashes/*.json

docs/TASK_BACKLOG.md
docs/tasks/TASK-014-immutable-case-revisions-persistence.md (only
                                       for back-references in impl)
```

This envelope is **NOT AUTHORIZED** in this design PR and MUST NOT
be implemented, stubbed, or partially constructed until the user
separately authorizes TASK-014 implementation.

## 18. Required test strategy for later implementation

The future implementation PR MUST ship tests covering:

### 18.1 Identity and validity

- `revision_id` uniqueness across the system.
- `(root_case_id, revision_number)` uniqueness.
- `(root_case_id, idempotency_key)` uniqueness.
- Required-field validation.
- Status enum validation.

### 18.2 Immutability

- A committed revision's `payload` field cannot be modified.
- A committed revision's `identity` field cannot be modified.
- A committed revision's `payload_hash` cannot be modified.
- A committed revision's `domain_snapshot_hash` cannot be modified.
- Archival and tombstone are metadata-only transitions.

### 18.3 Parent-chain consistency

- A revision's `parent_revision_id` resolves to a committed
  revision of the same `root_case_id`.
- The parent chain is reachable from any revision via
  `case_revision_parents` rows ordered by `link_order`.
- A revision with `parent_revision_id = None` is the first revision
  of its `root_case_id`.

### 18.4 Canonicalization and hash determinism

- Golden vectors (Section 11.4) match.
- Randomized payload field ordering produces the same hash.
- Excluded volatile fields (Section 11.3) do not affect the hash.

### 18.5 Concurrency

- Two concurrent create-requests on the same `root_case_id` do not
  both succeed.
- `expected_parent_revision_id` mismatch raises
  `StaleParentRevision`.
- `optimistic_concurrency_token` mismatch raises
  `CaseRevisionConflict`.
- Idempotent create-request returns the existing revision.

### 18.6 Atomicity

- A commit that fails after the revision row is written but before
  the audit event is written leaves no partial state (transactional
  rollback).

### 18.7 Audit

- Each state transition emits exactly one audit event.
- Audit events are immutable.
- Audit events carry `actor_id` and `source`.

### 18.8 Validation and blocker separation

- Structural blockers raise `InvalidRevisionPayload` /
  `RevisionPersistenceFailure`.
- Hash mismatches raise `RevisionHashMismatch`.
- Missing authority raises `MissingRevisionAuthority`.
- Restricted content raises `RestrictedContentViolation`.
- `blockers` and `warnings` are kept in disjoint lists; no
  blocker is downgraded to a warning.

### 18.9 Restricted-content fixture scan

- A repo-wide scan asserts that no TASK-014 fixture or example
  contains restricted standard text, vendor catalog body, paid
  price list, restricted property table, scanned page, or
  formula image.

### 18.10 Migration (when DB is introduced)

- Forward migration is idempotent.
- Backward migration rolls back cleanly.
- Migrations do not rewrite committed revision content.

## 19. Review and freeze procedure

The TASK-014 design follows the same lifecycle as TASK-011 / TASK-012
/ TASK-013 design contracts:

1. Open this design PR as **Draft**.
2. Address review feedback in subsequent commits on the same
   branch.
3. Request Ready after at least one round of review.
4. Mark Ready via `gh pr ready` only after explicit user
   authorization.
5. Merge via `gh pr merge --merge --match-head-commit <HEAD>` with
   head lock.
6. Wait for the main post-merge CI run to complete with status
   `success`.
7. Record the design freeze in `docs/TASK_BACKLOG.md` via a
   closeout docs PR on branch
   `docs/task-014-immutable-case-revisions-persistence-closeout`.
8. Close Issue #52 via `gh issue close 52 --reason completed` only
   after the closeout docs PR is merged and main CI is green.
9. TASK-014 implementation requires a separate explicit
   authorization. Do NOT start implementation until the user
   authorizes it.

The "Frozen Contract Authority SHA" for TASK-014 will be the merge
SHA of this design PR. It is **NOT ESTABLISHED** in this PR.

## 20. Explicit non-goals

This design PR does NOT introduce:

1. Any TASK-014 implementation.
2. Any `src/**` production code.
3. Any `tests/**` test code.
4. Any runtime database table, ORM model, repository, persistence
   adapter, schema snapshot, or migration.
5. Any `.github/workflows/**` workflow.
6. Any `benchmarks/cases/**` or `benchmarks/manifests/**` artifact.
7. Any frozen TASK-011 / TASK-012 / TASK-013 contract body change.
8. Any public HTTP / RPC / API behavior.
9. Any report rendering.
10. Any pressure-drop computation.
11. Any C4 / advanced constraint engine.
12. Any shell-and-tube / plate / air-cooler / two-phase / refrigerant
    / microchannel logic.
13. Any restricted standard / vendor catalog / paid price-list /
    restricted material property table / scanned page / formula
    image / copied table content.
14. Any TASK-015+ or TASK-020+ work.

## 21. Acceptance checklist

This design PR satisfies the TASK-014 design authorization when:

- [ ] Sections 1-22 of this document are present.
- [ ] Source-class discipline carries over from TASK-012 and
      TASK-013.
- [ ] Identity guarantees are explicit (Section 5).
- [ ] Immutability rules are explicit (Section 6).
- [ ] Lifecycle transitions are tabulated (Section 7).
- [ ] Persistence boundary is explicit (Section 8).
- [ ] Logical schema is storage-neutral (Section 9).
- [ ] Migration strategy is documented at the design level
      (Section 10).
- [ ] Canonical JSON helper reuse is explicit (Section 11).
- [ ] Validation / blocker model separates blockers from warnings
      (Section 12).
- [ ] Concurrency / atomicity contract is explicit (Section 13).
- [ ] Audit integration is append-only (Section 14).
- [ ] Restricted-content boundary carries forward (Section 15).
- [ ] Error model is structured and machine-readable (Section 16).
- [ ] Future implementation file envelope is documented and marked
      NOT AUTHORIZED (Section 17).
- [ ] Test contract is documented (Section 18).
- [ ] Review and freeze procedure follows the TASK-011 / TASK-012 /
      TASK-013 pattern (Section 19).
- [ ] Explicit non-goals are listed (Section 20).

## 22. Frozen contract checksum placeholder

The Frozen Contract Authority SHA for TASK-014 design is **NOT
ESTABLISHED** in this design PR. It will be set when the design PR
is merged and the closeout docs PR is created. The authority SHA
will be recorded in:

1. The TASK-014 row of `docs/TASK_BACKLOG.md`.
2. The TASK-014 design PR body (after merge).
3. The TASK-014 closeout docs PR body.

Until then, the TASK-014 design contract is in **DRAFT** status and
is not yet authoritative.