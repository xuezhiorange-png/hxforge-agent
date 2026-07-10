# TASK-019 Design Amendment 002-K — case_02 cost-stack coverage and fixture-authority design contract (binding, contract-frozen, governance-only)

| Field | Value |
|---|---|
| **Design-content provenance** | PRESERVED FROM PR #119 (PR #119 HEAD COMMIT `aa6692eb5a978b3ab3ebd052aed50bcd9b03a213`) AND THE PR #121 BUSINESS-SOURCE AVAILABILITY GOVERNANCE ADDITION (PR #121 MERGE COMMIT `bb5b8c46e37f37b089a48fdd22b917ed73336194`), BOTH ORIGINALLY RECORDED UNDER A SUPERSEDED TASK-020 LABEL (`docs/tasks/TASK-020-cost-stack-coverage-and-fixture-authority.md`, superseded by this corrective rename); PR #119 MERGE COMMIT `b1b6ea7f5b766d171f0454a29f3b9a6ba05907b1`; CONTENT RE-HOMED UNDER TASK-019 AMENDMENT 002-K WITH AUTHORIZED IDENTITY / NUMBERING / HEADER / CROSS-REFERENCE CORRECTIONS |
| **Corrective identity status** | TASK-019 DESIGN AMENDMENT 002-K RE-HOME MERGED / DESIGN FROZEN / MAIN-CI-VERIFIED |
| **Implementation status** | NOT AUTHORIZED |
| **Source authority** | §17 (TASK-019 Design Amendment 002-J) merged into `main`; case_02 002-G mass-chain already merged; case_03 002-H / 002-I bridge patterns already merged; PR #119 design content; PR #121 business-source availability gate; §17A.x (this contract, TASK-019 Design Amendment 002-K) |
| **Scope** | case_02 full cost-stack coverage contract + fixture-authority + derivation protocol + business-source availability gate; NOT implementation |
| **Applies to** | case_02 only (`TASK-019-GOLDEN-02`); case_01 / case_03 are explicitly out of scope |
| **Forbidden items** | pressure-drop, Bell-Delaware, Kern, TEMA, thermal rating, runtime catalog scan, runtime resolver, discount formula, salvage formula, invented expected values |

> This document is a **design contract** (governance-only). It does **NOT** authorize production implementation, fixture mutation, test mutation, or any algorithm authoring. Per §17A.8, implementation may only be initiated through one of four explicitly ordered Slices (A → B → C → D), each with its own entry and exit conditions, and all four slices are currently blocked by §17A.8.6.

---

## §17A.1 Scope and Authority (binding, contract-frozen)

### §17A.1.1 In-scope objectives

This amendment has exactly **five** in-scope objectives. Each objective is a contract-level declaration, not an implementation commitment.

1. **Extend case_02 cost-stack coverage**: extend the case_02 `expected_output` surface to carry a complete, deterministically-derived cost-stack (C0 material, C0 labor, C1 total, life-cycle energy envelope, and the cost-record selection handoff), consistent with the case_03 contract pattern at §15 and §16.
2. **Define complete cost-record selection authority**: declare the authoritative source of every cost record consumed by case_02 (input contract, record-role mapping, deterministic ordering), so that no record is sourced by inference, copy, or runtime discovery.
3. **Define catalog traversal boundary**: codify what is in scope (deterministic traversal over an authorized catalog input) and what is out of scope (runtime catalog scan, network lookup, plugin resolution, heuristic matching).
4. **Define expected_output fixture derivation protocol**: lock the only allowed ordering for converting production-chain output into fixture `expected_output`. Reverse-engineering and hand-calculating are explicitly forbidden.
5. **Freeze implementation vs. non-implementation boundary**: separate the four future Slices (A / B / C / D) and declare that no production code may be authored, modified, or executed under this amendment alone.

### §17A.1.2 Out-of-scope declarations (binding)

This amendment explicitly does **NOT**:

- Re-design or re-author the case_03 selector / adapter / validation contract (§15 / §16 are already merged and frozen).
- Re-design or re-author the case_01 bridge contract.
- Re-design or re-author the case_02 mass-chain contract (already frozen at TASK-019 Design Amendment 002-G; see `case_02_materials_mass_mechanical.json` `amendment_id: TASK-019-DESIGN-AMENDMENT-002-G`).
- Implement pressure-drop, Bell-Delaware, Kern, TEMA, thermal rating, or any thermal-method algorithm (see §17A.7).
- Implement runtime catalog scan, runtime catalog lookup, runtime catalog resolver, or any dynamic catalog integration (see §17A.4).
- Implement discount formula, salvage formula, or any cost formula that requires an `escalation_rule` / `discount_rate` to be evaluated (see §17A.4 “Out of Scope”).
- Author, edit, or commit any production code, fixture, test, or configuration file as part of §17A. Implementation is gated on Slices A → D, each requiring its own Charles-authorized round (see §17A.8).

### §17A.1.3 Authority hierarchy (binding)

The authority hierarchy for resolving any §17A question is:

1. **Charles explicit instruction** (current authorization message or future authorization message) — highest.
2. **Merged / frozen repository design contract** (`main` @ `bb5b8c46e37f37b089a48fdd22b917ed73336194`; §15, §16, §17, 002-A / 002-D / 002-E / 002-F / 002-G, PR #119 and PR #121 governance content).
3. **Committed fixture + production contract** (`tests/golden/double_pipe_rating/*.json`, `_provenance_metadata.json`, `_tolerance_metadata.json`).
4. **TASK-019 Design Amendment 002-K preparation report** — synthesis, not authority. Pre-amendment-002-K synthesis at `/root/TASK-020-preparation-report.md` and `/tmp/TASK-020-preparation-report.md` is historical, non-authoritative, and is NOT current authority for this amendment.
5. **Implementation inference** — lowest. Implementation inference MUST NOT override any of the above four tiers.

If two sources conflict, the higher-tier source governs. If the conflict is between two sources of the same tier, the source that is **explicit** governs over the source that is **implicit**. The anti-fabrication guard in §17A.10 applies in all cases.

---

## §17A.2 Current Frozen Baseline (binding, contract-frozen)

The following TASK-019 elements are already merged into `main` and are **unchangeable by this amendment**. Any future implementation that needs to alter any of these MUST be a separate Charles-authorized amendment to the TASK-019 design contract, not an action under §17A.

| Element | Authority location | Repository reference |
|---|---|---|
| Selector interface (case_03 `CostModelSelector.select` consumes `cost_records_bridge` as the sole source of cost-record inputs) | TASK-019 design contract §15.3.2 Q2 | `docs/tasks/TASK-019-golden-cases-double-pipe-validation.md` line 1531+ |
| Adapter interface (case_01 / case_02 / case_03 wiring pattern; case-bound bridge contract; produced_field discipline) | §15.3 / §15.7 / §16.2 / §16.7 | `docs/tasks/TASK-019-golden-cases-double-pipe-validation.md` lines 1531, 2084, 2419 |
| Fixture-driven selection (no runtime catalog; bridge is case-bound frozen data) | §15.3.2 Q2 / §4.8.5 / §4.9.4 | TASK-019 design contract |
| Validation boundary (`tests/validation_report/test_chain_wiring_adapter.py::test_expected_output_unchanged_across_adapter_runs` hard-codes `fixture_02["expected_output"]["mass_kg"]["fluid_mass_kg"] == 1.05`) | §4.9 (002-G) line 791 | `tests/validation_report/test_chain_wiring_adapter.py` |
| Selected record handoff (the `cost_records_bridge_bindings.c0_material_record_id` / `c0_labor_record_id` / `c1_total_record_id` triple) | §15.3 case_03 contract | `case_03_cost_lifecycle_envelope.json` `input.cost_records_bridge_bindings` |
| Current six-field cost selection contract (`c0_material_record_id` / `c0_labor_record_id` / `c1_total_record_id` / `c0_record_count` / `c1_record_count` / `selection_blockers`) | §15.3 | case_03 `input.cost_records_bridge_bindings` + `expected_output.selected_cost_model` |
| Existing chain execution order (input → bridge → adapter → produced_fields → comparison; no short-circuit; no copy from `expected_output` to `actual_output`) | §15.7 / §16.7 | TASK-019 design contract |
| Existing error semantics (`WIRED_VIA_CHAIN_PARTIAL`, `status: pending`, `slice3a_blocked_field_paths`, `unspecified_blocker`) | §15.7 / §16.7 / case_03 `expected_output.slice3a_blocked_field_paths` | case_03 fixture + test contract |

§17A.2 declares that all eight elements above are **frozen** for the purposes of this contract. Any future round that needs to alter any of them MUST first amend the TASK-019 design contract through a separate Charles-authorized round.

---

## §17A.3 Cost Record Selection Authority (binding, contract-frozen)

### §17A.3.1 Current state (frozen, recoverable from this file + repository)

| Selection aspect | Current authority (case_02) | Repository evidence |
|---|---|---|
| Static curated fixture subset | **NOT PRESENT** in case_02 | `case_02_materials_mass_mechanical.json` has no `input.cost_records_bridge` sub-block |
| Explicitly provided records | **NOT PRESENT** in case_02 | `case_02_materials_mass_mechanical.json` has no `input.cost_records_bridge_bindings` sub-block |
| Fixture-bound selection input | **NOT PRESENT** in case_02 | case_02 has no cost-related input sub-block |
| Deterministic selection | NOT APPLICABLE in case_02 (no cost-record selection exists yet) | — |
| `cost_records_bridge` (case_03 reference) | PRESENT in case_03 (3 records: C0 material, C0 labor, C1 total) | `case_03_cost_lifecycle_envelope.json` `input.cost_records_bridge` |

### §17A.3.2 Amendment 002-K target (binding, future Slices A + B)

This amendment declares the following **target** state for the case_02 cost-record selection. These are **contract targets**, not implementation commitments; implementation is gated on Slice A + Slice B per §17A.8 and currently blocked by §17A.8.6.

| Target aspect | Required by this amendment | Implementation in |
|---|---|---|
| Complete required record set for case_02 | REQUIRED (exact field set pending Slice A source) | Slice A (input contract) + Slice B (selection logic) |
| Explicit record-role mapping (per record: identity, role, purpose, necessity) | REQUIRED (one record per required cost-stack field, derived from the 6 deferred fields in §17.2 + the curated-subset fields in `selected_cost_model` per case_03 pattern) | Slice A |
| Deterministic record ordering | REQUIRED (the order is the explicit ordering of records in `input.cost_records_bridge`; no implicit sort; no timestamp-based ordering) | Slice A + Slice B |
| No implicit fallback | REQUIRED (if a record is missing or malformed, the chain reports `WIRED_VIA_CHAIN_PARTIAL` + `selection_blockers` entries, NOT a default / placeholder / first-valid-record) | Slice B |
| No hidden runtime discovery | REQUIRED (no filesystem scan, no network lookup, no plugin resolution, no heuristic matching) | §17A.4 + Slice B |

### §17A.3.3 Record-role mapping rule (binding)

For every cost record that case_02 will require, the Slice A authoring round MUST declare, at minimum:

- **Identity**: a stable `record_id` (string; case-bound; no reuse across cases; no reuse across amendments).
- **Role**: one of `{C0_material, C0_labor, C1_total, life_cycle_energy_record, discount_record, salvage_record}`. Discount / salvage records are explicitly DEFERRED to separately authorized future cost-model scope outside TASK-019 Design Amendment 002-K, task number unassigned per §17A.4 and are NOT included in Slice A.
- **Purpose**: a one-sentence statement of what cost-stack field this record supports (mapping to one of the 6 §17.2 deferred fields, or to the curated-subset `selected_cost_model.*` fields).
- **Necessity**: a `mandatory` / `optional` flag. Mandatory records are required for the chain to report `WIRED_VIA_CHAIN_FULL`; optional records contribute only if present.
- **Source**: which future real production chain (per §17.7 item 2) is authorized to derive the record’s content. **No record source may be “TBD” / “to be invented” / “agent-decided” / “placeholder”.**

If any of the above five attributes is **SOURCE_MISSING** (no Charles-provided text, no committed repo hook, no future production chain identified), the record is **deferred to CHARLES_SOURCE_REQUIRED** status and is **NOT** authored in Slice A.

### §17A.3.4 Status register for record-role coverage

The following record roles are tracked for case_02. Statuses are the formal states defined in §17A.9.

| Record role | Current status (case_02) | Required by §17A.3.2 | Notes |
|---|---|---|---|
| `C0_material` | SOURCE_MISSING | YES (Slice A) | Maps to `c0_subtotal.component_breakdown[]` per §17.2 |
| `C0_labor` | SOURCE_MISSING | YES (Slice A) | Maps to `c0_subtotal.component_breakdown[]` per §17.2 |
| `C1_total` | SOURCE_MISSING | YES (Slice A) | Maps to `c1_subtotal.component_breakdown[]` per §17.2 |
| `life_cycle_energy_record` | SOURCE_MISSING | YES (Slice A) | Maps to `life_cycle_energy_envelope.P_intake_kW` / `P_total_kW` / `P_cooling_kW` / `P_loop_kW` per §17.2 |
| `discount_record` | DEFERRED | NO (excluded per §17A.4) | separately authorized future cost-model scope outside TASK-019 Design Amendment 002-K, task number unassigned |
| `salvage_record` | DEFERRED | NO (excluded per §17A.4) | separately authorized future cost-model scope outside TASK-019 Design Amendment 002-K, task number unassigned |

---

## §17A.4 Catalog Traversal Boundary (binding, contract-frozen)

### §17A.4.1 In-scope (binding; Slice B may authorize ONLY these)

The following operations are **in scope** for the future case_02 cost-record selection implementation, and ONLY these:

- **Deterministic traversal over an authorized catalog input**: a pre-authored `input.cost_records_bridge` array (case-bound, frozen, audit-traceable) is read in array order. No sort, no shuffle, no implicit reordering.
- **Explicit filtering rules**: filtering is permitted only by attribute values that are themselves explicitly listed in the bridge (e.g. `record_id`, `record_role`, `currency_ISO_4217`, `date_ISO_8601`). No attribute inference.
- **Stable ordering**: the order of records in the `cost_records_bridge` array is the authoritative order. The output selection preserves this order.
- **Reproducible selection**: given the same `cost_records_bridge` input, the chain MUST produce the same selection output byte-for-byte (no time-of-day, no random seed, no env-var dependency).
- **Traceable record provenance**: every selected record carries an explicit `provenance_amendment_id` (case-bound; cross-references the TASK-019 amendment that froze the bridge value, e.g. `"TASK-019-DESIGN-AMENDMENT-002-J"` for §17A-authored content).

### §17A.4.2 Out-of-scope / Deferred (binding; explicitly forbidden)

The following operations are **out of scope** for the future case_02 cost-record selection implementation. They are **NOT** authorized by §17A. Any future round that wishes to authorize any of them MUST be a separate Charles-authorized amendment, not a §17A action.

- **Unrestricted runtime catalog scan** (e.g. scanning a directory tree for `*.json` files at execution time).
- **Ambient filesystem discovery** (e.g. walking `os.environ` paths to find a catalog).
- **Network catalog lookup** (any HTTP / HTTPS / FTP / SFTP / WebSocket call to a remote cost database).
- **Dynamic plugin resolution** (e.g. `importlib` dynamic import of cost catalog modules).
- **Hidden fallback records** (e.g. “if no record matches, use the first record in the catalog”).
- **Heuristic record matching** (e.g. fuzzy string match, regex match, ML-based match).
- **Discount logic** (any computation involving `discount_rate` or `escalation_rule`).
- **Salvage logic** (any computation involving `salvage_fraction`).
- **Runtime resolver invention** (any new function, method, or callable that produces a cost record from sources other than the explicit `cost_records_bridge` input).

§17A.4.2 explicitly forbids writing the phrase “dynamic catalog integration is authorized” anywhere in §17A implementation artifacts. Per §17A.10, “current fixture subset ≠ complete catalog” and “current selector output ≠ complete cost stack” are anti-fabrication facts.

### §17A.4.3 Boundary statement (binding)

§17A establishes that case_02 cost-record selection is **fixture-bound static curated**, analogous to case_03’s `cost_records_bridge` pattern (per §15.3.2 Q2) and case_02’s `material_catalog_bridge` pattern (per 002-G). The selection input is **authored at design time**, **frozen at fixture-freeze time**, and **consumed verbatim at execution time**. There is no future catalog service outside this amendment; there is no future catalog database outside this amendment. There is only a `cost_records_bridge` block on the case_02 fixture, authored by Slice A and consumed by Slice B.

---

## §17A.5 Expected Output Contract (binding, contract-frozen)

### §17A.5.1 Status classification (per field, case_02 only)

Every expected_output field for case_02 is classified into exactly one of the following five states. The classification is the **single source of truth** for what may be written into the fixture by any future round.

| State | Definition | Authoritative write timing | Invention allowed? |
|---|---|---|---|
| `EXISTING_FROZEN` | Field is already present in the case_02 fixture; central value is fixed; tolerance is fixed. | Already written (001 / 002-F / 002-G). No re-write permitted. | NO (frozen) |
| `REQUIRED_MISSING` | Field is required by §17A.5.2 / §17.2 but the central value is not yet present in the case_02 fixture. | Slice C (after Slice B’s production-chain execution and only after §17A.8.6 is lifted). | NO (only derived from production chain) |
| `DERIVED_VIA_CHAIN` | Field’s value MUST be derived from a real production-chain run on the same fixture input, reproducibly, on a clean checkout. | Slice C (only). | NO (only via chain output) |
| `DEFERRED` | Field is required by §17A.5.2 but the underlying algorithm is NOT yet contract-frozen (e.g. discount / salvage). | separately authorized future cost-model scope outside TASK-019 Design Amendment 002-K, task number unassigned. | NO (this contract) |
| `PROHIBITED_MANUAL` | Field is required by §17A.5.2 but is FORBIDDEN from manual invention under any circumstance; may only be authored by §17A.5.3 (chain capture). | Slice C (only). | NO (strict) |

### §17A.5.2 Field-by-field contract (case_02 only; case_01 / case_03 untouched)

The following table enumerates every expected_output field that §17A contractually addresses. Fields already at `EXISTING_FROZEN` are listed for completeness; the table does NOT re-author them. Fields at `REQUIRED_MISSING` / `DERIVED_VIA_CHAIN` / `DEFERRED` / `PROHIBITED_MANUAL` are future Slice targets, currently blocked by §17A.8.6 where they depend on business cost Source.

| Field path | State | Authority | Derivation source | Write timing | Assertion purpose | Currently missing? |
|---|---|---|---|---|---|---|
| `expected_output.mass_kg.shell_mass_kg` | `EXISTING_FROZEN` | 002-G frozen | case_01 geometry × SS304 8000 kg/m^3 (002-G derivation) | already written | Regression baseline for mass_kg | NO |
| `expected_output.mass_kg.tube_mass_kg` | `EXISTING_FROZEN` | 002-G frozen | same | already written | Regression baseline for mass_kg | NO |
| `expected_output.mass_kg.total_mass_kg` | `EXISTING_FROZEN` | 002-G frozen | same | already written | Regression baseline for mass_kg | NO |
| `expected_output.mass_kg.fluid_mass_kg` | `EXISTING_FROZEN` (DEFERRED status marker) | 002-F baseline; 002-G DEFER | 002-F baseline (1.05); future real fluid-volume × fluid-density chain | already written (value); produced_field status DEFERRED | Marker-only; not a current production produced_field | NO (value) |
| `expected_output.preliminary_mechanical_check.status` | `EXISTING_FROZEN` | 001 frozen | SS304 allowable_stress_mpa_at_design_temperature = 137.0 (002-F bridge) | already written | Categorical pass / fail | NO |
| `expected_output.selected_material_ids.shell_material_id` | `EXISTING_FROZEN` | 002-F frozen | descriptive string from 002-F bridge | already written | Audit / description only (per 002-F) | NO |
| `expected_output.selected_material_ids.tube_material_id` | `EXISTING_FROZEN` | 002-F frozen | descriptive string from 002-F bridge | already written | Audit / description only (per 002-F) | NO |
| `expected_output.cost_components_C0_C1.cost_components.C0_material_minor_units` | `REQUIRED_MISSING` | §17A / §17.2 G1 | Real production chain on case_02 fixture (per §17A.6) | Slice C | CAPEX C0 material value | **YES** |
| `expected_output.cost_components_C0_C1.cost_components.C0_labor_minor_units` | `REQUIRED_MISSING` | §17A / §17.2 G1 | Real production chain on case_02 fixture | Slice C | CAPEX C0 labor value | **YES** |
| `expected_output.cost_components_C0_C1.cost_components.C1_total_minor_units` | `REQUIRED_MISSING` | §17A / §17.2 G1 | Real production chain on case_02 fixture | Slice C | CAPEX C1 total value | **YES** |
| `expected_output.cost_components_C0_C1.currency_ISO_4217` | `REQUIRED_MISSING` | this amendment | Real production chain on case_02 fixture | Slice C | Currency code | **YES** |
| `expected_output.cost_components_C0_C1.cost_components.C0_material.component_breakdown[]` | `REQUIRED_MISSING` | §17.2 G1 | Real production chain on case_02 fixture | Slice C | C0 material component breakdown | **YES** |
| `expected_output.cost_components_C0_C1.cost_components.C0_labor.component_breakdown[]` | `REQUIRED_MISSING` | §17.2 G1 | Real production chain on case_02 fixture | Slice C | C0 labor component breakdown | **YES** |
| `expected_output.cost_components_C0_C1.cost_components.C1_total.component_breakdown[]` | `REQUIRED_MISSING` | §17.2 G2 | Real production chain on case_02 fixture | Slice C | C1 total component breakdown | **YES** |
| `expected_output.life_cycle_energy_envelope.P_intake_kW` | `REQUIRED_MISSING` | §17.2 G3 | Real production chain on case_02 fixture | Slice C | Life-cycle intake power | **YES** |
| `expected_output.life_cycle_energy_envelope.P_total_kW` | `REQUIRED_MISSING` | §17.2 G4 | Real production chain on case_02 fixture | Slice C | Life-cycle total power | **YES** |
| `expected_output.life_cycle_energy_envelope.P_cooling_kW` | `REQUIRED_MISSING` | §17.2 G5 | Real production chain on case_02 fixture | Slice C | Life-cycle cooling power | **YES** |
| `expected_output.life_cycle_energy_envelope.P_loop_kW` | `REQUIRED_MISSING` | §17.2 G6 | Real production chain on case_02 fixture | Slice C | Life-cycle loop power | **YES** |
| `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.annual_operating_hours` | `REQUIRED_MISSING` | this amendment | Real production chain on case_02 fixture | Slice C | Hours per year | **YES** |
| `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.design_life_years` | `REQUIRED_MISSING` | this amendment | Real production chain on case_02 fixture | Slice C | Design life in years | **YES** |
| `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.annual_energy_MJ` | `REQUIRED_MISSING` | this amendment | Real production chain on case_02 fixture | Slice C | Annual energy MJ | **YES** |
| `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.total_lifecycle_energy_MJ` | `REQUIRED_MISSING` | this amendment | Real production chain on case_02 fixture | Slice C | Total lifecycle energy MJ | **YES** |
| `expected_output.life_cycle_energy_envelope.blocker_codes` | `REQUIRED_MISSING` | this amendment | Real production chain on case_02 fixture | Slice C | Per-field blocker codes (e.g. `P_intake_kW` not yet derivable) | **YES** |
| `expected_output.selected_cost_model.selected_model_id` | `REQUIRED_MISSING` | this amendment | Real production chain on case_02 fixture | Slice C | Selected cost-model identifier | **YES** |
| `expected_output.selected_cost_model.selection_blockers[]` | `REQUIRED_MISSING` | this amendment | Real production chain on case_02 fixture | Slice C | Selection blocker list | **YES** |
| `expected_output.discounted_total_minor_units` | `DEFERRED` | TASK-018 §5.3 / §17A.4.2 | Discount formula not yet contract-frozen | separately authorized future cost-model scope outside TASK-019 Design Amendment 002-K, task number unassigned future round | Discounted total (separately authorized future cost-model scope outside TASK-019 Design Amendment 002-K, task number unassigned) | **YES** (and stays missing) |
| `expected_output.salvage_minor_units` | `DEFERRED` | TASK-018 §5.3.2 / §17A.4.2 | Salvage formula not yet contract-frozen | separately authorized future cost-model scope outside TASK-019 Design Amendment 002-K, task number unassigned future round | Salvage value (separately authorized future cost-model scope outside TASK-019 Design Amendment 002-K, task number unassigned) | **YES** (and stays missing) |
| `expected_output.unspecified_blocker.*` | `EXISTING_FROZEN` (case_03 only; case_02 may mirror) | case_03 / §17A | n/a in this amendment | n/a | Audit marker for unknown blockers | n/a (case_02 may add in Slice C if chain reports unspecified blockers) |
| `expected_output.slice3a_blocked_field_paths.*` | `EXISTING_FROZEN` (case_02) | 002-G frozen | n/a | already written (case_02) | Slice-3A / Slice-3B field path status markers | NO (case_02) |
| `expected_output.provenance.*` (record provenance / selection trace) | `REQUIRED_MISSING` | §17A.4.1 / Slice A | Slice A: explicit `provenance_amendment_id` per record | Slice A + Slice C | Per-record traceability | **YES** (block until Slice A) |

**Reading the table**:

- Rows marked “Currently missing = **YES**” are gated on Slice C. None of them may be authored by §17A itself.
- Rows marked “Currently missing = NO” are already present and frozen; do NOT modify.
- Rows in `DEFERRED` state are explicitly out of scope for §17A; do NOT author them.

### §17A.5.3 Anti-invention discipline (binding)

Per §17.7 item 2 and §17A.10, the following is the **only** allowed write sequence for any `REQUIRED_MISSING` / `DERIVED_VIA_CHAIN` / `PROHIBITED_MANUAL` field, after §17A.8.6 has been explicitly lifted:

1. Run the real production chain on the case_02 fixture input.
2. Capture the deterministic output.
3. Write the captured value into the `expected_output` field.
4. Commit the fixture change.

**Reverse order is forbidden** (write-then-verify). **Hand-calculation is forbidden**. **Copy from a documentation example is forbidden**. **Use of a mocked production output as fixture authority is forbidden**. **Modification of `expected_output` before the production output exists is forbidden**.

The “deterministic” qualifier in step 1 means: the production chain run MUST be reproducible on a clean checkout given the same fixture input. If the chain output is non-deterministic (e.g. time-of-day, random seed, env-var dependency), the run MUST be reported as a non-determinism discovery and the field MUST remain `REQUIRED_MISSING` until the non-determinism is resolved.

---

## §17A.6 Fixture Derivation Protocol (binding, contract-frozen)

### §17A.6.1 The only allowed derivation sequence (binding)

Any future round that wishes to populate a `REQUIRED_MISSING` / `DERIVED_VIA_CHAIN` / `PROHIBITED_MANUAL` expected_output field on case_02 MUST first satisfy §17A.8.6 and then follow this exact sequence, in this exact order. Skipping any step or reordering any step is a §17A.10 violation.

1. **Prepare authorized fixture inputs**: confirm the case_02 fixture has the required `input.cost_records_bridge` (Slice A), `input.cost_model_selection` (Slice A), and any other Slice A–authored input sub-blocks. If any required input is missing, STOP and return to Slice A — do NOT proceed.
2. **Execute the real production chain**: run the production chain on the case_02 fixture input. The chain MUST be the case_02 selection / cost-stack production chain (per the contract pattern in §15.3.2 Q2 and §17A.4). It MUST NOT be a mock, a stub, a hand-rolled script, or a partial re-implementation.
3. **Capture actual deterministic output**: record the chain’s output as a structured value. Record the chain invocation timestamp, the input snapshot, and the chain version (commit SHA) for traceability.
4. **Verify internal reconciliation**: confirm the captured output is internally consistent (e.g. C0_material + C0_labor = C1_total within tolerance; annual_energy_MJ × design_life_years ≈ total_lifecycle_energy_MJ; selected_model_id corresponds to the actual selection logic; selection_blockers list is non-empty iff the chain actually reported blockers).
5. **Write captured values into `expected_output`**: for each captured field, write the value into the case_02 fixture. Add or update the `slice3a_blocked_field_paths` markers per the existing pattern (case_03 is the reference; case_02 mirrors it).
6. **Add or update assertions**: add focused assertions that bind the new `expected_output` fields to the chain’s actual output (i.e. a `tests/.../test_case_02_cost_stack.py::test_expected_output_matches_chain_output` style assertion). DO NOT add assertions that bind `expected_output` to hand-calculated values.
7. **Re-run focused tests**: run the test suite. Confirm that (a) the case_02 chain still reports `WIRED_VIA_CHAIN_FULL` (or the appropriate partial status), (b) the new assertions pass, (c) no existing test (especially the hard-coded `test_expected_output_unchanged_across_adapter_runs`) regresses.
8. **Commit fixture and test changes separately from production changes**: the fixture change and the test change are committed in one commit; any production change (if Slice B is in flight) is in a separate commit. The two commits reference each other in the commit message body.

### §17A.6.2 Explicitly forbidden (binding)

The following are forbidden at every step of §17A.6.1, regardless of author intent or round authorization:

- **Reverse-engineering expected values from desired assertions**: writing a `test_case_02_*.py` assertion first, then writing `expected_output` to satisfy it, then claiming the chain “happens to” produce the asserted value. This is a §17A.10 anti-fabrication violation.
- **Hand-calculating placeholders**: writing a number into `expected_output` that was computed by hand (e.g. “C1_total = C0_material + C0_labor”) without running the production chain. This is a §17A.10 anti-fabrication violation, even if the hand calculation is correct.
- **Copying values from documentation examples**: writing a number into `expected_output` that was copied from a §17A / §17 / §15 / §16 example, a PR description, an Issue body, or any other prose artifact. Examples in prose are NOT authority for `expected_output` per §17A.10.
- **Using mocked production outputs as fixture authority**: writing a number into `expected_output` that was produced by a mock, a stub, a partial re-implementation, or any chain variant that is NOT the real production chain. This is a §17A.10 anti-fabrication violation.
- **Modifying `expected_output` before the production output exists**: writing any number into `expected_output` when no real production chain run has been performed in the current round. This is a §17A.10 anti-fabrication violation.

### §17A.6.3 Determinism guarantee (binding)

The production chain output captured in step 2 of §17A.6.1 MUST be deterministic with respect to the fixture input. “Deterministic” means: given the same fixture input bytes, the chain produces the same output bytes on a clean checkout, modulo the following explicitly allowed variations:

- Floating-point rounding error (within the existing `_tolerance_metadata.json` tolerances).
- External system clock (used for `provenance.amendment_id` timestamps; not for any numeric value).
- External file-system listing order (NOT used by the chain; if the chain uses file listing, it is a chain non-determinism that MUST be reported).

If the chain output varies in any other way (e.g. different `record_id` ordering, different `selected_model_id`, different `selection_blockers` set), the round MUST report the non-determinism and STOP. The field MUST remain `REQUIRED_MISSING` until the non-determinism is resolved.

---

## §17A.7 Thermal and Pressure-Drop Exclusion Boundary (binding, contract-frozen)

### §17A.7.1 Items NOT in scope for this amendment (binding)

The following are **explicitly excluded** from this amendment. They are NOT implementation targets under §17A. They are NOT future Slices A–D targets. They are NOT to be authored in any §17A implementation artifact.

- **Pressure-drop calculation** (any algorithm, any formula, any method).
- **TEMA method** (any TEMA configuration schema, TEMA tube layout, TEMA shell diameter, TEMA tube-side rating).
- **Kern method** (any Kern screening, Kern correlation, Kern formula).
- **Bell-Delaware method** (any Bell-Delaware correlation, Bell-Delaware formula).
- **Thermal rating** (any thermal-method computation, any thermal-method acceptance criteria, any thermal expansion screening).
- **Exchanger hydraulic sizing** (any hydraulic-network computation, any pump / compressor curve integration).
- **Correlation selection** (any new correlation ID, any correlation registry mutation).
- **Empirical coefficient authoring** (any new constant, any new curve fit, any new vendor data).

The M3 family is separately governed by `docs/TASK_BACKLOG.md`. The literal backlog statement that “TASK-020 through TASK-039 cover TEMA configuration schemas…” is a repository quotation and does not allocate any of these methods to this amendment. None of these methods is authorized by TASK-019 Design Amendment 002-K.

### §17A.7.2 Forbidden content (binding)

§17A implementation artifacts (PRs, commits, fixture files, test files, documentation) MUST NOT contain any of the following:

- Pressure-drop formulas (C4 / TEMA / Kern / Bell-Delaware / equivalent).
- Bell-Delaware formulas.
- Kern formulas.
- TEMA formulas.
- Thermal implementation content (thermal-method computation, thermal expansion screening, thermal-method acceptance criteria).
- Empirical coefficient values (new constants, new curve fits, new vendor data).
- Correlation selection logic.
- Any code, pseudo-code, formula, or algorithm hint for any of the above.

§17A.7.2 is a §17A.10 anti-fabrication guard. Violation is a hard STOP. Future thermal or pressure-drop design cards require separate Charles authorization and task-number assignment.

### §17A.7.3 Cross-references (binding)

The exclusion boundary in §17A.7 is consistent with the TASK-019 design contract:

- §6 of TASK-019 design contract (`pressure drop remains NOT_COMPUTABLE`).
- §15.8 of TASK-019 design contract (Amendment 002-H does NOT authorize pressure-drop / thermal).
- §16.8 of TASK-019 design contract (Amendment 002-I does NOT authorize pressure-drop / thermal).
- §17.5 of TASK-019 design contract (pressure-drop / thermal-method exclusion boundary).
- `pressure_drop_excluded_from_taska_019: true` marker on `case_01_heat_balance_rating.json` / `case_02_materials_mass_mechanical.json` / `case_03_cost_lifecycle_envelope.json`.

---

## §17A.8 Implementation Slices and Gates (binding, contract-frozen)

The implementation described by this amendment is split into **four slices**, each with explicit **entry conditions** and **exit conditions**. Each slice is a separate Charles-authorized round. No slice may begin until the previous slice’s exit conditions are met. No slice may combine with another slice. Section §17A.8.6 currently blocks all four slices.

### §17A.8.1 Amendment 002-K Slice A — Fixture / Input Authority

| Field | Value |
|---|---|
| Scope | Author the case_02 `input.cost_records_bridge` sub-block + the case_02 `input.cost_model_selection` sub-block + the case_02 `input.lifecycle_inputs` sub-block (where applicable). |
| Does NOT | Author any expected_output numeric value. Author any algorithm. Modify any production code. Modify any test. |
| Entry conditions | (1) This amendment is merged into `main`. (2) §17 is merged into `main`. (3) §17A.8.6 has been explicitly lifted by a Charles-authorized round with a traceable business Source. (4) Charles explicitly authorizes Slice A. |
| Exit conditions | (1) The case_02 fixture has `input.cost_records_bridge` (one entry per required record per §17A.3.3, with all 5 attributes populated). (2) The case_02 fixture has `input.cost_model_selection` (with explicit `currency_ISO_4217`, `date_ISO_8601`, `escalation_rule_id`, `region_id`). (3) The case_02 fixture has `input.lifecycle_inputs` (with explicit `annual_operating_hours`, `design_life_years`, `discount_rate_input`, `fouling_energy_penalty_factor`, `salvage_fraction_input`). (4) `_provenance_metadata.json` is updated with Slice A provenance entries. (5) The fixture contract test (`test_expected_output_unchanged_across_adapter_runs`) still passes (no regression in the `mass_kg.fluid_mass_kg == 1.05` assertion). |
| Forbidden write | Any `expected_output.*` numeric value, any `actual_output.*` value, any production code change, any test change, any algorithm hint. |

### §17A.8.2 Amendment 002-K Slice B — Production Cost-Stack Coverage

| Field | Value |
|---|---|
| Scope | Implement the case_02 cost-record selection / traversal logic (per §17A.4.1) and the case_02 cost-stack production chain (per §17A.3.2). |
| Does NOT | Modify `expected_output` to mask a chain error. Author any runtime catalog scan / resolver. Author any pressure-drop / thermal / discount / salvage logic. |
| Entry conditions | (1) Slice A exit conditions met. (2) Charles explicitly authorizes Slice B. |
| Exit conditions | (1) The case_02 production chain executes end-to-end on the case_02 fixture input. (2) The chain reports `WIRED_VIA_CHAIN_FULL` (or the appropriate partial status with explicit `selection_blockers` entries). (3) The chain output is deterministic per §17A.6.3. (4) No production code path mutates `expected_output`. (5) The chain output is logged to `/tmp/case_02_chain_output_<commit_sha>.json` for traceability. |
| Forbidden write | Any `expected_output` mutation. Any runtime catalog scan. Any runtime resolver. Any pressure-drop / thermal / discount / salvage logic. |

### §17A.8.3 Amendment 002-K Slice C — Fixture Capture

| Field | Value |
|---|---|
| Scope | Run the Slice B production chain on the case_02 fixture. Capture the deterministic output. Write the captured values into case_02 `expected_output` per §17A.5.2. |
| Does NOT | Re-author the production chain. Author any value not produced by the chain. Modify the chain’s output. |
| Entry conditions | (1) Slice B exit conditions met. (2) Charles explicitly authorizes Slice C. |
| Exit conditions | (1) Every `REQUIRED_MISSING` field in §17A.5.2 is populated with the captured value. (2) The captured value matches the chain output byte-for-byte (no manual overwrite, no hand-calculated substitution). (3) `_provenance_metadata.json` is updated with Slice C provenance entries. (4) `_tolerance_metadata.json` is updated with the new field tolerances (preserving existing 001 / 002-F / 002-G tolerance values for the 4 mass_kg fields + preliminary_mechanical_check.status). (5) The fixture contract test still passes. |
| Forbidden write | Any value not produced by the Slice B production chain run. Any reverse-order write (assertion-first, expected_output-second). |

### §17A.8.4 Amendment 002-K Slice D — Assertions and Reconciliation

| Field | Value |
|---|---|
| Scope | Add focused tests that bind `expected_output` to the Slice C captured values. Verify component sum / total consistency. Verify record provenance. Verify deterministic ordering. |
| Does NOT | Add assertions that bind `expected_output` to hand-calculated values. Re-author any existing test. |
| Entry conditions | (1) Slice C exit conditions met. (2) Charles explicitly authorizes Slice D. |
| Exit conditions | (1) New tests added under `tests/validation_report/test_case_02_cost_stack.py` (or equivalent). (2) C0_material + C0_labor = C1_total within tolerance assertion exists. (3) annual_energy_MJ × design_life_years ≈ total_lifecycle_energy_MJ within tolerance assertion exists. (4) Per-record `provenance_amendment_id` assertion exists. (5) Deterministic ordering assertion exists (e.g. record order in `selected_cost_model.selection_blockers` is stable across reruns). (6) The fixture contract test still passes. (7) All new tests pass. |
| Forbidden write | Any assertion that binds `expected_output` to hand-calculated values. Any modification to existing tests. Any pressure-drop / thermal / discount / salvage assertion. |

### §17A.8.5 Inter-slice discipline (binding)

- Slices MUST be executed in order A → B → C → D. Out-of-order execution is a §17A.10 anti-fabrication violation.
- Each Slice is a separate Charles-authorized round. Combining Slices is a §17A.10 anti-fabrication violation.
- Each Slice’s commit message MUST name the Slice (e.g. `docs(task-019): amendment 002-k slice A — fixture authority`).
- The four Slices’ commits MAY be in the same branch but MUST be separate commits with separate provenance entries.

### §17A.8.6 Business Cost Source Availability Gate (binding, contract-frozen)

Implementation under TASK-019 Design Amendment 002-K requires a traceable case_02 business cost Source before Slice A may begin. This subsection codifies the business-source availability gate as a hard precondition for every Amendment 002-K implementation slice.

**Acceptable Source types** (case_02 business cost Source, in priority order):

- approved cost catalog (TASK-013 governed; case_02-bound entries with stable `cost_record_id` and `cost_record_version`; documented `source_*` fields; `provenance_chain_hash` reproducible from canonical JSON of `{source_record_ids, correlation_ids, case_input_field, license_class, schema_version}` per TASK-018 §7 / §10);
- supplier quotation (with quote ID, effective date, currency, region, escalation rule, validity period, vendor contact);
- contract or purchase record (with contract ID, line-item breakdown, effective date, party identification);
- formally approved internal cost baseline (with approval ID, approver chain, effective date, scope statement);
- another Charles-confirmed, traceable business Source (must be explicitly named by Charles in a separate authorization message).

**Current state** (binding, governance-only):

```text
TASK019_AMENDMENT_002K_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE
```

While this state applies, the following are ALL **explicitly forbidden**:

- Amendment 002-K Slice A is blocked.
- Amendment 002-K Slice B is blocked.
- Amendment 002-K Slice C is blocked.
- Amendment 002-K Slice D is blocked.
- fixture mutation is forbidden.
- expected_output capture is forbidden.
- production mutation is forbidden.
- cost-related test mutation is forbidden.

**Implementation authorization cannot be inferred** from:

- Issue #120 (`TASK-020: case_02 cost-stack coverage and fixture authority`), which is preserved only as a historical source-availability tracking artifact under the superseded TASK-020 label;
- Issue #122, which authorized only the corrective 002-K identity re-home and creation of the Draft PR; the later Ready transition was separately authorized by Charles after final docs-only re-review and does not authorize merge or implementation;
- this Amendment 002-K design contract itself (governance-only);
- any prior Slice entry condition being individually met;
- any §17A.10 anti-fabrication check passing (passing anti-fabrication checks is necessary but NOT sufficient for business-source authorization).

The state `TASK019_AMENDMENT_002K_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE` is lifted only by a future Charles-authorized round that:

1. identifies the specific case_02 business cost Source from the five acceptable types above;
2. documents the Source identity, version, effective date, and authority chain;
3. explicitly states that the Source is sufficient for Amendment 002-K Slice A entry and downstream slices;
4. updates the §17A.9 register status of the relevant R-items (R2 / R9 / R10 / R11 / R22 / R23) from `REPO_SOURCE_REQUIRED` to `RESOLVED` or to another separately authorized state, with provenance recorded in `_provenance_metadata.json`.

Until that round, **no TASK-019 Design Amendment 002-K implementation slice is authorized**, regardless of any other gate status.

---

## §17A.9 Source-Missing Register (binding, contract-frozen)

The following table is the **formal register** of source-missing items. Each item is classified by ID, missing authority, why required, blocked downstream work, acceptable source type, anti-fabrication rule, and status. Status is one of: `SOURCE_MISSING` / `CHARLES_SOURCE_REQUIRED` / `REPO_SOURCE_REQUIRED` / `DEFERRED` / `RESOLVED`. Items with no current source MUST NOT be marked `RESOLVED`.

| ID | Missing authority | Why required | Blocked downstream work | Acceptable source type | Anti-fabrication rule | Status |
|---|---|---|---|---|---|---|
| R1 | case_02 full cost-stack source authority (6 deferred fields per §17.2) | Required by §17A.5.2 (`REQUIRED_MISSING` rows) | Slice C fixture capture (cannot run chain without a contract-frozen cost-stack source) | Real production chain on case_02 fixture input (per §17A.6) | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible on a clean checkout | `SOURCE_MISSING` |
| R2 | case_02 cost-record selection authority (per §17A.3.2) | Required by §17A.3.3 record-role mapping | Slice A (cannot author `input.cost_records_bridge` without record-role mapping) | `input.cost_records_bridge` (case-bound, frozen, audit-traceable) authored in Slice A | MUST NOT be inferred; MUST be explicitly declared per §17A.3.3 (5 attributes per record) | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R3 | case_02 expected_output authority for `cost_components_C0_C1.*` | Required by §17A.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R4 | case_02 expected_output authority for `life_cycle_energy_envelope.*` | Required by §17A.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R5 | case_02 expected_output authority for `selected_cost_model.*` | Required by §17A.5.2 | Slice C | Real production chain output (case_03 pattern reference) | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R6 | case_02 catalog traversal authority (per §17A.4) | Required by §17A.4.1 (in scope) and §17A.4.2 (out of scope) | Slice B (cannot implement selection without a traversal boundary) | `input.cost_records_bridge` traversal (case-bound, deterministic, no runtime discovery) | MUST NOT be runtime scan; MUST NOT be network lookup; MUST NOT be plugin resolution; MUST be `cost_records_bridge` array iteration only | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R7 | Discount formula / calculation authority | Required by `expected_output.discounted_total_minor_units` (case_03 pattern) | separately authorized future cost-model scope outside TASK-019 Design Amendment 002-K, task number unassigned future design card (NOT in this amendment scope) | Future separately authorized cost-model design card | MUST NOT be invented under this amendment; MUST be a separate Charles-authorized round | `DEFERRED` |
| R8 | Salvage formula / calculation authority | Required by `expected_output.salvage_minor_units` (case_03 pattern) | separately authorized future cost-model scope outside TASK-019 Design Amendment 002-K, task number unassigned future design card (NOT in this amendment scope) | Future separately authorized cost-model design card | MUST NOT be invented under this amendment; MUST be a separate Charles-authorized round | `DEFERRED` |
| R9 | case_02 `input.cost_records_bridge` (the sub-block itself) | Required by §17A.4.1 and §17A.3.2 | Slice A (cannot start Slice A without the contract-frozen sub-block shape) | Slice A authoring after §17A.8.6 is lifted | MUST NOT be invented under this amendment | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R10 | case_02 `input.cost_model_selection` (the sub-block itself) | Required by §17A.3.2 (case_03 pattern: `currency_ISO_4217`, `date_ISO_8601`, `escalation_rule_id`, `region_id`) | Slice A | Slice A authoring after §17A.8.6 is lifted | MUST NOT be invented under this amendment | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R11 | case_02 `input.lifecycle_inputs` (the sub-block itself) | Required by §17A.5.2 (`life_cycle_energy_envelope.life_cycle_energy_summary.*`) | Slice A | Slice A authoring after §17A.8.6 is lifted | MUST NOT be invented under this amendment | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R12 | case_02 expected_output authority for `cost_components_C0_C1.cost_components.C0_material.component_breakdown[]` | Required by §17.2 G1 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R13 | case_02 expected_output authority for `cost_components_C0_C1.cost_components.C0_labor.component_breakdown[]` | Required by §17.2 G1 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R14 | case_02 expected_output authority for `cost_components_C0_C1.cost_components.C1_total.component_breakdown[]` | Required by §17.2 G2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R15 | case_02 expected_output authority for `life_cycle_energy_envelope.life_cycle_energy_summary.annual_operating_hours` | Required by §17A.5.2 | Slice C | Real production chain output (case_03 pattern reference) | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R16 | case_02 expected_output authority for `life_cycle_energy_envelope.life_cycle_energy_summary.design_life_years` | Required by §17A.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R17 | case_02 expected_output authority for `life_cycle_energy_envelope.life_cycle_energy_summary.annual_energy_MJ` | Required by §17A.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R18 | case_02 expected_output authority for `life_cycle_energy_envelope.life_cycle_energy_summary.total_lifecycle_energy_MJ` | Required by §17A.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R19 | case_02 expected_output authority for `life_cycle_energy_envelope.blocker_codes` | Required by §17A.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R20 | case_02 expected_output authority for `selected_cost_model.selected_model_id` | Required by §17A.5.2 | Slice C | Real production chain output (case_03 pattern reference) | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R21 | case_02 expected_output authority for `selected_cost_model.selection_blockers[]` | Required by §17A.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R22 | case_02 expected_output authority for `provenance.*` (record provenance / selection trace) | Required by §17A.4.1 | Slice A | Slice A authoring (`provenance_amendment_id` per record), after §17A.8.6 is lifted | MUST NOT be invented; MUST be a stable case-bound identifier | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R23 | case_02 fixture `amendment_id` and `amendment_status` update for this amendment | Required by governance sync | After §17A is merged, governance sync may update case_02 `amendment_id` to `"TASK-019-DESIGN-AMENDMENT-002-K"` (post-merge, separate round) | Post-§17A-merge governance sync | MUST NOT be updated under §17A itself; MUST be a separate post-merge round | `REPO_SOURCE_REQUIRED` (via post-merge governance sync) |
| R24 | TASK-019 Design Amendment 002-K tracking GitHub Issue | Required for Slice A / B / C / D tracking | Slice A entry condition requires separate Charles authorization | Issue #120 is historical source-availability tracking under the superseded label; Issue #122 is corrective identity governance only | Neither Issue resolves business-source authority or authorizes implementation | `CHARLES_SOURCE_REQUIRED` |
| R25 | Pressure-drop / thermal-method / TEMA / Kern / Bell-Delaware implementation authority | Excluded from this amendment (per §17A.7) | n/a (out of this amendment scope) | Future separately authorized design card with task number unassigned | MUST NOT be authored under this amendment; MUST be a separate Charles-authorized round | `DEFERRED` |

**Status transition rule (binding)**: a register item’s status MAY transition from `SOURCE_MISSING` / `REPO_SOURCE_REQUIRED` / `CHARLES_SOURCE_REQUIRED` to `RESOLVED` ONLY in the round that actually produces the missing authority. The status transition MUST be recorded in `_provenance_metadata.json` and the §17A.9 register in a future round. A `RESOLVED` item in this round’s register is a §17A.10 anti-fabrication violation.

**§17A.9 register-level note (business-source availability governance, preserved from PR #121 and re-homed under Amendment 002-K)**: The R1–R25 item statuses remain unchanged in this amendment. The overall Amendment 002-K implementation state is blocked by unavailable business cost Source under §17A.8.6 `TASK019_AMENDMENT_002K_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE`.

- Issue #120 remains a historical source-availability tracking artifact under the superseded TASK-020 label. Issue #122 is the corrective 002-K governance Issue. **Neither Issue resolves the business Source blockers or authorizes an implementation slice.**
- No R-item becomes `RESOLVED` in this round. R1–R25 retain their existing statuses (`SOURCE_MISSING` × 14 / `REPO_SOURCE_REQUIRED` × 7 / `CHARLES_SOURCE_REQUIRED` × 1 / `DEFERRED` × 3 / `RESOLVED` × 0). The blocked state does NOT transition any R-item to `RESOLVED`; a future Charles-authorized round with a real business cost Source is the only valid path to lift the state and transition R2 / R9 / R10 / R11 / R22 / R23 in particular.
- The blocked state applies to Amendment 002-K implementation slices, NOT to this governance-only corrective re-home. The corrective governance-only re-home does not require a business cost Source to preserve and rename the contract.

---

## §17A.10 Non-Actions and Anti-Fabrication Guard (binding, contract-frozen)

### §17A.10.1 Non-action declarations (binding)

The following declarations are **explicitly non-actions** of §17A. Each is a §17A.10 anti-fabrication fact that any future round (Slice A / B / C / D or any other) MUST honor.

- **§17A design document does NOT authorize implementation.** This amendment is a design contract. Any implementation under this amendment alone is a §17A.10 violation. Implementation requires Slice A → B → C → D, each with its own Charles-authorized round, after §17A.8.6 is lifted.
- **A skeleton is NOT an implementation approval.** §17A.8’s four Slices are skeletons, not approvals. Each Slice’s explicit Charles-authorization entry condition is a hard gate.
- **A missing field is NOT an invitation to supply a default.** A `REQUIRED_MISSING` field in §17A.5.2 stays missing until an authorized production-chain run in Slice C captures the value. No default, no placeholder, no first-valid-record, no copy from a sibling case.
- **The current fixture subset is NOT a complete catalog.** case_02 currently has mass-chain bridges (002-F / 002-G) but no cost-stack bridges. The absence of a cost-stack bridge is NOT a license to invent one under §17A. The cost-stack bridge is gated on Slice A and §17A.8.6.
- **The current selector output is NOT a complete cost stack.** case_03’s `CostModelSelector.select` (per §15.3.2 Q2) consumes the case_03 `cost_records_bridge` and emits a curated-subset output. That output is NOT a “complete” cost stack. The 6 §17.2 deferred fields are NOT covered by case_03’s selector output.
- **The existence of `total cost` is NOT a license to claim component breakdown is authorized.** If a future round writes `expected_output.cost_components_C0_C1.cost_components.C1_total_minor_units` it MUST also write `C0_material_minor_units` and `C0_labor_minor_units` and the component breakdowns per §17.2 G1 / G2. A total without components is a §17A.10 anti-fabrication violation.
- **A documentation example is NOT `expected_output` authority.** Numbers appearing in this amendment / §17 / §15 / §16 prose are examples, not authority. Authority is the production-chain output captured in Slice C after all gates are satisfied.
- **A test convenience is NOT business authority.** A test asserting `assert expected_output.cost_components_C0_C1.cost_components.C1_total_minor_units == 12345` does NOT make 12345 the business authority for that field. Business authority comes from a traceable Source and the authorized production chain.

The following additional anti-fabrication rules apply while `TASK019_AMENDMENT_002K_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE` is in effect:

- **No synthetic cost records.** Creating artificial cost records through a hand-written loop, generated sequence, test fixture, mock, or any other method to satisfy schema or test requirements is a §17A.10 violation. A `cost_records_bridge` list may remain empty; it MUST NOT be populated with invented records.
- **No placeholder monetary values.** Writing `0` or any non-real number into `cost_value_minor_units` to satisfy schema or test requirements is a §17A.10 violation. The schema requires an integer only when a real business Source exists. An empty list is the correct representation while the Source is unavailable.
- **No zero values used merely to satisfy schema or tests.** A `0` in `cost_value_minor_units` is a positive business claim that cost equals zero minor units. It is NEVER a placeholder.
- **No random or example record IDs.** Inventing IDs such as `EXAMPLE-001`, `TEST-RECORD`, `PLACEHOLDER`, or any non-traceable identifier is a §17A.10 violation. Real `cost_record_id` values come from an authorized Source and documented naming convention.
- **No copying case_03 cost records into case_02.** Case_03’s `cost_records_bridge` records are case_03-specific and bound to `TASK-019-DESIGN-AMENDMENT-002-H`. Copying those records or their cost values into case_02 would misattribute the Source. The two cases share the bridge PATTERN, not the bridge CONTENT.
- **No copying case_03 monetary values into case_02.** A case_02 `cost_value_minor_units` MUST come from a case_02-specific business Source. Values in `case_03_cost_lifecycle_envelope.json` MUST NOT be copied or adapted into case_02.
- **No deriving component costs by reversing a target total.** Computing `C0_material` or `C0_labor` from a guessed `C1_total`, or vice versa, is hidden source fabrication.
- **No deriving costs from equipment mass without an authorized cost Source.** Multiplying a case_02 mass value by a guessed unit price is source fabrication. Equipment mass is a derived quantity, not unit-price authority.
- **No filling required fields solely to make tests pass.** A test requiring `cost_records_bridge` to be non-empty MUST NOT be satisfied by inventing a record. The expected blocked or empty state must be tested instead.
- **No treating `null`, empty string, or empty list as a completed business Source.** These are explicit not-yet-sourced markers. The blocked state is the correct governance representation while the Source is unavailable.

**Schema existence is not business-value authority.** A required field declares SHAPE; a traceable business Source provides VALUE. The two are independent.

**A field being required does not authorize invention of its value.** Until the Source exists, “required” means the field must be filled when authority becomes available, not that it must be filled now with an arbitrary value.

### §17A.10.2 Anti-fabrication checks (binding)

The following checks MUST be performed by any future round that authors an artifact in the TASK-019 Design Amendment 002-K lineage (Slice A / B / C / D, governance sync, fixture update, test update, production change):

1. **No invented numeric expected values**: any number in `expected_output` MUST be traceable to a real production-chain run. The chain run MUST be in the same round’s commit log. The chain invocation timestamp + commit SHA MUST be in `_provenance_metadata.json`.
2. **No TODO-as-authorized-scope**: any `TODO` / `FIXME` / `placeholder` / `to-be-determined` in a Slice A / B / C / D commit MUST be flagged as a §17A.10 violation. Slice commits MUST be complete or explicitly aborted.
3. **No pressure-drop / Bell-Delaware / Kern / TEMA / thermal implementation content**: per §17A.7. Any such content in an Amendment 002-K lineage commit is a hard STOP.
4. **No runtime catalog scan authorization**: per §17A.4.2. Any code that performs a runtime catalog scan in an Amendment 002-K lineage commit is a hard STOP.
5. **No production implementation claims**: §17A lineage commits MUST NOT claim that any production capability is implemented or available beyond the existing TASK-019 frozen baseline. Slice B is a future round, not this round.
6. **No cross-Slice scope creep**: a Slice A commit MUST NOT include Slice B / C / D content. A Slice C commit MUST NOT include Slice A / B / D content. The four Slices are separate commits.
7. **No fixture contract test regression**: the hard-coded `test_expected_output_unchanged_across_adapter_runs` assertion on `fixture_02["expected_output"]["mass_kg"]["fluid_mass_kg"] == 1.05` MUST NOT regress under any Amendment 002-K lineage change.
8. **Business-source gate remains binding**: no implementation artifact may be authored while §17A.8.6 remains in the blocked state.

### §17A.10.3 STOP conditions (binding)

The following conditions are hard STOPS. Any TASK-019 Design Amendment 002-K lineage round that encounters any of these MUST stop immediately and report the violation to Charles. The violation is binding and may not be silently fixed.

- A `RESOLVED` status in the §17A.9 register without the separately authorized round that actually produces and records the missing authority.
- An `expected_output` numeric value that is NOT traceable to a real authorized production-chain run and business Source.
- A pressure-drop / Bell-Delaware / Kern / TEMA / thermal implementation in an Amendment 002-K lineage commit.
- A runtime catalog scan / resolver in an Amendment 002-K lineage commit.
- A combined-slice commit (e.g. one commit that includes both Slice A and Slice B content).
- An implementation Slice commit that does not name Amendment 002-K and the Slice (A / B / C / D) in the commit subject.
- Any implementation attempt while `TASK019_AMENDMENT_002K_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE` remains in effect.

---

## §17A.11 Change Log (binding)

| Date | Change | Author |
|---|---|---|
| 2026-07-10 | Initial cost-stack / fixture-authority design content authored and later merged through PR #119 under a superseded TASK-020 identity. Historical content preserved; implementation not authorized. | Charles-authorized design-only round |
| 2026-07-10 | **Business-Source Availability Gate governance addition**, originally merged through PR #121 under the superseded identity and now preserved under §17A.8.6 / §17A.9 / §17A.10. Recorded `TASK019_AMENDMENT_002K_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE`; R1–R25 status distribution remains 14 / 7 / 1 / 3 / 0; no implementation authorization. | Charles-authorized governance-only round |
| 2026-07-10 | **Amendment 002-K corrective re-home.** Corrected task identity, file path, section numbering, normative terminology, blocker token, Issue references, and authority chain without reverting or rewriting PR #119 or PR #121 history. Corrective identity remains Draft / not merged. | Charles-authorized corrective governance round; Issue #122 / Draft PR #123 |
| 2026-07-10 | **PR #123 Ready-state governance sync.** After final docs-only re-review and successful CI on head `c3f780876cb2fec99417f745636dbbec6fea34fe`, Charles separately authorized PR #123's Ready transition. PR #123 remains not merged; merge and implementation remain separately unauthorized. | Charles-authorized Ready-state sync round |
| 2026-07-10 | **Amendment 002-K post-merge closeout.** PR #123 reviewed head `b409a3a6ef94f337a9734e25e4ba354f2c68701d` merged into `main` at commit `905b46753c33603ebdc61148871e40ffb0481c4f` (merged at 2026-07-10T12:16:40Z); main push CI run `29092046857` completed / success. R1–R25 status distribution (14 / 7 / 1 / 3 / 0), business-source gate, Slice A–D blocker, and implementation NOT AUTHORIZED are preserved unchanged; §17A.8.6 cyclic gate remains for a separate follow-up amendment and is intentionally NOT resolved in this closeout. PR #118 remains Draft; TASK-021–TASK-039 remain unallocated; Issue #122 is intentionally NOT closed in this round. | Charles-authorized post-merge closeout round; PR #123 / `docs/task-019-amendment-002k-closeout` |

---

**Final declaration**:

> **TASK-019 DESIGN AMENDMENT 002-K CORRECTIVE IDENTITY CONTRACT MERGED INTO MAIN / DESIGN FROZEN / MAIN-CI-VERIFIED; IMPLEMENTATION NOT AUTHORIZED; READY AND MERGE AUTHORIZATIONS COMPLETED PER THE PR #123 / 905b46753 LIFECYCLE.**
> **This is a corrective re-home of design content originally merged via PR #119 and supplemented via PR #121 under a superseded TASK-020 label; those labels are historical and non-authoritative.**
> **BUSINESS COST SOURCE UNAVAILABLE; AMENDMENT 002-K SLICES A–D BLOCKED.**
> **FIXTURE MUTATION NOT AUTHORIZED.**
> **EXPECTED OUTPUT VALUES NOT INVENTED.**
> **NO PRODUCTION, TEST, FIXTURE, OR IMPLEMENTATION MUTATION PERFORMED.**

This document is a **design contract** (governance-only). It does not authorize production implementation, fixture mutation, test mutation, or algorithm authoring. Implementation remains gated on §17A.8, with §17A.8.6 currently blocking Slices A → B → C → D and each Slice requiring a separate Charles-authorized round.
