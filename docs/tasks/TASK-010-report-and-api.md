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
| `SizingRequestIdentity` / `OptimizationObjective` / `ExpectedProviderIdentity` / `PassedSizingGate` / `MaterializedCandidateSet` | (at TASK-009 merge) | `src/hexagent/optimization/context.py` | `076126034eaf4116506ecbae54b32e644b4fc1c8` | `fa23a2e6a6d0c1544bc522933fbf3d87c4baed2d42a4ab9e6da78f7dcbb2a14b` |
| `MaterializationResult` | (at TASK-009 merge) | `src/hexagent/optimization/identities.py` | `4b649d4f24a10ea04089483b1787bb5fbaa0d754` | `b450df49dffef9373b39f4b658870dc6eff507c02a09d71363b0b1c4b0d780e1` |
| `CandidateEvaluationRecord` / `Phase3EvaluationInput` / `CandidateDispositionRecord` | (at TASK-009 merge) | `src/hexagent/optimization/phase3_evaluation.py` | `f5906ffd118fa2206bf026ed2680b6ae8c2d088a` | `b85d3245708ff325028d11577585ed42df50f05250a8426790f22986b81c1dcb` |
| `RankedCandidateRecord` / `OptimizationResult` / `build_optimization_result` | (at TASK-009 merge) | `src/hexagent/optimization/phase3_builder.py` | `6921bd2ef65a719e49cfec854fdf85e8c9009f5b` | `388e027c9bc65f9ef0de6d5c7bf5340e55381d0731965124d5160f8029d5fca4` |
| `Phase3AuthoritativeArtifacts` / `verify_phase3_result_semantics_or_raise` | (at TASK-009 merge) | `src/hexagent/optimization/phase3_verifier.py` | `09b2020799ca2ef4cf1cbb9b15a6f88fea95c866` | `4a0bfe69382d9ff927873e52051fdb3045a7e68738a2b5b0ad3d952aa0d489a0` |
| Base `main` | `3af8eb85e2a293c2706402dae8ec317a45fed38a` (PR #27 merge) | — | — | — |

**SHA-1 columns are 40-character hexadecimal git object hashes. SHA-256 columns are 64-character hexadecimal content hashes.** No shortened or placeholder values.

**`api_schema_version` is unified to `Literal["1"]` in all DTOs, envelopes, and the report model.**

### 2.1 Placeholder sizing path

**Forbidden:** `DoublePipeService.size()` — EXISTS in production at `src/hexagent/exchangers/double_pipe/service.py:140`. Contains `assumed_u = 500.0`. TASK-010 routes and application services MUST NOT call it. The API integration test must monkeypatch/trap this exact method and prove no TASK-010 code path invokes it. An import-time check is insufficient (see test T45).

---

## 3. Public API Request DTOs

### 3.1 Design Principle

Public HTTP requests are independent `StrictBaseModel`-based DTOs with explicit unit-bearing `Quantity` subtypes. They project to internal domain models during application-level orchestration.

**No public request uses bare unitless floats for dimensional quantities.** Every dimensional field uses a typed `Quantity` subclass.

**Catalog models are server-side immutable. Public HTTP requests accept catalog references, not raw production catalog models with internal bare-float fields.** The application service resolves references through a read-only registry, verifies content hashes, and freezes resolved snapshots.

All DTOs are `frozen`, `extra="forbid"`.

### 3.2 `ValidationApiRequest`

```python
class FluidStreamSpec(StrictBaseModel):
    fluid: FluidSpec                                    # backend + name + composition
    # phase_hint is already on FluidSpec — NOT duplicated here
    inlet: TPStateSpec                                  # temperature + pressure (unit-bearing)
    mass_flow: MassFlow                                  # kg/s
    fouling: FoulingResistanceSpec                       # with provenance


class ValidationApiRequest(StrictBaseModel):
    api_schema_version: Literal["1"]
    case_name: str                                       # non-empty, trimmed
    hot_stream: FluidStreamSpec
    cold_stream: FluidStreamSpec
    target_duty: Power                                   # REQUIRED — unit-bearing
    minimum_terminal_delta_t: TemperatureDifference      # K with unit metadata
    design_pressure_hot: AbsolutePressure
    design_pressure_cold: AbsolutePressure
    design_temperature_hot: AbsoluteTemperature
    design_temperature_cold: AbsoluteTemperature
    required_area_margin_fraction: float = Field(ge=0.0, le=1.0)
```

**`target_duty` is REQUIRED** (not optional). The TASK-010 double-pipe vertical slice always requires a target duty. Production `DesignCase` requires `target_duty` non-None OR at least one `outlet_temperature` — and the public DTO provides only the `target_duty` path.

**Single authority rules:**
- `FluidSpec.phase_hint` is the sole authority — `FluidStreamSpec` does NOT redeclare it.
- `minimum_terminal_delta_t` is the sole authority — rating/sizing requests consume it from the case.

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
    # Fouling authority is solely from stream-level FoulingResistanceSpec.


class ThermalConductivitySpec(StrictBaseModel):
    """Unit-bearing thermal conductivity."""
    value: float = Field(allow_inf_nan=False, gt=0)
    unit: Literal["W/(m*K)"]


class SolverParamsSpec(StrictBaseModel):
    absolute_residual_w: Power = Field(default=Power(value=1e-3, unit="W"))
    relative_residual_fraction: float = Field(default=1e-8, ge=0)
    bracket_temperature_tolerance_k: TemperatureDifference = Field(
        default=TemperatureDifference(value=1e-4, unit="K")
    )
    max_iterations: int = Field(default=100, ge=1)
```

**SolverParamsSpec defaults match production `SolverParams` exactly:**
`absolute_residual_w=1e-3`, `relative_residual_fraction=1e-8`, `bracket_temperature_tolerance_k=1e-4`, `max_iterations=100`.
Omitting `solver_params` or passing `{}` produces the same result and same canonical request identity.

#### 3.3.1 Projection to domain models

| RatingApiRequest field | Target |
|---|---|
| `case` → `ValidationApiRequest` | `DesignCase` (via §3.2.1) |
| `geometry` → `DoublePipeGeometrySpec` | `DoublePipeGeometry` (`.si_value` from each `Length`, `.value` from `ThermalConductivitySpec`) |
| `solver_params` → `SolverParamsSpec` | `SolverParams` (`.si_value` from `Power` and `TemperatureDifference`) |

#### 3.3.2 Fouling authority

**Single-authority rule:** The public `DoublePipeGeometrySpec` does NOT accept fouling fields. Fouling comes solely from `case.hot_stream.fouling` and `case.cold_stream.fouling` (both `FoulingResistanceSpec` with provenance). Any user-submitted fouling value on the geometry DTO is rejected at 422.

### 3.3.3 Provider Resolution Chain (Rating)

`RatingApiRequest.provider_ref` is resolved through an immutable provider registry **before** computing `request_digest`. The full resolved identity is bound into the canonical request.

```python
class ResolvedProviderAuthority(StrictBaseModel):
    provider_ref: str                           # original lookup key
    identity: ProviderIdentitySnapshot          # full immutable identity
    identity_digest: str                        # sha256 of identity payload
```

Resolution chain:

```
RatingApiRequest.provider_ref
→ resolve through immutable registry
→ obtain full ProviderIdentitySnapshot (name, version, git_revision,
  reference_state_policy, configuration_fingerprint, cache_policy_version)
→ reject unresolved identity → 422
→ construct ResolvedProviderAuthority
→ include full resolved identity in canonical request context
→ compute request_digest (binds full identity, NOT just provider_ref string)
→ claim idempotency namespace
→ execute rating with exactly that provider
```

**Prohibitions:**
- Computing `request_digest` before resolving provider
- Including only `provider_ref` string in request digest
- Same `provider_ref` replaying across different backend/version

**For Sizing:** `ExpectedProviderIdentity` is the caller's expectation. `ResolvedProviderAuthority.identity` is the actual configured provider. Actual identity must satisfy `ExpectedProviderIdentity.matches(actual)`. Canonical request binds both expected and actual resolved identity. Provider mismatch fails closed before execution. Actual provider identity changes produce different request digests.

### 3.4 `SizingApiRequest`

```python
class CatalogSnapshotReference(StrictBaseModel):
    """Server-side immutable catalog reference — NOT raw production catalog."""
    catalog_id: str
    catalog_version: str
    catalog_content_hash: str                    # sha256:[0-9a-f]{64}
    source_identity: str
    schema_version: str


class SizingApiRequest(StrictBaseModel):
    api_schema_version: Literal["1"]
    case: ValidationApiRequest

    # Catalog — immutable references, not raw bare-float models
    catalog_refs: tuple[CatalogSnapshotReference, ...]

    # Length bounds — unit-bearing
    minimum_effective_length: Length | None = None
    maximum_effective_length: Length | None = None
    request_raw_combination_cap: int | None = None

    # Sizing constraints
    tube_boundary_condition: Literal["constant_wall_temperature", "inner_wall_heated"]
    annulus_boundary_condition: Literal["inner_wall_heated", "constant_wall_temperature"]
    flow_arrangement: Literal["counterflow", "parallel"]
    tube_in_hot: bool = True

    # Duty — SINGLE AUTHORITY: derived from case.target_duty
    # required_duty removed — DesignCase.target_duty is the sole authority.
    # SizingRequestIdentity.required_duty_w = case.target_duty.si_value
    duty_absolute_tolerance: Power = Field(default=Power(value=0, unit="W"))
    duty_relative_tolerance: Dimensionless = Field(
        default=Dimensionless(value=0, unit="dimensionless"))

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
- `duty_absolute_tolerance` → `Power`
- `duty_relative_tolerance` → `Dimensionless` with `unit="dimensionless"` (not `""`)

**Catalog ref canonical ordering:**

`catalog_refs` are sorted before resolution, digest computation, and domain projection:

```python
catalog_refs = tuple(sorted(
    catalog_refs,
    key=lambda r: (
        r.catalog_id,
        r.catalog_version,
        r.catalog_content_hash,
        r.source_identity,
        r.schema_version,
    ),
))
```

Uniqueness key: `catalog_id + catalog_version + source_identity + schema_version`. Same key with different `content_hash` → reject. Completely duplicate reference → reject (no silent dedup). Resolved catalogs follow the same canonical order into `SizingRequest.catalogs`, `SizingRequestIdentity.catalog_snapshot_identities`, canonical request snapshot, and artifact bundle.

**Catalog resolution contract:**
The application service must, before computing `request_digest`:
1. Look up each `CatalogSnapshotReference` in the immutable read-only registry.
2. Resolved `CompleteDoublePipeCatalogSnapshot` must match `catalog_content_hash` — mismatch → `422`.
3. Reference not found → `422`.
4. After resolution, the snapshot is frozen and immutable.
5. The canonical request context binds the full resolved snapshot + content hash.
6. Same reference pointing to different content → fail closed.

#### 3.4.1 Projection to `SizingRequest` + `SizingRequestIdentity`

The orchestration layer extracts `.si_value` from each Quantity:

```python
# Sizing projection: api_request (SizingApiRequest) → domain (SizingRequest + identity)
api_request: SizingApiRequest  # public DTO with case.target_duty

# 1. Resolve duty from single authority
required_duty_w: float = api_request.case.target_duty.si_value

# 2. Build domain request (no case/duty — domain SizingRequest has no case field)
domain_request = SizingRequest(
    catalogs=resolved_catalogs,
    minimum_effective_length_m=(
        api_request.minimum_effective_length.si_value
        if api_request.minimum_effective_length is not None
        else None
    ),
    maximum_effective_length_m=(
        api_request.maximum_effective_length.si_value
        if api_request.maximum_effective_length is not None
        else None
    ),
    request_raw_combination_cap=api_request.request_raw_combination_cap,
)

# 3. Build identity (duty from api_request, not domain_request)
identity = build_sizing_request_identity(
    domain_request,
    required_duty_w=required_duty_w,
    duty_absolute_tolerance_w=api_request.duty_absolute_tolerance.si_value,
    duty_relative_tolerance=api_request.duty_relative_tolerance.si_value,
    ...
)
```

---

## 4. Application-Service Orchestration Contract

### 4.1 Sizing Orchestration

```
SizingApiRequest
│
├─ 1. validate_public_request() → rejects at 422
├─ 2. resolve provider authority (§3.3.3)
│      → ResolvedProviderAuthority (or 422 if not found / identity mismatch)
│      → verify ExpectedProviderIdentity.matches(actual)
├─ 3. resolve catalog refs → verify hash → freeze snapshots
├─ 4. construct canonical context (expected provider + actual provider + resolved catalogs)
├─ 5. compute request_digest (binds full provider identity + catalogs + all inputs)
├─ 6. claim idempotency namespace
├─ 7. project_to_domain() → SizingRequest + SizingRequestIdentity
├─ 8. sizing_gate() → PassedSizingGate
├─ 9. candidate_materialization() → MaterializationResult
├─ 10. phase2_candidate_evaluation() → tuple[CandidateEvaluationRecord, ...]
├─ 11. phase3_evaluation_input() → Phase3EvaluationInput
│       (materialization_result is already MaterializationResult)
├─ 12. phase3_classification() → per-candidate
├─ 13. deterministic_ranking()
├─ 14. top_n_projection()
├─ 15. build_optimization_result() → + authoritative verification + provenance
├─ 16. build_sizing_run_artifacts()
├─ 17. build_sizing_run_envelope()
└─ 18. complete run in repository
```

**Provider not found or identity mismatch → HTTP 422:** No run record generated, no namespace claimed, no catalog gate or rating execution started.

### 4.2 Rating Orchestration

```
RatingApiRequest
│
├─ 1. validate_public_request() → rejects at 422
├─ 2. resolve provider_ref through immutable registry
│      → ResolvedProviderAuthority (full ProviderIdentitySnapshot)
│      → verify identity completeness (or 422 if not found)
├─ 3. construct canonical request context
│      (full provider identity + geometry + solver + case + flow arrangement)
├─ 4. compute request_digest (binds full resolved provider identity — NOT just provider_ref string)
├─ 5. claim idempotency namespace
├─ 6. project_to_domain() → DesignCase + DoublePipeGeometry + SolverParams
├─ 7. DoublePipeRatingService.rate() — execute with exactly the resolved provider
├─ 8. build_rating_run_artifacts()
├─ 9. build_rating_run_envelope()
└─ 10. complete run in repository
```

**Prohibitions:**
- Computing `request_digest` before resolving provider
- Including only `provider_ref` string in request digest
- Claiming namespace then discovering provider does not exist
- Executing with a different provider version than was resolved

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
- `GET /v1/runs/{run_id}/report.html` (rating/sizing only): `200`; `404`; `500`.
- `GET /v1/runs/{validation_run_id}/report.html` → `404` (validation runs have no report).
- `GET /v1/runs/{run_id}/report.pdf` (rating/sizing only): `application/pdf` or `501` (no adapter).

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
    report_links: None = None                             # validation runs have no report
```

Validation runs do NOT support report generation. `GET /v1/runs/{validation_run_id}/report.html` returns `404`.

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
    artifact_bundle: RatingRunArtifacts                   # REQUIRED for self-verification
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

        # Bundle parity
        verify_rating_artifact_bundle(self.artifact_bundle)
        if self.artifact_bundle.result != self.result:
            raise ValueError("bundle.result != result")
        if self.artifact_bundle.request_identity != self.result.request_identity:
            raise ValueError("bundle.request_identity != result.request_identity")
        if self.artifact_bundle.provider_identity != self.result.provider_identity:
            raise ValueError("bundle.provider_identity != result.provider_identity")
        if self.artifact_bundle.provenance_graph != self.result.provenance_graph:
            raise ValueError("bundle.provenance_graph != result.provenance_graph")
        if compute_rating_artifact_bundle_digest(self.artifact_bundle) != self.artifact_bundle_digest:
            raise ValueError("artifact_bundle_digest mismatch")

        recomputed = self.provenance.compute_hash()
        if self.provenance_digest != recomputed:
            raise ValueError("provenance_digest mismatch")
        # P0-4: Three-way provenance parity
        if self.provenance_digest != self.result.provenance_digest:
            raise ValueError("envelope provenance_digest != result.provenance_digest")
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
    artifact_bundle: SizingRunArtifacts                    # REQUIRED
    artifact_bundle_digest: str
    report_links: ReportLinks

    @model_validator(mode="after")
    def verify_projection(self) -> typing.Self:
        if self.result_hash != self.result.result_hash:
            raise ValueError("result_hash != result.result_hash")

        verify_sizing_artifact_bundle(self.artifact_bundle)
        recomputed_digest = compute_artifact_bundle_digest(self.artifact_bundle)
        if recomputed_digest != self.artifact_bundle_digest:
            raise ValueError("artifact_bundle_digest mismatch")
        if self.result != self.artifact_bundle.optimization_result:
            raise ValueError("result != bundle.optimization_result")

        expected_warnings = reconstruct_sizing_warnings(self.artifact_bundle)
        expected_blockers = reconstruct_sizing_blockers(self.artifact_bundle)
        if self.warnings != expected_warnings:
            raise ValueError("warning projection mismatch")
        if self.blockers != expected_blockers:
            raise ValueError("blocker projection mismatch")

        # P0-3: Sizing failure is always None.
        # OptimizationResult only has COMPLETE/PARTIAL termination_status.
        # Candidate-level and run-level exceptions are expressed via
        # blocker digests, dispositions, and failure bindings — NOT RunFailure.
        if self.failure is not None:
            raise ValueError("sizing envelope failure must be None")

        # PARTIAL termination must have auditable authority
        if self.result.termination_status == TerminationStatus.PARTIAL:
            verify_partial_termination_authority(
                result=self.result,
                artifacts=self.artifact_bundle.phase3_authoritative_artifacts,
                dispositions=self.artifact_bundle.dispositions,
            )

        # P0-3: Provenance object parity — not just digest equality
        if self.provenance != self.artifact_bundle.provenance_graph:
            raise ValueError("provenance != bundle.provenance_graph")
        recomputed_prov = self.provenance.compute_hash()
        if self.provenance_digest != recomputed_prov:
            raise ValueError("provenance_digest mismatch")
        if self.provenance_digest != self.result.provenance_digest:
            raise ValueError("provenance_digest != result.provenance_digest")
        return self
```

**Reconstruction functions:**

```python
def reconstruct_sizing_warnings(bundle: SizingRunArtifacts) -> tuple[EngineeringMessage, ...]:
    artifacts = bundle.phase3_authoritative_artifacts
    return resolve_phase3_message_digests(
        ordered_digests=bundle.optimization_result.ordered_warning_digests,
        binding_tuples=artifacts.warning_binding_tuples,
        descriptor_tuples=artifacts.warning_descriptor_tuples,
    )

def reconstruct_sizing_blockers(bundle: SizingRunArtifacts) -> tuple[EngineeringMessage, ...]:
    artifacts = bundle.phase3_authoritative_artifacts
    return resolve_phase3_message_digests(
        ordered_digests=bundle.optimization_result.ordered_blocker_digests,
        binding_tuples=artifacts.blocker_binding_tuples,
        descriptor_tuples=artifacts.blocker_descriptor_tuples,
    )
```

def verify_partial_termination_authority(
    *,
    result: OptimizationResult,
    artifacts: Phase3AuthoritativeArtifacts,
    dispositions: tuple[CandidateDispositionRecord, ...],
) -> None:
    """Verify PARTIAL termination has an auditable explanation.

    PARTIAL requires at least one of:
    - non-empty blocker digests in OptimizationResult
    - at least one non-FEASIBLE disposition record
    - source_failure_bindings contains at least one non-None element
    - evidence_failure_bindings contains at least one non-None element
    - phase3_failure_bindings contains at least one non-None element

    The failure-binding tuples are fixed-length (one slot per candidate),
    filled with None for candidates without failure.  Therefore
    bool(tuple) is NOT sufficient — each element must be checked
    individually.

    COMPLETE requires none of these (but may have them).
    """
    has_blockers = bool(result.ordered_blocker_digests)
    has_non_feasible = any(
        d.disposition != Phase3Disposition.FEASIBLE for d in dispositions
    )
    has_source_failure = any(
        binding is not None
        for binding in artifacts.source_failure_bindings
    )
    has_evidence_failure = any(
        binding is not None
        for binding in artifacts.evidence_failure_bindings
    )
    has_phase3_failure = any(
        binding is not None
        for binding in artifacts.phase3_failure_bindings
    )
    has_failure_authority = (
        has_source_failure or has_evidence_failure or has_phase3_failure
    )

    if not (has_blockers or has_non_feasible or has_failure_authority):
        raise ValueError(
            "PARTIAL termination requires at least one blocker, "
            "non-FEASIBLE disposition, or non-None failure binding"
        )
```

**Rules:** Digest order from `OptimizationResult` — no manual reorder. Descriptor+tuple from same `Phase3AuthoritativeArtifacts`. Unresolved/conflicting → fail closed. Never re-derive authority from display text.

### 6.5 Cross-Field Invariants

| Invariant | Enforcement |
|---|---|
| Rating envelope MUST NOT carry `OptimizationResult` | Typed `result` field |
| Sizing envelope MUST NOT carry `RatingResult` | Typed `result` field |
| Validation `result` MUST be `None` | Explicit `None` type |
| `result_hash` == `result.result_hash` | `@model_validator` |
| Bundle parity (result, identity, provider, provenance, digest) | `@model_validator` |
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
    record_version: int
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

**State transition table:**

| Current State | Event | Next State | Notes |
|---|---|---|---|
| ABSENT | claim() | CLAIMED | New record, new owner_token, record_version=1 |
| CLAIMED | start() | RUNNING | CAS: owner_token + expected_version |
| CLAIMED | fail() | FAILED | CAS: owner_token + expected_version |
| CLAIMED | lease expired | STALE | No CAS — determined by clock |
| RUNNING | complete() | COMPLETE | CAS: owner_token + expected_version |
| RUNNING | fail() | FAILED | CAS: owner_token + expected_version |
| RUNNING | lease expired | STALE | No CAS — determined by clock |
| STALE | claim(takeover=True) | CLAIMED | Atomic CAS takeover: new owner_token, record_version+1, refresh timestamps. Old owner_token immediately invalidated. |
| COMPLETE | claim() same digest | COMPLETE (replay) | No state change, returns existing envelope |
| COMPLETE | claim() different digest | 409 conflict | Namespace collision |
|| FAILED | claim() same digest | FAILED_REPLAY | Return existing failed result; no re-execution |
|| FAILED | claim() different digest | 409 | IDEMPOTENCY_CONFLICT |
| CLAIMED/RUNNING | heartbeat() | same state | CAS: owner_token + expected_version, refresh lease |

**`claim()` return type:**

```python
class ClaimOutcome(StrEnum):
    NEW_CLAIM = "new_claim"
    COMPLETE_REPLAY = "complete_replay"
    IN_PROGRESS = "in_progress"
    FAILED_REPLAY = "failed_replay"
    STALE_REJECTED = "stale_rejected"
    STALE_TAKEOVER = "stale_takeover"

@dataclass(frozen=True)
class ClaimResult:
    outcome: ClaimOutcome
    record: RunRecord
```

**`claim()` behavior by case:**

| Condition | Outcome | Response |
|---|---|---|
| Same namespace + COMPLETE + same digest | COMPLETE_REPLAY | Return existing envelope, 200 |
| Same namespace + COMPLETE + different digest | 409 | Namespace conflict |
| Same namespace + CLAIMED/RUNNING + lease valid | IN_PROGRESS | Return 409 + structured IN_PROGRESS |
|| Same namespace + STALE + takeover=False | STALE_REJECTED | HTTP 409 structured error; record not modified |
|| Same namespace + STALE + takeover=True | STALE_TAKEOVER | Atomic CAS: new owner_token, version+1, refresh timestamps |
|| Same namespace + FAILED + same digest | FAILED_REPLAY | Return existing failed result; no re-execution |
|| Same namespace + FAILED + different digest | 409 | IDEMPOTENCY_CONFLICT |
| New namespace | NEW_CLAIM | Create record, new owner_token |

**Takeover atomicity:**
- Generates new `owner_token`
- Increments `record_version`
- Refreshes `claimed_at` and `lease_expires_at`
- Old `owner_token` immediately invalidated
- Old owner's subsequent heartbeat/complete/fail all CAS-fail

**All mutating methods** (start, heartbeat, complete, fail) must check:
- `owner_token` matches
- `expected_version` matches
- Current state is in the allowed set
- Lease is valid (or call is a legal takeover)

**`complete()` additional checks:**
- `artifact_bundle == envelope.artifact_bundle` (object equality, not just type/digest)
- `record.request_digest == envelope.request_digest`
- `record.operation == envelope.operation`
- Bundle result matches envelope result
- Bundle digest matches envelope.artifact_bundle_digest

### 7.4 Run Repository Protocol

```python
LEASE_DURATION: timedelta = timedelta(seconds=30)
HEARTBEAT_INTERVAL: timedelta = timedelta(seconds=10)


class RunRepository(Protocol):
    def claim(
        self,
        *,
        namespace_digest: str,
        request_digest: str,
        operation: str,
        takeover: bool = False,
    ) -> ClaimResult: ...
    def start(self, *, owner_token, expected_version) -> RunRecord: ...
    def heartbeat(self, *, owner_token, expected_version) -> RunRecord: ...
    def complete(self, *, owner_token, expected_version, envelope, artifact_bundle) -> RunRecord: ...
    def fail(self, *, owner_token, expected_version, failure) -> RunRecord: ...
    def get_by_run_id(self, run_id: UUID) -> RunRecord | None: ...
    def get_by_namespace(self, namespace_digest: str) -> RunRecord | None: ...
```

**`complete()` parity checks:**
- `record.request_digest == envelope.request_digest`
- `record.operation == envelope.operation`
- `artifact_bundle` type matches `envelope.operation`: rating → `RatingRunArtifacts`, sizing → `SizingRunArtifacts`
- Bundle result matches envelope result
- Bundle digest == envelope.artifact_bundle_digest
- Bundle canonical request digest == envelope.request_digest
- Rating run MUST NOT store sizing bundle; sizing run MUST NOT store rating bundle.

**Behavior:** Same namespace+same digest+COMPLETE → replay. Same namespace+different digest → 409. CAS via expected_version. Stale takeover handled.

### 7.5 Scope Limitations

- Process-local only; not persistent; lost on restart.
- Report retrieval reads stored `artifact_bundle`.

---

## 8. Canonical Request Algorithm

### 8.1 Design Decision: Quantity values as JSON strings

**Canonical scalar type rules:** `Decimal`, `float`, and `Quantity` numeric values are encoded as **JSON strings** (to avoid binary float serialization differences). `int` remains JSON number. `bool` remains JSON boolean. `None` remains JSON null.

```python
def canonical_decimal_string(value: Decimal) -> str:
    """Normalize Decimal to canonical string with 15 significant digits.

    Algorithm:
    1. Reject non-finite (NaN, Inf, -Inf).
    2. Reject signed negative zero (Decimal("-0"), float("-0.0")).
    3. Zero → "0".
    4. Determine adjusted exponent.
    5. Quantize to 15 significant digits via ROUND_HALF_EVEN.
    6. If rounding produces negative zero → reject.
    7. If |adjusted exponent| <= 10: fixed notation, strip trailing zeros and trailing dot.
    8. Otherwise: scientific notation.
       Format: mantissa "E" sign exponent (e.g. "E+15", "E-30").
       No leading zeros in exponent. Uppercase 'E'.

    Rules:
    - All finite non-zero numbers use the same 15-digit rounding — no subnormal exception.
    - Negative zero is ALWAYS rejected, never normalized to "0".
    - Decimal and float canonical scalar outputs are JSON strings.
    - int remains JSON number, bool remains JSON boolean.
    - Float entry: Decimal(repr(float_value)) is the only conversion path.
    - Quantity SI conversion uses exact Decimal factor, never binary float si_value.

    Test vectors:
      0 → "0"
      -0 → REJECTED
      1 → "1"
      1.0 → "1"
      1.5000 → "1.5"
      1.234567890123445 → "1.23456789012344"
      1.234567890123455 → "1.23456789012346"
      999999999999999.5 → "1E+15"
      1E-30 → "1E-30"
      1E+30 → "1E+30"
      0.00000000001 → "1E-11"
      0.000000000001 → "1E-12"
      99999999999 → "99999999999"
      100000000000 → "1E+11"
    """
    if not value.is_finite():
        raise ValueError("non-finite decimal")
    if value.is_zero() and value.is_signed():
        raise ValueError("negative zero")
    if value.is_zero():
        return "0"

    precision = 15
    adjusted = value.adjusted()
    quantum = Decimal(1).scaleb(adjusted - precision + 1)
    rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)

    if rounded.is_zero() and rounded.is_signed():
        raise ValueError("rounding produced negative zero")

    rounded_adjusted = rounded.adjusted()
    if -10 <= rounded_adjusted <= 10:
        result = format(rounded, "f")
        if "." in result:
            result = result.rstrip("0").rstrip(".")
        return result

    # Scientific notation: mantissa "E" sign exponent
    normalized = rounded.normalize()
    mantissa_str = format(normalized, "E")
    # Split mantissa and exponent
    parts = mantissa_str.split("E")
    mantissa = parts[0]
    exp = int(parts[1])
    return f"{mantissa}E{exp:+d}"

