# Single-Phase Tube and Annulus Heat-Transfer Correlations

## Overview

TASK-007 implements deterministic, source-traceable single-phase convective
heat-transfer correlation evaluation for circular tubes and concentric annuli.

## Supported Geometry Types

| Geometry | Model | Description |
|----------|-------|-------------|
| `circular_tube` | `CircularTubeGeometry` | Single enclosed cylindrical flow passage |
| `concentric_annulus` | `ConcentricAnnulusGeometry` | Annular gap between inner tube OD and outer pipe ID |

## Correlation Matrix

| ID | Geometry | Regime | Boundary | Nu Equation | Source | Status |
|----|----------|--------|----------|-------------|--------|--------|
| `tube_laminar_cwt` | tube | laminar | const T wall | Nu = 3.66 | Incropera 7th ed. Table 8.1 | validated |
| `tube_laminar_chf` | tube | laminar | const q" | Nu = 4.36 | Incropera 7th ed. Table 8.1 | validated |
| `tube_turbulent_gnielinski` | tube | turbulent | both | Gnielinski (1976) | Int. Chem. Eng. Vol. 16 | validated |
| `annulus_laminar_inner_chf` | annulus | laminar | inner heated | Kays Table 9-1 interp. | Kays & Crawford 3rd ed. Ch. 9, Table 9-1 | **metadata_only / unverified** |
| `annulus_turbulent_gnielinski_dh` | annulus | turbulent | both (adaptation) | Gnielinski with D_h | Kays & Crawford Ch. 10 (unverified) | implemented / unverified |

## Equations

### Tube Laminar (C1, C2)

Fully developed, constant properties:

- CWT: **Nu_D = 3.66**
- CHF: **Nu_D = 4.36**

### Tube Turbulent — Gnielinski (C3)

```
Nu_D = (f/8)(Re_D - 1000)Pr / [1 + 12.7√(f/8)(Pr^{2/3} - 1)]
```

Friction factor (Petukhov, 1970):
```
f = (0.790 ln Re - 1.64)^{-2}
```

### Annulus Laminar (C4) — DEFERRED / metadata_only

**Status:** metadata_only / unverified. The correlation is structurally present
but all numeric data is pending independent engineer verification from the
authoritative source:

- **Source:** Kays, W.M., Crawford, M.E., "Convective Heat and Mass Transfer,"
  3rd Edition, McGraw-Hill, 1993, **Chapter 9, Table 9-1**.
- **Characteristic length:** Hydraulic diameter D_h (NOT inner tube OD D_i).
- **Boundary conditions:** Inner wall heated, outer insulated.
- **Data:** Not yet extracted from the verified table. The previously implemented
  values (4.85, 5.70, 7.30, 10.10) referenced "Table 8-2" and used D_i basis —
  both were **INCORRECT** per independent reviewer check.
- **Status:** C4 is blocked at the selection layer by `implementation_status=metadata_only`.
  The service returns `NOT_IMPLEMENTED` before calling `evaluate()`.
  No diameter_ratio NumericBound is registered (placeholder κ bounds [0.1, 0.75]
  removed because they are unverified).
- **Remaining work:** C4 complete implementation is deferred to a follow-up task.

### Annulus Turbulent (C5)

Hydraulic-diameter adaptation of Gnielinski. Explicitly marked as adaptation.

**Source verification:** unverified. The Kays & Crawford 3rd ed. Ch. 10 citation
for hydraulic-diameter approximation has NOT been independently verified for this
specific annulus adaptation.

**Characteristic length basis:** D_h (hydraulic diameter).

## Symbols and Units

| Symbol | Description | SI Unit |
|--------|-------------|---------|
| Re | Reynolds number | — |
| Pr | Prandtl number | — |
| Nu | Nusselt number | — |
| D_h | Hydraulic diameter | m |
| v | Mean velocity | m/s |
| h | Heat-transfer coefficient | W/(m²·K) |
| κ | Diameter ratio (D_i/D_o) | — |

## Validity Envelopes

