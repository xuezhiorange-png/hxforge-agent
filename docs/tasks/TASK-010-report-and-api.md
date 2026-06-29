# TASK-010 — Versioned API and Traceable Report Contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** PENDING RE-REVIEW
**Frozen Contract SHA:** NOT ESTABLISHED
**Implementation Authorization:** NOT GRANTED

---

## 1. Scope

Freeze the normative API request/response DTOs, discriminated run envelopes, idempotency semantics, canonical request algorithm, artifact bundles, report model, and traceable HTML report contract for the hxforge-agent double-pipe vertical slice.

**This PR is docs-only. It does not implement any production code.**

### 1.1 Phase-Based Scope

| Phase | Scope |
|---|---|
| **Current PR (design-only)** | Frozen contract text, Pydantic type signatures, algorithmic rules, test scenarios. No `src/`, no `tests/`. |
| **TASK-010 implementation (when authorized)** | FastAPI app/router, request/response DTOs, application services, exception handlers, OpenAPI, in-memory RunRepository, HTML report builder, HTML renderer, report retrieval endpoints, integration/determinism/security tests. |
| **TASK-010 product scope (permanent exclusions)** | Database, ORM, persistent storage, object storage, authentication, authorization, rate limiting, specific PDF engine, TASK-011+, C4, pressure drop computation, velocity constraints, materials, cost, mechanical compliance. |

---

## 2. Upstream Dependencies

