# TASK-009 — Manufacturable sizing and deterministic candidate optimization

**Status:** BLOCKED — Engineering design review changes required
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-005, TASK-008
**GitHub Issue:** #23
**Implementation branch:** Not created
**Draft PR:** Not created
**Production implementation:** Not started

TASK-009 returns to READY only after Round 4 Engineering Design Review passes.

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
| 3 | 4797267787 | CHANGES REQUIRED |

---

## 4. Data Model

### 4.1 Container Hierarchy

```text
SizingRequest
  └── CatalogSnapshotRef[]
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

### 4.3 CompleteDoublePipeCatalogSnapshot

```text
catalog_id: str
catalog_version: str
source_identity: str
schema_version: str
assembly_options: tuple[CompleteDoublePipeAssemblyOption, ...]
catalog_content_hash: str
```

`catalog_content_hash` is `sha256:<64 lowercase hex>`. Computed over the canonical JSON payload of all fields **except itself**. Payload field order: `catalog_id`, `catalog_version`, `source_identity`, `schema_version`, `assembly_options`. Assembly options sorted by `assembly_option_id` ASCII ascending. JSON serialized via `canonical_json()` — sorted keys, no whitespace, no trailing newline.

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

Fouling resistances are physical design properties of the assembly option. They enter `SourceQualifiedCandidateIdentity` and the TASK-008 `RatingRequestIdentity` (via geometry).

`manufacturing_metadata`: unordered at input, stored as sorted tuple of `(key, value)` pairs — keys unique, keys ASCII ascending, values str. Deep-frozen on construction.

### 4.5 LengthSource

Exactly one of:

**Mode A — Explicit Lengths**

```text
allowed_effective_lengths_m: tuple[float, ...]
```

Each value finite and > 0. All values canonicalized through the unified power-of-10 length quantum, sorted ascending, deduplicated. Empty after canonicalization → `CATALOG_INVALID`.

**Mode B — Length Grid**

```text
LengthGridSpec:
  minimum_length_m: float
  maximum_length_m: float
  increment_m: float
  endpoint_policy: LengthEndpointPolicy
  length_quantum_m: str
```

No assembly option may provide both modes.

---

## 5. Length Quantum and Canonicalization

### 5.1 Power-of-10 Quantum

All lengths are canonicalized through a single **power-of-10 quantum** per length source.

```text
length_quantum_m: str  — must be constructable as Decimal and equal to 1E−N for integer N >= 0
```

Valid examples: `"1"`, `"0.1"`, `"0.01"`, `"0.001"`. Invalid: `"0.025"`, `"0.333"`.

Validation:

```python
from decimal import Decimal
quantum = Decimal(length_quantum_m)
if not quantum.is_finite() or quantum <= 0:
    raise Invalid
normalized = quantum.normalize()
digits = normalized.as_tuple().digits
# A power-of-10 Decimal has exactly one digit (1) after normalize
if digits != (1,):
    raise Invalid
```

### 5.2 Integer Tick Conversion

```python
def to_tick(value_m: float, quantum: Decimal) -> int:
    raw = Decimal(str(value_m))
    if not raw.is_finite() or raw <= 0:
        raise InvalidLength()
    qty = raw.quantize(quantum, rounding=ROUND_HALF_EVEN)
    tick = int((qty / quantum).to_integral_exact())
    return tick

def from_tick(tick: int, quantum: Decimal) -> Decimal:
    return Decimal(tick) * quantum
```

Length output for identity and hash uses the **canonical Decimal string**:

```text
effective_length_m_canonical: str  — e.g. "12.350"
```

### 5.3 Explicit Lengths Canonicalization

```python
ticks = sorted({to_tick(v, quantum) for v in allowed_effective_lengths_m})
canonical_lengths = [str(from_tick(t, quantum)) for t in ticks]
if not canonical_lengths:
    raise CatalogInvalid()
```

`raw_combination_count` uses the deduplicated canonical length set for each option, intersected with request bounds.

---

## 6. Length Grid Algorithm

### 6.1 Validation

```python
from decimal import Decimal, ROUND_HALF_EVEN

quantum = Decimal(length_quantum_m)
lo_tick = to_tick(minimum_length_m, quantum)
hi_tick = to_tick(maximum_length_m, quantum)
step_tick = to_tick(increment_m, quantum)

assert lo_tick > 0
assert hi_tick >= lo_tick
assert step_tick > 0
# increment_m < length_quantum_m causes step_tick == 0 → CatalogInvalid
```

### 6.2 Count-Only Algorithm (Before Materialization)

```python
delta = hi_tick - lo_tick
quotient, remainder = divmod(delta, step_tick)
```

#### INCLUDE_MAX_IF_ALIGNED

```python
catalog_count = delta // step_tick + 1
# same as: quotient + (1 if remainder != 0 or True else ...)
# Corrected: all points lo + i*step <= hi are included.
# The aligned hi is included if it lands exactly.
```

#### EXCLUDE_MAX

```python
catalog_count = delta // step_tick + 1
if remainder == 0:
    catalog_count -= 1
