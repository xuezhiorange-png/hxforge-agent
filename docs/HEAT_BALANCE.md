# Heat Balance and Specification Closure

**Version:** 0.1.0  
**Scope:** Single-phase sensible heat only  
**Status:** Implemented (TASK-006)

## Overview

The heat-balance kernel resolves valid combinations of duty, flow, and
inlet/outlet states while enforcing energy conservation, phase consistency,
and temperature feasibility.

## Energy Convention

- Duty *Q* is positive from hot stream to cold stream.
- **Hot side:** `Q_hot = m_hot × (h_hot,in − h_hot,out)`
- **Cold side:** `Q_cold = m_cold × (h_cold,out − h_cold,in)`
- **Residual:** `R = Q_hot − Q_cold`
- **Relative imbalance:** `|R| / max(|Q_hot|, |Q_cold|)` when Q > 0
- Zero-duty cases are handled separately without division by zero.

## Specification Modes

| Mode | Description | Unknowns |
|------|-------------|----------|
| `KNOWN_DUTY` | Duty known | Both outlet temperatures |
| `KNOWN_HOT_OUTLET` | Hot-side outlet known | Duty + cold outlet |
| `KNOWN_COLD_OUTLET` | Cold-side outlet known | Duty + hot outlet |
| `BOTH_OUTLETS_KNOWN` | Both outlets known | Duty (verification) |
| `UNDER_SPECIFIED` | Insufficient information | Error |
| `OVER_SPECIFIED` | Conflicting information | Error |

### Classification Rules

```
hot_outlet  cold_outlet  duty    → mode
─────────   ──────────   ────      ────
   ✗           ✗          ✗      UNDER_SPECIFIED
   ✗           ✗          ✓      KNOWN_DUTY
   ✓           ✗          ✗      KNOWN_HOT_OUTLET
   ✗           ✓          ✗      KNOWN_COLD_OUTLET
   ✓           ✓          ✗      BOTH_OUTLETS_KNOWN
   ✓           ✗          ✓      KNOWN_HOT_OUTLET (verify duty)
   ✗           ✓          ✓      KNOWN_COLD_OUTLET (verify duty)
   ✓           ✓          ✓      OVER_SPECIFIED
```

## Solver

Uses **Brent's method** (`scipy.optimize.brentq`) for bounded root-finding.

### Endpoint Detection

Before calling Brent's method, the solver checks if either bracket endpoint
is an exact (or near-exact) root by evaluating `|f(endpoint)| < absolute_energy_tolerance_w`.
If so, the endpoint is accepted directly:
- Algorithm iterations = 0
- Brent function evaluations = 0 (no brentq call)
- Bracket probes retain their real count

Non-endpoint roots use brentq normally, and algorithm iterations come
directly from SciPy's `RootResults.iterations` without post-hoc override.

### Control Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `temperature_tolerance` | 1e-4 K | Absolute temperature convergence tolerance |
| `energy_tolerance` | 1e-3 | Maximum relative energy imbalance (dimensionless) |
| `max_iterations` | 100 | Maximum function evaluations per root-finding call |

### Bracket Construction

The search bracket is built dynamically:
1. Start from the inlet temperature.
2. Probe outward in 10 K steps (up to 300 K).
3. Stop when the residual changes sign.
4. Apply Brent's method on the resulting bracket.

This avoids hard-coded bounds that may fall outside a fluid's valid
property range.

## Temperature Feasibility

For positive duty:
- Hot outlet must not exceed hot inlet.
- Cold outlet must not be below cold inlet.

Additional checks (produce warnings):
- Temperature cross detection (hot outlet < cold outlet).
- Non-positive minimum approach temperature.
- Near-zero approach temperature (within tolerance).

## Phase-Change Handling

v0.1 supports **single-phase sensible heat only**.

The kernel checks the phase region of all property-evaluation results.
If any state is in a two-phase, saturated, or unknown region, the
calculation returns a `UNSUPPORTED_SERVICE` blocker.

Phase regions that are rejected:
- `SATURATED_LIQUID`
- `SATURATED_VAPOR`
- `UNKNOWN`

Phase regions that are accepted:
- `LIQUID`
- `GAS`
- `SUPERCRITICAL`
- `SUPERCRITICAL_GAS`
- `SUPERCRITICAL_LIQUID`

## Property Provider Integration

The kernel uses the `PropertyProvider` protocol for all thermodynamic
evaluations:

- **No fixed Cp approximations** in public services.
- All states are evaluated via `state_tp()`.
- Property calls are recorded for provenance.
- Property failures and out-of-range states produce structured blockers.

### Property Call Records

Each property call is recorded with:
- Fluid identifier
- Query type (TP)
- Input values (temperature, pressure)
- Backend name and version
- Result state (temperature, pressure)

