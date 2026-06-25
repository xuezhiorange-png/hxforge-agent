# TASK-008 — Fixed-geometry double-pipe rating

**Status:** DONE
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-003, TASK-005, TASK-006, TASK-007
**GitHub Issue:** #20 — CLOSED / COMPLETED
**Branch:** `codex/task-008-fixed-geometry-double-pipe-rating` — merged; remote branch deleted
**PR:** #21 — MERGED

## Completion Record

- **Reviewed Head:** `37eda3580ba7acced1beb4cec307343a9f5449ec`
- **Merge commit:** `cef3f85402b1696b336347293afc7276bbf67545`
- **Engineering Review Passed:** Review `4567761204`
- **CI Run:** `28145757989` — success on Python 3.11 and 3.12
- **Final diff:** 39 files, +22,104 / -58
- **r13 correction tests:** 75 passed, 0 skipped
- **All correction files:** 192 passed, 0 skipped
- **Full unit-test suite:** 1,502 passed, 1 skipped
- **Deferred scope:** C4 remains unimplemented and tracked by open Issue #19
- **Next task:** TASK-009 remains READY; no TASK-009 implementation was included in TASK-008

## Objective

Perform rating analysis for a fixed-geometry double-pipe heat exchanger. Given operating conditions and fixed equipment parameters, compute duty, outlet temperatures, and key thermal-hydraulic metrics.

## Frozen Engineering Contracts

### Flow Arrangements

- **Supported:** Counter-flow, parallel-flow

### Sign Convention

- **Hot side:** Fluid losing heat (T_hot,in > T_hot,out)
- **Cold side:** Fluid gaining heat (T_cold,out > T_cold,in)
- **Duty Q:** Positive when heat transfers from hot to cold
- **Q_hot = m_hot × (h_hot,in - h_hot,out)**
- **Q_cold = m_cold × (h_cold,out - h_cold,in)**

### Fixed Geometry Fields

| Field | Unit | Description |
|-------|------|-------------|
| `inner_tube_outer_diameter_m` | m | Inner tube outer diameter |
| `inner_tube_inner_diameter_m` | m | Inner tube inner diameter |
| `outer_pipe_inside_diameter_m` | m | Outer pipe inside diameter |
| `heat_transfer_length_m` | m | Effective heat transfer length |
| `inner_roughness_m` | m | Inner tube surface roughness (default 0) |
| `outer_roughness_m` | m | Outer pipe surface roughness (default 0) |

### Thermal Resistance

- **Tube wall conduction:** Cylindrical wall resistance using inner/outer diameters and wall thermal conductivity
- **Fouling:** Optional, on tube-side and/or annulus-side
- **Area basis for fouling:** Must be explicitly documented per side (inner tube OD or ID)
- **Overall U area basis:** Outer surface of inner tube (OD), unless explicitly overridden

### Characteristic Lengths

- **Tube side:** Inside diameter D_i
- **Annulus side:** Hydraulic diameter D_h = D_o - D_i (outer ID minus inner OD)

### Property Evaluation

- **Temperature strategy:** T_bulk = (T_in + T_out) / 2 for property evaluation
- **Pressure:** P_bulk = P_in, P_out = P_in (no pressure drop model)

### Heat Transfer Coefficients

- **h_tube:** From tube-side correlation (TASK-007 C1/C2/C3)
- **h_annulus:** From annulus-side correlation (TASK-007 C4/C5)
- **U:** Overall coefficient based on outer surface of inner tube
- **UA:** U × A_outer
- **NTU:** UA / C_min
- **ε-NTU:** Standard effectiveness relations for counter/parallel flow
- **LMTD:** Log-mean temperature difference with correction factor F=1 for pure counter/parallel

### Solver Contract

**Primary unknown:** Heat duty Q (scalar root variable)
- Q > 0: energy transfers from designated hot side to designated cold side
- For trial Q:
  - h_hot,out = h_hot,in - Q / m_hot
  - h_cold,out = h_cold,in + Q / m_cold
- Outlet temperatures MUST be back-calculated from PropertyProvider enthalpy inversion, NOT linear Cp

**Primary residual:**
- residual(Q) = Q - UA(Q) × LMTD(Q)
- UA(Q) updates with trial outlet state, properties, and both-side heat transfer coefficients
- Counter-flow and parallel-flow use correct terminal temperature differences
- LMTD near-equal ΔT uses stable limit expression (no 0/0)
- Any terminal ΔT ≤ 0 is a pinch/temperature-crossing blocker (no abs value masking)
- ε-NTU used as post-convergence diagnostic and independent cross-check, NOT as conflicting second outlet temperature result