def canonical_quantity_payload(q: Quantity) -> dict[str, str]:
    """Quantity → {"value": "<canonical SI string>", "unit": "<SI symbol>"}

    Conversion:
    1. Input Quantity value → Decimal(repr(value)) (exact binary-to-decimal).
    2. Convert to SI using EXACT Decimal conversion factor (never binary float si_value).
    3. Apply canonical_decimal_string() (15-digit rounding, reject -0).
    4. Output value as JSON string.
    5. Output unit as SI symbol — NOT the original input unit.
    """
    ...
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
|| `Decimal` | `canonical_decimal_string()` → JSON string (15 significant digits, ROUND_HALF_EVEN) |
|| `float` | `Decimal(repr(f))` → `canonical_decimal_string()` → JSON string (no binary float intermediate for SI) |
|| `int` | JSON number |
|| `bool` | JSON boolean |
| `Quantity` subtypes | `{"value": "<Decimal string>", "unit": "<SI symbol>"}` |
| Unicode | NFC |
| Negative zero | REJECTED (Decimal("-0"), float("-0.0"), any equivalent) |
| NaN / Inf | REJECTED |

### 8.3 Test Vectors

| Input | Canonical form |
|---|---|
| `1` (int) | `1` |
| `1.0` (Decimal) | `"1"` |
| `1.5000` (Decimal) | `"1.5"` |
| `0` (int) | `0` |
| `-0` (Decimal) | REJECTED |
| `float("-0.0")` | REJECTED |
|| `0.000001` (Decimal) | `"0.000001"` |
|| `1000000` (int) | `1000000` |
|| `1.234567890123445` (Decimal) | `"1.23456789012344"` |
|| `1.234567890123455` (Decimal) | `"1.23456789012346"` |
|| `999999999999999.5` (Decimal) | `"1E+15"` |
|| `1E-30` (Decimal) | `"1E-30"` |
|| `1E+30` (Decimal) | `"1E+30"` |
|| `0.00000000001` (Decimal) | `"1E-11"` |
|| `0.000000000001` (Decimal) | `"1E-12"` |
|| `99999999999` (Decimal) | `"99999999999"` |
|| `100000000000` (Decimal) | `"1E+11"` |
| `TemperatureDifference(5, "delta_degC")` | `{"value": "5", "unit": "K"}` |
| `TemperatureDifference(5, "K")` | `{"value": "5", "unit": "K"}` |
| `Length(250, "cm")` | `{"value": "2.5", "unit": "m"}` |
| `AbsolutePressure(1, "bar")` | `{"value": "100000", "unit": "Pa"}` |
| `Power(2, "kW")` | `{"value": "2000", "unit": "W"}` |

