# TASK-007 — Single-phase tube and concentric-annulus heat-transfer correlations

**Status:** DONE
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-003, TASK-004, TASK-006
**GitHub Issue:** #17 (scope updated: C4 deferred)
**C4 Follow-up:** #19
**Branch:** `codex/task-007-tube-annulus-correlations`
**PR:** #18 (merged — merge commit `493c0b7618ddc9e14684d370eb64e1709cf8d56f`)
**Final CI:** 28013648275 (Python 3.11 + 3.12 success)
**Tests:** 1154 passed

## Objective

Implement a deterministic, source-traceable single-phase convective heat-transfer correlation kernel for circular tubes and concentric annuli. Provide laminar and turbulent Nusselt correlations with full applicability envelopes, provenance, and deterministic hashing.

**C4 scope note:** C4 (annulus laminar inner CHF) is deferred from TASK-007 per engineering review. C4 is delivered as metadata_only with structured maturity blocker. Full numerical implementation is tracked in Issue #19.

## Frozen Correlation Matrix

### Geometry Types

| ID | Geometry | Description |
|----|----------|-------------|
| `circular_tube` | Circular tube | Single enclosed cylindrical flow passage |
| `concentric_annulus` | Concentric annulus | Annular gap between inner tube OD and outer pipe ID |

### Thermal Boundary Conditions

