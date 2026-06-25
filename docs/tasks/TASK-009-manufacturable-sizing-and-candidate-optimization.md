# TASK-009 — Manufacturable sizing and deterministic candidate optimization

**Status:** BLOCKED — Engineering design review changes required
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-005, TASK-008
**GitHub Issue:** #23
**Implementation branch:** Not created
**Draft PR:** Not created
**Production implementation:** Not started

TASK-009 returns to READY only after Round 3 Engineering Design Review passes.

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

From a caller-supplied, structurally validated, hash-verified set of complete double-pipe assembly options, generate deterministic discrete candidates, evaluate each through the TASK-008 `rate_double_pipe()` kernel, apply explicit feasibility and manufacturability contracts, and return a deterministic ranked result with complete hash, provenance, and JSON round-trip integrity.

---

## 3. Design Review History

| Round | Review Comment ID | Decision |
|-------|-------------------|----------|
| 1 | 4797079477 | CHANGES REQUIRED |
| 2 | 4797175254 | CHANGES REQUIRED |

---

## 4. Data Model

### 4.1 Container Hierarchy

```text
SizingRequest
  └── CompleteDoublePipeCatalogSnapshot[]
        └── CompleteDoublePipeAssemblyOption[]
              └── LengthSource
```

A single request carries one or more **catalog snapshots**. Each catalog snapshot contains one or more **assembly options**. Each assembly option contains exactly one **length source**.

### 4.2 CompleteDoublePipeCatalogSnapshot

```text
catalog_id: str
catalog_version: str
source_identity: str
schema_version: str
assembly_options: tuple[CompleteDoublePipeAssemblyOption, ...]
catalog_content_hash: str
```

`catalog_content_hash` is a SHA-256 hex digest computed over the canonical JSON payload of all fields **except itself**. The payload is serialized in the following order: `catalog_id`, `catalog_version`, `source_identity`, `schema_version`, and each `assembly_options` element in canonical option order (sorted by `assembly_option_id` ascending, ASCII). JSON fields are serialized with sorted keys, no whitespace, no trailing newline.

### 4.3 CompleteDoublePipeAssemblyOption

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
manufacturing_metadata: dict[str, str]
```

Fouling resistances are physical/design properties of the assembly option. They enter both `SourceQualifiedCandidateIdentity` and the TASK-008 `RatingRequestIdentity`.

### 4.4 LengthSource

Exactly one of:

**Mode A — Explicit Lengths**

```text
allowed_effective_lengths_m: tuple[float, ...]
```

- each value must be finite and > 0
- values are Decimal-canonicalized, sorted ascending, and deduplicated
- empty tuple is invalid (catalog BLOCKED)

**Mode B — Length Grid**

```text
LengthGridSpec:
  minimum_length_m: float
  maximum_length_m: float
  increment_m: float
  endpoint_policy: LengthEndpointPolicy
  decimal_quantization: str
```

- all three numeric fields must be finite
- `minimum_length_m > 0`
- `maximum_length_m >= minimum_length_m`
- `increment_m > 0`
- `decimal_quantization` is a string constructable as `Decimal(quantum) > 0`
- grid expansion uses integer arithmetic over Decimal values (not cumulative float addition)
- a snapshot must not provide both explicit lengths and a LengthGridSpec

### 4.5 LengthEndpointPolicy

```text
class LengthEndpointPolicy(StrEnum):
    INCLUDE_MAX_IF_ALIGNED = "include_max_if_aligned"
    EXCLUDE_MAX = "exclude_max"
```

`INCLUDE_MAX_IF_ALIGNED`: include `maximum_length_m` only when the last grid step lands exactly on it within numerical tolerance.

`EXCLUDE_MAX`: exclude `maximum_length_m` from the generated set.

### 4.6 Grid Expansion Algorithm

```python
from decimal import Decimal, ROUND_HALF_EVEN

quantum = Decimal(decimal_quantization)
lo = Decimal(str(minimum_length_m)).quantize(quantum, rounding=ROUND_HALF_EVEN)
hi = Decimal(str(maximum_length_m)).quantize(quantum, rounding=ROUND_HALF_EVEN)
step = Decimal(str(increment_m)).quantize(quantum, rounding=ROUND_HALF_EVEN)

assert step > 0, "increment must remain positive after quantization"

