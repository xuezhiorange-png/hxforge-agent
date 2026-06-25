# TASK-009 — Manufacturable sizing and deterministic candidate optimization

**Status:** BLOCKED — Engineering design review changes required
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-005, TASK-008
**GitHub Issue:** #23
**Implementation branch:** Not created
**Draft PR:** Not created
**Production implementation:** Not started

TASK-009 returns to READY only after Round 12 Engineering Design Review passes.

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

---

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
    "hash_verification_outcome": ...,
    "provenance_verification_outcome": ...,
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

Only the following field names may be read from the unverified result:

```text
rating_status
result_hash
provenance_digest
request_identity_digest
execution_context_digest
provider_identity_digest
```

Each entry:

```python
field_digest = sha256_digest({
    "field_name": field_name,
    "canonical_value": safe_canonical_value,
})
```

`safely_readable_field_digests` is `tuple[(field_name, field_digest), ...]` sorted by field_name ASCII ascending.

Rules:
- If a whitelist field doesn't exist on the result object → skip (do not include in tuple)
- If reading the field raises an exception → skip (record as unavailable)
- If the field value cannot be safely canonicalized → skip
- No alias detection (field_name must match exactly 1:1)
- Duplicate with snapshot-level claimed fields is expected (the field digest is the same canonicalized value used independently)
- `UNREADABLE` = all whitelist fields are unavailable (no object, damaged object)
- Never read `__dict__`, internal properties, or call arbitrary methods

**Digest payload:**

```python
claimed_audit_payload = {
    "source_qualified_candidate_id": ...,
    "evaluation_order_index": ...,
    "claim_state": ...,
    "claimed_rating_status": ...,
    "claimed_result_hash": ...,
    "claimed_provenance_digest": ...,
    "claimed_request_identity_digest": ...,
    "claimed_execution_context_digest": ...,
    "claimed_provider_identity_digest": ...,
    "hash_verification_outcome": ...,
    "provenance_verification_outcome": ...,
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
5. `selected_candidate = None`, `top_candidates = ()`, `partial_audit = True`
6. Evaluate `remaining_unevaluated_candidate_count = unique - evaluated`

**hash_verification_outcome == ERROR or provenance_verification_outcome == ERROR:**

1. `CandidateEvaluationState = RUNTIME_FAILED`
2. `failure_stage = RATING_VERIFICATION`
3. This candidate counted in `evaluated_candidate_count`
4. **Stop immediately** — remaining candidates unevaluated
5. `status = FAILED`, `failure = RunFailure`
6. `selected_candidate = None`, `top_candidates = ()`, `partial_audit = True`
7. Evaluate `remaining_unevaluated_candidate_count = unique - evaluated`

The error path does NOT construct a trusted `InvalidRatingEvidenceRecord` (the verification process failed, not the integrity check). If a claimed audit record is needed, use `CLAIMED_TASK008_RATING_RESULT` (§21.4 RATING_VERIFICATION).

### 14.7 VerifiedRatingEvidenceDigest

Full deterministic digest payload for `VerifiedRatingEvidenceSnapshot`:

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
# RatingRequestIdentity
rating_request_identity_payload = {
    "source_qualified_candidate_id": ...,
    "sizing_request_identity_digest": ...,
    "rating_request_identity_digest": ...,
    "provider_identity_digest": ...,
    "execution_context_identity_digest": ...,
    "rating_result_hash": ...,
    "rating_provenance_digest": ...,
}
rating_request_identity_digest = sha256_digest(rating_request_identity_payload)
```

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

```python
# EngineeringMessage
engineering_message_payload = {
    "code": ...,
    "severity": ...,
    "source_module": ...,
    "affected_paths": ...,
    "message": ...,
    "context_digest": ...,
}
engineering_message_digest = sha256_digest(engineering_message_payload)
```

```python
# RunFailure
run_failure_payload = {
    "failure_stage": ...,
    "candidate_id": ...,
    "evaluation_order_index": ...,
    "context": canonicalized_context,
}
run_failure_digest = sha256_digest(run_failure_payload)
```

