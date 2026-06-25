# TASK-009 — Manufacturable sizing and deterministic candidate optimization

**Status:** BLOCKED — Engineering design review changes required
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-005, TASK-008
**GitHub Issue:** #23
**Implementation branch:** Not created
**Draft PR:** Not created
**Production implementation:** Not started

TASK-009 returns to READY only after Round 31 Engineering Design Review passes.

---

## 1. Dependency Baseline

- TASK-008 PR #21: merged
- TASK-008 reviewed Head: `37eda3580ba7acced1beb4cec307343a9f5449ec`
- TASK-008 merge commit: `cef3f85402b1696b336347293afc7276bbf67545`
- TASK-008 Issue #20: closed
- C4 Issue #19: open; C4 deferred and unimplemented
- TASK-016: PLANNED; not a v0.1 dependency

---

## 2. Objective

From a caller-supplied, structurally validated, hash-verified set of complete double-pipe assembly options, generate deterministic discrete candidates, evaluate each through the TASK-008 `rate_double_pipe()` kernel, apply explicit feasibility and manufacturability contracts, and return a deterministic ranked result with complete identity digests, hash, provenance, and JSON round-trip integrity.

---

## 3. Design Review History

| Round | Comment ID | Decision |
|-------|-----------|----------|
| 1 | 4797079477 | CHANGES REQUIRED |
| 2 | 4797175254 | CHANGES REQUIRED |
| 3 | 4797267787 | CHANGES REQUIRED |
| 4 | 4797374705 | CHANGES REQUIRED |
| 5 | 4797451288 | CHANGES REQUIRED |
| 6 | 4797612208 | CHANGES REQUIRED |
| 7 | 4797806616 | CHANGES REQUIRED |
| 8 | — | CHANGES REQUIRED — review delivered without GitHub comment |
| 9 | 4798128591 | CHANGES REQUIRED |
| 10 | 4798318702 | CHANGES REQUIRED |
| 11 | 4798512240 | CHANGES REQUIRED |
| 12 | 4798693707 | CHANGES REQUIRED |
| 13 | 4798895696 | CHANGES REQUIRED |
| 14 | 4799066285 | CHANGES REQUIRED |
| 15 | 4799188706 | CHANGES REQUIRED |
| 16 | 4799475298 | CHANGES REQUIRED |
| 17 | 4799885832 | CHANGES REQUIRED |
| 18 | 4800120135 | CHANGES REQUIRED |
| 19 | 4800488397 | CHANGES REQUIRED |
| 20 | 4800787131 | CHANGES REQUIRED |
| 21 | 4800977010 | CHANGES REQUIRED |
| 22 | 4801215509 | CHANGES REQUIRED |
| 23 | 4801552673 | CHANGES REQUIRED |
| 24 | 4801928304 | CHANGES REQUIRED |
| 25 | 4802083544 | CHANGES REQUIRED |
| 26 | 4802228027 | CHANGES REQUIRED |
| 27 | 4802328600 | CHANGES REQUIRED |
| 28 | 4802483910 | CHANGES REQUIRED |
| 29 | 4802701831 | CHANGES REQUIRED |
| 30 | 4802836532 | CHANGES REQUIRED |

|---|

## 4. Data Model

### 4.1 Container Hierarchy

```text
SizingRequest
  └── CompleteDoublePipeCatalogSnapshot[]
        └── CompleteDoublePipeAssemblyOption[]
              └── LengthSource
```

### 4.2 CatalogSnapshotRef

```text
catalog_id: str
catalog_version: str
catalog_content_hash: str
source_identity: str
schema_version: str
```

`CatalogSnapshotRef` is derived from each `CompleteDoublePipeCatalogSnapshot` and appears in `SizingRequestIdentity`. Caller-supplied full snapshots are the runtime input; refs are constructed from them. If both are caller-supplied, exact one-to-one equality is enforced.

### 4.3 CompleteDoublePipeCatalogSnapshot

```text
catalog_id: str
catalog_version: str
source_identity: str
schema_version: str
assembly_options: tuple[CompleteDoublePipeAssemblyOption, ...]
catalog_content_hash: str
```

`catalog_content_hash`: `sha256:...`. Computed via `sha256_digest()` over canonical JSON of all fields **except itself**. Field order: `catalog_id`, `catalog_version`, `source_identity`, `schema_version`, `assembly_options`. Assembly options sorted by `assembly_option_id` ASCII ascending after duplicate ID validation. JSON via `canonical_json()` — sorted keys, no whitespace, no trailing newline.

### 4.4 CompleteDoublePipeAssemblyOption

```text
assembly_option_id: str
inner_tube_inner_diameter_m: float
inner_tube_outer_diameter_m: float
outer_pipe_inner_diameter_m: float
wall_thermal_conductivity_w_m_k: float
inner_surface_roughness_m: float
annulus_surface_roughness_m: float
inner_fouling_resistance_m2k_w: float
outer_fouling_resistance_m2k_w: float
length_source: LengthSource
manufacturing_option_identity: str
manufacturing_metadata: tuple[tuple[str, str], ...]
```

Fouling resistances are physical design properties. They enter `SourceQualifiedCandidateIdentity` and the geometry passed to `rate_double_pipe()`.

`manufacturing_metadata`: input may be dict → stored as sorted `(key, value)` tuples — keys unique, keys ASCII ascending, values str. Deep-frozen on construction.

### 4.5 LengthSource (with Quantum)

Both modes carry `length_quantum_m`.

```text
class LengthSource:
    length_quantum_m: str
    # exactly one of the following:
    allowed_effective_lengths_m: tuple[float, ...] | None = None  # Mode A
    grid: LengthGridSpec | None = None                            # Mode B
```

No assembly option may provide both `allowed_effective_lengths_m` and `grid`.

### 4.6 LengthGridSpec

```text
class LengthGridSpec:
    minimum_length_m: float
    maximum_length_m: float
    increment_m: float
    endpoint_policy: LengthEndpointPolicy
```

`LengthEndpointPolicy`:

```text
class LengthEndpointPolicy(StrEnum):
    INCLUDE_MAX_IF_ALIGNED = "include_max_if_aligned"
    EXCLUDE_MAX = "exclude_max"
```

---

## 5. Length Quantum and Canonicalization

### 5.1 Power-of-10 Quantum

`length_quantum_m`: must be constructable as `Decimal`, finite, positive, and equal to `1E-N` where `N >= 0`.

Valid: `"1"`, `"0.1"`, `"0.01"`, `"0.001"`. Invalid: `"0.025"`, `"0.333"`, `"10"`, `"100"`.

```python
from decimal import Decimal
quantum = Decimal(length_quantum_m)
if not quantum.is_finite() or quantum <= 0:
    raise InvalidLengthQuantum()
norm = quantum.normalize()
# A power-of-10 canonic Decimal has exactly one digit (1) and exponent <= 0
digit_tuple = norm.as_tuple().digits
exponent = norm.as_tuple().exponent
if digit_tuple != (1,) or exponent > 0:
    raise InvalidLengthQuantum()
```

Freeze canonical quantum string: `str(quantum.normalize())` (e.g. `"0.001"` rather than `"0.0010"`). Use this canonical form in identity and hash payloads.

### 5.2 Integer Tick Conversion

```python
def to_tick(value_m: float | str | Decimal, quantum: Decimal) -> int:
    raw = Decimal(str(value_m))
    if not raw.is_finite() or raw <= 0:
        raise InvalidLengthError(...)   # structured, not assert
    if raw < quantum:
        raise InvalidLengthError(...)   # sub-quantum rejected before quantization
    qty = raw.quantize(quantum, rounding=ROUND_HALF_EVEN)
    tick = int((qty / quantum).to_integral_exact())
    if tick <= 0:
        raise InvalidLengthError(...)   # should not happen after < quantum guard
    return tick

def from_tick(tick: int, quantum: Decimal) -> Decimal:
    return Decimal(tick) * quantum
```

Output for identity/hash: canonical Decimal string — e.g. `"12.350"`.

### 5.3 Explicit Lengths Canonicalization

```python
quantum = Decimal(length_quantum_m)
ticks = sorted({to_tick(v, quantum) for v in allowed_effective_lengths_m})
canonical_lengths = [str(from_tick(t, quantum)) for t in ticks]
if not canonical_lengths:
    raise CatalogInvalid(...)
```

### 5.4 Grid Count-Only Algorithm (Pre-Cap)

```python
quantum = Decimal(length_quantum_m)
lo_tick = to_tick(minimum_length_m, quantum)
hi_tick = to_tick(maximum_length_m, quantum)

if hi_tick < lo_tick:
    raise CatalogInvalid(...)  # reversed grid — no delta, no divmod

raw_increment = Decimal(str(increment_m))
if not raw_increment.is_finite() or raw_increment <= 0:
    raise CatalogInvalid(...)
if raw_increment < quantum:
    raise CatalogInvalid(...)  # sub-quantum increment, even if quantization would round up

step_tick = to_tick(increment_m, quantum)
if step_tick <= 0:
    raise CatalogInvalid(...)

delta = hi_tick - lo_tick
quotient, remainder = divmod(delta, step_tick)
```

#### INCLUDE_MAX_IF_ALIGNED

```python
catalog_count = delta // step_tick + 1
```

Includes every point `lo_tick + i * step_tick <= hi_tick`. When aligned, `hi_tick` is included.

#### EXCLUDE_MAX

```python
catalog_count = delta // step_tick + 1
if remainder == 0:
    catalog_count -= 1
```

When `minimum_length_m == maximum_length_m`: `delta=0`, `catalog_count = 1 - 1 = 0`.

### 5.5 Request Bounds Intersection (Count-Only, Ceiling/Floor)

Request bounds **must not widen** the catalog interval. Convert min by ceiling (round up), max by floor (round down).

```python
request_min_tick: int | None = None
if minimum_effective_length_m is not None:
    raw = Decimal(str(minimum_effective_length_m))
    if not raw.is_finite() or raw <= 0:
        raise InvalidRequestBounds(...)
    qty = raw.quantize(quantum, rounding=ROUND_UP)
    request_min_tick = int((qty / quantum).to_integral_exact())

request_max_tick: int | None = None
if maximum_effective_length_m is not None:
    raw = Decimal(str(maximum_effective_length_m))
    if not raw.is_finite() or raw <= 0:
        raise InvalidRequestBounds(...)
    qty = raw.quantize(quantum, rounding=ROUND_DOWN)
    request_max_tick = int((qty / quantum).to_integral_exact())

first_idx = 0
if request_min_tick is not None:
    # ceil division: smallest i with lo + i*step >= request_min_tick
    first_idx = max(first_idx,
                    -((- (request_min_tick - lo_tick)) // step_tick))

last_idx = catalog_count - 1
if request_max_tick is not None:
    # floor division: largest i with lo + i*step <= request_max_tick
    last_idx = min(last_idx,
                   (request_max_tick - lo_tick) // step_tick)

intersection_count = max(0, last_idx - first_idx + 1)
```

### 5.6 Explicit-Length Request Intersection

```python
catalog_ticks = sorted({to_tick(v, quantum) for v in allowed_effective_lengths_m})
filtered_ticks = tuple(
    tick for tick in catalog_ticks
    if (request_min_tick is None or tick >= request_min_tick)
    and (request_max_tick is None or tick <= request_max_tick)
)
```

`raw_combination_count` contribution = `len(filtered_ticks)`.

### 5.7 Materialization (After Cap Passes)

```python
ticks = [lo_tick + step_tick * i for i in range(first_idx, last_idx + 1)]
canonical_lengths = [str(from_tick(t, quantum)) for t in ticks]
```

**Invariant:** `len(materialized_ticks) == intersection_count`.

### 5.8 Error-Code Mapping for Length/Quantum/Grid

| Condition | ErrorCode |
|-----------|-----------|
| Invalid quantum (non-1E-N, non-positive, non-finite) | `CATALOG_INVALID` |
| tick <= 0 after quantization | `CATALOG_INVALID` |
| hi_tick < lo_tick (reversed grid) | `CATALOG_INVALID` |
| raw_increment < quantum (sub-quantum) | `CATALOG_INVALID` |
| step_tick <= 0 | `CATALOG_INVALID` |
| Empty explicit lengths after canonicalization | `CATALOG_INVALID` |
| Explicit length value not finite / <= 0 | `CATALOG_INVALID` |
| Request bound not finite / <= 0 | `INVALID_SIZING_REQUEST` |
| Request min > max | `INVALID_SIZING_REQUEST` |

### 5.9 Pipeline Order

```text
 1. SizingRequest schema validation
 2. Catalog schema validation
 3. Duplicate assembly_option_id validation
 4. Duplicate catalog_id + catalog_version refs validation
 5. Catalog canonical hash verification
 6. Assembly option validation
 7. Length source validation and count-only request intersection
 8. raw_combination_count summation
 9. Hard/request cap check (before any materialization or rating)
10. Length materialization
11. Candidate identity materialization
12. Deduplication by SourceQualifiedCandidateIdentity
13. TASK-008 evaluation in canonical order
```

### 5.10 Cap

```text
HARD_RAW_COMBINATION_CAP = 10_000
request_raw_combination_cap (optional int, 1..HARD_RAW_COMBINATION_CAP, reject bool)
effective_cap = min(request_raw_combination_cap, HARD_RAW_COMBINATION_CAP)
```

Cap exceeded: `status=BLOCKED`, `raw=computed`, `unique=0`, `evaluated=0`, `selected=None`, `top_candidates=()`.

---

## 6. Candidate Identity

### 6.1 PhysicalCandidateIdentity

Pure geometry + length — no catalog source.

```text
inner_tube_inner_diameter_m
inner_tube_outer_diameter_m
outer_pipe_inner_diameter_m
effective_length_m_canonical: str
wall_thermal_conductivity_w_m_k
inner_surface_roughness_m
annulus_surface_roughness_m
inner_fouling_resistance_m2k_w
outer_fouling_resistance_m2k_w
```

### 6.2 SourceQualifiedCandidateIdentity

```text
physical_candidate_identity_digest: str
catalog_id: str
catalog_version: str
catalog_content_hash: str
assembly_option_id: str
manufacturing_option_identity: str
```

### 6.3 Deduplication

By `SourceQualifiedCandidateIdentity`. Different catalog or manufacturing option → distinct.

### 6.4 Canonical Evaluation Order

After deduplication, ascending `source_qualified_candidate_id` (ASCII string).

---

## 7. TASK-008 Exact Boundary

### 7.1 Exact Public Callable

```python
hexagent.exchangers.double_pipe.rating.rate_double_pipe(
    geometry=DoublePipeGeometry(...),
    hot_fluid=FluidIdentifier,
    cold_fluid=FluidIdentifier,
    hot_mass_flow_kg_s=float,
    cold_mass_flow_kg_s=float,
    hot_inlet_temperature_k=float,
    cold_inlet_temperature_k=float,
    hot_inlet_pressure_pa=float,
    cold_inlet_pressure_pa=float,
    tube_in_hot=bool,
    flow_arrangement=FlowArrangement,
    provider=PropertyProvider,
    solver_params=SolverParams,
    context=CalculationContext,
    minimum_terminal_delta_t=float,
    tube_boundary_condition=ThermalBoundaryCondition,
    annulus_boundary_condition=ThermalBoundaryCondition,
)
```

### 7.2 SolverParams (Exact Merged TASK-008 Fields)

`hexagent.exchangers.double_pipe.solver.SolverParams` has exactly four fields:

```text
absolute_residual_w: float
relative_residual_fraction: float
bracket_temperature_tolerance_k: float
max_iterations: int
```

Rating request fields in `SizingRequestIdentity` map to:

```python
SolverParams(
    absolute_residual_w=rating_solver_absolute_residual_w,
    relative_residual_fraction=rating_solver_relative_residual_fraction,
    bracket_temperature_tolerance_k=rating_solver_bracket_temperature_tolerance_k,
    max_iterations=rating_solver_max_iterations,
)
```

All params uniform across candidates in a single sizing run.

### 7.3 TASK-008 RatingRequestIdentity Boundary

Current merged `RatingRequestIdentity` contains:

- fluid identities (name + equation-of-state backend + normalized components)
- inlet temperatures and pressures
- hot and cold mass flow rates
- `DoublePipeGeometry` (including fouling)
- `FlowArrangement`
- `SolverParams` (4 fields)
- `minimum_terminal_delta_t`
- `tube_boundary_condition`, `annulus_boundary_condition`

Does **not** contain `tube_in_hot`. TASK-009 forwards `tube_in_hot` to `rate_double_pipe()` and binds it in `SizingRequestIdentity` / `CandidateEvaluationIdentity`, but the current TASK-008 `RatingRequestIdentity` does not include it. TASK-009 does not modify TASK-008's identity schema.

### 7.4 ProviderIdentitySnapshot

```text
name: str
version: str
git_revision: str
reference_state_policy: str
configuration_fingerprint: str
cache_policy_version: str
```

### 7.5 ExpectedProviderIdentity

```text
name: str
version: str
git_revision: str
reference_state_policy: str
configuration_fingerprint: str | None
cache_policy_version: str | None
```

### 7.6 Provider Identity Comparison Rules

1. `ExpectedProviderIdentity` is declared in `SizingRequestIdentity`.
2. Every TASK-008 call returns an actual `ProviderIdentitySnapshot`.
3. For each **verified** `RatingResult` (verify_hash + verify_provenance pass):
   - mandatory fields (name, version, git_revision, reference_state_policy) must match the expected identity; mismatch → BLOCKED with `PROPERTY_PROVIDER_IDENTITY_MISMATCH`.
   - optional expected fields (configuration_fingerprint, cache_policy_version), if not None, must match the actual snapshot.
4. Provider identity/configuration must be **consistent across all verified candidates** in a single sizing run. If any verified candidate's provider differs from another's → BLOCKED.
5. Identity data extracted from an integrity-invalid `RatingResult` is **claimed identity only** and must not be used as verified evidence for matching decisions.
6. If no verified candidate exists (all candidates are INTEGRITY_INVALID or RUNTIME_FAILED), the claimed identities are recorded but provider consistency cannot be enforced; the sizing run terminates via integrity/failure path.

### 7.7 Per-Candidate CalculationContext

Three fields:

```text
request_id: UUID | None
design_case_revision_id: UUID | None
calculation_run_id: UUID | None
```

Fixed namespace (frozen once, never changed):

```python
TASK009_CONTEXT_NAMESPACE = UUID("a0b1c2d3-e4f5-6789-abcd-ef0123456789")
```

Derivation rules:

- `design_case_revision_id`: preserved from caller input; `None` if not supplied.
- `calculation_run_id`: preserved from caller input; `None` if not supplied.
- `request_id`: derived deterministically per candidate UUID5:

```python
name = f"{sizing_request_identity_digest}:{source_qualified_candidate_id}"
request_id = uuid5(TASK009_CONTEXT_NAMESPACE, name)
```

No random UUIDs. No synthetic domain identities for missing design-case or run IDs.

### 7.8 ExecutionContextSnapshot

TASK-008 `RatingResult` preserves the exact `ExecutionContextSnapshot`:

```text
request_id: UUID | None
design_case_revision_id: UUID | None
calculation_run_id: UUID | None
```

TASK-009 verified evidence digest:

```python
rating_execution_context_digest = sha256_digest({
    "request_id": str(request_id) if request_id is not None else None,
    "design_case_revision_id": str(design_case_revision_id)
        if design_case_revision_id is not None else None,
    "calculation_run_id": str(calculation_run_id)
        if calculation_run_id is not None else None,
})
```

All three fields enter the verified evidence digest and JSON round-trip.

---

## 8. SizingRequestIdentity

```text
hot_fluid_name: str
cold_fluid_name: str
hot_fluid_equation_of_state: str
cold_fluid_equation_of_state: str
hot_fluid_normalized_components: tuple[tuple[str, float], ...]
cold_fluid_normalized_components: tuple[tuple[str, float], ...]
hot_inlet_temperature_k: float
cold_inlet_temperature_k: float
hot_inlet_pressure_pa: float
cold_inlet_pressure_pa: float
hot_mass_flow_kg_s: float
cold_mass_flow_kg_s: float
flow_arrangement: str
tube_in_hot: bool
tube_boundary_condition: str
annulus_boundary_condition: str
minimum_terminal_delta_t: float
required_duty_w: float
duty_absolute_tolerance_w: float
duty_relative_tolerance: float
optimization_objective: str
top_n: int
request_raw_combination_cap: int | None
catalog_snapshot_identities: tuple[CatalogSnapshotRef, ...]
minimum_effective_length_m: float | None
maximum_effective_length_m: float | None
rating_solver_absolute_residual_w: float
rating_solver_relative_residual_fraction: float
rating_solver_bracket_temperature_tolerance_k: float
rating_solver_max_iterations: int
expected_provider_identity: ExpectedProviderIdentity
design_case_revision_id: UUID | None
calculation_run_id: UUID | None
rating_software_version: str
execution_context_policy_version: str
```

`required_duty_w` is a sizing feasibility input only. It does **not** enter TASK-008 `RatingRequestIdentity` and must not derive `SolverParams`.

All digests computed via `sha256_digest()` (returns `sha256:<64hex>`).

---

## 9. Request Validation

| Field | Rule |
|-------|------|
| `required_duty_w` | finite, > 0 |
| `minimum_effective_length_m` | None or finite, > 0 |
| `maximum_effective_length_m` | None or finite, > 0; if both: min <= max |
| `top_n` | `type(value) is int`, `>= 1` — reject `bool` |
| `request_raw_combination_cap` | None → `HARD_RAW_COMBINATION_CAP`; else `type is int`, `1..HARD_RAW_COMBINATION_CAP` — reject `bool` |
| Duplicate catalog refs | No two refs share `(catalog_id, catalog_version)` |
| Provider identity | ExpectedProviderIdentity declared in `SizingRequestIdentity`. Each verified candidate's actual provider identity must match expected mandatory fields (name, version, git_revision, reference_state_policy). Optional fields (configuration_fingerprint, cache_policy_version) compared when not None. Provider must be consistent across all verified candidates. |

---

## 10. Duty Feasibility

### 10.1 Tolerance

```text
effective_duty_tolerance_w = max(duty_absolute_tolerance_w, duty_relative_tolerance * max(required_duty_w, 1.0))
```

Both tolerances: finite, `>= 0`.

### 10.2 Feasibility Condition

```text
rated_duty_w + effective_duty_tolerance_w >= required_duty_w
```

Feasibility may only be computed from a verified TASK-008 `SUCCEEDED` result with non-None `heat_duty_w`. Verified TASK-008 `BLOCKED` / `FAILED` results are non-feasible audit entries.

### 10.3 Derived Fields

```text
duty_margin_w = rated_duty_w - required_duty_w
duty_shortfall_w = max(-duty_margin_w, 0.0)
duty_overshoot_w = max(duty_margin_w, 0.0)
meets_target_without_tolerance = rated_duty_w >= required_duty_w
target_satisfaction_rank = 0 if meets_target_without_tolerance else 1
```

---

## 11. Optimization Objectives

### 11.1 Enum

```text
class OptimizationObjective(StrEnum):
    MINIMUM_OUTER_HEAT_TRANSFER_AREA = "minimum_outer_heat_transfer_area"
    MINIMUM_EFFECTIVE_LENGTH = "minimum_effective_length"
```

Area objective uses `RatingResult.area_outer_m2`.

### 11.2 Feasible Ranking (Target Satisfaction First)

#### MINIMUM_OUTER_HEAT_TRANSFER_AREA

```text
(
    target_satisfaction_rank,
    area_outer_m2,
    duty_shortfall_w,
    duty_overshoot_w,
    effective_length_m,
    source_qualified_candidate_id,
)
```

#### MINIMUM_EFFECTIVE_LENGTH

```text
(
    target_satisfaction_rank,
    effective_length_m,
    duty_shortfall_w,
    duty_overshoot_w,
    area_outer_m2,
    source_qualified_candidate_id,
)
```

All ascending. No weighted score. `selected_candidate == top_candidates[0]`.

---

## 12. SizingStatus and Invariants

```text
class SizingStatus(StrEnum):
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"
```

### 12.1 SUCCEEDED

- `>=1` feasible candidate
- `selected_candidate is not None`, `feasible is True`
- `top_candidates` non-empty
- `blockers` empty, `failure` empty
- `verify_hash()` True, `verify_provenance()` True

### 12.2 BLOCKED

Invalid request, invalid catalog, hash mismatch, cap exceeded, no manufacturable candidate, no feasible candidate, unsupported constraint, rating integrity failure, provider identity mismatch.

- `>=1` blocker, `selected_candidate is None`, `failure` empty

### 12.3 FAILED

Unexpected runtime. `failure is not None`, `selected_candidate is None`.

---

## 13. Top-N Contract

- `top_n <= feasible_candidate_count`: return top `top_n`
- `top_n > feasible_candidate_count > 0`: return all feasible + `TOP_N_REDUCED_TO_FEASIBLE_COUNT` warning
- `feasible_candidate_count == 0`: BLOCKED, `NO_FEASIBLE_CANDIDATE`

---

## 14. Candidate Evaluation States

```text
class CandidateEvaluationState(StrEnum):
    UNEVALUATED = "unevaluated"
    VERIFIED = "verified"
    INTEGRITY_INVALID = "integrity_invalid"
    RUNTIME_FAILED = "runtime_failed"
```

### 14.1 Evidence Invariants by State

| State | candidate_evaluation_identity | verified_rating_evidence | invalid_rating_evidence | evaluation_failure | feasible |
|-------|------------------------------|------------------------|------------------------|-------------------|----------|
| UNEVALUATED | None | None | None | None | False |
| VERIFIED | not None | not None | None | None | per duty check |
| INTEGRITY_INVALID | None | None | not None | None | False |
| RUNTIME_FAILED | None | None | None | not None | False |

**VERIFIED subtypes:**

| Subtype | feasible | feasibility_status | rating_status | duty fields |
|---------|----------|-------------------|---------------|-------------|
| VERIFIED+SUCCEEDED | per duty check | FEASIBLE or INFEASIBLE | SUCCEEDED | populated when heat_duty_w not None |
| VERIFIED+BLOCKED | False | RATING_BLOCKED | BLOCKED | all None |
| VERIFIED+FAILED | False | RATING_FAILED | FAILED | all None |
| VERIFIED+PROVIDER_IDENTITY_MISMATCH | False | PROVIDER_IDENTITY_MISMATCH | actual TASK-008 status | all None |

### 14.2 VerifiedRatingEvidenceSnapshot

Constructed only when `verify_hash() and verify_provenance() is True`.

```text
rating_status: RatingStatus
heat_duty_w: float | None
hot_outlet_temperature_k: float | None
cold_outlet_temperature_k: float | None
area_inner_m2: float
area_outer_m2: float
UA_w_k: float | None
LMTD_k: float | None
energy_residual_w: float | None
ua_lmtd_residual_w: float | None
tube_inlet_density_kg_m3: float | None
annulus_inlet_density_kg_m3: float | None
tube_flow_area_m2: float     (geometry-derived)
annulus_flow_area_m2: float  (geometry-derived)
warnings: tuple[EngineeringMessage, ...]
blockers: tuple[EngineeringMessage, ...]
failure: RunFailure | None
provider_identity: ProviderIdentitySnapshot
tube_correlation: SelectedCorrelationSnapshot | None
annulus_correlation: SelectedCorrelationSnapshot | None
rating_result_hash: str
rating_provenance_digest: str
hash_verification_outcome: VerificationOutcome
provenance_verification_outcome: VerificationOutcome
rating_request_identity: RatingRequestIdentity
rating_request_identity_digest: str
rating_execution_context: ExecutionContextSnapshot
rating_execution_context_digest: str
```

`SelectedCorrelationSnapshot` (TASK-008 exact type):

```text
correlation_id: str
version: str
definition_hash: str
source_title: str
source_authors: str
source_year: int
source_reference: str
source_verification_status: str
nusselt_basis: str
is_adaptation: bool
adaptation_limitation: str
```
### 14.3 InvalidRatingEvidenceRecord

```text
class VerificationOutcome(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
```

```text
InvalidRatingEvidenceRecord
- candidate_id: str
- claimed_rating_status: str | None
- claimed_result_hash: str | None
- claimed_provenance_digest: str | None
- hash_verification_outcome: VerificationOutcome
- provenance_verification_outcome: VerificationOutcome
- rating_request_identity_digest: str | None
- claimed_provider_identity: ProviderIdentitySnapshot | None
- failure_reason: str
```

Fields allowed to be None because a damaged or incomplete RatingResult may not provide all values. `claimed_provider_identity` is read from the unverified result's provider snapshot when safely readable; `None` when the field is damaged or unreadable.

`VerificationOutcome` replaces the old `verify_hash_result: bool` and `verify_provenance_result: bool`:

| Scenario | hash_verification_outcome | provenance_verification_outcome |
|----------|--------------------------|--------------------------------|
| verify_hash returns False | FAILED | NOT_RUN |
| verify_hash raises exception | ERROR | NOT_RUN |
| verify_hash PASSED, verify_provenance returns False | PASSED | FAILED |
| verify_hash PASSED, verify_provenance raises exception | PASSED | ERROR |
| Both PASSED | PASSED | PASSED |

| Scenario | CandidateEvaluationState | failure_stage |
|----------|-------------------------|---------------|
| hash FAILED or provenance FAILED | INTEGRITY_INVALID | None (blocked) |
| hash ERROR or provenance ERROR | RUNTIME_FAILED | RATING_VERIFICATION |