n_steps_exact = (hi - lo) / step
n_steps = int(n_steps_exact.to_integral_value(rounding=ROUND_HALF_EVEN))

values = [lo + step * Decimal(i) for i in range(n_steps + 1)]

if endpoint_policy == LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED:
    last_val = values[-1]
    if abs(last_val - hi) > quantum / Decimal("2"):
        values.pop()
elif endpoint_policy == LengthEndpointPolicy.EXCLUDE_MAX:
    if len(values) > 0 and abs(values[-1] - hi) <= quantum / Decimal("2"):
        values.pop()

# Final canonicalization
result = sorted({v.quantize(quantum, rounding=ROUND_HALF_EVEN) for v in values})
result_float = tuple(float(v) for v in result)
```

`n_steps_exact` computation must use exact Decimal division. When `n_steps_exact` is not an integer, only the integer floor of generated points is included (the non-aligned endpoint is excluded regardless of policy).

### 4.7 Validation Fail-Closed

If any assembly option in any catalog snapshot is structurally invalid (missing field, negative diameter, zero-length non-positive increment, empty explicit-length tuple, or any validation failure), the entire sizing run is **BLOCKED** with `CATALOG_INVALID` and no TASK-008 rating call is made.

If any catalog snapshot has a `catalog_content_hash` mismatch, the entire run is **BLOCKED** with `CATALOG_IDENTITY_MISMATCH`.

If two or more assembly options share the same `assembly_option_id` within the same catalog snapshot, the entire run is **BLOCKED** with `CATALOG_INVALID`.

---

## 5. Rating Entry Point and Fouling

TASK-009 calls `rate_double_pipe()` directly — the pure function in `hexagent.exchangers.double_pipe.rating`. It does **not** call `DoublePipeRatingService.rate()` or any wrapper that may silently override geometry fouling from stream-side defaults.

Each candidate evaluation constructs a `DoublePipeGeometry` from the assembly option fields (including `inner_fouling_resistance_m2k_w`, `outer_fouling_resistance_m2k_w`) and passes it to `rate_double_pipe()`.

Fouling fields enter:
- the `SourceQualifiedCandidateIdentity` (via geometry)
- the TASK-008 `RatingRequestIdentity` (via the rating request digest)

---

## 6. Candidate Identity

### 6.1 PhysicalCandidateIdentity

Mutable-agnostic identity covering pure geometry and effective length:

```text
inner_tube_inner_diameter_m
inner_tube_outer_diameter_m
outer_pipe_inner_diameter_m
effective_length_m
wall_thermal_conductivity_w_m_k
inner_surface_roughness_m
annulus_surface_roughness_m
inner_fouling_resistance_m2k_w
outer_fouling_resistance_m2k_w
```

Two assembly options with identical geometry and length produce the same `PhysicalCandidateIdentity` regardless of catalog source or manufacturing option.

### 6.2 SourceQualifiedCandidateIdentity

```text
physical_candidate_identity_hash
catalog_id
catalog_version
catalog_content_hash
assembly_option_id
manufacturing_option_identity
```

### 6.3 Deduplication Rule

`unique_candidate_count` is computed after deduplication by `SourceQualifiedCandidateIdentity`. A catalog change (version, content hash), different assembly_option_id, or different manufacturing_option_identity produces a distinct candidate, even if geometry is identical. This reflects that different supply sources or manufacturing lines represent distinct manufacturable options.

Raw counts are computed before deduplication; the cap applies to `raw_combination_count`, not `unique_candidate_count`.

---

## 7. Pre-Evaluation Pipeline and Candidate Counts

### 7.1 Pipeline Order

```text
1. SizingRequest schema validation
2. Catalog snapshot schema and catalog_content_hash validation
3. Assembly option validation (fail-closed per §4.7)
4. Length expansion per §4.6 + request min/max intersection
5. raw_combination_count summation
6. Hard/request raw-cap check
7. Candidate identity materialization
8. SourceQualifiedCandidateIdentity deduplication
9. TASK-008 rating evaluation (iterate unique candidates)
```

### 7.2 Three Exact Counters

```text
raw_combination_count
unique_candidate_count
evaluated_candidate_count
```

`raw_combination_count`: sum of expanded length counts (after request min/max intersection) across all eligible assembly options, computed before candidate identity materialization. Uses Decimal arithmetic — no oversized list is allocated for the count.

`unique_candidate_count`: candidates remaining after `SourceQualifiedCandidateIdentity` deduplication.

`evaluated_candidate_count`: actual TASK-008 calls made (one per unique candidate).

### 7.3 Request Length Filtering

Request fields `minimum_effective_length_m` and `maximum_effective_length_m` intersect the catalog-provisioned length set. Filtering is applied after length expansion and before `raw_combination_count` enters the cap check. If an assembly option yields zero lengths after intersection, it contributes 0 to `raw_combination_count`. If all options yield zero, the run returns `NO_MANUFACTURABLE_CANDIDATE`.

Request must not supply an independent increment or grid to regenerate catalog lengths.

### 7.4 Cap

```text
HARD_RAW_COMBINATION_CAP = 10_000
request_raw_combination_cap  (optional, must be <= HARD_RAW_COMBINATION_CAP)
effective_cap = min(request_raw_combination_cap, HARD_RAW_COMBINATION_CAP)
```

The cap is checked against `raw_combination_count` after step 5. On cap exceeded:

```text
status = BLOCKED
raw_combination_count = computed value
unique_candidate_count = 0
evaluated_candidate_count = 0
selected_candidate = None
top_candidates = ()
blocker = CANDIDATE_COUNT_LIMIT_EXCEEDED
```

No partial candidate instantiation, partial evaluation, or silent truncation.

---

## 8. Duty Feasibility

### 8.1 Tolerance Fields

```text
duty_absolute_tolerance_w: float  (finite, >= 0)
duty_relative_tolerance: float    (finite, >= 0)
```

### 8.2 Effective Tolerance

```text
effective_duty_tolerance_w = max(
    duty_absolute_tolerance_w,
    duty_relative_tolerance * max(required_duty_w, 1.0)
)
```

### 8.3 Feasibility Condition

```text
rated_duty_w + effective_duty_tolerance_w >= required_duty_w
```

### 8.4 Derived Fields

```text
duty_margin_w = rated_duty_w - required_duty_w
duty_shortfall_w = max(-duty_margin_w, 0.0)
duty_overshoot_w = max(duty_margin_w, 0.0)
meets_target_without_tolerance = rated_duty_w >= required_duty_w
```

All tolerance fields, formula version, and computed values enter request identity, result hash, and provenance.

---

## 9. Optimization Objectives

### 9.1 Objective Enum

```text
class OptimizationObjective(StrEnum):
    MINIMUM_OUTER_HEAT_TRANSFER_AREA = "minimum_outer_heat_transfer_area"
    MINIMUM_EFFECTIVE_LENGTH = "minimum_effective_length"