Explicit `None` handling: nullable fields enter the payload as `None` (not omitted).
All computed via the standard `sha256_digest(payload)` contract — single call, `canonical_json` handled internally.

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
{
    "source_qualified_candidate_identity_digest": ...,
    "candidate_evaluation_state": ...,
    "candidate_evaluation_identity_digest": ... | None,
    "evaluation_order_index": ...,
    "rating_status": ... | None,
    "feasibility_status": ...,
    "feasible": ...,
    "verified_rating_evidence_digest": ... | None,
    "invalid_rating_evidence_digest": ... | None,
    "evaluation_failure_digest": ... | None,
    "diagnostic_digests": [...],
    "primary_diagnostic_digest": ... | None,
    "duty_margin_w": ... | None,
    "duty_shortfall_w": ... | None,
    "duty_overshoot_w": ... | None,
    "meets_target_without_tolerance": ... | None,
}
candidate_evaluation_digest = sha256_digest(payload)
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

When `rating_status in (BLOCKED, FAILED)` or `heat_duty_w is None` or `CandidateEvaluationState == PROVIDER_IDENTITY_MISMATCH`:

```text
duty_margin_w = None
duty_shortfall_w = None
duty_overshoot_w = None
meets_target_without_tolerance = None
feasibility_status = RATING_BLOCKED (if BLOCKED) or RATING_FAILED (if FAILED)
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
| `NON_STRING_MAPPING_KEY` | `"non_string_mapping_key"` | `"Mapping key is not a string"` | `("$mapping_entries", key_payload_digest [, occurrence_index])` | `sha256(key_marker)` | `("key_type", "key_kind")` | 1 per non-string-key entry |
| `UNSUPPORTED_RAW_MAPPING_KEY` | `"unsupported_raw_mapping_key"` | `"Mapping key is an unsupported type"` | `("$mapping_entries", key_payload_digest [, occurrence_index])` | `sha256(key_marker)` | `("key_type",)` | 1 per opaque-key entry (NOT also NON_STRING_MAPPING_KEY) |
| `UNSUPPORTED_RAW_INPUT_TYPE` | `"unsupported_raw_input_type"` | `"Unsupported value type in input"` | `("$unsupported_type",)` | `sha256(marker)` | `("object_type",)` | 1 per occurrence |
| `CYCLIC_RAW_INPUT` | `"cyclic_raw_input"` | `"Container has cyclic reference"` | `("$cyclic_reference",)` | `sha256(marker)` | `("ancestor_distance",)` | 1 per cycle occurrence |
| `NON_FINITE_RAW_FLOAT` | `"non_finite_raw_float"` | `"Float value is NaN or Infinity"` | per context | `sha256(value)` | `("original_value",)` | 1 per occurrence |

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
    "status": ...,
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
warning_digests: tuple[str, ...]
blocker_digests: tuple[str, ...]
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
    primary_diagnostic.diagnostic_class_rank,
    primary_diagnostic.code,
    primary_diagnostic.source_module,
    primary_diagnostic.affected_paths,
    primary_diagnostic.message,
    source_qualified_candidate_id,
)
```

### 20.5 CandidateDiagnosticKey

```text
diagnostic_class_rank: int   # BLOCKER=0, ERROR=1, WARNING=2, INFO=3, RUNTIME_FAILURE=4
code: str
source_module: str
affected_paths: tuple[str, ...]
message: str
```

Sentinel when `None`: `(999, "", "", (), "")`.

From EngineeringMessage: direct. From RunFailure: class_rank=4. From pure duty-infeasible: class_rank=0, code=`REQUIRED_DUTY_NOT_MET`.

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
| CLAIMED_TASK008_RATING_RESULT | `INTERMEDIATE` | `"claimed_rating_{candidate_id}"` |
| SIZING_RESULT | `RESULT` | `"sizing_result"` |
| SIZING_RUN_FAILURE_RESULT | `RESULT` | `"sizing_run_failure"` |
| INVALID_EVIDENCE | `INTERMEDIATE` | `"invalid_evidence_{candidate_id}"` |
| RUNTIME_FAILURE | `BLOCKER` | `"runtime_failure"` |
| WARNING | `WARNING` | per message |
| BLOCKER | `BLOCKER` | per message |

