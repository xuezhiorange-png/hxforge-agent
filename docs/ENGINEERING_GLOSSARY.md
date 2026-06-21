# HXForge Engineering Glossary

## Screening

A comparative assessment that identifies technically plausible exchanger families. Screening does not produce a fabrication-ready design.

## Sizing

A workflow that selects or generates geometry to satisfy a specified duty and constraints. Sizing returns one or more candidate designs.

## Rating

A workflow that evaluates the performance of a specified geometry under a specified operating condition.

## Operating condition

The expected process state used for thermal and hydraulic calculation.

## Design condition

The pressure and temperature basis used for preliminary mechanical boundaries. It is not automatically the same as the operating condition.

## Duty

The required or calculated rate of heat transfer, expressed in watts in the SI calculation core.

## Approach temperature

The smallest relevant hot-to-cold temperature difference for a defined exchanger arrangement.

## Temperature cross

A condition in which the cold outlet temperature exceeds the hot outlet temperature. It may be physically possible in counterflow service but must be checked against effectiveness and terminal-temperature constraints.

## LMTD

Log mean temperature difference for a defined flow arrangement. Correction factors, phase regions and segmented calculations must be handled explicitly.

## Allowable pressure drop

The maximum pressure loss permitted by the user or process design on one side of the exchanger.

## Calculated pressure drop

The pressure loss predicted by the selected model, including only the components explicitly represented by that model.

## Fouling resistance

An added thermal resistance representing expected deposit formation. It must include units, source and applicability.

## Area margin

The fractional excess of selected heat-transfer area above the calculated required area.

## Preliminary mechanical design

An early estimate of mechanical boundaries used for comparison or feasibility. It is not a code-stamped pressure-vessel design.

## Code compliance

A conclusion that requires licensed rules, complete design inputs, qualified review and applicable statutory processes. HXForge must not claim compliance from preliminary calculations alone.

## Candidate

A discrete, manufacturable design option with geometry, performance, warnings and provenance.

## Recommendation

A ranked candidate accompanied by the ranking criteria, trade-offs, warnings and residual uncertainties.

## Warning

A non-fatal condition that may affect confidence, applicability or downstream decisions.

## Blocker

A condition that prevents a valid recommendation or calculation result.

## Provenance

The traceable record of inputs, software version, property backend, formula IDs, applicability checks, intermediate values and outputs.
## Extended Engineering Terms

### Test condition
The pressure and temperature basis used for pressure testing or leak testing of the completed exchanger. It is neither the operating condition nor the design condition, and must be specified separately when test requirements apply.

### Mass flow rate vs volumetric flow rate
The mass flow rate (kg/s in SI) is the mass of fluid passing a cross-section per unit time. Volumetric flow rate (m³/s in SI) is the volume of fluid passing a cross-section per unit time and varies with fluid density. Public inputs accept either form, but the internal calculation kernel normalizes to mass flow rate.

### Heat-transfer area vs frontal area
Heat-transfer area (m²) is the wetted surface available for thermal exchange. Frontal area (m²) is the face area through which a fluid approaches a heat-exchanger surface, relevant for air-side and cross-flow equipment. These dimensions must not be confused.

### Fouling resistance vs conduction resistance
The conduction resistance (m²·K/W per unit thickness) represents the thermal resistance of the tube wall or plate material. Fouling resistance and conduction resistance are additive components of the total thermal resistance and must be tracked separately in provenance.

### Effectiveness (ε)
The heat-transfer effectiveness, defined as the ratio of actual duty to the maximum possible duty for the given inlet states. Used in the ε-NTU method as an alternative to LMTD.

### NTU
Number of Transfer Units: a dimensionless measure of heat-transfer capability, defined as UA/C_min where U is the overall heat-transfer coefficient and C_min is the minimum heat-capacity rate.

### Reynolds number (Re)
The dimensionless ratio of inertial forces to viscous forces. It determines the flow regime (laminar, transition, turbulent) and is required for correlation applicability checks.

### Prandtl number (Pr)
The dimensionless ratio of momentum diffusivity to thermal diffusivity. It relates the velocity and thermal boundary layers and is required for convective heat-transfer correlations.

### Nusselt number (Nu)
The dimensionless convective heat-transfer coefficient, defined as hD/k where h is the convective coefficient, D is the characteristic length, and k is the fluid thermal conductivity.

### Friction factor
The dimensionless factor relating pressure drop to flow velocity. Darcy (Darcy-Weisbach) friction factor f is used in HXForge. The Fanning friction factor f_F = f/4 must not be confused with it. Every correlation must declare which definition it uses.

### Hydraulic diameter
A characteristic length for non-circular ducts, defined as 4A/P where A is the cross-sectional area and P is the wetted perimeter. Used to apply circular-tube correlations to annuli and other geometries.

### Applicability envelope
The set of conditions (Reynolds range, Prandtl range, geometry limits, roughness limits, phase, fluid type) under which a registered correlation is considered valid. Input outside the envelope triggers a WARNING, REJECTED status, or BLOCKED result according to the correlation's over-range policy.

### Overall heat-transfer coefficient (U)
The composite thermal conductance per unit area (W/m²·K) combining all series thermal resistances: hot-side convection, wall conduction, cold-side convection, and fouling. Must not be assumed or guessed.

### Hairpin
A U-shaped double-pipe heat exchanger element consisting of two parallel tube runs connected by a return bend. Multiple hairpins may be connected in series or parallel to form a complete exchanger.

### Annulus
The annular space between the inner tube outer surface and the outer tube inner surface in a double-pipe or concentric arrangement. The annulus carries one of the two process fluids.
