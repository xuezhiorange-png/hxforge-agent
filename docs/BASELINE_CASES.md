# HXForge v0.1 Baseline Representation Cases

These cases validate the product requirements and public data dictionary. They are documentation cases, not calculation benchmarks. No numerical result in this file is an approved Golden result.

## CASE-001 — Water-to-water double-pipe sizing

**Purpose:** prove that the first complete vertical slice can represent a normal single-phase liquid-liquid sizing request, including over-specified consistency checking.

**Workflow:** `sizing`  
**Requested exchanger:** `double_pipe`

**Hot stream inputs**

| Field | Value |
|---|---|
| fluid.backend | CoolProp |
| fluid.name | Water |
| mass_flow | 2.0 kg/s |
| state_spec | {type: "TP", temperature: {value: 90, unit: "°C"}, pressure: {value: 4, unit: "bar(a)"}} |
| outlet_temperature | 60 °C |
| allowable_pressure_drop | 50 kPa |
| fouling_resistance.value | 0.0002 m²·K/W |
| fouling_resistance.source | {source_type: "STANDARD", reference_id: "TEMA-RGP-T-2.4", edition: "TBD", table_or_clause: "TBD", verification_status: "UNVERIFIED_REFERENCE", note: "Placeholder pending licensed rule-pack verification"} |

**Cold stream inputs**

| Field | Value |
|---|---|
| fluid.backend | CoolProp |
| fluid.name | Water |
| mass_flow | 2.0 kg/s |
| state_spec | {type: "TP", temperature: {value: 20, unit: "°C"}, pressure: {value: 3, unit: "bar(a)"}} |
| outlet_temperature | solved variable |
| allowable_pressure_drop | 50 kPa |
| fouling_resistance.value | 0.0002 m²·K/W |
| fouling_resistance.source | {source_type: "STANDARD", reference_id: "TEMA-RGP-T-2.4", edition: "TBD", table_or_clause: "TBD", verification_status: "UNVERIFIED_REFERENCE", note: "Placeholder pending licensed rule-pack verification"} |

**Case constraints**

- target_duty: 250 kW (input specification, value to be verified against hot-side energy balance);
- area_margin_fraction: explicitly selected by user;
- material and geometry catalog: approved rule/catalog reference;
- design_pressure_hot, design_pressure_cold, design_temperature_hot, design_temperature_cold: required before mechanical screening.

**Specification closure note:** This case is deliberately over-specified (hot-side inlet + outlet temperatures AND target_duty are all provided). The specification-closure checker should verify energy balance consistency: if `abs(Q_hot - target_duty) / max(Q_hot, target_duty, 1 W) > tolerance`, return BLOCKED with inconsistency message; if consistent, proceed with a consistency warning recorded in provenance.

**Expected documentation behavior**

- input can be represented without hidden fields using the I/O dictionary;
- specification closure is checked before geometry generation;
- output carries `workflow_stage`, `verification_level`, and `requires_review`;
- initial `verification_level` is `UNVERIFIED` or `PRELIMINARY`;
- `requires_review` is `true` (verification_level is not ENGINEERING_APPROVED);
- output includes multiple manufacturable candidates, warnings and provenance.

---

## CASE-002 — Fixed-geometry double-pipe rating

**Purpose:** prove that rating is distinct from sizing and requires a versioned geometry schema resolved from a catalog.

**Workflow:** `rating`  
**Requested exchanger:** `double_pipe`

**Hot stream inputs**

| Field | Value |
|---|---|
| fluid.backend | CoolProp |
| fluid.name | Water |
| mass_flow | 1.8 kg/s |
| state_spec | {type: "TP", temperature: {value: 85, unit: "°C"}, pressure: {value: 5, unit: "bar(a)"}} |
| fouling_resistance.value | 0.0002 m²·K/W |
| fouling_resistance.source | {source_type: "STANDARD", reference_id: "TEMA-RGP-T-2.4", edition: "TBD", table_or_clause: "TBD", verification_status: "UNVERIFIED_REFERENCE", note: "Placeholder pending licensed rule-pack verification"} |

**Cold stream inputs**

| Field | Value |
|---|---|
| fluid.backend | CoolProp |
| fluid.name | Water |
| mass_flow | 2.5 kg/s |
| state_spec | {type: "TP", temperature: {value: 25, unit: "°C"}, pressure: {value: 4, unit: "bar(a)"}} |
| fouling_resistance.value | 0.0002 m²·K/W |
| fouling_resistance.source | {source_type: "STANDARD", reference_id: "TEMA-RGP-T-2.4", edition: "TBD", table_or_clause: "TBD", verification_status: "UNVERIFIED_REFERENCE", note: "Placeholder pending licensed rule-pack verification"} |