Root selection: if `design_case_revision_id` is present and not None → `ROOT_CASE_REVISION` with `CASE_REVISION` type and label `"revision_{id}"`. Otherwise → `ROOT_EXTERNAL` with `EXTERNAL` type and label `"external_root"`.

Two distinct `ROOT` concepts prevent expression of root-type selection within a single ambiguous table entry.

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

No two edges share an ambiguous label with different semantics.

### 22.2 UUID5 Namespace

```python
TASK009_PROVENANCE_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
```

### 22.3 UUID5 Name Payloads

```text
sizing-run:{validated_sizing_request_identity_digest}
sizing-run:raw:{raw_request_digest}            (invalid request)
catalog:{catalog_id}:{catalog_version}:{catalog_content_hash}
candidate:{source_qualified_candidate_id}
rating-result:{rating_result_hash}
claimed-rating-result:{source_qualified_candidate_id}:{evaluation_order_index}:{audit_digest}
invalid-evidence:{source_qualified_candidate_id}:{invalid_evidence_digest}
optimizer:{validated_sizing_request_identity_digest}
sizing-result:{result_hash}
sizing-run-failure:{failure_result_hash}
warning:{code}:{message_digest}:{context_digest}
blocker:{code}:{message_digest}:{context_digest}
runtime-failure:{failure_digest}
root-case-revision:{design_case_revision_id}
root-external:{raw_request_digest if invalid request else validated_sizing_request_identity_digest}
```

### 22.4 Termination-Class Topologies

Each entry lists exact nodes (with multiplicity), exact edges, and forbidden nodes.

#### INVALID_REQUEST

```
Nodes:
- ROOT (1, type per root selection rule)
- SIZING_RUN (1, id = sizing-run:raw:{raw_request_digest})
- BLOCKER (>=1)
- SIZING_RESULT (1)
Forbidden: CATALOG, CANDIDATE, TASK008_RATING_RESULT, OPTIMIZER, INVALID_EVIDENCE, RUNTIME_FAILURE
Edges:
- ROOT -> SIZING_RUN "initiates"
- BLOCKER -> SIZING_RESULT "blocks"
- SIZING_RUN -> SIZING_RESULT "produces"
```

#### INVALID_CATALOG / CATALOG_IDENTITY_MISMATCH

```
Nodes:
- ROOT (1)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (1 per invalid catalog)
- BLOCKER (>=1)
- SIZING_RESULT (1)
Forbidden: CANDIDATE, TASK008_RATING_RESULT, OPTIMIZER, INVALID_EVIDENCE, RUNTIME_FAILURE
Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- BLOCKER -> SIZING_RESULT "blocks"
- SIZING_RUN -> SIZING_RESULT "produces"
```

#### CAP_EXCEEDED / NO_MANUFACTURABLE_CANDIDATE

```
Nodes:
- ROOT (1)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (1 per catalog)
- BLOCKER (>=1)
- SIZING_RESULT (1)
Forbidden: CANDIDATE, TASK008_RATING_RESULT, OPTIMIZER, INVALID_EVIDENCE, RUNTIME_FAILURE
Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- BLOCKER -> SIZING_RESULT "blocks"
- SIZING_RUN -> SIZING_RESULT "produces"
```

#### NO_FEASIBLE_CANDIDATE (evaluated but no feasible)

```
Nodes:
- ROOT (1)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (1 per catalog)
- CANDIDATE (1 per candidate)
- TASK008_RATING_RESULT (1 per candidate)
- OPTIMIZER (1)
- BLOCKER (>=1)
- SIZING_RESULT (1)
Forbidden: INVALID_EVIDENCE, RUNTIME_FAILURE
Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- CATALOG_SNAPSHOT -> CANDIDATE "generates"
- SIZING_RUN -> OPTIMIZER "executes"
- CANDIDATE -> TASK008_RATING_RESULT "rated_as"
- TASK008_RATING_RESULT -> OPTIMIZER "evaluated_by"
- OPTIMIZER -> SIZING_RESULT "produces"
- BLOCKER -> SIZING_RESULT "blocks"
```