```

Area objective uses TASK-008 `RatingResult.area_outer_m2` (consistent with the frozen inner-tube outer-surface U basis).

May **not** use: `area_inner_m2`, `UA_w_k`, `U_w_m2_k`, custom equivalent area, or implicit area basis.

Area basis enters request identity, result identity, and provenance.

### 9.2 Feasible Ranking Sort Keys

All tuples sorted ascending.

#### MINIMUM_OUTER_HEAT_TRANSFER_AREA

```text
(
    area_outer_m2,
    0 if meets_target_without_tolerance else 1,
    duty_shortfall_w,
    duty_overshoot_w,
    effective_length_m,
    source_qualified_candidate_id,
)
```

#### MINIMUM_EFFECTIVE_LENGTH

```text
(
    effective_length_m,
    0 if meets_target_without_tolerance else 1,
    duty_shortfall_w,
    duty_overshoot_w,
    area_outer_m2,
    source_qualified_candidate_id,
)
```

No weighted composite score. `selected_candidate == top_candidates[0]`. Input insertion order does not affect ranking. Identical engineering metrics resolved by canonical candidate ID (ascending).

---

## 10. SizingStatus and Invariants

```text
class SizingStatus(StrEnum):
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"
```

### 10.1 SUCCEEDED

- at least one feasible candidate
- `selected_candidate is not None`
- `selected_candidate.feasible is True`
- `top_candidates` is non-empty
- `blockers` is empty
- `failure` is empty
- `verify_hash()` is True
- `verify_provenance()` is True

### 10.2 BLOCKED

Deterministic non-executability or no solution. Includes: invalid request, invalid catalog, hash mismatch, cap exceeded, no manufacturable candidate, no feasible candidate, unsupported constraint, rating integrity failure.

- at least one blocker
- `selected_candidate is None`
- `failure` is empty
- result hash and provenance remain valid

`NO_FEASIBLE_CANDIDATE` → `BLOCKED`. Not FAILED.

### 10.3 FAILED

Unexpected runtime failures only.

- `failure` is not None
- `selected_candidate is None`
- result hash and provenance remain valid

---

## 11. Top-N Contract

```text
top_n: int  (>= 1)
```

`top_candidates` contains only feasible candidates, ranked by the objective-specific sort key (§9.2).

- `top_n <= feasible_candidate_count`: return exactly top `top_n`
- `top_n > feasible_candidate_count > 0`: return all feasible candidates, add `TOP_N_REDUCED_TO_FEASIBLE_COUNT` warning — do not block, do not pad
- `feasible_candidate_count == 0`: `status = BLOCKED`, `selected_candidate = None`, `top_candidates = ()`, `blocker = NO_FEASIBLE_CANDIDATE`

---

## 12. Non-Feasible Candidate Ordering

Non-feasible candidates appear in audit output only, not in `top_candidates`.

### 12.1 Feasibility Status Severity

```text
INFEASIBLE < RATING_BLOCKED < RATING_FAILED < INTEGRITY_INVALID
```

### 12.2 Rating Status Rank

```text
SUCCEEDED < BLOCKED < FAILED
```

A candidate that SUCCEEDs in TASK-008 but fails sizing feasibility is `INFEASIBLE`, not BLOCKED.

### 12.3 Non-Feasible Sort Key

```text
(
    feasibility_status_rank,
    rating_status_rank,
    diagnostic_key_error_code,
    source_qualified_candidate_id,
)
```

### 12.4 CandidateDiagnosticKey

Unified diagnostic for all non-feasible candidates:

```text
class CandidateDiagnosticKey:
    diagnostic_class_rank: int   # BLOCKER=0, ERROR=1, WARNING=2, INFO=3, RUNTIME_FAILURE=4
    error_code: str
    source_module: str
    affected_paths: tuple[str, ...]
    message: str