**Equivalence test:** `TemperatureDifference(5, "K")` and `TemperatureDifference(5, "delta_degC")` produce identical canonical payload and identical `request_digest`.

### 8.4 Single Authority

All idempotency identity, `request_digest`, and report input snapshot MUST call `compute_api_request_digest()`.

---

## 9. Authoritative Artifact Bundles

### 9.1 `RatingRunArtifacts`

```python
class RatingRunArtifacts(StrictBaseModel):
    canonical_request_snapshot: dict[str, object]
    request_identity: RatingRequestIdentity
    geometry_snapshot: DoublePipeGeometry
    solver_settings: SolverParams
    provider_identity: ProviderIdentitySnapshot
    result: RatingResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str

    @model_validator(mode="after")
    def _validate_bundle_hash(self) -> typing.Self:
        recomputed = compute_rating_artifact_bundle_digest(self)
        if self.artifact_bundle_digest != recomputed:
            raise ValueError("artifact_bundle_digest mismatch")
        return self
```

### 9.2 `SizingRunArtifacts`

```python
class SizingRunArtifacts(StrictBaseModel):
    canonical_request_snapshot: dict[str, object]
    sizing_request: SizingRequest
    evaluation_input: Phase3EvaluationInput
    # NOTE: materialization_result, sizing_request_identity, passed_gate,
    # candidate_set are derived from evaluation_input — not duplicated.
    phase3_authoritative_artifacts: Phase3AuthoritativeArtifacts
    dispositions: tuple[CandidateDispositionRecord, ...]
    ranked_records: tuple[RankedCandidateRecord, ...]
    top_n_records: tuple[RankedCandidateRecord, ...]
    optimization_result: OptimizationResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str
```