#### RATING_RESULT_INTEGRITY_FAILED

```text
Nodes:
- ROOT (1, type per root selection rule)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (1 per catalog)
- CANDIDATE (unique_candidate_count)
- VERIFIED TASK008_RATING_RESULT (verified_rating_count)
- INVALID_EVIDENCE (1 per integrity-invalid candidate)
- BLOCKER (>=1)
- SIZING_RESULT (1)
Forbidden: OPTIMIZER, RUNTIME_FAILURE, CLAIMED_TASK008_RATING_RESULT

Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- CATALOG_SNAPSHOT -> CANDIDATE "generates"
- CANDIDATE -> VERIFIED TASK008 result "rated_as" (for each verified)
- CANDIDATE(current) -> INVALID_EVIDENCE "produced_unverified"
- INVALID_EVIDENCE -> SIZING_RESULT "invalidates"
- BLOCKER -> SIZING_RESULT "blocks"
- SIZING_RUN -> SIZING_RESULT "produces"

Counters:
attempted = completed = verified + 1
evaluated = attempted
remaining = unique - attempted
partial_audit = True

Candidate records:
- prior candidates = VERIFIED
- current candidate = INTEGRITY_INVALID
- remaining candidates = UNEVALUATED
```

All `CANDIDATE` nodes correspond to the full `unique_candidate_count` — not just the evaluated subset.

#### SUCCEEDED

```
Nodes:
- ROOT (1)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (1 per catalog)
- CANDIDATE (1 per candidate)
- TASK008_RATING_RESULT (1 per candidate)
- OPTIMIZER (1)
- WARNING (0 or more)
- SIZING_RESULT (1)
Forbidden: BLOCKER, INVALID_EVIDENCE, RUNTIME_FAILURE
Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- CATALOG_SNAPSHOT -> CANDIDATE "generates"
- SIZING_RUN -> OPTIMIZER "executes"
- CANDIDATE -> TASK008_RATING_RESULT "rated_as"
- TASK008_RATING_RESULT -> OPTIMIZER "evaluated_by"
- OPTIMIZER -> SIZING_RESULT "produces"
- WARNING -> SIZING_RESULT "annotates"  (if any)
```

#### PROPERTY_PROVIDER_IDENTITY_MISMATCH

```text
Nodes:
- ROOT (1, type per root selection rule)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (1 per catalog)
- CANDIDATE (unique_candidate_count)
- VERIFIED TASK008_RATING_RESULT (verified_rating_count)
- BLOCKER (>=1)
- SIZING_RESULT (1)
Forbidden: OPTIMIZER, INVALID_EVIDENCE, CLAIMED_TASK008_RATING_RESULT, RUNTIME_FAILURE

Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- CATALOG_SNAPSHOT -> CANDIDATE "generates"
- CANDIDATE -> VERIFIED TASK008 result "rated_as" (for each verified)
- BLOCKER -> SIZING_RESULT "blocks"
- SIZING_RUN -> SIZING_RESULT "produces"

Counters:
attempted = completed = verified
evaluated = attempted
remaining = unique - attempted
partial_audit = (attempted < unique)

Candidate records:
- through mismatching candidate = VERIFIED
- remaining = UNEVALUATED
```

Provider mismatch candidate's verified evidence:
- Preserves actual provider identity
- Marks mismatch diagnostic (not feasibility/ranking failure)
- `selected_candidate = None`, `top_candidates = ()`

#### RUNTIME_FAILED

Each RUNTIME_FAILED result is assigned a `FailureStage` (see §21). The exact topology is determined by the stage at which the failure occurred.

##### REQUEST_VALIDATION

```
Nodes:
- ROOT (1)
- SIZING_RUN (1, id = sizing-run:raw:{raw_request_digest})
- RUNTIME_FAILURE (1)
- SIZING_RESULT (1)
Forbidden: CATALOG_SNAPSHOT, CANDIDATE, TASK008_RATING_RESULT, OPTIMIZER, INVALID_EVIDENCE
Edges:
- ROOT -> SIZING_RUN "initiates"
- RUNTIME_FAILURE -> SIZING_RESULT "fails"
- SIZING_RUN -> SIZING_RESULT "produces"
Count sources: raw_request_digest
```