```

**From EngineeringMessage:** map fields directly.

**From RunFailure:** `diagnostic_class_rank = 4`, `error_code` = failure code, `source_module = ""`, `affected_paths = ()`, `message` = failure message.

**From pure duty infeasibility (SUCCEEDED rating, not meeting duty):** `diagnostic_class_rank = 0` (BLOCKER), `error_code = "required_duty_not_met"`, `source_module = "sizing"`, `affected_paths = ()`, `message = "Rated duty {rated} W < required duty {required} W even with effective tolerance {tol} W"`.

### 12.5 Primary Diagnostic Selection

When multiple diagnostics exist for a candidate, select by:

1. `diagnostic_class_rank` ascending (lower = more severe)
2. `error_code` string ascending
3. `source_module` string ascending
4. `affected_paths` canonical tuple ascending
5. `message` string ascending

Must not rely on insertion order.

---

## 13. Rating Evidenc

### 13.1 VerifiedRatingEvidenceSnapshot

Constructed only when:

```text
rating.verify_hash() is True
rating.verify_provenance() is True
```

Fields:

```text
rating_status
heat_duty_w
hot_outlet_temperature_k
cold_outlet_temperature_k
area_inner_m2
area_outer_m2
UA_w_k
LMTD_k
energy_residual_w
ua_lmtd_residual_w
tube_inlet_density_kg_m3
annulus_inlet_density_kg_m3
tube_flow_area_m2
annulus_flow_area_m2
warnings
blockers
failure
provider_identity
selected_correlation_identities
rating_result_hash
rating_provenance_digest
rating_verify_hash_result
rating_verify_provenance_result
rating_request_identity_digest
rating_execution_context_identity
```

### 13.2 InvalidRatingEvidenceRecord

Constructed when `verify_hash()` or `verify_provenance()` fails. Contains:

```text
candidate_id
rating_status
claimed_result_hash
claimed_provenance_digest
verify_hash_result
verify_provenance_result
rating_request_identity_digest
provider_identity
failure_reason
```

Must **not** copy or expose trusted thermal metrics from an unverified `RatingResult`.

### 13.3 Sizing-Level Fail-Closed

If any evaluated candidate returns `INTEGRITY_INVALID` (hash or provenance verification fails), the entire sizing run is **BLOCKED**:

```text
status = BLOCKED
selected_candidate = None
top_candidates = ()
blocker = RATING_RESULT_INTEGRITY_FAILED
```

Previously evaluated (trusted) candidates remain in audit output, marked as `partial_audit = True`. No candidate may be selected while any candidate has unverified evidence.

### 13.4 Replay

The complete TASK-008 rating request is reconstructable from frozen sizing evidence. Replay is deterministic only when the same software version, property-provider implementation, provider configuration, source data, and execution policy are available.

---

## 14. Sizing Request Template

### 14.1 SizingRequestIdentity fields

```text
hot_fluid: FluidIdentifier
cold_fluid: FluidIdentifier
hot_inlet_temperature_k: float
cold_inlet_temperature_k: float
hot_inlet_pressure_pa: float
cold_inlet_pressure_pa: float
hot_mass_flow_kg_s: float
cold_mass_flow_kg_s: float
flow_arrangement: FlowArrangement
tube_in_hot: bool
tube_boundary_condition: ThermalBoundaryCondition
annulus_boundary_condition: ThermalBoundaryCondition
minimum_terminal_delta_t: float
required_duty_w: float
duty_absolute_tolerance_w: float
duty_relative_tolerance: float
optimization_objective: OptimizationObjective
top_n: int
request_raw_combination_cap: int | None
catalog_snapshot_identities: tuple[CatalogSnapshotRef, ...]
minimum_effective_length_m: float | None
maximum_effective_length_m: float | None
```

Plus rating execution template:

```text
rating_solver_absolute_residual_w: float
rating_solver_relative_residual_fraction: float
rating_solver_bracket_temperature_tolerance_k: float
rating_solver_max_iterations: int
property_provider_identity: str
property_provider_name: str
property_provider_version: str
property_provider_git_revision: str
property_provider_reference_state_policy: str
property_provider_configuration_fingerprint: str
rating_software_version: str
execution_context_policy_version: str
```

### 14.2 Exact TASK-008 Callable

```text
rate_double_pipe(
    geometry=DoublePipeGeometry,
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
    minimum_terminal_delta_t=float,
    tube_boundary_condition=ThermalBoundaryCondition,
    annulus_boundary_condition=ThermalBoundaryCondition,
)
```

Provider is caller-injected. Solver parameters are taken from the request template, not from defaults.

### 14.3 Per-Candidate CalculationContext

Derived deterministically from sizing run identity + `source_qualified_candidate_id` via UUID5 with a fixed namespace UUID. No random UUIDs.

### 14.4 Rating Request Identity

Each TASK-008 rating request identity includes:

- full geometry (from assembly option)
- all required_duty_w-derived solver inputs
- fouling (from assembly option)
- boundary conditions, flow arrangement, side assignment
- solver parameters
- provider identity fingerprint
- execution context identity

---

## 15. Provenance Node Mapping

### 15.1 Node Type Mapping

| Business Concept | ProvenanceNodeType | Label |
|-----------------|-------------------|-------|
| SIZING_RUN | `CALCULATION_RUN` | `"sizing_run_{identity}"` |
| SIZING_OPTIMIZER | `OPTIMIZER` | `"sizing_optimizer"` |
| CATALOG_SNAPSHOT | `INTERMEDIATE` | `"catalog_snapshot_{catalog_id}"` |
| MANUFACTURABLE_CANDIDATE | `INTERMEDIATE` | `"candidate_{id}"` |
| TASK008_RATING_RESULT | `RESULT` | `"rating_result_{hash}"` |
| SIZING_RESULT | `RESULT` | `"sizing_result"` |
| WARNING | `WARNING` | (per message) |
| BLOCKER | `BLOCKER` | (per message) |
| ROOT | `CASE_REVISION` or `EXTERNAL` | as appropriate |

### 15.2 Required Edges

| From | To | Label |
|------|----|-------|
| ROOT | SIZING_RUN | `"initiates"` |
| SIZING_RUN | CATALOG_SNAPSHOT | `"consumes"` |
| CATALOG_SNAPSHOT | CANDIDATE | `"generates"` |
| SIZING_RUN | OPTIMIZER | `"executes"` |
| CANDIDATE | TASK008_RATING_RESULT | `"rated_as"` |
| TASK008_RATING_RESULT | OPTIMIZER | `"evaluated_by"` |
| OPTIMIZER | SIZING_RESULT | `"produces"` |
| WARNING | SIZING_RESULT | `"annotates"` |
| BLOCKER | SIZING_RESULT | `"blocks"` |

### 15.3 Deterministic Node IDs

All node IDs are UUID5 with a fixed namespace UUID. The name payload is a canonical string over the node identity fields.

`verify_provenance()` checks:
- required node multiplicity (exactly one CALCULATION_RUN, at least one RESULT, etc.)
- required edge existence
- DAG consistency
- payload hash integrity per node
- edge hash integrity

---

## 16. Frozen ErrorCode Values

### 16.1 Existing Reused Codes

```text
INPUT_MISSING        — missing required field in SizingRequest
INPUT_INCONSISTENT   — conflicting fields in SizingRequest
UNIT_INVALID         — unit/quantity contract violation
HASH_MISMATCH        — catalog hash or request hash mismatch
PROVENANCE_INCOMPLETE — provenance graph missing required nodes/edges
UNSUPPORTED_SERVICE  — unsupported feature requested
CALCULATION_BLOCKED  — generic calculation blocked
CORRELATION_IMPLEMENTATION_UNAVAILABLE — propagated from C4, unchanged
```

### 16.2 New TASK-009 ErrorCode Strings

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
```