**Geometry object (versioned, catalog-resolved)**

| Field | Value | Provenance |
|---|---|---|
| schema_version | "1.0" | — |
| catalog_id | "HXFORGE-DP-CATALOG-001" | — |
| catalog_revision | "0.1.0-draft" | — |
| catalog_source | "HXForge internal standard catalog (draft)" | Pending validation against commercial pipe schedules |
| geometry_entry_id | "DP-CS-25x33-Sch40-6m" | — |
| inner_tube_id | 25.4 mm | Schedule 40 per catalog entry |
| inner_tube_od | 33.4 mm | Schedule 40 per catalog entry |
| outer_tube_id | 52.5 mm | Schedule 40 per catalog entry |
| tube_length | 6.0 m | Catalog maximum for this entry |
| hairpin_count | 4 | User-specified |
| circuit_arrangement | series | User-specified |
| inner_tube_material | Carbon steel ASTM A106 Gr.B | Catalog entry material |
| outer_tube_material | Carbon steel ASTM A106 Gr.B | Catalog entry material |
| inner_tube_roughness | 0.046 mm | Source: catalog material properties, commercial steel default |
| annulus_roughness | 0.046 mm | Source: catalog material properties, commercial steel default |

**Optional:** allowable_pressure_drop limits for pass/fail comparison.

**Expected documentation behavior**

- no geometry is generated by the rating workflow;
- geometry dimensions must reconcile with the referenced catalog entry;
- unknown geometry fields are rejected rather than ignored (BLOCKED status);
- output carries `workflow_stage`, `verification_level`, and `requires_review`;
- `requires_review` is `true` (verification_level is not ENGINEERING_APPROVED);
- output contains calculated duty, outlet states, pressure-drop components, thermal resistance components, convergence information, warnings and provenance;
- unsupported geometry schema versions return `NOT_IMPLEMENTED`.

---

## CASE-003 — Gas-to-liquid shell-and-tube technology screening

**Purpose:** prove that a family can participate in screening before a validated detailed solver is available.

**Workflow:** `screening`  
**Requested exchanger:** `auto`

**Fixed fluids and conditions**

| Parameter | Hot side | Cold side |
|---|---|---|
| Fluid (backend) | Air (CoolProp) | Water (CoolProp) |
| Phase hint | `gas` | `liquid` |
| Mass flow | 1.5 kg/s | 3.0 kg/s |
| state_spec | {type: "TP", temperature: {value: 150, unit: "°C"}, pressure: {value: 3, unit: "bar(a)"}} | {type: "TP", temperature: {value: 25, unit: "°C"}, pressure: {value: 4, unit: "bar(a)"}} |
| Outlet temperature | 80 °C (specified) | solved variable |
| Allowable pressure drop | 15 kPa | 30 kPa |
| fouling_resistance.value | 0.0001 m²·K/W | 0.0002 m²·K/W |
| fouling_resistance.source | {source_type: "STANDARD", reference_id: "TEMA-RGP-T-2.4", edition: "TBD", table_or_clause: "TBD", verification_status: "UNVERIFIED_REFERENCE", note: "Placeholder pending licensed rule-pack verification"} | {source_type: "STANDARD", reference_id: "TEMA-RGP-T-2.4", edition: "TBD", table_or_clause: "TBD", verification_status: "UNVERIFIED_REFERENCE", note: "Placeholder pending licensed rule-pack verification"} |

**Constraints:** footprint max 3 m × 1.5 m; maintenance access from both ends.

**Expected documentation behavior**

- screening may rank double-pipe, shell-and-tube, plate or air-cooled concepts where technically relevant;
- detailed shell-and-tube sizing/rating is NOT_IMPLEMENTED at this milestone;
- result explains why each family is included or excluded;
- `workflow_stage` is `TECHNOLOGIES_SCREENED` with `verification_level = UNVERIFIED`;
- `requires_review` is `true` (verification_level is UNVERIFIED);
- downstream calculation requirements flagged as NOT_IMPLEMENTED.

---

## CASE-004 — Plate-exchanger screening with sanitation constraints

**Purpose:** ensure that non-thermal requirements influence technology selection.

**Workflow:** `screening`  
**Requested exchanger:** `plate`

**Fixed fluids and conditions**