Error-path (hash or provenance raises exception) uses `RunFailure` and must NOT construct a trusted invalid evidence record. If a claimed audit record is desired, use a separate `CLAIMED_TASK008_RATING_RESULT` node, not the verified `InvalidRatingEvidenceRecord` digest path.

**Rules:**
1. `claimed_provider_identity` is **audit-only**.
2. It must NOT participate in: expected provider matching, verified provider consistency, feasibility, ranking, selected candidate selection, or verified evidence digest.
3. `claimed_provider_identity` enters the invalid evidence's own digest.
4. Verified and claimed provider evidence use **different field names** and different digest paths.
5. `claimed_rating_status` is the raw status string from the unverified `RatingResult`. It is audit-only.
6. `claimed_rating_status` must NOT be promoted to trusted `RatingStatus` in `CandidateEvaluation.rating_status`.
7. `CandidateEvaluation.rating_status` must be `None` for `INTEGRITY_INVALID` candidates.

Must not copy trusted thermal metrics from an unverified `RatingResult`.

### 14.4 InvalidEvidenceDigest

```python
invalid_evidence_digest = sha256_digest({
    "candidate_id": ...,
    "claimed_rating_status": ... | None,
    "claimed_result_hash": ... | None,
    "claimed_provenance_digest": ... | None,
    "hash_verification_outcome": hash_verification_outcome.value,
    "provenance_verification_outcome": provenance_verification_outcome.value,
    "rating_request_identity_digest": ... | None,
    "claimed_provider_identity_digest": ... | None,
    "failure_reason": ...,
})
```

- Explicit `None` values enter the payload.
- Does not depend on `claimed_result_hash` being present.
- Changing any claimed field changes the digest.
- The provenance node payload hash reuses this same payload.
- UUID5 name and node payload are both constructable even when result hash is damaged/unreadable.

### 14.5 ClaimedRatingResultAuditSnapshot

When verification raises an exception (not returns False), a `ClaimedRatingResultAuditSnapshot` is constructed instead of `InvalidRatingEvidenceRecord`. This provides deterministic audit evidence without trusting the unverified result.

```text
class ClaimedRatingResultState(StrEnum):
    HASH_VERIFICATION_ERROR = "hash_verification_error"
    PROVENANCE_VERIFICATION_ERROR = "provenance_verification_error"
    UNREADABLE = "unreadable"
```

```text
ClaimedRatingResultAuditSnapshot
- source_qualified_candidate_id: str
- evaluation_order_index: int
- claim_state: ClaimedRatingResultState
- claimed_rating_status: str | None
- claimed_result_hash: str | None
- claimed_provenance_digest: str | None
- claimed_request_identity_digest: str | None
- claimed_execution_context_digest: str | None
- claimed_provider_identity_digest: str | None
- hash_verification_outcome: VerificationOutcome
- provenance_verification_outcome: VerificationOutcome
- safely_readable_field_digests: tuple[tuple[str, str], ...]
- audit_digest: str
```

All unreadable fields must be explicitly `None`.

**safely_readable_field_digests whitelist:**

Only the following six real `RatingResult` public attributes may be read from the unverified result:

```text
status
result_hash
provenance_digest
request_identity
execution_context
provider_identity
```

Nonexistent digest attributes (`request_identity_digest`, `execution_context_digest`, `provider_identity_digest`) are prohibited — these are derived, not stored on `RatingResult`.

### 14.5.1 Safe extraction contract

Accepted source object:

```text
type(result) is RatingResult
```

Any other type yields `UNREADABLE`. Do not walk arbitrary attributes, inspect `__dict__`, call user methods, use aliases, invoke `repr`, inspect private fields, or traverse arbitrary descriptors. Each field read is independently wrapped in exception handling.

### 14.5.2 Exact conversions

**`status`:**

Available only when value is an exact `RatingStatus`.

```python
claimed_rating_status = status.value
safe_canonical_value = status.value
```

Otherwise unavailable.

**`result_hash`:**

Available only when value is `str`.

```python
claimed_result_hash = value
safe_canonical_value = value
```

Do not require its validity before retaining it as an audit claim.

**`provenance_digest`:**

Available only when value is `str`.

```python
claimed_provenance_digest = value
safe_canonical_value = value
```

**`request_identity`:**

Available only when value is an exact TASK-008 `RatingRequestIdentity`.

```python
safe_canonical_value = rating_request_identity_payload  # §14.7.1 exact 21-field payload
claimed_request_identity_digest = sha256_digest(
    rating_request_identity_payload
)
```

**`execution_context`:**

Available only when value is an exact `ExecutionContextSnapshot`.

```python
execution_context_payload = {
    "request_id":
        str(value.request_id) if value.request_id is not None else None,
    "design_case_revision_id":
        str(value.design_case_revision_id)
        if value.design_case_revision_id is not None
        else None,
    "calculation_run_id":
        str(value.calculation_run_id)
        if value.calculation_run_id is not None
        else None,
}
claimed_execution_context_digest = sha256_digest(
    execution_context_payload
)
safe_canonical_value = execution_context_payload
```

**`provider_identity`:**

Available only when value is an exact `ProviderIdentitySnapshot`.

```python
provider_identity_payload = {
    "name": value.name,
    "version": value.version,
    "git_revision": value.git_revision,
    "reference_state_policy": value.reference_state_policy,
    "configuration_fingerprint": value.configuration_fingerprint,
    "cache_policy_version": value.cache_policy_version,
}
claimed_provider_identity_digest = sha256_digest(
    provider_identity_payload
)
safe_canonical_value = provider_identity_payload
```

### 14.5.3 Field digest

Use the real public source field name:

```python
field_digest = sha256_digest({
    "field_name": field_name,
    "canonical_value": safe_canonical_value,
})
```

Store:

```text
tuple[(field_name, field_digest), ...]
```

sorted by ASCII `field_name`.

### 14.5.4 UNREADABLE

Set `claim_state = UNREADABLE` only when all six real `RatingResult` fields are unavailable.

Top-level claimed fields (`claimed_rating_status`, `claimed_result_hash`, `claimed_provenance_digest`, `claimed_request_identity_digest`, `claimed_execution_context_digest`, `claimed_provider_identity_digest`) and the per-field digests are independently retained. Explicit `None` remains in the audit payload.

**Digest payload:**

```python
claimed_audit_payload = {
    "source_qualified_candidate_id": ...,
    "evaluation_order_index": ...,
    "claim_state": claim_state.value,
    "claimed_rating_status": ...,
    "claimed_result_hash": ...,
    "claimed_provenance_digest": ...,
    "claimed_request_identity_digest": ...,
    "claimed_execution_context_digest": ...,
    "claimed_provider_identity_digest": ...,
    "hash_verification_outcome": hash_verification_outcome.value,
    "provenance_verification_outcome": provenance_verification_outcome.value,
    "safely_readable_field_digests": [...],
}
audit_digest = sha256_digest(claimed_audit_payload)
```

**safely_readable_field_digests:**
- Field names sorted ASCII ascending
- Field values safely canonicalized
- No trusted promotion of claimed data

**Storage:**
- `SizingOptimizationResult.claimed_rating_audits: tuple[ClaimedRatingResultAuditSnapshot, ...]`
- `SizingResultIdentity.claimed_rating_audit_digests: tuple[str, ...]`
- RATING_VERIFICATION exception: count = 1
- All other paths: count = 0

Sort key: `(source_qualified_candidate_id, evaluation_order_index, audit_digest)`.

**Provenance:** `CLAIMED_TASK008_RATING_RESULT` node UUID5 is always derived from audit digest:

```text
uuid5(TASK009_PROVENANCE_NAMESPACE,
    "claimed-rating-result:{source_qualified_candidate_id}:{evaluation_order_index}:{audit_digest}")
```

Payload hash: `sha256_digest(claimed_audit_payload)`.

### 14.6 Integrity-Failure Policy

Candidates evaluated in canonical order (§6.4, §18.1.5 strict pipeline). Each candidate's verification outcomes drive the next state:

**hash_verification_outcome == FAILED or provenance_verification_outcome == FAILED:**

1. Record `InvalidRatingEvidenceRecord` with the exact `VerificationOutcome` values
2. This candidate: `CandidateEvaluationState = INTEGRITY_INVALID`, counted in `evaluated_candidate_count`
3. **Stop immediately** — remaining candidates unevaluated
4. `status = BLOCKED`, `termination = "rating_result_integrity_failed"`
5. `selected_candidate = None`, `top_candidates = ()`, `partial_audit = attempted_rating_count < unique_candidate_count`
6. Evaluate `remaining_unevaluated_candidate_count = unique - evaluated`

**hash_verification_outcome == ERROR or provenance_verification_outcome == ERROR:**

1. `CandidateEvaluationState = RUNTIME_FAILED`
2. `failure_stage = RATING_VERIFICATION`
3. This candidate counted in `evaluated_candidate_count`
4. **Stop immediately** — remaining candidates unevaluated
5. `status = FAILED`, `failure = RunFailure`
6. `selected_candidate = None`, `top_candidates = ()`, `partial_audit = attempted_rating_count < unique_candidate_count`
7. Evaluate `remaining_unevaluated_candidate_count = unique - evaluated`

The error path does NOT construct a trusted `InvalidRatingEvidenceRecord` (the verification process failed, not the integrity check). If a claimed audit record is needed, use `CLAIMED_TASK008_RATING_RESULT` (§21.4 RATING_VERIFICATION).

### 14.6.1 Global enum serialization rule

Every `Enum`/`StrEnum` value entering an identity, evidence, audit, ranking, failure, result, provenance payload, UUID5 name component, or diagnostic key is serialized as `.value`.

This includes but is not limited to:

```text
RatingStatus
VerificationOutcome
ClaimedRatingResultState
CandidateEvaluationState
FeasibilityStatus
SizingStatus
FailureStage
ErrorCode / RawInputValidationCode
EngineeringMessageSeverity
flow_arrangement
boundary_condition enums
optimization_objective
endpoint_policy
```

For nullable enum fields:

```python
value.value if value is not None else None
```

Do not pass enum objects directly to any frozen exact payload.

### 14.7 VerifiedRatingEvidenceDigest

Exact 26-field deterministic digest payload for `VerifiedRatingEvidenceSnapshot`:

```python
verified_evidence_payload = {
    "rating_status": rating_status.value,
    "heat_duty_w": heat_duty_w,
    "hot_outlet_temperature_k": hot_outlet_temperature_k,
    "cold_outlet_temperature_k": cold_outlet_temperature_k,
    "area_inner_m2": area_inner_m2,
    "area_outer_m2": area_outer_m2,
    "UA_w_k": UA_w_k,
    "LMTD_k": LMTD_k,
    "energy_residual_w": energy_residual_w,
    "ua_lmtd_residual_w": ua_lmtd_residual_w,
    "tube_inlet_density_kg_m3": tube_inlet_density_kg_m3,
    "annulus_inlet_density_kg_m3": annulus_inlet_density_kg_m3,
    "tube_flow_area_m2": tube_flow_area_m2,
    "annulus_flow_area_m2": annulus_flow_area_m2,
    "warning_digests": [...],
    "blocker_digests": [...],
    "failure_digest": failure_digest_or_none,
    "provider_identity_digest": provider_identity_digest,
    "tube_correlation_digest": tube_correlation_digest_or_none,
    "annulus_correlation_digest": annulus_correlation_digest_or_none,
    "rating_result_hash": rating_result_hash,
    "rating_provenance_digest": rating_provenance_digest,
    "hash_verification_outcome": "passed",
    "provenance_verification_outcome": "passed",
    "rating_request_identity_digest": rating_request_identity_digest,
    "rating_execution_context_digest": rating_execution_context_digest,
}
verified_evidence_digest = sha256_digest(verified_evidence_payload)
```

Requirements:
- All nullable fields enter the payload explicitly
- warnings/blockers canonical sorted before digest
- `failure_digest` explicit None or digest string
- correlation snapshot None → digest None
- provider/request/context snapshots must be reconstructable from stored objects
- evidence snapshot JSON round-trip preserves identical digest
- Any evidence field tamper changes the digest
- This digest enters CandidateEvaluation, SizingResultIdentity, and failure audit records

### 14.7.1 Nested Identity Digests

Each nested type has an exact digest payload:

```python
# ProviderIdentitySnapshot
provider_identity_payload = {
    "name": ...,
    "version": ...,
    "git_revision": ...,
    "reference_state_policy": ...,
    "configuration_fingerprint": ...,
    "cache_policy_version": ...,
}
provider_identity_digest = sha256_digest(provider_identity_payload)
```

```python
# RatingRequestIdentity (TASK-008 exact 21-field payload)
rating_request_identity_payload = {
    "hot_fluid_name": snapshot.hot_fluid_name,
    "hot_fluid_backend": snapshot.hot_fluid_backend,
    "hot_fluid_components": snapshot.hot_fluid_components,
    "cold_fluid_name": snapshot.cold_fluid_name,
    "cold_fluid_backend": snapshot.cold_fluid_backend,
    "cold_fluid_components": snapshot.cold_fluid_components,
    "hot_mass_flow_kg_s": snapshot.hot_mass_flow_kg_s,
    "cold_mass_flow_kg_s": snapshot.cold_mass_flow_kg_s,
    "hot_inlet_pressure_pa": snapshot.hot_inlet_pressure_pa,
    "cold_inlet_pressure_pa": snapshot.cold_inlet_pressure_pa,
    "hot_inlet_temperature_k": snapshot.hot_inlet_temperature_k,
    "cold_inlet_temperature_k": snapshot.cold_inlet_temperature_k,
    "flow_arrangement": snapshot.flow_arrangement,
    "geometry": snapshot.geometry,
    "solver_absolute_residual_w": snapshot.solver_absolute_residual_w,
    "solver_relative_residual_fraction": snapshot.solver_relative_residual_fraction,
    "solver_bracket_temperature_tolerance_k":
        snapshot.solver_bracket_temperature_tolerance_k,
    "solver_max_iterations": snapshot.solver_max_iterations,
    "tube_boundary_condition": snapshot.tube_boundary_condition,
    "annulus_boundary_condition": snapshot.annulus_boundary_condition,
    "minimum_terminal_delta_t": snapshot.minimum_terminal_delta_t,
}
rating_request_identity_digest = sha256_digest(
    rating_request_identity_payload
)
```

Rules:
- No self-reference (no `rating_request_identity_digest` inside its own payload)
- No provider identity, execution context, candidate ID, or rating fields
- `geometry` is the actual stored TASK-008 geometry dictionary
- `flow_arrangement`, `tube_boundary_condition`, `annulus_boundary_condition`:
  TASK-008 `RatingRequestIdentity` already stores these as primitive strings.
  No additional `.value` conversion is performed.
- Equivalent `dataclasses.asdict(snapshot)` is allowed only if field keys exactly match the frozen list above
- Output uses `sha256:` prefix via repository `sha256_digest()`

```python
# ExecutionContextSnapshot
execution_context_payload = {
    "request_id": str(request_id) if request_id is not None else None,
    "design_case_revision_id": str(design_case_revision_id)
        if design_case_revision_id is not None else None,
    "calculation_run_id": str(calculation_run_id)
        if calculation_run_id is not None else None,
}
rating_execution_context_digest = sha256_digest(execution_context_payload)
```

```python
# SelectedCorrelationSnapshot
selected_correlation_payload = {
    "correlation_id": ...,
    "version": ...,
    "definition_hash": ...,
    "source_title": ...,
    "source_authors": ...,
    "source_year": ...,
    "source_reference": ...,
    "source_verification_status": ...,
    "nusselt_basis": ...,
    "is_adaptation": ...,
    "adaptation_limitation": ...,
}
selected_correlation_digest = sha256_digest(selected_correlation_payload)
```

### 14.7.2 Shared canonical context normalization (merged block)

All canonicalization types, constants, and functions in a single executable block:

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from inspect import getattr_static
import math
from typing import (
    Literal,
    Protocol,
    TypeAlias,
    cast,
)
from uuid import UUID

from pydantic import BaseModel


_MISSING_ATTRIBUTE = object()
RUN_FAILURE_SCHEMA_VERSION = "1"
CONTEXT_CANONICALIZATION_FAILURE_MESSAGE = "Trusted context canonicalization failed."
NON_STRING_CONTEXT_KEY_MARKER = "<non-string-context-key>"
NON_STRING_MAPPING_KEY_MARKER = "<non-string-mapping-key>"


CanonicalValue: TypeAlias = (
    None
    | bool
    | int
    | float
    | str
    | list["CanonicalValue"]
    | dict[str, "CanonicalValue"]
)


ContextCanonicalizationFailureKind: TypeAlias = Literal[
    "unsupported_type", "non_finite_float", "cyclic_reference",
    "naive_datetime", "non_string_key", "canonicalization_exception",
]


@dataclass(frozen=True, slots=True)
class ContextCanonicalizationErrorData:
    failure_kind: ContextCanonicalizationFailureKind
    context_key: str
    context_path: tuple[str, ...]
    offending_type: str


class ContextCanonicalizationError(ValueError):
    data: ContextCanonicalizationErrorData

    def __init__(
        self,
        failure_kind: ContextCanonicalizationFailureKind,
        context_key: str,
        context_path: tuple[str, ...],
        offending_type: str,
    ) -> None:
        self.data = ContextCanonicalizationErrorData(
            failure_kind=failure_kind,
            context_key=context_key,
            context_path=context_path,
            offending_type=offending_type,
        )
        super().__init__(failure_kind)


def qualified_type_name(value: object) -> str:
    return f"{type(value).__module__}.{type(value).__qualname__}"


@dataclass(frozen=True, slots=True)
class QuantityKindProtocol:
    value: str


@dataclass(frozen=True, slots=True)
class QuantitySIResultProtocol:
    value: object


class QuantityToSIProtocol(Protocol):
    def __call__(self) -> QuantitySIResultProtocol: ...


_REQUIRED_QUANTITY_ATTRIBUTES = (
    "value",
    "unit",
    "kind",
    "to_si",
)


def has_all_repository_quantity_attributes(value: object) -> bool:
    return all(
        getattr_static(value, attribute_name, _MISSING_ATTRIBUTE)
        is not _MISSING_ATTRIBUTE
        for attribute_name in _REQUIRED_QUANTITY_ATTRIBUTES
    )


@dataclass(frozen=True, slots=True)
class RepositoryQuantityAdapter:
    raw_value: object
    unit: object
    kind: QuantityKindProtocol | None
    to_si: QuantityToSIProtocol


def try_read_repository_quantity_adapter(
    value: object,
    *,
    context_key: str,
    context_path: tuple[str, ...],
) -> RepositoryQuantityAdapter | None:
    try:
        has_required_attributes = has_all_repository_quantity_attributes(value)
    except ContextCanonicalizationError:
        raise
    except Exception as exc:
        raise ContextCanonicalizationError(
            failure_kind="canonicalization_exception",
            context_key=context_key,
            context_path=context_path,
            offending_type=qualified_type_name(value),
        ) from exc
    if not has_required_attributes:
        return None
    try:
        raw_value = getattr(value, "value")
        unit = getattr(value, "unit")
        kind = getattr(value, "kind")
        to_si = getattr(value, "to_si")
    except ContextCanonicalizationError:
        raise
    except Exception as exc:
        raise ContextCanonicalizationError(
            failure_kind="canonicalization_exception",
            context_key=context_key,
            context_path=context_path,
            offending_type=qualified_type_name(value),
        ) from exc
    if not callable(to_si):
        return None
    typed_kind = cast(QuantityKindProtocol | None, kind)
    typed_to_si = cast(QuantityToSIProtocol, to_si)
    return RepositoryQuantityAdapter(
        raw_value=raw_value, unit=unit, kind=typed_kind, to_si=typed_to_si,
    )


@dataclass(frozen=True, slots=True)
class PydanticModelAdapter:
    model: BaseModel
    model_fields: Mapping[str, object]


def try_read_pydantic_model_adapter(
    value: object,
    *,
    context_key: str,
    context_path: tuple[str, ...],
) -> PydanticModelAdapter | None:
    if not isinstance(value, BaseModel):
        return None
    try:
        model_fields = type(value).model_fields
    except ContextCanonicalizationError:
        raise
    except Exception as exc:
        raise ContextCanonicalizationError(
            failure_kind="canonicalization_exception",
            context_key=context_key,
            context_path=context_path,
            offending_type=qualified_type_name(value),
        ) from exc
    if not isinstance(model_fields, Mapping):
        raise ContextCanonicalizationError(
            failure_kind="canonicalization_exception",
            context_key=context_key,
            context_path=context_path,
            offending_type=qualified_type_name(value),
        )
    return PydanticModelAdapter(
        model=value,
        model_fields=model_fields,
    )


def canonicalize_trusted_context_value(
    value: object,
    context_key: str,
    context_path: tuple[str, ...],
    ancestor_ids: frozenset[int],
) -> CanonicalValue:
    """Recursively canonicalize a trusted context value.

    Dispatch order:
      1. None
      2. Enum/StrEnum → .value then recurse
      3. UUID → str
      4. timezone-aware datetime
      5. bool
      6. int
      7. finite float
      8. str
      9. tuple/list → recursive
     10. Mapping → recursive (str keys only)
     11. repository Quantity-like (canonical.py)
     12. Pydantic model (canonical.py)
     13. Unsupported → raise
    """
    try:
        if value is None:
            return None

        # Cycle detection
        object_id = id(value)
        if object_id in ancestor_ids:
            raise ContextCanonicalizationError(
                failure_kind="cyclic_reference",
                context_key=context_key,
                context_path=context_path,
                offending_type=qualified_type_name(value),
            )

        # Enum → .value then recurse
        if isinstance(value, Enum):
            return canonicalize_trusted_context_value(
                value.value,
                context_key=context_key,
                context_path=context_path,
                ancestor_ids=ancestor_ids,
            )

        # UUID → str
        if isinstance(value, UUID):
            return str(value)

        # timezone-aware datetime
        if isinstance(value, datetime):
            try:
                offset = value.utcoffset()
            except ContextCanonicalizationError:
                raise
            except Exception as exc:
                raise ContextCanonicalizationError(
                    failure_kind="canonicalization_exception",
                    context_key=context_key,
                    context_path=context_path,
                    offending_type=qualified_type_name(value),
                ) from exc
            if value.tzinfo is None or offset is None:
                raise ContextCanonicalizationError(
                    failure_kind="naive_datetime",
                    context_key=context_key,
                    context_path=context_path,
                    offending_type=qualified_type_name(value),
                )
            try:
                utc_value = value.astimezone(UTC)
            except ContextCanonicalizationError:
                raise
            except Exception as exc:
                raise ContextCanonicalizationError(
                    failure_kind="canonicalization_exception",
                    context_key=context_key,
                    context_path=context_path,
                    offending_type=qualified_type_name(value),
                ) from exc
            return utc_value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # bool (must be before int)
        if isinstance(value, bool):
            return value

        # int
        if isinstance(value, int):
            return value

        # finite float
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ContextCanonicalizationError(
                    failure_kind="non_finite_float",
                    context_key=context_key,
                    context_path=context_path,
                    offending_type=qualified_type_name(value),
                )
            return value

        # str
        if isinstance(value, str):
            return value

        # tuple/list → recursive
        if isinstance(value, (tuple, list)):
            updated_ancestors = ancestor_ids | {id(value)}
            result: list[CanonicalValue] = []
            for index, item in enumerate(value):
                result.append(canonicalize_trusted_context_value(
                    item, context_key=context_key,
                    context_path=context_path + (f"[{index}]",),
                    ancestor_ids=updated_ancestors,
                ))
            return result

        # Mapping → recursive (str keys only)
        if isinstance(value, Mapping):
            try:
                items = value.items()
                updated_ancestors = ancestor_ids | {id(value)}
                result: dict[str, CanonicalValue] = {}
                for key, item in items:
                    if type(key) is not str:
                        raise ContextCanonicalizationError(
                            failure_kind="non_string_key",
                            context_key=context_key,
                            context_path=context_path + (NON_STRING_MAPPING_KEY_MARKER,),
                            offending_type=qualified_type_name(key),
                        )
                    child_path = context_path + (key,)
                    result[key] = canonicalize_trusted_context_value(
                        item,
                        context_key=context_key,
                        context_path=child_path,
                        ancestor_ids=updated_ancestors,
                    )
                return result
            except ContextCanonicalizationError:
                raise
            except Exception as exc:
                raise ContextCanonicalizationError(
                    failure_kind="canonicalization_exception",
                    context_key=context_key,
                    context_path=context_path,
                    offending_type=qualified_type_name(value),
                ) from exc

        # repository Quantity-like (canonical.py)
        adapter = try_read_repository_quantity_adapter(
            value, context_key=context_key, context_path=context_path,
        )
        if adapter is not None:
            try:
                si_value = adapter.raw_value
                if adapter.kind is not None:
                    si_value = adapter.to_si().value
                return {
                    "si_value": canonicalize_trusted_context_value(
                        si_value, context_key=context_key,
                        context_path=context_path + ("si_value",),
                        ancestor_ids=ancestor_ids,
                    ),
                    "kind": (
                        adapter.kind.value
                        if adapter.kind is not None
                        else None
                    ),
                }
            except ContextCanonicalizationError:
                raise
            except Exception as exc:
                raise ContextCanonicalizationError(
                    failure_kind="canonicalization_exception",
                    context_key=context_key, context_path=context_path,
                    offending_type=qualified_type_name(value),
                ) from exc

        # Pydantic model - field-level traversal
        pydantic_adapter = try_read_pydantic_model_adapter(
            value, context_key=context_key, context_path=context_path,
        )
        if pydantic_adapter is not None:
            updated_ancestors = ancestor_ids | {id(value)}
            result: dict[str, CanonicalValue] = {}
            for field_name in pydantic_adapter.model_fields:
                try:
                    field_value = getattr(
                        pydantic_adapter.model, field_name,
                    )
                except ContextCanonicalizationError:
                    raise
                except Exception as exc:
                    raise ContextCanonicalizationError(
                        failure_kind="canonicalization_exception",
                        context_key=context_key,
                        context_path=context_path + (field_name,),
                        offending_type=qualified_type_name(value),
                    ) from exc
                result[field_name] = canonicalize_trusted_context_value(
                    field_value, context_key=context_key,
                    context_path=context_path + (field_name,),
                    ancestor_ids=updated_ancestors,
                )
            return result

        raise ContextCanonicalizationError(
            failure_kind="unsupported_type",
            context_key=context_key,
            context_path=context_path,
            offending_type=qualified_type_name(value),
        )
    except ContextCanonicalizationError:
        raise
    except Exception as exc:
        raise ContextCanonicalizationError(
            failure_kind="canonicalization_exception",
            context_key=context_key,
            context_path=context_path,
            offending_type=qualified_type_name(value),
        ) from exc


@dataclass(frozen=True, slots=True)
class CanonicalContextEntry:
    key: str
    value: CanonicalValue
    value_digest: str


def build_canonical_context_entries(
    context: tuple[tuple[str, object], ...],
) -> tuple[CanonicalContextEntry, ...]:
    """Canonicalize context entries for EngineeringMessage and RunFailure.

    Each (key, value) pair is canonicalized via canonicalize_trusted_context_value(),
    its value_digest computed, and the result sorted by (key, value_digest).
    Duplicate entries are preserved.
    """
    entries: list[CanonicalContextEntry] = []
    for key, value in context:
        if type(key) is not str:
            raise ContextCanonicalizationError(
                failure_kind="non_string_key",
                context_key=NON_STRING_CONTEXT_KEY_MARKER,
                context_path=(),
                offending_type=qualified_type_name(key),
            )
        canonical_value = canonicalize_trusted_context_value(
            value,
            context_key=key,
            context_path=(),
            ancestor_ids=frozenset(),
        )
        value_digest = sha256_digest({"value": canonical_value})
        entries.append(CanonicalContextEntry(
            key=key,
            value=canonical_value,
            value_digest=value_digest,
        ))
    entries.sort(key=lambda e: (e.key, e.value_digest))
    return tuple(entries)


def build_run_failure_payload(failure: RunFailure) -> CanonicalPayload:
    entries = build_canonical_context_entries(failure.context)
    return {
        "schema_version": failure.schema_version,
        "code": failure.code.value,
        "message": failure.message,
        "traceback": failure.traceback,
        "context_entries": [
            {"key": entry.key, "value": entry.value, "value_digest": entry.value_digest}
            for entry in entries
        ],
    }


def digest_run_failure(failure: RunFailure) -> str:
    return sha256_digest(build_run_failure_payload(failure))


def build_context_canonicalization_fallback(
    *, failure_stage: FailureStage, owner_kind: MessageOwnerKind,
    owner_id: str, original_code: ErrorCode,
    error: ContextCanonicalizationError,
) -> RunFailure:
    safe_marker_payload = {
        "context_key": error.data.context_key,
        "context_path": list(error.data.context_path),
        "offending_type": error.data.offending_type,
        "failure_kind": error.data.failure_kind,
    }
    safe_marker_digest = sha256_digest(safe_marker_payload)
    fallback_failure_context = (
        ("failure_stage", failure_stage.value),
        ("owner_kind", owner_kind.value),
        ("owner_id", owner_id),
        ("original_code", original_code.value),
        ("context_key", error.data.context_key),
        ("context_path_digest", sha256_digest({"context_path": list(error.data.context_path)})),
        ("offending_type", error.data.offending_type),
        ("failure_kind", error.data.failure_kind),
        ("safe_marker_digest", safe_marker_digest),
    )
    return RunFailure(
        schema_version=RUN_FAILURE_SCHEMA_VERSION,
        code=ErrorCode.PROVENANCE_INCOMPLETE,
        message=CONTEXT_CANONICALIZATION_FAILURE_MESSAGE,
        traceback=None,
        context=fallback_failure_context,
    )