##### CATALOG_VALIDATION

```
Nodes:
- ROOT (1)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (validated_catalog_count)
- RUNTIME_FAILURE (1)
- SIZING_RESULT (1)
Forbidden: CANDIDATE, TASK008_RATING_RESULT, OPTIMIZER, INVALID_EVIDENCE
Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- RUNTIME_FAILURE -> SIZING_RESULT "fails"
- SIZING_RUN -> SIZING_RESULT "produces"
Count sources: validated_catalog_count
```

##### CANDIDATE_MATERIALIZATION

```
Nodes:
- ROOT (1)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (catalog_count)
- CANDIDATE (materialized_candidate_count)
- RUNTIME_FAILURE (1)
- SIZING_RESULT (1)
Forbidden: TASK008_RATING_RESULT, OPTIMIZER, INVALID_EVIDENCE
Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- CATALOG_SNAPSHOT -> CANDIDATE "generates"
- RUNTIME_FAILURE -> SIZING_RESULT "fails"
- SIZING_RUN -> SIZING_RESULT "produces"
Count sources: catalog_count, materialized_candidate_count
```

##### PRE_RATING

```
Nodes:
- ROOT (1)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (catalog_count)
- CANDIDATE (unique_candidate_count)
- TASK008_RATING_RESULT (0)
- RUNTIME_FAILURE (1)
- SIZING_RESULT (1)
Forbidden: TASK008_RATING_RESULT, OPTIMIZER, INVALID_EVIDENCE
Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- CATALOG_SNAPSHOT -> CANDIDATE "generates"
- SIZING_RUN -> SIZING_RESULT "produces"
- RUNTIME_FAILURE -> SIZING_RESULT "fails"
partial_audit: True, evaluated_candidate_count: 0
```

##### RATING_CALL

```
Nodes:
- ROOT (1)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (catalog_count)
- CANDIDATE (unique_candidate_count)
- TASK008_RATING_RESULT (completed_rating_count)
- RUNTIME_FAILURE (1)
- SIZING_RESULT (1)
Forbidden: INVALID_EVIDENCE, OPTIMIZER
Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- CATALOG_SNAPSHOT -> CANDIDATE "generates"
- CANDIDATE -> TASK008_RATING_RESULT "rated_as" (for each completed rating)
- RUNTIME_FAILURE -> SIZING_RESULT "fails"
- SIZING_RUN -> SIZING_RESULT "produces"
Count sources: attempted_rating_count = completed_rating_count + 1
evaluated_candidate_count = attempted_rating_count
remaining_unevaluated_candidate_count = unique_candidate_count - attempted_rating_count
verified_rating_count = completed_rating_count
The failed candidate is RUNTIME_FAILED, has no TASK008_RATING_RESULT,
and is NOT counted as remaining unevaluated.
```

##### RATING_VERIFICATION

```text
Nodes:
- ROOT (1, type per root selection rule)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (catalog_count)
- CANDIDATE (unique_candidate_count)
- VERIFIED TASK008_RATING_RESULT (verified_rating_count)
- CLAIMED TASK008_RATING_RESULT (exactly 1)
- RUNTIME_FAILURE (1)
- SIZING_RESULT (1)
Forbidden: INVALID_EVIDENCE, OPTIMIZER
Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- CATALOG_SNAPSHOT -> CANDIDATE "generates"
- CANDIDATE -> VERIFIED result "rated_as" (for each verified rating)
- CANDIDATE(current) -> CLAIMED result "rated_as_claimed" (exactly 1)
- RUNTIME_FAILURE -> SIZING_RESULT "fails"
- SIZING_RUN -> SIZING_RESULT "produces"
Count: attempted_rating_count = completed_rating_count
evaluated_candidate_count = attempted_rating_count
completed_rating_count = verified_rating_count + 1
CLAIMED_TASK008_RATING_RESULT multiplicity = 1 (exactly one claimed node)
remaining_unevaluated_candidate_count = unique_candidate_count - attempted_rating_count

The claimed-rating-result node uses CLAIMED_TASK008_RATING_RESULT concept
(ProvenanceNodeType.INTERMEDIATE). It is NOT a verified TASK008 result.
UUID5 name (when result hash unreadable):

```text
uuid5(TASK009_PROVENANCE_NAMESPACE,
    "claimed-rating-result:{source_qualified_candidate_id}:{evaluation_order_index}:{audit_digest}")
