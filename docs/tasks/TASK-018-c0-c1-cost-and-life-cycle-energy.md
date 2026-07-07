# TASK-018 — C0/C1 Cost Model and Life-Cycle Energy Estimate Design Contract

> Design contract for TASK-018. Defines the deterministic application layer that consumes the **TASK-013 cost-data governance** records (frozen) and the **TASK-017 mass / mechanical application layer** outputs (frozen) to produce a C0/C1 cost model and a bounded life-cycle energy estimate for double-pipe heat-exchanger cases.
>
> This document is design-only: no production code, no public API, no report rendering, no database schema, no C2/C3 work, no pressure-drop implementation, no C4 logic, no life-cycle energy computation, no TASK-019+ content, and no mutation of any frozen contract is introduced by this design PR.
>
> The frozen design contract status (`DESIGN FROZEN`) is established only after Charles authorizes `Ready → Merge` in a separate round. This file is the candidate contract under `Issue #76` for that freeze.

## 1. Authority and status

| Field | Value |
|---|---|
| Authorizing issue | #76 |
| Backlog item | TASK-018 — Add C0/C1 cost model and life-cycle energy estimate |
| Backlog status before authorization | `PLANNED` |
| Backlog dependency | TASK-009, TASK-013, TASK-017 |
| Dependency status at design freeze window | TASK-009 work on main (squash-closed by #24); TASK-013 closed/completed (#46 design, #49 impl); TASK-017 closed/completed (#72 design, #74 impl) |
| Design branch | `docs/task-018-c0-c1-cost-life-cycle-energy-design` |
| Design file | `docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md` (this file) |
| Base authority | TASK-017 implementation merge `5f96cf761d470b82faa1a5d164eefd42360c7df9` (PR #75, `merged_at 2026-07-06T06:32:24Z`) |
| Upstream contracts consumed (read-only) | TASK-013 cost-data governance contract (frozen), TASK-017 mass / mechanical contract (frozen), MASTER_DEVELOPMENT_SPEC §10 (cost categorization C0..C3 + life-cycle list) |
| Design contract status | **DRAFT** (Issue #76 OPEN; PR not yet opened in this proposal) |
| Frozen Contract Authority Commit SHA | **TBD** (set when design PR is reviewed PASS, frozen, and merged; self-reference guard per §19.1) |
| Frozen Contract Authority Base SHA | `5f96cf761d470b82faa1a5d164eefd42360c7df9` |
| Implementation status | **NOT AUTHORIZED** |
| Implementation Issue | NOT YET CREATED |
| TASK-019+ status | NOT STARTED |
| PR (this design) | DRAFT / NOT READY / NOT MERGED |
| Issue #76 status | OPEN (not closed in this round; closeout happens with a separate closeout PR + Charles authorization per TASK-013/014/015/016/017 closeout precedent) |

Implementation work is explicitly blocked until this design contract is reviewed, merged, and closeout-posted under a separate Charles authorization. The "frozen" wording in the table above is the **target** state; the current state is DRAFT.

## 2. Problem statement

The double-pipe vertical slice currently has thermal correlations, fixed-geometry rating, manufacturable sizing, standards rule-pack, material / cost **data governance**, immutable case revisions, geometry **catalog**, materials / mass / preliminary mechanical application layer, and CI / security / release hardening contracts merged on main. The next M2 layer is the **deterministic cost and life-cycle-energy model** that consumes those frozen data layers and produces a bounded, governance-compliant envelope for client-side cost screens and life-cycle energy displays.

Without an explicit TASK-018 contract, future code can drift in any of the following ways:

1. Re-deriving C0 heuristic coefficients, C1 labor/minute formulas, or material unit prices inline instead of consuming TASK-013 cost-data records (governance layer).
2. Mixing currency conversions, escalation math, or region-specific tax/installation factor handling inside cost records themselves, instead of returning them through TASK-013's pre-existing escalation-record-and-pointer rules (§11 of TASK-013).
3. Embedding restricted price-list bodies, vendor quote bodies, or proprietary cost-handbook content into engineering artifacts in violation of TASK-013 §9 license boundary.
4. Reading mass or preliminary mechanical numbers from a non-canonical recomputation rather than the frozen TASK-017 outputs, causing cost/energy numbers to diverge from the governance-tracked mass breakdown.
5. Prematurely introducing C2 history-project regression or C3 vendor quotation interfaces before the data governance for those sources exists, producing unstable interfaces with no upstream license boundary.
6. Treating preliminary mechanical checks as authoritative structural design — preliminary checks must surface `BLOCKED_FOR_DETAILED_DESIGN` for any geometry that exceeds the screening envelope.
7. Pre-committing to a discount-rate model in the engineering kernel; discount rate must be an `INPUT`, not a constant (the design contract must state this explicitly).
8. Re-introducing two-phase / refrigerants / shell-and-tube / plate / air-cooler / microchannel content (TASK-020+), or pressure-drop / C4 logic, in what is supposed to be a cost- and energy-only layer.
9. Embedding life-cycle energy computation under the design without explicit user-supplied inputs (operating hours, discount rate, life years, residual salvage), silently producing non-traceable numbers.

TASK-018 closes this design gap by freezing the application-layer contract before any cost / energy implementation.

## 3. Scope and non-scope

### 3.1 In scope for this design contract

1. **C0 cost model** definition: rule-of-thumb / engineering-estimate style cost categories that consume TASK-013 cost-data records (`cost_category` ∈ closed set per TASK-013 §6.1), inherit ISO 4217 currency + ISO 3166-1 region + effective_date + escalation semantics, and produce a `C0CostSubtotal` output shape. The design contract defines the input envelope and output shape; **no computation** is introduced.
2. **C1 cost model** definition: material-weight + man-hour + labor-burden cost categories that consume TASK-017 mass totals (`MassBreakdown`) plus TASK-013 labor-minute records, and produce a `C1CostSubtotal` output shape. **No computation** is introduced.
3. **CostModelSelector** (per §5.1) that selects TASK-013 cost records deterministically based on case attributes; defines inputs and outputs, not implementation.
4. **CostCalculator** (per §5.2) that produces a `CostBreakdown` envelope aggregating C0 + C1 sub-totals, currency-tagged, escalation-aware, provenance-attached.
5. **LifeCycleEnergyEstimator** (per §5.3) that produces a `LifeCycleEnergyBreakdown` envelope that consumes the heat-transfer results from the existing thermal path, TASK-017 mechanical envelope (where relevant), plus **user-supplied** inputs (`annual_operating_hours`, `discount_rate`, `design_life_years`, `salvage_fraction`, `fouling_energy_penalty_factor`), and surfaces an envelope-only output (`LCC energy summary`) without prescribing the calculation.
6. **Currency / region / date / escalation rules** inherited from TASK-013 §11 with extension rules for adding `discount_rate` and `design_life_years` as INPUT-only fields.
7. **Provenance requirements** that every C0/C1 sub-total and every life-cycle-energy summary entry must carry `cost_record_id` (or `correlation_id`), `source_class`, `cost_basis`, `escalation_index_reference`, and `license_class`.
8. **License boundary** clause that explicitly inherits TASK-013 §9 restricted-source rules; no embedding of restricted source bodies in cost outputs.
9. **Error / blocker model** with a frozen closed-set of error codes (mirrors TASK-013/014/015/016/017 precedent).
10. **JSON canonicalization / deterministic hash / ordering rules** following RFC 8785 (per TASK-013 §16 inheritance + TASK-017 §10 extension).
11. **Future test strategy** specifying test classes for C0 / C1 / life-cycle energy (deterministic, golden, license-boundary, frozen-contract-unchanged).
12. **CI ownership plan** specifying how future implementation slices register their own test files in the existing `ci` shard per the TASK-017 §13.2 slice-authorization pattern.
13. **Future implementation file boundary**: `src/hexagent/costing/` and `tests/costing/`.
14. **Slice plan** mirroring TASK-017 §14 (A selector + B calculator + C life-cycle-energy + D closeout).
15. **Acceptance + closeout criteria** mirrors TASK-017.
16. **Boundary clauses** to TASK-013 cost-data governance (read-only) and TASK-017 mass/mechanical outputs (read-only).
17. **Frozen contract authority model** declaring the three-way SHA synchronization and self-reference guard.

### 3.2 Explicit non-scope

This design contract does **not** authorize:

- TASK-018 production implementation under `src/hexagent/costing/`.
- Any TASK-019+ task, including "Add Golden cases and double-pipe validation report" (TASK-019).
- **C2 historical-project regression** (vendor / customer / internal project history table regression).
- **C3 vendor quotation** interface, supplier quote ingestion, or RFP / quote body handling.
- Any **pressure-drop implementation**, **C4 logic**, or any pressure-drop correlation.
- Any new solver, any modification to existing production solver behavior under `src/hexagent/`.
- Any re-implementation of unit prices, currency conversions, escalation math, or region-specific tax/installation factors inside the cost record itself (those live in TASK-013 cost-data layer and are read-only consumers here; per TASK-013 §11 escalation MUST go through `cost_value.escalation_index_reference`, never embedded).
- Any re-implementation of mass totals, component allocation, or preliminary mechanical check logic inside the cost layer (those live in TASK-017 and are read-only consumers here).
- Any embedding of restricted price-list bodies, vendor quote bodies, or proprietary cost-handbook content (per TASK-013 §9).
- Any mutation of `src/`, `tests/`, `.github/`, `ci-shard-manifest.yml`, `pyproject.toml`.
- Any mutation of TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015 / TASK-015A / TASK-016 / TASK-017 frozen contracts.
- Any detailed mechanical, structural, fatigue, creep, seismic, weld, NDE, or detailed cost engineering (those return `BLOCKED_FOR_DETAILED_DESIGN` from the cost layer and are out of scope).
- Any two-phase, refrigerants, shell-and-tube, plate, air cooler, or microchannel content (TASK-020+).
- Pre-committing to a discount rate or life-years default; those must be INPUT, not constants.
- Secret registration, OIDC trust, registry push, or external service integration.
- Closing the authorizing Issue (`#76`).
- Marking the design PR Ready for review.
- Merging the design PR.
- Feishu outbound from the design round.

## 4. Design goals

1. **Deterministic** — same TASK-013 cost records + same TASK-017 mass outputs + same user-supplied life-cycle inputs → same `CostBreakdown` and `LifeCycleEnergyBreakdown` byte-for-byte. JSON canonicalization (RFC 8785) + input-ordered `escalation_index_reference` ensures reproducibility.
2. **Governance-compliant** — every C0/C1 sub-total and every life-cycle-energy summary entry inherits the TASK-013 §11 currency / region / date / escalation shape and the TASK-013 §9 license boundary.
3. **Read-only consumer** — TASK-018 consumes TASK-013 cost-data records and TASK-017 mass / mechanical outputs as **read-only**; the cost layer never mutates cost records, mass records, or geometry records.
4. **License-respecting** — explicit surface for `license_class` and `restriction_class` per output element; restricted bodies never appear in engineering artifacts.
5. **Input-first lifecycle** — life-cycle energy estimate is input-driven (`annual_operating_hours`, `discount_rate`, `design_life_years`, `salvage_fraction`, `fouling_energy_penalty_factor`) with no internal defaults for the discount/rate/life choices.
6. **Provenance-attached** — every output element carries `source_record_ids` and `correlation_id`s; numbers without provenance are blockers.
7. **Bounded** — preliminary mechanical checks surface `BLOCKED_FOR_DETAILED_DESIGN` for any geometry beyond the screening envelope; the cost / energy layer does the same when cost inputs are outside the C0/C1 envelope (e.g. when a project exceeds the cost-record's `validity_envelope`).
8. **C2 / C3-explicit** — the design contract explicitly states that C2 / C3 belong to future tasks and that those interfaces are NOT defined here. Any future attempt to add them via TASK-018 implementation is a blocking review finding.
9. **Schema-versioned** — outputs carry `schema_version` (semver) following TASK-013 §5.5 / TASK-014 §7 inheritance.

## 5. Domain model

This section defines the input envelopes and output envelopes for the three top-level cost-model / energy-estimate components. The components are **defined**, not implemented, by this design contract.

### 5.1 CostModelSelector

#### 5.1.1 TASK-013 cost-records lookup (input contract)

| Input | Type | Required | Source |
|---|---|---|---|
| `material_family` | enum (TASK-013 §5.1 closed set) | yes | caller (from TASK-017 `MaterialResolutionResult.material_family`) |
| `case_region` | enum ISO 3166-1 alpha-2 or `"INTL"` | yes | caller (case-level) |
| `effective_date` | RFC 3339 UTC `Z` string | yes | caller (case-level) |
| `cost_category_filter` | set of TASK-013 §6.1 cost_category enum values | yes | TASK-018 (e.g. `{"c0_baseline_estimate", "c1_material_weight", "c1_man_hours_labor"}`) |
| `validity_envelope` | object `{max_material_density_kg_m3, max_unit_price_currency, ...}` | yes | TASK-018 (forward-looking envelope based on geometry) |
| `quantity_basis_filter` | set of TASK-013 §6.3 quantity_basis enum values | yes | TASK-018 (e.g. `{"currency_per_kg", "currency_per_hour"}`) |
| `escalation_index_reference_filter` | set of `cost_record_id` strings | no | TASK-018 caller; if absent, no escalation selection |
| `license_class_filter` | set of license strings | yes | TASK-018 caller (e.g. `{"public_open", "internal_open"}`); default excludes `proprietary_restricted` |

#### 5.1.2 TASK-018 required canonical cost-record fields

The selector MUST return TASK-013 cost records that satisfy the filters above, projected to a canonical shape:

| Output field | Type | Source |
|---|---|---|
| `cost_record_id` | string | TASK-013 cost record |
| `cost_record_version` | semver string | TASK-013 |
| `cost_category` | enum | TASK-013 §6.1 |
| `cost_basis` | enum | TASK-013 §6.2 |
| `currency` | ISO 4217 alpha | TASK-013 |
| `quantity_basis` | enum | TASK-013 §6.3 |
| `cost_value` | canonical value payload | TASK-013 §6.4 |
| `escalation_index_reference` | `cost_record_id` or `null` | TASK-013 §11 |
| `license_class` | string | TASK-013 §9 |
| `source_class` | enum | TASK-013 §4 |
| `validity_envelope` | object | TASK-013 |

#### 5.1.3 CostModelSelectionResult shape

```jsonc
{
  "schema_version": "0.1.0",
  "selector_run_id": "<deterministic uuid v5 over canonical inputs>",
  "c0_records": [
    /* 1..N TASK-013 cost records with cost_category starting with `c0_` */
  ],
  "c1_records": [
    /* 1..N TASK-013 cost records with cost_category starting with `c1_` */
  ],
  "selection_warnings": [
    /* non-fatal issues (e.g. preferred currency missing in region; fallback used) */
  ],
  "selection_blockers": [
    /* fatal issues (e.g. required cost_category has no records in region) */
  ],
  "license_class_summary": {
    "public_open_count": 0,
    "internal_open_count": 0,
    "proprietary_restricted_count": 0
  }
}
```

Selection rules:

- Order of records within `c0_records` / `c1_records` is by `cost_record_id` ascending (deterministic), then `cost_record_version` descending (latest first within each id).
- All `proprietary_restricted`-class records are surfaced **only** as `cost_record_id` pointers; no `cost_value` body is exposed in the result.
- A `selection_blockers` array with ≥1 element makes the result `NOT_COMPUTABLE`.

### 5.2 CostCalculator

#### 5.2.1 Input envelope

| Input | Type | Required | Source |
|---|---|---|---|
| `cost_model_selection_result` | `CostModelSelectionResult` (§5.1.3) | yes | `CostModelSelector` |
| `mass_breakdown` | TASK-017 `MassBreakdown` | yes (for C1 only) | TASK-017 |
| `component_role_overrides` | dict `component_role → material_family` | no | caller |
| `c0_heuristic_overrides` | dict `cost_category → multiplier` | no | caller (e.g. `--c0_compactness=0.9`); must be `BLOCKED` if any override's multiplicative effect > documented C0 envelope |
| `case_currency` | ISO 4217 alpha or `"SOURCE"` (= use cost record's `currency` as-is) | yes | caller |
| `case_region` | ISO 3166-1 alpha-2 or `"INTL"` | yes | caller |
| `effective_date` | RFC 3339 UTC `Z` string | yes | caller |

#### 5.2.2 Output envelope — CostBreakdown

```jsonc
{
  "schema_version": "0.1.0",
  "calculator_run_id": "<deterministic uuid v5 over canonical inputs>",
  "cost_breakdown": {
    "c0_subtotal": {
      "amount_minor_units": <integer>,
      "currency": "<ISO 4217>",
      "component_breakdown": [
        /* per-component-role C0 sub-totals */
      ],
      "source_record_ids": ["<cost_record_id>", ...]
    },
    "c1_subtotal": {
      "amount_minor_units": <integer>,
      "currency": "<ISO 4217>",
      "component_breakdown": [
        /* per-component-role C1 sub-totals (material weight + labor minutes) */
      ],
      "source_record_ids": ["<cost_record_id>", ...]
    },
    "capex_envelope_minor_units": <integer>,
    "capex_envelope_currency": "<ISO 4217>",
    "escalation_pointer_used": "<cost_record_id>" | null
  },
  "license_class_summary": { /* same shape as §5.1.3 */ },
  "warnings": [],
  "blockers": []
}
```

Rules:

- All `amount_minor_units` are integer minor units (e.g. USD cents, EUR cents); no floats in amounts (mirrors TASK-013 canonicalization rules).
- Conversion between source-record currency and `case_currency` is **not** performed by this contract; if mismatch occurs the calculator returns a `currency_mismatch_blocker`.
- The `escalation_pointer_used`, when present, must be one of the records in `escalation_index_reference_filter` from the §5.1.1 input; if the caller did not provide the filter, no escalation is applied (no defaults).
- A `c0_heuristic_overrides` value that violates the documented C0 envelope (multiplier outside `[0.5, 2.0]` per C0 design rationale; revisable in future TASK-018 implementation rounds) is a `c0_heuristic_out_of_envelope_blocker`.

### 5.3 LifeCycleEnergyEstimator

#### 5.3.1 Input envelope

| Input | Type | Required | Source |
|---|---|---|---|
| `cost_breakdown` | `CostBreakdown` (§5.2.2) | yes | `CostCalculator` |
| `thermal_service_summary` | TASK-008 / TASK-017 envelope of `Q` (W), `A` (m²), `U` (W/m²/K), `LMTD` (K) | yes | upstream thermal path |
| `pump_or_fan_power_kw` | float (kW) per unit, with provenance | yes | upstream (rating / sizing); can also be caller-supplied |
| `pump_or_fan_efficiency` | float ∈ `[0, 1]` | yes | caller / vendor-supplied |
| `annual_operating_hours` | float > 0 | yes | caller (no default; absence blocks) |
| `design_life_years` | int > 0 | yes | caller (no default) |
| `discount_rate` | float ∈ `[0, 1]` | yes | caller (no default) |
| `salvage_fraction` | float ∈ `[0, 1]` | yes | caller (no default) |
| `fouling_energy_penalty_factor` | float ∈ `[1.0, 2.0]` | yes | caller (no default) |
| `cleaning_cycle_years` | float > 0 or `null` | no | caller; absence leaves cleaning-impact line-item `null` |
| `spares_cost_per_year_minor_units` | int + currency | no | caller; absence leaves spares `null` |
| `case_currency` | ISO 4217 alpha | yes | caller |

#### 5.3.2 Output envelope — LifeCycleEnergyBreakdown

```jsonc
{
  "schema_version": "0.1.0",
  "life_cycle_run_id": "<deterministic uuid v5 over canonical inputs>",
  "energy_breakdown": {
    "annual_pump_or_fan_energy_kwh": <float>,
    "annual_fouling_energy_penalty_kwh": <float>,
    "annual_cleaning_impact_minor_units": <int> | null,
    "annual_spares_minor_units": <int> | null,
    "design_life_years": <int>,
    "discount_rate": <float>,
    "total_lifecycle_pump_fan_energy_kwh": <float>,
    "total_lifecycle_fouling_energy_kwh": <float>,
    "total_lifecycle_cleaning_minor_units": <int> | null,
    "total_lifecycle_spares_minor_units": <int> | null,
    "salvage_minor_units": <int>,
    "discounted_total_minor_units": <int>,
    "discounted_total_currency": "<ISO 4217>"
  },
  "inputs_used": {
    "pump_or_fan_power_kw_provenance": "<correlation_id or `caller_supplied`>",
    "pump_or_fan_efficiency_provenance": "<correlation_id or `caller_supplied`>",
    "annual_operating_hours_source": "case_input",
    "discount_rate_source": "case_input",
    "design_life_years_source": "case_input",
    "salvage_fraction_source": "case_input",
    "fouling_energy_penalty_factor_source": "case_input"
  },
  "warnings": [],
  "blockers": []
}
```

Rules:

- **No defaults.** Any of `annual_operating_hours`, `discount_rate`, `design_life_years`, `salvage_fraction`, `fouling_energy_penalty_factor` missing → `missing_required_lifecycle_input_blocker`.
- This contract **does not** prescribe the discount formula; it leaves the discount formula to the implementation-round design-amendment contract (per TASK-018 design-amendment precedent, e.g. PR #46).
- The default absence of `discounted_total_minor_units` `0` is **not allowed**; if the implementation cannot compute it (e.g. discount rate out of model support envelope), the output block is `null` (not 0).
- The estimator does not need to know about C0 / C1 cost records directly; it consumes the `CostBreakdown` envelope only. This keeps the cost model and the energy model decoupled.

## 6. Currency / region / date / escalation rules

This section inherits and extends TASK-013 §11. The TASK-018 design contract does NOT redefine those rules; it provides the operational reading for the cost + energy layer.

### 6.1 Currency (inherited from TASK-013 §11)

- `currency` MUST be a valid ISO 4217 alphabetic code at the time of record creation.
- TASK-018 does NOT perform currency conversion. Mismatch between record currency and case currency is a `currency_mismatch_blocker`.

### 6.2 Region (inherited)

- `region` MUST be ISO 3166-1 alpha-2 or `"INTL"`.

### 6.3 Date (inherited)

- `effective_date` is RFC 3339 UTC with `Z` suffix.
- `escalation_date` is OPTIONAL on records; the cost-record escalation-pointer rule (TASK-013 §11) applies unchanged.

### 6.4 Escalation (inherited + extended)

- Escalation is applied through `escalation_index_reference` (TASK-013 §11), never embedded into the cost record's `cost_value`.
- TASK-018 introduces `discount_rate` as an **input-only** field on the `LifeCycleEnergyEstimator` (§5.3.1). The discount rate is NOT sourced from a TASK-013 cost record by default; it is sourced from the case input. A future TASK-019+ design-amendment may propose sourcing it from a TASK-013 cost record if discipline allows, but the present design contract explicitly forbids the default-source pattern.

### 6.5 `validity_envelope` clamp (new in TASK-018)

The cost-model selector and the calculator MUST enforce `validity_envelope` matches against the case attributes; violation is a `validity_envelope_blocker`.

## 7. Provenance requirements

Every element of a `CostBreakdown` and a `LifeCycleEnergyBreakdown` MUST carry:

| Field | Type | Description |
|---|---|---|
| `source_record_ids` | list of `cost_record_id` strings | TASK-013 cost records the value depends on |
| `correlation_ids` | list of strings | Heat-transfer correlation ids consumed (e.g. `dittus_boelter`, `sieder_tate`) |
| `case_input_field` | dict | Mapping from output line-item to case-input field name (for `LifeCycleEnergyEstimator` inputs) |
| `license_class` | string | One of `{public_open, internal_open, proprietary_restricted}`. Restricted records contribute only as `cost_record_id` pointers; no value body is propagated into the output. |
| `provenance_chain_hash` | string (hex) | SHA-256 over canonical-JSON of `{source_record_ids, correlation_ids, case_input_field, license_class, schema_version}`. |

A `CostBreakdown` or `LifeCycleEnergyBreakdown` without `provenance_chain_hash` is a **blocker** at the integration boundary.

## 8. License and restricted-source boundary

Inherits TASK-013 §9 in full. The cost + energy layer adds the following enforcement rules:

- A cost record with `license_class = proprietary_restricted` contributes ONLY a `cost_record_id` pointer to any output envelope. Its `cost_value`, `cost_basis`, and any quantity are **NOT** propagated to the engineering artifact.
- The license class is **never** flipped in the cost + energy layer (no `proprietary_restricted → internal_open` transformation).
- A `license_class_summary` field on `CostModelSelectionResult` and `CostBreakdown` lists counts per class; `proprietary_restricted_count > 0` results in a `restricted_only_provenance_warning`, not a blocker (because the restricted pointers are valid output elements).

This layer does NOT embed, summarize, or paraphrase any restricted source body.

## 9. Error / blocker model

The cost + energy layer uses a frozen closed set of error / blocker / warning codes. **No new codes may be introduced** without amending this section via a separate TASK-018 design-amendment PR; any runtime-only error in the implementation that this contract does not capture is a `unspecified_blocker` (a top-level contract violation).

### 9.1 Blocker codes (frozen set)

| Code | Trigger |
|---|---|
| `currency_mismatch_blocker` | record currency ≠ case currency and no conversion is allowed |
| `region_unsupported_blocker` | no TASK-013 records for the case `region` |
| `validity_envelope_blocker` | case attributes violate the cost record's `validity_envelope` |
| `missing_required_lifecycle_input_blocker` | any of `annual_operating_hours`, `discount_rate`, `design_life_years`, `salvage_fraction`, `fouling_energy_penalty_factor` missing |
| `restricted_body_propagation_blocker` | implementation accidentally propagates a `proprietary_restricted` value body (caught at the integration boundary) |
| `unspecified_blocker` | anything else |

### 9.2 Warning codes (frozen set)

| Code | Trigger |
|---|---|
| `currency_fallback_used_warning` | preferred currency missing in region; secondary currency was substituted |
| `region_fallback_used_warning` | preferred region has no records; `"INTL"` was substituted |
| `fouling_energy_penalty_factor_at_upper_bound_warning` | input equals 2.0 (treated as suspect) |
| `discount_rate_zero_warning` | input equals 0 (no discounting applied); kept as a warning so engineering reviewers see it explicitly |
| `restricted_only_provenance_warning` | the `CostBreakdown` includes only restricted-source pointers (no public-open values) |
| `unspecified_warning` | anything else |

### 9.3 Result-state implications

- `blockers.len() >= 1` ⇒ `CostBreakdown.state = NOT_COMPUTABLE` / `LifeCycleEnergyBreakdown.state = NOT_COMPUTABLE`.
- `warnings.len() >= 1` (and blockers empty) ⇒ `state = COMPUTABLE_WITH_WARNINGS`.
- Else ⇒ `state = COMPUTABLE`.

## 10. JSON canonicalization / deterministic hash / ordering rules

Inherits TASK-013 §16 (RFC 8785) + TASK-014 canonical-JSON + TASK-017 §10. Adds the following TASK-018-specific rules:

- The top-level hash of any output envelope is `provenance_chain_hash` (§7), computed over the canonical-JSON of `{source_record_ids, correlation_ids, case_input_field, license_class, schema_version}`.
- `CostBreakdown.amount_minor_units`, `LifeCycleEnergyBreakdown.*_minor_units` are INTEGER (no floats).
- `LifeCycleEnergyBreakdown.*_kwh` values are FLOAT with deterministic IEEE-754 round-trip via `repr()` (no JSON-float ambiguity by avoiding `NaN`/`Infinity`).
- `escalation_index_reference` and `source_record_ids` are SORTED ASCENDING before hashing.
- `selectors.c0_records` and `selectors.c1_records` are SORTED by `cost_record_id` ASC, then `cost_record_version` DESC.

## 11. Future test strategy

No test is run in this design round; the test plan is specified for future implementation rounds.

### 11.1 Test classes (future implementation)

| Class | Scope |
|---|---|
| Deterministic selector tests | Same inputs ⇒ same `CostModelSelectionResult` byte-for-byte |
| Deterministic calculator tests | Same inputs ⇒ same `CostBreakdown` byte-for-byte |
| Deterministic estimator tests | Same inputs ⇒ same `LifeCycleEnergyBreakdown` byte-for-byte |
| Golden tests | Approved reference numbers for canonical C0 / C1 / LCC scenarios; numeric equality (modulo canonical-JSON byte comparison) |
| License-boundary tests | `proprietary_restricted` records contribute ONLY pointers; no value body propagates |
| Frozen-contract-unchanged tests | `tests/costing/test_frozen_contract_unchanged.py` asserts `docs/tasks/TASK-018-…md` SHA matches the documented Frozen Contract Authority Commit SHA |
| Currency / region / escalation tests | Each blocker in §9.1 is exercised; each warning in §9.2 is exercised |
| Integration tests | TASK-013 records + TASK-017 outputs ⇒ TASK-018 outputs end-to-end, deterministic |

### 11.2 Test-fixture policy

- All test fixtures referencing cost records must be public-open-license (`license_class in {public_open, internal_open}`); no proprietary-restricted bodies in fixtures.
- All test fixtures referencing mass totals must come from TASK-017 golden scenarios.
- All test fixtures referencing `discount_rate` / `design_life_years` etc. must be explicitly documented in the test as "case_input" provenance.

## 12. CI ownership plan

Inherits TASK-015 + TASK-017 CI ownership model. Adds the following TASK-018-specific rows:

- Future TASK-018 implementation tests live under `tests/costing/`.
- New test files registered in the existing `ci` shard per TASK-017 §13.2 slice-authorized registration pattern (one line per file under the existing shard's `files:` list; no shard rename, no new shard, no python-version mutation).
- The `frozen-contract-unchanged` test goes in the `ci` shard's `files:` list.
- A `pytest.mark.costing` marker is registered; tests asserting `provenance_chain_hash` byte-equality require this marker.

This design PR is documentation-only and does not register any CI row; registration is deferred to the future implementation-slice rounds.

## 13. Future implementation file boundary

The future implementation PRs (NOT authorized by this design contract) may only add files under:

- `src/hexagent/costing/`
- `tests/costing/`

The empty placeholder `src/hexagent/costing/__init__.py` currently on main (blob `e69de29…`, no claimed contract owner) is **NOT** mutated by this design round; it remains as-is. The future implementation will populate it.

### 13.1 Naming rationale

The path `src/hexagent/costing/` is intentionally distinct from existing application-layer paths:

| Path | Owning task | Role | Authority |
|---|---|---|---|
| `src/hexagent/material_costs/` | TASK-013 (frozen) | Material / cost **data governance** — record schema, validation, license boundary, selection | Read-only canonical source for cost records |
| `src/hexagent/geometry_catalogs/` | TASK-016 (frozen) | Approved geometry **catalog** — record schema, validation, hashing | Read-only canonical source for geometry records |
| `src/hexagent/material_mass_mechanical/` | TASK-017 (frozen) | Material / mass / preliminary mechanical **application layer** — consumes from TASK-013 + TASK-016, derives mass + mechanical checks | Application-layer derivation; never a canonical source |
| `src/hexagent/costing/` | TASK-018 (this design) | Cost / life-cycle-energy **application layer** — consumes from TASK-013 + TASK-017, derives C0/C1 + life-cycle energy envelopes | Application-layer derivation; never a canonical source |

The empty directory `src/hexagent/materials/` that pre-exists in the repo is **NOT** part of any frozen contract and is **NOT** claimed by TASK-018.

The future implementation MUST NOT modify:

- Any file under `src/hexagent/` outside the `costing/` subtree.
- Any file under `tests/` outside the `costing/` subtree.
- Any file under `docs/tasks/TASK-011-*.md` … `docs/tasks/TASK-017-*.md`.
- `ci-shard-manifest.yml`, except as carved out in §13.2.
- Any file under `.github/`.
- `pyproject.toml` except for adding the new subtree to the package find path (no version bump, no new dependency).

If a future implementation needs to touch any other file, it must open a separate Issue and obtain separate authorization.

### 13.2 CI manifest ownership for slice-authorized test files (clarification)

The blanket prohibition on modifying `ci-shard-manifest.yml` above is narrowed as follows for the implementation phase:

- TASK-018 implementation slices MAY register their own **explicitly slice-authorized** test files in `ci-shard-manifest.yml` when repository governance requires manifest registration (i.e. the `verify-manifest` CI job enforces `D == M` ownership). This is a content-level registration of the slice's own newly-introduced test file in an existing shard's `files:` list; it is NOT a structural mutation (no new shards, no removed shards, no shard rename, no python-version / timeout changes).
- This clarification does NOT authorize:
  - unrelated CI shard changes (other shards, other files);
  - changes to `.github/`;
  - test files outside the current slice's authorized scope;
  - moving, re-ordering, or deleting other manifest entries;
  - slice B / C / D / Closeout test registration before that slice is explicitly authorized.
- Each implementation slice MUST surface its manifest registration as a separate evidence row in `docs/TASK_BACKLOG.md` (TASK-017 Slice A governance-repair precedent).

## 14. Slice plan

The future TASK-018 implementation will follow the TASK-017 §14 slice pattern, with each slice authorized by a separate Charles round:

| Slice | Files | Authorization gate |
|---|---|---|
| A — `CostModelSelector` | `src/hexagent/costing/cost_model_selector.py`, `src/hexagent/costing/errors.py`, `tests/costing/test_cost_model_selector.py`, `tests/costing/test_frozen_contract_unchanged.py` | Slice A authorization only |
| B — `CostCalculator` (C0 + C1) | `src/hexagent/costing/cost_calculator.py`, `tests/costing/test_cost_calculator.py` | Slice B authorization only |
| C — `LifeCycleEnergyEstimator` | `src/hexagent/costing/life_cycle_energy_estimator.py`, `tests/costing/test_life_cycle_energy_estimator.py` | Slice C authorization only |
| D — Closeout | `docs/TASK_BACKLOG.md` evidence rows (closeout PR separate from this design PR), closeout comment on Issue #76, Issue #76 closed | Closeout authorization only |

No slice may carry files from a later slice forward.

## 15. Acceptance criteria

The TASK-018 design contract is **DRAFT** under this PR. The contract target state is `DESIGN FROZEN` and is achieved only when, in separate future rounds:

1. Charles authorizes the design PR to leave DRAFT.
2. Engineering review verdict is `PASS` on the design-branch head SHA.
3. P0/P1/P2 review items (if any) are addressed in the same branch with new commits.
4. Final-flow preflight review PASS (post-amendment).
5. Freeze comment is posted, recording:
   - **Frozen Contract Authority Commit SHA** (the head SHA of the design branch at freeze time).
   - **Frozen Contract Authority Base SHA** = `5f96cf761d470b82faa1a5d164eefd42360c7df9`.
6. Design PR is merged to main; main post-merge CI run is `completed` / `success` with head SHA matching the merge commit.
7. Closeout docs PR records the merged-into-main evidence in `docs/TASK_BACKLOG.md`.
8. A closeout comment is posted on Issue #76 and Issue #76 is closed with `state_reason = completed`.

Until all of these happen, this design contract remains `DRAFT` and **NO** production code under `src/hexagent/costing/` may be written by future rounds within the bounds of this design contract.

## 16. Closeout criteria

The TASK-018 design contract closeout completes when:

1. The design PR is merged; main HEAD = the merge commit SHA.
2. Main post-merge CI run is `completed` / `success`.
3. `docs/TASK_BACKLOG.md` records the design merge SHA, main post-merge CI run id, frozen Contract Authority Commit SHA.
4. A closeout comment is posted on Issue #76 with concrete numerical evidence (sha, run id, conclusion).
5. Issue #76 is `closed` with `state_reason = completed`.
6. `src/hexagent/costing/` is left exactly as the empty placeholder `__init__.py` was on main (no implementation files added yet).
7. No mutation to any frozen TASK-011..TASK-017 contract body.
8. No mutation to `ci-shard-manifest.yml` / `.github/` / `pyproject.toml`.
9. No Feishu outbound from the closeout round (per TASK-018 design round standing rule).

## 17. Boundary to TASK-013 cost-data governance

TASK-018 consumes TASK-013 cost-data records **read-only**. The following responsibilities are explicitly NOT migrated from TASK-013 into TASK-018:

- Cost record schema (`cost_record_id`, `cost_record_version`, `cost_category`, `cost_basis`, `currency`, `quantity_basis`, `cost_value`).
- Cost-record source-class taxonomy.
- Cost-record license boundary (`license_class`).
- Cost-record escalation-pointer rule (TASK-013 §11).
- Cost-record selection engine.
- Cost-record canonicalization (TASK-013 §16).

Conversely, TASK-018 does **NOT** introduce:

- A new cost record type.
- A new source class.
- A new license class.
- A new `cost_category` value (the contract reuses TASK-013's closed set).
- A new currency-escalation math form.
- Embedding of cost-record bodies into engineering artifacts.

The TASK-013 closeout doc (§15) states that "TASK-018 cost + life-cycle concerns remain absent until TASK-018 is authorized." TASK-018 opens that layer without overlapping TASK-013's data-layer responsibilities.

## 18. Boundary to TASK-017 mass / mechanical outputs

TASK-018 consumes TASK-017 mass totals and preliminary mechanical check outputs **read-only**. The following responsibilities are explicitly NOT migrated from TASK-017 into TASK-018:

- Material selection (`MaterialSelector`).
- Mass calculation (`MassCalculator`).
- Preliminary mechanical checks (`PreliminaryMechanicalChecker §9.1 / §9.2 / §9.3`).
- Component allocation rules (TASK-017 §6).
- Preliminary mechanical `BLOCKED_FOR_DETAILED_DESIGN` semantics.

Conversely, TASK-018 does **NOT** introduce:

- A new material selector.
- A new mass calculator.
- A new preliminary mechanical check.
- A new `MassBreakdown` shape.
- A new `MaterialResolutionResult` shape.

The TASK-017 closeout doc (§15) states "TASK-018 cost + life-cycle concerns remain absent." TASK-018 opens that layer without overlapping TASK-017's mass/mechanical responsibilities.

### 18.1 No-pressure-drop rule (inherited)

`PreliminaryMechanicalChecker` does NOT compute pressure-drop; pressure-drop / C4 belongs to TASK-020+ domains. TASK-018 inherits this rule and does NOT introduce pressure-drop inputs to the cost + energy model. Any future attempt to add pressure-drop-derived cost (e.g. pumping-cost-from-dP) is a separate task, NOT TASK-018.

## 19. Frozen contract authority model

### 19.1 Frozen Contract Authority Commit SHA

The TASK-018 design contract establishes a **Frozen Contract Authority Commit SHA** when the design PR is merged. That SHA is set at freeze time and recorded in:

- The freeze comment on the design PR.
- The closeout docs PR's `docs/TASK_BACKLOG.md` row.
- A future `tests/costing/test_frozen_contract_unchanged.py` (added by Slice A implementation) that asserts the file SHA matches the documented Frozen Contract Authority Commit SHA.

### 19.2 Frozen Contract Authority Base SHA

| Field | Value |
|---|---|
| Base SHA | `5f96cf761d470b82faa1a5d164eefd42360c7df9` |
| Meaning | main HEAD at TASK-017 implementation merge (PR #75) |
| Used by | the self-reference guard in §19.3 |

### 19.3 Self-reference guard

This file MUST NOT modify itself. The frozen-contract-unchanged test asserts that `docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md` SHA at the head of the frozen branch matches the Frozen Contract Authority Commit SHA. Any drift is a `frozen_contract_drift_blocker` at the integration boundary.

### 19.4 Status declarations

This contract uses the same status vocabulary as the rest of the project:

| Status | Meaning |
|---|---|
| `DRAFT` | Under review; not frozen |
| `DESIGN FROZEN` | Engineering review PASS + freeze comment posted + branch merged |
| `IMPLEMENTATION NOT AUTHORIZED` | Implementation Issue not yet created |
| `IMPLEMENTATION AUTHORIZED` | Separate authorization PR opens it |
| `IMPLEMENTATION CLOSED` | Issue closed / completed |

### 19.5 Three-way SHA synchronization

At the moment the design contract is moved from `DRAFT` to `DESIGN FROZEN`, three SHAs must be synchronized:

1. The frozen contract file SHA on the main branch (= the Frozen Contract Authority Commit SHA).
2. The frozen contract file SHA on the design branch at the moment of freeze (must equal #1).
3. The freeze comment records #1 verbatim (no transcription error).

A divergence between any two of these is a `frozen_contract_authority_drift_blocker`. The TASK-017 design closeout precedent establishes that this discipline is mandatory at freeze time.

## 20. Self-reference guard / frozen-contract-unchanged rule

The TASK-018 self-reference guard mirrors TASK-013/014/015/017 §19 conventions.

### 20.1 Guard scope

The guard asserts that `docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md` at TASK-018-frozen `main` HEAD has SHA equal to the documented Frozen Contract Authority Commit SHA.

### 20.2 Guard evaluation

The guard runs in the existing `ci` shard's test set after Slice A implementation has registered `tests/costing/test_frozen_contract_unchanged.py`. The guard failure halts the implementation PR's CI with a clear `frozen_contract_drift_blocker` message that names the documented Frozen Contract Authority Commit SHA and the observed SHA.

### 20.3 Guard anti-rewrite rule

A drift triggers a **freeze-comment amendment** + a **separate TASK-018 design-amendment PR** (per TASK-017 design-amendment precedent, PR #46). The implementation PR cannot itself rewrite the frozen contract; doing so is a contract violation that requires rollback + separate amendment.

## 21. Explicit non-authorization statement

This design round explicitly does NOT authorize any of:

1. Production code under `src/hexagent/costing/`.
2. Test code under `tests/costing/`.
3. CI / governance mutation under `ci-shard-manifest.yml` / `.github/` / `pyproject.toml` / `docs/TASK_BACKLOG.md`.
4. Mutation of any frozen contract body under `docs/tasks/TASK-011-*.md` … `docs/tasks/TASK-017-*.md`.
5. C2 historical-project regression work.
6. C3 vendor quotation / supplier-quote ingestion.
7. Pressure-drop implementation / C4 logic.
8. TASK-019+ work (Golden cases + double-pipe validation report or anything later).
9. Two-phase / refrigerants / shell-and-tube / plate / air-cooler / microchannel content (TASK-020+).
10. Discount rate defaults or life-year defaults inside the engineering kernel.
11. Closing Issue #76.
12. Marking the design PR Ready.
13. Merging the design PR.
14. Feishu outbound.
15. Touching the 17 preexisting untracked items in the local checkout.

Authorization for any of the items above requires a separate, explicit Charles round with its own preflight, design contract (or design-amendment contract), and freeze closeout.