```

Usage:

```python
canonical_context_entries = build_canonical_context_entries(context)
context_digest = sha256_digest({
    "entries": [
        {"key": entry.key, "value": entry.value, "value_digest": entry.value_digest}
        for entry in canonical_context_entries
    ],
})
```

### 14.7.3 EngineeringMessage exact payload

```python
engineering_message_payload = {
    "schema_version": message.schema_version,
    "code": message.code.value,
    "severity": message.severity.value,
    "message": message.message,
    "source_module": message.source_module,
    "affected_paths": list(message.affected_paths),
    "context_entries": [
        {"key": entry.key, "value": entry.value, "value_digest": entry.value_digest}
        for entry in canonical_context_entries
    ],
}
engineering_message_digest = sha256_digest(
    engineering_message_payload
)
```

`allows_continuation` is excluded from the digest because it is derived from severity. Before digesting, verify:

```text
INFO/WARNING  → allows_continuation == True
ERROR/BLOCKER → allows_continuation == False
```

A mismatch is an invalid shared message object and must not be silently hashed.

### 14.7.4 RunFailure exact payload

Shared digest functions, usable from every failure path without import ambiguity (definitions in §14.7.2 merged block):

```python
run_failure_payload = build_run_failure_payload(failure)
run_failure_digest = digest_run_failure(failure)
```

Rules:
- Nullable `traceback` enters the payload explicitly as `None`.
- `failure_stage`, `candidate_id`, and `evaluation_order_index` remain entries inside `RunFailure.context`; they do not replace `code`, `message`, `traceback`, or `schema_version`.

### 14.7.5 Explicit None handling

Nullable fields enter the payload as `None` (not omitted).
All computed via the standard `sha256_digest(payload)` contract — single call, `canonical_json` handled internally.

### 14.7.6 Trusted context fail-closed canonicalization

`EngineeringMessage.context` and `RunFailure.context` are `tuple[tuple[str, Any], ...]`. Their value records must be safely canonicalized before entering the digest.

Allowed types (trusted canonical JSON domain):

```text
None
bool
int
finite float
str
Enum / StrEnum (→ `.value`)
UUID
datetime with timezone
tuple / list  (recursive)
dict[str, supported value]  (recursive, string keys only)
Mapping (dict, MappingProxyType, etc.)
repository Quantity-like object (supported by canonical.py)
Pydantic model (supported by canonical.py)
```

Before digesting each value, use `canonicalize_trusted_context_value()` which handles the full dispatch order and raises `ContextCanonicalizationError` on failure.

If `canonicalize_trusted_context_value()` fails (unsupported type, non-finite float, cyclic reference, naive datetime, non-string mapping key, canonicalization exception):

- During candidate evidence construction: terminate with `RUNTIME_FAILED`, `failure_stage = RATING_VERIFICATION`, `RunFailure` code `PROVENANCE_INCOMPLETE`.
- During result/failure-result construction: terminate through RESULT_CONSTRUCTION failure contract.
- Do not silently skip, `repr()`, stringify, or fall back to a non-deterministic marker.
- Do not let the implementation choose the handling strategy at runtime.

### 14.7.7 ContextCanonicalizationFailureSnapshot

When trusted context canonicalization fails, a primitive-only `ContextCanonicalizationFailureSnapshot` is constructed.

```text
ContextCanonicalizationFailureSnapshot
- failure_stage: FailureStage
- owner_kind: MessageOwnerKind
- owner_id: str
- original_code_value: str
- context_key: str
- context_path: tuple[str, ...]
- offending_type: str
- failure_kind: str
- safe_marker_digest: str
```

Exact safe marker payload (built from error data, not the original value):

```python
safe_marker_payload = {
    "context_key": error.data.context_key,
    "context_path": list(error.data.context_path),
    "offending_type": error.data.offending_type,
    "failure_kind": error.data.failure_kind,
}
safe_marker_digest = sha256_digest(safe_marker_payload)
```

`failure_kind` values: `unsupported_type`, `non_finite_float`, `cyclic_reference`, `naive_datetime`, `non_string_key`, `canonicalization_exception` (definition in §14.7.2 merged block).

This is the **single path** for constructing a RunFailure from a canonicalization failure. There is no alternative code path, no conditional marker, no fallback within the fallback.

All-stage mapping (failure_stage depends on where canonicalization occurs):

| Pipeline Stage | Where context canonicalization can fail |
|---------------|--------------------------------------|
| REQUEST_VALIDATION | request message context |
| CATALOG_VALIDATION | catalog message context |
| CANDIDATE_MATERIALIZATION | diagnostic context |
| PRE_RATING | evidence preparation context |
| RATING_CALL | TASK-008 call message context |
| RATING_VERIFICATION | rating evidence/message context |
| OPTIMIZATION | optimizer message context |
| RESULT_CONSTRUCTION | result/failure-result context |

Non-recursive proof:
- `fallback_failure_context` domain = `tuple[tuple[str, str], ...]`
- `canonical_json(fallback failure payload)` succeeds without reading `unsupported_value` again
- The entry domain is guaranteed primitive by the construction contract above.
- To avoid cascading failure, the RunFailure context entry is constructed without attempting to canonicalize the unsupported value; the context path digest, failure kind, and safe marker digest provide traceability without risking a second canonicalization failure.

---

## 15. CandidateEvaluation

```text
source_qualified_candidate_identity: SourceQualifiedCandidateIdentity
candidate_evaluation_state: CandidateEvaluationState
candidate_evaluation_identity: CandidateEvaluationIdentity | None
evaluation_order_index: int
rating_status: RatingStatus | None     # TASK-008 RatingStatus; None for UNEVALUATED/RUNTIME_FAILED/INTEGRITY_INVALID
feasibility_status: FeasibilityStatus  # always populated (UNEVALUATED for unevaluated)
feasible: bool
verified_rating_evidence: VerifiedRatingEvidenceSnapshot | None
invalid_rating_evidence: InvalidRatingEvidenceRecord | None
evaluation_failure: RunFailure | None
diagnostics: tuple[CandidateDiagnosticKey, ...]
primary_diagnostic: CandidateDiagnosticKey | None
duty_margin_w: float | None
duty_shortfall_w: float | None
duty_overshoot_w: float | None
meets_target_without_tolerance: bool | None
```

### 15.1 CandidateEvaluation Digest

Unified digest across all evaluation states:

```python
def candidate_diagnostic_sort_key(diagnostic: CandidateDiagnosticKey):
    return (
        int(diagnostic.diagnostic_class_rank),
        diagnostic.code.value,
        diagnostic.source_module,
        diagnostic.affected_paths,
        diagnostic.message,
    )


def build_diagnostic_payload(diagnostic: CandidateDiagnosticKey) -> CanonicalPayload:
    return {
        "diagnostic_class_rank": int(diagnostic.diagnostic_class_rank),
        "code": diagnostic.code.value,
        "source_module": diagnostic.source_module,
        "affected_paths": list(diagnostic.affected_paths),
        "message": diagnostic.message,
    }


def build_diagnostic_digest(diagnostic: CandidateDiagnosticKey) -> str:
    return sha256_digest(build_diagnostic_payload(diagnostic))


def build_candidate_evaluation_payload(
    evaluation: CandidateEvaluation,
) -> CanonicalPayload:
    return {
        "source_qualified_candidate_identity_digest": evaluation.source_qualified_candidate_identity.identity_digest,
        "candidate_evaluation_state": evaluation.candidate_evaluation_state.value,
        "candidate_evaluation_identity_digest": evaluation.candidate_evaluation_identity.identity_digest if evaluation.candidate_evaluation_identity is not None else None,
        "evaluation_order_index": evaluation.evaluation_order_index,
        "rating_status": evaluation.rating_status.value if evaluation.rating_status is not None else None,
        "feasibility_status": evaluation.feasibility_status.value,
        "feasible": evaluation.feasible,
        "verified_rating_evidence_digest": evaluation.verified_rating_evidence.evidence_digest if evaluation.verified_rating_evidence is not None else None,
        "invalid_rating_evidence_digest": evaluation.invalid_rating_evidence.invalid_evidence_digest if evaluation.invalid_rating_evidence is not None else None,
        "evaluation_failure_digest": digest_run_failure(evaluation.evaluation_failure) if evaluation.evaluation_failure is not None else None,
        "diagnostic_digests": [build_diagnostic_digest(d) for d in evaluation.diagnostics] if evaluation.diagnostics else [],
        "primary_diagnostic_digest": build_diagnostic_digest(evaluation.primary_diagnostic) if evaluation.primary_diagnostic is not None else None,
        "duty_margin_w": evaluation.duty_margin_w,
        "duty_shortfall_w": evaluation.duty_shortfall_w,
        "duty_overshoot_w": evaluation.duty_overshoot_w,
        "meets_target_without_tolerance": evaluation.meets_target_without_tolerance,
    }

candidate_evaluation_digest = sha256_digest(build_candidate_evaluation_payload(evaluation))
```

Invariants by state:

| State | candidate_evaluation_identity | verified_evidence | invalid_evidence | evaluation_failure | feasible | rating_status | duty fields | diagnostics |
|-------|------------------------------|------------------|-----------------|-------------------|----------|---------------|-------------|-------------|
| VERIFIED + SUCCEEDED | not None | not None (duty fields populated) | None | None | per duty check | SUCCEEDED | populated (float, not None, feasible determination) | allowed |
| VERIFIED + BLOCKED | not None | not None | None | None | False | BLOCKED | all None | allowed |
| VERIFIED + FAILED | not None | not None | None | None | False | FAILED | all None | allowed |
| VERIFIED + PROVIDER_IDENTITY_MISMATCH | not None | not None | None | None | False | actual TASK-008 status | all None | allowed |
| INTEGRITY_INVALID | None | None | not None | None | False | None | all None | allowed |
| RUNTIME_FAILED | None | None | None | not None | False | None | all None | allowed |
| UNEVALUATED | None | None | None | None | False | None | all None | allowed |

When `rating_status == SUCCEEDED` and `heat_duty_w is not None`:

```text
duty_margin_w: float
duty_shortfall_w: float
duty_overshoot_w: float
meets_target_without_tolerance: bool
feasibility_status: FEASIBLE | INFEASIBLE
tube_correlation != None
annulus_correlation != None
```

When `rating_status in (BLOCKED, FAILED)` or `heat_duty_w is None`:

```text
duty_margin_w = None
duty_shortfall_w = None
duty_overshoot_w = None
meets_target_without_tolerance = None
feasibility_status = RATING_BLOCKED (if BLOCKED) or RATING_FAILED (if FAILED)
```

### 15.2 Provider mismatch sizing-feasibility precedence

Provider mismatch overrides all other feasibility derivation. The candidate retains `VERIFIED` state with actual `rating_status`, but sizing-feasibility fields follow a strict ordered decision tree:

```text
Step 1: Provider identity mismatch?
  → feasibility_status = PROVIDER_IDENTITY_MISMATCH
  → feasible = False
  → duty_margin_w = None, duty_shortfall_w = None,
    duty_overshoot_w = None, meets_target_without_tolerance = None
  → Stop sizing-feasibility derivation for this candidate

Step 2: Else rating_status == SUCCEEDED and heat_duty_w is not None?
  → Derive FEASIBLE / INFEASIBLE and duty fields per §15 duty check

Step 3: Else rating_status == BLOCKED?
  → feasibility_status = RATING_BLOCKED
  → All duty fields = None

Step 4: Else rating_status == FAILED?
  → feasibility_status = RATING_FAILED
  → All duty fields = None
```

Provider mismatch candidate invariants:

```text
candidate_evaluation_state = VERIFIED
rating_status = actual TASK-008 RatingStatus (SUCCEEDED/BLOCKED/FAILED)
verified_rating_evidence != None
candidate_evaluation_identity != None
```

---

## 16. CandidateEvaluationIdentity

```python
{
    "source_qualified_candidate_identity_digest": ...,
    "sizing_request_identity_digest": ...,
    "rating_request_identity_digest": ...,
    "provider_identity_digest": ...,
    "execution_context_identity_digest": ...,
    "rating_result_hash": ...,
    "rating_provenance_digest": ...,
}
```

Computed via `sha256_digest(payload)`. All values are `sha256:...`.

---

## 17. CandidateRankingRecord

```text
source_qualified_candidate_id: str
objective: str
sort_key: tuple  # serialized as canonical JSON array — supports nesting (e.g. affected_paths)
rank: int
feasible: bool
```

`sort_key` is the full comparison tuple serialized as a JSON array via `canonical_json`. For non-feasible sort key containing `affected_paths` (a tuple of strings), the nested tuple becomes a JSON array of strings.

---

## 18. SizingResultIdentity

### 18.1 Raw Input Canonicalization Contract

#### 18.1.1 canonicalize_raw_input

```text
canonicalize_raw_input(value, seen_object_ids=()) -> RawCanonicalizationResult
```

Recursive value canonicalization for safe JSON-round-trippable representation of raw sizing request inputs, including non-finite floats, unsupported types, non-string mapping keys, and cyclic containers.

**Return type:**

```text
RawCanonicalizationResult
- canonical_value: CanonicalRawValue
- validation_errors: tuple[SizingValidationErrorSnapshot, ...]
```

Raw canonicalization never raises an exception for unsupported input structure. Validation errors are returned alongside the safe canonical value, not as Python exceptions.

**Supported types and representations:**

| Input | Output |
|-------|--------|
| `None` | `None` |
| `bool` | `bool` |
| `int` | `int` |
| finite `float` | original value |
| `NaN` | `{"$non_finite_float": "nan"}` |
| `+Infinity` | `{"$non_finite_float": "+infinity"}` |
| `-Infinity` | `{"$non_finite_float": "-infinity"}` |
| `str` | `str` |
| `Enum` | `.value` |
| `UUID` | canonical lowercase string |
| `tuple` | ordered JSON array |
| `list` | ordered JSON array |
| `dict` | string-key-sorted JSON object |

**Non-string mapping keys:** `dict` keys that are not `str` produce a deterministic ordered entry list with type-sensitive key representation. Each entry independently preserves its key-value association.

The canonicalizer distinguishes several key types defined by `CanonicalRawKey`:

```text
CanonicalRawKey =
    CanonicalStringKey
  | CanonicalBoolKey
  | CanonicalIntKey
  | CanonicalFiniteFloatKey
  | CanonicalNonFiniteFloatKey
  | CanonicalUUIDKey
  | CanonicalEnumKey
  | CanonicalOpaqueKey
```

**String key:**

```python
{"key_kind": "string", "value": original_string}
```

**Bool key (checked before int to avoid Python bool-is-int overlap):**

```python
{"key_kind": "bool", "value": true | false}
```

**Int key:**

```python
{"key_kind": "int", "value": str(integer_value)}
```

**Finite float key (handled in §dispatch order):** replaced by the definition below.

**Non-finite float key:**

```python
{"key_kind": "non_finite_float", "value": "nan" | "+infinity" | "-infinity"}
```

**UUID key:**

```python
{"key_kind": "uuid", "value": canonical_lowercase_uuid_string}
```

**Enum key:**

```python
enum_value_result = canonicalize_raw_input(enum.value)
key_payload = {
    "key_kind": "enum",
    "enum_type": f"{type(key).__module__}.{type(key).__qualname__}",
    "value": enum_value_result.canonical_value,
}
nested_validation_errors.extend(enum_value_result.validation_errors)
```

**Opaque unsupported object key** (not readable or serializable):

```python
{"key_kind": "opaque_unsupported", "key_type": "<module>.<qualname>"}
```

Rules:
- No `repr()`, no object attributes, no memory address, no process-local identity.
- Do not claim injective/discriminative representation for opaque objects of the same type.
- Each opaque key generates a `UNSUPPORTED_RAW_MAPPING_KEY` validation error.
- Entry count and value are preserved; the representation is deterministic but NOT reversible.

**Dispatch order (frozen, must check in this sequence):**

```text
1. Enum (including StrEnum, IntEnum — checked before str/int to preserve type)
2. UUID
3. str
4. bool (checked before int to avoid Python bool-is-int)
5. int
6. float
7. tuple/list
8. Mapping:
   - string-key-only mapping → canonical sorted JSON object
   - mapping containing any non-string key → `$mapping_entries` representation
9. opaque unsupported (catch-all for arbitrary unrecognized objects)
```

**Mapping collision scope:**

```text
TASK-009 canonicalizes only entries actually visible in the Mapping at call time.
Python pre-collision on equivalent keys (e.g. True/1/1.0) occurs during dict
construction and is NOT recoverable by TASK-009. Tests must use custom Mapping
types or separate dict instances to verify dispatch correctness — not a single
built-in dict with pre-collided equivalent keys.
```

**Finite float key value type:**

```python
{
    "key_kind": "finite_float",
    "value": float_value
}
```

The value is the Python float, not a JSON string. In JSON, `value` is serialized via `canonical_json(float_value)`.

**$mapping_entries schema:**

Each entry carries canonical key payload, key digest, value, and value digest:

```text
{
  "$mapping_entries": [
    {
      "key": <CanonicalRawKey>,
      "key_payload_digest": "sha256:<64hex>",
      "value": <CanonicalRawValue>,
      "value_digest": "sha256:<64hex>"
    }
  ]
}
```

Where:

```python
key_payload_digest = sha256_digest(key_payload)    # full CanonicalRawKey dict
value_digest = sha256_digest({"value": canonical_value})
```

**Sort order (immutable rank, then digest-based tiebreak):**

```text
string           key_kind_rank = 0  sort: (0, key_payload_digest, value_digest)
bool             key_kind_rank = 1  sort: (1, key_payload_digest, value_digest)
int              key_kind_rank = 2  sort: (2, key_payload_digest, value_digest)
finite_float     key_kind_rank = 3  sort: (3, key_payload_digest, value_digest)
non_finite_float key_kind_rank = 4  sort: (4, key_payload_digest, value_digest)
uuid             key_kind_rank = 5  sort: (5, key_payload_digest, value_digest)
enum             key_kind_rank = 6  sort: (6, key_payload_digest, value_digest)
opaque_unsupported key_kind_rank = 7  sort: (7, key_payload_digest, value_digest)
```

This ensures same input with different insertion order produces identical canonical output. Duplicate canonical entries (same key_payload_digest + value_digest) are retained in the list — duplicate count enters the snapshot.

**Validation error field path for mapping entries:**

```text
("$mapping_entries", key_payload_digest [, str(occurrence_index)])
```

Where `occurrence_index` is a 0-based consecutive count within identical (key_payload_digest, value_digest) groups after sorting. This avoids the pre-sort entry-index circular dependency.

Rules:
- Every original mapping entry is independently preserved — nothing collapsed or discarded.
- Must not silently convert via `str(key)` (key collision risk).
- Must not call arbitrary `repr()`.
- Must not raise any exception (would lose snapshot).
- A `SizingValidationErrorSnapshot` with code `NON_STRING_MAPPING_KEY` is added per non-string-key entry.
- A `SizingValidationErrorSnapshot` with code `UNSUPPORTED_RAW_MAPPING_KEY` is added per opaque-key entry.
- Validation error field path uses the frozen `(key_payload_digest, occurrence_index)` after sorting — no pre-sort dependence.

**Unsupported arbitrary objects:** Represent safely using type metadata only:

```text
{"$unsupported_type": "<module>.<qualname>"}
```

Where `module` and `qualname` are the object's type metadata.

Rules:
- No `__repr__`, no memory address, no process-local state, no object attribute reads.
- The marker enters `canonical_raw_input`.
- A `SizingValidationErrorSnapshot` with code `UNSUPPORTED_RAW_INPUT_TYPE` is added to `validation_errors`.
- Unsupported objects never enter valid `SizingRequestIdentity`.

**Cyclic reference detection:** Use object-id recursion stack. Always use the single deterministic, index-independent marker:

```text
{"$cyclic_reference": {"ancestor_distance": <positive integer>}}
```

Where `ancestor_distance` is the number of frames between the current recursion-stack frame and the frame where the same container was first entered. The first entry into a container records its object identity; re-encountering the same identity computes `distance = stack_depth - first_seen_depth`.

Rules:
- The marker is independent of final mapping entry index, insertion order, and value digest.
- No path-based syntax (`$`, `$.field`, `$[index]`) — avoids circular dependency between path computation and entry sorting.
- All container types (tuple, list, dict, mapping-entry list) use the same marker.
- Repeated runs on the same input produce identical `ancestor_distance` values.
- No alternate path expression, no exception, no blocker fallback.

#### 18.1.2 Invalid request construction order

```text
1. canonicalize_raw_input(value) → RawCanonicalizationResult
2. Build RawSizingRequestSnapshot from canonical_value
3. Compute raw_request_digest (self-excluding)
4. Merge canonicalization validation_errors + request schema validation errors
5. Canonical-sort merged validation errors
6. Build InvalidSizingRequestSnapshot with sorted errors
7. Build BLOCKED result, raw_request_digest, result_hash, provenance_digest
```

Every invalid input must produce:
- `raw_request_digest`
- `InvalidSizingRequestSnapshot`
- `result_hash`
- `provenance_digest`
- JSON round-trip

#### 18.1.3 RawSizingRequestSnapshot

```text
RawSizingRequestSnapshot
- schema_version: str
- canonical_raw_input: object
- raw_request_digest: str
```

Digest payload (self-excluding):

```python
raw_request_payload = {
    "schema_version": schema_version,
    "canonical_raw_input": canonical_raw_input,
}
raw_request_digest = sha256_digest(raw_request_payload)
```

`raw_request_digest` must not enter its own payload.

#### 18.1.4 SizingValidationErrorSnapshot

```text
SizingValidationErrorSnapshot
- code: RawInputValidationCode
- message_key: str
- field_path: tuple[str, ...]
- message: str
- rejected_value_digest: str | None
- context: tuple[tuple[str, CanonicalRawValue], ...]
- context_digest: str
- error_digest: str
```

Digest payload:

```python
error_payload = {
    "code": code.value,
    "message_key": message_key,
    "field_path": list(field_path),
    "rejected_value_digest": rejected_value_digest,
    "context_digest": context_digest,
}
error_digest = sha256_digest(error_payload)
```

Sort key (message NOT in digest or sort — informational only):

```text
(code.value, message_key, field_path, rejected_value_digest or "", context_digest)
```

`message` is for display only, mapped from `message_key` to frozen English text. It does NOT enter error_digest or canonical ordering.

Validation error sort key (single frozen form, no Python raw-tuple comparison of nested context):

```text
(code.value, message_key, field_path, rejected_value_digest or "", context_digest)
```

### 18.1.5 RawInputValidationCode

```text
class RawInputValidationCode(StrEnum):
    NON_STRING_MAPPING_KEY = "non_string_mapping_key"
    UNSUPPORTED_RAW_MAPPING_KEY = "unsupported_raw_mapping_key"
    UNSUPPORTED_RAW_INPUT_TYPE = "unsupported_raw_input_type"
    CYCLIC_RAW_INPUT = "cyclic_raw_input"
    NON_FINITE_RAW_FLOAT = "non_finite_raw_float"
```

**Error multiplicity:**

| Input | Code | Count |
|-------|------|-------|
| supported non-string scalar key | NON_STRING_MAPPING_KEY | 1 per entry |
| opaque unsupported mapping key | UNSUPPORTED_RAW_MAPPING_KEY | 1 per entry (NOT also NON_STRING_MAPPING_KEY) |
| unsupported value in input | UNSUPPORTED_RAW_INPUT_TYPE | 1 per occurrence |
| cyclic container | CYCLIC_RAW_INPUT | 1 per cycle occurrence |
| non-finite float value | NON_FINITE_RAW_FLOAT | 1 per occurrence |

No "or frozen equivalent" — these exact values are frozen.

**Frozen message registry:**

| Code | message_key | Message | field_path | rejected_value_digest | context keys | multiplicity |
|------|------------|---------|------------|----------------------|--------------|-------------|
| `NON_STRING_MAPPING_KEY` | `"non_string_mapping_key"` | `"Mapping key is not a string"` | `("$mapping_entries", key_payload_digest [, occurrence_index])` | `sha256_digest({"key_payload": key_payload})` | `("key_type", "key_kind")` | 1 per non-string-key entry |
| `UNSUPPORTED_RAW_MAPPING_KEY` | `"unsupported_raw_mapping_key"` | `"Mapping key is an unsupported type"` | `("$mapping_entries", key_payload_digest [, occurrence_index])` | `sha256_digest({"key_payload": key_payload})` | `("key_type",)` | 1 per opaque-key entry (NOT also NON_STRING_MAPPING_KEY) |
| `UNSUPPORTED_RAW_INPUT_TYPE` | `"unsupported_raw_input_type"` | `"Unsupported value type in input"` | `("$unsupported_type",)` | `sha256_digest({"unsupported_value_marker": {"$unsupported_type": qualified_type_name}})` | `("object_type",)` | 1 per occurrence |
| `CYCLIC_RAW_INPUT` | `"cyclic_raw_input"` | `"Container has cyclic reference"` | `("$cyclic_reference",)` | `sha256_digest({"cyclic_reference_marker": {"$cyclic_reference": {"ancestor_distance": ancestor_distance}}})` | `("ancestor_distance",)` | 1 per cycle occurrence |
| `NON_FINITE_RAW_FLOAT` | `"non_finite_raw_float"` | `"Float value is NaN or Infinity"` | per context | `sha256_digest({"non_finite_float_marker": "nan" | "+infinity" | "-infinity"})` | `("original_value",)` | 1 per occurrence |

**SizingValidationErrorSnapshot (updated):**

```text
SizingValidationErrorSnapshot
- code: RawInputValidationCode      # typed, not bare str
- message_key: str                  # stable identity key, not localized text
- field_path: tuple[str, ...]
- message: str                      # frozen English text
- rejected_value_digest: str | None
- context: tuple[tuple[str, CanonicalRawValue], ...]
- context_digest: str
- error_digest: str
```

`message_key` is the stable identity root for digest/provenance. The `message` field is informational only.

### 18.1.6 Strict Per-Candidate Evaluation Pipeline

Each candidate evaluation follows a frozen sequential order within a single sizing run:

```text
1. attempted_rating_count += 1
2. Call rate_double_pipe()
3. Normal return → completed_rating_count += 1
4. Call verify_hash()
5. Hash PASSED → call verify_provenance()
6. Both PASSED:
   a. Build VerifiedRatingEvidenceSnapshot
   b. Build VERIFIED CandidateEvaluation (with candidate_evaluation_identity)
   c. verified_rating_count += 1
   d. Compare expected vs actual provider identity
   e. If provider mismatch:
      - Preserve current VERIFIED evidence and CandidateEvaluation
      - Add PROPERTY_PROVIDER_IDENTITY_MISMATCH blocker
      - Duty fields: all None (sizing feasibility not yet computed)
      - feasible = False, feasibility_status = PROVIDER_IDENTITY_MISMATCH
      - selected_candidate = None, top_candidates = ()
      - Stop — no further candidates, no feasibility/ranking
   f. If provider match:
      - Compute duty feasibility fields
      - Advance to next candidate (§6.4 canonical order)
```

Rules:
- All candidates are evaluated in a single tight loop — no batching, no parallel TASK-008 calls.
- verify_hash() runs immediately after each rating returns. If hash returns False or raises an exception, verify_provenance() is NOT called.
- Hash verification outcome drives the candidate state immediately — the pipeline does not proceed to provider comparison unless both verification steps pass.
- Provider comparison occurs only after verification passes for the current candidate. It does NOT batch across candidates.

### 18.1.7 Safe verification wrappers

The merged TASK-008 `verify_provenance()` contract catches its internal exceptions and returns `False`. Verification outcomes are derived through two defensive wrappers that distinguish normal boolean outcomes from unexpected runtime exceptions:

```python
def safe_verify_hash(result) -> VerificationOutcome:
    try:
        return (
            VerificationOutcome.PASSED
            if result.verify_hash()
            else VerificationOutcome.FAILED
        )
    except Exception:
        return VerificationOutcome.ERROR
```

```python
def safe_verify_provenance(result) -> VerificationOutcome:
    try:
        return (
            VerificationOutcome.PASSED
            if result.verify_provenance()
            else VerificationOutcome.FAILED
        )
    except Exception:
        return VerificationOutcome.ERROR
