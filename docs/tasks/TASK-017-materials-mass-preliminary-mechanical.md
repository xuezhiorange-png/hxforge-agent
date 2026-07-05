# TASK-017 — Materials, Mass and Preliminary Mechanical Checks Design Contract

> Design contract for TASK-017. Defines the application-layer
> components that consume the TASK-013 material/cost governance data
> layer and the TASK-016 approved geometry catalog to produce
> deterministic mass totals and a bounded set of preliminary
> mechanical checks for double-pipe heat-exchanger geometries.
>
> This document is design-only: no production code, no public API,
> no report rendering, no database schema, no cost model, no
> pressure-drop implementation, no C4 logic, and no mutation of
> any frozen contract is introduced by this design PR.

## 1. Authority and status

| Field | Value |
|---|---|
| Authorizing issue | #72 |
| Backlog item | TASK-017 — Add materials, mass and preliminary mechanical checks |
| Backlog status before authorization | PLANNED |
| Backlog dependency | TASK-012 (impl), TASK-013, TASK-016 |
| Design branch | `docs/task-017-materials-mass-preliminary-mechanical-design` |
| Design file | `docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md` |
| Base authority | TASK-016 implementation merge `fbb05ae71f21e6cfd4d1041afb5958c863166248` (PR #71, merged 2026-07-05T16:37:19Z) |
| Upstream contracts consumed (read-only) | TASK-013 material/cost governance contract (frozen), TASK-016 geometry catalog contract (frozen) |
| Implementation status | NOT AUTHORIZED |
| Frozen contract SHA | NOT ESTABLISHED until this design PR is merged |

Implementation work is explicitly blocked until this design contract
is reviewed, merged, and closed out under Charles authorization.

## 2. Problem statement

The double-pipe vertical slice currently has thermal correlations,
fixed-geometry rating, manufacturable sizing, standards rule-pack,
material / cost **data governance**, immutable case revisions,
geometry **catalog**, and CI / security / release hardening
contracts. The remaining M2 layer before shell-and-tube is the
**application of those data layers to compute deterministic mass
totals and a bounded set of preliminary mechanical screening
checks** for double-pipe geometries.

Without an explicit TASK-017 contract, future code can drift in
any of the following ways:

1. Re-deriving material density, modulus, or allowable-stress
   values inline instead of consuming the frozen TASK-013
   governance layer.
2. Mixing shell-side vs. tube-side metal allocation without a
   documented allocation rule, producing non-deterministic mass
   splits between renders.
3. Embedding pressure-drop correlation behavior (forbidden by the
   TASK-016 catalog contract and by Charles's standing
   "no pressure-drop implementation" rule) inside what is supposed
   to be a mechanical check.
4. Treating preliminary mechanical checks as authoritative
   structural design — preliminary checks must surface
   `BLOCKED_FOR_DETAILED_DESIGN` for any geometry that exceeds
   the screening envelope.
5. Re-introducing cost calculations in what is supposed to be a
   pre-cost material / mass / mechanical layer (cost belongs to
   TASK-018).

TASK-017 closes this design gap by freezing the application-layer
contract before any implementation.

## 3. Scope and non-scope

### 3.1 In scope for this design contract

1. Material selector that consumes TASK-013 governance records
   (read-only) and returns the resolved material record for a
   given component role.
2. Mass calculator that, given an approved TASK-016 geometry
   record and a resolved material record, returns deterministic
   mass totals broken down by component role (inner tube, outer
   pipe, hairpin return bend if applicable, end fittings
   placeholder if applicable).
3. Preliminary mechanical screening checks, scope-limited to:
   - Allowable-stress screening (uses TASK-013 material
     allowable values; returns PASS / MARGINAL / BLOCKED based on
     design pressure × diameter / 2 × wall-thickness ratio vs.
     allowable stress at design temperature).
   - Minimum-wall screening (returns BLOCKED if selected wall
     thickness is below the documented minimum).
   - Straight-pipe span screening (returns BLOCKED if unsupported
     span exceeds a documented default).
4. Audit / provenance fields that bind every mass / mechanical
   output back to its source geometry record (TASK-016 catalog
   entry id) and its resolved material record (TASK-013
   governance record id).
5. Structured blocker codes for every failure mode.
6. Frozen test expectations for the future implementation PR.

### 3.2 Explicit non-scope

This design contract does **not** authorize:

- TASK-017 production implementation under `src/`.
- Any TASK-018+ task, including C0/C1 cost model and life-cycle
  energy estimate.
- Any TASK-019+ Golden cases or double-pipe validation report.
- **Pressure-drop implementation**, **C4 logic**, or any
  pressure-drop correlation.
- Any new solver, any modification to existing production solver
  behavior under `src/hexagent/`.
- Any re-implementation of material density / modulus /
  allowable-stress values (those live in TASK-013 governance
  and are read-only consumers here).
- Any cost calculation, currency conversion, vendor price list,
  CAPEX / OPEX / life-cycle estimate (TASK-018).
- Any mutation of `src/`, `tests/`, `.github/`,
  `ci-shard-manifest.yml`.
- Any mutation of TASK-011 / TASK-012 / TASK-013 / TASK-014 /
  TASK-015 / TASK-015A / TASK-016 frozen contracts or
  implementation.
- Any detailed mechanical design (FEA, fatigue, creep, seismic,
  wind, weld, NDE). These return
  `BLOCKED_FOR_DETAILED_DESIGN` from the preliminary check and
  are out of scope for this layer.
- Any two-phase, refrigerants, shell-and-tube, plate, air cooler,
  or microchannel content (TASK-020+).
- Secret registration, OIDC trust, registry push, external service
  integration.
- Closing the authorizing Issue (#72).
- Marking the design PR Ready for review.
- Merging the design PR.

## 4. Design goals

The TASK-017 application layer must be:

1. **Deterministic** — every mass / mechanical output is a pure
   function of its inputs (geometry record + resolved material
   record). No network, no clock, no environment lookups.
2. **Read-only on frozen contracts** — only reads TASK-013
   governance records and TASK-016 catalog records. Never
   mutates them.
3. **Unit-explicit** — all dimensional values flow through the SI
   kernel. No bare unitless public inputs.
4. **Blocker-driven** — every failure mode surfaces a structured
   `MechanicalCheckError` with a stable error code; never a
   silent PASS / MARGINAL / BLOCKED ambiguity.
5. **Provenance-bound** — every result carries the geometry
   record id, the resolved material record id, and the input
   checksum so downstream layers can audit the result.
6. **Bounded** — the mechanical screening envelope is explicitly
   documented in §9. Anything outside that envelope returns
   `BLOCKED_FOR_DETAILED_DESIGN` and must not silently
   extrapolate.

## 5. Domain model

### 5.1 MaterialSelector

A `MaterialSelector` resolves a `MaterialResolutionRequest`
(component_role, design_temperature_c, design_pressure_mpa,
corrosion_allowance_mm, applicable_standard_id,
material_record_id) to a `MaterialResolutionResult`.

#### 5.1.1 TASK-013 property_values lookup

TASK-013 frozen contract §5.5 carries material engineering values
in a `property_values: [{property_name, value_si, unit_si, ...}]`
array — NOT as typed top-level fields. The TASK-017 selector
MUST therefore walk the TASK-013 record's `property_values[]`
array and read the entries whose `property_name` matches the
TASK-017 required canonical property names listed in §5.1.2.

The `value_si` field is a decimal string; the selector MUST convert
it to a Python `float` using `Decimal(value_si)` (not `float(...)`)
to preserve precision. The `unit_si` field MUST be checked against
the canonical SI unit expected for that property; a unit mismatch
returns `MATERIAL_GOVERNANCE_INCOMPLETE`.

#### 5.1.2 TASK-017 required canonical property names

The TASK-017 selector reads the following property entries from
TASK-013 `property_values[]`. These names are **declared by
TASK-017** as the canonical names it requires — they are NOT
claimed to be a frozen enum of TASK-013. If a future TASK-013
amendment uses different property_name strings, the TASK-017
selector must be updated to match (this is a contract revision,
not a runtime concern).

| TASK-017 required `property_name` | Type | SI unit | Used for |
|---|---|---|---|
| `density` | `float` | `kg/m^3` | MassCalculator (§5.2, §6) |
| `youngs_modulus` | `float` | `GPa` | PreliminaryMechanicalChecker §9.3 |
| `allowable_stress` | `dict[float, float]` (temperature_c → MPa) | `MPa` | PreliminaryMechanicalChecker §9.1 |

Notes:

- `allowable_stress` is a **table**, not a scalar. The TASK-013
  `property_values[]` entry for this property MUST carry
  `value_si` as a JSON-encoded string of the table shape
  `{"<temperature_c>": "<stress_mpa_decimal_string>", ...}`,
  with `unit_si = "MPa"`. The selector parses this JSON, converts
  each decimal string to `float`, and returns the table as
  `dict[float, float]` keyed by °C. If the TASK-013 record's
  `property_values[]` does not contain an `allowable_stress`
  entry, the selector returns `MATERIAL_GOVERNANCE_INCOMPLETE`.
- `youngs_modulus` MAY be absent from TASK-013 for materials
  where it is not applicable; the selector returns `None` for
  this field in that case (and mechanical checks that need it
  return `BLOCKED_FOR_DETAILED_DESIGN` if invoked without it).
- The selector MUST NOT perform any derivation, interpolation,
  extrapolation, or unit conversion outside what TASK-013
  already provides. If a required property is missing, the
  selector returns `MATERIAL_GOVERNANCE_INCOMPLETE` (see §7).

#### 5.1.3 MaterialResolutionResult shape

The selector returns:

- `material_record_id: str` — the resolved TASK-013 governance
  record id (e.g. `"mat:astm-sa-106-b:rev:2026-Q2"`).
- `material_grade: str` — the material grade label from TASK-013
  (copied verbatim from `material_grade_or_designation`).
- `density_kg_m3: float | None` — converted from TASK-013
  `property_values[*].value_si` for `property_name="density"`.
  `None` if the property is absent.
- `youngs_modulus_gpa: float | None` — same shape for
  `property_name="youngs_modulus"`.
- `allowable_stress_mpa: dict[float, float] | None` — same
  shape for `property_name="allowable_stress"`. Key is °C,
  value is MPa.
- `provenance: MaterialProvenance` — see §8.

Any field that depends on a TASK-013 property_name listed in
§5.1.2 but absent from the resolved record's `property_values[]`
MUST be set to `None` AND the selector MUST return
`MATERIAL_GOVERNANCE_INCOMPLETE` (i.e. the resolution is
unsuccessful — see §7).

### 5.2 MassCalculator

A `MassCalculator` takes a `MassCalculationRequest`
(geometry_record, material_resolutions_by_component_role,
fitting_overrides_kg, include_hairpin: bool) and returns a
`MassBreakdown`.

#### 5.2.1 component_role enumeration (frozen closed set)

TASK-017 defines the following closed set of component_role
strings, each corresponding to a metal component of the
double-pipe geometry:

| `component_role` | Metal component | TASK-016 geometry fields consumed |
|---|---|---|
| `inner_tube` | inner tube metal mass | `outer_diameter_m`, `inner_diameter_m`, `effective_length_m` |
| `outer_pipe` | outer pipe metal mass | `outer_diameter_m`, `inner_diameter_m`, `effective_length_m` |
| `hairpin_bend` | hairpin return-bend metal mass | `bend_radius_m`, `effective_length_m`, `number_of_tubes` |
| `fittings` | end-fitting placeholder mass | not geometry-derived; uses `fitting_overrides_kg` |

`material_resolutions_by_component_role` MUST contain a
`MaterialResolutionResult` for **every** component_role listed
above. Any missing role returns `MATERIAL_RESOLUTION_MISSING_ROLE`
(see §7). This single-source-of-truth design replaces the
earlier single-material simplification.

#### 5.2.2 MassBreakdown

| Field | Type | Meaning |
|---|---|---|
| `inner_tube_kg` | `float` | inner tube metal mass (uses `component_role="inner_tube"` resolution) |
| `outer_pipe_kg` | `float` | outer pipe metal mass (uses `component_role="outer_pipe"` resolution) |
| `hairpin_bend_kg` | `float` | hairpin return-bend metal mass (uses `component_role="hairpin_bend"` resolution; 0 if not applicable) |
| `fittings_kg` | `float` | end-fitting placeholder mass (uses `component_role="fittings"` resolution; 0 if no overrides) |
| `total_kg` | `float` | sum of the four component masses |
| `calculation_hash: str` | deterministic 64-char SHA-256 over the canonical inputs (see §10) |
| `provenance: MassProvenance` | see §8 |

The breakdown MUST be deterministic across runs on the same
input. The component allocation is defined in §6.

### 5.3 PreliminaryMechanicalChecker

A `PreliminaryMechanicalChecker` takes a
`MechanicalCheckRequest` (geometry_record,
material_resolutions_by_component_role, design_pressure_mpa,
design_temperature_c, unsupported_span_m, corrosion_allowance_mm,
component_under_check) and returns a `MechanicalCheckReport`.

`component_under_check` selects which `component_role`'s
`MaterialResolutionResult` from
`material_resolutions_by_component_role` is used for the
mechanical checks. Valid values: `"inner_tube"` or `"outer_pipe"`
(the preliminary envelope covers pressure-bearing metal
components). Selecting `"hairpin_bend"` or `"fittings"` returns
`MECHANICAL_CHECK_UNSUPPORTED_ROLE` (see §7).

The returned report has:

- `allowable_stress_check: CheckVerdict` — see §9.1.
- `minimum_wall_check: CheckVerdict` — see §9.2.
- `straight_pipe_span_check: CheckVerdict` — see §9.3.
- `overall_verdict: Verdict` — one of `PASS`, `MARGINAL`,
  `BLOCKED_PRELIMINARY`, `BLOCKED_FOR_DETAILED_DESIGN`.
- `provenance: MechanicalProvenance` — see §8.

If any check returns `BLOCKED_FOR_DETAILED_DESIGN`, the overall
verdict is `BLOCKED_FOR_DETAILED_DESIGN`. If any check returns
`BLOCKED_PRELIMINARY` (preliminary envelope violation),
`overall_verdict` is `BLOCKED_PRELIMINARY`. If any check returns
`MARGINAL` and none are BLOCKED, `overall_verdict` is `MARGINAL`.
Otherwise `PASS`.

## 6. Component allocation rules

To keep the mass breakdown deterministic and reproducible:

1. **Inner tube mass** = `material_resolutions_by_component_role["inner_tube"].density_kg_m3
   * π * ((outer_diameter_m / 2)² − (inner_diameter_m / 2)²)
   * effective_length_m`.
   - `outer_diameter_m`, `inner_diameter_m`, `effective_length_m`
     are read from the TASK-016 tube geometry record.
2. **Outer pipe mass** = `material_resolutions_by_component_role["outer_pipe"].density_kg_m3
   * π * ((outer_diameter_m / 2)² − (inner_diameter_m / 2)²)
   * effective_length_m`.
   - `outer_diameter_m`, `inner_diameter_m`, `effective_length_m`
     are read from the TASK-016 pipe geometry record.
3. **Hairpin bend mass** is computed from TASK-016 hairpin
   geometry fields using the following normative formula:

   ```
   bend_cross_section_area_m2 =
       π * ((tube_outer_diameter_m / 2)² − (tube_inner_diameter_m / 2)²)
   bend_centerline_arc_length_m =
       π * bend_radius_m          # half-torus centerline approximation
   single_bend_volume_m3 =
       bend_cross_section_area_m2 * bend_centerline_arc_length_m
   total_bend_volume_m3 =
       single_bend_volume_m3 * number_of_tubes
   hairpin_bend_kg =
       material_resolutions_by_component_role["hairpin_bend"].density_kg_m3
       * total_bend_volume_m3
   ```

   Fields used (all TASK-016 frozen contract §5.5 hairpin
   fields): `tube_outer_diameter_m`, `tube_inner_diameter_m`
   (resolved from the hairpin record's `tube_geometry_id`
   reference via TASK-016 catalog lookup), `bend_radius_m`,
   `effective_length_m` (used as a sanity check; if
   `effective_length_m < π * bend_radius_m`, the geometry is
   flagged as inconsistent — see §7), `number_of_tubes`.

   If the geometry record is straight-pipe only (no hairpin
   entry), `hairpin_bend_kg` is 0.

   If a required hairpin field is missing, the calculator
   returns `HAIRPIN_BEND_INPUT_INCOMPLETE` (see §7) and the
   `hairpin_bend_kg` field is `NaN` (NOT zero, to distinguish
   "not applicable" from "applicable but unresolved").

4. **Fittings mass** = sum of `fitting_overrides_kg` values,
   scaled by `material_resolutions_by_component_role["fittings"].density_kg_m3 / 7850.0`
   where 7850.0 kg/m³ is a documented reference carbon-steel
   density (the override is supplied as a mass, not a volume,
   so this scale factor only applies if the caller opts in via
   `fitting_density_normalization: bool = True` in the request;
   otherwise `fittings_kg = sum(fitting_overrides_kg)` exactly).
   If no overrides are supplied, `fittings_kg` is 0.

These formulas are normative; the future implementation must not
introduce alternative formulas without an updated frozen design
contract.

## 7. Error model

| Error code | Meaning | Recovery |
|---|---|---|
| `MATERIAL_GOVERNANCE_INCOMPLETE` | A required property_name from §5.1.2 is missing from the resolved TASK-013 material record's `property_values[]`, OR a unit mismatch was detected. | Caller must either supply an alternative governance record id or open a TASK-013 follow-up to add the missing property (out of scope for TASK-017). |
| `MATERIAL_GOVERNANCE_UNAPPROVED` | The TASK-013 material record is in a non-approved state (`approval_state != "approved"`). | Caller must select an approved alternative. |
| `MATERIAL_RESOLUTION_MISSING_ROLE` | `material_resolutions_by_component_role` is missing one or more of the four frozen component_role keys (`inner_tube`, `outer_pipe`, `hairpin_bend`, `fittings`). | Caller must supply a MaterialResolutionResult for every role. |
| `GEOMETRY_CATALOG_UNAPPROVED` | The TASK-016 geometry record is in a non-approved state. | Caller must select an approved geometry. |
| `GEOMETRY_CATALOG_INCONSISTENT` | The geometry record has inconsistent dimensions (e.g. `outer_diameter_m < inner_diameter_m`, OR hairpin `effective_length_m < π * bend_radius_m`). | Caller must select a different geometry or open a TASK-016 follow-up. |
| `HAIRPIN_BEND_INPUT_INCOMPLETE` | A hairpin geometry record is present but lacks one or more required fields (`tube_geometry_id`, `bend_radius_m`, `effective_length_m`, `number_of_tubes`, OR the referenced tube geometry record cannot be resolved). | Caller must supply a complete hairpin geometry record. The `hairpin_bend_kg` field in the breakdown is `NaN` (not 0). |
| `ALLOWABLE_STRESS_EXCEEDED` | Design pressure / diameter / wall-thickness ratio exceeds TASK-013 allowable stress at design temperature. | Caller must select a thicker wall, lower design pressure, or a higher-allowable material. |
| `MINIMUM_WALL_VIOLATED` | Selected wall thickness is below the documented minimum. | Caller must select a geometry with thicker wall. |
| `UNSUPPORTED_SPAN_EXCEEDED` | Unsupported span exceeds the documented default. | Caller must add intermediate supports or escalate to detailed design. |
| `BLOCKED_FOR_DETAILED_DESIGN` | The check is outside the preliminary envelope. | Caller must escalate to detailed mechanical design (FEA, fatigue, creep, seismic). |
| `MECHANICAL_CHECK_UNSUPPORTED_ROLE` | `component_under_check` is `"hairpin_bend"` or `"fittings"` — the preliminary mechanical check envelope covers pressure-bearing metal components only. | Caller must use `"inner_tube"` or `"outer_pipe"`. |
| `INPUT_DIMENSIONAL_INCONSISTENT` | Caller supplied an inconsistent input dimension (e.g. negative length). | Caller must correct the input. |
| `INPUT_UNIT_INCONSISTENT` | Caller supplied a value with non-SI units. | Caller must convert to SI before retry. |

All errors are returned as a single `MechanicalCheckError`
exception with `.code`, `.message`, `.context`, `.provenance`.

## 8. Audit fields and provenance requirements

Every `MassBreakdown` and `MechanicalCheckReport` carries a
provenance block with at minimum:

| Field | Meaning |
|---|---|
| `geometry_record_id` | TASK-016 catalog record id |
| `material_record_id` | TASK-013 governance record id |
| `applicable_standard_id` | TASK-012 rule-pack standard id, if any |
| `design_pressure_mpa` | input echo (SI) |
| `design_temperature_c` | input echo (SI) |
| `correlation_ids` | list of correlation registry ids consulted (empty list for mass; mechanical checks may use documented ids from TASK-005 registry) |
| `software_version` | HXForge version string |
| `git_commit` | commit SHA at calculation time |
| `result_hash` | 64-char SHA-256 over the canonical result JSON |

Provenance is mandatory. A result without provenance is a
`MechanicalCheckError` with code
`PROVENANCE_INCOMPLETE` (a failure, not a soft warning).

## 9. Preliminary mechanical screening envelope

The screening envelope is intentionally bounded. Anything outside
it returns `BLOCKED_FOR_DETAILED_DESIGN`.

### 9.1 Allowable-stress check

- **Input**: `design_pressure_mpa`, `inner_or_outer_diameter_m`
  (per component), `wall_thickness_m` (from geometry record),
  `allowable_stress_mpa[design_temperature_c]`.
- **Formula**: `hoop_stress_mpa = design_pressure_mpa *
  diameter_m / (2 * wall_thickness_m)`.
- **Verdict**:
  - `PASS` if `hoop_stress_mpa <= 0.6 * allowable_stress_mpa`.
  - `MARGINAL` if `0.6 * allowable_stress_mpa < hoop_stress_mpa
    <= 0.8 * allowable_stress_mpa`.
  - `BLOCKED_PRELIMINARY` if `hoop_stress_mpa >
    0.8 * allowable_stress_mpa`.
  - `BLOCKED_FOR_DETAILED_DESIGN` if the geometry is outside
    the preliminary envelope (e.g. diameter > 1.0 m).

### 9.2 Minimum-wall check

- **Input**: `wall_thickness_m` (from geometry record),
  `corrosion_allowance_m` (from caller input).
- **Formula**: `effective_wall_m = wall_thickness_m -
  corrosion_allowance_m`.
- **Verdict**:
  - `PASS` if `effective_wall_m >= 1.5 mm` AND
    `effective_wall_m / diameter_m >= 0.0005`.
  - `BLOCKED_PRELIMINARY` if either threshold is violated.
  - `BLOCKED_FOR_DETAILED_DESIGN` if `diameter_m > 1.0 m`.

### 9.3 Straight-pipe span check

- **Input**: `unsupported_span_m` (caller input),
  `outer_diameter_m`, `material_modulus_gpa`,
  `material_resolutions_by_component_role[component_under_check].density_kg_m3`,
  `component_under_check`.
- **Formula** (normative, computed under the conservative
  loading factor `K_load = 1.5` and the allowable deflection
  ratio `L / 360`):

  ```
  # weight per unit length (kg/m), conservatively using only
  # the metal cross-section area for the component_under_check
  outer_d = outer_diameter_m
  inner_d = inner_diameter_m
  cross_section_area_m2 =
      π * ((outer_d / 2)² − (inner_d / 2)²)
  weight_per_length_n_per_m =
      material_density_kg_m3 * cross_section_area_m2 * 9.80665

  # distributed load (N/m), scaled by K_load
  w = weight_per_length_n_per_m * K_load

  # second moment of area (m^4) for thin-walled circular tube
  I = (π / 64) * (outer_d⁴ − inner_d⁴)

  # elastic deflection (m) for a simply-supported beam under
  # uniform load
  L = unsupported_span_m
  E_gpa = material_modulus_gpa
  E_pa = E_gpa * 1e9
  deflection_m = (5 * w * L⁴) / (384 * E_pa * I)

  # allowable deflection (m)
  allowable_deflection_m = L / 360

  verdict_input = (deflection_m, allowable_deflection_m, L)
  ```

- **Verdict**:
  - `PASS` if `deflection_m <= allowable_deflection_m`.
  - `BLOCKED_PRELIMINARY` if `deflection_m > allowable_deflection_m`.
  - `BLOCKED_FOR_DETAILED_DESIGN` if any input is outside the
    preliminary envelope (e.g. `unsupported_span_m > 12 m`,
    or `material_modulus_gpa is None`,
    or `outer_diameter_m > 1.0 m`).
  - The check returns `BLOCKED_FOR_DETAILED_DESIGN` (NOT
    `MECHANICAL_CHECK_UNSUPPORTED_ROLE`) when `material_modulus_gpa`
    is missing for the component_under_check, because the
    preliminary envelope for span checking inherently requires
    modulus. The caller must escalate to detailed mechanical
    design.

This formula is normative for the design contract and is part
of the contract body (not deferred to implementation docs). It
MUST NOT change without an updated frozen contract.

## 10. JSON / hash / ordering rules

1. Every `MassBreakdown` and `MechanicalCheckReport` is
   serializable to JSON via a documented
   `MechanicalSchema` (see §13). The JSON schema is fixed by
   this design contract.
2. JSON keys are sorted lexicographically before hashing.
3. Floating-point values are formatted with a documented
   `Decimal` quantizer: 6 decimal places for kg, 4 decimal
   places for m / mm / MPa / °C, 9 decimal places for GPa.
4. The result hash is the lowercase hex SHA-256 of the UTF-8
   encoded canonical JSON.
5. Provenance fields are included in the hashed JSON.
6. Optional fields are either present with `null` or absent per
   the documented schema. They are not added ad hoc per render.

## 11. Test strategy

The future implementation MUST include:

1. **Unit tests** for every §6 mass formula and every §9
   mechanical check, covering PASS / MARGINAL / BLOCKED
   transitions.
2. **Boundary tests** at the envelope thresholds (e.g.
   `hoop_stress = 0.6 * allowable`, `1.5 mm` wall, `L / 360`
   deflection).
3. **Blocker tests** for every error code in §7.
4. **Determinism tests**: identical inputs across two
   invocations must produce byte-identical JSON and identical
   SHA-256 hashes, across Python 3.10, 3.11, 3.12.
5. **Frozen-task tests**: the implementation MUST NOT modify
   any frozen TASK-011 / TASK-012 / TASK-013 / TASK-014 /
   TASK-015 / TASK-016 contract artifact (verifiable via
   `git diff --name-only <base>..<impl-head>` returning only
   `src/hexagent/material_mass_mechanical/` and
   `tests/material_mass_mechanical/`).
6. **No-pressure-drop test**: a guard test asserts that no
   pressure-drop correlation id appears anywhere in the TASK-017
   code path.
7. **No-cost test**: a guard test asserts that no currency code,
   CAPEX / OPEX / life-cycle symbol appears anywhere in the
   TASK-017 code path.

## 12. CI ownership plan

The future implementation PR must be observed against all of:

- `lint` job: `uv run --locked ruff check .`
- `typecheck` job: `uv run --locked mypy src/ tests/`
- `unit-tests` job: `uv run --locked pytest tests/material_mass_mechanical -q`
- `regression-tests` job: full suite, no regression vs. base.
- `docs-check` job (if present): confirms TASK_BACKLOG.md
  evidence row added with the Frozen Contract Authority SHA.
- `ci-shard-manifest` job: confirms `ci-shard-manifest.yml` was
  not modified by the implementation PR.

The implementation PR is **NOT** authorized to modify
`ci-shard-manifest.yml` or `.github/`.

## 13. Future implementation file boundary

The future implementation PR (NOT authorized by this design
contract) may only add files under:

- `src/hexagent/material_mass_mechanical/`
- `tests/material_mass_mechanical/`

#### 13.1 Naming rationale and boundary relationship

The proposed path `src/hexagent/material_mass_mechanical/` is
intentionally distinct from the existing TASK-013 path
(`src/hexagent/material_costs/`) and the TASK-016 path
(`src/hexagent/geometry_catalogs/`). The boundary is:

| Path | Owning task | Role | Authority |
|---|---|---|---|
| `src/hexagent/material_costs/` | TASK-013 (frozen) | Material / cost **data governance** — record schema, validation, license boundary, selection | Read-only canonical source for material properties |
| `src/hexagent/geometry_catalogs/` | TASK-016 (frozen) | Approved geometry **catalog** — record schema, validation, hashing | Read-only canonical source for geometry records |
| `src/hexagent/material_mass_mechanical/` | TASK-017 (this design) | Material / mass / preliminary mechanical **application layer** — consumes from TASK-013 + TASK-016, derives mass + mechanical checks | Application-layer derivation; never a canonical source |

The empty directory `src/hexagent/materials/` that pre-exists
in the repo is **NOT** part of any frozen contract and is **NOT**
claimed by TASK-017. TASK-017's chosen path deliberately avoids
that name to prevent future confusion with TASK-013's
`material_costs/` (the data layer) and to make the
"application-layer" semantics explicit in the directory name.

It MUST NOT modify:

- Any file under `src/hexagent/` outside the
  `material_mass_mechanical/` subtree.
- Any file under `tests/` outside the
  `material_mass_mechanical/` subtree.
- Any file under `docs/tasks/TASK-011-*.md` … `docs/tasks/TASK-016-*.md`.
- `ci-shard-manifest.yml`.
- Any file under `.github/`.
- `pyproject.toml` except for adding the new subtree to
  `[tool.setuptools.packages.find]` (no version bump, no new
  dependency).

If a future implementation needs to touch any other file, it
must open a separate Issue and obtain separate authorization.

## 14. Slice plan

TASK-017 implementation, when later authorized, is recommended
to be split into the following slices (each slice requires
its own authorization):

1. **TASK-017 Slice A** — MaterialSelector + read-only
   consumption of TASK-013 governance records. No mass, no
   mechanical checks. Brings new types
   `MaterialResolutionRequest/Result/Provenance` only.
2. **TASK-017 Slice B** — MassCalculator + MassBreakdown.
   Consumes Slice A. No mechanical checks.
3. **TASK-017 Slice C** — PreliminaryMechanicalChecker with
   allowable-stress check only. Consumes Slice A.
4. **TASK-017 Slice D** — PreliminaryMechanicalChecker extended
   with minimum-wall and straight-pipe-span checks. Consumes
   Slice A + B + C.
5. **TASK-017 closeout** — closes Issue (#72 or follow-up),
   merges closeout docs PR, records Frozen Contract Authority
   SHA in three places.

Each slice is independent enough to be reviewed separately and
small enough to keep review risk bounded.

## 15. Acceptance criteria

This design contract is acceptable to Charles only if:

1. All 19 sections in this design contract (background /
   non-goals / scope / forbidden scope / input-output /
   domain model / error model / provenance / determinism /
   JSON / test / CI / slice plan / acceptance / closeout /
   boundary to TASK-016 / non-authorization declaration /
   naming rationale / frozen contract checksum placeholder)
   are present and concrete. The minimum was 17 sections per
   Charles's authorization; this contract provides 19
   (the two extras are §13.1 naming rationale and §19 frozen
   contract checksum placeholder).
2. The `BLOCKED_FOR_DETAILED_DESIGN` boundary is documented
   and bounded.
3. The non-scope list explicitly excludes pressure-drop, C4,
   cost, new solver, and mutation of frozen contracts.
4. Provenance is mandatory on every result.
5. The future implementation file boundary restricts new code
   to a single new subtree.
6. The CI ownership plan documents **at least the four
   standard jobs** (`lint`, `typecheck`, `unit-tests`,
   `regression-tests`) plus optional `docs-check` and
   `ci-shard-manifest` jobs (§12).
7. The slice plan is small enough that each slice is reviewable
   in one round.

## 16. Closeout criteria

When this design contract is later approved and merged:

1. A closeout docs PR records the merge SHA in three places
   (Issue #72 body, design PR body, `docs/TASK_BACKLOG.md`
   evidence row).
2. The Frozen Contract Authority SHA appears in
   `docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md`
   Section "Frozen contract checksum" (added at merge time, not
   in this design PR).
3. TASK-017 implementation Issue is opened separately; it does
   NOT inherit authorization from this design kickoff.

## 17. Boundary to TASK-016

TASK-017 consumes TASK-016 geometry records **read-only**. The
following responsibilities are explicitly NOT migrated from
TASK-016 into TASK-017:

- Geometry approval state transitions.
- Geometry canonical hashing rules.
- Geometry source binding.
- Geometry consumer-side caching.
- Catalog loading and validation.

Conversely, TASK-017 does NOT introduce:

- A new geometry record type.
- A new geometry hashing rule.
- A modification to the TASK-016 catalog schema.

The TASK-016 closeout doc already states (§15): "TASK-017
material / mass / mechanical concerns remain absent." TASK-017
opens that layer without overlapping TASK-016's catalog
responsibilities.

## 18. Explicit non-authorization

This design contract does NOT authorize:

- TASK-017 production implementation.
- Any TASK-018+ work.
- Any pressure-drop / C4 / cost / new-solver work.
- Closing Issue #72.
- Marking the design PR Ready for review.
- Merging the design PR.

Future TASK-017 implementation requires a separate
implementation Issue and separate authorization.

## 19. Frozen contract checksum placeholder

The Frozen Contract Authority SHA is **NOT** established by this
design PR. It will be filled in at merge time by the closeout
PR. Format:

```
Frozen Contract Authority SHA: <to-be-filled-at-merge>
```

This section must not be edited to a real SHA before the
design PR has been merged.

## 20. Document history and prior-report wording notes

### 20.1 Prior-report wording issue (non-contractual)

The TASK-017 design-kickoff report (saved at
`.hermes/agents/.../sessions/.../task017-design-kickoff-report.md`)
wrote:

> "本轮 5 mutations: Issue #72 → design branch → design doc →
>  backlog update → push → Draft PR #73"

This enumerated **6** items (counting "push" and "Draft PR #73"
as two separate items) under a "5 mutations" label. The actual
mutational breakdown for that round was:

1. `POST /repos/.../issues` (Issue #72 creation) — 1 mutation
2. `git checkout -b` (design branch creation) — local-only, not a
   remote mutation
3. `git add` + `git commit` (design doc + backlog update, single
   commit) — 1 commit
4. `git push` (push to origin) — 1 mutation
5. `gh pr create --draft` (Draft PR #73) — 1 mutation

Net remote-side mutations: **3** (issue creation + commit push +
PR creation). The original "5 mutations" phrasing conflated the
3 remote mutations with 2 local operations (branch creation +
commit, both prerequisites of the push) and then enumerated all
6 action types. The label "5" was therefore a wording bug; the
correct count is 3 remote mutations.

This note is recorded here for audit transparency. It is
**non-contractual**: it does not modify any §1–§19 contract
provision and does not change the design intent. The design
contract itself (this document) is the canonical source of
truth for TASK-017 governance, not the prior kickoff report.

### 20.2 Document revision history

| Revision | Author | Date | Notes |
|---|---|---|---|
| Rev 1 (initial) | Charles via TASK-017 design kickoff | 2026-07-05 | Commit `06232fc710017e36d145d797333309cf59d8265a` — 19 sections |
| Rev 2 (remediation) | Charles via TASK-017 design remediation | 2026-07-05 | (this commit) — fixes P1-1, P1-2, P1-3, P2-1, P2-2, P2-4, P2-5; adds §13.1 (naming rationale), §20 (this note) |