**Convergence conditions (all must be satisfied):**
- |residual_Q| <= max(1e-3 W, 1e-8 × max(|Q|, 1 W))
- bracket width converted to outlet-temperature effect <= 1e-4 K
- iterations <= 100

**Dynamic bracket:**
- Start from Q=0, construct Q_max from enthalpy reach limits, minimum allowable terminal ΔT, and temperature feasibility
- Counter-flow: both terminal ΔT must be positive
- Parallel-flow: hot outlet must be above cold outlet at exit
- If no sign change at bracket endpoints: deterministic interval probing
- If still no bracket: return SOLVER_BRACKET_NOT_FOUND blocker
- No infeasible endpoints sent to property library relying on exception escape

**Result must record:** converged, iterations, final residual, final bracket, tolerance configuration, termination reason

### Solver convergence contract

The solver enforces a formal convergence contract: all three conditions
(absolute residual, bracket temperature-effect, iteration limit) must be
satisfied simultaneously. The `EvaluationRecorder` captures every trial
evaluation with a continuous identity (monotonic counter + phase tag),
enabling deterministic replay and the evaluation identity verifier to
confirm no steps were skipped or duplicated.

### Blockers
- **Partial post-calculation BLOCKED with `converged=True`:** When a property
  or correlation evaluation fails after the solver has already converged (Q
  root-finding succeeded), the result emits `BLOCKED` status with
  `converged=True` that **preserves all diagnostic data collected so far**
  (evaluations, partial residuals, correlation applicability warnings).
  Debugging context is never lost even when the rating cannot complete.
- **Solver convergence vs engineering BLOCKED distinction:**
  - `converged=True, BLOCKED`: Solver found valid Q root; post-convergence
    property/correlation evaluation failed.
  - `converged=False, BLOCKED`: Solver itself could not converge.
  - `converged=False, FAILED`: Unrecoverable runtime error.
- Temperature crossover (hot outlet < cold outlet in counter-flow)
- Invalid property values (NaN, Infinity, negative)
- Correlation unavailable (including C4 implementation_unavailable)
- Solver non-convergence

### Result Model

- Deterministic SHA-256 result hash
- Provenance DAG with CALCULATION_RUN, CORRELATION, PROPERTY_CALL, RESULT nodes
- JSON round-trip (model_dump_json → model_validate_json)
- EngineeringMessage warnings and blockers with context

## C4 Behavior

If operating conditions require C4 (annulus laminar inner CHF):
- Return `implementation_unavailable` blocker from correlation selection
- Do NOT silently substitute other correlations
- Do NOT implement or guess C4 table data

## Geometry Request Model

Immutable, JSON round-trip capable. Fields:
- `inner_tube_inner_diameter_m` (m)
- `inner_tube_outer_diameter_m` (m)
- `outer_pipe_inside_diameter_m` (m)
- `heat_transfer_length_m` (m)
- `wall_thermal_conductivity` (W/m·K)
- `inner_roughness_m` (m, default 0)
- `outer_roughness_m` (m, default 0)
- `inner_fouling_resistance` (m²·K/W, default 0)
- `outer_fouling_resistance` (m²·K/W, default 0)
- `minimum_terminal_delta_t` (K, **required, no default**)
- `tube_boundary_condition` (str, **required, no default**)
- `annulus_boundary_condition` (str, **required, no default**)

Validation:
- 0 < D_i < D_o < D_outer
- L > 0
- k_wall > 0
- fouling >= 0

## Flow Side Mapping

Explicitly specify:
- Which fluid in inner tube
- Which fluid in annulus
- Which is designated hot side
- Which is designated cold side
- Flow arrangement: parallel or counter

No silent exchange based on inlet temperatures. If T_hot,in <= T_cold,in: return input blocker.

