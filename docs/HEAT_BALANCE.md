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

The same engineering inputs, property results, software identity, and provenance context produce the same result hash.
Changing the execution or lineage context changes provenance_digest and therefore changes result_hash.

`result_hash` represents the identity of a complete execution result. The identity includes:
- Engineering request (fluid, streams, solver params)
- Provider identity (backend, version, config)
- Computed result (states, energy balance, solver diagnostics)
- Property-call trace
- Warnings, blockers, failure
- Provenance lineage/context (request_id, design_case_revision_id, calculation_run_id)

The same engineering inputs and property results, under different `CalculationContext`, may produce different `result_hash` values because the provenance digest is included in the hash payload.

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

The `provenance_digest` field stores a deterministic SHA-256 hash of the core provenance graph (all nodes EXCEPT the RESULT node, all edges EXCEPT the `produces` edge). This breaks the circular dependency between the result hash and the provenance graph:

1. Core provenance is built (without RESULT node)
2. `provenance_digest = _provenance_graph_digest(core_graph)`
3. `provenance_digest` is included in the result hash payload
4. Result hash is computed
5. RESULT node is added to the graph with the result hash

The `verify_provenance()` method validates:
1. Recomputable `provenance_digest` from the core graph
2. DAG validity (enforced by `ProvenanceGraph` validator)
3. All node payload hashes are valid SHA-256
4. Exactly one root, one `CALCULATION_RUN`, one `RESULT`
5. `PROPERTY_CALL` count matches `len(property_calls)`
6. `WARNING` count matches `len(warnings)`
7. `BLOCKER` count matches `len(blockers)`
8. All edge endpoints reference existing nodes
9. RESULT node's `result_hash` matches the result's own `result_hash`

The `verify_hash()` method verifies both the formal result hash AND provenance integrity.

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