```

`audit_digest` is the full `ClaimedRatingResultAuditSnapshot` digest. Always uses the same formula — no condition on result hash readability.

Claimed node payload hash: `sha256_digest(claimed_audit_payload)`.

The `claim_state` is one of: `"hash_verification_error"`, `"provenance_verification_error"`, `"unreadable"`.
```
```

##### OPTIMIZATION

```text
Nodes:
- ROOT (1)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (catalog_count)
- CANDIDATE (unique_candidate_count)
- TASK008_RATING_RESULT (evaluated_candidate_count = unique_candidate_count; all verified)
- OPTIMIZER (1)
- RUNTIME_FAILURE (1)
- SIZING_RESULT (1)
Forbidden: INVALID_EVIDENCE, CLAIMED_TASK008_RATING_RESULT
Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- CATALOG_SNAPSHOT -> CANDIDATE "generates"
- CANDIDATE -> TASK008_RATING_RESULT "rated_as"
- TASK008_RATING_RESULT -> OPTIMIZER "evaluated_by"
- OPTIMIZER -> SIZING_RESULT "produces"
- RUNTIME_FAILURE -> SIZING_RESULT "fails"
partial_audit: False, evaluated_candidate_count: unique
optimizer_node_exists: True, rating_result_nodes_exist: True
CLAIMED_TASK008_RATING_RESULT count: 0 (precondition: attempted == completed == verified == unique)
```

##### RESULT_CONSTRUCTION

Uses `SizingRunFailureResult` (independent schema, not `SizingOptimizationResult`):

```text
SizingRunFailureResult
- status: FAILED
- raw_request_digest: str
- validated_sizing_request_identity_digest: str | None
- failure_stage: RESULT_CONSTRUCTION
- failure: RunFailure
- catalog_snapshots: tuple[CompleteDoublePipeCatalogSnapshot, ...]
- candidate_evaluations: tuple[CandidateEvaluation, ...]
- verified_rating_evidence: tuple[VerifiedRatingEvidenceSnapshot, ...]
- invalid_rating_evidence: tuple[InvalidRatingEvidenceRecord, ...]
- claimed_rating_audits: tuple[ClaimedRatingResultAuditSnapshot, ...]
- ranking_records: tuple[CandidateRankingRecord, ...]
- warnings: tuple[EngineeringMessage, ...]
- blockers: tuple[EngineeringMessage, ...]
- catalog_snapshot_digests: tuple[str, ...]
- candidate_evaluation_digests: tuple[str, ...]
- verified_evidence_digests: tuple[str, ...]
- invalid_evidence_digests: tuple[str, ...]
- claimed_rating_audit_digests: tuple[str, ...]
- warning_digests: tuple[str, ...]
- blocker_digests: tuple[str, ...]
- ranking_record_digests: tuple[str, ...]
- attempted_rating_count: int
- completed_rating_count: int
- verified_rating_count: int
- unique_candidate_count: int
- feasible_candidate_count: int
- partial_audit: bool
- core_provenance_digest: str
- failure_result_hash: str
- provenance: ProvenanceGraph
- provenance_digest: str
```

All digest collections sorted by canonical order (§23.4). `partial_audit = False` (evaluation completed all unique candidates).

**Failure hash payload:**

```python
failure_result_payload = {
    "raw_request_digest": ...,
    "validated_sizing_request_identity_digest": ...,
    "failure_stage": "result_construction",
    "failure_digest": ...,
    "catalog_snapshot_digests": [...],
    "candidate_evaluation_digests": [...],
    "verified_evidence_digests": [...],
    "invalid_evidence_digests": [...],
    "claimed_rating_audit_digests": [...],
    "warning_digests": [...],
    "blocker_digests": [...],
    "ranking_record_digests": [...],
    "attempted_rating_count": ...,
    "completed_rating_count": ...,
    "verified_rating_count": ...,
    "unique_candidate_count": ...,
    "feasible_candidate_count": ...,
    "partial_audit": False,
    "core_provenance_digest": ...,
}
failure_result_hash = sha256_digest(failure_result_payload)
```

**Provenance node concept:** `SIZING_RUN_FAILURE_RESULT`

```text
ProvenanceNodeType   = RESULT
label                = "sizing_run_failure"
UUID5                = uuid5(TASK009_PROVENANCE_NAMESPACE,
                       "sizing-run-failure:{failure_result_hash}")
