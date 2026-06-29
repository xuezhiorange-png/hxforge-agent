# TASK-010 — Versioned API and Traceable Report Contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** PENDING RE-REVIEW
**Frozen Contract SHA:** NOT ESTABLISHED
**Implementation Authorization:** NOT GRANTED

---

## 1. Scope

Freeze the normative API request/response DTOs, discriminated run envelopes, idempotency semantics, canonical request algorithm, artifact bundles, report model, and traceable HTML report contract for the hxforge-agent double-pipe vertical slice.

Non-goals: production API server, HTML renderer, PDF engine, database, authentication/authorization, C4, pressure drop computation, velocity constraints, materials, cost, procurement readiness, TASK-011+.

---

## 2. Upstream Dependencies

| Artifact | Frozen Commit | Schema Identity |
|---|---|---|
| `TASK-008` RatingResult + provenance | `c77d723` (Phase 2 HEAD) | `RatingResult` Pydantic model v1 |
| `TASK-009` OptimizationResult + Phase3EvaluationInput | `1ac3fe6` (merged PR #24) | `OptimizationResult` Pydantic model v1 |
| `DesignCase` (domain models) | `main` HEAD | `src/hexagent/domain/models.py` |
| `DoublePipeGeometry` (frozen dataclass) | `main` HEAD | `src/hexagent/exchangers/double_pipe/geometry.py` |
| `SolverParams` (frozen dataclass) | `main` HEAD | `src/hexagent/exchangers/double_pipe/solver.py` |
| `SizingRequest` / `SizingRequestIdentity` | `main` HEAD | `src/hexagent/optimization/models.py` / `context.py` |

**Forbidden:** `DoublePipeService.size()` (does not exist), `assumed_u_w_m2_k = 500` (placeholder).

---

## 3. Public API Request DTOs

### 3.1 Design Principle

Public HTTP requests are **independent DTOs** with explicit unit-bearing quantities. They are projected to internal domain models (`DesignCase`, `DoublePipeGeometry`, `SolverParams`, `SizingRequest`) during application-level orchestration.

No public request uses bare unitless floats.

### 3.2 `ValidationApiRequest`

```python
class FluidStreamSpec(StrictBaseModel):
    fluid: FluidSpec                                              # backend + name + composition
    inlet: TPStateSpec                                            # temperature + pressure (unit-bearing)
    mass_flow: MassFlow                                           # kg/s with unit metadata
    phase_hint: PhaseHint = PhaseHint.AUTO
    fouling: FoulingResistance | None = None


class ValidationApiRequest(StrictBaseModel):
    api_schema_version: Literal["1.0"]
    case_name: str                                                # non-empty, trimmed
    hot_stream: FluidStreamSpec
    cold_stream: FluidStreamSpec
    target_duty: Power                                            # W with unit metadata
    minimum_terminal_delta_t: float                               # K (bare — dimensionless unit)
```

- `Power`, `MassFlow`, `AbsoluteTemperature`, `AbsolutePressure`, `FoulingResistance` are `Quantity` subtypes from `hexagent.domain.quantities`.
- Validation endpoint does not execute sizing; it canonicalizes the request and returns a receipt.

### 3.3 `RatingApiRequest`

```python
class RatingApiRequest(StrictBaseModel):
    api_schema_version: Literal["1.0"]
    case: ValidationApiRequest                          # full case validated upstream
    geometry: DoublePipeGeometrySpec                    # explicit geometry DTO (see below)
    tube_in_hot: bool = True
    flow_arrangement: Literal["counterflow", "parallel"]
    tube_boundary_condition: Literal["constant_wall_temperature", "inner_wall_heated"]
    annulus_boundary_condition: Literal["inner_wall_heated", "constant_wall_temperature"]
    minimum_terminal_delta_t: float                     # K
    solver_params: SolverParamsSpec | None = None
    provider_ref: str                                   # key into configured provider registry


class DoublePipeGeometrySpec(StrictBaseModel):
    inner_tube_inner_diameter: Length
    inner_tube_outer_diameter: Length
    outer_pipe_inner_diameter: Length
    effective_length: Length
    wall_thermal_conductivity: float                     # W/(m·K)
    inner_surface_roughness: Length
    annulus_surface_roughness: Length
    inner_fouling_resistance: FoulingResistance
    outer_fouling_resistance: FoulingResistance


class SolverParamsSpec(StrictBaseModel):
    absolute_residual_w: float = 1e-6
    relative_residual_fraction: float = 1e-6
    bracket_temperature_tolerance_k: float = 1e-6
    max_iterations: int = 100
```

- `DoublePipeGeometrySpec` projects to `DoublePipeGeometry` (values extracted from Quantity wrappers).
- `RatingApiRequest` projects to `DesignCase` + `DoublePipeGeometry` + `SolverParams` during orchestration.

### 3.4 `SizingApiRequest`

```python
class SizingApiRequest(StrictBaseModel):
    api_schema_version: Literal["1.0"]
    case: ValidationApiRequest                     # validated upstream
    # Catalog selection
    catalog_identity: str                          # frozen catalog SHA or identity key
    # Materialization bounds
    min_inner_diameter: Length
    max_inner_diameter: Length
    min_outer_diameter: Length
    max_outer_diameter: Length
    min_effective_length: Length
    max_effective_length: Length
    # Combination cap
    raw_combination_cap: int                       # max raw combos before gate
    # Optimization
    optimization_objective: Literal["minimize_outer_area"]
    requested_top_n: int
    # Sizing-specific constraints
    minimum_terminal_delta_t: float                # K
    tube_boundary_condition: Literal["constant_wall_temperature", "inner_wall_heated"]
    annulus_boundary_condition: Literal["inner_wall_heated", "constant_wall_temperature"]
    flow_arrangement: Literal["counterflow", "parallel"]
    tube_in_hot: bool = True
    # Provider
    provider_ref: str                              # key into configured provider registry
    # Solver
    solver_params: SolverParamsSpec | None = None
```

- Projects to internal `SizingRequest` + `SizingRequestIdentity` during orchestration.
- All lengths are unit-bearing `Quantity` subtypes.
- `requested_top_n ≤ raw_combination_cap` enforced at validation boundary.

---

## 4. Application-Service Orchestration Contract

### 4.1 Sizing Orchestration (P0-2)

The HTTP sizing handler MUST execute the following frozen chain. No route-level assembly of engineering results is permitted.

```
RatingApiRequest (or SizingApiRequest)
│
├─ 1. validate_public_request()
│     → rejects at 422 for schema/unit/constraint violations
│
├─ 2. canonicalize_request()
│     → normalizes units to SI, validates catalog identity, computes request_digest
│
├─ 3. project_to_domain()
│     RatingApiRequest  → DesignCase + DoublePipeGeometry + SolverParams
│     SizingApiRequest  → SizingRequest + SizingRequestIdentity
│
├─ 4. sizing_gate()                         [TASK-009 Phase 1]
│     → raw_combination_cap, geometry bounds, passes SizingGate
│
├─ 5. candidate_materialization()           [TASK-009 Phase 1]
│     → produces tuple[ManufacturableCandidate, ...]
│
├─ 6. phase2_candidate_evaluation()         [TASK-008 + TASK-009 Phase 2]
│     → produces tuple[CandidateEvaluationRecord, ...]
│     → dependency injection: PropertyProvider + catalog identity
│
├─ 7. phase3_evaluation_input()             [TASK-009 Phase 3]
│     → constructs Phase3EvaluationInput
│
├─ 8. phase3_classification()              [TASK-009 Phase 3]
│     → per-candidate classify_candidate()
│
├─ 9. deterministic_ranking()               [TASK-009 Phase 3]
│     → primary objective + secondary tie-break
│
├─ 10. top_n_projection()                   [TASK-009 Phase 3]
│      → min(requested_top_n, feasible_count)
│
├─ 11. build_optimization_result()          [TASK-009 Phase 3]
│      → + authoritative verification + provenance construction
│
├─ 12. build_sizing_run_artifacts()         [this contract, §9]
│      → bundles canonical request + all intermediate artifacts + result + provenance
│
└─ 13. build_sizing_run_envelope()          [this contract, §6]
       → discriminated SizingRunEnvelope
```

### 4.2 Rating Orchestration

```
RatingApiRequest
│
├─ 1. validate + canonicalize (same as sizing steps 1-2)
├─ 2. project_to_domain() → DesignCase + DoublePipeGeometry + SolverParams
├─ 3. rate_double_pipe()                   [TASK-008]
│      → dependency injection: PropertyProvider
├─ 4. build_rating_run_artifacts()         [this contract, §9]
├─ 5. build_rating_run_envelope()          [this contract, §6]
```

### 4.3 Forbidden Paths

- `DoublePipeService.size()` — does not exist in production code; must not be called, imported, or tested as reachable.
- Any assumed-U, placeholder-area, or starter-result logic.
- Route handler directly assembling `OptimizationResult` fields.
- Bypassing TASK-009 artifact construction or authoritative verification.

---

## 5. API Endpoints

### 5.1 Endpoint Summary

| Method | Path | operation_id | Request DTO | Response Envelope |
|---|---|---|---|---|
| POST | `/v1/cases/validate` | `validateCase` | `ValidationApiRequest` | `ValidationRunEnvelope` |
| POST | `/v1/double-pipe/rating` | `rateDoublePipe` | `RatingApiRequest` | `RatingRunEnvelope` |
| POST | `/v1/double-pipe/sizing` | `sizeDoublePipe` | `SizingApiRequest` | `SizingRunEnvelope` |
| GET | `/v1/runs/{run_id}` | `getRun` | — (path param only) | `AnyRunEnvelope` |
| GET | `/v1/runs/{run_id}/report.html` | `getRunReportHtml` | — | `text/html` |
| GET | `/v1/runs/{run_id}/report.pdf` | `getRunReportPdf` | — | `application/pdf` or 501 |

### 5.2 `POST /v1/cases/validate`

- **Request:** `ValidationApiRequest`
- **Response:** `ValidationRunEnvelope` — `result_kind = "validation"`, no domain computation result
- **Status:** `200` (accepted + canonicalized); `422` (schema/unit/constraint)
- **Idempotency:** Not enforced
- **Result hash:** `validation_receipt_hash` — computed from canonical request payload + validation schema version (not a provenance-derived domain result hash)

### 5.3 `POST /v1/double-pipe/rating`

- **Request:** `RatingApiRequest`
- **Response:** `RatingRunEnvelope` — `result_kind = "rating"`, `result = RatingResult`
- **Domain → HTTP:** `SUCCEEDED` → `200`; `BLOCKED` → `200`; controlled `FAILED` → `200`
- **HTTP 500:** Unexpected server exception only
- **Idempotency:** Required

### 5.4 `POST /v1/double-pipe/sizing`

- **Request:** `SizingApiRequest`
- **Response:** `SizingRunEnvelope` — `result_kind = "sizing"`, `result = OptimizationResult`
- **Domain → HTTP:** `COMPLETE` → `200`; `PARTIAL` (strict-stop) → `200`; input rejection → `422`
- **Idempotency:** Required

### 5.5 `GET /v1/runs/{run_id}`

- **Path param:** `run_id: UUID` (validated via Pydantic `UUID` type, not bare `str`)
- **Response:** Stored envelope (discriminated union)
- **Status:** `200` (found); `404` (unknown)

### 5.6 `GET /v1/runs/{run_id}/report.html`

- **Response:** `text/html; charset=utf-8`
- **Status:** `200`; `404`; `500` (unexpected rendering failure)
- **Authority:** Built from stored envelope + artifact bundle — no re-computation

### 5.7 `GET /v1/runs/{run_id}/report.pdf`

- **Response:** `application/pdf` (adapter configured) or `HTTP 501` (no adapter)
- **No adapter:** Structured `ApiError` body, status 501

---

## 6. Discriminated Run Envelopes (P0-3)

### 6.1 Union Type

```python
from pydantic import Discriminator

AnyRunEnvelope = Annotated[
    ValidationRunEnvelope | RatingRunEnvelope | SizingRunEnvelope,
    Discriminator("result_kind"),
]
```

### 6.2 `ValidationRunEnvelope`

```python
class ValidationRunEnvelope(StrictBaseModel):
    api_schema_version: Literal["1"]
    operation: Literal["validateCase"]
    run_id: UUID
    request_digest: str                                    # sha256 of canonical request
    result_kind: Literal["validation"]
    result: None                                           # MUST be None
    validation_receipt_hash: str                           # not a domain result hash
    report_links: ReportLinks
```

### 6.3 `RatingRunEnvelope`

```python
class RatingRunEnvelope(StrictBaseModel):
    api_schema_version: Literal["1"]
    operation: Literal["rateDoublePipe"]
    run_id: UUID
    idempotency_key_digest: str
    request_digest: str
    result_kind: Literal["rating"]
    result: RatingResult                                   # TASK-008 RatingResult
    result_hash: str                                       # == result.result_hash
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None
    provenance: ProvenanceGraph                            # TASK-008 provenance
    artifact_bundle_digest: str                            # §9 RatingRunArtifacts
    report_links: ReportLinks

    @model_validator(mode="after")
    def _validate_cross_field(self) -> typing.Self:
        if self.result_hash != self.result.result_hash:
            raise ValueError("result_hash != result.result_hash")
        if self.warnings != self.result.warnings:
            raise ValueError("warning projection mismatch")
        if self.blockers != self.result.blockers:
            raise ValueError("blocker projection mismatch")
        if self.failure != self.result.failure:
            raise ValueError("failure projection mismatch")
        return self
```

### 6.4 `SizingRunEnvelope`

```python
class SizingRunEnvelope(StrictBaseModel):
    api_schema_version: Literal["1"]
    operation: Literal["sizeDoublePipe"]
    run_id: UUID
    idempotency_key_digest: str
    request_digest: str
    result_kind: Literal["sizing"]
    result: OptimizationResult                            # TASK-009 OptimizationResult
    result_hash: str                                      # == result.result_hash
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None
    provenance: ProvenanceGraph                           # TASK-009 provenance
    artifact_bundle_digest: str                           # §9 SizingRunArtifacts
    report_links: ReportLinks

    @model_validator(mode="after")
    def _validate_cross_field(self) -> typing.Self:
        if self.result_hash != self.result.result_hash:
            raise ValueError("result_hash != result.result_hash")
        # Warnings/blockers projected from ordered_*_digests in OptimizationResult
        return self
```

### 6.5 Cross-Field Invariants

| Invariant | Enforcement |
|---|---|
| Rating envelope MUST NOT carry `OptimizationResult` | Discriminated union + typed `result` field |
| Sizing envelope MUST NOT carry `RatingResult` | Discriminated union + typed `result` field |
| Validation envelope `result` MUST be `None` | Explicit `None` type |
| Outer `result_hash` MUST equal inner `result.result_hash` | `@model_validator` cross-check |
| Warnings/blockers/failure MUST be projections from authoritative result | Model validator or build-time projection |

---

## 7. Idempotency Contract (P0-5)

### 7.1 Request Header

```
Idempotency-Key: <1-128 printable ASCII, trimmed, no control characters>
```

### 7.2 Identity Namespace

```python
def compute_idempotency_namespace_digest(
    *,
    api_schema_version: str,
    operation_id: str,
    idempotency_key: str,               # trimmed
) -> str:
    return sha256_digest({
        "api_schema_version": api_schema_version,
        "operation_id": operation_id,
        "idempotency_key_digest": sha256_digest(idempotency_key),
    })
```

### 7.3 Run Repository Protocol

```python
from typing import Protocol
from uuid import UUID

class RunRepository(Protocol):
    """Process-local, non-persistent run store with atomic claim-or-get."""

    def claim_or_get(
        self,
        *,
        namespace_digest: str,
        request_digest: str,
        create_run: Callable[[], tuple[UUID, AnyRunEnvelope]],
    ) -> tuple[UUID, AnyRunEnvelope, bool]:
        """Atomically claim or retrieve a run.

        Returns (run_id, envelope, is_new).
        - Same namespace + same request_digest → returns existing (is_new=False)
        - Same namespace + different request_digest → raises IdempotencyConflict (HTTP 409)
        - New namespace → creates via `create_run` (is_new=True)
        """
        ...

    def complete(
        self,
        run_id: UUID,
        envelope: AnyRunEnvelope,
    ) -> None:
        """Store the final envelope after run completion."""
        ...

    def get_by_run_id(self, run_id: UUID) -> AnyRunEnvelope | None: ...


class InMemoryRunRepository:
    """Reference implementation — lost on restart, no multi-process consistency.

    Uses threading.Lock for single-process atomicity on claim_or_get.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._namespace_map: dict[str, UUID] = {}        # namespace_digest → run_id
        self._store: dict[UUID, AnyRunEnvelope] = {}     # run_id → envelope
```

### 7.4 Behavior Matrix

| Condition | Outcome |
|---|---|
| Same namespace + same `request_digest` | Return same `run_id` + same envelope; `is_new=False` |
| Same namespace + different `request_digest` | Raise `IdempotencyConflict` → `HTTP 409` |
| Same key + different `operation_id` | Different namespace (namespace includes `operation_id`) |
| Concurrent same-namespace + same-digest | `threading.Lock` serialises; one wins, others get existing |
| JSON key order change in request | No effect (canonical JSON normalises key order before digest) |

### 7.5 Scope Limitations

- Process-local only; not persistent; lost on restart.
- Not suitable for multi-process or distributed deployments.
- Does not claim exactly-once delivery.

---

## 8. Canonical Request Algorithm (P0-6)

### 8.1 Entry Point

```python
def canonical_api_request_payload(request: StrictBaseModel) -> dict[str, object]:
    """Produce a deterministic canonical payload dict for a validated API request.

    Preconditions:
    1. Request has passed strict schema validation (Pydantic, extra="forbid").
    2. All Quantity fields have been resolved to their SI canonical form.
    """


def compute_api_request_digest(request: StrictBaseModel) -> str:
    """sha256 of canonical_api_request_payload(request)."""
    return sha256_digest(canonical_api_request_payload(request))
```

### 8.2 Canonicalization Rules

| Aspect | Rule |
|---|---|
| Dict key order | Recursively sorted by key (Python `sort_keys=True` equivalent) |
| `None` values | **Retained** (explicit null in canonical payload) |
| Pydantic aliases | **Not used** — field names only |
| Pydantic defaults | **Explicitly expanded** (no omission of default-valued fields) |
| `Enum` members | Encoded as `.value` (string) |
| `UUID` | Encoded as canonical 36-char string (`str(uuid)`) |
| `tuple` / `list` | Encoded as JSON list |
| `Decimal` | Encoded as `str(decimal)` (normalized, no trailing zeros) |
| `float` | Encoded with `repr()` (full precision, `nan`/`inf` → rejected at validation) |
| `int` vs `float` | Distinguishable (`1` ≠ `1.0`); both rejected if ambiguous |
| Unicode | NFC normalized |
| `Quantity` subtypes | Encoded as `{"value": <canonical SI value>, "unit": "<SI unit symbol>"}` |
| Catalog identity | Bound as content-hash of canonical catalog snapshot |
| Provider config | Fingerprint from `provider.name` + `provider.version` + `provider.reference_state_policy` |
| Negative zero | Forbidden (rejected at validation boundary) |

### 8.3 Single Authority

All idempotency identity, `request_digest`, and report input snapshot MUST call `compute_api_request_digest()` — no hand-rolled alternatives.

---

## 9. Authoritative Artifact Bundles (P0-4)

### 9.1 `RatingRunArtifacts`

```python
class RatingRunArtifacts(StrictBaseModel):
    canonical_request_snapshot: dict[str, object]          # from canonical_api_request_payload
    request_identity: CaseIdentity                         # normalized case identity
    geometry_snapshot: DoublePipeGeometry
    solver_settings: SolverParams
    provider_identity: ProviderIdentitySnapshot
    result: RatingResult                                   # the authoritative RatingResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str                            # sha256 over canonical bundle payload
```

### 9.2 `SizingRunArtifacts`

```python
class SizingRunArtifacts(StrictBaseModel):
    canonical_request_snapshot: dict[str, object]
    sizing_request_identity: SizingRequestIdentity
    passed_gate: SizingGate                               # TASK-009 gate result
    materialization_result: MaterializationResult          # raw + passed candidates
    evaluation_input: Phase3EvaluationInput
    source_evaluation_records: tuple[CandidateEvaluationRecord, ...]
    identity_snapshots: tuple[Phase2SourceRecordIdentitySnapshot, ...]
    complete_snapshots: tuple[Phase2SourceRecordSnapshot | None, ...]
    source_record_descriptors: tuple[Phase2SourceRecordDescriptor | None, ...]
    source_bindings: tuple[Phase3SourceRecordBinding | None, ...]
    preparation_results: tuple[Phase3CandidatePreparationResult | None, ...]
    candidate_dispositions: tuple[CandidateDispositionRecord, ...]
    ranked_candidate_records: tuple[RankedCandidateRecord, ...]
    top_n_records: tuple[RankedCandidateRecord, ...]
    manufactured_candidates: tuple[ManufacturableCandidate, ...]
    optimization_result: OptimizationResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str
```

### 9.3 Verifier Replay

Both bundles MUST support:

```python
def verify_rating_artifact_bundle(bundle: RatingRunArtifacts) -> None:
    """Replay all authoritative verifiers against independent artifacts."""
    # 1) Provenance semantic verification
    # 2) RatingResult cross-field validator
    # 3) Geometry ↔ result consistency
    # 4) Artifact bundle digest recomputation

def verify_sizing_artifact_bundle(bundle: SizingRunArtifacts) -> None:
    """Replay all authoritative verifiers against independent artifacts."""
    # 1) Phase3EvaluationInput.verify_or_raise()
    # 2) Per-index identity snapshot, complete snapshot, descriptor, binding, prep result, disposition
    # 3) verify_phase3_result_semantics_or_raise()
    # 4) Provenance semantic verification
    # 5) Artifact bundle digest recomputation
```

Bundle verification is NOT a digest-format check. It re-executes every per-artifact `verify_or_raise()` against independent authority.

---

## 10. Report Model (P0-7, P0-8)

### 10.1 Discriminated Report Artifact

```python
class ReportArtifactKind(StrEnum):
    PRESENT = "present"
    NOT_AVAILABLE = "not_available"
    NOT_IMPLEMENTED = "not_implemented"
    OUT_OF_SCOPE = "out_of_scope"


class PresentReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.PRESENT]
    artifact_id: str
    source_json_pointer: str                               # RFC 6901 pointer into source envelope
    authority_digest: str                                  # hash identifying the source artifact
    canonical_raw_value: str                               # canonical string form of raw value
    source_unit: str | None
    display_unit: str | None
    formatter_id: str
    formatter_version: str
    rounding_mode: str
    formatted_display_value: str


class UnavailableReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.NOT_AVAILABLE]
    artifact_id: str
    reason_code: str                                       # e.g. "RATING_NOT_EXECUTED"
    capability: str                                        # e.g. "heat_balance"


class NotImplementedReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.NOT_IMPLEMENTED]
    artifact_id: str
    capability: str                                        # e.g. "pressure_drop"


class OutOfScopeReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.OUT_OF_SCOPE]
    artifact_id: str
    capability: str                                        # e.g. "cost_estimate"


ReportArtifact = Annotated[
    PresentReportArtifact | UnavailableReportArtifact
    | NotImplementedReportArtifact | OutOfScopeReportArtifact,
    Discriminator("kind"),
]
```

- Non-PRESENT artifacts have **no** `source_json_pointer`, `authority_digest`, `canonical_raw_value`, or units.
- No fake `null` pointers for missing data.

### 10.2 Report Model and Hashing

```python
class DoublePipeReportModel(StrictBaseModel):
    report_schema_version: Literal["1"]
    sections: tuple[ReportSection, ...]                    # fixed order, unique section_id
    report_content_hash: str                               # sha256 of canonical sections payload
    report_instance_hash: str                              # binds content + source + template


class ReportSection(StrictBaseModel):
    section_id: ReportSectionId                            # enum, see §10.3
    status: ReportSectionStatus
    artifacts: tuple[ReportArtifact, ...]


class ReportInstanceIdentity(StrictBaseModel):
    report_schema_version: Literal["1"]
    report_content_hash: str
    source_run_envelope_digest: str                        # sha256 of source RunEnvelope
    source_domain_result_hash: str                         # from RatingResult.result_hash or OptimizationResult.result_hash
    source_artifact_bundle_digest: str                     # from §9
    template_id: str
    template_version: str
    template_definition_hash: str
    formatter_registry_version: str
```

- `report_content_hash`: engineering-deterministic — same input artifacts → same hash.
- `report_instance_hash = sha256_digest(canonical_payload(ReportInstanceIdentity))`: run-instance-deterministic.
- Run-level metadata (timestamp, PID, host, trace, temp path) excluded from `report_content_hash`.

### 10.3 Report Section Enum

```python
class ReportSectionId(StrEnum):
    STATUS_BANNER = "status_banner"
    RUN_IDENTITY = "run_identity"
    INPUT_SUMMARY = "input_summary"
    HEAT_BALANCE = "heat_balance"
    GEOMETRY = "geometry"
    THERMAL_PERFORMANCE = "thermal_performance"
    SIZING_RANKING = "sizing_ranking"
    TOP_RANKED_CANDIDATES = "top_ranked_candidates"
    WARNINGS = "warnings"
    BLOCKERS = "blockers"
    FAILURE_DETAILS = "failure_details"
    PROVENANCE = "provenance"
    INTEGRITY = "integrity"


MANDATORY_SECTIONS: tuple[ReportSectionId, ...] = (
    ReportSectionId.STATUS_BANNER,
    ReportSectionId.RUN_IDENTITY,
    ReportSectionId.BLOCKERS,
    ReportSectionId.FAILURE_DETAILS,
    ReportSectionId.INTEGRITY,
)

SECTION_ORDER: tuple[ReportSectionId, ...] = (
    ReportSectionId.STATUS_BANNER,
    ReportSectionId.RUN_IDENTITY,
    ReportSectionId.INPUT_SUMMARY,
    ReportSectionId.GEOMETRY,
    ReportSectionId.HEAT_BALANCE,
    ReportSectionId.THERMAL_PERFORMANCE,
    ReportSectionId.SIZING_RANKING,
    ReportSectionId.TOP_RANKED_CANDIDATES,
    ReportSectionId.WARNINGS,
    ReportSectionId.BLOCKERS,
    ReportSectionId.FAILURE_DETAILS,
    ReportSectionId.PROVENANCE,
    ReportSectionId.INTEGRITY,
)
```

### 10.4 Pre-Render Verification Chain

Before any HTML is emitted, the following MUST pass:

1. Domain result verification (RatingResult or OptimizationResult)
2. Provenance verification
3. Artifact bundle verification (§9.3)
4. Envelope projection verification (warnings/blockers/failure parity)
5. Report model verification (section uniqueness, mandatory set, order)
6. Template identity verification (template_definition_hash matches)
7. Any failure → render fails closed (no partial output)

---

## 11. Status Banner

The status banner MUST bind to the authoritative domain result:

| Envelope | Source Field |
|---|---|
| `RatingRunEnvelope` | `result.status` (`SUCCEEDED` / `BLOCKED` / `FAILED`) |
| `SizingRunEnvelope` | `result.termination_status` (`COMPLETE` / `PARTIAL`) |

---

## 12. Top-Ranked Candidates (P0-10)

The section formerly named `selected_candidate` is renamed to `top_ranked_candidates`.

TASK-009 authorises deterministic ranking and Top-N projection only — it does NOT authorise recommendation, approval, procurement selection, or any "selected" semantics.

The following words MUST NOT appear in report labels: `selected`, `recommended`, `approved`, `procurement-ready`.

---

## 13. Status and Risk Display

### 13.1 Every Print Page

Every HTML page produced by the report renderer MUST display:

```
PRELIMINARY
NOT FOR PROCUREMENT
NOT FOR CONSTRUCTION
```

This is static boilerplate inserted by the renderer. It is:

- Present in the repeating `@media print` header/footer DOM
- Visible in normal (screen) view as well
- Not suppressible by user configuration
- Not colour-dependent

### 13.2 Blocker Display

When `RunEnvelope.blockers` is non-empty:
- Blockers appear at the top of the report (above or integrated into the status banner)
- NOT restricted to an appendix
- NOT softened by narrative
- NOT relying solely on colour for severity

### 13.3 Not-Implemented Capabilities

| Capability | Display |
|---|---|
| Pressure drop | `NOT_IMPLEMENTED` |
| Velocity constraints | `NOT_IMPLEMENTED` |
| Materials | `OUT_OF_SCOPE` |
| Cost | `OUT_OF_SCOPE` |
| Mechanical compliance | `OUT_OF_SCOPE` |
| Procurement readiness | `OUT_OF_SCOPE` |

Never display: `0`, `PASS`, `COMPLIANT`, `ACCEPTABLE`.

---

## 14. HTML Security Contract

- Template engine autoescape enabled (HTML-escape all variables by default)
- User-specified template path forbidden
- Arbitrary file-system reads forbidden
- External network resources (CDNs, fonts, tracking pixels) forbidden
- User-provided input (case name, fluid name, message content, context tuples) HTML-escaped
- Environment variables, tokens, absolute paths, tracebacks NOT in rendered output
- No `| safe` or equivalent on user-originated data

---

## 15. PDF Boundary

```python
class PdfReportAdapter(Protocol):
    def render_pdf(self, html: str, *, report_id: str) -> bytes: ...
```

- No adapter configured → `GET /v1/runs/{run_id}/report.pdf` returns `HTTP 501` with `ApiError` body
- No empty PDF, no fake link, no degraded fallback
- Specific PDF engine selection is out of scope

---

## 16. Determinism Contract

### 16.1 Engineering Content Determinism

Same inputs → same `report_content_hash`:

| Input | Deterministic Output |
|---|---|
| Canonical request payload | `request_digest` |
| Provider identity (name + version + config fingerprint) | Same domain result |
| Catalog identity (frozen catalog SHA) | Same `OptimizationResult` |
| Solver settings (tolerances, max iterations) | Same solver convergence |
| Template version + definition hash | Same HTML structure |
| Report model version | Same `report_content_hash` |

### 16.2 Run Instance Determinism

Same stored `run_id` → repeated GET returns identical envelope + report bytes.

### 16.3 HTML Byte Determinism

Same canonical request + same template + same formatter → byte-identical HTML engineering content.

### 16.4 Excluded from Engineering Hashes

| Field | Rationale |
|---|---|
| `current_time` / timestamp | Non-deterministic |
| `run_id` | Random UUID |
| Process ID | OS-specific |
| Host name | Environment-specific |
| Trace ID | Observability, not engineering |
| Temporary directory | File-system layout |

---

## 17. Error Envelope

```python
class ApiErrorCode(StrEnum):
    VALIDATION_FAILED = "validation_failed"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    RUN_NOT_FOUND = "run_not_found"
    PDF_NOT_AVAILABLE = "pdf_not_available"
    INTERNAL_ERROR = "internal_error"


class ApiError(StrictBaseModel):
    api_schema_version: Literal["1"]
    operation: str | None
    status_code: int
    error_code: ApiErrorCode
    error_message: str                              # human-readable, no traceback/path/token
    request_digest: str | None
    details: tuple[ErrorDetail, ...]                # max 20 items
    MAX_DISPLAYED_VALUE_LENGTH: ClassVar[int] = 200


class ErrorDetail(StrictBaseModel):
    field: str | None                                # JSON pointer or empty
    reason: str
    value: str | None                                # truncated to MAX_DISPLAYED_VALUE_LENGTH
```

### 17.1 HTTP Mapping

| HTTP Status | `error_code` | Condition |
|---|---|---|
| 404 | `RUN_NOT_FOUND` | Unknown `run_id` |
| 409 | `IDEMPOTENCY_CONFLICT` | Same namespace, different request |
| 422 | `VALIDATION_FAILED` | Schema/unit/constraint failure |
| 500 | `INTERNAL_ERROR` | Unexpected exception (no traceback/path/token leak) |
| 501 | `PDF_NOT_AVAILABLE` | PDF endpoint, no adapter |

---

## 18. TASK-010 Implementation Scope (P0-9)

TASK-010 implementation **includes** (when authorized):

| Component | Description |
|---|---|
| FastAPI application / router | Endpoint registration per §5 |
| Request/response DTOs | Pydantic models per §3, §6 |
| Application services | Orchestration per §4 |
| Exception handlers | FastAPI exception → `ApiError` mapping |
| OpenAPI schema | Auto-generated from Pydantic models |
| In-memory idempotency/run repository | Per §7 |
| HTML report model builder | Constructs `DoublePipeReportModel` from envelope + artifact bundle |
| HTML renderer | Jinja2 or equivalent; autoescape; per §14 |
| Report retrieval endpoints | `getRunReportHtml`, `getRunReportPdf` |
| Integration tests | Full pipeline, determinism, idempotency |
| Security tests | HTML escaping, path/token leak detection |

TASK-010 implementation **excludes**:

- Database, ORM, persistent storage
- Object storage
- Authentication, authorization, rate limiting
- Specific PDF engine integration
- TASK-011+
- C4, pressure drop, velocity constraints, materials, cost, mechanical compliance

The design contract is **design-only**. Implementation is `BLOCKED` pending independent review and explicit authorization.

---

## 19. Test Contract

| # | Test | Expected Outcome |
|---|---|---|
| T1 | `operation_id` values unique and stable across 6 endpoints | 6 unique IDs |
| T2 | Public request DTO JSON Schema exportable | Valid JSON Schema draft-07 |
| T3 | Bare unitless float in public request → `422` | Quantity validation |
| T4 | Invalid unit string → `422` | Enum validation |
| T5 | Unknown field in request → `422` | `extra="forbid"` |
| T6 | `ValidationApiRequest` + same payload → same `validation_receipt_hash` | Deterministic |
| T7 | `ValidationApiRequest` + different payload → different `validation_receipt_hash` | Discriminative |
| T8 | Canonical request: sorted vs unsorted JSON keys → same `request_digest` | Key-order independence |
| T9 | Canonical request: different value → different `request_digest` | Value sensitivity |
| T10 | Rating → `RatingRunEnvelope` carries `RatingResult`, not `OptimizationResult` | Type enforcement |
| T11 | Sizing → `SizingRunEnvelope` carries `OptimizationResult`, not `RatingResult` | Type enforcement |
| T12 | Validation → `result` is `None` | Cross-field invariant |
| T13 | Envelope `result_hash` mismatch → model validator rejects | Cross-field invariant |
| T14 | Warning projection mismatch → model validator rejects | Cross-field invariant |
| T15 | Same namespace + same `request_digest` → same `run_id` + same envelope | Idempotency hit |
| T16 | Same namespace + different `request_digest` → `IdempotencyConflict` → `409` | Idempotency collision |
| T17 | Same key + different `operation_id` → independent namespaces | Namespace isolation |
| T18 | Concurrent same-namespace + same-digest → one wins, others get existing | Atomic claim-or-get |
| T19 | `BLOCKED` rating result → `HTTP 200` | Not `500` |
| T20 | Unknown `run_id` → `404` with `RUN_NOT_FOUND` | Repository miss |
| T21 | Unhandled exception → `HTTP 500` with `INTERNAL_ERROR`, no traceback/path/token | Structured error, regex on body |
| T22 | PDF endpoint no adapter → `HTTP 501` with `PDF_NOT_AVAILABLE` | Structured error |
| T23 | Artifact bundle: `verify_sizing_artifact_bundle()` replays all per-artifact verifiers | Independent authority replay |
| T24 | Artifact bundle: tampered `artifact_bundle_digest` → rejected | Digest cross-check |
| T25 | Report: `ReportValueBinding.source_json_pointer` resolves to correct value in envelope | RFC 6901 pointer resolution |
| T26 | Report: PRESENT artifact missing `source_json_pointer` → rejected | Invariant enforcement |
| T27 | Report: NOT_IMPLEMENTED artifact has `source_json_pointer` → rejected | Invariant enforcement |
| T28 | Report: duplicate `section_id` → rejected | Uniqueness enforcement |
| T29 | Report: missing mandatory section → rejected | Mandatory set enforcement |
| T30 | Report: wrong section order → rejected | Order enforcement |
| T31 | Report: tampered `report_content_hash` → render rejects | Fail-closed |
| T32 | Report: tampered source envelope digest in `ReportInstanceIdentity` → render rejects | Fail-closed |
| T33 | Report: tampered artifact bundle digest in `ReportInstanceIdentity` → render rejects | Fail-closed |
| T34 | Report: tampered template `definition_hash` → render rejects | Template identity |
| T35 | Blocker present → "BLOCKED" text in HTML top banner | String search |
| T36 | HTML print-header DOM contains "PRELIMINARY" / "NOT FOR PROCUREMENT" / "NOT FOR CONSTRUCTION" | 3-string check in `@media print` structure |
| T37 | Disclaimer visible in normal (screen) view | Not print-only |
| T38 | HTML injection in case name → escaped (`&lt;script&gt;`) | Autoescape enforcement |
| T39 | No absolute path, traceback, or environment variable in error response body | Regex exclusion |
| T40 | Pressure drop / velocity → `NOT_IMPLEMENTED` in report | String search |
| T41 | Materials / cost / mechanical / procurement → `OUT_OF_SCOPE` in report | String search |
| T42 | Report does not contain "selected" / "recommended" / "approved" | Negative string search |
| T43 | Same canonical request → byte-identical HTML engineering content | `report_content_hash` equality |
| T44 | Same stored run → repeated GET returns identical report | Run instance determinism |
| T45 | Placeholder `DoublePipeService.size()` unreachable | Import check |
| T46 | Python 3.11 full suite passes | Exit 0 |
| T47 | Python 3.12 full suite passes | Exit 0 |

---

## 20. Explicit Exclusions

- Production API server implementation (FastAPI app, routing, middleware)
- HTML template engine or HTML rendering implementation
- PDF engine selection, integration, or rendering
- Database, ORM, persistent storage, object storage
- Authentication, authorization, rate limiting
- TASK-011+, C4, pressure drop, velocity constraints, materials, cost, mechanical compliance
- Stochastic or heuristic optimization
- Procurement conclusions or compliance claims

---

## 21. Design Status

| Field | Value |
|---|---|
| TASK-010 design | READY_FOR_REVIEW |
| TASK-010 implementation | BLOCKED |
| Frozen Contract SHA | NOT ESTABLISHED |
| Implementation Authorization | NOT GRANTED |
