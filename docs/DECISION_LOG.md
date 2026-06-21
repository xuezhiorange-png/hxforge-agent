# HXForge Engineering Decision Log

This log records product and engineering decisions that affect schemas, defaults, calculations, warnings or compliance language. Coding tools must not convert a proposed item into code behavior until its status is `APPROVED`.

Status values: `PROPOSED`, `APPROVED`, `REJECTED`, `SUPERSEDED`.

| ID | Decision | Status | Owner | Rationale / consequence |
|---|---|---|---|---|
| DEC-001 | The first complete calculation vertical slice is single-phase double-pipe / hairpin service. | PROPOSED | Engineering owner | Limits early validation scope and proves the full input-to-report workflow before adding more exchanger families. |
| DEC-002 | Shell-and-tube and plate exchangers may appear in v0.1 screening before their detailed sizing/rating solvers are complete. | PROPOSED | Engineering owner | Allows technology comparison without falsely claiming validated detailed calculations. |
| DEC-003 | Condensation, evaporation and other two-phase services return `NOT_IMPLEMENTED` until approved correlations and validation cases are merged. | PROPOSED | Engineering owner | Prevents unvalidated refrigerant calculations from being presented as engineering results. |
| DEC-004 | Public engineering inputs never use hidden numerical defaults. Values such as fouling resistance, area margin, roughness, material, cost basis and corrosion allowance must be provided or explicitly selected from an approved rule set. | PROPOSED | Engineering owner | Makes assumptions visible and traceable. |
| DEC-005 | The deterministic calculation core uses SI units; API and reports may convert to user-selected display units. Absolute temperature and temperature difference are separate dimensions. | PROPOSED | Engineering owner | Avoids unit ambiguity and offset-temperature errors. |
| DEC-006 | Result states include `VALIDATED_INPUT`, `PRELIMINARY`, `REVIEW_REQUIRED`, `BLOCKED`, `NOT_IMPLEMENTED` and `VERIFIED`. | PROPOSED | Engineering + product owner | Separates successful computation from engineering approval and implementation availability. |
| DEC-007 | HXForge never claims certified ASME, TEMA, API or statutory compliance from preliminary calculations. | PROPOSED | Engineering owner | Code compliance requires licensed rules, complete inputs, qualified review and applicable legal processes. |
| DEC-008 | Every numerical output must include calculation provenance and structured warnings. | PROPOSED | Engineering + software owner | Supports reproducibility, review and regression control. |
| DEC-009 | Candidate generation is limited to approved, manufacturable catalog geometry; continuous optimization cannot invent arbitrary procurement dimensions. | PROPOSED | Engineering owner | Keeps optimized designs buildable and comparable. |
| DEC-010 | A blocking input, safety, property or applicability error prevents candidate recommendation and report-ready status. | PROPOSED | Engineering owner | Prevents the Agent from forcing a result through an invalid workflow. |
| DEC-011 | CoolProp is the first and default property backend for v0.1. Alternative backends (REFPROP, custom databases) are architecture-ready but not implemented in v0.1. | PROPOSED | Engineering owner | Limits property validation scope to one well-documented open-source backend while proving the injectable-provider interface. |
| DEC-012 | For single-phase correlations, the transition Reynolds-number zone (typically 2300 < Re < 10000 for internal flow) must use an explicit, documented policy: interpolation with WARNING, or rejection. Blind interpolation without provenance is prohibited. | PROPOSED | Engineering owner | Prevents silent extrapolation into unvalidated flow regimes. The specific policy (interpolate vs reject) must be chosen and documented before TASK-007. |
| DEC-013 | The double-pipe geometry catalog is maintained as a versioned YAML file. Each entry specifies standard pipe OD, wall thickness, schedule, and maximum hairpin length. Continuous optimization may only select from catalog entries. | PROPOSED | Engineering owner | Ensures manufactured dimensions are procurable. |
| DEC-014 | Iterative solvers must declare a maximum iteration count and a convergence tolerance before execution. Default tolerance: energy balance residual < 0.1%. Default max iterations: 100. Both are configurable and traceable. | PROPOSED | Engineering owner | Prevents infinite loops and silent non-convergence. |
| DEC-015 | In sizing workflows, the area margin is applied to the generated candidate geometry (design area = required area × (1 + margin)). In rating workflows, the margin is reported as informational only and does not modify the calculation. | PROPOSED | Engineering owner | Makes the role of area margin explicit and consistent across workflows. |
| DEC-016 | The v0.1 supported fluid list is: Water, Air, R134a, R404A (or R507A), R717, and Propylene Glycol water solution (if backend support is confirmed). Fluids outside this list are supported architecturally but return NOT_IMPLEMENTED until validated. | PROPOSED | Engineering owner | Defines the property-validation scope for the first release. |
| DEC-017 | The fouling_resistance source field is a free-text reference string (e.g., 'TEMA Table RGP-T-2.4 clean service' or 'user-specified'). When fouling resistance is zero, the source must still state 'explicitly zero — no fouling assumed' to confirm deliberate choice. | PROPOSED | Engineering owner | Makes zero-fouling assumptions visible and traceable. |

