# TASK-008 — Fixed-geometry double-pipe rating

**Status:** IN_PROGRESS
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-003, TASK-005, TASK-006, TASK-007
**GitHub Issue:** #20
**Branch:** `codex/task-008-fixed-geometry-double-pipe-rating`
**Draft PR:** pending

## Objective

Perform rating analysis for a fixed-geometry double-pipe heat exchanger. Given operating conditions and fixed equipment parameters, compute duty, outlet temperatures, and key thermal-hydraulic metrics.

## Frozen Engineering Contracts

### Flow Arrangements

- **Supported:** Counter-flow, parallel-flow
- **Default assumption:** Counter-flow unless explicitly specified

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

- **Temperature strategy:** Film temperature T_f = (T_wall + T_bulk) / 2 for property evaluation
- **Fallback:** Bulk temperature if wall temperature unavailable

### Heat Transfer Coefficients

- **h_tube:** From tube-side correlation (TASK-007 C1/C2/C3)
- **h_annulus:** From annulus-side correlation (TASK-007 C4/C5)
- **U:** Overall coefficient based on outer surface of inner tube
- **UA:** U × A_outer
- **NTU:** UA / C_min
- **ε-NTU:** Standard effectiveness relations for counter/parallel flow
- **LMTD:** Log-mean temperature difference with correction factor F=1 for pure counter/parallel

### Solver Strategy

- **Outlet temperature:** Iterative solver using energy balance + heat transfer equations
- **Convergence tolerance:** ΔT < 1e-6 K for outlet temperatures
- **Maximum iterations:** 100
- **Method:** Bounded root-finding (Brent's method)

### Blockers

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
- Pressure drop models not confirmed by this task card
