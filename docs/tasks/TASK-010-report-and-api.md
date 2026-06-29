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

| Artifact | Frozen Commit (40-char SHA) | Schema / Blob Identity |
|---|---|---|
| `TASK-008` RatingResult + provenance + RatingRequestIdentity | `cef3f85402b1696b336347293afc7276bbf67545` (PR #21 merge) | `RatingResult` typed schema: blob `sha256:06ddea1c6143537b1768c6fe2c17541635f45692` |
| `TASK-009` OptimizationResult + Phase3EvaluationInput + Phase3AuthoritativeArtifacts | `8f2ef3014bedfbd1592ab36264af580f50b8cb6d` (PR #24 merge) | `OptimizationResult` blob `sha256:54b0a008…`; `Phase3EvaluationInput` blob `sha256:ea823547…` |
| `DesignCase` / `StreamSpec` / `DesignConstraints` | Pinned at TASK-009 merge commit `8f2ef301…` | `src/hexagent/domain/models.py` blob `sha256:54b0a008…` (includes `FoulingResistanceSpec`) |
| `DoublePipeGeometry` | Pinned at TASK-008 HEAD `cef3f854…` | `src/hexagent/exchangers/double_pipe/geometry.py` blob `sha256:<geo-blob>` |
| `SolverParams` | Pinned at TASK-008 HEAD `cef3f854…` | `src/hexagent/exchangers/double_pipe/solver.py` blob `sha256:<solver-blob>` |
| `SizingRequest` / `SizingRequestIdentity` / `ExpectedProviderIdentity` / `OptimizationObjective` | Pinned at TASK-009 merge `8f2ef301…` | `models.py` blob `sha256:ea823547…`; `context.py` blob `sha256:fa23a2e6…` |
| `Phase3AuthoritativeArtifacts` / `CandidateEvaluationRecord` / verification types | Pinned at TASK-009 merge `8f2ef301…` | `evaluation.py` blob `sha256:b5d3e85b…` |
| Base `main` | `3af8eb85e2a293c2706402dae8ec317a45fed38a` (PR #27 merge) | — |

**All upstream pins use full 40-character commit SHAs with verified blob SHAs from `git show <commit>:<path> | sha256sum`.**

**`api_schema_version` is unified to `Literal["1"]` in all DTOs, envelopes, and the report model. The canonical JSON representation stores it as the string `"1"`. No `"1.0"` variant is used in any public contract.**

### 2.1 Placeholder sizing path

**Forbidden:** `DoublePipeService.size()` — EXISTS in production at `src/hexagent/exchangers/double_pipe/service.py:140`. Contains `assumed_u = 500.0`. TASK-010 routes and application services MUST NOT call it. The API integration test must monkeypatch/trap this exact method and prove no TASK-010 code path invokes it. An import-time check is insufficient (see test T45).

---

## 3. Public API Request DTOs

### 3.1 Design Principle

Public HTTP requests are independent `StrictBaseModel`-based DTOs with explicit unit-bearing `Quantity` subtypes. They project to internal domain models during application-level orchestration.

**No public request uses bare unitless floats for dimensional quantities.**

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

- All dimensional fields use typed `Quantity` subclasses: `Power`, `MassFlow`, `AbsoluteTemperature`, `AbsolutePressure`, `TemperatureDifference`, `FoulingResistance`, `Length`.
- `FoulingResistanceSpec` provides traceable fouling with `FoulingSource` provenance.
- `minimum_terminal_delta_t` is a single authoritative field — the rating/sizing request does not re-declare it.

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

**Rejection rules:**
- `FluidSpec` already has `phase_hint` — if `FluidStreamSpec` re-declares it, the two must agree or the request is rejected.
- `minimum_terminal_delta_t` is consumed during projection; no duplicate field exists in rating/sizing requests.

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
    inner_fouling_resistance: FoulingResistance
    outer_fouling_resistance: FoulingResistance


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

- `thermal_conductivity` is NOT a bare `float` — it uses `ThermalConductivitySpec`.
- Solver tolerances use typed `Quantity` subtypes: `Power`, `TemperatureDifference`.
- `DoublePipeRatingService` overrides geometry fouling from stream values (§3.3.2).

#### 3.3.1 Projection to domain models

| RatingApiRequest field | Target |
|---|---|
| `case` → `ValidationApiRequest` | `DesignCase` (via §3.2.1 projection) |
| `geometry` → `DoublePipeGeometrySpec` | `DoublePipeGeometry` (extract `.si_value` from each `Length`, `.value` from `ThermalConductivitySpec`) |
| `solver_params` → `SolverParamsSpec` | `SolverParams` (extract `.si_value` from `Power` and `TemperatureDifference`, `.value` from `float`) |
| `minimum_terminal_delta_t` | Consumed from `case.minimum_terminal_delta_t.si_value` |

#### 3.3.2 Fouling authority

`DoublePipeRatingService` overrides geometry fouling with stream-level values:
```
hot_fouling = case.hot_stream.fouling_resistance.value.si_value
cold_fouling = case.cold_stream.fouling_resistance.value.si_value
inner_fouling = hot_fouling if tube_in_hot else cold_fouling
outer_fouling = cold_fouling if tube_in_hot else hot_fouling
```
The public `DoublePipeGeometrySpec` fouling values are documentation-only. The canonical fouling values are the stream-level values from `DesignCase`. The DTO MUST accept geometry fouling fields but the actual computation uses stream-level overrides.

### 3.4 `SizingApiRequest`

```python
class SizingApiRequest(StrictBaseModel):
    api_schema_version: Literal["1"]
    case: ValidationApiRequest

    # Catalog — full immutable snapshots, not just string references
    catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...]

    # Length bounds
    minimum_effective_length_m: float | None = None    # SI, positive if set
    maximum_effective_length_m: float | None = None    # SI, positive if set
    request_raw_combination_cap: int | None = None

    # Sizing constraints
    tube_boundary_condition: Literal["constant_wall_temperature", "inner_wall_heated"]
    annulus_boundary_condition: Literal["inner_wall_heated", "constant_wall_temperature"]
    flow_arrangement: Literal["counterflow", "parallel"]
    tube_in_hot: bool = True

    # Duty
    required_duty_w: float                              # W, positive
    duty_absolute_tolerance_w: float = Field(ge=0)
    duty_relative_tolerance: float = Field(ge=0)

    # Optimization
    optimization_objective: OptimizationObjective
    # Values: "minimum_outer_heat_transfer_area" | "minimum_effective_length"
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

- `catalogs` is `tuple[CompleteDoublePipeCatalogSnapshot, ...]` (the concrete TASK-009 catalog model), not a string reference.
- `optimization_objective` uses the production `OptimizationObjective` StrEnum values: `"minimum_outer_heat_transfer_area"` and `"minimum_effective_length"`.
- `expected_provider_identity` is the production `ExpectedProviderIdentity` model.
- No `diameter_bounds` — `SizingRequest` does not support them. If needed, they are a future independent gate design.
- `minimum_terminal_delta_t` is consumed from `case.minimum_terminal_delta_t.si_value` during orchestration.

#### 3.4.1 Projection to `SizingRequest` + `SizingRequestIdentity`

```
SizingApiRequest
→ SizingRequest(catalogs=catalogs, minimum_effective_length_m=..., ...)
→ build_sizing_request_identity(
    request,
    hot_fluid_name=case.hot_stream.fluid.name,
    cold_fluid_name=case.cold_stream.fluid.name,
    hot_fluid_equation_of_state=case.hot_stream.fluid.backend,
    cold_fluid_equation_of_state=case.cold_stream.fluid.backend,
    hot_inlet_temperature_k=case.hot_stream.inlet.temperature.si_value,
    cold_inlet_temperature_k=case.cold_stream.inlet.temperature.si_value,
    hot_inlet_pressure_pa=case.hot_stream.inlet.pressure.si_value,
    cold_inlet_pressure_pa=case.cold_stream.inlet.pressure.si_value,
    hot_mass_flow_kg_s=case.hot_stream.mass_flow.si_value,
    cold_mass_flow_kg_s=case.cold_stream.mass_flow.si_value,
    tube_in_hot=tube_in_hot,
    flow_arrangement=flow_arrangement,
    tube_boundary_condition=tube_boundary_condition,
    annulus_boundary_condition=annulus_boundary_condition,
    minimum_terminal_delta_t=case.minimum_terminal_delta_t.si_value,
    required_duty_w=required_duty_w,
    duty_absolute_tolerance_w=duty_absolute_tolerance_w,
    duty_relative_tolerance=duty_relative_tolerance,
    optimization_objective=optimization_objective,
    top_n=requested_top_n,
    solver_params=SolverParams(...),
    expected_provider_identity=expected_provider_identity,
    ...
)
```

---

## 4. Application-Service Orchestration Contract

### 4.1 Sizing Orchestration

The HTTP sizing handler MUST execute the following frozen chain:

```
SizingApiRequest
│
├─ 1. validate_public_request()
│     → rejects at 422 for schema/unit/constraint violations
│
├─ 2. canonicalize_request() → compute request_digest
│
├─ 3. project_to_domain()
│     → SizingRequest + SizingRequestIdentity
│
├─ 4. sizing_gate()                      [TASK-009 Phase 1]
│     → produces PassedSizingGate
│
├─ 5. candidate_materialization()        [TASK-009 Phase 1]
│     → produces MaterializedCandidateSet
│
├─ 6. phase2_candidate_evaluation()      [TASK-008 + TASK-009 Phase 2]
│     → produces tuple[CandidateEvaluationRecord, ...]
│
├─ 7. phase3_evaluation_input()          [TASK-009 Phase 3]
│     → constructs Phase3EvaluationInput
│
├─ 8. phase3_classification()            [TASK-009 Phase 3]
│     → per-candidate classify_candidate()
│
├─ 9. deterministic_ranking()            [TASK-009 Phase 3]
│
├─ 10. top_n_projection()                [TASK-009 Phase 3]
│
├─ 11. build_optimization_result()       [TASK-009 Phase 3]
│      → + authoritative verification + provenance
│
├─ 12. build_sizing_run_artifacts()      [this contract, §9]
│
├─ 13. build_sizing_run_envelope()       [this contract, §6]
│
└─ 14. complete run in repository        [this contract, §7]
```

### 4.2 Rating Orchestration

```
RatingApiRequest
│
├─ 1. validate + canonicalize
├─ 2. project_to_domain() → DesignCase + DoublePipeGeometry + SolverParams
├─ 3. DoublePipeRatingService.rate()     [TASK-008]
├─ 4. build_rating_run_artifacts()       [this contract, §9]
├─ 5. build_rating_run_envelope()        [this contract, §6]
└─ 6. complete run in repository
```

### 4.3 Forbidden Paths

- **`DoublePipeService.size()`** — EXISTS in production at `src/hexagent/exchangers/double_pipe/service.py:140`. Contains `assumed_u = 500.0`. TASK-010 routes/services MUST NOT call it.
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
| GET | `/v1/runs/{run_id}` | `getRun` | — | `AnyRunEnvelope` |
| GET | `/v1/runs/{run_id}/report.html` | `getRunReportHtml` | — | `text/html` |
| GET | `/v1/runs/{run_id}/report.pdf` | `getRunReportPdf` | — | `application/pdf` or 501 |

### 5.2 `POST /v1/cases/validate`

- **Response:** `ValidationRunEnvelope` — `result_kind = "validation"`
- **Status:** `200` (accepted + canonicalized); `422` (schema/unit/constraint)
- **Idempotency:** Not enforced
- **Result hash:** `validation_receipt_hash` — computed from canonical request payload + validation schema version (NOT a provenance-derived domain result hash)
- **report_links:** May be absent or point to a validation-specific receipt endpoint. Does NOT promise a full rating/sizing report.

### 5.3 `POST /v1/double-pipe/rating`

- **Response:** `RatingRunEnvelope` — `result_kind = "rating"`, `result = RatingResult`
- **Domain → HTTP:** `SUCCEEDED` → `200`; `BLOCKED` → `200`; controlled `FAILED` → `200`
- **HTTP 500:** Unexpected server exception only
- **Idempotency:** Required

### 5.4 `POST /v1/double-pipe/sizing`

- **Response:** `SizingRunEnvelope` — `result_kind = "sizing"`, `result = OptimizationResult`
- **Domain → HTTP:** `COMPLETE` → `200`; `PARTIAL` (strict-stop) → `200`; input rejection → `422`
- **Idempotency:** Required

### 5.5–5.7 (unchanged from prior contract)

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
    artifact_bundle_digest: str
    report_links: ReportLinks

    @model_validator(mode="after")
    def _validate_cross_field(self) -> typing.Self:
        if self.result_hash != self.result.result_hash:
            raise ValueError("result_hash != result.result_hash")
        recomputed_prov = self.provenance.compute_hash()
        if self.provenance_digest != recomputed_prov:
            raise ValueError("provenance_digest mismatch")
        if self.provenance_digest != self.result.provenance_digest:
            raise ValueError("provenance_digest != result.provenance_digest")
        return self
```

**Sizing warning/blocker/failure authority:**

`OptimizationResult` stores ordered digests, not full messages. Warnings/blockers in the envelope are reconstructed from the authoritative artifact bundle:

1. Resolve `ordered_phase3_warning_digests` from `result.result_core`.
2. For each digest, look up the corresponding `EngineeringMessage` from the artifact bundle's `warning_binding_tuples` or `blocker_binding_tuples`.
3. Descriptors (preparation-level) are resolved to messages via `descriptor → message` reconstruction using `EngineeringMessageDescriptor` content.
4. Order is preserved exactly as in `ordered_phase3_warning_digests` / `ordered_phase3_blocker_digests`.
5. `failure` is derived from the highest-severity disposition failure record in the artifact bundle.

The build-time projection is the single normative algorithm — no "or" alternatives.

### 6.5 Cross-Field Invariants

| Invariant | Enforcement |
|---|---|
| Rating envelope MUST NOT carry `OptimizationResult` | Typed `result` field |
| Sizing envelope MUST NOT carry `RatingResult` | Typed `result` field |
| Validation `result` MUST be `None` | Explicit `None` type |
| `result_hash` == `result.result_hash` | `@model_validator` |
| `warnings`/`blockers`/`failure` == authority projection | Build-time single algorithm |
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
    *,
    api_schema_version: str,
    operation_id: str,
    idempotency_key: str,
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
    CLAIMED = "claimed"        # namespace reserved, owner token issued
    RUNNING = "running"        # execution in progress
    COMPLETE = "complete"      # finished, envelope + artifact bundle stored
    FAILED = "failed"          # execution failed, failure metadata stored


class RunRecord(StrictBaseModel):
    run_id: UUID
    namespace_digest: str
    request_digest: str
    operation: str
    state: RunState
    owner_token: str           # opaque token for CAS operations
    envelope: AnyRunEnvelope | None = None
    artifact_bundle: RatingRunArtifacts | SizingRunArtifacts | None = None
    failure: RunFailure | None = None
    report_instance_id: str | None = None
```

### 7.4 Run Repository Protocol

```python
class RunRepository(Protocol):
    def claim(
        self, *, namespace_digest: str, request_digest: str, operation: str,
    ) -> tuple[RunRecord, bool]:
        """Atomically claim a namespace.

        Returns (record, is_new).
        - Same namespace + same request_digest → returns existing record (is_new=False)
        - Same namespace + different request_digest → raises IdempotencyConflict (HTTP 409)
        - New namespace → creates CLAIMED record with owner_token (is_new=True)
        """
        ...

    def start(self, *, owner_token: str) -> None:
        """Transition CLAIMED → RUNNING. Validates owner_token."""
        ...

    def complete(
        self, *, owner_token: str,
        envelope: AnyRunEnvelope,
        artifact_bundle: RatingRunArtifacts | SizingRunArtifacts,
    ) -> None:
        """Transition RUNNING → COMPLETE. Stores envelope + artifact bundle."""
        ...

    def fail(self, *, owner_token: str, failure: RunFailure) -> None:
        """Transition RUNNING → FAILED. Stores failure metadata."""
        ...

    def get_by_run_id(self, run_id: UUID) -> RunRecord | None: ...

    def get_by_namespace(self, namespace_digest: str) -> RunRecord | None: ...
```

### 7.5 Behavior Matrix

| Condition | Outcome |
|---|---|
| Same namespace + same `request_digest` | Return same `run_id` + existing record; `is_new=False` |
| Same namespace + different `request_digest` | Raise `IdempotencyConflict` → `HTTP 409` |
| Concurrent same-namespace + same-digest | `threading.Lock` serialises; one wins, others get existing |
| Concurrent same-namespace + different-digest | First claims; second gets 409 |
| Same key + different `operation_id` | Different namespace (namespace includes `operation_id`) |

### 7.6 Concurrency Contract

- `claim()` is the ONLY serialized operation (protected by `threading.Lock`).
- Engineering execution (`start()` → `complete()`/`fail()`) occurs OUTSIDE the lock.
- `start()` validates owner_token — rejects if token doesn't match.
- Lost-owner recovery: not required in process-local scope.

### 7.7 Scope Limitations

- Process-local only; not persistent; lost on restart.
- Not suitable for multi-process or distributed deployments.
- Report retrieval reads the stored `artifact_bundle`, not just `artifact_bundle_digest`.

---

## 8. Canonical Request Algorithm

### 8.1 Entry Points

```python
def canonical_decimal_string(d: Decimal) -> str:
    """Normalize Decimal: strip trailing zeros, scientific if needed.
    Example: Decimal("1.500") → "1.5"
    """
    ...

def canonical_float_string(f: float) -> str:
    """Encode finite float as canonical JSON number string.
    Uses repr() with full precision. NaN/Inf rejected at validation.
    Example: 1.5 → "1.5"
    """
    ...

def canonical_quantity_payload(q: Quantity) -> dict[str, object]:
    """Quantity → {"value": <canonical SI float>, "unit": "<SI symbol>"}"""
    return {"value": q.si_value, "unit": si_unit(q.quantity_kind)}

def canonical_api_request_context(request: StrictBaseModel) -> dict[str, object]:
    """Produce a deterministic canonical payload dict.

    Preconditions:
    1. Request has passed strict schema validation (Pydantic, extra="forbid").
    2. All Quantity fields have been resolved to their SI canonical form.
    3. Provider identity fully resolved (git_revision, cache_policy included).
    4. Catalog snapshots fully resolved (content hash bound).
    """

def compute_api_request_digest(request: StrictBaseModel) -> str:
    """sha256 of canonical_api_request_context(request)."""
    return sha256_digest(canonical_api_request_context(request))
```

### 8.2 Canonicalization Rules

| Rule | Behavior |
|---|---|
| Dict key order | Recursively sorted by key |
| `None` values | **Retained** as JSON null |
| Pydantic aliases | Not used — field names only |
| Pydantic defaults | **Explicitly expanded** (no omission) |
| `Enum` | `.value` as string |
| `UUID` | Canonical 36-char string (`str(uuid)`) |
| `tuple` / `list` | JSON array |
| `Decimal` | `canonical_decimal_string()` — normalized, no trailing zeros |
| `float` | `canonical_float_string()` — JSON number representation |
| `int` vs `float` | Field type determines encoding — `1` (int) ≠ `1.5` (float). No ambiguous input permitted. |
| Unicode | NFC normalized |
| `Quantity` subtypes | `{"value": <si_value>, "unit": "<SI symbol>"}` via `canonical_quantity_payload()` |
| Catalog identity | Full canonical catalog snapshot payload → content hash |
| Provider config | `name` + `version` + `git_revision` + `reference_state_policy` + `configuration_fingerprint` + `cache_policy_version` |
| Negative zero | Forbidden (rejected at validation) |
| NaN / Inf | Forbidden (rejected at validation) |
| SI conversion | Performed with full precision float; rounding only at display time |
| `int` field that receives `1.0` (float) | Rejected by Pydantic strict mode |

### 8.3 Single Authority

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
    artifact_bundle_digest: str                            # sha256 over canonical bundle payload

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
    sizing_request_identity: SizingRequestIdentity
    passed_gate: PassedSizingGate
    materialization_result: MaterializedCandidateSet
    evaluation_input: Phase3EvaluationInput
    source_evaluation_records: tuple[CandidateEvaluationRecord, ...]
    identity_snapshots: tuple[Phase2SourceRecordIdentitySnapshot, ...]
    complete_snapshots: tuple[Phase2SourceRecordSnapshot | None, ...]
    source_record_descriptors: tuple[Phase2SourceRecordDescriptor | None, ...]
    source_bindings: tuple[Phase3SourceRecordBinding | None, ...]
    classification_inputs: tuple[Phase3CandidateClassificationInput | None, ...]
    preparation_results: tuple[Phase3CandidatePreparationResult | None, ...]
    warning_descriptor_tuples: tuple[tuple[EngineeringMessageDescriptor, ...], ...]
    blocker_descriptor_tuples: tuple[tuple[EngineeringMessageDescriptor, ...], ...]
    warning_binding_tuples: tuple[tuple[Phase3RunFailureDescriptorBinding, ...], ...]
    blocker_binding_tuples: tuple[tuple[Phase3RunFailureDescriptorBinding, ...], ...]
    evidence_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...]
    source_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...]
    phase3_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...]
    dispositions: tuple[CandidateDispositionRecord, ...]
    ranked_records: tuple[RankedCandidateRecord, ...]
    top_n_records: tuple[RankedCandidateRecord, ...]
    optimization_result: OptimizationResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str
```

All types are production TASK-009 types. The bundle is essentially a superset of `Phase3AuthoritativeArtifacts` plus the `evaluation_input`, `dispositions`, `ranked_records`, `optimization_result`, and `provenance_graph`.

### 9.3 Verifier Replay

```python
def verify_rating_artifact_bundle(bundle: RatingRunArtifacts) -> None:
    """Replay all authoritative verifiers against independent artifacts."""
    # 1) RatingResult.validate() — cross-field model validator
    # 2) Provenance semantic verification
    # 3) Artifact bundle digest recomputation

def verify_sizing_artifact_bundle(bundle: SizingRunArtifacts) -> None:
    """Replay all authoritative verifiers against independent artifacts."""
    # 1) Phase3EvaluationInput.verify_or_raise(...)
    # 2) Per-index: identity snapshot, complete snapshot, descriptor, binding, prep result, disposition
    # 3) verify_phase3_index_artifact_matrix() per-index
    # 4) verify_phase3_result_semantics_or_raise(...)
    # 5) Provenance semantic verification (with independent authority)
    # 6) Artifact bundle digest recomputation
```

### 9.4 Bundle Digest Self-Hash Exclusion

`artifact_bundle_digest` is computed over all bundle fields EXCEPT `artifact_bundle_digest` itself:

```python
def compute_bundle_canonical_payload(bundle: StrictBaseModel) -> dict[str, object]:
    d = canonicalize(bundle)
    d.pop("artifact_bundle_digest", None)
    return d
```

---

## 10. Report Model

### 10.1 Discriminated Report Artifact

```python
class ReportSourceDocument(StrEnum):
    RUN_ENVELOPE = "run_envelope"
    ARTIFACT_BUNDLE = "artifact_bundle"


class ReportArtifactKind(StrEnum):
    PRESENT = "present"
    NOT_AVAILABLE = "not_available"
    NOT_IMPLEMENTED = "not_implemented"
    OUT_OF_SCOPE = "out_of_scope"


class PresentReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.PRESENT]
    artifact_id: str
    source_document: ReportSourceDocument              # which source doc to resolve against
    source_document_digest: str                         # hash of that source document
    source_json_pointer: str                            # RFC 6901 pointer within source_document
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
    artifact_id: str
    reason_code: str
    capability: str


class NotImplementedReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.NOT_IMPLEMENTED]
    artifact_id: str
    capability: str


class OutOfScopeReportArtifact(StrictBaseModel):
    kind: Literal[ReportArtifactKind.OUT_OF_SCOPE]
    artifact_id: str
    capability: str


ReportArtifact = Annotated[
    PresentReportArtifact | UnavailableReportArtifact
    | NotImplementedReportArtifact | OutOfScopeReportArtifact,
    Discriminator("kind"),
]
```

- Non-PRESENT artifacts have **no** `source_document`, `source_document_digest`, `source_json_pointer`, `authority_digest`, `canonical_raw_value`, or unit/formatting fields.
- `source_document` + `source_json_pointer` allow resolution from either the envelope or the artifact bundle.

### 10.2 Report Model and Hashing

```python
class ReportSectionStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class ReportSection(StrictBaseModel):
    section_id: ReportSectionId                # enum, see §10.3
    status: ReportSectionStatus
    artifacts: tuple[ReportArtifact, ...]


class ReportInstanceIdentity(StrictBaseModel):
    report_schema_version: Literal["1"]
    report_content_hash: str
    source_run_envelope_digest: str
    source_domain_result_hash: str
    source_artifact_bundle_digest: str
    template_id: str
    template_version: str
    template_definition_hash: str
    formatter_registry_version: str


class DoublePipeReportModel(StrictBaseModel):
    report_schema_version: Literal["1"]
    sections: tuple[ReportSection, ...]         # fixed order, unique section_id
    report_instance_identity: ReportInstanceIdentity
    report_content_hash: str                    # sha256 of canonical sections payload (including schema_version)
    report_instance_hash: str                   # sha256 of canonical ReportInstanceIdentity

    @model_validator(mode="after")
    def _validate_hashes(self) -> typing.Self:
        if self.report_content_hash != compute_report_content_hash(self.sections, self.report_schema_version):
            raise ValueError("report_content_hash mismatch")
        if self.report_instance_hash != sha256_digest(self.report_instance_identity):
            raise ValueError("report_instance_hash mismatch")
        return self
```

- `report_content_hash`: engineering-deterministic — same input artifacts → same hash.
- `report_content_hash` includes `report_schema_version` + section order + statuses + artifact IDs + source bindings + formatted values.
- `report_instance_hash = sha256_digest(canonical_payload(ReportInstanceIdentity))`: binds content + source envelope + artifact bundle + template.
- Run-level metadata (timestamp, PID, host, trace, temp path) excluded from both hashes.

### 10.3 Report Section Enum and Ordering

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


OPTIONAL_SECTIONS: tuple[ReportSectionId, ...] = (
    ReportSectionId.INPUT_SUMMARY,
    ReportSectionId.GEOMETRY,
    ReportSectionId.HEAT_BALANCE,
    ReportSectionId.THERMAL_PERFORMANCE,
    ReportSectionId.SIZING_RANKING,
    ReportSectionId.TOP_RANKED_CANDIDATES,
    ReportSectionId.WARNINGS,
    ReportSectionId.PROVENANCE,
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

- Optional sections must appear in subsection ordering (preserving relative order when present) but may be absent.
- Sections present MUST be in exact SECTION_ORDER sequence.
- No duplicate `section_id`.

#### 10.3.1 Artifact ID Enum

```python
class ReportArtifactId(StrEnum):
    # Status banner
    STATUS = "status"
    TERMINATION_STATUS = "termination_status"
    # Run identity
    RUN_ID = "run_id"
    API_VERSION = "api_version"
    OPERATION = "operation"
    REQUEST_DIGEST = "request_digest"
    # Input
    CASE_NAME = "case_name"
    HOT_FLUID = "hot_fluid"
    COLD_FLUID = "cold_fluid"
    HOT_INLET_T = "hot_inlet_t"
    COLD_INLET_T = "cold_inlet_t"
    MASS_FLOWS = "mass_flows"
    DESIGN_PRESSURES = "design_pressures"
    DESIGN_TEMPERATURES = "design_temperatures"
    # Geometry
    GEOMETRY_SPEC = "geometry_spec"
    # Heat balance
    HEAT_DUTY = "heat_duty"
    ENERGY_RESIDUAL = "energy_residual"
    # Thermal
    TUBE_HTC = "tube_htc"
    ANNULUS_HTC = "annulus_htc"
    OVERALL_U = "overall_u"
    EFFECTIVENESS = "effectiveness"
    # Sizing
    SIZING_RANK = "sizing_rank"
    OPTIMIZATION_OBJECTIVE = "optimization_objective"
    # Top candidates
    TOP_CANDIDATE_RANK = "top_candidate_rank"
    TOP_CANDIDATE_GEOMETRY = "top_candidate_geometry"
    # Blocker
    BLOCKER_MESSAGE = "blocker_message"
    # Failure
    FAILURE_REASON = "failure_reason"
    # Provenance
    PROVENANCE_GRAPH = "provenance_graph"
    # Integrity
    RESULT_HASH = "result_hash"
    BUNDLE_HASH = "bundle_hash"
    # Not-implemented / out-of-scope
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

- Each `artifact_id` within a section MUST be unique.
- Mandatory artifact IDs MUST be present in their expected section.

### 10.4 Pre-Render Verification Chain

Before any HTML is emitted, the following MUST pass:

1. Domain result verification (RatingResult or OptimizationResult validators)
2. Provenance verification (independent authority)
3. Artifact bundle verification (§9.3)
4. Envelope projection verification (warnings/blockers/failure parity)
5. Report model verification (section uniqueness, mandatory set, order, artifact IDs)
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

## 12. Top-Ranked Candidates

The section is named `top_ranked_candidates`.

TASK-009 authorises deterministic ranking and Top-N projection only — it does NOT authorise recommendation, approval, procurement selection, or any "selected" semantics.

**Restricted words (user-facing labels only):** `selected`, `recommended`, `approved`, `procurement-ready`.

These restrictions apply to:
- Candidate section headers
- Candidate decision labels
- Status narrative text

These restrictions do NOT apply to:
- TASK-009 provenance relation values (`selected`, `selected_by`) — these are upstream authority data and must be preserved verbatim.
- Provenance appendix content.

---

## 13. Status and Risk Display (unchanged)

### 13.1 Every Print Page

Every HTML page produced by the report renderer MUST display:

```
PRELIMINARY
NOT FOR PROCUREMENT
NOT FOR CONSTRUCTION
```

- Present in the repeating `@media print` header/footer DOM
- Visible in normal (screen) view
- Not suppressible by user configuration
- Not colour-dependent

### 13.2 Blocker Display

Blockers appear at the top of the report, above or integrated into the status banner.

### 13.3 Not-Implemented Capabilities

| Capability | Display |
|---|---|
| Pressure drop | `NOT_IMPLEMENTED` |
| Velocity constraints | `NOT_IMPLEMENTED` |
| Materials | `OUT_OF_SCOPE` |
| Cost | `OUT_OF_SCOPE` |
| Mechanical compliance | `OUT_OF_SCOPE` |
| Procurement readiness | `OUT_OF_SCOPE` |

---

## 14. HTML Security Contract (unchanged)

---

## 15. PDF Boundary (unchanged)

---

## 16. Determinism Contract

### 16.1 Engineering Content Determinism

Same inputs → same `report_content_hash`.

### 16.2 Run Instance Determinism

Same stored `run_id` → repeated GET returns identical envelope + report.

### 16.3 HTML Byte Determinism

Same canonical request + same template + same formatter → byte-identical HTML engineering content. Test compares actual bytes, not only hashes.

### 16.4 Excluded from Engineering Hashes

- `current_time` / timestamp
- Random `run_id`
- Process ID
- Host name
- Trace ID
- Temporary directory

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
    value: str | None                               # truncated per MAX_DISPLAYED_VALUE_LENGTH
```

### 17.1 HTTP Mapping

| HTTP Status | `error_code` | Condition |
|---|---|---|
| 404 | `RUN_NOT_FOUND` | Unknown `run_id` |
| 409 | `IDEMPOTENCY_CONFLICT` | Same namespace, different request |
| 422 | `VALIDATION_FAILED` | Schema/unit/constraint failure |
| 500 | `INTERNAL_ERROR` | Unexpected exception (no traceback/path/token) |
| 501 | `PDF_NOT_AVAILABLE` | No PDF adapter configured |

### 17.2 FastAPI Exception-Handler Mapping

```python
@app.exception_handler(IdempotencyConflict)
async def idempotency_conflict_handler(request, exc):
    return JSONResponse(status_code=409, content=ApiError(...).model_dump())

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(status_code=422, content=ApiError(...).model_dump())

@app.exception_handler(Exception)
async def unexpected_error_handler(request, exc):
    # Redact traceback, path, token
    return JSONResponse(status_code=500, content=ApiError(...).model_dump())
```

---

## 18. Test Contract

| # | Test | Expected Outcome |
|---|---|---|
| T1 | `operation_id` values unique and stable | 6 unique IDs |
| T2 | Public request DTO JSON Schema exportable | Valid JSON Schema |
| T3 | Dimensional `float` in public request (e.g., `minimum_terminal_delta_t: 5.0` without unit) → `422` | Quantity validation rejects bare float |
| T4 | Invalid unit string → `422` | Unit enum validation |
| T5 | Unknown field in request → `422` | `extra="forbid"` |
| T6 | `ValidationApiRequest` + same payload → same `validation_receipt_hash` | Deterministic |
| T7 | `ValidationApiRequest` + different payload → different `validation_receipt_hash` | Discriminative |
| T8 | Canonical request: sorted vs unsorted JSON keys → same `request_digest` | Key-order independence |
| T9 | Canonical request: different value → different `request_digest` | Value sensitivity |
| T10 | Rating → `RatingRunEnvelope` carries `RatingResult`, not `OptimizationResult` | Type enforcement |
| T11 | Sizing → `SizingRunEnvelope` carries `OptimizationResult`, not `RatingResult` | Type enforcement |
| T12 | Validation → `result` is `None` | Cross-field invariant |
| T13 | Envelope `result_hash` mismatch → model validator rejects | Cross-field invariant |
| T14 | Rating envelope warning/blocker/failure mismatch → rejected | Cross-field invariant |
| T14b | Sizing envelope warning reconstruction from ordered digests matches authoritative bundle | Warning parity |
| T14c | Sizing envelope blocker reconstruction from ordered digests matches authoritative bundle | Blocker parity |
| T14d | Sizing envelope failure derived from highest-severity disposition | Failure authority |
| T14e | Sizing envelope provenance_digest matches result.provenance_digest | Provenance parity |
| T15 | Same namespace + same `request_digest` → same `run_id` + same record | Idempotency hit |
| T16 | Same namespace + different `request_digest` → `IdempotencyConflict` → `409` | Idempotency collision |
| T17 | Same key + different `operation_id` → independent namespaces | Namespace isolation |
| T18 | Concurrent same-namespace + same-digest → one CLAIMED, others get existing | Atomic claim |
| T19 | `BLOCKED` rating result → `HTTP 200` | Not `500` |
| T20 | Unknown `run_id` → `404` with `RUN_NOT_FOUND` | Repository miss |
| T21 | Unhandled exception → `HTTP 500`, no traceback/path/token | Structured error |
| T22 | PDF endpoint no adapter → `HTTP 501` with `PDF_NOT_AVAILABLE` | Structured error |
| T23 | Artifact bundle: `verify_sizing_artifact_bundle()` replays all per-artifact verifiers | Independent authority replay |
| T24 | Artifact bundle: tampered `artifact_bundle_digest` → rejected | Digest cross-check |
| T25 | Report: `PresentReportArtifact.source_document` + `source_json_pointer` resolves to correct value | RFC 6901 pointer with discriminator |
| T26 | Report: PRESENT artifact missing `source_json_pointer` → rejected | Invariant enforcement |
| T27 | Report: NOT_IMPLEMENTED artifact has `source_document` → rejected | Invariant enforcement |
| T28 | Report: duplicate `section_id` → rejected | Uniqueness enforcement |
| T29 | Report: missing mandatory section → rejected | Mandatory set enforcement |
| T30 | Report: wrong section order → rejected | Order enforcement |
| T31 | Report: tampered `report_content_hash` → render rejects | Fail-closed |
| T32 | Report: tampered source envelope digest in `ReportInstanceIdentity` → render rejects | Fail-closed |
| T33 | Report: tampered artifact bundle digest in `ReportInstanceIdentity` → render rejects | Fail-closed |
| T34 | Report: tampered template `definition_hash` → render rejects | Template identity |
| T35 | Blocker present → "BLOCKED" text in HTML top banner | String search |
| T36 | HTML print-header DOM contains `PRELIMINARY` / `NOT FOR PROCUREMENT` / `NOT FOR CONSTRUCTION` | Verify `@media print` repeating header/footer structure. NOTE: This tests HTML DOM structure — per-PDF-page verification requires actual PDF adapter |
| T37 | Disclaimer visible in normal (screen) view | Not print-only |
| T38 | HTML injection in case name → escaped (`&lt;script&gt;`) | Autoescape enforcement |
| T39 | No absolute path, traceback, or environment variable in error response body | Regex exclusion |
| T40 | Pressure drop / velocity → `NOT_IMPLEMENTED` in report | String search on specific artifact |
| T41 | Materials / cost / mechanical / procurement → `OUT_OF_SCOPE` in report | String search on specific artifact |
| T42 | Report user-facing labels do not contain "selected"/"recommended"/"approved" in candidate decision context | Section-specific negative check. Provenance appendix may contain these values. |
| T43 | Same canonical request → byte-identical HTML engineering content | `bytes` comparison |
| T44 | Same stored run → repeated GET returns identical report | Run instance determinism |
| T45 | `DoublePipeService.size()` monkeypatched to raise → full TASK-010 rating/sizing path succeeds without hitting the trap | Call-path unreachability proof |
| T46 | Python 3.11 full suite passes | Exit 0 |
| T47 | Python 3.12 full suite passes | Exit 0 |
| T48 | DTO → `DesignCase` projection: all fields map exactly | Field parity |
| T49 | DTO → `DoublePipeGeometry` projection: all fields map exactly | Field parity |
| T50 | DTO → `SolverParams` projection: all fields map exactly | Field parity |
| T51 | DTO → `SizingRequest` projection: all fields map exactly | Field parity |
| T52 | DTO → `SizingRequestIdentity` projection: all fields map exactly | Field parity |
| T53 | RunRepository: save envelope + artifact bundle, then generate report | Full replay test |

---

## 19. Explicit Exclusions

- **This docs-only design PR** excludes all implementation.
- **TASK-010 implementation** (when authorized) includes: FastAPI app/router, DTOs, application services, exception handlers, OpenAPI, in-memory RunRepository, HTML report builder, HTML renderer, report retrieval endpoints, integration/determinism/security tests.
- **TASK-010 permanent product exclusions**: database, ORM, persistent storage, object storage, authentication, authorization, rate limiting, specific PDF engine, TASK-011+, C4, pressure drop, velocity constraints, materials, cost, mechanical compliance, stochastic/heuristic optimization, procurement conclusions, compliance claims.

---

## 20. Design Status

| Field | Value |
|---|---|
| TASK-010 design | READY_FOR_REVIEW |
| TASK-010 implementation | BLOCKED |
| Frozen Contract SHA | NOT ESTABLISHED |
| Implementation Authorization | NOT GRANTED |