# When minimum_length_m == maximum_length_m, delta=0, quotient=0, remainder=0
# catalog_count = 1 - 1 = 0
```

No value generated exceeds `hi_tick`.

### 6.3 Materialization (After Cap Passes)

```python
ticks = [lo_tick + step_tick * i for i in range(catalog_count)]
canonical_lengths = [str(from_tick(t, quantum)) for t in ticks]
```

### 6.4 Request Bounds Intersection (Count-Only)

```python
request_min_tick: int | None = None if minimum_effective_length_m is None
    else to_tick(minimum_effective_length_m, quantum)
request_max_tick: int | None = None if maximum_effective_length_m is None
    else to_tick(maximum_effective_length_m, quantum)
```

Closed interval: `request_min_tick <= tick <= request_max_tick`.

```python
first_idx = 0
if request_min_tick is not None:
    # ceil division: smallest i such that lo + i*step >= request_min_tick
    first_idx = max(first_idx, -((- (request_min_tick - lo_tick)) // step_tick))

last_idx = catalog_count - 1
if request_max_tick is not None:
    # floor division: largest i such that lo + i*step <= request_max_tick
    last_idx = min(last_idx, (request_max_tick - lo_tick) // step_tick)

intersection_count = max(0, last_idx - first_idx + 1)
```

An option with `intersection_count == 0` contributes 0 to `raw_combination_count`. If all options yield 0, return `NO_MANUFACTURABLE_CANDIDATE`.

---

## 7. Pre-Evaluation Pipeline

### 7.1 Pipeline Order

```text
 1. SizingRequest schema validation
 2. Catalog schema validation
 3. Duplicate assembly_option_id validation (before hash verification)
 4. Duplicate catalog_id + catalog_version references validation
 5. Catalog canonical hash verification
 6. Assembly option validation
 7. Length source validation and count-only request intersection
 8. raw_combination_count summation
 9. Hard/request raw-cap check
10. Length materialization (only if cap passes)
11. Candidate identity materialization
12. Deduplication by SourceQualifiedCandidateIdentity
13. TASK-008 evaluation (in canonical order)
```

### 7.2 Sequence Constraints

- Cap check (step 9) occurs **before** any length tuple, candidate object, or TASK-008 call.
- `raw_combination_count` is computed by integer arithmetic only — no oversized list allocation.
- Cap exceeded: `status=BLOCKED`, `unique=0`, `evaluated=0`, `selected=None`, `top_candidates=()`.

### 7.3 Raw Combination Count

```text
raw_combination_count = sum over all eligible assembly options of
    intersection_count (after request bounds filtering,
    on canonicalized, deduplicated catalog lengths)
```

### 7.4 Cap

```text
HARD_RAW_COMBINATION_CAP = 10_000
request_raw_combination_cap (optional; if set, must be int, 1..HARD_RAW_COMBINATION_CAP)
effective_cap = min(request_raw_combination_cap, HARD_RAW_COMBINATION_CAP)
```

---

## 8. Candidate Identity

### 8.1 PhysicalCandidateIdentity

Pure geometry + length — no catalog source.

```text
inner_tube_inner_diameter_m: float
inner_tube_outer_diameter_m: float
outer_pipe_inner_diameter_m: float
effective_length_m_canonical: str
wall_thermal_conductivity_w_m_k: float
inner_surface_roughness_m: float
annulus_surface_roughness_m: float
inner_fouling_resistance_m2k_w: float
outer_fouling_resistance_m2k_w: float
```

Two options with identical geometry and length (after canonicalization) produce the same `PhysicalCandidateIdentity`, regardless of catalog source.

### 8.2 SourceQualifiedCandidateIdentity

```text
physical_candidate_identity_digest: str
catalog_id: str
catalog_version: str
catalog_content_hash: str
assembly_option_id: str
manufacturing_option_identity: str
```

### 8.3 Deduplication

`unique_candidate_count` is after deduplication by `SourceQualifiedCandidateIdentity`. Different catalog source, version, content hash, `assembly_option_id`, or manufacturing option yields distinct candidates, even if geometry is identical.

### 8.4 Canonical Evaluation Order

After deduplication, candidates are evaluated in ascending `source_qualified_candidate_id` (string, ASCII). This order determines:

- `evaluated_candidate_count`
- TASK-008 call sequence
- property call trace order
- partial audit cutoff point
- integrity stop position
- result hash input order
- provenance topology

---

## 9. Rating Entry Point

### 9.1 Exact Callable

```python
rate_double_pipe(
    geometry=DoublePipeGeometry(
        inner_tube_inner_diameter_m=...,
        inner_tube_outer_diameter_m=...,
        outer_pipe_inner_diameter_m=...,
        effective_length_m=float(from_tick(tick, quantum)),
        wall_thermal_conductivity_w_m_k=...,
        inner_surface_roughness_m=...,
        annulus_surface_roughness_m=...,
        inner_fouling_resistance_m2k_w=...,
        outer_fouling_resistance_m2k_w=...,
    ),
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
    solver_params=SolverParams(...),
    context=CalculationContext(...),
    minimum_terminal_delta_t=float,
    tube_boundary_condition=ThermalBoundaryCondition,
    annulus_boundary_condition=ThermalBoundaryCondition,
)
```

Fouling enters via geometry (not overridden by any service layer). TASK-009 calls the pure function directly, not `DoublePipeRatingService.rate()`.

### 9.2 SolverParams

Mapped directly from request fields:

```python
SolverParams(
    temperature_tolerance=rating_solver_temperature_tolerance_k,
    energy_tolerance=rating_solver_energy_tolerance_fraction,
    max_iterations=rating_solver_max_iterations,
    bracket_step_k=rating_solver_bracket_step_k,
    max_bracket_span_k=rating_solver_max_bracket_span_k,
    absolute_energy_tolerance_w=rating_solver_absolute_energy_tolerance_w,
    near_zero_duty_threshold_w=rating_solver_near_zero_duty_threshold_w,
)
```

All solver params are uniform across every candidate in a single sizing run and enter `RatingRequestIdentity`.

### 9.3 Per-Candidate CalculationContext

Derived deterministically via UUID5:

```python
TASK009_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # example; frozen once
name = f"sizing-eval:{sizing_request_identity_digest}:{source_qualified_candidate_id}"
context_id = uuid5(TASK009_NAMESPACE, name)
```

No random UUIDs.

---

## 10. Identity Boundaries

### 10.1 RatingRequestIdentity (TASK-008)

Contains only:

- fluids (hot/cold identifiers)
- flow rates (hot/cold mass flow)
- inlet temperatures and pressures
- `DoublePipeGeometry` (including fouling)
- `tube_in_hot`
- `FlowArrangement`
- `SolverParams` (all 7 fields)
- `minimum_terminal_delta_t`
- `tube_boundary_condition`
- `annulus_boundary_condition`

Does **not** contain: provider identity, execution context, required duty, sizing objective, top-N, tolerances.

### 10.2 ProviderIdentitySnapshot

```text
name: str
version: str
git_revision: str
reference_state_policy: str
configuration_fingerprint: str
cache_policy_version: str
```

Captured from the first successful TASK-008 call (or caller-pre-declared).

### 10.3 ExecutionContextSnapshot

```text
request_id: str
design_case_revision_id: str
calculation_run_id: str
```

### 10.4 CandidateEvaluationIdentity

```text
source_qualified_candidate_identity_digest: str
sizing_request_identity_digest: str
rating_request_identity_digest: str
provider_identity_digest: str
execution_context_identity_digest: str
rating_result_hash: str
rating_provenance_digest: str
```

All fields are `sha256:<64 hex>` digests. Canonical payload: fields in declaration order, each on its own line, key=value, no extra whitespace.

### 10.5 SizingRequestIdentity

```text
hot_fluid_name: str
cold_fluid_name: str
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
rating_solver_temperature_tolerance_k: float
rating_solver_energy_tolerance_fraction: float
rating_solver_max_iterations: int
rating_solver_bracket_step_k: float
rating_solver_max_bracket_span_k: float
rating_solver_absolute_energy_tolerance_w: float
rating_solver_near_zero_duty_threshold_w: float
property_provider_name: str
property_provider_version: str
property_provider_git_revision: str
property_provider_reference_state_policy: str
property_provider_cache_policy_version: str
rating_software_version: str
execution_context_policy_version: str
```

`required_duty_w` is a sizing feasibility input only. It does **not** enter TASK-008 `RatingRequestIdentity` and must not derive `SolverParams`.

---

## 11. Request Validation

| Field | Rule |
|-------|------|
| `required_duty_w` | finite, > 0 |
| `minimum_effective_length_m` | None or finite, > 0 |
| `maximum_effective_length_m` | None or finite, > 0; if both present: min <= max |
| `top_n` | `type(value) is int`, `value >= 1` — reject `bool` (Python `bool` is a subclass of `int`) |
| `request_raw_combination_cap` | None → defaults to `HARD_RAW_COMBINATION_CAP`; if set, `type(value) is int`, `1..HARD_RAW_COMBINATION_CAP` — reject `bool` |
| Duplicate catalog refs | No two `CatalogSnapshotRef` may share `(catalog_id, catalog_version)` |
| Provider identity | Caller-declared identity fields must match actual `ProviderIdentitySnapshot` from first TASK-008 call. Mismatch → BLOCKED with `PROPERTY_PROVIDER_IDENTITY_MISMATCH` |

---

## 12. Duty Feasibility

### 12.1 Tolerance Fields

```text
duty_absolute_tolerance_w: float  (finite, >= 0)
duty_relative_tolerance: float    (finite, >= 0)
```

### 12.2 Effective Tolerance

```text
effective_duty_tolerance_w = max(
    duty_absolute_tolerance_w,
    duty_relative_tolerance * max(required_duty_w, 1.0)
)
```

### 12.3 Feasibility Condition

```text
rated_duty_w + effective_duty_tolerance_w >= required_duty_w
```

### 12.4 Derived Fields

```text
duty_margin_w = rated_duty_w - required_duty_w
duty_shortfall_w = max(-duty_margin_w, 0.0)
duty_overshoot_w = max(duty_margin_w, 0.0)
meets_target_without_tolerance = rated_duty_w >= required_duty_w
target_satisfaction_rank = 0 if meets_target_without_tolerance else 1
```

---

## 13. Optimization Objectives

### 13.1 Enum

```text
class OptimizationObjective(StrEnum):
    MINIMUM_OUTER_HEAT_TRANSFER_AREA = "minimum_outer_heat_transfer_area"
    MINIMUM_EFFECTIVE_LENGTH = "minimum_effective_length"
```

Area objective uses TASK-008 `RatingResult.area_outer_m2` (consistent with frozen inner-tube outer-surface U basis). May **not** use `area_inner_m2`, `UA_w_k`, `U_w_m2_k`, custom equivalent area, or implicit area basis. Area basis enters request identity, result identity, and provenance.

### 13.2 Feasible Ranking (Target Satisfaction First)

**Actual target satisfaction dominates objective value.** A candidate meeting `required_duty_w` without tolerance always ranks above one accepted only by tolerance, regardless of objective metric.

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

All ascending. Only feasible candidates participate. No weighted composite score. `selected_candidate == top_candidates[0]`. Identical engineering metrics resolved by canonical candidate ID ascending. Input insertion order does not affect ranking.

---

## 14. SizingStatus and Invariants

```text
class SizingStatus(StrEnum):
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"
```

### 14.1 SUCCEEDED

- at least one feasible candidate
- `selected_candidate is not None` and `selected_candidate.feasible is True`
- `top_candidates` non-empty
- `blockers` empty
- `failure` empty
- `verify_hash()` True
- `verify_provenance()` True

### 14.2 BLOCKED

Deterministic non-executability or no solution. Includes: invalid request, invalid catalog, hash mismatch, cap exceeded, no manufacturable candidate, no feasible candidate, unsupported constraint, rating integrity failure, provider identity mismatch.

- at least one blocker
- `selected_candidate is None`
- `failure` empty
- result hash and provenance remain valid

`NO_FEASIBLE_CANDIDATE` → BLOCKED.

### 14.3 FAILED

Unexpected runtime failures only.

- `failure` is not None
- `selected_candidate is None`
- result hash and provenance remain valid

---

## 15. Top-N Contract

```text
top_n: int  (>= 1)
```

`top_candidates` contains only feasible candidates, ranked by objective-specific sort key (§13.2).

- `top_n <= feasible_candidate_count`: return exactly top `top_n`
- `top_n > feasible_candidate_count > 0`: return all feasible candidates, add `TOP_N_REDUCED_TO_FEASIBLE_COUNT` warning
- `feasible_candidate_count == 0`: `status = BLOCKED`, `selected_candidate = None`, `top_candidates = ()`, `blocker = NO_FEASIBLE_CANDIDATE`

---

## 16. Non-Feasible Candidate Ordering

Non-feasible candidates appear in audit output only, not in `top_candidates`.

### 16.1 Feasibility Status Severity

```text
INFEASIBLE < RATING_BLOCKED < RATING_FAILED < INTEGRITY_INVALID
```

### 16.2 Rating Status Rank

```text
SUCCEEDED < BLOCKED < FAILED
```

### 16.3 Full Non-Feasible Sort Key

```text
(
    feasibility_status_rank,
    rating_status_rank,
    primary_diagnostic.diagnostic_class_rank,
    primary_diagnostic.error_code,
    primary_diagnostic.source_module,
    primary_diagnostic.affected_paths,
    primary_diagnostic.message,
    source_qualified_candidate_id,
)
```

### 16.4 CandidateDiagnosticKey

```text
class CandidateDiagnosticKey:
    diagnostic_class_rank: int     # BLOCKER=0, ERROR=1, WARNING=2, INFO=3, RUNTIME_FAILURE=4
    error_code: str
    source_module: str
    affected_paths: tuple[str, ...]
    message: str
```

Sentinel when none present: `(999, "", "", (), "")`.

**From EngineeringMessage:** map directly.

**From RunFailure:** `diagnostic_class_rank=4`, `error_code` = failure code, `source_module=""`, `affected_paths=()`, `message` = failure message.

**From pure duty infeasibility (SUCCEEDED rating, not meeting duty):** `diagnostic_class_rank=0`, `error_code="required_duty_not_met"`, `source_module="sizing"`, `affected_paths=()`, `message` = formatted string.

### 16.5 Primary Diagnostic Selection

When multiple diagnostics exist, select by (ascending):

1. `diagnostic_class_rank`
2. `error_code` string
3. `source_module` string
4. `affected_paths` canonical tuple
5. `message` string

Must not rely on insertion order.

---

## 17. Rating Evidence

### 17.1 VerifiedRatingEvidenceSnapshot

Constructed only when `rating.verify_hash() is True and rating.verify_provenance() is True`.

```text
rating_status: str
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
tube_flow_area_m2: float        (derived deterministically from candidate geometry)
annulus_flow_area_m2: float     (derived deterministically from candidate geometry)
warnings: tuple[EngineeringMessage, ...]
blockers: tuple[EngineeringMessage, ...]
failure: RunFailure | None
provider_identity: ProviderIdentitySnapshot
selected_correlation_identities: tuple[str, ...]
rating_result_hash: str
rating_provenance_digest: str
rating_verify_hash_result: bool
rating_verify_provenance_result: bool
rating_request_identity_digest: str
rating_execution_context_identity: str
```

Heat duty and temperatures may be `None` for verified BLOCKED/FAILED rating results. Flow areas are geometry-derived and enter the evidence hash.

### 17.2 InvalidRatingEvidenceRecord

Constructed when `verify_hash()` or `verify_provenance()` fails.

```text
candidate_id: str
rating_status: str
claimed_result_hash: str
claimed_provenance_digest: str
verify_hash_result: bool
verify_provenance_result: bool
rating_request_identity_digest: str
provider_identity: ProviderIdentitySnapshot
failure_reason: str
```

Must **not** copy or expose trusted thermal metrics from an unverified `RatingResult`.

### 17.3 Integrity-Failure Policy

Candidates are evaluated in canonical order (§8.4). If any candidate's TASK-008 `verify_hash()` or `verify_provenance()` fails:

1. Record `InvalidRatingEvidenceRecord` for this candidate
2. This candidate increments `evaluated_candidate_count`
3. **Stop immediately** — no remaining candidates are evaluated
4. `status = BLOCKED`, `termination_reason = "rating_result_integrity_failed"`
5. `selected_candidate = None`, `top_candidates = ()`
6. `partial_audit = True`
7. Previously evaluated (trusted) candidates remain in audit with `partial_audit` field

`remaining_unevaluated_candidate_count = unique_candidate_count - evaluated_candidate_count`.

If `verify_hash()` or `verify_provenance()` themselves raise an exception (not return False), treat as `FAILED` (runtime error), not integrity invalid.

### 17.4 Replay

The complete TASK-008 rating request is reconstructable from frozen sizing evidence. Replay is deterministic only when the same software version, property-provider implementation, provider configuration, source data, and execution policy are available.

---

## 18. Provenance

### 18.1 Node Type Mapping

| Business Concept | ProvenanceNodeType | Label |
|-----------------|-------------------|-------|
| SIZING_RUN | `CALCULATION_RUN` | `"sizing_run_{identity_digest}"` |
| SIZING_OPTIMIZER | `OPTIMIZER` | `"sizing_optimizer"` |
| CATALOG_SNAPSHOT | `INTERMEDIATE` | `"catalog_{catalog_id}"` |
| MANUFACTURABLE_CANDIDATE | `INTERMEDIATE` | `"candidate_{candidate_id}"` |
| TASK008_RATING_RESULT | `RESULT` | `"rating_{result_hash}"` |
| SIZING_RESULT | `RESULT` | `"sizing_result"` |
| WARNING | `WARNING` | per message |
| BLOCKER | `BLOCKER` | per message |
| ROOT | `CASE_REVISION` or `EXTERNAL` | as appropriate |

### 18.2 UUID5 Namespace

```python
TASK009_PROVENANCE_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
```

### 18.3 UUID5 Name Payload Formats

```text
sizing-run:{sizing_request_identity_digest}
catalog:{catalog_id}:{catalog_version}:{catalog_content_hash}
candidate:{source_qualified_candidate_id}
rating-result:{rating_result_hash}
optimizer:{sizing_request_identity_digest}
sizing-result:{result_hash}
warning:{error_code}:{canonical_affected_paths}:{message_hash}
blocker:{error_code}:{canonical_affected_paths}:{message_hash}
```

### 18.4 Status-Specific Topologies

#### Invalid Request

```text
ROOT -> SIZING_RUN       "initiates"
BLOCKER -> SIZING_RESULT "blocks"
SIZING_RUN -> SIZING_RESULT "produces"
```

No catalog, candidate, or rating nodes required.

#### Invalid Catalog / Hash Mismatch

```text
ROOT -> SIZING_RUN          "initiates"
SIZING_RUN -> CATALOG       "consumes"
BLOCKER -> SIZING_RESULT    "blocks"
SIZING_RUN -> SIZING_RESULT "produces"
```

#### Cap Exceeded / No Manufacturable Candidate

May include catalog nodes. No candidate or rating nodes required.

#### Evaluated, No Feasible Candidate

Full topology: catalog, candidate, rating result, optimizer, sizing result, blocker.

#### Integrity Invalid

Verified rating result nodes + invalid evidence node + blocker + partial audit marker.

#### SUCCEEDED

Full topology (§18.5).

#### FAILED

May include partial catalog/candidate/rating nodes. Failure node mapped to `BLOCKER` or `WARNING` as appropriate.

### 18.5 Required Edges (Full Topology)

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

### 18.6 Two-Stage Provenance Construction

1. Build core provenance (all nodes except SIZING_RESULT and associated WARNING/BLOCKER)
2. Compute `core_provenance_digest`
3. Build `SizingResultIdentity` payload (includes `core_provenance_digest`)
4. Compute `result_hash` (does **not** include final provenance digest — avoids circular dependency)
5. Add SIZING_RESULT node, associated WARNING and BLOCKER nodes
6. Build final provenance graph
7. Compute `final_provenance_digest`

### 18.7 Edge Tamper Detection

`ProvenanceEdge` has no per-edge hash field. Edge tampering is detected through the canonical graph digest — the serialized graph topology (nodes, edges, payload hashes) is hashed via `sha256_digest()`. Any edge insertion, removal, or modification changes the graph digest.

### 18.8 verify_provenance() Checks

- Required node multiplicity (exactly one `CALCULATION_RUN`, at least one `RESULT`)
- Required edge existence per status topology
- DAG consistency
- Payload hash integrity per node
- Graph digest integrity

---

## 19. Canonical Hash Contract

### 19.1 Shared Utilities

All TASK-009 hashing uses:

```text
hexagent.core.canonical.canonical_json
hexagent.core.canonical.sha256_digest
```

`sha256_digest()` returns `sha256:<64 lowercase hex>`.

### 19.2 Catalog Hash

`catalog_content_hash` must be `sha256:<64 lowercase hex>`. Computed over sorted-key canonical JSON of `(catalog_id, catalog_version, source_identity, schema_version, assembly_options)` where options are sorted by `assembly_option_id` ASCII ascending.

Duplicate `assembly_option_id` validation must occur **before** sorting for hash verification. If duplicates exist, the run is BLOCKED with `CATALOG_INVALID` — no hash verification is performed.

### 19.3 Numeric Normalization

- Float fields (diameters, roughness, fouling, tolerances): serialized via `canonical_json` default float representation.
- Length fields: canonicalized through integer tick conversion (§5.2); stored in identity/hash as canonical Decimal string (e.g. `"12.350"`).
- The same canonical form is used for catalog hash, candidate identity, and JSON round-trip.

### 19.4 Identity/Hash Payload Format

Each identity's canonical payload is a `canonical_json` object with fields in declared order, sorted keys, no whitespace, no trailing newline.

---

## 20. CandidateEvaluation

```text
candidate_identity: SourceQualifiedCandidateIdentity
candidate_evaluation_identity: CandidateEvaluationIdentity
rating_status: str | None
feasibility_status: str | None
feasible: bool
verified_rating_evidence: VerifiedRatingEvidenceSnapshot | None
invalid_rating_evidence: InvalidRatingEvidenceRecord | None
diagnostics: tuple[CandidateDiagnosticKey, ...]
primary_diagnostic: CandidateDiagnosticKey | None
duty_margin_w: float | None
duty_shortfall_w: float | None
duty_overshoot_w: float | None
meets_target_without_tolerance: bool | None
partial_audit: bool
```

### Invariants

- `verified_rating_evidence is not None` ⇔ `invalid_rating_evidence is None`
- `invalid_rating_evidence is not None` ⇒ `feasible == False`
- `partial_audit == True` ⇒ candidate is in audit set but no subsequent candidate was evaluated

---

## 21. CandidateRankingRecord

```text
source_qualified_candidate_id: str
objective: str
sort_key: tuple[float | int | str, ...]
rank: int
feasible: bool
```

`sort_key` is the full serialized comparison tuple (§13.2, §16.3), not only the final rank.

---

## 22. SizingResultIdentity

```text
sizing_request_identity_digest: str
catalog_snapshot_digests: tuple[str, ...]
canonical_candidate_evaluation_digests: tuple[str, ...]
canonical_ranking_record_digests: tuple[str, ...]
selected_candidate_id: str | None
top_candidate_ids: tuple[str, ...]
raw_combination_count: int
unique_candidate_count: int
evaluated_candidate_count: int
feasible_candidate_count: int
non_feasible_candidate_count: int
termination_reason: str
core_provenance_digest: str
```

All digests are `sha256:<64 hex>`. Computed via `canonical_json` over the fields in declaration order.

---

## 23. SizingOptimizationResult

```text
status: SizingStatus
request_identity: SizingRequestIdentity
catalog_snapshots: tuple[CompleteDoublePipeCatalogSnapshot, ...]
raw_combination_count: int
unique_candidate_count: int
evaluated_candidate_count: int
feasible_candidate_count: int
candidate_evaluations: tuple[CandidateEvaluation, ...]
ranking_records: tuple[CandidateRankingRecord, ...]
selected_candidate: CandidateEvaluation | None
top_candidates: tuple[CandidateEvaluation, ...]
warnings: tuple[EngineeringMessage, ...]
blockers: tuple[EngineeringMessage, ...]
failure: RunFailure | None
termination_reason: str
partial_audit: bool
core_provenance_digest: str
result_hash: str
provenance: ProvenanceGraph
provenance_digest: str
```

- `result_hash` = `sha256_digest(canonical_json(SizingResultIdentity payload))`
- `selected_candidate` references the first entry in `top_candidates`
- JSON round-trip must preserve all fields, hashes, and provenance

---

## 24. Frozen ErrorCode Values

### 24.1 Existing Reused Codes

```text
INPUT_MISSING              — missing required field in SizingRequest
INPUT_INCONSISTENT         — conflicting fields in SizingRequest
UNIT_INVALID               — unit/quantity contract violation
HASH_MISMATCH              — tamper verification of already-built sizing identity/result
PROVENANCE_INCOMPLETE      — provenance graph missing required nodes/edges
UNSUPPORTED_SERVICE        — unsupported feature requested
CALCULATION_BLOCKED        — generic calculation blocked
CORRELATION_IMPLEMENTATION_UNAVAILABLE — propagated from C4, unchanged
```

### 24.2 ErrorCode Ownership Distinction

```text
CATALOG_IDENTITY_MISMATCH  — caller-supplied catalog_content_hash differs from computed hash
HASH_MISMATCH              — verify_hash() on an already-constructed sizing identity/result fails
```

These are not synonymous.

### 24.3 New TASK-009 ErrorCode Strings

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

Total: 14 new codes. No synonymous duplicates.

---

## 25. Terminology

TASK-009 does not claim organizational source approval.

| Imprecise | Precise |
|-----------|---------|
| "approved catalog snapshots" | "caller-supplied, structurally validated, hash-verified catalog snapshots" |
| "approved candidates" | "structurally valid, hash-verified candidates" |
| "organization-approved master catalogs" | reserved for TASK-016 |

---

## 26. Exclusions

- pressure-drop formulas or constraints
- continuous nonlinear optimization
- stochastic, genetic, Bayesian, or ML optimization
- velocity envelope constraints (deferred to future review)
- cost and life-cycle economics
- material selection
- mechanical strength or code compliance
- API endpoints, reports, UI
- C4 numerical implementation
- two-phase, shell-and-tube, plate, air-cooled exchanger sizing
- independent Cartesian product of inner-tube and outer-pipe options

---

## 27. Required Test Matrix

### 27.1 Length and Catalog (1–22)

1. Power-of-10 quantum — rejects non-1E-N quantum
2. Explicit lengths use unified quantum
3. Explicit duplicates after quantization — deduplicated
4. Grid `INCLUDE_MAX_IF_ALIGNED` — aligned endpoint included
5. Grid non-aligned — floor applied, no value > maximum
6. Grid `EXCLUDE_MAX` — aligned endpoint excluded
7. Grid `EXCLUDE_MAX` — non-aligned (no hi generated)
8. No value generated > `maximum_length_m`
9. `minimum == maximum`, `INCLUDE_MAX_IF_ALIGNED` — count = 1
10. `minimum == maximum`, `EXCLUDE_MAX` — count = 0
11. `increment_m < length_quantum_m` → `CATALOG_INVALID`
12. Request `minimum_effective_length_m` closed-boundary intersection
13. Request `maximum_effective_length_m` closed-boundary intersection
14. Request bounds quantization matches catalog quantum
15. Count-only grid algorithm — no list allocated before cap check
16. Count-only request intersection — no list allocated
17. Cap blocks before length materialization
18. Cap blocks before candidate materialization
19. Cap blocks before any TASK-008 call
20. Exact `raw_combination_count`, `unique_candidate_count`, `evaluated_candidate_count`
21. Catalog hash uses `sha256:` format
22. Duplicate `assembly_option_id` detected before hash verification

### 27.2 Identity and Evaluation (23–34)

23. `PhysicalCandidateIdentity` stability across catalog sources
24. `SourceQualifiedCandidateIdentity` — different catalog → distinct
25. `CandidateEvaluationIdentity` changes with request
26. Corrected ranking — target satisfaction first
27. `MINIMUM_OUTER_HEAT_TRANSFER_AREA` ranking key
28. `MINIMUM_EFFECTIVE_LENGTH` ranking key
29. Objectives select different candidates in Golden case
30. Exact feasible tie resolved by canonical candidate ID
31. `CandidateEvaluation` JSON round-trip
32. `SizingOptimizationResult` hash payload
33. Canonical evaluation order (`source_qualified_candidate_id` ascending)
34. `SizingRequestIdentity` includes all required fields

### 27.3 Integrity and Evidence (35–43)

35. Mixed SUCCEEDED/BLOCKED/FAILED candidates audited
36. `VerifiedRatingEvidenceSnapshot` vs `InvalidRatingEvidenceRecord` — distinct
37. Integrity invalid — immediate stop, remaining count reported
38. Verification routine exception → `FAILED` (not BLOCKED)
39. `VerifiedRatingEvidenceSnapshot` — permitted null thermal fields
40. Flow areas marked as geometry-derived
41. C4 (`CORRELATION_IMPLEMENTATION_UNAVAILABLE`) propagated unchanged
42. `InvalidRatingEvidenceRecord` does not expose trusted metrics
43. `partial_audit` field semantics

### 27.4 Provenance (44–49)

44. SUCCEEDED provenance topology
45. Invalid request provenance topology
46. Invalid catalog provenance topology
47. Cap exceeded / no candidate provenance topology
48. Integrity invalid provenance topology
49. FAILED provenance topology

### 27.5 Two-Stage Provenance (50–53)

50. Two-stage core/final provenance
51. `result_hash` excludes final provenance digest
52. Edge tamper detected via graph digest
53. UUID5 deterministic node IDs

### 27.6 Validation and ErrorCodes (54–63)

54. `required_duty_w > 0` enforced
55. `top_n` rejects `bool`
56. `request_raw_combination_cap` rejects `bool`
57. Duplicate `(catalog_id, catalog_version)` references rejected
58. `CATALOG_IDENTITY_MISMATCH` vs `HASH_MISMATCH` non-overlapping
59. Provider identity mismatch → BLOCKED with `PROPERTY_PROVIDER_IDENTITY_MISMATCH`
60. Exact callable forwards `SolverParams` (7 fields)
61. Exact callable forwards `CalculationContext`
62. `required_duty_w` does **not** enter `RatingRequestIdentity`
63. `PROPERTY_PROVIDER_IDENTITY_MISMATCH` ErrorCode

### 27.7 Diagnostics and Ordering (64–67)

64. Full non-feasible sort key (8 fields)
65. `CandidateDiagnosticKey` sentinel when no diagnostic
66. Pure duty-infeasible diagnostic (`REQUIRED_DUTY_NOT_MET`)
67. Deterministic primary diagnostic selection

### 27.8 Tamper Detection (68–74)

68. Catalog tamper
69. Candidate tamper
70. Ranking tamper
71. Selected-candidate tamper
72. Solver parameter change changes identity
73. Fouling change changes identity
74. Repeated-run determinism

### 27.9 Golden Cases and Documentation (75–78)

75. Independent smallest-outer-area Golden case
76. Independent shortest-effective-length Golden case
77. Issue #23 references canonical task card and frozen commit SHA
78. JSON round-trip preserves all fields, hashes, provenance

### 27.10 Quality Gates (79–80)

79. Ruff, format check, mypy, pytest with coverage pass
80. pip-audit, Python 3.11 and 3.12

---

## 28. Delivery Sequence

1. Complete Round 4 Engineering Design Review.
2. Only after review passes: create implementation branch and Draft PR.
3. Implement catalog and identity models before optimizer.
4. Implement deterministic candidate generation and deduplication.
5. Integrate TASK-008 `rate_double_pipe()` evaluation.
6. Implement feasibility and ranking.
7. Implement result hash, provenance, JSON round-trip, and tamper verification.
8. Add direct, Golden, and integration tests.
9. Keep PR Draft through engineering review and CI pass.

---

## 29. Acceptance Criteria

- [ ] Round 4 Design Review passes before implementation starts
- [ ] Only caller-supplied, structurally validated, hash-verified catalog candidates are generated
- [ ] `SourceQualifiedCandidateIdentity` is the deduplication key
- [ ] TASK-008 `rate_double_pipe()` is the sole thermal evaluator
- [ ] Candidate generation and ranking are insertion-order independent
- [ ] Objective is explicit and typed; no weighted composite score
- [ ] `NO_FEASIBLE_CANDIDATE` is `BLOCKED`, not `FAILED`
- [ ] Target satisfaction dominates objective value in feasible ranking
- [ ] Top-N contains feasible candidates only; truncation adds a warning
- [ ] Non-feasible ordering uses full `CandidateDiagnosticKey` sort key
- [ ] `VerifiedRatingEvidenceSnapshot` vs `InvalidRatingEvidenceRecord` are distinct
- [ ] Single integrity-invalid candidate stops evaluation immediately and blocks the run
- [ ] Provenance topology is status-specific; two-stage core/final construction
- [ ] All identity/hash uses `sha256:<64hex>` and `canonical_json` from shared utilities
- [ ] Exact 14 TASK-009 ErrorCode strings are used; `CATALOG_IDENTITY_MISMATCH` and `HASH_MISMATCH` are non-overlapping
- [ ] No pressure-drop or velocity constraint is introduced
- [ ] Blocked and failed candidates remain auditable
- [ ] Candidate and result hashes are deterministic
- [ ] JSON round-trip and tamper detection pass
- [ ] Required 78 test items + 2 Golden cases are covered
- [ ] Ruff, format check, mypy, pytest with coverage, and pip-audit pass on Python 3.11 and 3.12
- [ ] Engineering design review passes before Ready or merge
