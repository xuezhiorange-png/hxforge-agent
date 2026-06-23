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

| ID | Geometry | Regime | Boundary | Nu Equation | Source |
|----|----------|--------|----------|-------------|--------|
| `tube_laminar_cwt` | tube | laminar | const T wall | Nu = 3.66 | Incropera 7th ed. Table 8.1 |
| `tube_laminar_chf` | tube | laminar | const q" | Nu = 4.36 | Incropera 7th ed. Table 8.1 |
| `tube_turbulent_gnielinski` | tube | turbulent | both | Gnielinski (1976) | Int. Chem. Eng. Vol. 16 |
| `annulus_laminar_inner_chf` | annulus | laminar | inner heated | Kays table interp. | Kays & Crawford 3rd ed. Table 8-2 |
| `annulus_turbulent_gnielinski_dh` | annulus | turbulent | both (adaptation) | Gnielinski with D_h | Kays & Crawford Ch. 10 |

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

### Annulus Laminar (C4)

Nu_i interpolated from Kays & Crawford Table 8-2 for inner wall heated,
outer insulated, as a function of diameter ratio κ = D_i/D_o.

**Characteristic length basis:** D_i (inner tube outer diameter), NOT D_h.
Heat-transfer coefficient: h = Nu_i · k / D_i.

**κ range (frozen):** [0.1, 0.75] inclusive — verified data only, no extrapolation.

### Annulus Turbulent (C5)

Hydraulic-diameter adaptation of Gnielinski. Explicitly marked as adaptation.

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
| C4 | (0, 2300) | (0.6, ∞) | [0.1, 0.75] | Inner wall heated, D_i basis |
| C5 | (10000, 5×10⁶) | (0.5, 2000) | (0, 1) | D_h adaptation |

## Transition Policy

Transitional flow (2300 ≤ Re ≤ 10000) is **BLOCKED**.
Returns structured blocker with actual Re and transition bounds.

## Selection Rules

1. Filter by applicability (geometry, regime, boundary condition) via `InMemoryCorrelationRegistry.assess_applicability()`
2. Sort by: priority (desc), correlation_id (asc), version (desc)
3. First candidate wins
4. If no candidate: BLOCKED with `CORRELATION_NOT_FOUND`
5. Order-independent: different insertion orders produce same selection
6. Selection is registry-backed — all 5 correlations registered with applicability metadata

## Boundary Condition Validation

All boundary conditions are **typed** — validated via Pydantic models, not string matching.
Annulus boundary conditions (inner_wall_heated, outer_wall_heated, both_walls_heated) are
distinguished from tube conditions. heated_surface vs BC consistency is enforced at input time.

## Hash Integrity

- `result_hash` is computed over all public fields **excluding itself** (no self-referential hash).
- Hash recomputation via `verify_provenance()` validates against the stored digest.

## Wall-Property Policy

- Laminar correlations: no wall properties required
- Turbulent correlations: no viscosity correction (Sieder-Tube not in scope)
- Missing wall property for a correlation that requires it → BLOCKER

## Limitations

- Annulus turbulent (C5) is a hydraulic-diameter adaptation, not an original
  annulus correlation. May underpredict for asymmetric heating.
- Fully developed assumption for laminar correlations.
- No developing-flow correction implemented.
- No Sieder-Tube viscosity correction.

## Provenance Identity

- Root: EXTERNAL or CASE_REVISION
- CALCULATION_RUN: correlation evaluation run
- CORRELATION: selected correlation identity
- WARNING/BLOCKER: any messages
- RESULT: final result
- Full graph verification via `verify_provenance()`: graph digest, node/edge uniqueness, DAG validation, payload hash recomputation

## Unsupported Cases

- Transitional flow
- Two-phase, boiling, condensation
- Non-circular cross-sections other than annulus
- Finned surfaces, microchannels
- Pressure drop (friction factor is intermediate only)