```

**Semantics:**
- `FAILED` is the normal integrity-invalid boolean outcome — the TASK-008 result failed verification.
- `ERROR` is only an unexpected defensive wrapper/runtime exception — it means the verification code itself could not execute normally.
- Do not claim TASK-008 `verify_provenance()` normally raises; the merged TASK-008 API catches exceptions internally and returns `False`.
- Do not modify TASK-008 to manufacture an exception path.

**Outcome combinations:**

| hash | provenance | candidate state | sizing status | termination_reason |
|------|-----------|-----------------|---------------|--------------------|
| FAILED | NOT_RUN | INTEGRITY_INVALID | BLOCKED | rating_result_integrity_failed |
| ERROR | NOT_RUN | RUNTIME_FAILED | FAILED | (RunFailure, failure_stage=RATING_VERIFICATION) |
| PASSED | FAILED | INTEGRITY_INVALID | BLOCKED | rating_result_integrity_failed |
| PASSED | ERROR | RUNTIME_FAILED | FAILED | (RunFailure, failure_stage=RATING_VERIFICATION) |
| PASSED | PASSED | VERIFIED | per provider | — |

### 18.2 InvalidSizingRequestSnapshot

```text
InvalidSizingRequestSnapshot
- raw_request_snapshot: RawSizingRequestSnapshot
- validation_errors: tuple[SizingValidationErrorSnapshot, ...]
```

An invalid request BLOCKED result must still produce:

- `raw_request_digest`
- `result_hash`
- `provenance_digest`
- JSON round-trip integrity

### 18.3 SizingResultIdentity

```python
{
    "raw_request_digest": ...,
    "validated_sizing_request_identity_digest": ... | None,
    "catalog_snapshot_digests": [...],
    "status": status.value,
    "termination_reason": ...,
    "partial_audit": ...,
    "raw_combination_count": ...,
    "unique_candidate_count": ...,
    "evaluated_candidate_count": ...,
    "attempted_rating_count": ...,
    "completed_rating_count": ...,
    "verified_rating_count": ...,
    "feasible_candidate_count": ...,
    "non_feasible_candidate_count": ...,
    "remaining_unevaluated_candidate_count": ...,
    "canonical_evaluation_digests": [...],
    "canonical_ranking_digests": [...],
    "warning_digests": [...],
    "blocker_digests": [...],
    "warning_occurrence_digests": [...],
    "blocker_occurrence_digests": [...],
    "failure_digest": ... | None,
    "verified_evidence_digests": [...],
    "invalid_evidence_digests": [...],
    "claimed_rating_audit_digests": [...],
    "selected_candidate_id": ... | None,
    "top_candidate_ids": [...],
    "core_provenance_digest": ...,
}
```

All digests `sha256:...`. Computed via `sha256_digest(payload)`.

---

## 19. SizingOptimizationResult

```text
status: SizingStatus
request_identity: SizingRequestIdentity | InvalidSizingRequestSnapshot
raw_request_digest: str
catalog_snapshots: tuple[CompleteDoublePipeCatalogSnapshot, ...]
raw_combination_count: int
unique_candidate_count: int
evaluated_candidate_count: int
attempted_rating_count: int
completed_rating_count: int
verified_rating_count: int
feasible_candidate_count: int
non_feasible_candidate_count: int
remaining_unevaluated_candidate_count: int
candidate_evaluations: tuple[CandidateEvaluation, ...]
ranking_records: tuple[CandidateRankingRecord, ...]
selected_candidate: CandidateEvaluation | None
top_candidates: tuple[CandidateEvaluation, ...]
warnings: tuple[EngineeringMessage, ...]
blockers: tuple[EngineeringMessage, ...]
failure: RunFailure | None
termination_reason: str
partial_audit: bool
catalog_snapshot_digests: tuple[str, ...]
candidate_evaluation_digests: tuple[str, ...]
verified_evidence_digests: tuple[str, ...]
invalid_evidence_digests: tuple[str, ...]
claimed_rating_audits: tuple[ClaimedRatingResultAuditSnapshot, ...]
claimed_rating_audit_digests: tuple[str, ...]
warning_digests: tuple[str, ...]
blocker_digests: tuple[str, ...]
warning_occurrences: tuple[MessageOccurrenceSnapshot, ...]
blocker_occurrences: tuple[MessageOccurrenceSnapshot, ...]
warning_occurrence_digests: tuple[str, ...]
blocker_occurrence_digests: tuple[str, ...]
failure_digest: str | None
ranking_record_digests: tuple[str, ...]
core_provenance_digest: str
result_hash: str
provenance: ProvenanceGraph
provenance_digest: str
```

For invalid-request BLOCKED results, `request_identity` is an `InvalidSizingRequestSnapshot` and `raw_request_digest` is set from the `RawSizingRequestSnapshot`. All other fields populated per status invariants.

`result_hash = sha256_digest(SizingResultIdentity payload)`.

JSON round-trip must preserve all fields, hashes, and provenance.

---

## 19A. Rating Counters

### 19A.1 Definitions

```text
attempted_rating_count   = candidates that entered rate_double_pipe()
completed_rating_count   = rate_double_pipe() returned RatingResult normally
verified_rating_count    = returned RatingResult passed verify_hash + verify_provenance
```

Invariant: `0 ≤ verified ≤ completed ≤ attempted ≤ unique_candidate_count`.

### 19A.2 evaluated_candidate_count

`evaluated_candidate_count = attempted_rating_count` always. This is the number of candidates that actually executed TASK-008.

### 19A.3 Normal Completion (K candidates all verified)

```text
attempted_rating_count = completed_rating_count = verified_rating_count = K
```

### 19A.4 RATING_CALL exception (N-th candidate raises)

If the N-th candidate's TASK-008 call raises an exception, the call has started but never returned:

```text
attempted_rating_count = completed_rating_count + 1
evaluated_candidate_count = attempted_rating_count
verified_rating_count = completed_rating_count
remaining_unevaluated_candidate_count = unique_candidate_count - attempted_rating_count
```

The failed candidate:
- `CandidateEvaluationState = RUNTIME_FAILED`
- `failure_stage = RATING_CALL`
- No `TASK008_RATING_RESULT` node
- NOT counted as `remaining_unevaluated`

Subsequent candidates: `UNEVALUATED`.

### 19A.5 Verification returns False (integrity invalid)

RatingResult returned normally, but verify_hash() or verify_provenance() returned non-PASSED:

```text
attempted_rating_count = completed_rating_count
completed_rating_count = verified_rating_count + 1
evaluated_candidate_count = attempted_rating_count
remaining_unevaluated_candidate_count = unique_candidate_count - attempted_rating_count
```

The current candidate:
- If hash/provenance FAILED: `CandidateEvaluationState = INTEGRITY_INVALID`, `status = BLOCKED`
- `InvalidRatingEvidenceRecord` constructed
- `rating_status = None` on `CandidateEvaluation`

### 19A.6 Verification raises exception (runtime error)

RatingResult returned normally and verification raised:

```text
attempted_rating_count = completed_rating_count
completed_rating_count = verified_rating_count + 1
CLAIMED_TASK008_RATING_RESULT count = 1
claimed_rating_audits count = 1
evaluated_candidate_count = attempted_rating_count
remaining_unevaluated_candidate_count = unique_candidate_count - attempted_rating_count
```

The current candidate:
- `CandidateEvaluationState = RUNTIME_FAILED`
- `failure_stage = RATING_VERIFICATION`
- `RunFailure` used (not trusted InvalidRatingEvidenceRecord)
- `CLAIMED_TASK008_RATING_RESULT` node created for audit

### 19A.7 Provider mismatch (verification passes, identity mismatches)

Provider comparison runs only after both verification steps PASSED:

```text
attempted_rating_count = completed_rating_count = verified_rating_count
```

The mismatching candidate is already VERIFIED, but the sizing run is BLOCKED. Verified evidence is preserved.

### 19A.8 Entering OPTIMIZATION / RESULT_CONSTRUCTION

Allowed only when:

```text
attempted_rating_count = completed_rating_count = verified_rating_count = unique_candidate_count
```

No `CLAIMED_TASK008_RATING_RESULT` nodes exist during optimization or result construction.

---

## 20. FeasibilityStatus and Non-Feasible Ordering

### 20.1 FeasibilityStatus Enum

```text
class FeasibilityStatus(StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    RATING_BLOCKED = "rating_blocked"
    RATING_FAILED = "rating_failed"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    INTEGRITY_INVALID = "integrity_invalid"
    UNEVALUATED = "unevaluated"
    RUNTIME_FAILED = "runtime_failed"
```

Rank (lower = higher priority in non-feasible sort):

```text
FEASIBLE = 0
INFEASIBLE = 1
RATING_BLOCKED = 2
RATING_FAILED = 3
PROVIDER_IDENTITY_MISMATCH = 4
INTEGRITY_INVALID = 5
UNEVALUATED = 6
RUNTIME_FAILED = 7
```

### 20.2 Rating Status Rank

Rating status from TASK-008 `RatingStatus`:

```text
SUCCEEDED = 0
BLOCKED = 1
FAILED = 2
None = 999
```

### 20.3 CandidateEvaluationState Invariant Rows

4 `CandidateEvaluationState` enum values:

```text
UNEVALUATED, VERIFIED, INTEGRITY_INVALID, RUNTIME_FAILED
```

7 status-specific invariant rows (covering VERIFIED subtypes):

```text
VERIFIED+SUCCEEDED, VERIFIED+BLOCKED, VERIFIED+FAILED, VERIFIED+PROVIDER_IDENTITY_MISMATCH,
INTEGRITY_INVALID, RUNTIME_FAILED, UNEVALUATED
```

### 20.4 Full Non-Feasible Sort Key

```text
(
    feasibility_status_rank,
    rating_status_rank,
    candidate_diagnostic_sort_key(primary_diagnostic_or_sentinel),
    source_qualified_candidate_id,
)
```

### 20.5 CandidateDiagnosticKey

```python
from enum import IntEnum
from dataclasses import dataclass


class CandidateDiagnosticRank(IntEnum):
    BLOCKER = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    RUNTIME_FAILURE = 4


@dataclass(frozen=True, slots=True)
class CandidateDiagnosticKey:
    diagnostic_class_rank: CandidateDiagnosticRank
    code: ErrorCode
    source_module: str
    affected_paths: tuple[str, ...]
    message: str
```

Sentinel when `None`: `CandidateDiagnosticKey(CandidateDiagnosticRank.INFO, ErrorCode.PROVENANCE_INCOMPLETE, "", (), "")`.

From EngineeringMessage: `diagnostic_class_rank` = severity, `code` = `message.code`. From RunFailure: `diagnostic_class_rank=CandidateDiagnosticRank.RUNTIME_FAILURE`, `code` = `failure.code`. From pure duty-infeasible: `diagnostic_class_rank=CandidateDiagnosticRank.BLOCKER`, `code=ErrorCode.REQUIRED_DUTY_NOT_MET`.

### 20.6 Primary Diagnostic Selection

Ascending: class_rank → code → source_module → affected_paths → message.

## 21. RunFailure Stage Model

### 21.1 FailureStage Enum

```text
class FailureStage(StrEnum):
    REQUEST_VALIDATION = "request_validation"
    CATALOG_VALIDATION = "catalog_validation"
    CANDIDATE_MATERIALIZATION = "candidate_materialization"
    PRE_RATING = "pre_rating"
    RATING_CALL = "rating_call"
    RATING_VERIFICATION = "rating_verification"
    OPTIMIZATION = "optimization"
    RESULT_CONSTRUCTION = "result_construction"
```

`RunFailure.context` carries:

```text
failure_stage: FailureStage
candidate_id: str | None
evaluation_order_index: int | None
```

`RunFailure` type itself is not modified; the context dict stores these fields.

---

## 22. Provenance

### 22.1 Node Type Mapping

| Concept | ProvenanceNodeType | Label |
|---------|-------------------|-------|
| ROOT_CASE_REVISION | `CASE_REVISION` | `"revision_{design_case_revision_id}"` |
| ROOT_EXTERNAL | `EXTERNAL` | `"external_root"` |
| SIZING_RUN | `CALCULATION_RUN` | `"sizing_run_{digest}"` |
| SIZING_OPTIMIZER | `OPTIMIZER` | `"sizing_optimizer"` |
| CATALOG_SNAPSHOT | `INTERMEDIATE` | `"catalog_{catalog_id}"` |
| CANDIDATE | `INTERMEDIATE` | `"candidate_{id}"` |
| TASK008_RATING_RESULT | `RESULT` | `"rating_{result_hash}"` |
| CLAIMED_TASK008_RATING_RESULT | `INTERMEDIATE` | `"claimed_rating_{source_qualified_candidate_id}"` |
| SIZING_RESULT | `RESULT` | `"sizing_result"` |
| SIZING_RUN_FAILURE_RESULT | `RESULT` | `"sizing_run_failure"` |
| INVALID_EVIDENCE | `INTERMEDIATE` | `"invalid_evidence_{source_qualified_candidate_id}"` |
| RUNTIME_FAILURE | `BLOCKER` | `"runtime_failure"` |
| WARNING | `WARNING` | per message |
| BLOCKER | `BLOCKER` | per message |

Root selection delegates to `select_root_concept()` (§22.1). The two distinct `ROOT` concepts (`ROOT_CASE_REVISION`, `ROOT_EXTERNAL`) prevent expression of root-type selection within a single ambiguous table entry. Callers should never hard-code root selection logic.

### 22.2 Enums and Base Types

```python
from enum import StrEnum
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    Mapping,
    TypeAlias,
    TypeVar,
)
from uuid import UUID

class ProvenanceConcept(StrEnum):
    ROOT_CASE_REVISION = "root_case_revision"
    ROOT_EXTERNAL = "root_external"
    SIZING_RUN = "sizing_run"
    SIZING_OPTIMIZER = "sizing_optimizer"
    CATALOG_SNAPSHOT = "catalog_snapshot"
    CANDIDATE = "candidate"
    TASK008_RATING_RESULT = "task008_rating_result"
    CLAIMED_TASK008_RATING_RESULT = "claimed_task008_rating_result"
    SIZING_RESULT = "sizing_result"
    SIZING_RUN_FAILURE_RESULT = "sizing_run_failure_result"
    INVALID_EVIDENCE = "invalid_evidence"
    RUNTIME_FAILURE = "runtime_failure"
    WARNING = "warning"
    BLOCKER = "blocker"


class TerminationClass(StrEnum):
    INVALID_REQUEST = "invalid_request"
    INVALID_CATALOG = "invalid_catalog"
    CATALOG_IDENTITY_MISMATCH = "catalog_identity_mismatch"
    CAP_EXCEEDED = "cap_exceeded"
    NO_MANUFACTURABLE_CANDIDATE = "no_manufacturable_candidate"
    NO_FEASIBLE_CANDIDATE = "no_feasible_candidate"
    SUCCEEDED = "succeeded"
    PROPERTY_PROVIDER_IDENTITY_MISMATCH = "property_provider_identity_mismatch"
    RATING_RESULT_INTEGRITY_FAILED = "rating_result_integrity_failed"
    RUNTIME_FAILED_REQUEST_VALIDATION = "runtime_failed_request_validation"
    RUNTIME_FAILED_CATALOG_VALIDATION = "runtime_failed_catalog_validation"
    RUNTIME_FAILED_CANDIDATE_MATERIALIZATION = "runtime_failed_candidate_materialization"
    RUNTIME_FAILED_PRE_RATING = "runtime_failed_pre_rating"
    RUNTIME_FAILED_RATING_CALL = "runtime_failed_rating_call"
    RUNTIME_FAILED_RATING_VERIFICATION = "runtime_failed_rating_verification"
    RUNTIME_FAILED_OPTIMIZATION = "runtime_failed_optimization"
    RUNTIME_FAILED_RESULT_CONSTRUCTION = "runtime_failed_result_construction"


class SizingRunRequestKind(StrEnum):
    VALIDATED = "validated"
    RAW = "raw"


class MessageOccurrenceKind(StrEnum):
    WARNING = "warning"
    BLOCKER = "blocker"


class MessageOwnerKind(StrEnum):
    SIZING_RUN = "sizing_run"
    CATALOG_SNAPSHOT = "catalog_snapshot"
    CANDIDATE = "candidate"
    OPTIMIZER = "optimizer"


ProvenanceIncomingRelation = tuple[str, ProvenanceConcept]  # (label, source_concept)
ProvenanceOutgoingRelation = tuple[str, ProvenanceConcept]  # (label, target_concept)


# TypeAlias definitions
CanonicalPrimitive: TypeAlias = None | bool | int | float | str
CanonicalValue: TypeAlias = CanonicalPrimitive | list["CanonicalValue"] | dict[str, "CanonicalValue"]
CanonicalPayload: TypeAlias = dict[str, CanonicalValue]
CanonicalMetadata: TypeAlias = tuple[tuple[str, str], ...]
ContextT = TypeVar("ContextT")
LabelConstructor: TypeAlias = Callable[[ContextT], str]
Uuid5NameConstructor: TypeAlias = Callable[[ContextT], str]
PayloadConstructor: TypeAlias = Callable[[ContextT], CanonicalPayload]
MetadataConstructor: TypeAlias = Callable[[ContextT], CanonicalMetadata]


@dataclass(frozen=True, slots=True)
class ProvenanceRelationSpec:
    source_concept: ProvenanceConcept
    relation: str
    target_concept: ProvenanceConcept
```

### 22.3 Root Selection

```python
def select_root_concept(
    request_kind: SizingRunRequestKind,
    design_case_revision_id: UUID | None,
) -> ProvenanceConcept:
    if request_kind is SizingRunRequestKind.RAW:
        return ProvenanceConcept.ROOT_EXTERNAL
    if design_case_revision_id is not None:
        return ProvenanceConcept.ROOT_CASE_REVISION
    return ProvenanceConcept.ROOT_EXTERNAL


def root_node_type(root_concept: ProvenanceConcept) -> ProvenanceNodeType:
    if root_concept == ProvenanceConcept.ROOT_CASE_REVISION:
        return ProvenanceNodeType.CASE_REVISION
    return ProvenanceNodeType.EXTERNAL


def root_label(
    root_concept: ProvenanceConcept,
    effective_design_case_revision_id: UUID | None,
) -> str:
    if root_concept is ProvenanceConcept.ROOT_CASE_REVISION:
        if effective_design_case_revision_id is None:
            raise ValueError(
                "case-revision root requires revision id"
            )
        return f"revision_{effective_design_case_revision_id}"
    if root_concept is ProvenanceConcept.ROOT_EXTERNAL:
        return "external_root"
    raise ValueError("unsupported root concept")


@dataclass(frozen=True, slots=True)
class RootTopologySelection:
    root_concept: ProvenanceConcept
    root_node_type: ProvenanceNodeType
    root_label: str
    root_case_revision_count: Literal[0, 1]
    root_external_count: Literal[0, 1]
    initiates_edge: ProvenanceRelationSpec
    design_case_revision_id: UUID | None

    def __post_init__(self) -> None:
        # Exactly one root count must be 1
        if self.root_case_revision_count + self.root_external_count != 1:
            raise ValueError("exactly one root count must equal 1")
        # Concept ↔ count consistency
        if self.root_concept == ProvenanceConcept.ROOT_CASE_REVISION:
            if self.root_case_revision_count != 1 or self.root_external_count != 0:
                raise ValueError("ROOT_CASE_REVISION requires root_case_revision_count=1, root_external_count=0")
            if self.design_case_revision_id is None:
                raise ValueError("ROOT_CASE_REVISION requires non-None design_case_revision_id")
        elif self.root_concept == ProvenanceConcept.ROOT_EXTERNAL:
            if self.root_case_revision_count != 0 or self.root_external_count != 1:
                raise ValueError("ROOT_EXTERNAL requires root_case_revision_count=0, root_external_count=1")
            if self.design_case_revision_id is not None:
                raise ValueError("ROOT_EXTERNAL requires design_case_revision_id=None")
        else:
            raise ValueError(f"unexpected root concept: {self.root_concept}")
        # Concept ↔ node_type consistency
        expected_node_type = (
            ProvenanceNodeType.CASE_REVISION
            if self.root_concept == ProvenanceConcept.ROOT_CASE_REVISION
            else ProvenanceNodeType.EXTERNAL
        )
        if self.root_node_type is not expected_node_type:
            raise ValueError(f"root_node_type mismatch: expected {expected_node_type}, got {self.root_node_type}")
        # Concept ↔ label consistency
        if self.root_concept == ProvenanceConcept.ROOT_CASE_REVISION:
            expected_label = f"revision_{self.design_case_revision_id}"
        else:
            expected_label = "external_root"
        if self.root_label != expected_label:
            raise ValueError(f"root_label mismatch: expected '{expected_label}', got '{self.root_label}'")
        # Edge invariants
        if self.initiates_edge.source_concept is not self.root_concept:
            raise ValueError("root edge source must equal root concept")
        if self.initiates_edge.relation != "initiates":
            raise ValueError("root edge relation must be initiates")
        if self.initiates_edge.target_concept is not ProvenanceConcept.SIZING_RUN:
            raise ValueError("root edge target must be SIZING_RUN")


RootTopologyConstructor = Callable[[SizingRunRequestKind, UUID | None], RootTopologySelection]


def derive_root_topology(
    request_kind: SizingRunRequestKind,
    design_case_revision_id: UUID | None,
) -> RootTopologySelection:
    root_concept = select_root_concept(request_kind, design_case_revision_id)
    effective_design_case_revision_id = (
        design_case_revision_id
        if root_concept is ProvenanceConcept.ROOT_CASE_REVISION
        else None
    )
    ntype = root_node_type(root_concept)
    label = root_label(root_concept, effective_design_case_revision_id)
    is_case = root_concept == ProvenanceConcept.ROOT_CASE_REVISION
    return RootTopologySelection(
        root_concept=root_concept,
        root_node_type=ntype,
        root_label=label,
        root_case_revision_count=1 if is_case else 0,
        root_external_count=0 if is_case else 1,
        initiates_edge=ProvenanceRelationSpec(root_concept, "initiates", ProvenanceConcept.SIZING_RUN),
        design_case_revision_id=effective_design_case_revision_id,
    )
```

### 22.4 Edge Labels

Edge labels are uniquely frozen:

| Edge | Label |
|------|-------|
| ROOT → SIZING_RUN | `"initiates"` |
| SIZING_RUN → CATALOG_SNAPSHOT | `"consumes"` |
| SIZING_RUN → OPTIMIZER | `"executes"` |
| CATALOG_SNAPSHOT → CANDIDATE | `"generates"` |
| CANDIDATE → TASK008_RATING_RESULT (verified) | `"rated_as"` |
| CANDIDATE → CLAIMED_TASK008_RATING_RESULT (unverified) | `"rated_as_claimed"` |
| TASK008_RATING_RESULT → OPTIMIZER | `"evaluated_by"` |
| CANDIDATE → INVALID_EVIDENCE | `"produced_unverified"` |
| INVALID_EVIDENCE → SIZING_RESULT | `"invalidates"` |
| OPTIMIZER → SIZING_RESULT | `"produces"` |
| OPTIMIZER → SIZING_RUN_FAILURE_RESULT | `"precedes_failure"` |
| RUNTIME_FAILURE → SIZING_RESULT | `"fails"` |
| RUNTIME_FAILURE → SIZING_RUN_FAILURE_RESULT | `"fails"` |
| SIZING_RUN → SIZING_RESULT | `"produces"` |
| SIZING_RUN → SIZING_RUN_FAILURE_RESULT | `"produces_failure_record"` |
| BLOCKER → SIZING_RESULT | `"blocks"` |
| BLOCKER → SIZING_RUN_FAILURE_RESULT | `"annotates_failure"` (if applicable) |
| WARNING → SIZING_RESULT | `"annotates"` |
| WARNING → SIZING_RUN_FAILURE_RESULT | `"annotates_failure"` (if applicable) |
| SIZING_RUN → WARNING | `"emits"` |
| SIZING_RUN → BLOCKER | `"emits"` |
| CATALOG_SNAPSHOT → WARNING | `"emits"` |
| CATALOG_SNAPSHOT → BLOCKER | `"emits"` |
| CANDIDATE → WARNING | `"emits"` |
| CANDIDATE → BLOCKER | `"emits"` |
| OPTIMIZER → WARNING | `"emits"` |
| OPTIMIZER → BLOCKER | `"emits"` |

No two edges share an ambiguous label with different semantics.

### 22.5 UUID5 Namespace

```python
TASK009_PROVENANCE_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
```

### 22.6 Concept-Specific Construction Contexts

```python
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RootCaseRevisionConstructionContext:
    design_case_revision_id: UUID

@dataclass(frozen=True, slots=True)
class RootExternalConstructionContext:
    request_kind: SizingRunRequestKind
    request_digest: str

@dataclass(frozen=True, slots=True)
class SizingRunConstructionContext:
    request_kind: SizingRunRequestKind
    request_digest: str

@dataclass(frozen=True, slots=True)
class CatalogSnapshotConstructionContext:
    catalog_id: str
    catalog_version: str
    catalog_content_hash: str
    source_identity: str
    schema_version: str

@dataclass(frozen=True, slots=True)
class CandidateConstructionContext:
    source_qualified_candidate_id: str
    source_qualified_candidate_identity_digest: str

@dataclass(frozen=True, slots=True)
class RatingResultConstructionContext:
    source_qualified_candidate_id: str
    rating_result_hash: str
    rating_provenance_digest: str

@dataclass(frozen=True, slots=True)
class ClaimedRatingConstructionContext:
    source_qualified_candidate_id: str
    evaluation_order_index: int
    audit_digest: str

@dataclass(frozen=True, slots=True)
class SizingResultConstructionContext:
    result_hash: str

@dataclass(frozen=True, slots=True)
class SizingRunFailureConstructionContext:
    failure_result_hash: str
    failure_stage: FailureStage

@dataclass(frozen=True, slots=True)
class InvalidEvidenceConstructionContext:
    source_qualified_candidate_id: str
    invalid_evidence_digest: str

@dataclass(frozen=True, slots=True)
class RuntimeFailureConstructionContext:
    failure_digest: str

@dataclass(frozen=True, slots=True)
class OptimizerConstructionContext:
    request_kind: SizingRunRequestKind
    request_digest: str

@dataclass(frozen=True, slots=True)
class WarningOccurrenceConstructionContext:
    owner_kind: MessageOwnerKind
    owner_id: str
    message_digest: str
    occurrence_index: int
    occurrence_kind: Literal[MessageOccurrenceKind.WARNING] = field(
        default=MessageOccurrenceKind.WARNING,
        init=False,
    )

@dataclass(frozen=True, slots=True)
class BlockerOccurrenceConstructionContext:
    owner_kind: MessageOwnerKind
    owner_id: str
    message_digest: str
    occurrence_index: int
    occurrence_kind: Literal[MessageOccurrenceKind.BLOCKER] = field(
        default=MessageOccurrenceKind.BLOCKER,
        init=False,
    )
```

### 22.7 Constructor Functions

Each concept has its own typed context. Multiplicity is handled by `NODE_MULTIPLICITY_CONSTRUCTORS`.

```python
# ──────────────────────────────────────────────────────────
# 14 × 4 constructor functions (label, uuid5, payload, metadata)
# ──────────────────────────────────────────────────────────

# --- ROOT_CASE_REVISION ---

def build_revision_label(context: RootCaseRevisionConstructionContext) -> str:
    return f"revision_{context.design_case_revision_id}"


def build_root_case_revision_uuid5(context: RootCaseRevisionConstructionContext) -> str:
    return f"root-case-revision:{context.design_case_revision_id}"


def build_root_case_revision_payload(context: RootCaseRevisionConstructionContext) -> CanonicalPayload:
    return {"design_case_revision_id": str(context.design_case_revision_id)}


def build_root_case_revision_metadata(context: RootCaseRevisionConstructionContext) -> CanonicalMetadata:
    return (("design_case_revision_id", str(context.design_case_revision_id)),)


# --- ROOT_EXTERNAL ---

def build_external_label(context: RootExternalConstructionContext) -> str:
    return "external_root"


def build_root_external_uuid5(context: RootExternalConstructionContext) -> str:
    return f"root-external:{context.request_kind.value}:{context.request_digest}"


def build_root_external_payload(context: RootExternalConstructionContext) -> CanonicalPayload:
    return {
        "request_kind": context.request_kind.value,
        "request_digest": context.request_digest,
    }


def build_root_external_metadata(context: RootExternalConstructionContext) -> CanonicalMetadata:
    return ()


# --- SIZING_RUN ---

def build_sizing_run_label(context: SizingRunConstructionContext) -> str:
    return f"sizing_run_{context.request_digest}"


def build_sizing_run_uuid5(context: SizingRunConstructionContext) -> str:
    return f"sizing-run:{context.request_kind.value}:{context.request_digest}"


def build_sizing_run_payload(context: SizingRunConstructionContext) -> CanonicalPayload:
    return {
        "request_kind": context.request_kind.value,
        "request_digest": context.request_digest,
    }


def build_sizing_run_metadata(context: SizingRunConstructionContext) -> CanonicalMetadata:
    return (
        ("request_kind", context.request_kind.value),
        ("request_digest", context.request_digest),
    )


# --- SIZING_OPTIMIZER ---

def build_optimizer_label(context: OptimizerConstructionContext) -> str:
    return "sizing_optimizer"


def build_optimizer_uuid5(context: OptimizerConstructionContext) -> str:
    return f"optimizer:{context.request_digest}"


def build_optimizer_payload(context: OptimizerConstructionContext) -> CanonicalPayload:
    return {
        "request_kind": context.request_kind.value,
        "request_digest": context.request_digest,
    }


def build_optimizer_metadata(context: OptimizerConstructionContext) -> CanonicalMetadata:
    return (
        ("request_kind", context.request_kind.value),
        ("request_digest", context.request_digest),
    )


# --- CATALOG_SNAPSHOT ---

def build_catalog_label(context: CatalogSnapshotConstructionContext) -> str:
    return f"catalog_{context.catalog_id}"


def build_catalog_uuid5(context: CatalogSnapshotConstructionContext) -> str:
    return f"catalog:{context.catalog_id}:{context.catalog_version}:{context.catalog_content_hash}"