Total: 13 new codes. No synonymous duplicates.

---

## 17. Velocity Envelope

Deferred / out of scope for TASK-009 v0.1. Not included in feasibility or ranking. If enabled in a future version, may only use TASK-008's verified inlet-state snapshot density; must not call `PropertyProvider` independently.

---

## 18. Pressure-Drop Boundary

Pressure drop is out of scope for TASK-009 v0.1. No pressure-drop limit, correlation, score, or optimization term may be added until a separate reviewed contract is approved.

---

## 19. Terminology

TASK-009 does not claim organizational source approval. Replace the following imprecise terms:

| Imprecise | Precise |
|-----------|---------|
| "approved catalog snapshots" | "caller-supplied, structurally validated, hash-verified catalog snapshots" |
| "approved candidates" | "structurally valid, hash-verified candidates" |
| "organization-approved master catalogs" | reserved for TASK-016 |

---

## 20. Required Test Matrix

### 20.1 Catalog and Identity

1. Catalog canonical hash — deterministic across serialization order
2. Catalog hash mismatch → run BLOCKED before any option processed
3. Mixed valid/invalid option → entire run BLOCKED (fail-closed)
4. Catalog insertion-order independence
5. Assembly-option insertion-order independence
6. Explicit-length insertion-order independence
7. Explicit lengths Decimal canonicalization and deduplication
8. Grid `INCLUDE_MAX_IF_ALIGNED` aligned endpoint
9. Grid non-aligned endpoint (excluded regardless of policy)
10. Grid `EXCLUDE_MAX`
11. Increment smaller than quantization quantum → CATALOG_INVALID
12. Duplicate values after quantization → deduplicated
13. Request `minimum_effective_length_m` / `maximum_effective_length_m` intersection
14. Empty option after intersection → contributes 0 to raw count
15. All options empty → `NO_MANUFACTURABLE_CANDIDATE`
16. `raw_combination_count` computed before candidate materialization (Decimal arithmetic, no oversized list)
17. Hard cap (`HARD_RAW_COMBINATION_CAP`) blocks before materialization and rating
18. Request cap blocks before materialization and rating
19. Exact `raw_combination_count`, `unique_candidate_count`, `evaluated_candidate_count`
20. `SourceQualifiedCandidateIdentity` deduplication — identical geometry from different catalog sources remains distinct
21. Candidate identity stability across different operating conditions (identical geometry/different request → same source-qualified ID)
22. Candidate evaluation identity changes with request changes