**`Phase3EvaluationInput.materialization_result` is `MaterializationResult`** (production type from `identities.py`). It carries `candidates`, `candidate_set`, `sizing_gate`, `catalog_snapshots`, and length bounds. The bundle does NOT duplicate these as top-level fields — they are accessed via `evaluation_input.materialization_result.*`.

### 9.3 Verifier Replay

```python
def geometry_identity_payload(geometry: DoublePipeGeometry) -> dict[str, object]:
    """Deterministic projection of DoublePipeGeometry to a dict for identity comparison.

    Must match the complete geometry field set in RatingRequestIdentity.
    Uses frozen production float values — no display string comparison.
    """
    return {
        "inner_tube_inner_diameter_m": geometry.inner_tube_inner_diameter_m,
        "inner_tube_outer_diameter_m": geometry.inner_tube_outer_diameter_m,
        "outer_pipe_inner_diameter_m": geometry.outer_pipe_inner_diameter_m,
        "effective_length_m": geometry.effective_length_m,
        "wall_thermal_conductivity_w_m_k": geometry.wall_thermal_conductivity_w_m_k,
        "inner_surface_roughness_m": geometry.inner_surface_roughness_m,
        "annulus_surface_roughness_m": geometry.annulus_surface_roughness_m,
        "inner_fouling_resistance_m2k_w": geometry.inner_fouling_resistance_m2k_w,
        "outer_fouling_resistance_m2k_w": geometry.outer_fouling_resistance_m2k_w,
    }


def canonical_geometry_identity_payload(
    geometry: DoublePipeGeometry,
) -> dict[str, str]:
    """Canonical form of geometry identity for API snapshot parity.

    Every float value is converted to canonical JSON string via
    Decimal(repr(float_value)) → canonical_decimal_string() with
    15 significant digits, ROUND_HALF_EVEN.  Same algorithm as
    compute_api_request_digest().

    Used by verify_rating_canonical_request_parity() to compare
    canonical_request_snapshot["geometry"] against authoritative geometry.
    NOT used for raw production identity parity (use geometry_identity_payload).
    """
    raw = geometry_identity_payload(geometry)
    return {
        key: canonical_decimal_string(Decimal(repr(typing.cast(float, value))))
        for key, value in raw.items()
    }


def provider_identity_payload(
    provider: ProviderIdentitySnapshot,
) -> dict[str, str]:
    """Explicit canonical payload for ProviderIdentitySnapshot.

    ProviderIdentitySnapshot is a frozen dataclass, NOT a Pydantic model.
    model_dump() does not exist on dataclasses.  This helper provides the
    canonical dict for snapshot parity comparison.
    """
    return {
        "name": provider.name,
        "version": provider.version,
        "git_revision": provider.git_revision,
        "reference_state_policy": provider.reference_state_policy,
        "configuration_fingerprint": provider.configuration_fingerprint,
        "cache_policy_version": provider.cache_policy_version,
    }


def verify_rating_canonical_request_parity(
    *,
    snapshot: dict[str, object],
    request_identity: RatingRequestIdentity,
    geometry: DoublePipeGeometry,
    solver: SolverParams,
    provider: ProviderIdentitySnapshot,
) -> None:
    """Verify canonical request snapshot matches authoritative sources.

    Validates: geometry, solver controls, provider identity, flow arrangement,
    boundary conditions, minimum terminal delta-T, request identity payload.
    Must be called by verify_rating_artifact_bundle() and envelope validator.
    Prevents attack where snapshot is modified and bundle digest recomputed.
    """
    # All comparisons use canonical payloads — never raw float vs canonical string.
    # The snapshot stores values in the same canonical form as compute_api_request_digest().

    # Geometry: compare canonical payload dicts (all values are canonical JSON strings)
    # geometry_identity_payload() returns raw floats — used for production identity parity.
    # canonical_geometry_identity_payload() returns canonical strings — used for API snapshot.
    expected_geometry = canonical_geometry_identity_payload(geometry)
    if snapshot.get("geometry") != expected_geometry:
        raise ValueError("canonical snapshot geometry mismatch")

    # Solver controls: compare via canonical numeric string
    # (snapshot stores canonical Decimal strings, not raw floats)
    solver_canonical = {
        "absolute_residual_w": canonical_decimal_string(Decimal(repr(solver.absolute_residual_w))),
        "relative_residual_fraction": canonical_decimal_string(Decimal(repr(solver.relative_residual_fraction))),
        "bracket_temperature_tolerance_k": canonical_decimal_string(Decimal(repr(solver.bracket_temperature_tolerance_k))),
        "max_iterations": solver.max_iterations,  # int → JSON number
    }
    if snapshot.get("solver") != solver_canonical:
        raise ValueError("canonical snapshot solver mismatch")

    # Provider identity: explicit payload (dataclass, NOT Pydantic model_dump)
    expected_provider = provider_identity_payload(provider)
    if snapshot.get("provider_identity") != expected_provider:
        raise ValueError("canonical snapshot provider identity mismatch")

    # Flow arrangement
    if snapshot.get("flow_arrangement") != request_identity.flow_arrangement:
        raise ValueError("canonical snapshot flow_arrangement mismatch")

    # Boundary conditions (P0-4: must be checked)
    if snapshot.get("tube_boundary_condition") != request_identity.tube_boundary_condition:
        raise ValueError("canonical snapshot tube_boundary_condition mismatch")
    if snapshot.get("annulus_boundary_condition") != request_identity.annulus_boundary_condition:
        raise ValueError("canonical snapshot annulus_boundary_condition mismatch")

    # Minimum terminal delta-T: compare via canonical numeric string
    expected_delta_t = canonical_decimal_string(
        Decimal(repr(request_identity.minimum_terminal_delta_t))
    )
    if snapshot.get("minimum_terminal_delta_t") != expected_delta_t:
        raise ValueError("canonical snapshot minimum_terminal_delta_t mismatch")


def verify_rating_artifact_bundle(bundle: RatingRunArtifacts) -> None:
    # Reconstruct through real Pydantic validation
    reconstructed = RatingResult.model_validate(bundle.result.model_dump(mode="python"))
    if reconstructed != bundle.result:
        raise ValueError("RatingResult reconstruction mismatch")
    # Verify result hash
    if not bundle.result.verify_hash():
        raise ValueError("RatingResult hash verification failed")
    # Verify provenance
    if not bundle.result.verify_provenance():
        raise ValueError("RatingResult provenance verification failed")
    # Validate integrity
    valid, issues = bundle.result.validate_integrity()
    if not valid:
        raise ValueError("RatingResult integrity verification failed: " + "; ".join(issues))
    # P0-4: Cross-check identity references
    if bundle.result.request_identity != bundle.request_identity:
        raise ValueError("rating request identity mismatch")
    if bundle.result.provider_identity != bundle.provider_identity:
        raise ValueError("rating provider identity mismatch")
    if bundle.result.provenance_graph != bundle.provenance_graph:
        raise ValueError("rating provenance graph mismatch")

    # P0-4: Geometry snapshot binding
    if geometry_identity_payload(bundle.geometry_snapshot) != bundle.request_identity.geometry:
        raise ValueError("geometry snapshot mismatch")

    # P0-4: Solver settings binding (all four controls)
    if bundle.solver_settings.absolute_residual_w != bundle.request_identity.solver_absolute_residual_w:
        raise ValueError("solver absolute residual mismatch")
    if bundle.solver_settings.relative_residual_fraction != bundle.request_identity.solver_relative_residual_fraction:
        raise ValueError("solver relative residual mismatch")
    if bundle.solver_settings.bracket_temperature_tolerance_k != bundle.request_identity.solver_bracket_temperature_tolerance_k:
        raise ValueError("solver bracket tolerance mismatch")
    if bundle.solver_settings.max_iterations != bundle.request_identity.solver_max_iterations:
        raise ValueError("solver max iterations mismatch")

    # P0-4: Canonical request snapshot parity (not just bundle digest)
    verify_rating_canonical_request_parity(
        snapshot=bundle.canonical_request_snapshot,
        request_identity=bundle.request_identity,
        geometry=bundle.geometry_snapshot,
        solver=bundle.solver_settings,
        provider=bundle.provider_identity,
    )

    # Digest
    recompute_and_check_bundle_digest(bundle)


def verify_sizing_artifact_bundle(bundle: SizingRunArtifacts) -> None:
    artifacts = bundle.phase3_authoritative_artifacts
    ei = bundle.evaluation_input

    # 1) Structural validation
    SizingRequest.model_validate(bundle.sizing_request.model_dump(mode="python"))

    # 2) MaterializationResult.verify_or_raise()
    ei.materialization_result.verify_or_raise()

    # 3) Phase3EvaluationInput.verify_or_raise() with real parameters
    ei.verify_or_raise(
        sizing_request=bundle.sizing_request,
        candidates=ei.materialization_result.candidates,
        source_records=ei.evaluation_records,
        phase2_source_record_descriptors=artifacts.phase2_source_record_descriptors,
        warning_binding_tuples=artifacts.warning_binding_tuples,
        blocker_binding_tuples=artifacts.blocker_binding_tuples,
        source_failure_bindings=artifacts.source_failure_bindings,
        evidence_failure_bindings=artifacts.evidence_failure_bindings,
    )

    # 4) Semantic acceptance
    verify_phase3_result_semantics_or_raise(
        result=bundle.optimization_result,
        graph=bundle.provenance_graph,
        evaluation_input=ei,
        artifacts=artifacts,
        dispositions=bundle.dispositions,
        ranked_records=bundle.ranked_records,
    )

    # 5) Top-N prefix check
    if bundle.top_n_records != bundle.ranked_records[: len(bundle.top_n_records)]:
        raise ValueError("top_n_records are not ranked prefix")

    # 6) Bundle digest
    recompute_and_check_bundle_digest(bundle)
```