| ID | Description |
|----|-------------|
| `constant_wall_temperature` | Uniform wall temperature (T = const) |
| `constant_heat_flux` | Uniform wall heat flux (q" = const) |
| `inner_wall_heated` | Inner wall heated, outer insulated (annulus) |
| `outer_wall_heated` | Outer wall heated, inner insulated (annulus) |
| `both_walls_heated` | Both walls heated equally (annulus) |

### Regime Thresholds (frozen)

| Parameter | Value | Source |
|-----------|-------|--------|
| Laminar upper bound | Re < 2300 | Incropera & DeWitt, 7th ed., Ch. 8 |
| Turbulent lower bound | Re > 10000 | Incropera & DeWitt, 7th ed., Ch. 8 |
| Transitional zone | 2300 ≤ Re ≤ 10000 | BLOCKED (see transition policy) |

### Frozen Correlations

#### C1: Tube Laminar — Constant Wall Temperature

- **Correlation ID:** `tube_laminar_cwt`
- **Version:** `1.0.0`
- **Source:** Incropera, F.P., DeWitt, D.P., Bergman, T.L., Lavine, A.S., "Fundamentals of Heat and Mass Transfer," 7th Edition, Wiley, 2011, Table 8.1.
- **Equation:** Nu_D = 3.66 (fully developed, constant wall temperature)
- **Geometry:** circular_tube
- **Flow regime:** laminar (Re < 2300)
- **Boundary condition:** constant_wall_temperature
- **Reynolds range:** (0, 2300)
- **Prandtl range:** (0.6, ∞)
- **Diameter ratio:** N/A
- **Development length:** Assumes hydrodynamically and thermally fully developed
- **Wall property requirements:** None (no viscosity correction)
- **Heating/cooling:** Both
- **Priority:** 10

#### C2: Tube Laminar — Constant Heat Flux

- **Correlation ID:** `tube_laminar_chf`
- **Version:** `1.0.0`
- **Source:** Incropera et al., 7th ed., Table 8.1.
- **Equation:** Nu_D = 4.36 (fully developed, constant heat flux)
- **Geometry:** circular_tube
- **Flow regime:** laminar (Re < 2300)
- **Boundary condition:** constant_heat_flux
- **Reynolds range:** (0, 2300)
- **Prandtl range:** (0.6, ∞)
- **Diameter ratio:** N/A
- **Development length:** Assumes hydrodynamically and thermally fully developed
- **Wall property requirements:** None
- **Heating/cooling:** Both
- **Priority:** 10

#### C3: Tube Turbulent — Gnielinski

- **Correlation ID:** `tube_turbulent_gnielinski`
- **Version:** `1.0.0`
- **Source:** Gnielinski, V., "New Equations for Heat and Mass Transfer in Turbulent Pipe and Channel Flow," International Chemical Engineering, Vol. 16, No. 2, pp. 359-368, 1976.
- **Equation:** Nu_D = (f/8)(Re_D - 1000)Pr / [1 + 12.7(f/8)^0.5(Pr^(2/3) - 1)]
- **Friction factor (internal):** Petukhov: f = (0.790 ln(Re) - 1.64)^(-2), source: Petukhov, B.S., "Heat Transfer and Friction in Turbulent Pipe Flow," Advances in Heat Transfer, Vol. 6, Academic Press, 1970.
- **Geometry:** circular_tube
- **Flow regime:** turbulent (3000 ≤ Re ≤ 5×10^6) — note: Gnielinski valid from 3000, extending effective range
- **Boundary condition:** constant_heat_flux and constant_wall_temperature
- **Reynolds range:** (3000, 5×10^6)
- **Prandtl range:** (0.5, 2000)
- **Diameter ratio:** N/A
- **Development length:** Assumes hydrodynamically developed; thermally developing allowed via Graetz correction NOT implemented (conservative)
- **Wall property requirements:** None (Sieder-Tube viscosity correction NOT included)
- **Heating/cooling:** Both
- **Priority:** 10

#### C4: Annulus Laminar — Inner Wall Heated, Outer Insulated

- **Correlation ID:** `annulus_laminar_inner_chf`
- **Version:** `1.0.0`
- **Source:** Kays, W.M., Crawford, M.E., "Convective Heat and Mass Transfer," 3rd Edition, McGraw-Hill, 1993, **Chapter 9, Table 9-1** (NOT Table 8-2).
- **Status:** **metadata_only / unverified** — data pending independent engineer verification.
- **Characteristic length basis:** Hydraulic diameter D_h (NOT inner tube OD D_i).
- **Previously incorrect claims (corrected in Round 2/3):**
  - Table 8-2 → Table 9-1 (Chapter 9, not Chapter 8)
  - D_i basis → D_h basis
  - Values 4.85, 5.70, 7.30, 10.10 → NOT verified, removed
  - κ range [0.1, 0.75] → removed (unverified bounds)
- **Diameter ratio range:** TBD — no NumericBound registered; blocked by implementation_status=metadata_only
- **Implementation:** Blocked at selection layer before evaluator is called. Service returns NOT_IMPLEMENTED.
- **Remaining work:** C4 complete implementation is deferred to a follow-up task.

#### C5: Annulus Turbulent — Hydraulic Diameter Adaptation of Gnielinski

- **Correlation ID:** `annulus_turbulent_gnielinski_dh`
- **Version:** `1.0.0`
- **Source:** Kays & Crawford, 3rd ed., Ch. 10: "For turbulent flow in non-circular ducts, the hydraulic diameter provides a reasonable approximation." Adapted from Gnielinski (1976) with D replaced by D_h.
- **Equation:** Nu_h = (f/8)(Re_h - 1000)Pr / [1 + 12.7(f/8)^0.5(Pr^(2/3) - 1)]
  - Re_h = ρ v D_h / μ
  - D_h = 4A / P_wetted
  - f = Petukhov friction factor using Re_h
- **Metadata:** This is an **adaptation** — explicitly marked as such. Not an original annulus correlation. Has limitation warning.
- **Geometry:** concentric_annulus
- **Flow regime:** turbulent (Re_h > 10000)
- **Boundary condition:** All (with limitation warning for annulus-specific effects)
- **Reynolds range:** (10000, 5×10^6) based on D_h
- **Prandtl range:** (0.5, 2000)
- **Characteristic length basis:** D_h (hydraulic diameter)
- **Diameter ratio range:** (0, 1) exclusive
- **Development length:** Assumes developed
- **Wall property requirements:** None
- **Heating/cooling:** Both
- **Priority:** 5 (lower priority due to adaptation status)
- **Limitation:** "Hydraulic-diameter approximation may underpredict heat transfer for highly asymmetric heating in annuli with large diameter ratios. Consult Kays & Crawford for corrections."

### Transition Policy

- **Status:** BLOCKED
- **Code:** `UNSUPPORTED_FLOW_REGIME`
- **Message:** "Transitional flow (2300 ≤ Re ≤ 10000) is not supported. Specify laminar (Re < 2300) or turbulent (Re > 10000)."
- **Output:** Actual Re, transition bounds, candidate correlation IDs

### Applicability Handling (Registry-Backed — Mandatory)

Each correlation is registered in `InMemoryCorrelationRegistry` and goes through
`assess_applicability()`. All 5 correlations must be registered with full applicability
metadata. The `OutOfRangePolicy` is:
- `absolute_violation`: BLOCKER
- `recommended_violation`: WARNING
- `missing_input`: BLOCKER
- `incompatible_geometry`: BLOCKER
- `incompatible_phase`: BLOCKER
- `incompatible_flow_regime`: BLOCKER

### Deterministic Selection Rules

1. Filter by applicability status (only `applicable` or `recommended_range_exceeded`)
2. Geometry exact match
3. Boundary-condition exact match (typed validation, not string comparison)
4. Approved priority (higher = preferred)
5. Correlation ID (alphabetical tiebreak)
6. Version (highest wins, parsed via `parse_semver`/`compare_semver`)

If ambiguous after all keys: return structured ambiguity blocker.

### Typed Boundary Condition Validation

All boundary conditions are validated via typed Pydantic models at input time.
Annulus conditions (inner_wall_heated, outer_wall_heated, both_walls_heated) are
distinguished from tube conditions (constant_wall_temperature, constant_heat_flux).
heated_surface vs BC consistency is enforced — no silent fallback to string matching.

### Hash Integrity

- `result_hash` is computed over all public fields **excluding itself** (no self-referential hash).
- `verify_provenance()` recomputes and validates the hash against the stored digest.
- Source identity: `SelectedCorrelationInfo` populated from `CorrelationDefinition` metadata.

### Wall-Property Policy

- Laminar correlations (C1, C2, C4): No wall properties required
- Turbulent correlations (C3, C5): No viscosity correction implemented (Sieder-Tube not in scope)
- If a future correlation requires (μ_bulk/μ_wall)^n, wall viscosity must be explicitly provided
- Missing wall property → applicability BLOCKER, not default correction = 1

### Output Contract

The result model `CorrelationResult` is a frozen Pydantic model with:
- `status`: SUCCEEDED / BLOCKED / FAILED
- `geometry`: CircularTubeGeometry or ConcentricAnnulusGeometry
- `flow_properties`: FlowPropertiesInput
- `regime`: FlowRegime
- `selected_correlation`: SelectedCorrelationInfo
- `nusselt_number`: float
- `heat_transfer_coefficient`: float
- `reynolds_number`: float
- `prandtl_number`: float
- `applicability`: ApplicabilityAssessment
- `warnings`: tuple[EngineeringMessage, ...]
- `blockers`: tuple[EngineeringMessage, ...]
- `failure`: RunFailure | None
- `result_hash`: str ("sha256:<64 hex>")
- `provenance_graph`: ProvenanceGraph
- `provenance_digest`: str
- `execution_context`: ExecutionContextSnapshot
- `_field_hash`: PrivateAttr for tamper detection

### Provenance Identity

- Root node: EXTERNAL (no design_case_revision in this scope) or CASE_REVISION
- CORRELATION_RUN node (new type, analogous to CALCULATION_RUN)
- CORRELATION node for selected correlation
- PROPERTY_CALL nodes for any property evaluations
- WARNING/BLOCKER nodes
- RESULT node
- Deterministic UUID5 for each node
- Full provenance graph verification via `verify_provenance()`: graph digest, node/edge uniqueness, DAG validation, payload hash recomputation

### Exclusions (out of scope for TASK-007)

- TASK-008 rating, sizing, optimization
- Pressure drop (friction factor is intermediate only)
- Overall heat transfer coefficient U
- LMTD, ε-NTU (already in thermal.py, not part of this correlation kernel)
- Fouling
- Two-phase flow
- Finned surfaces, microchannels
- Database, API, report generation

## Test Categories

### Geometry tests
- tube area/perimeter/Dh
- annulus area/perimeters/Dh
- diameter ratio
- equal diameters (D_outer == D_inner → BLOCKED)
- reversed diameters (D_outer < D_inner → BLOCKED)
- zero/negative/non-finite dimensions
- very small valid gap

### Dimensionless tests
- velocity, Re, Pr, h
- zero/negative/non-finite properties
- zero mass flow

### Regime boundary tests
- Re = 2299 (just below laminar upper)
- Re = 2300 (exact boundary)
- Re = 2301 (transitional → BLOCKED)
- Re = 9999 (transitional → BLOCKED)
- Re = 10000 (exact turbulent lower)
- Re = 10001 (just above)

### Correlation reference cases
Each correlation: independent hand-crafted Nu value, expected h, valid-range nominal, each applicability boundary, missing wall property, boundary-condition mismatch, geometry mismatch

### Selection determinism
- registry order variation
- equivalent JSON round-trip
- ambiguous candidates
- version change → hash change
- source change → hash change

### Structured failure
- invalid geometry
- transitional unsupported
- Re out of range
- Pr out of range
- diameter ratio out of range
- unsupported boundary condition
- no applicable correlation
- ambiguous correlations

### Integrity
- public result immutable
- direct __setattr__ tamper tests
- provenance node/edge duplicate, missing, extra
- correlation metadata tamper
- execution context tamper
- JSON round-trip hash/provenance verification