| Correlation | Re range | Pr range | κ range | Notes |
|-------------|----------|----------|---------|-------|
| C1 | (0, 2300) | (0.6, ∞) | N/A | Fully developed |
| C2 | (0, 2300) | (0.6, ∞) | N/A | Fully developed |
| C3 | (3000, 5×10⁶) | (0.5, 2000) | N/A | |
| C4 | (0, 2300) | (0.6, ∞) | TBD (metadata_only) | Inner wall heated, D_h basis, BLOCKED |
| C5 | (3000, 5×10⁶) | (0.5, 2000) | (0, 1) | D_h adaptation, unverified |

## Transition Policy

Transitional flow (2300 ≤ Re ≤ 10000) is **BLOCKED**.
Returns structured blocker with actual Re and transition bounds.

## Selection Rules

1. Filter by applicability (geometry, regime, boundary condition) via `InMemoryCorrelationRegistry.assess_applicability()`
2. Metadata-only definitions (C4) are blocked at the selection layer before entering the evaluator
3. Sort by: priority (desc), correlation_id (asc), version (desc — via `compare_semver()`)
4. First candidate wins
5. If no candidate: BLOCKED with `CORRELATION_NOT_FOUND` or specific applicability blocker
6. Order-independent: different insertion orders produce same selection
7. Selection is registry-backed — all 5 correlations registered with applicability metadata
8. Failed applicability assessments are preserved in `rejected_candidates`

## Boundary Condition Validation

All boundary conditions are **typed** via `ThermalBoundaryCondition` StrEnum.
The public API accepts `ThermalBoundaryCondition | str` and converts at the
domain boundary. The domain layer operates on enum values exclusively.
Invalid strings return structured BLOCKER with `CORRELATION_GEOMETRY_INCOMPATIBLE`.

Annulus boundary conditions (inner_wall_heated, outer_wall_heated, both_walls_heated) are
distinguished from tube conditions (constant_wall_temperature, constant_heat_flux).
heated_surface vs BC consistency is enforced at input time.

## Hash Integrity

- `result_hash` is computed over all public fields **excluding itself** (no self-referential hash).
- `verify_hash()` validates hash and, if present, `ApplicabilityAssessment.verify_assessment_hash()`.
- `ApplicabilityAssessment` stores an `identity_snapshot` enabling hash recomputation and verification.
- Source identity: `SelectedCorrelationInfo` populated from `CorrelationDefinition` metadata.

## Provenance

### Nodes

- Root: EXTERNAL or CASE_REVISION (exactly one)
- CALCULATION_RUN: exactly one, with full execution context
- CORRELATION: exactly one (if SUCCEEDED), absent (if BLOCKED)
- WARNING/BLOCKER: match result messages exactly (code, message, source_module, allows_continuation)
- RESULT: exactly one

### Edges

- root → CALCULATION_RUN: "triggers"
- CALCULATION_RUN → CORRELATION: "uses" (if present)
- CALCULATION_RUN → WARNING: "emits" (per warning)
- CALCULATION_RUN → BLOCKER: "emits" (per blocker)
- CALCULATION_RUN → RESULT: "produces"

### Verification

`verify_provenance()` validates:
1. Graph digest matches provenance_digest
2. Node IDs are unique
3. Edge triples (source, target, relation) are unique
4. Edge endpoints reference existing nodes
5. No self-loops
6. Graph is a DAG
7. Each node's payload_hash can be recomputed and matches
8. Each node's UUID5 can be recomputed and matches
9. Root node type matches execution context
10. Exactly one CALCULATION_RUN
11. CORRELATION node identity matches selected definition (ID, version, definition_hash, source_title, nusselt_basis)
12. WARNING/BLOCKER nodes match result messages exactly
13. RESULT node matches result status
14. Exact topology: expected node types and edge set match exactly

## Wall-Property Policy

- Laminar correlations: no wall properties required
- Turbulent correlations: no viscosity correction (Sieder-Tube not in scope)
- Missing wall property for a correlation that requires it → BLOCKER

## Limitations

- Annulus laminar (C4) is **metadata_only** — deferred pending source verification.
- Annulus turbulent (C5) is a hydraulic-diameter adaptation, not an original
  annulus correlation. May underpredict for asymmetric heating. Source unverified.
- Fully developed assumption for laminar correlations.
- No developing-flow correction implemented.
- No Sieder-Tube viscosity correction.

## Unsupported Cases

- Transitional flow
- Two-phase, boiling, condensation
- Non-circular cross-sections other than annulus
- Finned surfaces, microchannels
- Pressure drop (friction factor is intermediate only)