### DEC-011 — CoolProp is the first and default property backend for v0.1

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** CoolProp is the first and default property backend for v0.1. Alternative backends (REFPROP, custom databases) are architecture-ready but not implemented in v0.1.

**Rationale / consequence:** Limits property validation scope to one well-documented open-source backend while proving the injectable-provider interface.

---

### DEC-012 — Transition Reynolds-number zone policy for single-phase correlations

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** For single-phase correlations, the transition Reynolds-number zone (typically 2300 < Re < 10000 for internal flow) must use an explicit, documented policy: interpolation with WARNING, or rejection. Blind interpolation without provenance is prohibited.

**Rationale / consequence:** Prevents silent extrapolation into unvalidated flow regimes. The specific policy (interpolate vs reject) must be chosen and documented before TASK-007.

---

### DEC-013 — Double-pipe geometry catalog as versioned YAML

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** The double-pipe geometry catalog is maintained as a versioned YAML file. Each entry specifies standard pipe OD, wall thickness, schedule, and maximum hairpin length. Continuous optimization may only select from catalog entries.

**Rationale / consequence:** Ensures manufactured dimensions are procurable.

---

### DEC-014 — Iterative solver iteration and tolerance defaults

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** Iterative solvers must declare a maximum iteration count and a convergence tolerance before execution. Default tolerance: energy balance residual < 0.1%. Default max iterations: 100. Both are configurable and traceable.

**Rationale / consequence:** Prevents infinite loops and silent non-convergence.

---

### DEC-015 — Area margin behavior in sizing vs rating workflows

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** In sizing workflows, the area margin is applied to the generated candidate geometry (design area = required area × (1 + margin)). In rating workflows, the margin is reported as informational only and does not modify the calculation.

**Rationale / consequence:** Makes the role of area margin explicit and consistent across workflows.

---

### DEC-016 — v0.1 supported fluid list

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** The v0.1 supported fluid list is: Water, Air, R134a, R404A (or R507A), R717, and Propylene Glycol water solution (if backend support is confirmed). Fluids outside this list are supported architecturally but return NOT_IMPLEMENTED until validated.

**Rationale / consequence:** Defines the property-validation scope for the first release.

---

### DEC-017 — Fouling resistance source field traceability

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** The fouling_resistance source field is a free-text reference string (e.g., 'TEMA Table RGP-T-2.4 clean service' or 'user-specified'). When fouling resistance is zero, the source must still state 'explicitly zero — no fouling assumed' to confirm deliberate choice.

**Rationale / consequence:** Makes zero-fouling assumptions visible and traceable.

## Approval checklist

Before changing a row to `APPROVED`, record:

- approver name or role;
- approval date;
- affected task IDs and schemas;
- references or enterprise rule source;
- whether existing examples, tests or reports require revision.

## New decision template

```text
ID: DEC-XXX
Decision:
Status: PROPOSED
Owner:
Context:
Options considered:
Decision rationale:
Affected modules and task IDs:
Evidence / references:
Approval record:
```