payload_hash         = sha256_digest({"failure_result_hash": failure_result_hash})
metadata             = (("failure_result_hash", failure_result_hash),
                       ("failure_stage", "result_construction"))
```

**Exact RESULT_CONSTRUCTION topology:**

```text
Nodes:
- ROOT (1, type per root selection rule)
- SIZING_RUN (1)
- CATALOG_SNAPSHOT (catalog_count)
- CANDIDATE (unique_candidate_count)
- VERIFIED TASK008_RATING_RESULT (verified_rating_count = unique_candidate_count)
- OPTIMIZER (1)
- RUNTIME_FAILURE (1)
- SIZING_RUN_FAILURE_RESULT (1)
Forbidden: CLAIMED_TASK008_RATING_RESULT, INVALID_EVIDENCE

Edges:
- ROOT -> SIZING_RUN "initiates"
- SIZING_RUN -> CATALOG_SNAPSHOT "consumes"
- CATALOG_SNAPSHOT -> CANDIDATE "generates"
- CANDIDATE -> TASK008_RATING_RESULT "rated_as" (all verified)
- TASK008_RATING_RESULT -> OPTIMIZER "evaluated_by"
- OPTIMIZER -> SIZING_RUN_FAILURE_RESULT "precedes_failure"
- RUNTIME_FAILURE -> SIZING_RUN_FAILURE_RESULT "fails"
- SIZING_RUN -> SIZING_RUN_FAILURE_RESULT "produces_failure_record"

partial_audit: False
attempted_rating_count == evaluated_candidate_count == verified_rating_count == unique_candidate_count
CLAIMED_TASK008_RATING_RESULT count: 0 (precondition for entering optimization/result construction)
```

**JSON:** `SizingRunFailureResult` must be JSON round-trippable with all fields, digests, and provenance.

### 22.5 Failure-Result Two-Stage Provenance Construction

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

1. Reconstruct failure core graph from result fields (catalog digests, evaluation digests, verified evidence digests, etc.)
2. Verify `core_provenance_digest` matches reconstruction
3. Recompute failure result payload and hash
4. Rebuild `SIZING_RUN_FAILURE_RESULT` node
5. Rebuild final failure graph
6. Verify `failure_final_provenance_digest`
7. Detect node, edge, and payload tamper

Standard result verification and failure result verification are two separate branches — no shared code path ambiguity.

### 22.6 partial_audit

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

### 22.7 Edge Tamper Detection

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

Each `CandidateEvaluation` has a digest computed from the unified payload defined in §15.1:

```python
candidate_evaluation_digest = sha256_digest({
    "source_qualified_candidate_identity_digest": ...,
    "candidate_evaluation_state": ...,
    "candidate_evaluation_identity_digest": ... | None,
    "evaluation_order_index": ...,
    "rating_status": ... | None,
    "feasibility_status": ...,
    "feasible": ...,
    "verified_rating_evidence_digest": ... | None,
    "invalid_rating_evidence_digest": ... | None,
    "evaluation_failure_digest": ... | None,
    "diagnostic_digests": [...],
    "primary_diagnostic_digest": ... | None,
    "duty_margin_w": ... | None,
    "duty_shortfall_w": ... | None,
    "duty_overshoot_w": ... | None,
    "meets_target_without_tolerance": ... | None,
    "partial_audit": ...,
})
```

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
- Validation errors (`SizingValidationErrorSnapshot`) | `(code.value, message_key, field_path, rejected_value_digest or "", context_digest)` ascending |

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
    "context": canonicalized_context
})
```