### 20.2 Feasibility and Ranking

23. `duty_absolute_tolerance_w` applied correctly
24. `duty_relative_tolerance` applied correctly
25. `max(abs, rel)` tolerance accepted
26. Tolerance-accepted shortfall ranks below actual target satisfaction
27. `MINIMUM_OUTER_HEAT_TRANSFER_AREA` ranking
28. `MINIMUM_EFFECTIVE_LENGTH` ranking
29. Objectives select different candidates in a Golden case
30. Exact feasible tie resolved by canonical candidate ID
31. Top-N = 1
32. Top-N equals feasible count
33. Top-N exceeds feasible count → warning, no block
34. No feasible candidate → BLOCKED (not FAILED)

### 20.3 Integrity and Evidence

35. Mixed SUCCEEDED/BLOCKED/FAILED candidates audited
36. Rating hash failure → entire run BLOCKED
37. Rating provenance failure → entire run BLOCKED
38. Invalid rating evidence does not expose trusted thermal metrics
39. C4 (`CORRELATION_IMPLEMENTATION_UNAVAILABLE`) propagated unchanged

### 20.4 Non-Feasible Diagnostics

40. Deterministic primary diagnostic from multiple EngineeringMessage blockers
41. RunFailure diagnostic normalization
42. Pure duty-infeasible diagnostic (`REQUIRED_DUTY_NOT_MET`)
43. Non-feasible deterministic ordering