**All verifier methods are real production APIs:**
- `verify_hash()` — exists on `RatingResult`
- `verify_provenance()` — exists on `RatingResult`
- `validate_integrity()` — exists on `RatingResult`
- `verify_or_raise()` — exists on `MaterializationResult` and `Phase3EvaluationInput`
- `verify_phase3_result_semantics_or_raise()` — exists in `phase3_verifier.py`
- `Phase3AuthoritativeArtifacts` is a frozen dataclass with NO `verify_or_raise()` method.

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
    artifact_id: ReportArtifactId
    source_document: ReportSourceDocument
    source_document_digest: str
    source_json_pointer: str
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
            raise ValueError("report_instance_identity.report_content_hash mismatch")
        if self.report_instance_identity.report_schema_version != self.report_schema_version:
            raise ValueError("report_schema_version mismatch in instance identity")

        # Content hash
        expected = compute_report_content_hash(self.sections, self.report_schema_version)
        if self.report_content_hash != expected:
            raise ValueError("report_content_hash mismatch")

        # Instance hash
        if self.report_instance_hash != sha256_digest(self.report_instance_identity):
            raise ValueError("report_instance_hash mismatch")

        # P0-5: Executable section uniqueness, ordering, and artifact validation
        section_ids = tuple(section.section_id for section in self.sections)
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("duplicate report section")
        if section_ids != SECTION_ORDER:
            raise ValueError("report section order mismatch")

        artifact_owners: dict[ReportArtifactId, ReportSectionId] = {}
        for section in self.sections:
            for artifact in section.artifacts:
                if artifact.artifact_id in artifact_owners:
                    raise ValueError(f"duplicate artifact_id: {artifact.artifact_id}")
                artifact_owners[artifact.artifact_id] = section.section_id
                verify_report_artifact_shape(artifact)

        for artifact_id, expected_owner in MANDATORY_ARTIFACT_OWNERS.items():
            actual_owner = artifact_owners.get(artifact_id)
            if actual_owner is None:
                raise ValueError(f"mandatory artifact missing: {artifact_id}")
            if actual_owner != expected_owner:
                raise ValueError(f"mandatory artifact wrong owner: {artifact_id}")

        return self