def build_catalog_payload(context: CatalogSnapshotConstructionContext) -> CanonicalPayload:
    return {
        "catalog_id": context.catalog_id,
        "catalog_version": context.catalog_version,
        "catalog_content_hash": context.catalog_content_hash,
        "source_identity": context.source_identity,
        "schema_version": context.schema_version,
    }


def build_catalog_metadata(context: CatalogSnapshotConstructionContext) -> CanonicalMetadata:
    return (
        ("catalog_id", context.catalog_id),
        ("catalog_version", context.catalog_version),
        ("catalog_content_hash", context.catalog_content_hash),
        ("source_identity", context.source_identity),
        ("schema_version", context.schema_version),
    )


# --- CANDIDATE ---

def build_candidate_label(context: CandidateConstructionContext) -> str:
    return f"candidate_{context.source_qualified_candidate_id}"


def build_candidate_uuid5(context: CandidateConstructionContext) -> str:
    return f"candidate:{context.source_qualified_candidate_id}"


def build_candidate_payload(context: CandidateConstructionContext) -> CanonicalPayload:
    return {"source_qualified_candidate_identity_digest": context.source_qualified_candidate_identity_digest}


def build_candidate_metadata(context: CandidateConstructionContext) -> CanonicalMetadata:
    return (("source_qualified_candidate_id", context.source_qualified_candidate_id),)


# --- TASK008_RATING_RESULT ---

def build_rating_result_label(context: RatingResultConstructionContext) -> str:
    return f"rating_{context.rating_result_hash}"


def build_rating_result_uuid5(context: RatingResultConstructionContext) -> str:
    return f"rating-result:{context.rating_result_hash}"


def build_rating_result_payload(context: RatingResultConstructionContext) -> CanonicalPayload:
    return {
        "source_qualified_candidate_id": context.source_qualified_candidate_id,
        "rating_result_hash": context.rating_result_hash,
        "rating_provenance_digest": context.rating_provenance_digest,
    }


def build_rating_result_metadata(context: RatingResultConstructionContext) -> CanonicalMetadata:
    return (
        ("source_qualified_candidate_id", context.source_qualified_candidate_id),
        ("rating_result_hash", context.rating_result_hash),
        ("rating_provenance_digest", context.rating_provenance_digest),
    )


# --- CLAIMED_TASK008_RATING_RESULT ---

def build_claimed_rating_label(context: ClaimedRatingConstructionContext) -> str:
    return f"claimed_rating_{context.source_qualified_candidate_id}"


def build_claimed_rating_uuid5(context: ClaimedRatingConstructionContext) -> str:
    return f"claimed-rating-result:{context.source_qualified_candidate_id}:{context.evaluation_order_index}:{context.audit_digest}"


def build_claimed_rating_payload(context: ClaimedRatingConstructionContext) -> CanonicalPayload:
    return {
        "source_qualified_candidate_id": context.source_qualified_candidate_id,
        "evaluation_order_index": context.evaluation_order_index,
        "audit_digest": context.audit_digest,
    }


def build_claimed_rating_metadata(context: ClaimedRatingConstructionContext) -> CanonicalMetadata:
    return (
        ("source_qualified_candidate_id", context.source_qualified_candidate_id),
        ("evaluation_order_index", str(context.evaluation_order_index)),
        ("audit_digest", context.audit_digest),
    )


# --- SIZING_RESULT ---

def build_sizing_result_label(context: SizingResultConstructionContext) -> str:
    return "sizing_result"


def build_sizing_result_uuid5(context: SizingResultConstructionContext) -> str:
    return f"sizing-result:{context.result_hash}"


def build_sizing_result_payload(context: SizingResultConstructionContext) -> CanonicalPayload:
    return {"result_hash": context.result_hash}


def build_sizing_result_metadata(context: SizingResultConstructionContext) -> CanonicalMetadata:
    return (("result_hash", context.result_hash),)


# --- SIZING_RUN_FAILURE_RESULT ---

def build_sizing_run_failure_label(context: SizingRunFailureConstructionContext) -> str:
    return "sizing_run_failure"


def build_sizing_run_failure_uuid5(context: SizingRunFailureConstructionContext) -> str:
    return f"sizing-run-failure:{context.failure_result_hash}"


def build_sizing_run_failure_payload(context: SizingRunFailureConstructionContext) -> CanonicalPayload:
    return {
        "failure_result_hash": context.failure_result_hash,
        "failure_stage": context.failure_stage.value,
    }


def build_sizing_run_failure_metadata(context: SizingRunFailureConstructionContext) -> CanonicalMetadata:
    return (
        ("failure_result_hash", context.failure_result_hash),
        ("failure_stage", context.failure_stage.value),
    )


# --- INVALID_EVIDENCE ---

def build_invalid_evidence_label(context: InvalidEvidenceConstructionContext) -> str:
    return f"invalid_evidence_{context.source_qualified_candidate_id}"


def build_invalid_evidence_uuid5(context: InvalidEvidenceConstructionContext) -> str:
    return f"invalid-evidence:{context.source_qualified_candidate_id}:{context.invalid_evidence_digest}"


def build_invalid_evidence_payload(context: InvalidEvidenceConstructionContext) -> CanonicalPayload:
    return {
        "source_qualified_candidate_id": context.source_qualified_candidate_id,
        "invalid_evidence_digest": context.invalid_evidence_digest,
    }


def build_invalid_evidence_metadata(context: InvalidEvidenceConstructionContext) -> CanonicalMetadata:
    return (
        ("source_qualified_candidate_id", context.source_qualified_candidate_id),
        ("invalid_evidence_digest", context.invalid_evidence_digest),
    )


# --- RUNTIME_FAILURE ---

def build_runtime_failure_label(context: RuntimeFailureConstructionContext) -> str:
    return "runtime_failure"


def build_runtime_failure_uuid5(context: RuntimeFailureConstructionContext) -> str:
    return f"runtime-failure:{context.failure_digest}"


def build_runtime_failure_payload(context: RuntimeFailureConstructionContext) -> CanonicalPayload:
    return {"failure_digest": context.failure_digest}


def build_runtime_failure_metadata(context: RuntimeFailureConstructionContext) -> CanonicalMetadata:
    return (("failure_digest", context.failure_digest),)


# --- WARNING ---

def build_warning_label(context: WarningOccurrenceConstructionContext) -> str:
    return f"{context.owner_kind.value}:{context.owner_id}:{context.occurrence_kind.value}:{context.message_digest}:{context.occurrence_index}"


def build_warning_uuid5(context: WarningOccurrenceConstructionContext) -> str:
    return f"{context.occurrence_kind.value}:{context.owner_kind.value}:{context.owner_id}:{context.message_digest}:{context.occurrence_index}"


def build_warning_payload(context: WarningOccurrenceConstructionContext) -> CanonicalPayload:
    return {
        "occurrence_kind": context.occurrence_kind.value,
        "owner_kind": context.owner_kind.value,
        "owner_id": context.owner_id,
        "message_digest": context.message_digest,
        "occurrence_index": context.occurrence_index,
    }


def build_warning_metadata(context: WarningOccurrenceConstructionContext) -> CanonicalMetadata:
    return (
        ("owner_kind", context.owner_kind.value),
        ("owner_id", context.owner_id),
        ("message_digest", context.message_digest),
        ("occurrence_index", str(context.occurrence_index)),
        ("occurrence_kind", context.occurrence_kind.value),
    )


# --- BLOCKER ---

def build_blocker_label(context: BlockerOccurrenceConstructionContext) -> str:
    return f"{context.owner_kind.value}:{context.owner_id}:{context.occurrence_kind.value}:{context.message_digest}:{context.occurrence_index}"


def build_blocker_uuid5(context: BlockerOccurrenceConstructionContext) -> str:
    return f"{context.occurrence_kind.value}:{context.owner_kind.value}:{context.owner_id}:{context.message_digest}:{context.occurrence_index}"


def build_blocker_payload(context: BlockerOccurrenceConstructionContext) -> CanonicalPayload:
    return {
        "occurrence_kind": context.occurrence_kind.value,
        "owner_kind": context.owner_kind.value,
        "owner_id": context.owner_id,
        "message_digest": context.message_digest,
        "occurrence_index": context.occurrence_index,
    }


def build_blocker_metadata(context: BlockerOccurrenceConstructionContext) -> CanonicalMetadata:
    return (
        ("owner_kind", context.owner_kind.value),
        ("owner_id", context.owner_id),
        ("message_digest", context.message_digest),
        ("occurrence_index", str(context.occurrence_index)),
        ("occurrence_kind", context.occurrence_kind.value),
    )
```

### 22.8 construct_provenance_node_parts Executor

Runtime executor that validates exact context type match before dispatching constructors:

```python
@dataclass(frozen=True, slots=True)
class ConstructedProvenanceNodeParts:
    label: str
    uuid5_name: str
    payload: CanonicalPayload
    metadata: CanonicalMetadata


class ProvenanceConstructionContextMismatch(Exception):
    """Raised when the provided context type does not match the spec's context_type."""
    pass


def construct_provenance_node_parts(
    spec: ProvenanceConstructorSpec[Any],
    context: Any,
) -> ConstructedProvenanceNodeParts:
    if type(context) is not spec.context_type:
        raise ProvenanceConstructionContextMismatch(
            f"expected context type {spec.context_type.__name__}, "
            f"got {type(context).__name__}"
        )
    return ConstructedProvenanceNodeParts(
        label=spec.label_constructor(context),
        uuid5_name=spec.uuid5_name_constructor(context),
        payload=spec.payload_constructor(context),
        metadata=spec.metadata_constructor(context),
    )
```

### 22.9 ProvenanceConstructorSpec and ProvenanceConceptSpec

```python
@dataclass(frozen=True, slots=True)
class ProvenanceConstructorSpec(Generic[ContextT]):
    context_type: type[ContextT]
    label_constructor: Callable[[ContextT], str]
    uuid5_name_constructor: Callable[[ContextT], str]
    payload_constructor: Callable[[ContextT], CanonicalPayload]
    metadata_constructor: Callable[[ContextT], CanonicalMetadata]


@dataclass(frozen=True, slots=True)
class ProvenanceConceptSpec:
    concept: ProvenanceConcept
    node_type: ProvenanceNodeType
    constructors: ProvenanceConstructorSpec[Any]
    allowed_incoming: tuple[ProvenanceRelationSpec, ...]
    allowed_outgoing: tuple[ProvenanceRelationSpec, ...]
```

### 22.10 PROVENANCE_CONCEPT_REGISTRY

The authoritative registry of all 14 provenance concepts:

```python
PROVENANCE_CONCEPT_REGISTRY: tuple[ProvenanceConceptSpec, ...] = (
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.ROOT_CASE_REVISION,
        node_type=ProvenanceNodeType.CASE_REVISION,
        constructors=ProvenanceConstructorSpec[RootCaseRevisionConstructionContext](
            context_type=RootCaseRevisionConstructionContext,
            label_constructor=build_revision_label,
            uuid5_name_constructor=build_root_case_revision_uuid5,
            payload_constructor=build_root_case_revision_payload,
            metadata_constructor=build_root_case_revision_metadata,
        ),
        allowed_incoming=(),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.ROOT_CASE_REVISION, "initiates", ProvenanceConcept.SIZING_RUN),
        ),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.ROOT_EXTERNAL,
        node_type=ProvenanceNodeType.EXTERNAL,
        constructors=ProvenanceConstructorSpec[RootExternalConstructionContext](
            context_type=RootExternalConstructionContext,
            label_constructor=build_external_label,
            uuid5_name_constructor=build_root_external_uuid5,
            payload_constructor=build_root_external_payload,
            metadata_constructor=build_root_external_metadata,
        ),
        allowed_incoming=(),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.ROOT_EXTERNAL, "initiates", ProvenanceConcept.SIZING_RUN),
        ),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.SIZING_RUN,
        node_type=ProvenanceNodeType.CALCULATION_RUN,
        constructors=ProvenanceConstructorSpec[SizingRunConstructionContext](
            context_type=SizingRunConstructionContext,
            label_constructor=build_sizing_run_label,
            uuid5_name_constructor=build_sizing_run_uuid5,
            payload_constructor=build_sizing_run_payload,
            metadata_constructor=build_sizing_run_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.ROOT_CASE_REVISION, "initiates", ProvenanceConcept.SIZING_RUN),
            ProvenanceRelationSpec(ProvenanceConcept.ROOT_EXTERNAL, "initiates", ProvenanceConcept.SIZING_RUN),
        ),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "executes", ProvenanceConcept.SIZING_OPTIMIZER),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces_failure_record", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "emits", ProvenanceConcept.WARNING),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "emits", ProvenanceConcept.BLOCKER),
        ),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.SIZING_OPTIMIZER,
        node_type=ProvenanceNodeType.OPTIMIZER,
        constructors=ProvenanceConstructorSpec[OptimizerConstructionContext](
            context_type=OptimizerConstructionContext,
            label_constructor=build_optimizer_label,
            uuid5_name_constructor=build_optimizer_uuid5,
            payload_constructor=build_optimizer_payload,
            metadata_constructor=build_optimizer_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "executes", ProvenanceConcept.SIZING_OPTIMIZER),
            ProvenanceRelationSpec(ProvenanceConcept.TASK008_RATING_RESULT, "evaluated_by", ProvenanceConcept.SIZING_OPTIMIZER),
        ),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "produces", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "precedes_failure", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "emits", ProvenanceConcept.WARNING),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "emits", ProvenanceConcept.BLOCKER),
        ),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.CATALOG_SNAPSHOT,
        node_type=ProvenanceNodeType.INTERMEDIATE,
        constructors=ProvenanceConstructorSpec[CatalogSnapshotConstructionContext](
            context_type=CatalogSnapshotConstructionContext,
            label_constructor=build_catalog_label,
            uuid5_name_constructor=build_catalog_uuid5,
            payload_constructor=build_catalog_payload,
            metadata_constructor=build_catalog_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
        ),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "emits", ProvenanceConcept.WARNING),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "emits", ProvenanceConcept.BLOCKER),
        ),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.CANDIDATE,
        node_type=ProvenanceNodeType.INTERMEDIATE,
        constructors=ProvenanceConstructorSpec[CandidateConstructionContext](
            context_type=CandidateConstructionContext,
            label_constructor=build_candidate_label,
            uuid5_name_constructor=build_candidate_uuid5,
            payload_constructor=build_candidate_payload,
            metadata_constructor=build_candidate_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
        ),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as", ProvenanceConcept.TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as_claimed", ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "produced_unverified", ProvenanceConcept.INVALID_EVIDENCE),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "emits", ProvenanceConcept.WARNING),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "emits", ProvenanceConcept.BLOCKER),
        ),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.TASK008_RATING_RESULT,
        node_type=ProvenanceNodeType.RESULT,
        constructors=ProvenanceConstructorSpec[RatingResultConstructionContext](
            context_type=RatingResultConstructionContext,
            label_constructor=build_rating_result_label,
            uuid5_name_constructor=build_rating_result_uuid5,
            payload_constructor=build_rating_result_payload,
            metadata_constructor=build_rating_result_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as", ProvenanceConcept.TASK008_RATING_RESULT),
        ),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.TASK008_RATING_RESULT, "evaluated_by", ProvenanceConcept.SIZING_OPTIMIZER),
        ),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT,
        node_type=ProvenanceNodeType.INTERMEDIATE,
        constructors=ProvenanceConstructorSpec[ClaimedRatingConstructionContext](
            context_type=ClaimedRatingConstructionContext,
            label_constructor=build_claimed_rating_label,
            uuid5_name_constructor=build_claimed_rating_uuid5,
            payload_constructor=build_claimed_rating_payload,
            metadata_constructor=build_claimed_rating_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as_claimed", ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        ),
        allowed_outgoing=(),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.SIZING_RESULT,
        node_type=ProvenanceNodeType.RESULT,
        constructors=ProvenanceConstructorSpec[SizingResultConstructionContext](
            context_type=SizingResultConstructionContext,
            label_constructor=build_sizing_result_label,
            uuid5_name_constructor=build_sizing_result_uuid5,
            payload_constructor=build_sizing_result_payload,
            metadata_constructor=build_sizing_result_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "produces", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.BLOCKER, "blocks", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.WARNING, "annotates", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        allowed_outgoing=(),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.SIZING_RUN_FAILURE_RESULT,
        node_type=ProvenanceNodeType.RESULT,
        constructors=ProvenanceConstructorSpec[SizingRunFailureConstructionContext](
            context_type=SizingRunFailureConstructionContext,
            label_constructor=build_sizing_run_failure_label,
            uuid5_name_constructor=build_sizing_run_failure_uuid5,
            payload_constructor=build_sizing_run_failure_payload,
            metadata_constructor=build_sizing_run_failure_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "precedes_failure", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.BLOCKER, "annotates_failure", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.WARNING, "annotates_failure", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces_failure_record", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
        ),
        allowed_outgoing=(),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.INVALID_EVIDENCE,
        node_type=ProvenanceNodeType.INTERMEDIATE,
        constructors=ProvenanceConstructorSpec[InvalidEvidenceConstructionContext](
            context_type=InvalidEvidenceConstructionContext,
            label_constructor=build_invalid_evidence_label,
            uuid5_name_constructor=build_invalid_evidence_uuid5,
            payload_constructor=build_invalid_evidence_payload,
            metadata_constructor=build_invalid_evidence_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "produced_unverified", ProvenanceConcept.INVALID_EVIDENCE),
        ),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.INVALID_EVIDENCE, "invalidates", ProvenanceConcept.SIZING_RESULT),
        ),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.RUNTIME_FAILURE,
        node_type=ProvenanceNodeType.BLOCKER,
        constructors=ProvenanceConstructorSpec[RuntimeFailureConstructionContext](
            context_type=RuntimeFailureConstructionContext,
            label_constructor=build_runtime_failure_label,
            uuid5_name_constructor=build_runtime_failure_uuid5,
            payload_constructor=build_runtime_failure_payload,
            metadata_constructor=build_runtime_failure_metadata,
        ),
        allowed_incoming=(),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
        ),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.WARNING,
        node_type=ProvenanceNodeType.WARNING,
        constructors=ProvenanceConstructorSpec[WarningOccurrenceConstructionContext](
            context_type=WarningOccurrenceConstructionContext,
            label_constructor=build_warning_label,
            uuid5_name_constructor=build_warning_uuid5,
            payload_constructor=build_warning_payload,
            metadata_constructor=build_warning_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "emits", ProvenanceConcept.WARNING),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "emits", ProvenanceConcept.WARNING),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "emits", ProvenanceConcept.WARNING),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "emits", ProvenanceConcept.WARNING),
        ),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.WARNING, "annotates", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.WARNING, "annotates_failure", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
        ),
    ),
    ProvenanceConceptSpec(
        concept=ProvenanceConcept.BLOCKER,
        node_type=ProvenanceNodeType.BLOCKER,
        constructors=ProvenanceConstructorSpec[BlockerOccurrenceConstructionContext](
            context_type=BlockerOccurrenceConstructionContext,
            label_constructor=build_blocker_label,
            uuid5_name_constructor=build_blocker_uuid5,
            payload_constructor=build_blocker_payload,
            metadata_constructor=build_blocker_metadata,
        ),
        allowed_incoming=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "emits", ProvenanceConcept.BLOCKER),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "emits", ProvenanceConcept.BLOCKER),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "emits", ProvenanceConcept.BLOCKER),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "emits", ProvenanceConcept.BLOCKER),
        ),
        allowed_outgoing=(
            ProvenanceRelationSpec(ProvenanceConcept.BLOCKER, "blocks", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.BLOCKER, "annotates_failure", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
        ),
    ),
)
```

### 22.11 Topology Infrastructure

```python
@dataclass(frozen=True, slots=True)
class TopologyCounters:
    catalog_count: int = 0
    unique_candidate_count: int = 0
    materialized_candidate_count: int = 0
    attempted_rating_count: int = 0
    completed_rating_count: int = 0
    verified_rating_count: int = 0
    claimed_rating_count: int = 0
    invalid_evidence_count: int = 0
    evaluated_candidate_count: int = 0
    optimizer_count: int = 0
    sizing_result_count: int = 0
    sizing_run_failure_result_count: int = 0
    runtime_failure_count: int = 0
    warning_content_count: int = 0
    blocker_content_count: int = 0
    feasible_candidate_count: int = 0


@dataclass(frozen=True, slots=True)
class TopologyConstructionContext:
    counters: TopologyCounters
    root_selection: RootTopologySelection


NodeMultiplicityConstructor = Callable[[TopologyConstructionContext], int]


NODE_MULTIPLICITY_CONSTRUCTORS: Mapping[str, NodeMultiplicityConstructor] = {
    "0": lambda ctx: 0,
    "1": lambda ctx: 1,
    "selected_root_case_revision_count": lambda ctx: ctx.root_selection.root_case_revision_count,
    "selected_root_external_count": lambda ctx: ctx.root_selection.root_external_count,
    "catalog_count": lambda ctx: ctx.counters.catalog_count,
    "unique_candidate_count": lambda ctx: ctx.counters.unique_candidate_count,
    "materialized_candidate_count": lambda ctx: ctx.counters.materialized_candidate_count,
    "completed_rating_count": lambda ctx: ctx.counters.completed_rating_count,
    "verified_rating_count": lambda ctx: ctx.counters.verified_rating_count,
    "claimed_rating_count": lambda ctx: ctx.counters.claimed_rating_count,
    "invalid_evidence_count": lambda ctx: ctx.counters.invalid_evidence_count,
    "evaluated_candidate_count": lambda ctx: ctx.counters.evaluated_candidate_count,
    "optimizer_count": lambda ctx: ctx.counters.optimizer_count,
    "sizing_result_count": lambda ctx: ctx.counters.sizing_result_count,
    "sizing_run_failure_result_count": lambda ctx: ctx.counters.sizing_run_failure_result_count,
    "runtime_failure_count": lambda ctx: ctx.counters.runtime_failure_count,
    "warning_content_count": lambda ctx: ctx.counters.warning_content_count,
    "blocker_content_count": lambda ctx: ctx.counters.blocker_content_count,
    "feasible_candidate_count": lambda ctx: ctx.counters.feasible_candidate_count,
}


# ── Topology Invariants (typed callables) ─────────────────────

TopologyInvariant = Callable[[TopologyConstructionContext], None]


def invariant_selected_root_sum_eq_1(ctx: TopologyConstructionContext) -> None:
    s = ctx.root_selection.root_case_revision_count + ctx.root_selection.root_external_count
    if s != 1:
        raise ValueError(f"root count sum must be 1, got {s}")


