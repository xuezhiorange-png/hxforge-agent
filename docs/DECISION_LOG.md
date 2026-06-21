# HXForge Engineering Decision Log

This log records product and engineering decisions that affect schemas, defaults, calculations, warnings or compliance language. Coding tools must not convert a proposed item into code behavior until its status is `APPROVED`.

Status values: `PROPOSED`, `APPROVED`, `REJECTED`, `SUPERSEDED`.

**Authoritative source:** Each decision's full text lives in the detailed section below. The index table provides a concise summary only.

## Decision index

| ID | One-line summary | Status | Owner |
|---|---|---|---|
| DEC-001 | First vertical slice is single-phase double-pipe / hairpin | PROPOSED | Engineering owner |
| DEC-002 | Shell-and-tube and plate may appear in v0.1 screening | PROPOSED | Engineering owner |
| DEC-003 | Two-phase services return `NOT_IMPLEMENTED` until validated | PROPOSED | Engineering owner |
| DEC-004 | No hidden numerical engineering defaults | PROPOSED | Engineering owner |
| DEC-005 | SI internal kernel; absolute temperature ≠ temperature difference | PROPOSED | Engineering owner |
| DEC-006 | Three-way state model: workflow_stage, verification_level, requires_review | PROPOSED | Engineering + product owner |
| DEC-007 | HXForge never claims certified compliance from preliminary calcs | PROPOSED | Engineering owner |
| DEC-008 | Every numerical output includes provenance and structured warnings | PROPOSED | Engineering + software owner |
| DEC-009 | Candidate generation limited to approved manufacturable catalog | PROPOSED | Engineering owner |
| DEC-010 | Blocking error prevents recommendation and report-ready status | PROPOSED | Engineering owner |
| DEC-011 | CoolProp is the first and default property backend for v0.1 | PROPOSED | Engineering owner |
| DEC-012 | Each correlation declares its own applicability envelope; reject-by-default outside envelope | PROPOSED | Engineering owner |
| DEC-013 | Candidate structures must come from versioned, sourced catalog; continuous opt must not invent procurement dimensions | PROPOSED | Engineering owner |
| DEC-014 | Typed convergence: heat-balance acceptance + per-solver absolute/relative tolerances + max iterations | PROPOSED | Engineering owner |
| DEC-015 | Sizing uses discrete structure selection; rating reports margins without modifying structure | PROPOSED | Engineering owner |
| DEC-016 | Three-tier fluid validation: mandatory, extended, independent-incompressible | PROPOSED | Engineering owner |
| DEC-017 | Fouling source is a structured object; zero fouling requires explicit choice and Warning | PROPOSED | Engineering owner |

## Detailed decisions

### DEC-001 — First vertical slice: single-phase double-pipe / hairpin

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** The first complete calculation vertical slice is single-phase double-pipe / hairpin service.

**Rationale / consequence:** Limits early validation scope and proves the full input-to-report workflow before adding more exchanger families.

**Affected modules:** TASK-007 through TASK-010

---

### DEC-002 — Screening may include unimplemented families

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** Shell-and-tube and plate exchangers may appear in v0.1 screening before their detailed sizing/rating solvers are complete.

**Rationale / consequence:** Allows technology comparison without falsely claiming validated detailed calculations.

**Affected modules:** Screening workflow, WORKFLOW_MATRIX

---

### DEC-003 — Two-phase services return NOT_IMPLEMENTED

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** Condensation, evaporation and other two-phase services return `NOT_IMPLEMENTED` until approved correlations and validation cases are merged.

**Rationale / consequence:** Prevents unvalidated refrigerant calculations from being presented as engineering results.

**Affected modules:** Thermal service classifier, property provider

---

### DEC-004 — No hidden numerical engineering defaults

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** Public engineering inputs never use hidden numerical defaults. Values such as fouling resistance, area margin, roughness, material, cost basis and corrosion allowance must be provided or explicitly selected from an approved rule set.

**Rationale / consequence:** Makes assumptions visible and traceable.

**Affected modules:** All input schemas, I/O dictionary

---

### DEC-005 — SI internal kernel with dimension separation

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** The deterministic calculation core uses SI units; API and reports may convert to user-selected display units. Absolute temperature and temperature difference are separate dimensions.

**Rationale / consequence:** Avoids unit ambiguity and offset-temperature errors.

