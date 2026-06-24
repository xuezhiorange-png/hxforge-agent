# Double-Pipe Heat-Exchanger Rating — TASK-008

**Status:** IN_PROGRESS / Draft
**Milestone:** M2
**Task card:** [docs/tasks/TASK-008-double-pipe-rating.md](tasks/TASK-008-double-pipe-rating.md)

---

## 1. Overview

TASK-008 implements rating analysis for a fixed-geometry double-pipe heat
exchanger. Given operating conditions (inlet temperatures, pressures, mass
flows) and a fixed geometry, it computes the heat duty, outlet temperatures,
and key thermal-hydraulic metrics.

The entry point is the pure function `rate_double_pipe()` in
`src/hexagent/exchangers/double_pipe/rating.py`. It always returns a
`RatingResult`; domain errors are expressed as `BLOCKED`/`FAILED` status
rather than raised exceptions.

**Supported flow arrangements:** Counter-flow, parallel-flow (counter-flow
default).

**Scope limitations (out of scope):** Sizing/optimization (TASK-009),
API/reports (TASK-010), C4 numerical implementation (Issue #19), two-phase
flow, shell-and-tube/plate/air-cooled exchangers, pressure-drop models.

---

## 2. Architecture

```
rate_double_pipe()          ← Main entry point (rating kernel)
  │
  ├─ geometry.py            ← DoublePipeGeometry (immutable, validated)
  │
  ├─ thermal.py             ← Thermal resistance network, LMTD, ε-NTU
  │
  ├─ solver.py              ← Q-based root-finding with dynamic bracket, EvaluationRecorder
  │
  ├─ result.py              ← RatingResult (Pydantic, immutable, hash-verified)
  │
  └─ service.py             ← DoublePipeRatingService (DesignCase → rating)
```

All source lives under `src/hexagent/exchangers/double_pipe/`.

### Source files

| File | Purpose |
|------|---------|
| `geometry.py` | `DoublePipeGeometry` frozen dataclass with validation |
| `thermal.py` | `ThermalResistanceBreakdown`, LMTD, ε-NTU pure functions |
| `solver.py` | `solve_rating()` — Q-based root-finding with dynamic bracket, EvaluationRecorder, SolverEvaluationPhase |
| `rating.py` | `rate_double_pipe()` — the rating kernel |
| `result.py` | `RatingResult` Pydantic model, provenance, hash |
| `service.py` | `DoublePipeRatingService` — DesignCase bridge |

---

## 3. Energy Convention

| Quantity | Formula | Sign convention |
|----------|---------|-----------------|
| Duty Q | Positive | Heat transfers from hot to cold |
| Hot-side loss | `Q_hot = m_hot × (h_hot_in − h_hot_out)` | Q_hot = Q |
| Cold-side gain | `Q_cold = m_cold × (h_cold_out − h_cold_in)` | Q_cold = Q |
| Energy residual | `|Q_hot − Q_cold|` | Checked post-convergence |

- For trial Q in the residual function:
  - `h_hot_out = h_hot_in − Q / m_hot`
  - `h_cold_out = h_cold_in + Q / m_cold`
- Outlet temperatures are back-calculated from `PropertyProvider.state_ph()`,
  **not** from linear Cp approximation.

---

## 4. Thermal Resistance Model

The five-resistance series network (all in K/W):

```
R_total = R_conv_i + R_foul_i + R_wall + R_foul_o + R_conv_o
UA = 1 / R_total
```

| Resistance | Formula | Notes |
|------------|---------|-------|
| `R_conv_i` | `1 / (h_i × A_i)` | Inner tube convection |
| `R_foul_i` | `Rf_i / A_i` | Inner fouling (m²·K/W per side) |
| `R_wall` | `ln(D_o / D_i) / (2π·k_wall·L)` | Cylindrical wall conduction |
| `R_foul_o` | `Rf_o / A_o` | Outer fouling |
| `R_conv_o` | `1 / (h_o × A_o)` | Annulus convection |

- `A_i = π × D_i × L` (inner tube ID area)
- `A_o = π × D_o × L` (inner tube OD area)
- Overall U basis: outer surface of inner tube (OD), i.e., `U_o = UA / A_o`
- Also reported: `U_i = UA / A_i`

The `ThermalResistanceBreakdown` dataclass stores each component plus
`total_resistance` and `ua_w_k`, and validates `sum(components) == 1/UA`.

---

## 5. LMTD Computation

### Counter-flow

```
ΔT₁ = T_h,in − T_c,out
ΔT₂ = T_h,out − T_c,in
LMTD = (ΔT₁ − ΔT₂) / ln(ΔT₁ / ΔT₂)
```

### Parallel-flow

```
ΔT₁ = T_h,in − T_c,in
ΔT₂ = T_h,out − T_c,out
LMTD = (ΔT₁ − ΔT₂) / ln(ΔT₁ / ΔT₂)
```

### Stable limits

- When `|ΔT₁ − ΔT₂| < temp_tolerance` (default 1e-10 K): returns arithmetic
  mean `(ΔT₁ + ΔT₂) / 2`.
- When either `ΔT₁ ≤ 0` or `ΔT₂ ≤ 0` (temperature crossing/pinch): returns
  `NaN`. No `abs()` masking — crossing is a hard blocker.
- Correction factor `F = 1` for pure counter/parallel flow.

---

## 6. ε-NTU Diagnostics

Post-convergence, ε-NTU is computed as an independent diagnostic:

```
NTU = UA / C_min
C_r = C_min / C_max
```

**Counter-flow effectiveness:**
```
ε = (1 − exp(−NTU·(1 − C_r))) / (1 − C_r·exp(−NTU·(1 − C_r)))
```
Special case `C_r = 1`: `ε = NTU / (1 + NTU)`

**Parallel-flow effectiveness:**
```
ε = (1 − exp(−NTU·(1 + C_r))) / (1 + C_r)
```

ε-NTU is a **diagnostic cross-check**, not a conflicting outlet temperature
source. The outlet temperatures come exclusively from the Q-based root-finding solver.

---

## 7. Solver Contract

### Root variable

Heat duty **Q** (scalar, in watts).

### Residual

```
residual(Q) = Q − UA(Q) × LMTD(Q)
```

Each residual evaluation:
1. Compute trial outlet enthalpies: `h_hot_out`, `h_cold_out` from Q
2. `PropertyProvider.state_ph()` to back-calculate outlet states
3. Compute representative bulk temperatures: `T_bulk = (T_in + T_out) / 2`
4. Call TASK-007 correlation service (`evaluate_hx_correlation`) for tube and
   annulus sides
5. Obtain `Re`, `Pr`, `Nu`, `h`, selected correlation, applicability
6. Build thermal resistance → compute UA
7. Compute LMTD (counter or parallel) and return residual

Property or correlation failures raise a typed `TrialEvaluationAbort` which
the solver catches; the evaluation is recorded via `EvaluationRecorder` and
the iteration proceeds with diagnostic preservation.

### Dynamic bracket and QMaxResult

`QMaxResult` captures the outcome of the upper-bracket search: the maximum
feasible Q, the terminal ΔT state (pinch/temperature-cross check), and
whether a valid bracket was established.

- **Q_max** derived from `C_min × (T_h,in − T_c,in) × max_q_fraction`
  (default 99%)
- Start from Q = 0, probe upward in 20 equal steps to find sign change
- Counter-flow: both terminal ΔT must remain positive
- Parallel-flow: hot outlet must exceed cold outlet at exit
- If no sign change → `SOLVER_BRACKET_NOT_FOUND` blocker

### Solver method
A bounded Q-based root-finder with dual tolerance convergence: absolute
residual and relative bracket-to-C_min temperature-effect tolerance. The
`SolverEvaluationPhase` enum tracks evaluation stages (ENTHALPY, PROPERTY,
CORRELATION, THERMAL_RESISTANCE, LMTD, RESIDUAL, POST_CALC) so each
iteration step is independently verifiable.

---

## 8. Convergence Criteria

**All conditions** must be satisfied (dual tolerance convergence):

The solver enforces **dual tolerance** convergence: absolute residual and
relative bracket-to-C_min temperature-effect tolerance. For parallel-flow,
an additional **parallel pinch check** verifies that the hot outlet remains
above the cold outlet at exit across the full bracket range, preventing
silent convergence to a physically infeasible solution.

| Criterion | Formula | Default |
|-----------|---------|---------|
| Absolute residual | `|residual_Q| ≤ max(abs_tol, rel_tol × max(|Q|, 1))` | 1e-3 W, 1e-8 |
| Bracket temperature effect | `bracket_width / C_hot ≤ bracket_tol` | 1e-4 K |
| Iteration limit | `iterations ≤ max_iterations` | 100 |

---

## 9. PropertyProvider Integration

**Inlet states** — `state_tp(fluid, T, P)`:
- Hot and cold inlet FluidStates obtained before solver loop
- Phase validated: must be single-phase (liquid, gas, or supercritical)
- Enthalpies, Cp, density, viscosity, conductivity extracted

**Outlet states** — `state_ph(fluid, P, h)`:
- Called inside the residual function for each trial Q
- Returns outlet temperature, density, transport properties
- Property failures raise typed `TrialEvaluationAbort`; the evaluation is
captured by `EvaluationRecorder` with the appropriate `EvaluationRole`
- All calls are recorded as `PropertyCallRecord` for provenance

**Representative bulk temperature:**
```
T_bulk = (T_inlet + T_outlet) / 2
```

Every PropertyProvider call is recorded by the `EvaluationRecorder` with:
- Fluid, query type (TP/PH), inputs, backend identity, stage, stream role
- Continuous evaluation identity (monotonic counter + phase tag)
- 7 `EvaluationRole` categories: INLET_STATE, OUTLET_STATE, BULK_EVAL,
  CORRELATION_CALL, THERMAL_RESISTANCE, LMTD_EVAL, POST_CONVERGENCE
- Evaluation identity verifier confirms replay integrity

---

## 10. TASK-007 Correlation Integration

The rating kernel calls `evaluate_hx_correlation()` from the correlation
service (`hexagent.correlations.service`) for each side:

| Side | Geometry type | Boundary condition |
|------|--------------|-------------------|
| Tube | `CircularTubeGeometry(inside_diameter_m=D_i, heat_transfer_length_m=L)` | **explicit, required** |
| Annulus | `ConcentricAnnulusGeometry(inner_tube_outer_diameter_m=D_o, outer_pipe_inside_diameter_m=D_outer, ...)` | **explicit, required** |

The `tube_in_hot` flag determines which fluid flows in the tube vs. annulus.

From each correlation call:
- `Re`, `Pr`, `Nu`, `h` (heat transfer coefficient)
- Selected correlation ID and version
- Applicability status and warnings

Correlation warnings are appended to the result's warning list.

---

## 11. C4 Behavior (Issue #19)

If operating conditions require C4 (annulus laminar inner constant-heat-flux):

- The correlation service returns `implementation_unavailable` status
- The rating kernel treats this as a **blocker** (not a silent fallback)
- No substitution with other correlations
- No guessing or interpolation of C4 table data
- Error code: `CORRELATION_IMPLEMENTATION_UNAVAILABLE`
- See [Issue #19](https://github.com/.../issues/19) for tracking

---

## 12. Result Model Fields

`RatingResult` is a frozen Pydantic `BaseModel` with these field groups:

### Status and arrangement
- `status` (`RatingStatus`: SUCCEEDED, BLOCKED, FAILED)
- `flow_arrangement` (`FlowArrangement`: COUNTERFLOW, PARALLEL)

### Primary results
- `heat_duty_w` (W)
- `hot_outlet_temperature_k` (K)
- `cold_outlet_temperature_k` (K)

### Tube-side convection
- `tube_reynolds`, `tube_prandtl`, `tube_nusselt`, `tube_h`
- `tube_selected_correlation_id`, `tube_selected_correlation_version`
- `tube_applicability_status`

### Annulus-side convection
- `annulus_reynolds`, `annulus_prandtl`, `annulus_nusselt`, `annulus_h`
- `annulus_selected_correlation_id`, `annulus_selected_correlation_version`
- `annulus_applicability_status`

### Areas and resistance
- `area_inner_m2`, `area_outer_m2`
- `resistance_breakdown` (5 components + total + UA)

### Overall coefficients
- `U_inner_basis`, `U_outer_basis`, `UA_w_k`

### ε-NTU diagnostics
- `C_hot_w_k`, `C_cold_w_k`, `C_min_w_k`, `C_max_w_k`
- `capacity_ratio`, `NTU`, `effectiveness`

### LMTD and residuals
- `LMTD_k`
- `energy_residual_w`, `ua_lmtd_residual_w`

### Solver diagnostics
- `iterations`, `converged`, `solver_termination_reason`
- `solver_details` (residual_w, bracket_width_w, function_evaluations)

### Messages
- `warnings` (tuple of `EngineeringMessage`)
- `blockers` (tuple of `EngineeringMessage`)
- `failure` (optional `RunFailure`)

### Provenance and identity
- `property_calls` (tuple of `PropertyCallRecord`)
- `provider_identity`, `request_identity`, `execution_context`
- `result_hash` (SHA-256, `sha256:<hex>`)
- `provenance_graph` (`ProvenanceGraph`)
- `provenance_digest`

**Post-calculation BLOCKED:** When a property or correlation evaluation fails
after partial convergence progress, the solver emits `BLOCKED` status that
**preserves all diagnostic data collected so far** (evaluations, partial
residuals, correlation applicability warnings). Debugging context is never
lost even when the rating cannot complete.

**Invariants:**
- BLOCKED requires ≥1 blocker; SUCCEEDED requires convergence and no blockers
- FAILED requires a `RunFailure` record
- `flow_arrangement` must match `request_identity.flow_arrangement`
- No NaN/Infinity in any float field

---

## 13. Provenance and Hash

### Two-layer hash and provenance

The result uses a **two-layer** provenance and identity model:

**Layer 1 — Evaluation identity:** Each solver evaluation receives a
continuous identity (monotonic counter + `SolverEvaluationPhase` tag) via
the `EvaluationRecorder`. The evaluation identity verifier confirms that
recorded evaluations are replay-consistent and no steps were skipped or
duplicated.

**Layer 2 — Result hash:** Deterministic SHA-256 computed over all
engineering-relevant fields:
- Request identity (geometry, fluids, operating conditions, solver params)
- Provider identity (name, version, reference state policy)
- All computed quantities (Q, outlet temperatures, Re, Pr, Nu, h, UA, etc.)
- Solver diagnostics, warnings, blockers

Format: `sha256:<64 hex characters>`

Verification methods:
- `verify_hash()` — recomputes hash and compares
- `validate_integrity()` — checks field hash + provenance

### Provenance graph

A directed acyclic graph with node types:
- `EXTERNAL` or `CASE_REVISION` — root input identity
- `CALCULATION_RUN` — the solver execution
- `CORRELATION` — each TASK-007 correlation evaluation
- `PROPERTY_CALL` — each PropertyProvider call
- `RESULT` — the final result (singleton)

Edges: `CALCULATION_RUN → RESULT` (`produces`), plus dependency edges.
All node IDs are UUID5-based and deterministic.

Verification: `verify_provenance()` checks node identities, edge structure,
and payload hashes.

---

## 14. ErrorCode Values

Double-pipe-specific error codes (defined in `hexagent.domain.messages`):

| ErrorCode | When raised |
|-----------|-------------|
| `INVALID_DOUBLE_PIPE_GEOMETRY` | Geometry validation failure |
| `INVALID_FLOW_SIDE_ASSIGNMENT` | Hot inlet ≤ cold inlet |
| `NON_POSITIVE_MASS_FLOW` | Mass flow ≤ 0 or non-finite |
| `PROPERTY_EVALUATION_FAILED` | PropertyProvider state query failed |
| `PHASE_NOT_SUPPORTED` | Inlet phase not single-phase |
| `CORRELATION_NOT_FOUND` | No matching correlation (TASK-007) |
| `CORRELATION_IMPLEMENTATION_UNAVAILABLE` | C4 or other unimplemented correlation |
| `TEMPERATURE_CROSSING` | Hot outlet < cold outlet (pinch violation) |
| `INVALID_LMTD` | LMTD non-positive or NaN |
| `SOLVER_BRACKET_NOT_FOUND` | No sign change in residual bracket |
| `SOLVER_NON_CONVERGENCE` | Max iterations exceeded |
| `ENERGY_BALANCE_NOT_CLOSED` | Zero duty or energy imbalance |

Failed results still receive a deterministic hash and valid provenance.

---

## 15. Test Coverage Summary

| Test file | Type | Test count | Scope |
|-----------|------|------------|-------|
| `tests/unit/test_double_pipe_geometry.py` | Unit | 48 | Geometry construction, validation, derived quantities, immutability, serialization |
| `tests/unit/test_double_pipe_thermal.py` | Unit | 45 | Thermal resistance, LMTD (counter + parallel), ε-NTU, wall/convective/fouling resistance |
| `tests/unit/test_double_pipe_solver.py` | Unit | 64 | Bracket finding, Q-based root-finding solver, convergence criteria, edge cases |
| `tests/integration/test_double_pipe_rating.py` | Integration | 20 | End-to-end rating with CoolProp: counterflow, parallel-flow, energy balance, zero/negative flows, temperature crossing, hash determinism, provenance, JSON round-trip |
| **Total** | | **177** | |

### Key integration test scenarios

1. Counter-flow rating with water-water case
2. Parallel-flow rating
3. Counter-flow duty ≥ parallel-flow duty (expected physics)
4. Zero hot mass flow → BLOCKED
5. Negative cold mass flow → BLOCKED
6. Hot inlet ≤ cold inlet → BLOCKED
7. Same input → same hash (determinism)
8. Different geometry → different hash
9. Provenance graph structure and verification
10. JSON round-trip preserves duty and convergence status

### Example case

`examples/water_water_double_pipe.json`: Water-to-water, 90°C/4 bar hot,
20°C/3 bar cold, 2 kg/s each, 4 bar operating pressure.

---

*Generated for TASK-008 on branch `codex/task-008-fixed-geometry-double-pipe-rating`.*