def invariant_catalog_count_eq_0(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.catalog_count != 0:
        raise ValueError(f"expected catalog_count=0, got {ctx.counters.catalog_count}")


def invariant_catalog_count_ge_1(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.catalog_count < 1:
        raise ValueError(f"expected catalog_count>=1, got {ctx.counters.catalog_count}")


def invariant_unique_candidate_count_eq_0(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.unique_candidate_count != 0:
        raise ValueError(f"expected unique_candidate_count=0, got {ctx.counters.unique_candidate_count}")


def invariant_unique_candidate_count_ge_1(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.unique_candidate_count < 1:
        raise ValueError(f"expected unique_candidate_count>=1, got {ctx.counters.unique_candidate_count}")


def invariant_no_candidate_nodes(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.unique_candidate_count != 0 or ctx.counters.materialized_candidate_count != 0:
        raise ValueError("candidate nodes present when none expected")


def invariant_verified_rating_eq_unique(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.verified_rating_count != ctx.counters.unique_candidate_count:
        raise ValueError(f"verified_rating_count ({ctx.counters.verified_rating_count}) != unique_candidate_count ({ctx.counters.unique_candidate_count})")


def invariant_run_failure_present(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.runtime_failure_count < 1:
        raise ValueError("expected at least one runtime failure")


def invariant_no_feasible_candidate(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.feasible_candidate_count != 0:
        raise ValueError("NO_FEASIBLE requires feasible_candidate_count=0")


def invariant_feasible_candidate_present(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.feasible_candidate_count < 1:
        raise ValueError("SUCCEEDED requires feasible_candidate_count>=1")


def invariant_feasible_count_range(ctx: TopologyConstructionContext) -> None:
    if not (0 <= ctx.counters.feasible_candidate_count <= ctx.counters.unique_candidate_count):
        raise ValueError(
            f"feasible_candidate_count ({ctx.counters.feasible_candidate_count}) "
            f"not in [0, unique_candidate_count ({ctx.counters.unique_candidate_count})]"
        )


def invariant_feasible_le_verified(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.feasible_candidate_count > ctx.counters.verified_rating_count:
        raise ValueError(
            f"feasible_candidate_count ({ctx.counters.feasible_candidate_count}) > "
            f"verified_rating_count ({ctx.counters.verified_rating_count})"
        )


def invariant_standard_result_node_present(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.sizing_result_count != 1:
        raise ValueError(
            f"expected sizing_result_count=1, got {ctx.counters.sizing_result_count}"
        )
    if ctx.counters.sizing_run_failure_result_count != 0:
        raise ValueError(
            "sizing_run_failure_result must be absent "
            "for a standard-result topology"
        )


def invariant_cap_exceeded_before_materialization(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.materialized_candidate_count > 0:
        raise ValueError("candidate materialization occurred before cap exceeded")


def invariant_no_manufacturable_candidates(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.unique_candidate_count > 0 or ctx.counters.materialized_candidate_count > 0:
        raise ValueError("manufacturable candidates present when none expected")


def invariant_all_candidates_verified(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.verified_rating_count < ctx.counters.unique_candidate_count:
        raise ValueError("not all candidates verified")


def invariant_provider_mismatch_before_optimizer(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.optimizer_count > 0:
        raise ValueError("optimizer present when provider mismatch should have prevented it")


def invariant_failure_result_node_present(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.sizing_run_failure_result_count != 1:
        raise ValueError("expected exactly one sizing_run_failure_result node")


def invariant_standard_result_absent(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.sizing_result_count > 0:
        raise ValueError("standard result present when only failure result expected")


def invariant_evaluated_eq_unique_eq_verified(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.evaluated_candidate_count != ctx.counters.unique_candidate_count:
        raise ValueError(f"evaluated ({ctx.counters.evaluated_candidate_count}) != unique ({ctx.counters.unique_candidate_count})")
    if ctx.counters.verified_rating_count != ctx.counters.unique_candidate_count:
        raise ValueError(f"verified ({ctx.counters.verified_rating_count}) != unique ({ctx.counters.unique_candidate_count})")


def invariant_attempted_eq_completed_plus_1(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.attempted_rating_count != ctx.counters.completed_rating_count + 1:
        raise ValueError(f"attempted ({ctx.counters.attempted_rating_count}) != completed ({ctx.counters.completed_rating_count}) + 1")


def invariant_completed_eq_verified_plus_1(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.completed_rating_count != ctx.counters.verified_rating_count + 1:
        raise ValueError(f"completed ({ctx.counters.completed_rating_count}) != verified ({ctx.counters.verified_rating_count}) + 1")


def invariant_claimed_node_count_1(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.claimed_rating_count != 1:
        raise ValueError(f"expected 1 claimed node, got {ctx.counters.claimed_rating_count}")


def invariant_optimizer_present(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.optimizer_count < 1:
        raise ValueError("optimizer node absent")


def invariant_failed_candidate_no_rating_result(ctx: TopologyConstructionContext) -> None:
    if ctx.counters.completed_rating_count > 0:
        raise ValueError("completed rating present when candidate failed")


def invariant_0_le_materialized_le_unique(ctx: TopologyConstructionContext) -> None:
    if not (0 <= ctx.counters.materialized_candidate_count <= ctx.counters.unique_candidate_count):
        raise ValueError(f"materialized ({ctx.counters.materialized_candidate_count}) not in [0, unique ({ctx.counters.unique_candidate_count})]")
```

> **NON-NORMATIVE GENERATED SUMMARY.** All constructor function names are resolved via `PROVENANCE_CONCEPT_REGISTRY` (14 typed entries, each with direct callable references). Allowed/forbidden termination classes are derived from `TERMINATION_TOPOLOGY_REGISTRY`. Node multiplicity is resolved via `NODE_MULTIPLICITY_CONSTRUCTORS`. This table is for human reference only and is not an authoritative contract.

| Concept | node_type | label_constructor | uuid5_name_constructor | payload_constructor | metadata_constructor | allowed_incoming | allowed_outgoing |
|---------|-----------|-------------------|------------------------|---------------------|----------------------|------------------|------------------|
| ROOT_CASE_REVISION | CASE_REVISION | `build_revision_label` | `build_root_case_revision_uuid5` | `build_root_case_revision_payload` | `build_root_case_revision_metadata` | () | (("initiates", "SIZING_RUN"),) |
| ROOT_EXTERNAL | EXTERNAL | `build_external_label` | `build_root_external_uuid5` | `build_root_external_payload` | `build_root_external_metadata` | () | (("initiates", "SIZING_RUN"),) |
| SIZING_RUN | CALCULATION_RUN | `build_sizing_run_label` | `build_sizing_run_uuid5` | `build_sizing_run_payload` | `build_sizing_run_metadata` | (("initiates", "ROOT_CASE_REVISION"), ("initiates", "ROOT_EXTERNAL")) | (("consumes", "CATALOG_SNAPSHOT"), ("executes", "SIZING_OPTIMIZER"), ("produces", "SIZING_RESULT"), ("produces_failure_record", "SIZING_RUN_FAILURE_RESULT"), ("emits", "WARNING"), ("emits", "BLOCKER")) |
| SIZING_OPTIMIZER | OPTIMIZER | `build_optimizer_label` | `build_optimizer_uuid5` | `build_optimizer_payload` | `build_optimizer_metadata` | (("executes", "SIZING_RUN"), ("evaluated_by", "TASK008_RATING_RESULT")) | (("produces", "SIZING_RESULT"), ("precedes_failure", "SIZING_RUN_FAILURE_RESULT"), ("emits", "WARNING"), ("emits", "BLOCKER")) |
| CATALOG_SNAPSHOT | INTERMEDIATE | `build_catalog_label` | `build_catalog_uuid5` | `build_catalog_payload` | `build_catalog_metadata` | (("consumes", "SIZING_RUN"),) | (("generates", "CANDIDATE"), ("emits", "WARNING"), ("emits", "BLOCKER")) |
| CANDIDATE | INTERMEDIATE | `build_candidate_label` | `build_candidate_uuid5` | `build_candidate_payload` | `build_candidate_metadata` | (("generates", "CATALOG_SNAPSHOT"),) | (("rated_as", "TASK008_RATING_RESULT"), ("rated_as_claimed", "CLAIMED_TASK008_RATING_RESULT"), ("produced_unverified", "INVALID_EVIDENCE"), ("emits", "WARNING"), ("emits", "BLOCKER")) |
| TASK008_RATING_RESULT | RESULT | `build_rating_result_label` | `build_rating_result_uuid5` | `build_rating_result_payload` | `build_rating_result_metadata` | (("rated_as", "CANDIDATE"),) | (("evaluated_by", "SIZING_OPTIMIZER"),) |
| CLAIMED_TASK008_RATING_RESULT | INTERMEDIATE | `build_claimed_rating_label` | `build_claimed_rating_uuid5` | `build_claimed_rating_payload` | `build_claimed_rating_metadata` | (("rated_as_claimed", "CANDIDATE"),) | () |
| SIZING_RESULT | RESULT | `build_sizing_result_label` | `build_sizing_result_uuid5` | `build_sizing_result_payload` | `build_sizing_result_metadata` | (("produces", "SIZING_OPTIMIZER"), ("fails", "RUNTIME_FAILURE"), ("blocks", "BLOCKER"), ("annotates", "WARNING"), ("produces", "SIZING_RUN")) | () |
| SIZING_RUN_FAILURE_RESULT | RESULT | `build_sizing_run_failure_label` | `build_sizing_run_failure_uuid5` | `build_sizing_run_failure_payload` | `build_sizing_run_failure_metadata` | (("precedes_failure", "SIZING_OPTIMIZER"), ("fails", "RUNTIME_FAILURE"), ("annotates_failure", "BLOCKER"), ("annotates_failure", "WARNING"), ("produces_failure_record", "SIZING_RUN")) | () |
| INVALID_EVIDENCE | INTERMEDIATE | `build_invalid_evidence_label` | `build_invalid_evidence_uuid5` | `build_invalid_evidence_payload` | `build_invalid_evidence_metadata` | (("produced_unverified", "CANDIDATE"),) | (("invalidates", "SIZING_RESULT"),) |
| RUNTIME_FAILURE | BLOCKER | `build_runtime_failure_label` | `build_runtime_failure_uuid5` | `build_runtime_failure_payload` | `build_runtime_failure_metadata` | () | (("fails", "SIZING_RESULT"), ("fails", "SIZING_RUN_FAILURE_RESULT")) |
| WARNING | WARNING | `build_warning_label` | `build_warning_uuid5` | `build_warning_payload` | `build_warning_metadata` | (("emits", "SIZING_RUN"), ("emits", "CATALOG_SNAPSHOT"), ("emits", "CANDIDATE"), ("emits", "SIZING_OPTIMIZER")) | (("annotates", "SIZING_RESULT"), ("annotates_failure", "SIZING_RUN_FAILURE_RESULT")) |
| BLOCKER | BLOCKER | `build_blocker_label` | `build_blocker_uuid5` | `build_blocker_payload` | `build_blocker_metadata` | (("emits", "SIZING_RUN"), ("emits", "CATALOG_SNAPSHOT"), ("emits", "CANDIDATE"), ("emits", "SIZING_OPTIMIZER")) | (("blocks", "SIZING_RESULT"), ("annotates_failure", "SIZING_RUN_FAILURE_RESULT")) |

### 22.12 TerminationTopologySpec Registry

The typed constant `TERMINATION_TOPOLOGY_REGISTRY` is the single authoritative source:

```python
@dataclass(frozen=True, slots=True)
class TerminationTopologySpec:
    termination_class: TerminationClass
    root_topology_constructor: RootTopologyConstructor
    result_concept: ProvenanceConcept
    base_node_multiplicities: tuple[tuple[ProvenanceConcept, str], ...]
    static_base_edges: tuple[ProvenanceRelationSpec, ...]
    forbidden_concepts: tuple[ProvenanceConcept, ...]
    allowed_message_owner_kinds: tuple[MessageOwnerKind, ...]
    minimum_warning_occurrences: int
    minimum_blocker_occurrences: int
    counter_invariants: tuple[TopologyInvariant, ...]
```

The typed constant `TERMINATION_TOPOLOGY_REGISTRY` is the single authoritative source:

```python
TERMINATION_TOPOLOGY_REGISTRY: tuple[TerminationTopologySpec, ...] = (
    TerminationTopologySpec(
        termination_class=TerminationClass.INVALID_REQUEST,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.CATALOG_SNAPSHOT, ProvenanceConcept.CANDIDATE, ProvenanceConcept.TASK008_RATING_RESULT, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.RUNTIME_FAILURE, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN,),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=1,
        counter_invariants=(
            invariant_catalog_count_eq_0,
            invariant_unique_candidate_count_eq_0,
            invariant_no_candidate_nodes,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.INVALID_CATALOG,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.CANDIDATE, ProvenanceConcept.TASK008_RATING_RESULT, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.RUNTIME_FAILURE, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=1,
        counter_invariants=(
            invariant_catalog_count_ge_1,
            invariant_unique_candidate_count_eq_0,
            invariant_no_candidate_nodes,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.CATALOG_IDENTITY_MISMATCH,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.CANDIDATE, ProvenanceConcept.TASK008_RATING_RESULT, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.RUNTIME_FAILURE, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=1,
        counter_invariants=(
            invariant_catalog_count_ge_1,
            invariant_unique_candidate_count_eq_0,
            invariant_no_candidate_nodes,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.CAP_EXCEEDED,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.CANDIDATE, ProvenanceConcept.TASK008_RATING_RESULT, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.RUNTIME_FAILURE, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=1,
        counter_invariants=(
            invariant_catalog_count_ge_1,
            invariant_unique_candidate_count_ge_1,
            invariant_cap_exceeded_before_materialization,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.NO_MANUFACTURABLE_CANDIDATE,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.CANDIDATE, ProvenanceConcept.TASK008_RATING_RESULT, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.RUNTIME_FAILURE, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=1,
        counter_invariants=(
            invariant_catalog_count_ge_1,
            invariant_unique_candidate_count_eq_0,
            invariant_no_manufacturable_candidates,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.NO_FEASIBLE_CANDIDATE,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.CANDIDATE, "unique_candidate_count"),
            (ProvenanceConcept.TASK008_RATING_RESULT, "verified_rating_count"),
            (ProvenanceConcept.SIZING_OPTIMIZER, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as", ProvenanceConcept.TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.TASK008_RATING_RESULT, "evaluated_by", ProvenanceConcept.SIZING_OPTIMIZER),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "executes", ProvenanceConcept.SIZING_OPTIMIZER),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "produces", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.RUNTIME_FAILURE),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT, MessageOwnerKind.CANDIDATE, MessageOwnerKind.OPTIMIZER),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=0,
        counter_invariants=(
            invariant_unique_candidate_count_ge_1,
            invariant_evaluated_eq_unique_eq_verified,
            invariant_no_feasible_candidate,
            invariant_feasible_count_range,
            invariant_feasible_le_verified,
            invariant_standard_result_node_present,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.SUCCEEDED,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.CANDIDATE, "unique_candidate_count"),
            (ProvenanceConcept.TASK008_RATING_RESULT, "unique_candidate_count"),
            (ProvenanceConcept.SIZING_OPTIMIZER, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as", ProvenanceConcept.TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.TASK008_RATING_RESULT, "evaluated_by", ProvenanceConcept.SIZING_OPTIMIZER),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "executes", ProvenanceConcept.SIZING_OPTIMIZER),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "produces", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.RUNTIME_FAILURE),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT, MessageOwnerKind.CANDIDATE, MessageOwnerKind.OPTIMIZER),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=0,
        counter_invariants=(
            invariant_unique_candidate_count_ge_1,
            invariant_evaluated_eq_unique_eq_verified,
            invariant_feasible_candidate_present,
            invariant_feasible_count_range,
            invariant_feasible_le_verified,
            invariant_standard_result_node_present,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.PROPERTY_PROVIDER_IDENTITY_MISMATCH,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.CANDIDATE, "unique_candidate_count"),
            (ProvenanceConcept.TASK008_RATING_RESULT, "verified_rating_count"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as", ProvenanceConcept.TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.RUNTIME_FAILURE),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT, MessageOwnerKind.CANDIDATE),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=1,
        counter_invariants=(
            invariant_verified_rating_eq_unique,
            invariant_provider_mismatch_before_optimizer,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.RATING_RESULT_INTEGRITY_FAILED,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.CANDIDATE, "unique_candidate_count"),
            (ProvenanceConcept.TASK008_RATING_RESULT, "verified_rating_count"),
            (ProvenanceConcept.INVALID_EVIDENCE, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as", ProvenanceConcept.TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "produced_unverified", ProvenanceConcept.INVALID_EVIDENCE),
            ProvenanceRelationSpec(ProvenanceConcept.INVALID_EVIDENCE, "invalidates", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT, ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.RUNTIME_FAILURE),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT, MessageOwnerKind.CANDIDATE),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=1,
        counter_invariants=(
            invariant_completed_eq_verified_plus_1,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.RUNTIME_FAILED_REQUEST_VALIDATION,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.RUNTIME_FAILURE, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.CATALOG_SNAPSHOT, ProvenanceConcept.CANDIDATE, ProvenanceConcept.TASK008_RATING_RESULT, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN,),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=0,
        counter_invariants=(
            invariant_catalog_count_eq_0,
            invariant_no_candidate_nodes,
            invariant_run_failure_present,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.RUNTIME_FAILED_CATALOG_VALIDATION,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.RUNTIME_FAILURE, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.CANDIDATE, ProvenanceConcept.TASK008_RATING_RESULT, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=0,
        counter_invariants=(
            invariant_catalog_count_ge_1,
            invariant_no_candidate_nodes,
            invariant_run_failure_present,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.RUNTIME_FAILED_CANDIDATE_MATERIALIZATION,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.CANDIDATE, "materialized_candidate_count"),
            (ProvenanceConcept.RUNTIME_FAILURE, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.TASK008_RATING_RESULT, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT, MessageOwnerKind.CANDIDATE),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=0,
        counter_invariants=(
            invariant_catalog_count_ge_1,
            invariant_0_le_materialized_le_unique,
            invariant_run_failure_present,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.RUNTIME_FAILED_PRE_RATING,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.CANDIDATE, "unique_candidate_count"),
            (ProvenanceConcept.RUNTIME_FAILURE, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.TASK008_RATING_RESULT, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT, MessageOwnerKind.CANDIDATE),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=0,
        counter_invariants=(
            invariant_catalog_count_ge_1,
            invariant_unique_candidate_count_ge_1,
            invariant_run_failure_present,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.RUNTIME_FAILED_RATING_CALL,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.CANDIDATE, "unique_candidate_count"),
            (ProvenanceConcept.TASK008_RATING_RESULT, "completed_rating_count"),
            (ProvenanceConcept.RUNTIME_FAILURE, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as", ProvenanceConcept.TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT, MessageOwnerKind.CANDIDATE),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=0,
        counter_invariants=(
            invariant_attempted_eq_completed_plus_1,
            invariant_failed_candidate_no_rating_result,
            invariant_run_failure_present,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.RUNTIME_FAILED_RATING_VERIFICATION,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.CANDIDATE, "unique_candidate_count"),
            (ProvenanceConcept.TASK008_RATING_RESULT, "verified_rating_count"),
            (ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT, "1"),
            (ProvenanceConcept.RUNTIME_FAILURE, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as", ProvenanceConcept.TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as_claimed", ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.SIZING_OPTIMIZER, ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT, MessageOwnerKind.CANDIDATE),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=0,
        counter_invariants=(
            invariant_completed_eq_verified_plus_1,
            invariant_claimed_node_count_1,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.RUNTIME_FAILED_OPTIMIZATION,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.CANDIDATE, "unique_candidate_count"),
            (ProvenanceConcept.TASK008_RATING_RESULT, "evaluated_candidate_count"),
            (ProvenanceConcept.SIZING_OPTIMIZER, "1"),
            (ProvenanceConcept.RUNTIME_FAILURE, "1"),
            (ProvenanceConcept.SIZING_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as", ProvenanceConcept.TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.TASK008_RATING_RESULT, "evaluated_by", ProvenanceConcept.SIZING_OPTIMIZER),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "executes", ProvenanceConcept.SIZING_OPTIMIZER),
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "produces", ProvenanceConcept.SIZING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces", ProvenanceConcept.SIZING_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT, ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT, MessageOwnerKind.CANDIDATE, MessageOwnerKind.OPTIMIZER),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=0,
        counter_invariants=(
            invariant_evaluated_eq_unique_eq_verified,
            invariant_optimizer_present,
            invariant_run_failure_present,
            invariant_selected_root_sum_eq_1,
        ),
    ),
    TerminationTopologySpec(
        termination_class=TerminationClass.RUNTIME_FAILED_RESULT_CONSTRUCTION,
        root_topology_constructor=derive_root_topology,
        result_concept=ProvenanceConcept.SIZING_RUN_FAILURE_RESULT,
        base_node_multiplicities=(
            (ProvenanceConcept.ROOT_CASE_REVISION, "selected_root_case_revision_count"),
            (ProvenanceConcept.ROOT_EXTERNAL, "selected_root_external_count"),
            (ProvenanceConcept.SIZING_RUN, "1"),
            (ProvenanceConcept.CATALOG_SNAPSHOT, "catalog_count"),
            (ProvenanceConcept.CANDIDATE, "unique_candidate_count"),
            (ProvenanceConcept.TASK008_RATING_RESULT, "evaluated_candidate_count"),
            (ProvenanceConcept.SIZING_OPTIMIZER, "1"),
            (ProvenanceConcept.RUNTIME_FAILURE, "1"),
            (ProvenanceConcept.SIZING_RUN_FAILURE_RESULT, "1"),
        ),
        static_base_edges=(
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "consumes", ProvenanceConcept.CATALOG_SNAPSHOT),
            ProvenanceRelationSpec(ProvenanceConcept.CATALOG_SNAPSHOT, "generates", ProvenanceConcept.CANDIDATE),
            ProvenanceRelationSpec(ProvenanceConcept.CANDIDATE, "rated_as", ProvenanceConcept.TASK008_RATING_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.TASK008_RATING_RESULT, "evaluated_by", ProvenanceConcept.SIZING_OPTIMIZER),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "executes", ProvenanceConcept.SIZING_OPTIMIZER),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_OPTIMIZER, "precedes_failure", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.RUNTIME_FAILURE, "fails", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
            ProvenanceRelationSpec(ProvenanceConcept.SIZING_RUN, "produces_failure_record", ProvenanceConcept.SIZING_RUN_FAILURE_RESULT),
        ),
        forbidden_concepts=(ProvenanceConcept.INVALID_EVIDENCE, ProvenanceConcept.CLAIMED_TASK008_RATING_RESULT, ProvenanceConcept.SIZING_RESULT),
        allowed_message_owner_kinds=(MessageOwnerKind.SIZING_RUN, MessageOwnerKind.CATALOG_SNAPSHOT, MessageOwnerKind.CANDIDATE, MessageOwnerKind.OPTIMIZER),
        minimum_warning_occurrences=0,
        minimum_blocker_occurrences=0,
        counter_invariants=(
            invariant_evaluated_eq_unique_eq_verified,
            invariant_failure_result_node_present,
            invariant_standard_result_absent,
            invariant_selected_root_sum_eq_1,
        ),
    ),
)
```



### 22.13 Topology Resolution

```python
@dataclass(frozen=True, slots=True)
class ResolvedTopology:
    node_multiplicities: tuple[tuple[ProvenanceConcept, int], ...]
    edges: tuple[ProvenanceRelationSpec, ...]


def resolve_termination_topology(
    spec: TerminationTopologySpec,
    request_kind: SizingRunRequestKind,
    design_case_revision_id: UUID | None,
    counters: TopologyCounters,
) -> ResolvedTopology:
    root_selection = spec.root_topology_constructor(request_kind, design_case_revision_id)
    context = TopologyConstructionContext(counters=counters, root_selection=root_selection)

    # Build node multiplicities from base specs
    seen_concepts: set[ProvenanceConcept] = set()
    node_multiplicities: list[tuple[ProvenanceConcept, int]] = []
    for concept, formula_name in spec.base_node_multiplicities:
        if concept in seen_concepts:
            raise ValueError(f"duplicate concept in base_node_multiplicities: {concept}")
        seen_concepts.add(concept)
        count = NODE_MULTIPLICITY_CONSTRUCTORS[formula_name](context)
        node_multiplicities.append((concept, count))

    multiplicity_by_concept: dict[ProvenanceConcept, int] = dict(node_multiplicities)

    # Forbidden concept check — use concept key directly, not formula name
    for forbidden in spec.forbidden_concepts:
        if multiplicity_by_concept.get(forbidden, 0) != 0:
            raise ValueError(f"forbidden concept {forbidden} has positive multiplicity")

    # Result multiplicity check
    result_count = multiplicity_by_concept.get(spec.result_concept, 0)
    if result_count != 1:
        raise ValueError(f"expected exactly 1 {spec.result_concept} node, got {result_count}")

    # Root concept multiplicity matches RootTopologySelection
    if root_selection.root_concept is ProvenanceConcept.ROOT_CASE_REVISION:
        root_count = multiplicity_by_concept.get(ProvenanceConcept.ROOT_CASE_REVISION, 0)
        if root_count != root_selection.root_case_revision_count:
            raise ValueError(
                f"ROOT_CASE_REVISION multiplicity {root_count} "
                f"does not match selection {root_selection.root_case_revision_count}"
            )
    elif root_selection.root_concept is ProvenanceConcept.ROOT_EXTERNAL:
        root_count = multiplicity_by_concept.get(ProvenanceConcept.ROOT_EXTERNAL, 0)
        if root_count != root_selection.root_external_count:
            raise ValueError(
                f"ROOT_EXTERNAL multiplicity {root_count} "
                f"does not match selection {root_selection.root_external_count}"
            )

    # Exactly-one-root anti-tamper check
    resolved_case = multiplicity_by_concept.get(ProvenanceConcept.ROOT_CASE_REVISION, 0)
    resolved_external = multiplicity_by_concept.get(ProvenanceConcept.ROOT_EXTERNAL, 0)
    if resolved_case + resolved_external != 1:
        raise ValueError("must contain exactly one root")
    if resolved_case != root_selection.root_case_revision_count:
        raise ValueError("case root count mismatch")
    if resolved_external != root_selection.root_external_count:
        raise ValueError("external root count mismatch")

    # Build edge set with dedup
    edges = [root_selection.initiates_edge]
    seen_edges: set[tuple[ProvenanceConcept, str, ProvenanceConcept]] = set()
    seen_edges.add((root_selection.initiates_edge.source_concept, root_selection.initiates_edge.relation, root_selection.initiates_edge.target_concept))

    for edge in spec.static_base_edges:
        key = (edge.source_concept, edge.relation, edge.target_concept)
        if key in seen_edges:
            raise ValueError(f"duplicate edge: {edge.source_concept} --{edge.relation}--> {edge.target_concept}")
        seen_edges.add(key)
        # Edge endpoint checks
        source_count = multiplicity_by_concept.get(edge.source_concept, 0)
        target_count = multiplicity_by_concept.get(edge.target_concept, 0)
        if source_count == 0:
            raise ValueError(f"edge source {edge.source_concept} has zero multiplicity")
        if target_count == 0:
            raise ValueError(f"edge target {edge.target_concept} has zero multiplicity")
        edges.append(edge)

    # Run invariants
    for invariant_fn in spec.counter_invariants:
        invariant_fn(context)

    return ResolvedTopology(
        node_multiplicities=tuple(node_multiplicities),
        edges=tuple(edges),
    )
```


### 22.14 Message Content and Occurrence Multiset

Each message content (warning or blocker) is uniquely identified by its `engineering_message_digest`. When multiple source events produce messages with identical digest, they share one unique content record but generate distinct occurrences.

- **Unique content collections:** Warnings and blockers are deduplicated by `engineering_message_digest`. Two messages with the same digest are stored once in the unique content collection (`warnings`/`blockers` tuple).
- **Occurrence multisets:** Each source event that generates a warning or blocker produces an occurrence. Multiple occurrences may share the same `message_digest`.
- **Invariant:** `occurrence_count >= unique_content_count`. Every unique content digest has at least one occurrence.
- **Occurrence index:** Within each owner scope, occurrences are grouped by `(owner_kind, owner_id, occurrence_kind, message_digest)`. Indices are assigned consecutively from 0 within each group.
- **Canonical sort key:** `(owner_kind.value, owner_id, occurrence_kind.value, message_digest, occurrence_index, occurrence_digest)`.

This separation ensures that the result payload carries both the unique message content (for human-readable diagnostics) and the full occurrence record (for provenance completeness). The occurrence digests bridge the two collections without duplicating full message content.

### 22.15 MessageOccurrenceKind, MessageOwnerKind, and MessageOccurrenceSnapshot

**MessageOccurrenceSnapshot** replaces the earlier MessageOccurrenceIdentity concept. Each snapshot captures a single occurrence of a warning or blocker message within its owner's scope.

```text
MessageOccurrenceSnapshot
- owner_kind: MessageOwnerKind
- owner_id: str
- occurrence_kind: MessageOccurrenceKind
- message_digest: str
- occurrence_index: int
- occurrence_digest: str       (sha256 of the complete occurrence payload)
```

The full `message: EngineeringMessage` field is NOT retained in the snapshot. Only the digest link (`message_digest`) survives into the occurrence record.

**Invariant:**
- Warning occurrence → `occurrence_kind == MessageOccurrenceKind.WARNING` and `message_digest` is in the canonical warnings collection (the owner's deduplicated warning message digests).
- Blocker occurrence → `occurrence_kind == MessageOccurrenceKind.BLOCKER` and `message_digest` is in the canonical blockers collection (the owner's deduplicated blocker message digests).

**Exact occurrence payload:**

```python
message_occurrence_payload = {
    "occurrence_kind": occurrence_kind.value,
    "owner_kind": owner_kind.value,
    "owner_id": owner_id,
    "message_digest": message_digest,
    "occurrence_index": occurrence_index,
}
occurrence_digest = sha256_digest(message_occurrence_payload)
```

**Canonical occurrence index rules:**

1. Within the same owner, messages are sorted by canonical message sort key (§8).
2. For identical `message_digest` values within the same owner, `occurrence_index` is assigned from 0 consecutively.
3. `occurrence_index` is independent of insertion order — it is purely a function of the canonical sort.
4. UUID5 formula uses all fields to guarantee distinctness across owners and occurrences.
5. `occurrence_digest` covers all fields — any tampering with a snapshot field produces a different digest.

**Provenance node UUID5 for WARNING/BLOCKER:**

```python
uuid5_name = f"{occurrence_kind.value}:{owner_kind.value}:{owner_id}:{message_digest}:{occurrence_index}"
node_uuid = uuid5(TASK009_PROVENANCE_NAMESPACE, uuid5_name)
```

**Persistence fields in SizingOptimizationResult:**

```text
warning_occurrences: tuple[MessageOccurrenceSnapshot, ...]
blocker_occurrences: tuple[MessageOccurrenceSnapshot, ...]
```

**Persistence fields in SizingRunFailureResult:**

```text
warning_occurrences: tuple[MessageOccurrenceSnapshot, ...]
blocker_occurrences: tuple[MessageOccurrenceSnapshot, ...]
```

**Digest fields in SizingResultIdentity:**

```text
warning_occurrence_digests: tuple[str, ...]
blocker_occurrence_digests: tuple[str, ...]
```

**JSON/tamper rules:**

- Each `MessageOccurrenceSnapshot` is immutable after construction — all fields are frozen.
- `occurrence_digest` is the sha256 of the serialized `message_occurrence_payload` (canonical JSON, sorted keys).
- Tampering with `owner_kind`, `owner_id`, `message_digest`, or `occurrence_index` changes `occurrence_digest` and breaks the provenance node UUID5 and payload hash chain.
- The WARNING and BLOCKER provenance node's payload hash equals `occurrence_digest`.
- JSON round-trip of `SizingOptimizationResult` and `SizingRunFailureResult` must preserve every `MessageOccurrenceSnapshot` field exactly.
- `warning_occurrence_digests` and `blocker_occurrence_digests` in `SizingResultIdentity` must match the `occurrence_digest` values from the corresponding `warning_occurrences` and `blocker_occurrences` collections, in the same sorted order.
- These digest-only fields in `SizingResultIdentity` enable tamper detection on the identity payload without embedding full occurrence snapshots. Full snapshots live only in the result objects.

**UUID5 name list (canonical order, for reference):**

```text
sizing-run:{request_kind.value}:{request_digest}
catalog:{catalog_id}:{catalog_version}:{catalog_content_hash}
candidate:{source_qualified_candidate_id}
rating-result:{rating_result_hash}
claimed-rating-result:{source_qualified_candidate_id}:{evaluation_order_index}:{audit_digest}
invalid-evidence:{source_qualified_candidate_id}:{invalid_evidence_digest}
optimizer:{validated_sizing_request_identity_digest}
sizing-result:{result_hash}
sizing-run-failure:{failure_result_hash}
{occurrence_kind.value}:{owner_kind.value}:{owner_id}:{message_digest}:{occurrence_index}
runtime-failure:{failure_digest}
root-case-revision:{design_case_revision_id}
root-external:{request_kind.value}:{request_digest}
```

### 22.16 Message Owner Assignment

Each `MessageOccurrenceSnapshot` has exactly one owner, determined by precedence rules.

**Owner kinds and identity formulas:**

1. **Candidate-owned:** `owner_kind = MessageOwnerKind.CANDIDATE`, `owner_id = source_qualified_candidate_id`

2. **Catalog-owned:** `owner_kind = MessageOwnerKind.CATALOG_SNAPSHOT`, `owner_id = f"{catalog_id}:{catalog_version}:{catalog_content_hash}"`

3. **Optimizer-owned:** `owner_kind = MessageOwnerKind.OPTIMIZER`, `owner_id = validated_sizing_request_identity_digest`

4. **Sizing-run-owned:** `owner_kind = MessageOwnerKind.SIZING_RUN`, `owner_id = validated_sizing_request_identity_digest` (valid request) or `raw_request_digest` (invalid request)

**Precedence (lower number = higher priority, first match wins):**

| Precedence | Owner Kind | Condition |
|------------|-----------|-----------|
| 1 (highest) | CANDIDATE | Message generated during candidate evaluation |
| 2 | CATALOG_SNAPSHOT | Message generated during catalog validation / candidate materialization |
| 3 | OPTIMIZER | Message generated during optimization |
| 4 (lowest) | SIZING_RUN | All other messages (request validation, result construction) |

**Invariant:** Each message occurrence has exactly one owner. No occurrence belongs to multiple owners. Owner assignment is frozen at snapshot construction time and cannot be reassigned.

### 22.17 Failure-Result Two-Stage Provenance Construction

Standard result and failure result use two distinct two-stage branches.

**Failure Core Graph:**

Build `failure_core_graph` containing only nodes whose payloads are determined before the failure result node:

```text
- ROOT
- SIZING_RUN
- CATALOG_SNAPSHOT
- CANDIDATE
- VERIFIED TASK008_RATING_RESULT
- OPTIMIZER
- RUNTIME_FAILURE
- warning/blocker nodes (whose payloads are already fixed)
```

Explicitly excluded: `SIZING_RUN_FAILURE_RESULT` and all edges where this node is source or target.

```python
failure_core_provenance_digest = digest(failure_core_graph)
```

**Failure Result Hash:**

```python
failure_result_payload = {
    ...
    "core_provenance_digest": failure_core_provenance_digest,
}
failure_result_hash = sha256_digest(failure_result_payload)
```

**Final Failure Graph:**

Add `SIZING_RUN_FAILURE_RESULT` node and its connecting edges:

```text
- OPTIMIZER -> SIZING_RUN_FAILURE_RESULT "precedes_failure"
- RUNTIME_FAILURE -> SIZING_RUN_FAILURE_RESULT "fails"
- SIZING_RUN -> SIZING_RUN_FAILURE_RESULT "produces_failure_record"
- WARNING -> SIZING_RUN_FAILURE_RESULT "annotates_failure" (if applicable)
- BLOCKER -> SIZING_RUN_FAILURE_RESULT "annotates_failure" (if applicable)
```

```python
failure_final_provenance_digest = digest(final_failure_graph)
```

**verify_provenance() for failure results:**

Digest collections are integrity indexes only; they are not sufficient reconstruction sources. Verification must rebuild from full immutable audit objects:

1. Read full stored audit objects: catalogs, candidate evaluations, verified evidence, invalid evidence, claimed audits, rankings, warnings, blockers, warning_occurrences, blocker_occurrences, and the RunFailure.
2. Recompute every object digest from its full object (not from stored digests).
3. Compare recomputed digests to stored digest collections. Any mismatch is tamper evidence.
4. Derive node IDs, payload hashes, metadata, and edges from the full objects and the executable provenance concept registry (§22.3).
5. Rebuild failure core graph.
6. Verify `core_provenance_digest` matches the reconstructed core graph.
7. Recompute failure result payload and hash.
8. Rebuild `SIZING_RUN_FAILURE_RESULT` node.
9. Rebuild final failure graph with full edge set.
10. Verify `failure_final_provenance_digest`.
11. Detect node, edge, and payload tamper.

Standard result verification and failure result verification are two separate branches — no shared code path ambiguity.

**Tamper detection requirements (tests #262–264):**

- Deleting full object but retaining its digest → verification fails.
- Modifying object content but keeping old digest → verification fails.
- Modifying stored graph edges/nodes only → verification fails.
- Full objects with recomputed digests reconstruct the identical graph.

### 22.18 partial_audit

`partial_audit` is a **boolean field** on `SizingResultIdentity` and `SizingOptimizationResult`. It is not a provenance node.

**Result-level formula:**

```text
partial_audit = evaluated_candidate_count < unique_candidate_count
```

**Per-stage:**

| Stage | evaluated_candidate_count | unique_candidate_count | partial_audit |
|-------|--------------------------|----------------------|---------------|
| REQUEST_VALIDATION | 0 | 0 (unique not established) | True |
| CATALOG_VALIDATION | 0 | 0 (candidate set not established) | True |
| CANDIDATE_MATERIALIZATION | 0 | 0 (candidate set not established) | True |
| PRE_RATING | 0 | > 0 (unique set known) | True |
| RATING_CALL | attempted (includes current) | unique | True (if attempted < unique), else False |
| RATING_VERIFICATION | attempted | unique | True (if attempted < unique), else False |
| PROVIDER_MISMATCH | attempted | unique | True (if attempted < unique), else False |
| OPTIMIZATION | unique | unique | False |
| RESULT_CONSTRUCTION | unique | unique | False |

`partial_audit = True` in early stages signals that full candidate evaluation was never completed.

`CandidateEvaluation.partial_audit` is **removed** from the `CandidateEvaluation` schema and its digest payload. The candidate record only expresses its own state (UNEVALUATED, VERIFIED, INTEGRITY_INVALID, RUNTIME_FAILED) with VERIFIED subtypes for additional context. Run-level completeness is the responsibility of the result object, not individual evaluations.

### 22.19 Edge Tamper Detection

Detected through the canonical graph digest (serialized topology: nodes, edges, payload hashes). No per-edge hash field is defined in the shared `ProvenanceEdge` model.
---

## 23. Hash Canonical Contract

- All hashing uses `hexagent.core.canonical.sha256_digest()` (returns `sha256:<64hex>`).
- All identity payloads use `hexagent.core.canonical.canonical_json()` (sorted keys, no whitespace, no trailing newline).
- `result_hash = sha256_digest(SizingResultIdentity payload)` — single call, single canonicalization. `sha256_digest()` internally calls `canonical_json()`, so callers pass the payload object, not a pre-serialized string.
- `sha256_digest()` canonicalizes its input, so the caller passes the raw payload dict → canonical_json is the serialization contract.

### 23.1 Catalog Hash

`catalog_content_hash`: `sha256_digest(payload)` over non-self fields. Duplicate `assembly_option_id` validated **before** sorting for hash.

### 23.2 Numeric Normalization

- Float fields: serialized by `canonical_json` default.
- Length fields: canonical Decimal string (`"12.350"`).
- Same canonical form for catalog hash, candidate identity, JSON round-trip.

### 23.3 Candidate Evaluation Hash

Each `CandidateEvaluation` has a digest computed from `build_candidate_evaluation_payload()` (§15.1):

> The exact function and invariants are defined in §15.1 CandidateEvaluation Digest.  
> **§23.3 does not redefine the payload.** Refer to §15.1 for the authoritative `build_candidate_evaluation_payload()` function, enum `.value` serialization, None-handling rules, and state-dependent invariants.

The authoritative sort order for evaluation digests is `source_qualified_candidate_id` ascending. `evaluation_order_index` is derived as the 0-based consecutive index in this sorted list; verification: `evaluation_order_index == canonical position in sorted list`.

### 23.4 Canonical Ordering for All Collections

Before building any identity/hash/provenance payload, collections must be sorted canonically using `EngineeringMessage.code` (not `error_code`):

| Collection | Sort Key |
|-----------|----------|
| Catalog snapshots / refs | `(catalog_id, catalog_version, catalog_content_hash, source_identity, schema_version)` ascending |
| Assembly options (within snapshot) | `assembly_option_id` ASCII ascending |
| `manufacturing_metadata` tuples | `key` ASCII ascending |
| Candidate evaluations | `source_qualified_candidate_id` ascending |
| Ranking records | `rank` ascending, then `source_qualified_candidate_id` ascending |
| Diagnostics (`CandidateDiagnosticKey`) | `(diagnostic_class_rank, code, source_module, affected_paths, message)` ascending |
| Warnings / blockers | `(severity_rank, code, source_module, affected_paths, message, canonical_context_digest)` ascending |
| Evidence records (verified, invalid) | `candidate_id` ascending |
| Claimed rating audits | `(source_qualified_candidate_id, evaluation_order_index, audit_digest)` ascending |
| Claimed rating audit digests | same order as claimed rating audits |
| Warning occurrences | canonical occurrence sort key |
| Blocker occurrences | canonical occurrence sort key |
| Warning occurrence digests | same order as warning occurrences |
| Blocker occurrence digests | same order as blocker occurrences |
| Validation errors (`SizingValidationErrorSnapshot`) | `(code.value, message_key, field_path, rejected_value_digest or "", context_digest)` ascending |

Severity rank:

```text
INFO = 0
WARNING = 1
ERROR = 2
BLOCKER = 3
```

Context digest:

```python
sha256_digest({
    "entries": canonical_context_entries
})
```

This ensures insertion-order independence for all identity digests and provenance graphs.

Provenance UUID5 names for warnings and blockers include context digest to prevent node collision when the same code and message have different context:

```text
{occurrence_kind.value}:{owner_kind.value}:{owner_id}:{message_digest}:{occurrence_index}
```

---

## 24. Frozen ErrorCode Values

### 24.1 Reused

```text
INPUT_MISSING, INPUT_INCONSISTENT, UNIT_INVALID
HASH_MISMATCH               — tamper verification of built sizing identity/result
PROVENANCE_INCOMPLETE       — provenance graph missing required nodes/edges
UNSUPPORTED_SERVICE, CALCULATION_BLOCKED
CORRELATION_IMPLEMENTATION_UNAVAILABLE  — C4, unchanged
```

### 24.2 Non-Overlapping Catalog/Identity Codes

```text
CATALOG_IDENTITY_MISMATCH   — caller-supplied hash differs from computed hash
HASH_MISMATCH               — verify_hash() on already-built identity/result fails tamper
```

### 24.3 New TASK-009 Codes (14)

```text
INVALID_SIZING_REQUEST = "invalid_sizing_request"
CATALOG_MISSING = "catalog_missing"
CATALOG_INVALID = "catalog_invalid"
CATALOG_IDENTITY_MISMATCH = "catalog_identity_mismatch"
NO_MANUFACTURABLE_CANDIDATE = "no_manufacturable_candidate"
CANDIDATE_COUNT_LIMIT_EXCEEDED = "candidate_count_limit_exceeded"
INVALID_OPTIMIZATION_OBJECTIVE = "invalid_optimization_objective"
INVALID_TOP_N = "invalid_top_n"
UNSUPPORTED_SIZING_CONSTRAINT = "unsupported_sizing_constraint"
RATING_RESULT_INTEGRITY_FAILED = "rating_result_integrity_failed"
NO_FEASIBLE_CANDIDATE = "no_feasible_candidate"
TOP_N_REDUCED_TO_FEASIBLE_COUNT = "top_n_reduced_to_feasible_count"
REQUIRED_DUTY_NOT_MET = "required_duty_not_met"
PROPERTY_PROVIDER_IDENTITY_MISMATCH = "property_provider_identity_mismatch"
```

No synonymous duplicates.

---

## 25. Terminology

| Imprecise | Precise |
|-----------|---------|
| "approved catalog snapshots" | "caller-supplied, structurally validated, hash-verified catalog snapshots" |
| "organization-approved master catalogs" | reserved for TASK-016 |

---

## 26. Exclusions

Same as Round 3: no pressure-drop, velocity, optimization methods, cost, materials, API, C4, multi-phase.

---

## 27. Required Test Matrix

### 27.1 Length and Catalog (1–25)

1. Power-of-10 quantum — rejects non-1E-N
2. Quantum rejects canonical forms `10`, `100` (exponent > 0)
3. Canonical quantum string frozen
4. Explicit lengths use quantum
5. Explicit duplicates after quantization — deduplicated
6. Grid `INCLUDE_MAX_IF_ALIGNED` aligned
7. Grid non-aligned — floor applied, no value > max
8. Grid `EXCLUDE_MAX` aligned — excluded
9. Grid `EXCLUDE_MAX` non-aligned — no hi
10. No value generated > `maximum_length_m`
11. `minimum == maximum` + INCLUDE → count=1
12. `minimum == maximum` + EXCLUDE → count=0
13. `increment_m < quantum` → CATALOG_INVALID
14. `to_tick()` rejects raw positive length below quantum via `< quantum` guard before quantization
15. Request min ceiling (does not widen)
16. Request max floor (does not widen)
17. Count-only grid — no list pre-cap
18. Count-only intersection — no list pre-cap
19. Cap before materialization
20. Cap before candidate materialization
21. Cap before TASK-008 call
22. Exact raw/unique/evaluated counts
23. Catalog hash `sha256:` format
24. Duplicate `assembly_option_id` before hash verification
25. `CatalogSnapshotRef` one-to-one with full snapshots

### 27.2 Identity and Evaluation (26–39)

26. `PhysicalCandidateIdentity` stable across sources
27. `SourceQualifiedCandidateIdentity` distinct per source
28. `CandidateEvaluationIdentity` changes with request
29. Target-satisfaction-first ranking
30. `MINIMUM_OUTER_HEAT_TRANSFER_AREA` sort key
31. `MINIMUM_EFFECTIVE_LENGTH` sort key
32. Objectives select different Golden candidates
33. Exact tie resolved by candidate ID
34. `CandidateEvaluation` JSON round-trip
35. `SizingOptimizationResult` hash payload
36. Canonical evaluation order (ID ascending)
37. `SizingRequestIdentity` full fields
38. `FluidIdentifier` identity includes EOS + components
39. `tube_in_hot` in sizing identity, not in rating identity

### 27.3 Evidence and Integrity (40–48)

40. `CandidateEvaluationState` enum (4 states) — VERIFIED includes PROVIDER_IDENTITY_MISMATCH subtype
41. `VERIFIED` state invariants
42. `INTEGRITY_INVALID` state invariants
43. `UNEVALUATED` state invariants
44. `RUNTIME_FAILED` state invariants
45. Integrity invalid — immediate stop, remaining count
46. Verification exception → `FAILED`
47. `VerifiedRatingEvidenceSnapshot` null thermal fields permitted
48. Feasibility only from verified SUCCEEDED + non-None duty

### 27.4 Provenance (49–60)

49. INVALID_REQUEST topology (no catalog/candidate/rating)
50. INVALID_CATALOG topology
51. CAP_EXCEEDED topology
52. EVALUATED_NO_FEASIBLE topology
53. INTEGRITY_INVALID topology (with INVALID_EVIDENCE node)
54. SUCCEEDED topology (full)
55. FAILED topology
56. Two-stage core/final construction
57. `result_hash` excludes final digest
58. Edge tamper via graph digest
59. UUID5 deterministic node IDs
60. INVALID_EVIDENCE node type/label/payload

### 27.5 Validation and ErrorCodes (61–71)

61. `required_duty_w > 0`
62. `top_n` rejects `bool`
63. Cap rejects `bool`
64. Duplicate `(catalog_id, catalog_version)` refs
65. `CATALOG_IDENTITY_MISMATCH` vs `HASH_MISMATCH`
66. Provider mandatory field mismatch → BLOCKED
67. Exact callable forwards 4-field `SolverParams`
68. `CalculationContext` 3 fields derived correctly
69. `required_duty_w` not in rating identity
70. `PROPERTY_PROVIDER_IDENTITY_MISMATCH` code
71. `FluidIdentifier` identity in request

### 27.6 Diagnostics and Ordering (72–76)

72. Full non-feasible sort key (8 fields, nested `affected_paths`)
73. Sentinel when no diagnostic
74. `REQUIRED_DUTY_NOT_MET` for pure duty-infeasible
75. Deterministic primary diagnostic selection
76. `sort_key` serialized as canonical JSON array

### 27.7 Tamper (77–83)

77. Catalog tamper
78. Candidate tamper
79. Ranking tamper
80. Selected-candidate tamper
81. Solver param change → identity change
82. Fouling change → identity change
83. Repeated-run determinism

### 27.8 Golden Cases (84–85)

84. Independent smallest-outer-area Golden
85. Independent shortest-effective-length Golden

### 27.9 Documentation and Quality (86–88)

86. Issue #23 references canonical commit SHA
87. JSON round-trip preserves all fields/hashes/provenance
88. Ruff, format, mypy, pytest+coverage, pip-audit, Python 3.11/3.12

### 27.10 Round 6 Contract Tests (89–136)

89. `sha256_digest(payload)` != `sha256_digest(canonical_json(payload))` — no pre-serialization
90. All TASK-009 `sha256_digest` callers pass payload object, not pre-serialized string
91. Raw request NaN canonicalization → `{"$non_finite_float": "nan"}`
92. Raw request +Infinity canonicalization → `{"$non_finite_float": "+infinity"}`
93. Raw request -Infinity canonicalization → `{"$non_finite_float": "-infinity"}`
94. Raw request unsupported object → deterministic `{"$unsupported_type": ...}`
95. Raw request non-string dict key → deterministic `$mapping_entries` marker + `NON_STRING_MAPPING_KEY` validation error; no exception
96. Raw request cyclic container → `{"$cyclic_reference": {"ancestor_distance": N}}`
97. Raw snapshot self-excluding digest (`raw_request_digest` not in own payload)
98. Structured `SizingValidationErrorSnapshot` digest round-trip
99. Validation-error insertion-order independence (different order → same digest)
100. Reversed grid → `CATALOG_INVALID` (hi_tick < lo_tick)
101. Explicit-length request intersection correct count
102. Explicit-length empty intersection → count 0
103. Explicit-length materialization count invariant: `len == intersection_count`
104. Grid materialization count invariant: `len(materialized_ticks) == intersection_count`
105. `ExpectedProviderIdentity` nested within `SizingRequestIdentity` digest
106. Optional configuration_fingerprint match when expected is not None
107. Optional cache_policy_version match when expected is not None
108. Provider mutation between verified candidates → `PROPERTY_PROVIDER_IDENTITY_MISMATCH`
109. Claimed provider identity NOT used for verified matching decisions
110. Claimed provider identity absent (`None`) when damaged/unreadable
111. Exact TASK-008 `SelectedCorrelationSnapshot` field names (11 fields)
112. Exact TASK-008 `SelectedCorrelationSnapshot` field types (source_year: int, adaptation_limitation: str)
113. `source_year` remains `int` through JSON round-trip
114. `adaptation_limitation` remains `str` through JSON round-trip
115. UUID request context types (`design_case_revision_id`, `calculation_run_id`) as `UUID | None`
116. REQUEST_VALIDATION FailureStage exact provenance topology
117. CATALOG_VALIDATION FailureStage exact provenance topology
118. CANDIDATE_MATERIALIZATION FailureStage exact provenance topology
119. PRE_RATING FailureStage exact provenance topology
120. RATING_CALL FailureStage exact provenance topology
121. RATING_VERIFICATION FailureStage exact provenance topology
122. OPTIMIZATION FailureStage exact provenance topology
123. RESULT_CONSTRUCTION FailureStage exact provenance topology
124. Each FailureStage exact forbidden nodes check
125. RUNTIME_FAILED retains `RunFailure` with failure_stage, candidate_id, evaluation_order_index
126. RUNTIME_FAILED candidate record digest (evaluation_failure_digest populated)
127. UNEVALUATED candidate record digest (all relevant fields None/False)
128. VERIFIED candidate record digest (complete payload)
129. INTEGRITY_INVALID candidate record digest (claimed_provider_identity in digest)
130. Candidate record tamper by modifying failure digest
131. Candidate record tamper by modifying diagnostic digest
132. `FeasibilityStatus` exact eight values and numerical ranks
133. `RatingStatus` None sentinel (None = 999 in sort)
134. Severity rank exact mapping (INFO=0, WARNING=1, ERROR=2, BLOCKER=3)
135. `EngineeringMessage` context affects digest (same code/message, different context → different digest)
136. Provenance UUID collision prevention: warning/blocker with same code/message but different context produce different UUIDs

### 27.11 Round 7 Contract Tests (137–176)

137. Raw increment below quantum rejected (Decimal `increment_m < quantum`)
138. Raw increment exactly equal to quantum accepted
139. Raw increment just above quantum canonicalized deterministically
140. Cyclic raw input always uses `$cyclic_reference` marker with `ancestor_distance` (no path-based syntax)
141. Cyclic `ancestor_distance` stability (`$.field`, `$.field[0]`, `$.field["key"]` path syntax removed — no sort/path loop)
142. Dict traversal order does not affect `ancestor_distance` determinism
143. Non-string mapping key still produces `RawSizingRequestSnapshot` (no exception)
144. Non-string mapping key produces structured `SizingValidationErrorSnapshot` with code `NON_STRING_MAPPING_KEY`
145. Unsupported object produces snapshot + `SizingValidationErrorSnapshot` (`UNSUPPORTED_RAW_INPUT_TYPE`)
146. `VERIFIED+SUCCEEDED` duty fields populated non-None when `heat_duty_w is not None`
147. `VERIFIED+BLOCKED` duty fields all None
148. `VERIFIED+FAILED` duty fields all None
149. `INTEGRITY_INVALID` trusted `CandidateEvaluation.rating_status` is None
150. `claimed_rating_status` in `InvalidRatingEvidenceRecord` audit-only, not promoted to trusted `RatingStatus`
151. Invalid evidence node ID works with `claimed_result_hash=None`: uses `invalid_evidence_digest`
152. Invalid evidence digest changes when any claimed field is tampered
153. Rating counter invariant: `0 ≤ verified ≤ completed ≤ attempted ≤ unique`
154. `RATING_CALL` exception: `attempted = completed + 1`, failed candidate not unevaluated
155. `RATING_CALL` failed candidate: `CandidateEvaluationState = RUNTIME_FAILED`, `failure_stage = RATING_CALL`
156. `RATING_VERIFICATION` exception: `attempted == completed`, `completed = verified + 1`
157. Claimed-result node ID always uses `audit_digest` with `claim_state` (not conditional `claimed_result_digest`)
158. `RESULT_CONSTRUCTION` uses exact `SizingRunFailureResult` schema (not degraded `SizingOptimizationResult`)
159. `RESULT_CONSTRUCTION` `partial_audit = False` (evaluation completed all candidates)
160. `failure_result_hash` tamper detection (changes on any payload field change)
161. `SizingRunFailureResult` JSON round-trip preserves all fields
162. `CandidateDiagnosticKey` sorts using string `code` (not `code.value`)
163. Validation error sort uses `context_digest` derived from canonical context
164. `evaluation_order_index` derived from `source_qualified_candidate_id` sorted position
165. Tampered `evaluation_order_index` rejected (does not match canonical position)
166. `EngineeringMessage` insertion-order independence (same content, different order → same digests)
167. CandidateDiagnosticKey insertion-order independence
168. Catalog snapshot insertion-order independence
169. Evidence record insertion-order independence
170. Validation error insertion-order independence
171. Markdown code fence in `SizingRequestIdentity` schema validated (no leading pipes)
172. Section numbering continuous (no gaps, no duplicates)
173. Acceptance Criteria references Round 19
174. Issue #23 frozen SHA equals new docs commit
175. Task-card test range headings match numbered entries
176. Issue test total equals task-card N

### 27.12 Round 8 Contract Tests (177–204)

177. Reversed grid rejected before `delta`/`divmod` (hi_tick < lo_tick → early guard)
178. Reversed grid produces no materialization, no rating, no evaluation
179. Explicit length positive sub-quantum rejected via `to_tick()` `< quantum` guard
180. Grid min/max positive sub-quantum rejected via `to_tick()` `< quantum` guard
181. Multi invalid-key mapping canonicalization preserves each entry independently
182. Mixed string/non-string mapping preserves all entries (no discarding)
183. Invalid mapping insertion-order independence (different order → same canonical output)
184. Invalid mapping value association preserved (each key paired with its value)
185. `SizingValidationErrorSnapshot.context_digest` present in schema and JSON round-trip
186. `context_digest` recomputation produces identical digest
187. Validation sort never compares raw nested context (uses `context_digest`)
188. `VERIFIED+BLOCKED` correlation snapshots may be `None`
189. `VERIFIED+FAILED` correlation snapshots may be `None`
190. No fabricated empty `SelectedCorrelationSnapshot` when correlation is None
191. `INTEGRITY_INVALID` `rating_status` is None (not claimed status)
192. `RATING_CALL` topology uses `attempted_rating_count` (not `completed_rating_count`)
193. `RATING_CALL` remaining count excludes the failed candidate
194. `RATING_VERIFICATION` topology distinguishes `VERIFIED` vs `CLAIMED` TASK008 result nodes
195. `RESULT_CONSTRUCTION` uses independent `SIZING_RUN_FAILURE_RESULT` node type/label/UUID
196. `RESULT_CONSTRUCTION` exact node multiplicity (`SIZING_RUN_FAILURE_RESULT × 1`)
197. `RESULT_CONSTRUCTION` exact edge set (9 edges, including `precedes_failure`)
198. Failure result embeds canonical audit digest collections (catalog, evaluation, evidence, ranking digests)
199. No `RawInputCanonicalizationError` exists in test descriptions (all use deterministic marker)
200. 4 `CandidateEvaluationState` enum values / 7 invariant rows consistency
201. Section numbering continuous (no gaps, section 20.3 present)
202. Issue #23 test total equals task-card N
203. Issue #23 frozen SHA equals new docs commit
204. Acceptance Criteria references Round 19

### 27.13 Round 9 Contract Tests (205–244)

205. `{1:"A",2:"B"}` vs `{1:"B",2:"A"}` produce different raw digests (key-value association preserved)
206. Bool/int key type-sensitive canonicalization (bool checked before int)
207. UUID key canonicalization produces deterministic lowercase string
208. Enum key canonicalization preserves enum type + value
209. Opaque object key does not claim injective/reversible representation
210. Duplicate opaque marker entries preserve entry count in snapshot
211. Cyclic invalid mapping canonicalization uses `ancestor_distance` (no sort/path loop)
212. Cycle marker `ancestor_distance` stability across repeated runs
213. `VerificationOutcome` enum exactly 4 values (NOT_RUN, PASSED, FAILED, ERROR)
214. Hash verification returns False → outcome FAILED, provenances NOT_RUN
215. Hash verification raises → outcome ERROR, provenances NOT_RUN, RUNTIME_FAILED
216. Hash PASSED, provenance returns False → outcome PASSED/FAILED, candidate INTEGRITY_INVALID
217. Hash PASSED, provenance raises → outcome PASSED/ERROR, RUNTIME_FAILED, failure_stage=RATING_VERIFICATION
218. Strict per-candidate pipeline order enforced (attempt→call→completed→hash→provenance→evidence→provider compare)
219. RATING_CALL exact equality: `attempted = completed + 1, verified = completed`
220. Verification false exact equality: `completed = verified + 1`
221. Verification exception exact equality: `completed = verified + 1`
222. Provider mismatch exact equality: `attempted = completed = verified`
223. RATING_RESULT_INTEGRITY_FAILED topology has no OPTIMIZER node
224. RATING_RESULT_INTEGRITY_FAILED topology includes all unique CANDIDATE nodes (not just evaluated subset)
225. PROPERTY_PROVIDER_IDENTITY_MISMATCH topology has no OPTIMIZER node
226. Provider mismatch topology remaining candidates = UNEVALUATED (not VERIFIED)
227. RATING_VERIFICATION topology exactly 1 CLAIMED_TASK008_RATING_RESULT node
228. OPTIMIZATION topology CLAIMED_TASK008_RATING_RESULT count = 0
229. RESULT_CONSTRUCTION topology CLAIMED_TASK008_RATING_RESULT count = 0
230. Failure core graph excludes SIZING_RUN_FAILURE_RESULT node
231. Failure result two-stage hash/provenance reconstruction (core→hash→final)
232. Failure result node/edge tamper detection via final provenance digest
233. `ExecutionContextSnapshot` exact field types (3 UUID | None)
234. Execution context digest round-trip (JSON→deserialize→recompute digest)
235. Verified evidence `rating_status` uses `RatingStatus` type (not `str`)
236. ROOT_EXTERNAL registry entry (type EXTERNAL, label "external_root")
237. CLAIMED_TASK008_RATING_RESULT registry entry (type INTERMEDIATE, label "claimed_rating_{candidate_id}")
238. Distinct `rated_as` (verified) vs `rated_as_claimed` (unverified) edge labels
239. Round 8 Design Review History records "—" (no PENDING), no comment ID
240. Round 9 Design Review Comment ID is `4798128591`
241. Round 10 Review Comment ID is `4798318702`; no duplicate Round 8/9 acceptance refs
242. Issue #23 frozen SHA equals new docs commit SHA
243. Round 9 subsection numbering is locally continuous within 205–244
244. Round 9 subsection heading range is 205–244

### 27.14 Round 10 Contract Tests (245–295)

245. Provider mismatch candidate evidence constructed before comparison check
246. Provider mismatch retains VERIFIED CandidateEvaluation (candidate_evaluation_identity not None, verified_evidence not None)
247. Provider mismatch duty/feasibility exact: all duty fields None, feasible=False, feasibility_status=PROVIDER_IDENTITY_MISMATCH
248. `ClaimedRatingResultAuditSnapshot` schema (10 claimed fields, audit_digest)
249. Claimed audit exact digest payload round-trip
250. Claimed audit explicit null fields when unreadable
251. Claimed audit stored in `SizingOptimizationResult.claimed_rating_audits`
252. Claimed audit digest enters `SizingResultIdentity.claimed_rating_audit_digests`
253. Claimed node rebuilt from stored audit (UUID5 uses audit_digest, not result hash)
254. Claimed audit tamper changes result hash/provenance digest
255. Verified evidence full payload exact field count and types
256. Verified evidence nullable field (heat_duty_w, correlation = None) tamper detection
257. Provider identity digest tamper changes verified_evidence_digest
258. Rating request identity digest tamper changes verified_evidence_digest
259. Execution context digest tamper changes verified_evidence_digest
260. Correlation digest tamper (None vs populated) changes verified_evidence_digest
261. Warning/blocker/failure digest tamper changes verified_evidence_digest
262. Failure result full audit objects reconstruct provenance graph (not just digests)
263. Failure result digest collection mismatch detected (store vs recompute)
264. Failure provenance reconstruction does NOT trust stored graph (recomputes from objects)
265. Result-level `partial_audit` formula: `partial_audit = evaluated < unique`
266. PRE_RATING: `partial_audit = True` (unique > 0, evaluated = 0)
267. Provider mismatch before final candidate → `partial_audit = True`
268. Provider mismatch on final candidate → `partial_audit = False`
269. `CandidateEvaluation.partial_audit` removed from schema and digest
270. RATING_VERIFICATION exact: `completed = verified + 1`
271. RATING_VERIFICATION exactly 1 claimed audit and 1 claimed node
272. Enum dispatch before str (StrEnum not matched as str)
273. IntEnum dispatch before int (IntEnum not matched as int)
274. Nested enum value validation errors propagated via `nested_validation_errors`
275. Mapping collision scope documented (Python pre-collision not recoverable)
276. Bool/int tests use separate observable mapping entries for dispatch verification
277. Finite float key value is float (not JSON string) in key_payload
278. `RawInputValidationCode` exact enum values (5 codes)
279. Supported non-string scalar key: `NON_STRING_MAPPING_KEY` ×1 (not also UNSUPPORTED_RAW_MAPPING_KEY)
280. Opaque mapping key: `UNSUPPORTED_RAW_MAPPING_KEY` ×1 (not also NON_STRING_MAPPING_KEY)
281. Unsupported value: `UNSUPPORTED_RAW_INPUT_TYPE` ×1 per occurrence
282. No "or frozen equivalent" text in document
283. Complete provenance registry contains all 14 concepts in Node Type Mapping
284. `ROOT_CASE_REVISION` UUID: `root-case-revision:{design_case_revision_id}`
285. `ROOT_EXTERNAL` UUID: `root-external:{...}` (request digest used)
286. CLAIMED result UUID: `claimed-rating-result:{candidate_id}:{index}:{audit_digest}` (always, not conditional)
287. Failure-result UUID: `sizing-run-failure:{failure_result_hash}`
288. Top-level heading sequence continuous (1–29, no gaps)
289. Section 21 exists (RunFailure Stage Model)
290. Section 28 Delivery Sequence heading exists
291. Round 10 subsection numbering is locally continuous within 245–295
292. Section heading test: all `## N.` extracted as int list equals `range(1, 30)`
293. Section heading test: no duplicates, no gaps
294. Test matrix section range 27.1–27.21 continuous
295. Round 10 subsection heading range is 245–295

### 27.15 Round 11 Contract Tests (296–332)

296. CandidateEvaluationState exactly 4 enum values (UNEVALUATED, VERIFIED, INTEGRITY_INVALID, RUNTIME_FAILED)
297. Provider mismatch candidate state is VERIFIED (not separate state)
298. Provider mismatch feasibility_status is PROVIDER_IDENTITY_MISMATCH
299. 7 invariant rows: VERIFIED+SUCCEEDED/BLOCKED/FAILED/PROVIDER_IDENTITY_MISMATCH + INTEGRITY_INVALID + RUNTIME_FAILED + UNEVALUATED
300. No PROVIDER_IDENTITY_MISMATCH in CandidateEvaluationState enum or table
301. Finite float key value is Python float (canonical_json handles serialization)
302. No `NON_STRING_KEY` in document (all use `NON_STRING_MAPPING_KEY`)
303. No old cycle path-string marker (all use `ancestor_distance`)
304. Validation error digest includes `message_key`, does NOT include `message`
305. Validation error sort key uses `message_key` not `message`
306. Exact validation message registry (5 codes × message_key × frozen message)
307. PRE_RATING topology: `partial_audit = True` (corrected from False)
308. Candidate hash payload has no `partial_audit` field
309. No `claimed_result_digest` in document (replaced by `audit_digest`)
310. RATING_VERIFICATION topology uses `audit_digest` always (not conditional on hash readability)
311. Old test #157 rewritten: uses `audit_digest` not `claimed_result_digest`
312. FeasibilityStatus exactly 8 values (PROVIDER_IDENTITY_MISMATCH included)
313. RATING_VERIFICATION equality: `completed = verified + 1`
314. Pipeline order: evidence constructed before provider comparison (not provider→evidence)
315. No `N=244` anywhere in document
316. Top-level headings continuous 1–29
317. Subsection headings continuous within each parent section (14.1–14.7, 18.1.1–18.1.6, 19A.1–19A.8, 20.1–20.6, 22.1–22.7, 27.1–27.21)
318. No duplicate `19A.5` heading
319. No `## 14.8` heading (is `### 14.7`)
320. Issue #23 lists Round 9/10/11 review entries
321. Issue #23 pipeline description matches evidence-before-provider order
322. Issue #23 state/row count matches 4 states / 7 rows
323. Issue #23 test total equals task card total
324. Claimed safely_readable_field_digests uses whitelist (6 fields only)
325. Claimed field digest formula: `sha256_digest({"field_name": name, "canonical_value": value})`
326. Provenance registry includes all 14 concepts with node_type/label/UUID/payload_hash/metadata/edges
327. Edge registry includes `SIZING_RUN -> SIZING_OPTIMIZER = "executes"`
328. Nested digest payloads frozen: ProviderIdentitySnapshot (6 fields), ExecutionContextSnapshot (3 fields), SelectedCorrelationSnapshot (11 fields)
329. Round 11 Review Comment ID is `4798512240`
330. Acceptance Criteria references Round 19
331. Issue #23 frozen SHA equals new docs commit
332. Round 11 subsection numbering is locally continuous within 296–332; Issue and task card test total match

### 27.16 Round 12 Contract Tests (333–370)

333. TASK-008 `RatingRequestIdentity` exact 21-field payload
334. Rating request digest has no self-reference (no `rating_request_identity_digest` field)
335. Provider/context/candidate/result fields excluded from rating request identity payload
336. `CandidateEvaluationIdentity` remains a separate exact 7-field payload
337. Claimed whitelist uses six real `RatingResult` attributes (`status`, `result_hash`, `provenance_digest`, `request_identity`, `execution_context`, `provider_identity`)
338. Nonexistent digest attributes (`request_identity_digest`, `execution_context_digest`, `provider_identity_digest`) are prohibited in whitelist
339. Safe `status` extraction uses `RatingStatus.value`
340. Safe request-identity extraction derives the exact 21-field digest
341. Safe execution-context extraction derives the exact 3-field digest
342. Safe provider-identity extraction derives the exact 6-field digest
343. Wrong object type or all unavailable fields yields `claim_state = UNREADABLE`
344. Claimed field digest uses the real public `RatingResult` field name (not alias)
345. `EngineeringMessage` exact shared payload (schema_version, code.value, severity.value, message, source_module, affected_paths, context_entries)
346. `allows_continuation` excluded from digest but verified from severity (INFO/WARNING → True, ERROR/BLOCKER → False)
347. Engineering-message context normalization: insertion-order independent via sorted entries
348. `RunFailure` exact shared payload (schema_version, code.value, message, traceback, context_entries)
349. RunFailure nullable `traceback` enters payload as `None`
350. TASK-009 `failure_stage`/`candidate_id`/`evaluation_order_index` remain in RunFailure.context entries, not top-level payload fields
351. Supported non-string key emits exactly one `NON_STRING_MAPPING_KEY` validation error (not also `UNSUPPORTED_RAW_MAPPING_KEY`)
352. Opaque key emits exactly one `UNSUPPORTED_RAW_MAPPING_KEY` validation error (not also `NON_STRING_MAPPING_KEY`)
353. Opaque key never emits both raw-key validation codes simultaneously
354. Rejected-value digests use exact `sha256_digest(payload)` formulas (not bare `sha256(marker)`)
355. Provider mismatch uses `VERIFIED + feasibility_status == PROVIDER_IDENTITY_MISMATCH` predicate (not `CandidateEvaluationState == PROVIDER_IDENTITY_MISMATCH`)
356. Removed state comparison (`CandidateEvaluationState == PROVIDER_IDENTITY_MISMATCH`) is prohibited
357. No executable `N=295` assertion remains in the document
358. One final test total only (1–370)
359. `verify_provenance() == False` is the normal integrity-failure outcome (maps to FAILED)
360. Unexpected wrapper/runtime exception maps to `VerificationOutcome.ERROR`
361. `verify_hash()` false and exception outcomes are distinct (FAILED vs ERROR)
362. Complete provenance registry contains all 14 concepts (ROOT_CASE_REVISION, ROOT_EXTERNAL, SIZING_RUN, SIZING_OPTIMIZER, CATALOG_SNAPSHOT, CANDIDATE, TASK008_RATING_RESULT, CLAIMED_TASK008_RATING_RESULT, SIZING_RESULT, SIZING_RUN_FAILURE_RESULT, INVALID_EVIDENCE, RUNTIME_FAILURE, WARNING, BLOCKER)
363. Every provenance concept has an exact payload-hash payload
364. Every provenance concept has exact metadata fields (node_type, label, UUID5 name, payload_hash, required metadata, allowed incoming/outgoing edges)
365. Every provenance concept has allowed incoming/outgoing relations validated
366. Global enum serialization uses `.value` for all enums in payloads (RatingStatus, VerificationOutcome, FeasibilityStatus, etc.)
367. No enum object is passed directly in an exact digest payload
368. Round 12 Review Comment ID is `4798693707`
369. Issue #23 frozen SHA equals the new Round 12 docs commit
370. Round 12 subsection numbering is locally continuous within 333–370; `dummy` is absent, hygiene commits retained

### 27.17 Round 13 Contract Tests (371–405)

371. Old global total assertion `1–332` absent from active tests
372. Old global total assertion `N=332` absent from active tests
373. Round 9 subsection local range 205–244 remains valid
374. Round 10 subsection local range 245–295 remains valid
375. CandidateEvaluation digest contains no `partial_audit` field
376. CandidateEvaluation schema contains no `partial_audit` field
377. Integrity failure before final candidate → partial_audit=True
378. Integrity failure on final candidate → partial_audit=False
379. Verification ERROR before final candidate → partial_audit=True
380. Verification ERROR on final candidate → partial_audit=False
381. Provider mismatch before final candidate → partial_audit=True
382. Provider mismatch on final candidate → partial_audit=False
383. RATING_CALL failure before final candidate → partial_audit=True
384. RATING_CALL failure on final candidate → partial_audit=False
385. Provider mismatch overrides SUCCEEDED feasibility derivation (Step 1 precedence)
386. Provider mismatch overrides BLOCKED feasibility status
387. Provider mismatch overrides FAILED feasibility status
388. Verified evidence exact key count = 26
389. Verified evidence exact key set frozen (all 26 field names match)
390. Issue summary states exact 26-field payload
391. Executable provenance registry contains all 14 concepts
392. Registry row includes payload-hash payload definition
393. Registry row includes ordered metadata fields
394. Registry row includes allowed incoming/outgoing relations
395. Registry row includes topology multiplicity and forbidden classes
396. Duplicate identical warning messages get distinct deterministic UUIDs
397. Duplicate identical blocker messages get distinct deterministic UUIDs
398. Warning ownership survives insertion-order changes (occurrence_index stable)
399. Blocker ownership survives insertion-order changes (occurrence_index stable)
400. TASK-008 request snapshot primitive strings (`flow_arrangement`, `tube_boundary_condition`, `annulus_boundary_condition`) are not double-converted
401. All actual enum payload fields use `.value` in exact payload examples
402. Unsupported trusted context value follows frozen fail-closed path (RUNTIME_FAILED + PROVENANCE_INCOMPLETE)
403. Non-finite float in trusted context follows frozen fail-closed path
404. Failure provenance reconstruction requires full audit objects (digest-only reconstruction fails)
405. Round 13 Comment ID `4798895696`, Issue frozen SHA matches Round 13 commit, global numbering continuous 1–405

### 27.18 Round 14 Contract Tests (406–430)

406. Actual executable registry contains exactly 14 concept entries
407. Every registry entry has node type and label formula
408. Every registry entry has UUID5 name formula
409. Every registry entry has exact payload-hash payload
410. Every registry entry has ordered metadata fields
411. Every registry entry has allowed incoming/outgoing relations
412. Every registry entry has multiplicity source and topology allow/deny sets
413. Topologies reference registry concepts without identity redefinition
414. MessageOccurrenceSnapshot exact schema and digest
415. Warning occurrences stored in standard and failure result models
416. Blocker occurrences stored in standard and failure result models
417. Occurrence digests enter standard/failure result hashes (result identity binding)
418. TASK-008 candidate warning owner assignment (owner_kind=CANDIDATE, owner_id=source_qualified_candidate_id)
419. Catalog/optimizer/run message owner assignment (owner_kind as appropriate)
420. Exactly one incoming `emits` edge per message occurrence node
421. Duplicate identical warnings retain distinct deterministic nodes via occurrence_index
422. Duplicate identical blockers retain distinct deterministic nodes via occurrence_index
423. Single context digest formula uses `{"entries": ...}` consistently
424. Old `{"context": canonicalized_context}` digest formula absent from active contract
425. Unsupported trusted context builds primitive-only fallback RunFailure
426. Fallback RunFailure does not recursively fail canonicalization
427. RESULT_CONSTRUCTION topology includes `SIZING_RUN -> OPTIMIZER "executes"` edge
428. RESULT_CONSTRUCTION exact base edge count updated (9 edges)
429. Every exact enum payload uses `.value` or explicitly notes already-primitive TASK-008 fields
430. Round 14 Comment ID `4799066285`; Issue frozen SHA matches new commit; global tests continuous 1–430

### 27.19 Round 15 Contract Tests (431–460)

431. Round 15 history uses Comment ID `4799188706`; no pre-populated future review row
432. Registry has exactly 14 typed ProvenanceConceptSpec entries
433. Registry allowed incoming relations include exact source + relation label
434. Registry allowed outgoing relations include exact relation label + target concept
435. Registry required metadata fields are ordered tuples
436. Registry payload constructors use no undefined aliases (`id`, `v`, `hash`, `digest`)
437. Registry uses no `all`, `all others`, or ambiguous dash termination sets
438. Registry multiplicity formulas reference frozen counters
439. Valid SIZING_RUN UUID/payload uses `request_kind`/`request_digest`
440. Raw invalid-request SIZING_RUN UUID/payload uses `request_kind`=RAW
441. ROOT_EXTERNAL permits invalid request and uses tagged request payload with `request_kind`
442. SIZING_RESULT termination set matches every standard-result topology (17 classes)
443. MessageOccurrenceSnapshot exact schema includes `occurrence_kind`
444. UUID uses `occurrence_kind.value` and `owner_kind.value` (not hardcoded prefix)
445. Standard result authoritative schema stores warning occurrences and digests
446. Standard result authoritative schema stores blocker occurrences and digests
447. Failure result authoritative schema stores warning occurrences and digests
448. Failure result authoritative schema stores blocker occurrences and digests
449. Occurrence collections have exact canonical sort keys
450. Candidate/catalog/optimizer/run owner assignment exact per P0-7
451. Every warning occurrence has exactly one incoming `emits` edge
452. Every blocker occurrence has exactly one incoming `emits` edge
453. Edge summary contains all 8 owner-to-message `emits` relations and valid Markdown
454. Base topology + occurrence expansion reconstructs exact graph
455. RESULT_CONSTRUCTION final edge count formula uses `9 + 2*W + 2*B`
456. Primitive fallback covers all 8 FailureStage values
457. Primitive fallback uses qualified type, context path digest, failure kind, safe marker digest
458. Every named exact payload serializes Enums using `.value`
459. Issue contains only 26-field verified evidence contract (no 24-field)
460. Round 16 Comment ID `4799475298`; frozen SHA matches new commit; global numbering continuous 1–540

### 27.20 Round 16 Contract Tests (461–500)

461. TerminationTopologySpec dataclass has exactly 10 fields (termination_class, root_topology_constructor, result_concept, base_node_multiplicities, static_base_edges, forbidden_concepts, allowed_message_owner_kinds, minimum_warning_occurrences, minimum_blocker_occurrences, counter_invariants)
462. Registry has exactly 17 entries, one per TerminationClass
463. INVALID_REQUEST uses ROOT_EXTERNAL, no CATALOG/CANDIDATE/RATING nodes
464. INVALID_CATALOG uses ROOT_CASE_REVISION with catalog_count CATALOG_SNAPSHOT nodes
465. CATALOG_IDENTITY_MISMATCH matches INVALID_CATALOG exactly
466. CAP_EXCEEDED forbids CANDIDATE, TASK008_RATING_RESULT, SIZING_OPTIMIZER
467. NO_MANUFACTURABLE_CANDIDATE matches CAP_EXCEEDED forbidden set
468. NO_FEASIBLE_CANDIDATE includes SIZING_OPTIMIZER and CANDIDATE nodes
469. SUCCEEDED uses unique_candidate_count for TASK008_RATING_RESULT (not verified_rating_count)
470. PROPERTY_PROVIDER_IDENTITY_MISMATCH has no SIZING_OPTIMIZER node
471. RATING_RESULT_INTEGRITY_FAILED has INVALID_EVIDENCE node, no OPTIMIZER
472. RUNTIME_FAILED_REQUEST_VALIDATION uses ROOT_EXTERNAL, has RUNTIME_FAILURE node
473. RUNTIME_FAILED_CATALOG_VALIDATION has catalog CATALOG_SNAPSHOT nodes
474. RUNTIME_FAILED_CANDIDATE_MATERIALIZATION uses materialized_candidate_count
475. RUNTIME_FAILED_PRE_RATING uses unique_candidate_count, no TASK008_RATING_RESULT
476. RUNTIME_FAILED_RATING_CALL uses completed_rating_count for TASK008_RATING_RESULT
477. RUNTIME_FAILED_RATING_VERIFICATION has exactly 1 CLAIMED_TASK008_RATING_RESULT node
478. RUNTIME_FAILED_OPTIMIZATION includes SIZING_OPTIMIZER node
479. RUNTIME_FAILED_RESULT_CONSTRUCTION uses SIZING_RUN_FAILURE_RESULT as result_concept (not SIZING_RESULT)
480. RESULT_CONSTRUCTION registry entry forbids INVALID_EVIDENCE, CLAIMED_TASK008_RATING_RESULT, SIZING_RESULT
481. Allowed message owner kinds per termination class contain at minimum SIZING_RUN
482. CAP_EXCEEDED and NO_MANUFACTURABLE_CANDIDATE forbidden sets match exactly
483. SUCCEEDED and NO_FEASIBLE_CANDIDATE both allow OPTIMIZER owner kind
484. RUNTIME_FAILED_REQUEST_VALIDATION allowed_owners is exactly (SIZING_RUN,) with no catalog/optimizer owners
485. SizingOptimizationResult schema contains warning_occurrences, blocker_occurrences, warning_occurrence_digests, blocker_occurrence_digests, claimed_rating_audit_digests
486. SizingRunFailureResult schema contains warning_occurrences, blocker_occurrences, warning_occurrence_digests, blocker_occurrence_digests
487. Base topology explicitly does NOT contain WARNING/BLOCKER nodes or edges
488. Final edge count formula verified: `base_edge_count + 2W + 2B`
489. Occurrence expansion adds 2 edges per WARNING (emits + annotates/annotates_failure)
490. Occurrence expansion adds 2 edges per BLOCKER (emits + blocks/annotates_failure)
491. Message content deduplication: unique_content_count <= occurrence_count
492. Occurrence index groups by (owner_kind, owner_id, occurrence_kind, message_digest), indices 0..count-1
493. Canonical sort key: (owner_kind.value, owner_id, occurrence_kind.value, message_digest, occurrence_index, occurrence_digest)
494. Every unique content digest has at least one occurrence
495. Primitive fallback RunFailure context does NOT cascade fail on canonicalization
496. Global test numbering continuous 1–540
497. Section 27 range now 27.1–27.21 continuous (no gaps)
498. Subsection headings range updated to 22.1–22.7 for provenance subsections
499. Delivery Sequence and Acceptance Criteria reference the same next Engineering Design Review round
500. Issue #23 frozen SHA equals new docs commit for Round 16

### 27.21 Round 30 Contract Tests (501–540)

501. **Input**: Review history table after Round 30 changes. **Expected output**: Round 29 row exists with Comment ID `4802701831`. **Exception**: N/A — sync test: structural consistency check.
502. **Input**: Review history table after Round 30 changes. **Expected output**: Round 30 row exists with Comment ID `4802836532`. **Exception**: N/A — sync test: structural consistency check.
503. **Input**: Round 29 and Round 30 rows in review history. **Expected output**: Round 29 immediately follows Round 28; Round 30 immediately follows Round 29. **Exception**: N/A — sync test: ordering check.
504. **Input**: Gate text at top of document. **Expected output**: References "Round 31 Engineering Design Review". **Exception**: N/A — sync test: gate reference check.
505. **Input**: `CountingMapping` with call counter. **Expected output**: `items()` is called exactly once during canonicalization. **Exception**: N/A — single-read invariant: items acquired exactly once.
506. **Input**: Captured Mapping items iterable is used for iteration. **Expected output**: Canonicalizer iterates the captured items, does not re-read the original Mapping. **Exception**: N/A — single-read invariant: captured iterable is consumed.
507. **Input**: Mapping whose second `items()` call raises `RuntimeError`. **Expected output**: Canonicalization succeeds because the second call is never made. **Exception**: N/A — single-read invariant: second call not triggered.
508. **Input**: `value.items()` raises `ContextCanonicalizationError`. **Expected output**: `ContextCanonicalizationError` propagates unchanged. **Exception**: `ContextCanonicalizationError` — typed error propagates.
509. **Input**: `value.items()` raises `RuntimeError("probe")`. **Expected output**: `ContextCanonicalizationError` with `failure_kind="canonicalization_exception"`. **Exception**: `ContextCanonicalizationError` — ordinary exception converted.
510. **Input**: Mapping iterable iteration raises `RuntimeError("probe")`. **Expected output**: `ContextCanonicalizationError` with `failure_kind="canonicalization_exception"`. **Exception**: `ContextCanonicalizationError` — iteration error converted.
511. **Input**: A real Pydantic `BaseModel` instance. **Expected output**: `try_read_pydantic_model_adapter` returns a valid `PydanticModelAdapter` with the `model` reference. **Exception**: N/A — `BaseModel` recognised.
512. **Input**: A `BaseModel` subclass instance. **Expected output**: `try_read_pydantic_model_adapter` returns a valid `PydanticModelAdapter`. **Exception**: N/A — subclass recognised.
513. **Input**: A plain object with `model_fields` set on the instance only. **Expected output**: `try_read_pydantic_model_adapter` returns `None`; canonicalizer treats it as `unsupported_type`. **Exception**: `ContextCanonicalizationError` with `failure_kind="unsupported_type"`.
514. **Input**: A plain class with class-level `model_fields = {"x": "y"}`. **Expected output**: `try_read_pydantic_model_adapter` returns `None`; canonicalizer rejects as `unsupported_type`. **Exception**: `ContextCanonicalizationError` with `failure_kind="unsupported_type"`.
515. **Input**: Pydantic `BaseModel` with instrumented `type(model).model_fields`. **Expected output**: `model_fields` is read exactly once during `try_read_pydantic_model_adapter`. **Exception**: N/A — single-read invariant.
516. **Input**: Captured `PydanticModelAdapter.model_fields` is iterated for field traversal. **Expected output**: The canonicalizer iterates the captured field mapping; `type(value).model_fields` is not re-read. **Exception**: N/A — single-read invariant.
517. **Input**: Pydantic field getter raises `ContextCanonicalizationError`. **Expected output**: `ContextCanonicalizationError` propagates unchanged. **Exception**: `ContextCanonicalizationError` — typed error propagates.
518. **Input**: Pydantic field getter raises `RuntimeError("probe")`. **Expected output**: `ContextCanonicalizationError` with `failure_kind="canonicalization_exception"`. **Exception**: `ContextCanonicalizationError` — ordinary exception converted.
519. **Input**: Object missing one of the four required Quantity static attributes (value, unit, kind, to_si). **Expected output**: `try_read_repository_quantity_adapter` returns `None`. **Exception**: N/A — missing static attribute returns None.
520. **Input**: Quantity-like object with `value` property that raises `AttributeError` internally. **Expected output**: `ContextCanonicalizationError` with `failure_kind="canonicalization_exception"`. **Exception**: `ContextCanonicalizationError` — getter failure is not None.
521. **Input**: Quantity-like object with `value` property that raises `RuntimeError("probe")`. **Expected output**: `ContextCanonicalizationError` with `failure_kind="canonicalization_exception"`. **Exception**: `ContextCanonicalizationError` — getter failure converted.
522. **Input**: Quantity-like object with `value` property that raises `ContextCanonicalizationError`. **Expected output**: `ContextCanonicalizationError` propagates unchanged. **Exception**: `ContextCanonicalizationError` — typed error propagates.
523. **Input**: Quantity-like object with `to_si` that raises `ContextCanonicalizationError`. **Expected output**: `ContextCanonicalizationError` propagates unchanged. **Exception**: `ContextCanonicalizationError` — typed error propagates.
524. **Input**: Quantity-like object with `to_si` that raises `RuntimeError("probe")`. **Expected output**: `ContextCanonicalizationError` with `failure_kind="canonicalization_exception"`. **Exception**: `ContextCanonicalizationError` — ordinary exception converted.
525. **Input**: Quantity-like object with non-callable `to_si`. **Expected output**: `try_read_repository_quantity_adapter` returns `None`. **Exception**: N/A — non-callable to_si means adapter returns None.
526. **Input**: Quantity adapter uses typed `QuantityKindProtocol` and `QuantityToSIProtocol`. **Expected output**: `adapter.kind` type reveals `value: str`; `adapter.to_si` is callable returning SI result. **Exception**: N/A — typed protocol guarantees.
527. **Input**: Quantity adapter `kind` field type. **Expected output**: `adapter.kind` is typed as `QuantityKindProtocol | None`; no `Any` or `object` escapes. **Exception**: N/A — typed protocol.
528. **Input**: Normative canonicalization block. **Expected output**: Contains zero `# type: ignore` comments. **Exception**: N/A — strict mypy compliance.
529. **Input**: Python 3.11 environment with `mypy --strict`. **Expected output**: Normative extracted canonicalization block passes. **Exception**: N/A — type-safe contract.
530. **Input**: Python 3.12 environment with `mypy --strict`. **Expected output**: Normative extracted canonicalization block passes. **Exception**: N/A — type-safe contract.
531. **Input**: Valid NO_FEASIBLE counters: `unique=10, evaluated=10, verified=10, feasible=0, result=1, failure=0`. **Expected output**: All top-level invariants pass. **Exception**: N/A — regression: valid fixture unchanged.
532. **Input**: NO_FEASIBLE: `unique=10, evaluated=2, verified=2, feasible=0, result=1, failure=0`. **Expected output**: `ValueError` raised with `"evaluated"`. **Exception**: `ValueError` — regression: partial evaluation still rejected.
533. **Input**: Valid SUCCEEDED counters: `unique=10, evaluated=10, verified=10, feasible=3, result=1, failure=0`. **Expected output**: All top-level invariants pass. **Exception**: N/A — regression: valid fixture unchanged.
534. **Input**: SUCCEEDED: `unique=10, evaluated=3, verified=10, feasible=3, result=1, failure=0`. **Expected output**: `ValueError` raised with `"evaluated"`. **Exception**: `ValueError` — regression: partial evaluation still rejected.
535. **Input**: Standard-result topology: `result=1, failure=0` vs `result=1, failure=1`. **Expected output**: `result=1, failure=0` passes; `result=1, failure=1` raises `ValueError` with `"sizing_run_failure_result"`. **Exception**: `ValueError` — regression: failure-result rejected.
536. **Input**: SUCCEEDED: `unique=10, evaluated=10, verified=10, feasible=11, result=1, failure=0`. **Expected output**: Rejected by `invariant_feasible_count_range` because `feasible > unique`. **Exception**: `ValueError` — feasible range invariant fires before feasible_le_verified.
537. **Input**: Standalone `invariant_feasible_le_verified` helper with `unique=10, verified=8, feasible=9`. **Expected output**: `ValueError` raised because `feasible > verified`. **Exception**: `ValueError` — unit contract for feasible_le_verified independent of registry ordering.
538. **Input**: Deterministic candidate UUID5: same request+candidate → same UUID; different candidate → different UUID; insertion-order independent. **Expected output**: All three UUID5 invariants satisfied. **Exception**: N/A — regression: deterministic IDs unchanged.
539. **Input**: Acceptance Criteria labels #501–#540 as Round 30. **Expected output**: First Acceptance Criteria item references Round 31; required test matrix entry references Round 30 (501–540). **Exception**: N/A — sync test: label and gate consistency.
540. **Input**: Tests 1–540 continuous, zero/dual roots rejected, Frozen SHA and Round 31 gate synchronized. **Expected output**: Global numbering continuous, Issue frozen SHA matches new commit, gate at Round 31. **Exception**: N/A — structural sync check.
---

## 28. Delivery Sequence

1. Complete Round 31 Engineering Design Review.
2. Only after review passes: create implementation branch and Draft PR.
3. Implement catalog and identity models before optimizer.
4. Implement deterministic candidate generation and deduplication.
5. Integrate TASK-008 `rate_double_pipe()` with exact 4-field `SolverParams`.
6. Implement feasibility and ranking.
7. Implement result hash, provenance, JSON round-trip, tamper detection.
8. Add direct, Golden, and integration tests.
9. Keep PR Draft through engineering review and CI pass.

---

## 29. Acceptance Criteria

- [ ] Round 31 Engineering Design Review passes before implementation starts
- [ ] Only caller-supplied, structurally validated, hash-verified catalog candidates
- [ ] `SourceQualifiedCandidateIdentity` is the deduplication key
- [ ] TASK-008 `rate_double_pipe()` is sole thermal evaluator
- [ ] `SolverParams` uses exact 4-field TASK-008 contract
- [ ] `tube_in_hot` bound in sizing identity, not rating identity
- [ ] `CalculationContext` preserves caller revision/run IDs; only `request_id` derived per candidate
- [ ] Candidate generation and ranking insertion-order independent
- [ ] Target satisfaction dominates objective value
- [ ] Top-N feasible-only; truncation adds warning
- [ ] Non-feasible ordering uses full `CandidateDiagnosticKey` sort key
- [ ] Four candidate evaluation states with exact evidence invariants
- [ ] Single integrity-invalid candidate stops immediately, blocks run
- [ ] Provenance topology deterministic per termination class
- [ ] Two-stage core/final provenance; edge tamper via graph digest
- [ ] Invalid-request BLOCKED uses `InvalidSizingRequestSnapshot`
- [ ] All identity/hash uses `sha256:...` + `canonical_json`
- [ ] Exact 14 TASK-009 ErrorCode strings; `CATALOG_IDENTITY_MISMATCH` vs `HASH_MISMATCH` non-overlapping
- [ ] No pressure-drop or velocity constraint
- [ ] Required test matrix entries 1–540 (continuous), including Round 6 (89–136), Round 7 (137–176), Round 8 (177–204), Round 9 (205–244), Round 10 (245–295), Round 11 (296–332), Round 12 (333–370), Round 13 (371–405), Round 14 (406–430), Round 15 (431–460), Round 16 (461–500), and Round 30 (501–540)
- [ ] Ruff, format, mypy, pytest+coverage, pip-audit pass on 3.11/3.12
- [ ] Engineering design review passes before Ready or merge