```

def validate_rfc6901_pointer(pointer: str) -> None:
    """Validate a JSON Pointer per RFC 6901.

    Allowed:
    - "" (empty root pointer)
    - "/" (root)
    - "/geometry/inner~1outer" (~1 decodes to /)
    - "/a~0b" (~0 decodes to ~)

    Rejected:
    - "a/b" (missing leading /)
    - "/a~" (trailing ~)
    - "/a~2b" (only ~0 and ~1 are valid escapes)
    """
    if pointer == "":
        return
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must be empty or start with '/'")
    for token in pointer.split("/")[1:]:
        index = 0
        while index < len(token):
            if token[index] != "~":
                index += 1
                continue
            if index + 1 >= len(token):
                raise ValueError("trailing '~' in JSON pointer token")
            escaped = token[index + 1]
            if escaped not in {"0", "1"}:
                raise ValueError(
                    "JSON pointer permits only ~0 and ~1 escapes"
                )
            index += 2


def verify_report_artifact_shape(artifact: ReportArtifact) -> None:
    """Validate PRESENT/non-PRESENT field invariants for a single artifact.

    PRESENT artifacts must have:
    - source_document, source_document_digest, source_json_pointer,
      authority_digest, canonical_raw_value, formatter_id, formatter_version,
      rounding_mode, formatted_display_value all non-None
    - source_json_pointer starts with "/" or is empty root pointer
    - Pointer tokens only allow canonical ~0, ~1 escapes

    Non-PRESENT artifacts must NOT have:
    - source_json_pointer, canonical_raw_value, source_unit, formatter fields
    """
    if artifact.kind == ReportArtifactKind.PRESENT:
        present = typing.cast(PresentReportArtifact, artifact)
        # RFC 6901 pointer validation (full token-level validation)
        validate_rfc6901_pointer(present.source_json_pointer)
        # All required fields present
        required = [
            present.source_document, present.source_document_digest,
            present.authority_digest, present.canonical_raw_value,
            present.formatter_id, present.formatter_version,
        ]
        if any(v is None or (isinstance(v, str) and not v.strip()) for v in required):
            raise ValueError("PRESENT artifact has empty required field")
    else:
        # Non-PRESENT must not carry source-only fields
        if hasattr(artifact, "source_json_pointer") and getattr(artifact, "source_json_pointer", None):
            raise ValueError("non-PRESENT artifact must not have source_json_pointer")
        if hasattr(artifact, "canonical_raw_value") and getattr(artifact, "canonical_raw_value", None):
            raise ValueError("non-PRESENT artifact must not have canonical_raw_value")


**Source pointer resolution rules (step 7 of pre-render chain):**
- `~1` in pointer token decodes to `/`
- `~0` in pointer token decodes to `~`
- Pointer cannot be resolved → fail closed
- Resolved canonical raw value differs from artifact's `canonical_raw_value` → fail closed

**`verify_report_section_status_matrix()` is a mandatory pre-render verifier** called by the only report builder before returning the model. It is NOT optional, NOT a comment, and NOT skippable. It is invoked at step 6 of the pre-render chain (§10.5).

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

### 10.4 Section Enum, Ordering, and Mandatory Artifacts

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
    WARNING_MESSAGES = "warning_messages"
    BLOCKER_MESSAGES = "blocker_messages"
    TOP_RANKED_CANDIDATES = "top_ranked_candidates"
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


class CanonicalBlockerItem(StrictBaseModel):
    """Deterministic ordered item in a blocker collection artifact."""
    occurrence_index: int
    code: str
    severity: str
    message_payload_digest: str
    source_binding_digest: str


class CanonicalWarningItem(StrictBaseModel):
    """Deterministic ordered item in a warning collection artifact."""
    occurrence_index: int
    code: str
    severity: str
    message_payload_digest: str
    source_binding_digest: str


class CanonicalRankedCandidateItem(StrictBaseModel):
    """Deterministic ordered item in a Top-N collection artifact."""
    rank: int
    source_qualified_candidate_id: str
    ranked_record_digest: str
    geometry_identity_digest: str


# Collection artifact canonical values are deterministic ordered tuples/lists.
# Ordering authority:
#   warnings/blockers: upstream result digest order
#   Top-N: ranked_records prefix order
# Prohibited: reordering by display text.


MANDATORY_ARTIFACT_IDS: frozenset[ReportArtifactId] = frozenset({
    ReportArtifactId.STATUS,
    ReportArtifactId.RUN_ID,
    ReportArtifactId.REQUEST_DIGEST,
    ReportArtifactId.RESULT_HASH,
    ReportArtifactId.BUNDLE_HASH,
})


MANDATORY_ARTIFACT_OWNERS: dict[ReportArtifactId, ReportSectionId] = {
    ReportArtifactId.STATUS: ReportSectionId.STATUS_BANNER,
    ReportArtifactId.RUN_ID: ReportSectionId.RUN_IDENTITY,
    ReportArtifactId.REQUEST_DIGEST: ReportSectionId.RUN_IDENTITY,
    ReportArtifactId.RESULT_HASH: ReportSectionId.INTEGRITY,
    ReportArtifactId.BUNDLE_HASH: ReportSectionId.INTEGRITY,
}
```

