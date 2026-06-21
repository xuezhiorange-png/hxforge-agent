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
| `standard_basis` | selected rule-pack reference | object: {standard_id: string, edition: string, scope: string} | — | optional until mechanical work |
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
| `fouling_resistance.value` | fouling thermal resistance | quantity | area·temperature/power | required or explicitly zero with source |
| `fouling_resistance.source` | structured fouling source object (see DEC-017) | object | — | required; fields: source_type, reference_id, edition, table_or_clause, note |
| `velocity_limit_max` | maximum allowable flow velocity | quantity | length/time | optional |
| `velocity_limit_min` | minimum required flow velocity | quantity | length/time | optional |
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

## 5A. Double-pipe geometry schema (rating)

For double-pipe rating, the geometry object must include:

| Field | Meaning | Type | Unit dimension | Requirement |
|---|---|---|---|---|
| `inner_tube_id` | inner tube inner diameter | quantity | length | required |
| `inner_tube_od` | inner tube outer diameter | quantity | length | required |
| `outer_tube_id` | outer tube inner diameter | quantity | length | required |
| `tube_length` | single-tube effective length | quantity | length | required |
| `hairpin_count` | number of hairpin elements | integer | — | required |
| `circuit_arrangement` | series, parallel, or mixed | enum | — | required |
| `material` | tube and shell material identifier | string | — | required |
| `inner_tube_roughness` | absolute roughness of inner tube wetted surface | quantity | length | required or resolved from material catalog with provenance |
| `annulus_roughness` | absolute roughness of annulus wetted surfaces | quantity | length | required or resolved from material catalog with provenance |

Unknown fields in the geometry object must cause a BLOCKED status, not be silently ignored.

## 6. Common outputs

| Field | Meaning | Type | Unit/status |
|---|---|---|---|
| `run_id` | calculation-run identifier | UUID | — |
| `workflow_stage` | execution state (see DEC-006 §7.1) | enum | one of: DRAFT, INPUT_VALIDATED, THERMAL_SERVICE_RESOLVED, TECHNOLOGIES_SCREENED, CANDIDATES_GENERATED, CANDIDATES_RATED, ENGINEERING_CHECKED, COSTED, VERIFICATION_COMPLETED, REPORT_READY, BLOCKED, NOT_IMPLEMENTED, NON_CONVERGED |
| `verification_level` | evidence maturity (see DEC-006 §7.2) | enum | one of: UNVERIFIED, PRELIMINARY, BENCHMARK_VALIDATED, ENGINEERING_APPROVED, N/A |
| `requires_review` | derived: human review needed before use | boolean | true when warnings exist or verification_level is UNVERIFIED/PRELIMINARY |
| `duty` | calculated or specified heat transfer | quantity | power |
| `energy_balance_error` | normalized hot/cold residual | number | fraction |
| `outlet_states` | solved stream outlets | object | unit-bearing |
| `pressure_drop_hot` | calculated hot-side loss | quantity | pressure difference |
| `pressure_drop_cold` | calculated cold-side loss | quantity | pressure difference |
| `geometry` | selected or supplied geometry | object | versioned schema |
| `warnings` | non-fatal engineering conditions | list | structured |
| `blockers` | fatal conditions | list | structured |
| `provenance` | formula/property/version trace | list/object | structured |
| `result_hash` | deterministic hash of canonical inputs + outputs (see §8) | string | — | always |
| `software_version` | HXForge version used | string | — | always |
| `property_backend_version` | property provider version | string | — | always when properties used |

## 7. Default policy

Permitted software defaults are limited to non-engineering behavior such as pagination or display formatting. Engineering defaults require an approved decision-log entry, a visible source and a user-facing warning.

## 8. Provenance and result-hash semantics

Every calculation run must record:
- Input snapshot (all user-provided and resolved values with units)
- Unit conversion records (input unit → SI unit for each quantity)
- Property backend identifier and version
- Correlation ID and version for each formula invoked
- Applicability status for each correlation call (VALID, WARNING, REJECTED)
- Intermediate results at each solver step
- Convergence status and iteration count (for iterative solvers)
- Warnings and blockers with severity codes
- Software version and Git commit hash

### 8.1 Result hash (deterministic)

`result_hash` is a SHA-256 hash of a canonical JSON payload. The payload includes **only** deterministic, reproducible fields:

**Included in hash payload:**
- All resolved input values (after unit normalization to SI)
- `workflow_stage` (final value)
- `verification_level` (final value)
- Deterministic calculation outputs (duty, outlet states, pressure drops, geometry)
- Formula/property backend names and versions
- Software version and Git commit hash
- `energy_balance_error`

**Excluded from hash payload:**
- `result_hash` itself (self-reference)
- `run_id` (random UUID)
- Timestamps, display formatting, locale-dependent text
- `requires_review` (derived from warnings, which are included)
- Warning/blocker message text (codes are included)

**Numeric canonicalization:**
- All floats are serialized with full precision (Python `repr` or equivalent)
- Units are normalized to SI before hashing
- Object keys are sorted alphabetically
- Lists are order-dependent (input order is part of the hash)

Sensitive information (API keys, customer names, internal cost data) must not appear in provenance records or hash payloads.