**Affected modules:** TASK-002 (units), all solvers

---

### DEC-006 — Three-way state model: workflow stage, verification maturity, review requirement

**Status:** PROPOSED
**Owner:** Engineering + product owner

**Decision:** Every calculation result carries three independent fields: `workflow_stage`, `verification_level`, and `requires_review`.

**`workflow_stage`** — the execution position of the workflow:

| Value | Meaning |
|---|---|
| `DRAFT` | Case created, not yet validated |
| `INPUT_VALIDATED` | Inputs pass schema and engineering validation |
| `THERMAL_SERVICE_RESOLVED` | Phase, service type identified |
| `TECHNOLOGIES_SCREENED` | Candidate families ranked |
| `CANDIDATES_GENERATED` | Geometry candidates produced |
| `CANDIDATES_RATED` | Candidates thermally and hydraulically rated |
| `ENGINEERING_CHECKED` | Mechanical, material and risk checks done |
| `COSTED` | Cost estimates attached |
| `VERIFICATION_COMPLETED` | Benchmark and regression verification step executed |
| `REPORT_READY` | Report packaged |
| `BLOCKED` | Terminal: input, safety, applicability, property or specification failure |
| `NOT_IMPLEMENTED` | Terminal: capability not yet available |
| `NON_CONVERGED` | Terminal: iterative solver failed to converge |

**`verification_level`** — the evidence maturity of the engineering result:

| Value | Meaning |
|---|---|
| `UNVERIFIED` | Result produced but not yet compared against benchmarks or hand calculations |
| `PRELIMINARY` | Calculation completed; engineering plausibility checked but not formally validated |
| `BENCHMARK_VALIDATED` | Result passes approved benchmark cases within declared tolerances |
| `ENGINEERING_APPROVED` | Result reviewed and approved by a qualified engineer |
| `N/A` | Not applicable when workflow_stage is a terminal state (BLOCKED, NOT_IMPLEMENTED, NON_CONVERGED) |

**`requires_review`** — whether a human engineering review is needed before the result can be used for decisions:

| Value | Derivation |
|---|---|
| `true` | Any WARNING is present, or any assumption/deviation from standard conditions exists, or verification_level is UNVERIFIED or PRELIMINARY |
| `false` | verification_level is BENCHMARK_VALIDATED or ENGINEERING_APPROVED with no open warnings |

`requires_review` is a derived boolean, not a user-set field. It is computed from warnings, assumptions, and verification_level.

**Rationale / consequence:** Separates three orthogonal concerns: where the workflow is (stage), how mature the evidence is (verification_level), and whether human action is needed (requires_review). Prevents conflating workflow completion with engineering confidence, and prevents requiring review for trivially verified results.

**Affected modules:** All result schemas, API responses, report generation, TASK-005

---

### DEC-007 — No certified compliance claims

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** HXForge never claims certified ASME, TEMA, API or statutory compliance from preliminary calculations.

**Rationale / consequence:** Code compliance requires licensed rules, complete inputs, qualified review and applicable legal processes.

**Affected modules:** Report templates, API responses

---

### DEC-008 — Mandatory provenance and warnings

**Status:** PROPOSED
**Owner:** Engineering + software owner

**Decision:** Every numerical output must include calculation provenance and structured warnings.

**Rationale / consequence:** Supports reproducibility, review and regression control.

**Affected modules:** TASK-005 (provenance), all result schemas

---

### DEC-009 — Catalog-limited candidate generation

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** Candidate generation is limited to approved, manufacturable catalog geometry; continuous optimization cannot invent arbitrary procurement dimensions.

**Rationale / consequence:** Keeps optimized designs buildable and comparable.

**Affected modules:** TASK-009 (sizing), geometry catalog

---

### DEC-010 — Blocking error prevents recommendation

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** A blocking input, safety, property or applicability error prevents candidate recommendation and report-ready status.

**Rationale / consequence:** Prevents the Agent from forcing a result through an invalid workflow.

**Affected modules:** All workflows, state machine

---

### DEC-011 — CoolProp as default property backend

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:** CoolProp is the first and default property backend for v0.1. Alternative backends (REFPROP, custom databases) are architecture-ready but not implemented in v0.1.