| Parameter | Hot side | Cold side |
|---|---|---|
| Fluid (backend) | Water (CoolProp) | Water (CoolProp) |
| Phase hint | `liquid` | `liquid` |
| Mass flow | 5.0 kg/s | 4.5 kg/s |
| state_spec | {type: "TP", temperature: {value: 72, unit: "°C"}, pressure: {value: 6, unit: "bar(a)"}} | {type: "TP", temperature: {value: 10, unit: "°C"}, pressure: {value: 4, unit: "bar(a)"}} |
| Outlet temperature | solved variable | solved variable |
| Target duty | 500 kW | — |
| Allowable pressure drop | 40 kPa | 40 kPa |
| fouling_resistance.value | 0.00015 m²·K/W | 0.00015 m²·K/W |
| fouling_resistance.source | {source_type: "STANDARD", reference_id: "TEMA-RGP-T-2.4", edition: "TBD", table_or_clause: "TBD", verification_status: "UNVERIFIED_REFERENCE", note: "Placeholder pending licensed rule-pack verification"} | {source_type: "STANDARD", reference_id: "TEMA-RGP-T-2.4", edition: "TBD", table_or_clause: "TBD", verification_status: "UNVERIFIED_REFERENCE", note: "Placeholder pending licensed rule-pack verification"} |

**Required constraints**

- hygienic design requirement (reference: 3-A Sanitary Standards or EHEDG — verification against specific standard pending licensed rule-pack);
- CIP compatibility (hot caustic and acid wash cycles — specific concentration, temperature and duration to be defined by user);
- wetted material restricted to AISI 316L stainless steel;
- gasket material: EPDM — **requires verification** that EPDM is compatible with the specific CIP chemistry, temperature and concentration before acceptance; this is a screening constraint, not an unconditional fact;
- preferred construction: gasketed plate (brazed not permitted due to CIP requirement);
- maintenance access: plates must be removable for inspection;
- footprint limit: 2 m × 1 m.

**Expected documentation behavior**

- technology screening records sanitation, gasket, cleaning and maintenance constraints;
- a generic plate model is not claimed to be equivalent to a proprietary vendor plate;
- missing licensed plate geometry prevents detailed rating but does not prevent high-level screening;
- EPDM compatibility is flagged as requiring verification, not stated as fact;
- output states the evidence and uncertainty behind the recommendation.

---

## CASE-005 — Unsupported two-phase refrigerant evaporator

**Purpose:** verify that an architecturally planned feature is not presented as implemented engineering capability, and that two-phase state specifications are representable.

**Workflow:** `rating`  
**Service:** R134a evaporation with a two-phase region.

**Fixed inputs**

| Parameter | Value |
|---|---|
| workflow | rating |
| exchanger_type | double_pipe |
| hot fluid.backend | CoolProp |
| hot fluid.name | R134a |
| hot phase_hint | two_phase |
| hot mass_flow | 0.15 kg/s |
| hot state_spec | {type: "PQ", pressure: {value: 3.0, unit: "bar(a)"}, quality: 0.3} |
| cold fluid.backend | CoolProp |
| cold fluid.name | Water |
| cold phase_hint | liquid |
| cold mass_flow | 2.0 kg/s |
| cold state_spec | {type: "TP", temperature: {value: 25, unit: "°C"}, pressure: {value: 4, unit: "bar(a)"}} |

**Expected documentation behavior**

- the PQ state specification is validly representable in the public I/O dictionary (Section 3A);
- service classification identifies phase change (two-phase inlet on hot side);
- the v0.1 single-phase solver is not used as a fallback;
- `workflow_stage` is `NOT_IMPLEMENTED`; `verification_level` is `N/A`; `requires_review` is `false` (no result to review);
- no heat-transfer coefficient, pressure drop or geometry recommendation is guessed;
- report clearly states the missing capability and required future task (TASK-080+).

---

## Representation review checklist

For each case, reviewers confirm:

- [ ] all numerical inputs carry explicit units;
- [ ] absolute pressure and pressure difference are distinguished;
- [ ] absolute temperature and temperature difference are distinguished;
- [ ] required, conditional and optional fields are identifiable;
- [ ] no undocumented engineering default is necessary;
- [ ] expected output fields include `workflow_stage`, `verification_level`, and `requires_review`;
- [ ] unsupported behavior is explicit;
- [ ] human engineering review responsibility is visible;
- [ ] every case names a specific fluid and property backend;
- [ ] fouling source fields use valid `source_type` enum values (STANDARD/VENDOR/USER/ASSUMED) with `verification_status: UNVERIFIED_REFERENCE` where applicable;
- [ ] CASE-005 uses a defined `state_spec` schema (PQ) from Section 3A;
- [ ] CASE-002 geometry reconciles with referenced catalog entry;
- [ ] all cases correctly derive `requires_review` per the tightened DEC-006 definition.