## Thermal Boundary Condition
- Both sides **must carry explicit boundary-condition policy** for laminar correlations — no silent defaults
- No silent selection between tube laminar CWT/CHF
- No substitution when annulus laminar C4 unavailable
- Any C4 scenario returns implementation_unavailable (Issue #19)

## Thermal Resistance Model

- A_i = π × D_i × L, A_o = π × D_o × L
- R_conv_i = 1 / (h_i × A_i)
- R_foul_i = Rf_i / A_i
- R_wall = ln(D_o / D_i) / (2π k_wall L)
- R_foul_o = Rf_o / A_o
- R_conv_o = 1 / (h_o × A_o)
- 1/UA = R_conv_i + R_foul_i + R_wall + R_foul_o + R_conv_o
- Output: UA, U_i = UA / A_i, U_o = UA / A_o
- Complete resistance breakdown with sum(components) == 1/UA
- All fouling resistance in m²·K/W with explicit area basis per side

## Iterative Property & Correlation Calls

Each residual evaluation:
1. Compute trial outlet enthalpies from Q
2. PropertyProvider: back-calculate outlet states from enthalpies
3. Establish representative bulk states for both sides
4. Call TASK-007 correlation service
5. Obtain: Re, Pr, Nu, h, selected correlation, applicability assessment, warnings/blockers
6. Recompute thermal resistance and UA
7. Compute LMTD and residual
Each evaluation is recorded by the `EvaluationRecorder` with a continuous
evaluation identity (monotonic counter + `SolverEvaluationPhase` tag) and
one of 7 `EvaluationRole` categories: `inlet`, `q_max_counterflow`,
`q_max_parallel_limits`, `q_max_parallel_pinch`, `bracket_probe`,
`solver_iteration`, `final_evaluation`. The evaluation identity verifier
confirms replay integrity. All PropertyProvider calls and correlation
selection enter provenance.

Representative bulk temperature: deterministic inlet/outlet bulk mean.

## Complete Result Model Fields

status, heat_duty, hot_outlet_state, cold_outlet_state, tube_side_outlet_state, annulus_side_outlet_state, tube_reynolds, tube_prandtl, tube_nusselt, tube_h, tube_selected_correlation, tube_applicability, annulus_reynolds, annulus_prandtl, annulus_nusselt, annulus_h, annulus_selected_correlation, annulus_applicability, area_inner, area_outer, resistance_breakdown, U_inner_basis, U_outer_basis, UA, C_hot, C_cold, C_min, C_max, capacity_ratio, NTU, effectiveness, LMTD, energy_residual, ua_lmtd_residual, iterations, converged, solver_termination_reason, warnings, blockers, property_provenance, provenance_graph, provenance_digest, result_hash

Must be immutable, deterministic, JSON round-trip, verify_hash(), verify_provenance().

## Structured Failure Paths

ErrorCode values:
- INVALID_DOUBLE_PIPE_GEOMETRY
- INVALID_FLOW_SIDE_ASSIGNMENT
- NON_POSITIVE_MASS_FLOW
- PROPERTY_EVALUATION_FAILED
- PHASE_NOT_SUPPORTED
- CORRELATION_NOT_FOUND
- CORRELATION_IMPLEMENTATION_UNAVAILABLE
- TEMPERATURE_CROSSING
- INVALID_LMTD
- SOLVER_BRACKET_NOT_FOUND
- SOLVER_NON_CONVERGENCE
- ENERGY_BALANCE_NOT_CLOSED

Reuse existing ErrorCode when available; no synonymous duplicates. Failed results also get deterministic hash and valid provenance.

## Test Matrix

| # | Test Case | Description |
|---|-----------|-------------|
| 1 | Counter-flow baseline | Known Q, verify outlet temperatures |
| 2 | Parallel-flow baseline | Known Q, verify outlet temperatures |
| 3 | Energy conservation | Q_hot == Q_cold within tolerance |
| 4 | ε-NTU / LMTD consistency | Both methods give same Q |
| 5 | Hot/cold side swap | Symbol consistency when sides are exchanged |
| 6 | Zero flow | Blocker returned |
| 7 | Temperature crossover | Blocker returned |
| 8 | Correlation unavailable | C4 metadata_only blocker |
| 9 | PropertyProvider failure | Structured error |
| 10 | Solver non-convergence | Blocker after max iterations |
| 11 | Source identity change | Different source → different result hash |
| 12 | Deterministic repeated run | Same input → same hash |
| 13 | JSON round-trip | Full model serialization |
| 14 | Provenance tamper | Tampered provenance fails verify |
| 15 | Golden case 1 | Hand-calc or literature reference |
| 16 | Golden case 2 | Hand-calc or literature reference |
| 17 | Golden case 3 | Hand-calc or literature reference |

## Exclusions (out of scope for TASK-008)

- Geometry sizing and candidate optimization → TASK-009
- API and formal reports → TASK-010
- C4 numerical implementation → Issue #19
- Two-phase flow
- Shell-and-tube, plate, air-cooled exchangers
- Mechanical design, material strength, cost
- Pressure drop models explicitly out of scope for TASK-008; see TASK-009 for sizing integration