**Rationale / consequence:** Limits property validation scope to one well-documented open-source backend while proving the injectable-provider interface.

**Affected modules:** TASK-003 (property service), FluidSpec schema

---

### DEC-012 — Per-correlation applicability envelope with reject-by-default

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:**

1. Each registered correlation must independently declare its own applicability envelope (Reynolds range, Prandtl range, geometry limits, roughness limits, fluid type, phase).
2. When input falls outside a correlation's declared envelope, the default behavior is **reject** — the correlation must not be used.
3. Interpolation across regime boundaries (e.g., laminar-to-turbulent transition) is permitted **only** when an approved composite model exists that has been validated for the transition zone.
4. All interpolation must produce a `WARNING` with the interpolation method recorded in provenance.
5. No blanket transition-zone policy (such as a system-wide Re range) overrides individual correlation envelopes.

**Rationale / consequence:** Ensures each correlation's适用范围 is self-contained and auditable. Prevents system-wide defaults from masking per-formula inappropriateness.

**Affected modules:** TASK-004 (correlation registry), TASK-007 (double-pipe correlations), applicability engine

---

### DEC-013 — Manufacturable catalog constraint

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:**

1. Candidate structures in sizing must come from a versioned, sourced, manufacturable geometry catalog.
2. Every catalog entry must carry a source reference, version, and revision date.
3. Continuous optimization may only select combinations of catalog-listed discrete parameters.
4. Optimization must not generate non-standard procurement dimensions.
5. Maximum hairpin effective length is constrained by **four independent factors**:
   - **Manufacturer capability:** standard production lengths available from approved suppliers;
   - **Transport:** maximum transportable length per road, rail or sea freight;
   - **Installation:** crane reach, site access and field assembly limits;
   - **Maintenance:** tube-pull distance, bundle removal access and clearances.
   These four factors must be checked independently; a hairpin that passes one constraint may fail another.

**Note:** The geometry catalog file format (YAML, JSON, etc.) is a software implementation decision and is recorded in the Architecture Decision Record, not here.

**Rationale / consequence:** Separates engineering constraints from software format choices. Prevents overly narrow geometric assumptions that exclude valid designs.

**Affected modules:** TASK-009 (sizing), TASK-016 (geometry catalog), TASK-017 (mechanical checks)

---

### DEC-014 — Typed convergence framework

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:**

Iterative solvers must declare and track typed convergence parameters. There are two independent convergence checks:

**A. Heat-balance acceptance** (energy closure)

$$\epsilon_{HB} = \frac{|Q_{hot} - Q_{cold}|}{\max(|Q_{hot}|, |Q_{cold}|, Q_{floor})}$$

where $Q_{floor}$ is a non-zero reference floor (default: 1 W) to prevent division by near-zero values. The default acceptance threshold is $\epsilon_{HB} < 0.001$ (0.1%). This check applies to every solver that computes duty from two streams.

**B. Numerical solver convergence** (per-solver)

Each iterative solver must declare a typed convergence specification:

| Field | Type | Description |
|---|---|---|
| `primary_variable` | string | Name of the variable being solved (e.g., "outlet_temperature", "pressure", "U_value") |
| `absolute_tolerance` | quantity (same dimension as primary_variable) | Maximum allowed absolute change between iterations |
| `relative_tolerance` | dimensionless fraction | Maximum allowed relative change between iterations |
| `scaling_quantity` | quantity (same dimension as primary_variable) | Reference scale for relative tolerance; prevents division by near-zero values |
| `residual_definition` | string | How the residual is computed (e.g., "abs(x_n - x_{n-1})", "L2 norm of residual vector") |

Convergence criterion: `abs(delta_x) <= absolute_tolerance + relative_tolerance * scaling_quantity`.

Default values are solver-specific and must be declared per solver, not globally assigned. Example for an outlet-temperature solver:
- `absolute_tolerance`: 0.005 K
- `relative_tolerance`: 1e-6
- `scaling_quantity`: |T_in| + 273.15 (absolute inlet temperature as scale)

Example for a U-value iteration:
- `absolute_tolerance`: 0.01 W/m²·K
- `relative_tolerance`: 1e-4
- `scaling_quantity`: current U estimate

**C. Maximum iteration count** — configurable per solver, default 100, always traceable in provenance.