### 20.5 Provenance

44. Exact provenance node type mapping
45. Required provenance edges
46. Graph node tamper detection
47. Graph edge tamper detection

### 20.6 Hash and Tamper Detection

48. Ranking tamper detection
49. Catalog tamper detection
50. Candidate tamper detection
51. Selected-candidate tamper detection
52. Solver parameter change changes identity digest
53. Fouling change changes identity digest
54. Provider identity/configuration change changes identity digest
55. Repeated-run determinism (same inputs → same outputs)
56. JSON round-trip preserves all fields, hash, and provenance

### 20.7 Golden Cases

57. Independent smallest-outer-area Golden case
58. Independent shortest-effective-length Golden case

### 20.8 Documentation Alignment

59. Issue #23 references canonical task card and frozen commit SHA

### 20.9 Quality Gates

60. Ruff, format check, mypy, pytest with coverage, and pip-audit pass on Python 3.11 and 3.12

---

## 21. Exclusions

- pressure-drop formulas or constraints
- continuous nonlinear optimization
- stochastic, genetic, Bayesian, or ML optimization
- velocity envelope constraints (deferred)
- cost and life-cycle economics
- material selection
- mechanical strength or code compliance
- API endpoints, reports, UI
- C4 numerical implementation
- two-phase, shell-and-tube, plate, air-cooled exchanger sizing
- independent Cartesian product of inner-tube and outer-pipe options

---

## 22. Delivery Sequence

1. Complete Round 3 Engineering Design Review.
2. Only after review passes: create implementation branch and Draft PR.
3. Implement catalog and identity models before optimizer.
4. Implement deterministic candidate generation and deduplication.
5. Integrate TASK-008 `rate_double_pipe()` evaluation.
6. Implement feasibility and ranking.
7. Implement result hash, provenance, JSON round-trip, and tamper verification.
8. Add direct, Golden, and integration tests.
9. Keep PR Draft through engineering review and CI pass.

---

## 23. Acceptance Criteria

- [ ] Round 3 Design Review passes before implementation starts
- [ ] Only caller-supplied, structurally validated, hash-verified catalog candidates are generated
- [ ] `SourceQualifiedCandidateIdentity` is the deduplication key
- [ ] TASK-008 `rate_double_pipe()` is the sole thermal evaluator
- [ ] Candidate generation and ranking are insertion-order independent
- [ ] Objective is explicit and typed; no weighted composite score
- [ ] `NO_FEASIBLE_CANDIDATE` is `BLOCKED`, not `FAILED`
- [ ] Top-N contains feasible candidates only; truncation adds a warning
- [ ] Non-feasible ordering, diagnostic key, and primary message selection are deterministic
- [ ] `VerifiedRatingEvidenceSnapshot` vs `InvalidRatingEvidenceRecord` are distinct types
- [ ] Single integrity-invalid candidate blocks the entire run
- [ ] Provenance node types map to existing shared enums with labelled metadata
- [ ] Exact 13 TASK-009 ErrorCode strings are used; no synonymous duplicates
- [ ] No pressure-drop or velocity constraint is introduced
- [ ] Blocked and failed candidates remain auditable
- [ ] Candidate and result hashes are deterministic
- [ ] Provenance topology and payload integrity are complete
- [ ] JSON round-trip and tamper detection pass
- [ ] Required 57 test scenarios + 2 Golden cases + 1 documentation alignment are covered
- [ ] Ruff, format check, mypy, pytest with coverage, and pip-audit pass on Python 3.11 and 3.12
- [ ] Engineering design review passes before Ready or merge