This ensures insertion-order independence for all identity digests and provenance graphs.

Provenance UUID5 names for warnings and blockers include context digest to prevent node collision when the same code and message have different context:

```text
warning:{code}:{message_digest}:{context_digest}
blocker:{code}:{message_digest}:{context_digest}
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
173. Acceptance Criteria references Round 12
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
197. `RESULT_CONSTRUCTION` exact edge set (8 edges, including `precedes_failure`)
198. Failure result embeds canonical audit digest collections (catalog, evaluation, evidence, ranking digests)
199. No `RawInputCanonicalizationError` exists in test descriptions (all use deterministic marker)
200. 4 `CandidateEvaluationState` enum values / 7 invariant rows consistency
201. Section numbering continuous (no gaps, section 20.3 present)
202. Issue #23 test total equals task-card N
203. Issue #23 frozen SHA equals new docs commit
204. Acceptance Criteria references Round 12

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
243. Test numbering continuous 1–295 (no gaps, no duplicates)
244. Issue #23 and task card test total both report N=295

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
267. Provider mismatch `partial_audit = True` (attempted < unique)
268. `CandidateEvaluation.partial_audit` removed from schema and digest
269. RATING_VERIFICATION exact: `completed = verified + 1`
270. RATING_VERIFICATION exactly 1 claimed audit and 1 claimed node
271. Enum dispatch before str (StrEnum not matched as str)
272. IntEnum dispatch before int (IntEnum not matched as int)
273. Nested enum value validation errors propagated via `nested_validation_errors`
274. Mapping collision scope documented (Python pre-collision not recoverable)
275. Bool/int tests use separate observable mapping entries for dispatch verification
276. Finite float key value is float (not JSON string) in key_payload
277. `RawInputValidationCode` exact enum values (5 codes)
278. Supported non-string scalar key: `NON_STRING_MAPPING_KEY` ×1 (not also UNSUPPORTED_RAW_MAPPING_KEY)
279. Opaque mapping key: `UNSUPPORTED_RAW_MAPPING_KEY` ×1 (not also NON_STRING_MAPPING_KEY)
280. Unsupported value: `UNSUPPORTED_RAW_INPUT_TYPE` ×1 per occurrence
281. No "or frozen equivalent" text in document
282. Complete provenance registry contains all 14 concepts in Node Type Mapping
283. `ROOT_CASE_REVISION` UUID: `root-case-revision:{design_case_revision_id}`
284. `ROOT_EXTERNAL` UUID: `root-external:{...}` (request digest used)
285. CLAIMED result UUID: `claimed-rating-result:{candidate_id}:{index}:{audit_digest}` (always, not conditional)
286. Failure-result UUID: `sizing-run-failure:{failure_result_hash}`
287. Top-level heading sequence continuous (1–29, no gaps)
288. Section 21 exists (RunFailure Stage Model)
289. Section 28 Delivery Sequence heading exists
290. Test numbering continuous 1–295
291. Section heading test: all `## N.` extracted as int list equals `range(1, 30)`
292. Section heading test: no duplicates, no gaps
293. Test matrix section range 27.1–27.15 continuous
294. Issue #23 test total equals task card N=332
295. Acceptance Criteria references Round 12

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
317. Subsection headings continuous within each parent section (14.1–14.7, 18.1.1–18.1.6, 19A.1–19A.8, 20.1–20.6, 22.1–22.7, 27.1–27.15)
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
330. Acceptance Criteria references Round 12
331. Issue #23 frozen SHA equals new docs commit
332. Test numbering continuous 1–332; Issue and task card test total match

---

## 28. Delivery Sequence

1. Complete Round 12 Engineering Design Review.
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

- [ ] Round 12 Engineering Design Review passes before implementation starts
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
- [ ] Required test matrix entries 1–332 (continuous), including Round 6 (89–136), Round 7 (137–176), Round 8 (177–204), Round 9 (205–244), Round 10 (245–295), and Round 11 (296–332)
- [ ] Ruff, format, mypy, pytest+coverage, pip-audit pass on 3.11/3.12
- [ ] Engineering design review passes before Ready or merge