All convergence parameters are configurable and traceable in provenance. When the maximum iteration count is reached without meeting tolerances, the run must terminate with workflow_stage `NON_CONVERGED` and a `BLOCKED` blocker explaining which tolerance was not met. The solver must not return the last iterate as a valid result.

**Rationale / consequence:** Prevents assigning a dimensionally invalid universal threshold to solvers with different primary unknowns. Ensures each solver declares convergence criteria appropriate to its variable type and scale.

**Affected modules:** TASK-006 (heat balance), TASK-008 (rating), TASK-009 (sizing), all iterative solvers

---

### DEC-015 — Discrete structure selection for sizing, reporting-only for rating

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:**

**Sizing:**
- Sizing selects discrete, catalog-listed structures.
- A candidate is accepted when: `actual_area >= required_area × (1 + required_margin)`.
- `required_area` is calculated from the thermal duty and predicted U-value for that specific geometry.
- `required_margin` is the user-specified `area_margin_fraction`.
- Rejected candidates (insufficient area) are discarded; accepted candidates are reported with their actual area and margin.

**Rating:**
- Rating does not modify the supplied structure.
- Rating reports four distinct area-related quantities:
  - `actual_area` — the geometric heat-transfer area of the supplied structure;
  - `required_area` — the area needed to achieve the calculated duty;
  - `area_margin` — `actual_area / required_area - 1` (dimensionless);
  - `duty_margin` — the excess duty capacity at the current geometry and conditions.
- None of these modify the geometry; they are informational outputs only.

**Rationale / consequence:** Makes the role of area margin explicit and consistent across workflows. Prevents ambiguity about whether margin changes geometry or just reporting.

**Affected modules:** TASK-008 (rating), TASK-009 (sizing), output schemas

---

### DEC-016 — Three-tier fluid validation scope

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:**

The v0.1 fluid validation scope is divided into three tiers:

**Tier 1 — Mandatory validation (must pass before TASK-003 completes):**
- Water (pure, single-phase)
- Air (single-phase, ideal-gas-like behavior)
- R134a (single-phase only; two-phase returns NOT_IMPLEMENTED)
- R717 (single-phase only; two-phase returns NOT_IMPLEMENTED)

**Tier 2 — Extended validation (must pass before v0.1 release):**
- R404A (single-phase only)
- R507A (single-phase only)

**Tier 3 — Independent incompressible-fluid task (separate task, not blocking v0.1 thermal core):**
- Propylene Glycol (MPG) water solutions at multiple concentrations
- Propylene Glycol (MPG2) water solutions
- Aqueous Propylene Glycol (APG) water solutions
- Other glycol-water mixtures as needed

Fluids not in any tier are supported architecturally (the PropertyProvider interface accepts them) but return `NOT_IMPLEMENTED` until validated with approved test cases.

R404A and R507A are listed independently; the phrase "R404A or R507A" must not be used as a single entry.

**Rationale / consequence:** Defines explicit validation scope per fluid. Separates mandatory thermal-core fluids from refrigerant and glycol extensions.

**Affected modules:** TASK-003 (property service), golden test suite

---

### DEC-017 — Structured fouling source object

**Status:** PROPOSED
**Owner:** Engineering owner

**Decision:**

The `fouling_resistance.source` field is a structured object, not a free-text string. Required fields:

| Field | Type | Description |
|---|---|---|
| `source_type` | enum: `STANDARD`, `VENDOR`, `USER`, `ASSUMED` | Origin of the fouling value |
| `reference_id` | string | Document identifier (e.g., "TEMA-RGP-T-2.4", "API 660 Table H") |
| `edition` | string | Edition or year of the reference |
| `table_or_clause` | string | Specific table, figure or clause within the reference |
| `note` | string | Free-text clarification or assumption statement |

When fouling resistance is zero:
- `source_type` must be `USER` or `ASSUMED`;
- `note` must state "explicitly zero — no fouling assumed";
- a `WARNING` must be returned to confirm the deliberate choice.

**Rationale / consequence:** Makes fouling assumptions traceable to a specific source. Prevents ambiguity about whether zero fouling is a deliberate engineering choice or a missing input.

**Affected modules:** All stream input schemas, TASK-008 (rating), TASK-009 (sizing), report templates

---

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
Status: PROPOSED
Owner:
Decision:
Rationale / consequence:
Affected modules:
```