| Artifact | Frozen commit SHA-1 (40 hex) | Repository path | Git blob SHA-1 (40 hex) | Content SHA-256 (64 hex) |
|---|---|---|---|---|
| TASK-008 merge (PR #21) | `cef3f85402b1696b336347293afc7276bbf67545` | — | — | — |
| `RatingResult` typed schema | (at TASK-008 merge) | `src/hexagent/exchangers/double_pipe/result.py` | `8e0f05538192521d24481594229acc1a1895a82c` | `54b0a008785428fc403ad6ac8127174dcc9230e65b58677719adeaea40a173bb` |
| TASK-009 merge (PR #24) | `8f2ef3014bedfbd1592ab36264af580f50b8cb6d` | — | — | — |
| `DesignCase` / `StreamSpec` / `FoulingResistanceSpec` | (at TASK-009 merge) | `src/hexagent/domain/models.py` | `a2149708a11b75c8ba09fb11f40e0212dfd1208a` | `148baef75c33f71800e80e769800b5a14d793d19c3b755d676f090af8e395407` |
| `Quantity` subtypes | (at TASK-009 merge) | `src/hexagent/domain/quantities.py` | `bc26ea02eca84771e85dfe0a5e58b3bfac4a227f` | `b9a066c941a11458e3eacf890d5cd87eb0abfe356b5fe6cb16bd9bd7f72ecb89` |
| `DoublePipeGeometry` | (at TASK-008 merge) | `src/hexagent/exchangers/double_pipe/geometry.py` | `c6a4acfdf27c07685a8bdbf11838148b3f81eabc` | `aeaf79077b7de9f891fd889a2fad67cb780c1b3adf83925659530aaf6616fd8e` |
| `SolverParams` | (at TASK-008 merge) | `src/hexagent/exchangers/double_pipe/solver.py` | `1ed290fd98fa877443cac57f3f59cc08038da01d` | `d8ed22aaea324534263e8950cd6e4bdc93ba0ec39899fa1ed8f4176bbc4b0737` |
| `SizingRequest` / `CatalogSnapshotRef` | (at TASK-009 merge) | `src/hexagent/optimization/models.py` | `baeba79b9be42535ca33bcbb5048115dae1e9c67` | `ea8235473eb3e2c322d825ffe2bc739c3ceec15881c14da2612041a42c1a7379` |
| `SizingRequestIdentity` / `OptimizationObjective` / `ExpectedProviderIdentity` / `PassedSizingGate` | (at TASK-009 merge) | `src/hexagent/optimization/context.py` | `076126034eaf4116506ecbae54b32e644b4fc1c8` | `fa23a2e6a6d0c1544bc522933fbf3d87c4baed2d42a4ab9e6da78f7dcbb2a14b` |
| `Phase3AuthoritativeArtifacts` / `CandidateEvaluationRecord` / `CandidateDispositionRecord` / `RankedCandidateRecord` | (at TASK-009 merge) | `src/hexagent/optimization/evaluation.py` | `0f69d84f0a7a29ab1417d7b24dadc35bdcefaab1` | `b5d3e85b14873671956a88bcc050cf7bd16e952f40ebe35b1218794304c1943b` |
| `Phase3` builder (`build_optimization_result`) | (at TASK-009 merge) | `src/hexagent/optimization/phase3_builder.py` | `6921bd2ef65a719e49cfec854fdf85e8c9009f5b` | (per blob SHA-1) |
| `Phase3` verifier (`verify_phase3_result_semantics_or_raise`) | (at TASK-009 merge) | `src/hexagent/optimization/phase3_verifier.py` | `09b2020799ca2ef4cf1cbb9b15a6f88fea95c866` | (per blob SHA-1) |
| Base `main` | `3af8eb85e2a293c2706402dae8ec317a45fed38a` (PR #27 merge) | — | — | — |

**SHA-1 columns are 40-character hexadecimal git object hashes. SHA-256 columns are 64-character hexadecimal content hashes obtained via `sha256sum`.** No shortened or placeholder values are permitted.

**`api_schema_version` is unified to `Literal["1"]` in all DTOs, envelopes, and the report model.**

### 2.1 Placeholder sizing path

**Forbidden:** `DoublePipeService.size()` — EXISTS in production at `src/hexagent/exchangers/double_pipe/service.py:140`. Contains `assumed_u = 500.0`. TASK-010 routes and application services MUST NOT call it. The API integration test must monkeypatch/trap this exact method and prove no TASK-010 code path invokes it. An import-time check is insufficient (see test T45).

---

## 3. Public API Request DTOs

### 3.1 Design Principle

Public HTTP requests are independent `StrictBaseModel`-based DTOs with explicit unit-bearing `Quantity` subtypes. They project to internal domain models during application-level orchestration.

**No public request uses bare unitless floats for dimensional quantities.** Every dimensional field uses a typed `Quantity` subclass.

All DTOs are `frozen`, `extra="forbid"`.

### 3.2 `ValidationApiRequest`

```python
class FluidStreamSpec(StrictBaseModel):
    fluid: FluidSpec                                    # backend + name + composition
    inlet: TPStateSpec                                  # temperature + pressure (unit-bearing)
    mass_flow: MassFlow                                  # kg/s
    phase_hint: PhaseHint = PhaseHint.AUTO
    fouling: FoulingResistanceSpec                       # with provenance


class ValidationApiRequest(StrictBaseModel):
    api_schema_version: Literal["1"]
    case_name: str                                       # non-empty, trimmed
    hot_stream: FluidStreamSpec
    cold_stream: FluidStreamSpec
    target_duty: Power | None = None                     # W with unit metadata
    minimum_terminal_delta_t: TemperatureDifference      # K with unit metadata
    design_pressure_hot: AbsolutePressure
    design_pressure_cold: AbsolutePressure
    design_temperature_hot: AbsoluteTemperature
    design_temperature_cold: AbsoluteTemperature
    required_area_margin_fraction: float = Field(ge=0.0, le=1.0)
```

**Rejection rules:**
- `FluidSpec` already has `phase_hint` — if `FluidStreamSpec` re-declares it, the two must agree or the request is rejected.
- `minimum_terminal_delta_t` is a single authoritative field; rating/sizing requests do not re-declare it.

#### 3.2.1 Projection to `DesignCase`

| ValidationApiRequest field | DesignCase field |
|---|---|
| `case_name` | `name` |
| `hot_stream.fluid` | `hot_stream.fluid` |
| `hot_stream.inlet` → `TPStateSpec` | `hot_stream.state_spec` |
| `hot_stream.mass_flow` | `hot_stream.mass_flow` |
| `hot_stream.fouling` | `hot_stream.fouling_resistance` |
| `cold_stream.fluid` | `cold_stream.fluid` |
| `cold_stream.inlet` → `TPStateSpec` | `cold_stream.state_spec` |
| `cold_stream.mass_flow` | `cold_stream.mass_flow` |
| `cold_stream.fouling` | `cold_stream.fouling_resistance` |
| `target_duty` | `target_duty` |
| `design_pressure_hot` … `required_area_margin_fraction` | `constraints: DesignConstraints(...)` |
| — | `id` (generated UUID) |

### 3.3 `RatingApiRequest`

```python
class RatingApiRequest(StrictBaseModel):
    api_schema_version: Literal["1"]
    case: ValidationApiRequest            # full case validated upstream
    geometry: DoublePipeGeometrySpec      # explicit geometry DTO
    tube_in_hot: bool = True
    flow_arrangement: Literal["counterflow", "parallel"]
    tube_boundary_condition: Literal["constant_wall_temperature", "inner_wall_heated"]
    annulus_boundary_condition: Literal["inner_wall_heated", "constant_wall_temperature"]
    solver_params: SolverParamsSpec | None = None
    provider_ref: str                     # key into configured provider registry


class DoublePipeGeometrySpec(StrictBaseModel):
    inner_tube_inner_diameter: Length
    inner_tube_outer_diameter: Length
    outer_pipe_inner_diameter: Length
    effective_length: Length
    wall_thermal_conductivity: ThermalConductivitySpec
    inner_surface_roughness: Length
    annulus_surface_roughness: Length
    # NOTE: fouling fields intentionally NOT present.
    # Fouling authority is solely from stream-level FoulingResistanceSpec
    # via case.hot_stream.fouling + case.cold_stream.fouling (§3.3.2).


class ThermalConductivitySpec(StrictBaseModel):
    """Unit-bearing thermal conductivity."""
    value: float = Field(allow_inf_nan=False, gt=0)
    unit: Literal["W/(m*K)"]


class SolverParamsSpec(StrictBaseModel):
    absolute_residual_w: Power = Field(default=Power(value=1e-6, unit="W"))
    relative_residual_fraction: float = Field(default=1e-6, ge=0)
    bracket_temperature_tolerance_k: TemperatureDifference = Field(
        default=TemperatureDifference(value=1e-6, unit="delta_degC")
    )
    max_iterations: int = Field(default=100, ge=1)
```

#### 3.3.1 Projection to domain models

| RatingApiRequest field | Target |
|---|---|
| `case` → `ValidationApiRequest` | `DesignCase` (via §3.2.1 projection) |
| `geometry` → `DoublePipeGeometrySpec` | `DoublePipeGeometry` (extract `.si_value` from each `Length`, `.value` from `ThermalConductivitySpec`) |
| `solver_params` → `SolverParamsSpec` | `SolverParams` (extract `.si_value` from `Power` and `TemperatureDifference`) |

#### 3.3.2 Fouling authority

**Single-authority rule:** The public `DoublePipeGeometrySpec` does NOT accept fouling fields. Fouling comes solely from `case.hot_stream.fouling` and `case.cold_stream.fouling` (both `FoulingResistanceSpec` with provenance). Any user-submitted fouling value on the geometry DTO is rejected at 422. The projection layer derives `DoublePipeGeometry` fouling fields automatically from stream values during orchestration:

```
hot_fouling = case.hot_stream.fouling_resistance.value.si_value
cold_fouling = case.cold_stream.fouling_resistance.value.si_value
inner_fouling = hot_fouling if tube_in_hot else cold_fouling
outer_fouling = cold_fouling if tube_in_hot else hot_fouling
```

### 3.4 `SizingApiRequest`

```python
class SizingApiRequest(StrictBaseModel):
    api_schema_version: Literal["1"]
    case: ValidationApiRequest

    # Catalog — full immutable snapshots
    catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...]

    # Length bounds — unit-bearing
    minimum_effective_length: Length | None = None
    maximum_effective_length: Length | None = None
    request_raw_combination_cap: int | None = None

    # Sizing constraints
    tube_boundary_condition: Literal["constant_wall_temperature", "inner_wall_heated"]
    annulus_boundary_condition: Literal["inner_wall_heated", "constant_wall_temperature"]
    flow_arrangement: Literal["counterflow", "parallel"]
    tube_in_hot: bool = True

    # Duty — unit-bearing
    required_duty: Power
    duty_absolute_tolerance: Power = Field(default=Power(value=0, unit="W"))
    duty_relative_tolerance: Dimensionless = Field(default=Dimensionless(value=0, unit=""))

    # Optimization
    optimization_objective: OptimizationObjective
    requested_top_n: int = Field(ge=1)

    # Provider
    expected_provider_identity: ExpectedProviderIdentity

    # Solver
    solver_params: SolverParamsSpec | None = None

    # Domain context (optional)
    design_case_revision_id: UUID | None = None
    calculation_run_id: UUID | None = None

    # Software metadata
    rating_software_version: str = "0.1.0"
    execution_context_policy_version: str = ""
```

**All dimensional fields use typed `Quantity` subclasses.** No bare `float`:
- `minimum_effective_length`, `maximum_effective_length` → `Length | None`
- `required_duty` → `Power`
- `duty_absolute_tolerance` → `Power`
- `duty_relative_tolerance` → `Dimensionless`

#### 3.4.1 Projection to `SizingRequest` + `SizingRequestIdentity`

The orchestration layer extracts `.si_value` from each Quantity:

```
SizingApiRequest
→ SizingRequest(
    catalogs=catalogs,
    minimum_effective_length_m=minimum_effective_length.si_value if set else None,
    maximum_effective_length_m=maximum_effective_length.si_value if set else None,
    request_raw_combination_cap=request_raw_combination_cap,
)
→ build_sizing_request_identity(
    request,
    hot_fluid_name=case.hot_stream.fluid.name,
    ...
    required_duty_w=required_duty.si_value,
    duty_absolute_tolerance_w=duty_absolute_tolerance.si_value,
    duty_relative_tolerance=duty_relative_tolerance.si_value,
    ...
)
```

---

## 4. Application-Service Orchestration Contract

### 4.1 Sizing Orchestration

The HTTP sizing handler MUST execute the following frozen chain using real TASK-009 production types:

```
SizingApiRequest
│
├─ 1. validate_public_request() → rejects at 422
├─ 2. canonicalize_request() → compute request_digest
├─ 3. project_to_domain() → SizingRequest + SizingRequestIdentity
├─ 4. sizing_gate() → PassedSizingGate                 [TASK-009 Phase 1]
├─ 5. candidate_materialization() → MaterializedCandidateSet   [TASK-009 Phase 1]
├─ 6. phase2_candidate_evaluation() → tuple[CandidateEvaluationRecord, ...]
├─ 7. phase3_evaluation_input() → Phase3EvaluationInput
├─ 8. phase3_classification() → per-candidate
├─ 9. deterministic_ranking()
├─ 10. top_n_projection()
├─ 11. build_optimization_result() → + authoritative verification + provenance
├─ 12. build_sizing_run_artifacts()                    [§9]
├─ 13. build_sizing_run_envelope()                     [§6]
└─ 14. complete run in repository                      [§7]
```

### 4.2 Rating Orchestration

```
RatingApiRequest
│
├─ 1. validate + canonicalize
├─ 2. project_to_domain() → DesignCase + DoublePipeGeometry + SolverParams
├─ 3. DoublePipeRatingService.rate()
├─ 4. build_rating_run_artifacts()
├─ 5. build_rating_run_envelope()
└─ 6. complete run in repository
```

### 4.3 Forbidden Paths

- **`DoublePipeService.size()`** — EXISTS at `src/hexagent/exchangers/double_pipe/service.py:140` with `assumed_u = 500.0`. TASK-010 MUST NOT call it.
- Any assumed-U, placeholder-area, or starter-result logic.
- Route handler directly assembling `OptimizationResult` fields.
- Bypassing TASK-009 artifact construction or authoritative verification.

---

## 5. API Endpoints

| Method | Path | operation_id | Request DTO | Response Envelope |
|---|---|---|---|---|
| POST | `/v1/cases/validate` | `validateCase` | `ValidationApiRequest` | `ValidationRunEnvelope` |
| POST | `/v1/double-pipe/rating` | `rateDoublePipe` | `RatingApiRequest` | `RatingRunEnvelope` |
| POST | `/v1/double-pipe/sizing` | `sizeDoublePipe` | `SizingApiRequest` | `SizingRunEnvelope` |
| GET | `/v1/runs/{run_id}` | `getRun` | — | `AnyRunEnvelope` |
| GET | `/v1/runs/{run_id}/report.html` | `getRunReportHtml` | — | `text/html` |
| GET | `/v1/runs/{run_id}/report.pdf` | `getRunReportPdf` | — | `application/pdf` or 501 |

- `POST /v1/cases/validate`: `200` (accepted); `422` (schema/unit/constraint). No idempotency. `validation_receipt_hash`.
- `POST /v1/double-pipe/rating`: `SUCCEEDED`/`BLOCKED`/`FAILED` → `200`; unexpected → `500`. Idempotency required.
- `POST /v1/double-pipe/sizing`: `COMPLETE`/`PARTIAL` → `200`; input rejection → `422`. Idempotency required.
- `GET /v1/runs/{run_id}`: `200` (found); `404` (unknown).
- `GET /v1/runs/{run_id}/report.html`: `200`; `404`; `500` (unexpected rendering failure).
- `GET /v1/runs/{run_id}/report.pdf`: `application/pdf` or `501` (no adapter).

---

## 6. Discriminated Run Envelopes

### 6.1 Union Type

```python
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
    request_digest: str
    result_kind: Literal["validation"]
    result: None                                          # MUST be None
    validation_receipt_hash: str
    report_links: ReportLinks | None = None
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
    result: RatingResult
    result_hash: str
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None
    provenance: ProvenanceGraph
    provenance_digest: str
    artifact_bundle_digest: str
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
        if self.provenance != self.result.provenance_graph:
            raise ValueError("provenance != result.provenance_graph")
        recomputed = self.provenance.compute_hash()
        if self.provenance_digest != recomputed:
            raise ValueError("provenance_digest mismatch")
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
    result: OptimizationResult
    result_hash: str
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None
    provenance: ProvenanceGraph
    provenance_digest: str
    artifact_bundle: SizingRunArtifacts | None    # None only if stored in repository
    artifact_bundle_digest: str
    report_links: ReportLinks

    @model_validator(mode="after")
    def verify_projection(self) -> typing.Self:
        if self.result_hash != self.result.result_hash:
            raise ValueError("result_hash != result.result_hash")

        if self.artifact_bundle is not None:
            verify_sizing_artifact_bundle(self.artifact_bundle)
            recomputed_digest = compute_artifact_bundle_digest(self.artifact_bundle)
            if recomputed_digest != self.artifact_bundle_digest:
                raise ValueError("artifact_bundle_digest mismatch")
            if self.result != self.artifact_bundle.optimization_result:
                raise ValueError("result != artifact_bundle.optimization_result")

            expected_warnings = reconstruct_sizing_warnings(self.artifact_bundle)
            expected_blockers = reconstruct_sizing_blockers(self.artifact_bundle)
            expected_failure = reconstruct_sizing_failure(self.artifact_bundle)
            if self.warnings != expected_warnings:
                raise ValueError("warning projection mismatch")
            if self.blockers != expected_blockers:
                raise ValueError("blocker projection mismatch")
            if self.failure != expected_failure:
                raise ValueError("failure projection mismatch")
        else:
            raise ValueError("artifact_bundle is required for envelope verification")

        recomputed_prov = self.provenance.compute_hash()
        if self.provenance_digest != recomputed_prov:
            raise ValueError("provenance_digest mismatch")
        if self.provenance_digest != self.result.provenance_digest:
            raise ValueError("provenance_digest != result.provenance_digest")
        return self
```

**`artifact_bundle` is the authoritative source for all projected messages.** Reconstruction functions:

```python
def reconstruct_sizing_warnings(bundle: SizingRunArtifacts) -> tuple[EngineeringMessage, ...]:
    ordered_digests = bundle.optimization_result.ordered_phase3_warning_digests
    return _resolve_digests_to_messages(ordered_digests, bundle.warning_binding_tuples,
                                         bundle.warning_descriptor_tuples)

def reconstruct_sizing_blockers(bundle: SizingRunArtifacts) -> tuple[EngineeringMessage, ...]:
    ordered_digests = bundle.optimization_result.ordered_phase3_blocker_digests
    return _resolve_digests_to_messages(ordered_digests, bundle.blocker_binding_tuples,
                                         bundle.blocker_descriptor_tuples)

def reconstruct_sizing_failure(bundle: SizingRunArtifacts) -> RunFailure | None:
    return derive_failure_from_dispositions(bundle.dispositions)
```

No envelope is valid without passing this validator. Build-time reconstruction is the single normative path.

### 6.5 Cross-Field Invariants

| Invariant | Enforcement |
|---|---|
| Rating envelope MUST NOT carry `OptimizationResult` | Typed `result` field |
| Sizing envelope MUST NOT carry `RatingResult` | Typed `result` field |
| Validation `result` MUST be `None` | Explicit `None` type |
| `result_hash` == `result.result_hash` | `@model_validator` |
| `warnings`/`blockers`/`failure` == authority projection | Bundle-based reconstruction |
| `provenance` == `result.provenance_graph` (rating) | `@model_validator` |
| `provenance_digest` == graph recomputation | `@model_validator` |

---

## 7. Idempotency Contract

### 7.1 Request Header

```
Idempotency-Key: <1-128 printable ASCII, trimmed, no control characters>
```

### 7.2 Identity Namespace

```python
def compute_idempotency_namespace_digest(
    *, api_schema_version: str, operation_id: str, idempotency_key: str,
) -> str:
    return sha256_digest({
        "api_schema_version": api_schema_version,
        "operation_id": operation_id,
        "idempotency_key_digest": sha256_digest(idempotency_key),
    })
```

### 7.3 RunRecord State Machine

```python
class RunState(StrEnum):
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    STALE = "stale"


class RunRecord(StrictBaseModel):
    run_id: UUID
    namespace_digest: str
    request_digest: str
    operation: str
    state: RunState
    record_version: int                  # CAS token — incremented on every mutation
    owner_token: str
    claimed_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    heartbeat_at: datetime | None = None
    lease_expires_at: datetime | None = None
    envelope: AnyRunEnvelope | None = None
    artifact_bundle: RatingRunArtifacts | SizingRunArtifacts | None = None
    failure: RunFailure | None = None
```

**State transitions:**

| From | To | Condition |
|---|---|---|
| (new) | CLAIMED | `claim()` succeeds |
| CLAIMED | RUNNING | `start()` with matching owner_token + expected_version |
| RUNNING | COMPLETE | `complete()` with matching owner_token + expected_version |
| RUNNING | FAILED | `fail()` with matching owner_token + expected_version |
| CLAIMED | STALE | `lease_expires_at` passed, no heartbeat |
| RUNNING | STALE | `lease_expires_at` passed, no heartbeat |
| STALE | CLAIMED | New `claim()` with `takeover=True` |

### 7.4 Run Repository Protocol

```python
LEASE_DURATION: timedelta = timedelta(seconds=30)
HEARTBEAT_INTERVAL: timedelta = timedelta(seconds=10)


class RunRepository(Protocol):
    def claim(
        self, *, namespace_digest: str, request_digest: str, operation: str,
        takeover: bool = False,
    ) -> tuple[RunRecord, bool]:
        """Atomically claim a namespace.

        Returns (record, is_new).
        - New namespace → CLAIMED with owner_token (is_new=True), record_version=1.
        - Same namespace + same request_digest + COMPLETE → existing (is_new=False).
        - Same namespace + same request_digest + FAILED → existing (is_new=False).
        - Same namespace + same request_digest + CLAIMED/RUNNING → existing.
        - Same namespace + different request_digest → IdempotencyConflict (409).
        - STALE + takeover=True → CLAIMED with new owner_token.
        """
        ...

    def start(
        self, *, owner_token: str, expected_version: int,
    ) -> RunRecord:
        """Transition CLAIMED → RUNNING. Validates owner_token + expected_version.
        Sets started_at, heartbeat_at, lease_expires_at."""
        ...

    def heartbeat(
        self, *, owner_token: str, expected_version: int,
    ) -> RunRecord:
        """Refresh heartbeat_at and lease_expires_at. CAS on expected_version."""
        ...

    def complete(
        self, *, owner_token: str, expected_version: int,
        envelope: AnyRunEnvelope,
        artifact_bundle: RatingRunArtifacts | SizingRunArtifacts,
    ) -> RunRecord:
        """Transition RUNNING → COMPLETE. Records envelope + bundle.
        Validates: record.request_digest == envelope.request_digest,
        record.operation == envelope.operation,
        bundle.optimization_result == envelope.result (for sizing),
        bundle digest == envelope.artifact_bundle_digest.
        Increments record_version."""
        ...

    def fail(
        self, *, owner_token: str, expected_version: int, failure: RunFailure,
    ) -> RunRecord:
        """Transition RUNNING → FAILED. Records failure. Increments record_version."""
        ...

    def get_by_run_id(self, run_id: UUID) -> RunRecord | None: ...
    def get_by_namespace(self, namespace_digest: str) -> RunRecord | None: ...
```

### 7.5 Behavior Matrix

| Condition | Outcome |
|---|---|
| Same namespace + same request_digest, COMPLETE | Return stored record; no re-execution |
| Same namespace + same request_digest, FAILED | Return stored record |
| Same namespace + same request_digest, CLAIMED/RUNNING | Return stored record; caller polls or waits |
| Same namespace + different request_digest | 409 IDEMPOTENCY_CONFLICT |
| STALE record + takeover claim | New CLAIMED with new owner_token; old owner_token invalidated |
| Old owner completes after takeover | Rejected: owner_token or expected_version mismatch |
| CAS version mismatch on any mutation | Rejected |

### 7.6 Concurrency Contract

- `claim()` is serialized by `threading.Lock`.
- Engineering execution (`start()` → `complete()`/`fail()`) occurs OUTSIDE the lock.
- `heartbeat()` is called periodically by the execution owner.
- CAS via `expected_version` + `record_version` prevents stale writes.
- After takeover, old owner_token is invalid; all mutations from old owner fail.

### 7.7 Scope Limitations

- Process-local only; not persistent; lost on restart.
- Not suitable for multi-process or distributed deployments.
- Report retrieval reads the stored `artifact_bundle`, not just `artifact_bundle_digest`.

---

## 8. Canonical Request Algorithm

### 8.1 Design Decision: Quantity values as JSON strings

All canonical scalar values are encoded as **JSON strings**, not JSON numbers, to avoid binary float serialization differences.

```python
def canonical_decimal_string(d: Decimal) -> str:
    """Normalize Decimal: strip trailing zeros, no scientific unless needed.
    -0 → "0". 1.5000 → "1.5". 1e-6 → "0.000001"."""
    ...

def canonical_quantity_payload(q: Quantity) -> dict[str, str]:
    """Quantity → {"value": "<canonical SI string>", "unit": "<SI symbol>"}

    Conversion:
    1. Input Quantity value → Decimal.
    2. Apply unit conversion factor as Decimal.
    3. Round with ROUND_HALF_EVEN.
    4. Quantize to 15 significant digits.
    5. Strip trailing zeros via normalize().
    6. Reject NaN, Inf, -Inf, negative zero.
    7. Output as normalized Decimal string.
    """
    ...

def canonical_api_request_context(request: StrictBaseModel) -> dict[str, object]:
    """Produce a deterministic canonical payload dict.

    Preconditions:
    1. Request has passed strict schema validation.
    2. All Quantity fields resolved to their SI canonical form.
    3. Provider identity fully resolved.
    4. Catalog snapshots fully resolved.
    """
```

### 8.2 Canonicalization Rules

| Rule | Behavior |
|---|---|
| Dict key order | Recursively sorted by key |
| `None` values | Retained as JSON null |
| Pydantic aliases | Not used — field names only |
| Pydantic defaults | Explicitly expanded |
| `Enum` | `.value` as string |
| `UUID` | Canonical 36-char string |
| `tuple` / `list` | JSON array |
| `Decimal` | `canonical_decimal_string()` → JSON string, e.g. `"1.5"` |
| `float` | Convert to `Decimal(repr(f))`, then `canonical_decimal_string()` |
| `int` | JSON number |
| `bool` | JSON boolean |
| `Quantity` subtypes | `{"value": "<Decimal string>", "unit": "<SI symbol>"}` |
| Unicode | NFC normalized |
| Catalog identity | Full canonical catalog snapshot payload → content hash |
| Provider config | `name` + `version` + `git_revision` + `reference_state_policy` + `configuration_fingerprint` + `cache_policy_version` |
| Negative zero | Forbidden (rejected at validation) |
| NaN / Inf | Forbidden (rejected at validation) |

### 8.3 Test Vectors

| Input | Canonical form |
|---|---|
| `1` (int) | `1` |
| `1.0` (Decimal) | `"1"` |
| `1.5000` (Decimal) | `"1.5"` |
| `0` (int) | `0` |
| `-0` (Decimal) | REJECTED |
| `0.000001` (Decimal) | `"0.000001"` |
| `1000000` (int) | `1000000` |
| `TemperatureDifference(value=5, unit="delta_degC")` | `{"value": "5", "unit": "delta_degC"}` |
| `AbsolutePressure(value=101325, unit="Pa")` | `{"value": "101325", "unit": "Pa"}` |
| `Length(value=2.5, unit="m")` | `{"value": "2.5", "unit": "m"}` |

### 8.4 Single Authority

All idempotency identity, `request_digest`, and report input snapshot MUST call `compute_api_request_digest()`.

---

## 9. Authoritative Artifact Bundles

### 9.1 `RatingRunArtifacts`

```python
class RatingRunArtifacts(StrictBaseModel):
    canonical_request_snapshot: dict[str, object]          # from canonical_api_request_context
    request_identity: RatingRequestIdentity                # TASK-008 production type
    geometry_snapshot: DoublePipeGeometry
    solver_settings: SolverParams
    provider_identity: ProviderIdentitySnapshot
    result: RatingResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str

    @model_validator(mode="after")
    def _validate_bundle_hash(self) -> typing.Self:
        recomputed = compute_rating_artifact_bundle_hash(self)
        if self.artifact_bundle_digest != recomputed:
            raise ValueError("artifact_bundle_digest mismatch")
        return self
```

### 9.2 `SizingRunArtifacts`

```python
class SizingRunArtifacts(StrictBaseModel):
    canonical_request_snapshot: dict[str, object]
    sizing_request: SizingRequest                              # REQUIRED — full production model
    sizing_request_identity: SizingRequestIdentity
    passed_gate: PassedSizingGate
    materialization_result: MaterializedCandidateSet
    evaluation_input: Phase3EvaluationInput
    phase3_authoritative_artifacts: Phase3AuthoritativeArtifacts  # embedded production type
    dispositions: tuple[CandidateDispositionRecord, ...]
    ranked_records: tuple[RankedCandidateRecord, ...]
    top_n_records: tuple[RankedCandidateRecord, ...]
    optimization_result: OptimizationResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str
```

**`Phase3AuthoritativeArtifacts` is directly embedded** — no hand-copied field list. It carries all production-required artifacts: evaluation records, identity snapshots, complete snapshots, source record descriptors, source bindings, classification inputs, preparation results, warning/blocker descriptor tuples, warning/blocker binding tuples, evidence/source/phase3 failure bindings, and preparatory auth artifacts.

`SizingRequest` is a REQUIRED field — not only `SizingRequestIdentity`.

### 9.3 Verifier Replay

```python
def verify_rating_artifact_bundle(bundle: RatingRunArtifacts) -> None:
    bundle.result.__pydantic_validate_model__()
    verify_provenance_or_raise(bundle.provenance_graph, result=bundle.result)
    recompute_and_check_bundle_digest(bundle)

def verify_sizing_artifact_bundle(bundle: SizingRunArtifacts) -> None:
    # 1) SizingRequest structural validation
    bundle.sizing_request.__class__.model_validate(bundle.sizing_request.model_dump())
    # 2) SizingRequestIdentity structural validation
    bundle.sizing_request_identity.__class__.model_validate(
        bundle.sizing_request_identity.model_dump())
    # 3) PassedSizingGate semantic validation
    #    PassedSizingGate.__init__ validates status, counts, per_option_records
    # 4) MaterializedCandidateSet structural validation
    # 5) Phase3EvaluationInput.verify_or_raise(artifacts=bundle.phase3_authoritative_artifacts)
    bundle.evaluation_input.verify_or_raise(
        artifacts=bundle.phase3_authoritative_artifacts)
    # 6) Phase3AuthoritativeArtifacts.verify_or_raise()
    bundle.phase3_authoritative_artifacts.verify_or_raise()
    # 7) verify_phase3_result_semantics_or_raise(
    #        result=bundle.optimization_result,
    #        artifacts=bundle.phase3_authoritative_artifacts,
    #        evaluation_input=bundle.evaluation_input)
    # 8) verify_provenance_or_raise(bundle.provenance_graph, ...)
    # 9) Recompute artifact_bundle_digest and cross-check
```

Each verifier call specifies its real parameter sources. No "essentially a superset" language.

### 9.4 Bundle Digest Self-Hash Exclusion

`artifact_bundle_digest` is computed over all bundle fields EXCEPT `artifact_bundle_digest` itself.

---

## 10. Report Model

### 10.1 Discriminated Report Artifact

```python
class ReportSourceDocument(StrEnum):
    RUN_ENVELOPE = "run_envelope"
    ARTIFACT_BUNDLE = "artifact_bundle"
    CANONICAL_REQUEST = "canonical_request"


class ReportArtifactKind(StrEnum):
    PRESENT = "present"
    NOT_AVAILABLE = "not_available"
    NOT_IMPLEMENTED = "not_implemented"
    OUT_OF_SCOPE = "out_of_scope"


class PresentReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.PRESENT]
    artifact_id: ReportArtifactId                       # typed enum, not bare str
    source_document: ReportSourceDocument
    source_document_digest: str
    source_json_pointer: str                            # RFC 6901
    authority_digest: str
    canonical_raw_value: str
    source_unit: str | None
    display_unit: str | None
    formatter_id: str
    formatter_version: str
    rounding_mode: str
    formatted_display_value: str


class UnavailableReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.NOT_AVAILABLE]
    artifact_id: ReportArtifactId
    reason_code: str
    capability: str


class NotImplementedReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.NOT_IMPLEMENTED]
    artifact_id: ReportArtifactId
    capability: str


class OutOfScopeReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.OUT_OF_SCOPE]
    artifact_id: ReportArtifactId
    capability: str


ReportArtifact = Annotated[
    PresentReportArtifact | UnavailableReportArtifact
    | NotImplementedReportArtifact | OutOfScopeReportArtifact,
    Discriminator("kind"),
]
```

All artifact union members use `artifact_id: ReportArtifactId` — no bare `str`.

### 10.2 Report Model and Hashing

```python
class ReportSectionStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class ReportSection(StrictBaseModel):
    section_id: ReportSectionId
    status: ReportSectionStatus
    artifacts: tuple[ReportArtifact, ...]


class ReportInstanceIdentity(StrictBaseModel):
    report_schema_version: Literal["1"]
    report_content_hash: str
    run_id: UUID
    request_digest: str
    source_run_envelope_digest: str
    source_domain_result_hash: str
    source_artifact_bundle_digest: str
    template_id: str
    template_version: str
    template_definition_hash: str
    formatter_registry_version: str


class DoublePipeReportModel(StrictBaseModel):
    report_schema_version: Literal["1"]
    sections: tuple[ReportSection, ...]
    report_instance_identity: ReportInstanceIdentity
    report_content_hash: str
    report_instance_hash: str

    @model_validator(mode="after")
    def _validate_hashes(self) -> typing.Self:
        # Cross-binding
        if self.report_instance_identity.report_content_hash != self.report_content_hash:
            raise ValueError("report_instance_identity.report_content_hash != report_content_hash")
        if self.report_instance_identity.report_schema_version != self.report_schema_version:
            raise ValueError("report_schema_version mismatch in instance identity")

        # Content hash
        expected_content = compute_report_content_hash(self.sections, self.report_schema_version)
        if self.report_content_hash != expected_content:
            raise ValueError("report_content_hash mismatch")

        # Instance hash
        expected_instance = sha256_digest(self.report_instance_identity)
        if self.report_instance_hash != expected_instance:
            raise ValueError("report_instance_hash mismatch")

        # Section uniqueness
        seen: set[str] = set()
        for s in self.sections:
            if s.section_id in seen:
                raise ValueError(f"duplicate section_id: {s.section_id}")
            seen.add(s.section_id)

        # Mandatory sections
        present = {s.section_id for s in self.sections}
        missing = set(MANDATORY_SECTIONS) - present
        if missing:
            raise ValueError(f"missing mandatory sections: {missing}")

        # Section order
        ordered = [s.section_id for s in self.sections]
        expected_order = [sid for sid in SECTION_ORDER if sid in ordered or sid in MANDATORY_SECTIONS]
        actual_order = [sid for sid in ordered if sid in expected_order]
        if actual_order != [sid for sid in expected_order if sid in ordered]:
            raise ValueError("section order violation")

        # Artifact ID uniqueness within section
        for s in self.sections:
            aids = [a.artifact_id for a in s.artifacts]
            if len(aids) != len(set(aids)):
                raise ValueError(f"duplicate artifact_id in section {s.section_id}")

        # PRESENT artifact source resolution
        for s in self.sections:
            for a in s.artifacts:
                if isinstance(a, PresentReportArtifact):
                    if not a.source_json_pointer:
                        raise ValueError(f"PRESENT artifact {a.artifact_id} missing pointer")

        return self
```

### 10.3 Section/Status Matrix

| Section | SUCCEEDED (rating) | BLOCKED (rating) | FAILED (rating) | COMPLETE (sizing) | PARTIAL (sizing) |
|---|---|---|---|---|---|
| `status_banner` | COMPLETE | BLOCKED | BLOCKED | COMPLETE | PARTIAL |
| `run_identity` | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE |
| `input_summary` | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE |
| `geometry` | COMPLETE | NOT_APPLICABLE | NOT_APPLICABLE | COMPLETE | PARTIAL |
| `heat_balance` | COMPLETE | NOT_APPLICABLE | PARTIAL | NOT_APPLICABLE | NOT_APPLICABLE |
| `thermal_performance` | COMPLETE | NOT_APPLICABLE | PARTIAL | NOT_APPLICABLE | NOT_APPLICABLE |
| `sizing_ranking` | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | COMPLETE | PARTIAL |
| `top_ranked_candidates` | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | COMPLETE | PARTIAL |
| `warnings` | COMPLETE | PARTIAL | PARTIAL | COMPLETE | COMPLETE |
| `blockers` | EMPTY | COMPLETE | PARTIAL | EMPTY | PARTIAL |
| `failure_details` | NOT_APPLICABLE | NOT_APPLICABLE | COMPLETE | NOT_APPLICABLE | NOT_APPLICABLE |
| `provenance` | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE |
| `integrity` | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE |

### 10.4 Report Section Enum and Ordering

```python
class ReportSectionId(StrEnum):
    STATUS_BANNER = "status_banner"
    RUN_IDENTITY = "run_identity"
    INPUT_SUMMARY = "input_summary"
    GEOMETRY = "geometry"
    HEAT_BALANCE = "heat_balance"
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

- Sections present MUST be in exact SECTION_ORDER sequence. No duplicates. Optional sections preserve relative order when present.

#### 10.4.1 Artifact ID Enum

```python
class ReportArtifactId(StrEnum):
    STATUS = "status"
    TERMINATION_STATUS = "termination_status"
    RUN_ID = "run_id"
    API_VERSION = "api_version"
    OPERATION = "operation"
    REQUEST_DIGEST = "request_digest"
    CASE_NAME = "case_name"
    HOT_FLUID = "hot_fluid"
    COLD_FLUID = "cold_fluid"
    HOT_INLET_T = "hot_inlet_t"
    COLD_INLET_T = "cold_inlet_t"
    MASS_FLOWS = "mass_flows"
    DESIGN_PRESSURES = "design_pressures"
    DESIGN_TEMPERATURES = "design_temperatures"
    GEOMETRY_SPEC = "geometry_spec"
    HEAT_DUTY = "heat_duty"
    ENERGY_RESIDUAL = "energy_residual"
    TUBE_HTC = "tube_htc"
    ANNULUS_HTC = "annulus_htc"
    OVERALL_U = "overall_u"
    EFFECTIVENESS = "effectiveness"
    SIZING_RANK = "sizing_rank"
    OPTIMIZATION_OBJECTIVE = "optimization_objective"
    TOP_CANDIDATE_RANK = "top_candidate_rank"
    TOP_CANDIDATE_GEOMETRY = "top_candidate_geometry"
    BLOCKER_MESSAGE = "blocker_message"
    FAILURE_REASON = "failure_reason"
    PROVENANCE_GRAPH = "provenance_graph"
    RESULT_HASH = "result_hash"
    BUNDLE_HASH = "bundle_hash"
    PRESSURE_DROP = "pressure_drop"
    VELOCITY = "velocity"
    MATERIALS = "materials"
    COST = "cost"
    MECHANICAL = "mechanical"
    PROCUREMENT = "procurement"


MANDATORY_ARTIFACT_IDS: frozenset[ReportArtifactId] = frozenset({
    ReportArtifactId.STATUS,
    ReportArtifactId.RUN_ID,
    ReportArtifactId.REQUEST_DIGEST,
    ReportArtifactId.RESULT_HASH,
    ReportArtifactId.BUNDLE_HASH,
})
```

### 10.5 Pre-Render Verification Chain

1. Domain result verification
2. Provenance verification (independent authority)
3. Artifact bundle verification (§9.3)
4. Envelope projection verification (warnings/blockers/failure parity)
5. Report model verification (sections, artifacts, pointers, status consistency)
6. Template identity verification (template_definition_hash matches)
7. Any failure → render fails closed (no partial output)

---

## 11. Status Banner

| Envelope | Source Field |
|---|---|
| `RatingRunEnvelope` | `result.status` |
| `SizingRunEnvelope` | `result.termination_status` |

---

## 12. Top-Ranked Candidates

Section name: `top_ranked_candidates`. TASK-009 authorises deterministic ranking only — NOT final selection.

**Restricted words (user-facing labels only):** `selected`, `recommended`, `approved`, `procurement-ready`. Provenance appendix may preserve upstream relation values verbatim.

---

## 13. Status and Risk Display

- Every HTML page displays: `PRELIMINARY` / `NOT FOR PROCUREMENT` / `NOT FOR CONSTRUCTION` — in `@media print` header/footer DOM and in normal view.
- Blockers appear above the status banner.
- Not-implemented: `NOT_IMPLEMENTED`. Out-of-scope: `OUT_OF_SCOPE`.

---

## 14. HTML Security Contract

- Autoescape enabled. No user-specified template paths. No external CDN/font/tracking resources.
- User-provided input HTML-escaped. No absolute paths, tracebacks, tokens, environment variables in rendered output.

---

## 15. PDF Boundary

No adapter → `HTTP 501` with structured `ApiError`. No empty PDF, no fake link, no degraded fallback. Physical per-page verification deferred until PDF adapter is selected.

---

## 16. Determinism Contract

- **Engineering content:** Same inputs → same `report_content_hash`.
- **Run instance:** Same `run_id` → identical envelope + report.
- **HTML byte:** Same canonical request + template + formatter → byte-identical HTML (test compares `bytes`).
- Excluded: timestamp, random run_id, PID, host, trace, temp paths.

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
    error_message: str                              # no traceback/path/token
    request_digest: str | None
    details: tuple[ErrorDetail, ...]
    MAX_DISPLAYED_VALUE_LENGTH: ClassVar[int] = 200


class ErrorDetail(StrictBaseModel):
    field: str | None
    reason: str
    value: str | None                               # truncated
```

- 404 → `RUN_NOT_FOUND`, 409 → `IDEMPOTENCY_CONFLICT`, 422 → `VALIDATION_FAILED`, 500 → `INTERNAL_ERROR`, 501 → `PDF_NOT_AVAILABLE`.

---

## 18. Test Contract

| # | Test | Outcome |
|---|---|---|
| T1 | `operation_id` values unique and stable | 6 unique IDs |
| T2 | Public request DTO JSON Schema exportable | Valid JSON Schema |
| T3 | Dimensional bare `float` in public request (e.g. `minimum_terminal_delta_t: 5.0` without unit) → `422` | Quantity validation |
| T3b | Sizing bare `float` for `required_duty`, `minimum_effective_length` → `422` | Quantity validation |
| T3c | Geometry DTO with `inner_fouling_resistance` → `422` (field not allowed) | Single-authority enforcement |
| T4 | Invalid unit string → `422` | Unit enum validation |
| T5 | Unknown field → `422` | `extra="forbid"` |
| T6–T7 | Validation receipt hash determinism / discriminability | Hash equality / inequality |
| T8–T9 | Canonical request key-order independence / value sensitivity | Digest equality / inequality |
| T9b | Canonical Quantity vectors: `Length(value=2.5, unit="m")` → `{"value":"2.5","unit":"m"}` | Decimal string output |
| T9c | Canonical `-0` → REJECTED | Negative zero rejected |
| T9d | Canonical `Decimal("1.5000")` → `"1.5"` | Trailing zero stripped |
| T9e | Canonical `TemperatureDifference(5, "delta_degC")` → `{"value":"5","unit":"delta_degC"}` | Unit preserved |
| T10–T12 | Envelope type enforcement (RatingResult only, OptimizationResult only, result=None) | Type / cross-field |
| T13 | Envelope `result_hash` mismatch → rejected | Cross-field |
| T14–T14e | Rating envelope warning/blocker/failure/provenance mismatch; sizing warning/blocker reconstruction, failure authority, provenance parity | All cross-field |
| T14f | Sizing envelope warning mismatch from bundle → rejected | Warning parity |
| T14g | Sizing envelope blocker mismatch from bundle → rejected | Blocker parity |
| T14h | Sizing envelope failure mismatch from bundle → rejected | Failure parity |
| T14i | Sizing envelope bundle digest mismatch → rejected | Digest parity |
| T15–T18 | Idempotency: same-key replay, collision, cross-operation isolation, concurrent single execution | Various outcomes |
| T18b | RUNNING same-key caller behavior (existing record returned) | Wait/replay |
| T18c | Stale claim takeover succeeds | New owner_token |
| T18d | Old owner completion after takeover → rejected (CAS version mismatch) | CAS enforcement |
| T18e | CAS version mismatch on `start()` or `complete()` → rejected | CAS enforcement |
| T19–T22 | BLOCKED→200, 404, 500 structured error, 501 no adapter | Status code contract |
| T23–T24 | Artifact bundle replay verification + digest cross-check | Verifier replay |
| T24b | Bundle missing `SizingRequest` → rejected | Required field enforcement |
| T25 | `PresentReportArtifact` RFC 6901 pointer resolution | Source document + pointer |
| T26–T27 | PRESENT missing pointer → rejected; NOT_IMPLEMENTED with source → rejected | Invariant |
| T28–T30 | Duplicate section, missing mandatory section, wrong order → rejected | Section contract |
| T30b | Invalid section/status combination → rejected | Section/status matrix |
| T30c | `artifact_id` not in `ReportArtifactId` enum → rejected | Typed enforcement |
| T31–T34 | Tampered `report_content_hash`, source envelope digest, bundle digest, template hash → rejected | Fail-closed |
| T34b | `report_instance_identity.report_content_hash != report_content_hash` → rejected | Cross-binding |
| T35–T37 | Blocker top-banner, print-header DOM, screen-view disclaimer | HTML structure |
| T38–T39 | HTML escaping, no path/traceback/token leakage | Security |
| T40–T41 | NOT_IMPLEMENTED / OUT_OF_SCOPE display | String search |
| T42 | User-facing labels no "selected"/"recommended"; provenance may preserve | Section-specific |
| T43 | Same canonical request → byte-identical HTML | `bytes` comparison |
| T44 | Same stored run → identical report | Determinism |
| T45 | `DoublePipeService.size()` monkeypatched to raise → TASK-010 path succeeds | Trap proof |
| T46–T47 | Python 3.11/3.12 full suite | Exit 0 |
| T48–T52 | DTO → DesignCase / DoublePipeGeometry / SolverParams / SizingRequest / SizingRequestIdentity exact projection | Field parity |
| T53 | RunRepository: save envelope + artifact bundle → generate report | Full replay |
| T54 | All upstream hash pins complete and correctly typed (40-hex SHA-1, 64-hex SHA-256) | Static audit |

---

## 19. Explicit Exclusions

- **This docs-only PR** excludes all implementation.
- **TASK-010 implementation** (when authorized) includes FastAPI, DTOs, services, handlers, OpenAPI, repository, HTML builder, HTML renderer, endpoints, tests.
- **TASK-010 permanent exclusions**: database, ORM, persistent storage, object storage, auth, rate limiting, specific PDF engine, TASK-011+, C4, pressure drop, velocity constraints, materials, cost, mechanical compliance, procurement conclusions.

---

## 20. Design Status

| Field | Value |
|---|---|
| TASK-010 design | READY_FOR_REVIEW |
| TASK-010 implementation | BLOCKED |
| Frozen Contract SHA | NOT ESTABLISHED |
| Implementation Authorization | NOT GRANTED |