**Mandatory artifact rules:**
- All `MANDATORY_ARTIFACT_IDS` must be present exactly once.
- Each must reside in its designated section per `MANDATORY_ARTIFACT_OWNERS`.
- Same `artifact_id` must NOT appear across multiple sections.
- Missing mandatory artifact → fail closed.

### 10.5 Pre-Render Verification Chain

```python
def verify_report_section_status_matrix(
    *, report_model: DoublePipeReportModel,
    source_envelope: RatingRunEnvelope | SizingRunEnvelope,
) -> None:
    source_state = derive_source_state(source_envelope)
    for sid in ReportSectionId:
        expected = SECTION_STATUS_MATRIX[source_state].get(sid)
        if expected is None: continue
        section = _find_section(report_model, sid)
        if section is None:
            if expected != ReportSectionStatus.NOT_APPLICABLE:
                raise ValueError(f"required section {sid} missing")
        elif section.status != expected:
            raise ValueError(f"section {sid} status {section.status} != {expected}")
```

Pre-render order:
1. Domain result verification
2. Provenance verification
3. Artifact bundle verification (§9.3)
4. Envelope projection verification
5. Report hash/section/artifact verification (mandatory artifact presence + owner)
6. `verify_report_section_status_matrix(report_model, source_envelope)`
7. Source pointer resolution and digest parity
8. Template identity verification
9. Render (fail closed on any error)

**T30b executable cases:**
- Rating SUCCEEDED + geometry BLOCKED → REJECT
- Rating BLOCKED + blockers EMPTY → REJECT
- Rating FAILED + failure_details NOT_APPLICABLE → REJECT
- Sizing COMPLETE + sizing_ranking NOT_APPLICABLE → REJECT
- Sizing PARTIAL + top_ranked_candidates COMPLETE → REJECT
- Missing STATUS artifact → REJECT
- Missing RUN_ID artifact → REJECT
- Missing REQUEST_DIGEST artifact → REJECT
- Missing RESULT_HASH artifact → REJECT
- Missing BUNDLE_HASH artifact → REJECT
- Mandatory artifact in wrong section → REJECT
- Same artifact in two sections → REJECT

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

- Every HTML page: `PRELIMINARY` / `NOT FOR PROCUREMENT` / `NOT FOR CONSTRUCTION`.
- Blockers appear above status banner.
- Not-implemented: `NOT_IMPLEMENTED`. Out-of-scope: `OUT_OF_SCOPE`.

---

## 14. HTML Security Contract

- Autoescape enabled. No user-specified template paths. No external CDN/font/tracking.
- User input HTML-escaped. No absolute paths, tracebacks, tokens, env vars in output.

---

## 15. PDF Boundary

No adapter → `HTTP 501` with structured `ApiError`. Physical per-page verification deferred until PDF adapter selected.

---

## 16. Determinism Contract

- Engineering content: same inputs → same `report_content_hash`.
- Run instance: same `run_id` → identical envelope + report.
- HTML byte: byte-identical HTML (test compares `bytes`).
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
```

class ErrorDetail(StrictBaseModel):
    path: tuple[str | int, ...]
    code: str
    message: str
    rejected_value_preview: str | None = None

    @field_validator("rejected_value_preview")
    @classmethod
    def limit_preview(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 200:
            return value[:200]
        return value
```

**ErrorDetail rules:**
- No traceback, no absolute paths, no tokens, no env vars, no full sensitive input
- `rejected_value_preview` max 200 characters
- `details` sorted deterministically by `(path, code)`

- 404 → `RUN_NOT_FOUND`, 409 → `IDEMPOTENCY_CONFLICT`, 422 → `VALIDATION_FAILED`, 500 → `INTERNAL_ERROR`, 501 → `PDF_NOT_AVAILABLE`.

---

## 18. Test Contract

