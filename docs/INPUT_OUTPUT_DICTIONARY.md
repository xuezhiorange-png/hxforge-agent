# HXForge Input and Output Dictionary — v0.1 Draft

## 1. Dictionary rules

- All public numerical values must carry a unit.
- The internal calculation unit system is SI.
- Absolute temperature and temperature difference are different dimensions.
- Missing values are never replaced by hidden engineering defaults.
- Conditional fields must state the condition that makes them required.

## 2. Case-level inputs

| Field | Meaning | Type | Unit dimension | Requirement |
|---|---|---|---|---|
| `case_id` | Stable case identifier | UUID | — | generated |
| `name` | User-facing case name | string | — | required |
| `workflow` | screening, sizing or rating | enum | — | required |
| `exchanger_type` | requested family or auto-screen | enum | — | required |
| `standard_basis` | selected rule-pack reference | list/string | — | optional until mechanical work |
| `target_duty` | required heat-transfer rate | quantity | power | conditional |
| `area_margin_fraction` | required excess area | number | dimensionless | optional, no hidden default |

## 3. Stream inputs

| Field | Meaning | Type | Unit dimension | Requirement |
|---|---|---|---|---|
| `fluid.backend` | property backend | string | — | required |
| `fluid.name` | backend fluid identifier | string | — | required |
| `fluid.composition` | component fractions | mapping | fraction | conditional for mixtures |
| `mass_flow` | stream mass flow | quantity | mass/time | required unless solved variable is explicitly supported |
| `inlet_temperature` | inlet absolute temperature | quantity | temperature | required |
| `inlet_pressure` | inlet absolute pressure | quantity | pressure | required |
| `outlet_temperature` | outlet absolute temperature | quantity | temperature | conditional |
| `allowable_pressure_drop` | maximum permitted loss | quantity | pressure difference | required for constrained sizing |
| `fouling_resistance` | fouling thermal resistance | quantity | area·temperature/power | required or explicitly zero with source |
| `phase_hint` | auto, liquid, gas or two-phase | enum | — | optional |

## 4. Design constraints

| Field | Meaning | Type | Unit dimension | Requirement |
|---|---|---|---|---|
| `design_pressure_hot` | hot-side mechanical design pressure | quantity | pressure | required before mechanical checks |
| `design_pressure_cold` | cold-side mechanical design pressure | quantity | pressure | required before mechanical checks |
| `design_temperature_hot` | hot-side mechanical design temperature | quantity | temperature | required before mechanical checks |
| `design_temperature_cold` | cold-side mechanical design temperature | quantity | temperature | required before mechanical checks |
| `corrosion_allowance` | thickness allowance | quantity | length | optional only when mechanical work is not requested |
| `material_constraints` | allowed/prohibited materials | object | — | optional for screening, required for material selection |
| `footprint_limits` | maximum dimensions | object | length | optional |
| `maintenance_constraints` | cleaning/removal/access rules | object | — | optional |

## 5. Geometry inputs for rating

Geometry is exchanger-specific. Every rating workflow must provide a versioned geometry schema. Unknown or unsupported geometry fields must be rejected rather than ignored.

## 6. Common outputs

| Field | Meaning | Type | Unit/status |
|---|---|---|---|
| `run_id` | calculation-run identifier | UUID | — |
| `status` | calculation state | enum | — |
| `duty` | calculated or specified heat transfer | quantity | power |
| `energy_balance_error` | normalized hot/cold residual | number | fraction |
| `outlet_states` | solved stream outlets | object | unit-bearing |
| `pressure_drop_hot` | calculated hot-side loss | quantity | pressure difference |
| `pressure_drop_cold` | calculated cold-side loss | quantity | pressure difference |
| `geometry` | selected or supplied geometry | object | versioned schema |
| `warnings` | non-fatal engineering conditions | list | structured |
| `blockers` | fatal conditions | list | structured |
| `provenance` | formula/property/version trace | list/object | structured |
| `confidence` | preliminary, review-required or verified | enum | — |

## 7. Default policy

Permitted software defaults are limited to non-engineering behavior such as pagination or display formatting. Engineering defaults require an approved decision-log entry, a visible source and a user-facing warning.