## Result Model

The `HeatBalanceResult` is a **frozen Pydantic model** containing:

- `specification_mode`: Classification of the input
- `duty_w`: Solved duty in watts
- `hot_inlet_state` / `hot_outlet_state`: Temperature and enthalpy dicts
- `cold_inlet_state` / `cold_outlet_state`: Temperature and enthalpy dicts
- `residual_w`: Energy residual (Q_hot - Q_cold)
- `relative_imbalance`: |residual| / max(|Q_hot|, |Q_cold|)
- `bracket_probe_count`: Provider calls during bracket search
- `brent_function_evaluation_count`: Brent residual function evaluations
- `brent_algorithm_iteration_count`: Brent algorithm iterations from SciPy
- `solver_converged`: Whether the Brent solver found a root
- `property_calls`: Traceable property evaluation records
- `warnings`: Non-fatal diagnostic messages
- `blockers`: Fatal error messages
- `failure`: RunFailure record (for FAILED status only)
- `result_hash`: Deterministic SHA-256 content hash
- `provenance_graph`: Valid DAG of calculation provenance
- `request_identity`: Frozen snapshot of all original request fields
- `provider_identity`: Frozen snapshot of provider configuration identity

### Deterministic Hashing

The result hash is computed via `_build_result_payload()` — the single source of truth. Both construction and verification call this function. The payload includes:
- Request identity (fluid EOS backend, components, mass flows, pressures, temperatures, known duty, flow arrangement, solver params) — **canonical source for request fields**
- Provider identity (name, version, git revision, reference state, config fingerprint, cache policy) — **canonical source for provider config** (from `ProviderIdentitySnapshot`)
- Specification mode
- All four fluid states (inlet/outlet × hot/cold)
- Energy balance fields (q_hot, q_cold, residual, relative imbalance, acceptance basis)
- Status, duty, solver convergence, failure
- Three solver counters (bracket probes, Brent function evaluations, Brent algorithm iterations)
- Property call trace, warnings, blockers
- Software version

`RequestIdentity` contains only request-side fields (fluid identity, stream inputs, solver params, flow arrangement). Provider configuration fields were removed to eliminate duplication — `ProviderIdentitySnapshot` is the sole canonical source for provider identity.

Same inputs + same property results + same software identity = same hash.
Any change to request identity, provider identity, or result fields changes the hash.
`verify_hash()` rebuilds the canonical payload from stored fields and compares.

## Provenance

The provenance graph is a valid DAG. When a `CalculationContext` is provided with a `design_case_revision_id`, the graph includes a `CASE_REVISION` root node; otherwise it starts with an `EXTERNAL` root node.

- `EXTERNAL` root node (when no `design_case_revision_id` — the default)
- Optional `CASE_REVISION` root node (only when `context.design_case_revision_id` is provided)
- `CALCULATION_RUN` node (with mode, flow arrangement, solver counts — bracket_probe_count, brent_function_evaluation_count, brent_algorithm_iteration_count, convergence, software version)
- `PROPERTY_CALL` nodes (one per property evaluation, including failed calls)
- `RESULT` node (with result hash)
- `WARNING` and `BLOCKER` nodes (as applicable)

Edges:
- `external/case_revision → calculation_run` (triggers)
- `calculation_run → property_call` (calls)
- `calculation_run → result` (produces)
- `calculation_run → warning/blocker` (emits)

### Provenance Integrity

The `verify_provenance()` method validates the provenance graph independently:
1. DAG validity (enforced by `ProvenanceGraph` validator)
2. All node payload hashes are valid SHA-256
3. All edge endpoints reference existing nodes
4. RESULT node's payload_hash matches the result's own `result_hash`
5. Graph is deterministic (recomputed digest matches)

The `_compute_field_hash()` (used by `validate_integrity()`) includes a deterministic digest of the provenance graph, ensuring tamper detection covers the full graph structure.

## API

### `solve_heat_balance(inp, provider) → HeatBalanceResult`

Main entry point for the heat-balance kernel.

### `run_heat_balance(case, provider, *, solver_params) → HeatBalanceResult`

Domain service that bridges `DesignCase` to the kernel.

### `classify_specification(inp) → SpecificationMode`

Classify the specification mode from input.

## Files

- `src/hexagent/core/heat_balance.py` — Core kernel
- `src/hexagent/domain/thermal_service.py` — Domain service
- `tests/unit/test_heat_balance.py` — Unit tests (mock provider)
- `tests/integration/test_heat_balance_property_provider.py` — Integration tests (CoolProp)
- `tests/golden/heat_balance/` — Golden case JSON files
- `docs/HEAT_BALANCE.md` — This document