| # | Test | Outcome |
|---|---|---|
| T1 | `operation_id` unique and stable | 6 unique IDs |
| T2 | Public request DTO JSON Schema exportable | Valid |
| T3 | Dimensional bare `float` → `422` | Quantity validation |
|| T3b | Sizing bare `float` for `duty_absolute_tolerance` → `422` | Quantity validation |
| T3c | Geometry DTO with fouling → `422` | Single-authority |
| T3d | `Dimensionless(value=0, unit="")` → `422` | Unit non-empty |
| T3e | `Dimensionless(value=0, unit="dimensionless")` → accepted | Valid unit |
| T3f | `Dimensionless(value=1, unit="%")` → canonicalized correctly | SI conversion |
| T3g | `ValidationApiRequest` without `target_duty` → `422` | Required field |
| T3h | `FluidStreamSpec` with `phase_hint` (not on FluidSpec) → rejected | No duplicate authority |
| T4 | Invalid unit string → `422` | Unit validation |
| T5 | Unknown field → `422` | `extra="forbid"` |
| T6–T7 | Validation receipt hash determinism / discriminability | Hash checks |
| T8–T9 | Canonical key-order independence / value sensitivity | Digest checks |
| T9b | Canonical Quantity: `Length(250, "cm")` → `{"value":"2.5","unit":"m"}` | SI conversion |
| T9c | Canonical `-0` → REJECTED | Negative zero |
| T9d | `Decimal("1.5000")` → `"1.5"` | Trailing zero stripped |
| T9e | `TemperatureDifference(5, "delta_degC")` → `{"value":"5","unit":"K"}` | SI unit |
| T9f | `TemperatureDifference(5, "K")` and `TemperatureDifference(5, "delta_degC")` → same digest | Unit equivalence |
|| T9g | SolverParams omitted → same defaults as explicit `SolverParamsSpec()` | Default projection |
|| T60 | `SizingApiRequest` has no `required_duty` field; duty derived from `case.target_duty.si_value` | Single authority |
|| T61 | `case.target_duty` SI-equivalent units: `Power(100, "kW")` and `Power(100000, "W")` → identical `required_duty_w` | Unit equivalence |
|| T62 | Extra `required_duty` field submitted → rejected by `extra="forbid"` at `422`; no idempotency namespace claimed | Forbid rejection |
|| T63 | Same `provider_ref`, different provider version → different `request_digest`; provider resolution occurs before digest computation | Provider identity binding + ordering |
|| T64 | Same `provider_ref`, different `git_revision` → different `request_digest`; provider resolution occurs before digest computation | Provider identity binding + ordering |
|| T65 | `configuration_fingerprint` change → different `request_digest`; provider resolution occurs before digest computation | Provider identity binding + ordering |
|| T66 | `cache_policy_version` change → different `request_digest`; provider resolution occurs before digest computation | Provider identity binding + ordering |
|| T67 | Expected provider identity does not match resolved provider → `422`; no run record, no namespace claim, no catalog/rating execution | Fail closed + ordering |
|| T68 | Provider not found in registry → `422`; no run record, no namespace claim | Resolution failure + ordering |
|| T86 | `catalog_refs` input order different → same `request_digest` | Canonical ordering |
|| T87 | Completely duplicate catalog ref → rejected | Uniqueness |
|| T88 | Same identity, different content hash → rejected | Identity consistency |
|| T10–T12 | Envelope type enforcement | Cross-field |
|| T13 | Envelope `result_hash` mismatch → rejected | Cross-field |
|| T14 | Rating envelope cross-field mismatch → rejected | Cross-field |
|| T14b–T14d | Sizing warning/blocker/provenance parity | Cross-field |
|| T14e | Sizing provenance graph object parity | Cross-field |
|| T14f | Sizing envelope warning mismatch → rejected | Warning parity |
|| T14g | Sizing envelope blocker mismatch → rejected | Blocker parity |
|| T14j | Sizing envelope failure non-None → rejected | Failure always None |
|| T14l | PARTIAL, no blocker, all dispositions FEASIBLE, all three failure-binding tuples contain only None → rejected | PARTIAL authority |
|| T14m | PARTIAL with blocker or non-FEASIBLE disposition → accepted | PARTIAL authority |
|| T14n | PARTIAL with only phase3_failure_bindings containing non-None binding → accepted | PARTIAL authority |
|| T14o | All three failure-binding tuples non-empty but every element is None, no blocker, all FEASIBLE → rejected | PARTIAL authority |
|| T14p | COMPLETE does not execute PARTIAL authority rejection | COMPLETE authority |
|| T14k | Sizing provenance graph object mismatch (even with same digest) → rejected | Provenance object parity |
|| T69 | Tampered `geometry_snapshot` → rejected | Geometry binding |
|| T70 | Tampered `solver_settings` → rejected | Solver binding |
|| T71 | Canonical request snapshot geometry/solver/provider/flow/boundary mismatch → rejected | Snapshot parity |
|| T71a | ProviderIdentitySnapshot uses explicit payload, not model_dump() | Dataclass parity |
|| T71b | tube_boundary_condition tampered → rejected | Boundary parity |
|| T71c | annulus_boundary_condition tampered → rejected | Boundary parity |
|| T71d | Canonical "0.001" matches authoritative float 0.001 via unified canonicalization → accepted | Canonical parity |
|| T71e | Snapshot uses raw float where contract requires canonical string → rejected | Type parity |
|| T71f | Provider configuration_fingerprint tampered → rejected | Provider parity |
|| T71g | minimum_terminal_delta_t canonical value tampered → rejected | Terminal delta-T parity |
|| T71h | Canonical snapshot geometry values are canonical strings ("0.02", "5", "16") matching production raw floats (0.02, 5.0, 16.0) via unified canonicalization → accepted | Canonical geometry parity |
|| T71i | Canonical snapshot geometry uses raw float where contract requires canonical string → rejected | Geometry type parity |
|| T71j | Any geometry canonical string tampered (e.g. "0.02" → "0.021") → rejected | Geometry tamper |
|| T71k | Geometry input SI-equivalent (e.g. Length(2, "cm") vs Length(0.02, "m")) → same canonical payload → same request digest | Geometry SI equivalence |
|| T71l | Geometry with negative zero / NaN / Inf → rejected before digest/claim | Geometry non-finite rejection |
|| T72 | Envelope `provenance_digest` differs from `result.provenance_digest` → rejected; three-way parity: envelope.provenance_digest == result.provenance_digest == envelope.provenance.compute_hash() | Provenance three-way parity |
|| T73 | Two blockers represented and order stable | Collection identity |
|| T74 | Two warnings represented and order stable | Collection identity |
|| T75 | `requested_top_n=3` represents three candidates | Collection identity |
|| T76 | Collection item digest tampered → rejected | Fail-closed |
|| T77 | Collection order modified → rejected | Order authority |
|| T14h | Rating bundle digest mismatch → rejected | Bundle parity |
|| T14i | Rating bundle result mismatch → rejected | Bundle parity |
|| T15–T18 | Idempotency: replay, collision, isolation, concurrency | Various |
| T18b–T18e | RUNNING replay, stale takeover, CAS rejection | CAS |
| T19–T22 | BLOCKED→200, 404, 500, 501 | Status code |
| T23–T24 | Artifact bundle replay + digest cross-check | Verifier |
| T24b | Bundle missing SizingRequest → rejected | Required field |
|| T25 | PresentReportArtifact pointer resolution | RFC 6901 + discriminator |
|| T25b | Valid pointer `""` (root) → accepted | RFC 6901 |
|| T25c | Valid pointer `"/geometry/inner~1outer"` → accepted, decoded to `/geometry/inner/outer` | RFC 6901 ~1 decode |
|| T25d | Valid pointer `"/a~0b"` → accepted, decoded to `/a~b` | RFC 6901 ~0 decode |
|| T25e | Invalid pointer `"a/b"` (no leading /) → rejected | RFC 6901 |
|| T25f | Invalid pointer `"/a~"` (trailing ~) → rejected | RFC 6901 |
|| T25g | Invalid pointer `"/a~2b"` (invalid escape) → rejected | RFC 6901 |
|| T25h | Source pointer cannot be resolved → fail closed | Pointer resolution |
|| T25i | Resolved value differs from `canonical_raw_value` → fail closed | Pointer parity |
| T26–T27 | PRESENT missing pointer → reject; non-PRESENT with source → reject | Invariant |
| T28–T30 | Section uniqueness, mandatory, order → reject | Section contract |
| T30b | Section/status matrix violations (see §10.5) | 12 cases |
| T30c | `artifact_id` not in `ReportArtifactId` → reject | Typed enforcement |
| T31–T34 | Tampered hashes → reject | Fail-closed |
| T34b | `report_instance_identity.report_content_hash` cross-binding → reject | Cross-binding |
| T35–T37 | Blocker top-banner, print DOM, screen disclaimer | HTML structure |
| T38–T39 | HTML escaping, no path/traceback/token leak | Security |
| T40–T41 | NOT_IMPLEMENTED / OUT_OF_SCOPE display | String search |
| T42 | User labels: no "selected"/"recommended"; provenance appendix may preserve | Section-specific |
| T43 | Byte-identical HTML | `bytes` comparison |
| T44 | Same run → identical report | Determinism |
| T45 | `DoublePipeService.size()` monkeypatched → TASK-010 path succeeds | Trap proof |
| T46–T47 | Python 3.11/3.12 full suite | Exit 0 |
| T48–T52 | DTO → domain model exact projection | Field parity |
| T53 | RunRepository complete → report generation | Full replay |
| T54 | All upstream hash pins complete and correctly typed | Static audit |
| T55 | Catalog reference not found → `422` | Resolution failure |
| T56 | Catalog reference hash mismatch → `422` | Content hash failure |
| T57 | `SolverParamsSpec()` default values match production `SolverParams` defaults | Default alignment |
| T58 | `complete()` rejects rating envelope with sizing bundle | Type mismatch |
| T59 | `complete()` rejects sizing envelope with rating bundle | Type mismatch |
|| T78 | claim new record → ClaimResult(NEW_CLAIM, record) | State machine |
|| T79 | COMPLETE same digest → ClaimResult(COMPLETE_REPLAY, record); no re-execution | Replay |
|| T80 | RUNNING lease valid → ClaimResult(IN_PROGRESS, record); HTTP 409 | In-progress response |
|| T81 | STALE takeover=True → ClaimResult(STALE_TAKEOVER, record); new owner_token, version+1 | CAS takeover |
|| T82 | STALE takeover=False → ClaimResult(STALE_REJECTED, record); record not modified | Stale rejection |
|| T83 | Takeover → old owner heartbeat → CAS reject (owner_token mismatch) | Owner invalidation |
|| T84 | Takeover → old owner complete → CAS reject (owner_token mismatch) | Owner invalidation |
|| T85 | Illegal CLAIMED → COMPLETE transition → reject | State machine |
|| T86a | FAILED same digest → ClaimResult(FAILED_REPLAY, record); no re-execution | Failed replay |
|| T86b | FAILED different digest → 409 IDEMPOTENCY_CONFLICT | Namespace conflict |
|| T86c | complete() with bundle != envelope bundle → reject | Bundle parity |
|| T86d | claim() returns ClaimResult, not tuple[RunRecord, bool] | Type contract |

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
