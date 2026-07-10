# TASK-020 — Cost-stack coverage and fixture-authority design contract (binding, contract-frozen, governance-only)

| Field | Value |
|---|---|
| **Status** | DESIGN FROZEN / MERGE-NOT-AUTHORIZED |
| **Source authority** | §17 (TASK-019 Design Amendment 002-J) merged into `main`; case_02 002-G mass-chain already merged; case_03 002-H / 002-I bridge patterns already merged |
| **Scope** | case_02 full cost-stack coverage contract + fixture-authority + derivation protocol; NOT implementation |
| **Applies to** | case_02 only (`TASK-019-GOLDEN-02`); case_01 / case_03 are explicitly out of scope |
| **Forbidden items** | pressure-drop, Bell-Delaware, Kern, TEMA, thermal rating, runtime catalog scan, runtime resolver, discount formula, salvage formula, invented expected values |

> This document is a **design contract** (governance-only). It does **NOT** authorize production implementation, fixture mutation, test mutation, or any algorithm authoring. Per §20.8, the implementation may only be initiated through one of four explicitly-ordered Slices (A → B → C → D), each with its own entry and exit conditions.

---

## §20.1 Scope and Authority (binding, contract-frozen)

### §20.1.1 In-scope objectives

TASK-020 has exactly **five** in-scope objectives. Each objective is a contract-level declaration, not an implementation commitment.

1. **Extend case_02 cost-stack coverage**: extend the case_02 `expected_output` surface to carry a complete, deterministically-derived cost-stack (C0 material, C0 labor, C1 total, life-cycle energy envelope, and the cost-record selection handoff), consistent with the case_03 contract pattern at §15 and §16.
2. **Define complete cost-record selection authority**: declare the authoritative source of every cost record consumed by case_02 (input contract, record-role mapping, deterministic ordering), so that no record is sourced by inference, copy, or runtime discovery.
3. **Define catalog traversal boundary**: codify what is in-scope (deterministic traversal over an authorized catalog input) and what is out-of-scope (runtime catalog scan, network lookup, plugin resolution, heuristic matching).
4. **Define expected_output fixture derivation protocol**: lock the only allowed ordering for converting production-chain output into fixture `expected_output`. Reverse-engineering and hand-calculating are explicitly forbidden.
5. **Freeze implementation vs. non-implementation boundary**: separate the four future Slices (A / B / C / D) and declare that no production code may be authored, modified, or executed under §20 alone.

### §20.1.2 Out-of-scope declarations (binding)

TASK-020 explicitly does **NOT**:

- Re-design or re-author the case_03 selector / adapter / validation contract (§15 / §16 are already merged and frozen).
- Re-design or re-author the case_01 bridge contract.
- Re-design or re-author the case_02 mass-chain contract (already frozen at TASK-019 Design Amendment 002-G; see `case_02_materials_mass_mechanical.json` `amendment_id: TASK-019-DESIGN-AMENDMENT-002-G`).
- Implement pressure-drop, Bell-Delaware, Kern, TEMA, thermal rating, or any thermal-method algorithm (see §20.7).
- Implement runtime catalog scan, runtime catalog lookup, runtime catalog resolver, or any dynamic catalog integration (see §20.4).
- Implement discount formula, salvage formula, or any cost formula that requires an `escalation_rule` / `discount_rate` to be evaluated (see §20.4 "Out of Scope").
- Author, edit, or commit any production code, fixture, test, or configuration file as part of §20. Implementation is gated on Slices A → D, each requiring its own Charles-authorized round (see §20.8).

### §20.1.3 Authority hierarchy (binding)

The authority hierarchy for resolving any §20 question is:

1. **Charles explicit instruction** (current authorization message or future authorization message) — highest.
2. **Merged / frozen repository design contract** (`main` @ `da6e064`; §15, §16, §17, 002-A / 002-D / 002-E / 002-F / 002-G).
3. **Committed fixture + production contract** (`tests/golden/double_pipe_rating/*.json`, `_provenance_metadata.json`, `_tolerance_metadata.json`).
4. **TASK-020 preparation report** (`/root/TASK-020-preparation-report.md`, `/tmp/TASK-020-preparation-report.md`) — synthesis, not authority.
5. **Implementation inference** — lowest. Implementation inference MUST NOT override any of the above four tiers.

If two sources conflict, the higher-tier source governs. If the conflict is between two sources of the same tier, the source that is **explicit** governs over the source that is **implicit**. The "anti-fabrication guard" in §20.10 applies in all cases.

---

## §20.2 Current Frozen Baseline (binding, contract-frozen)

The following TASK-019 elements are already merged into `main` and are **unchangeable by §20**. Any future implementation that needs to alter any of these MUST be a separate Charles-authorized amendment to the TASK-019 design contract, not an action under §20.

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

§20.2 declares that all eight elements above are **frozen** for the purposes of this contract. Any future TASK-020 implementation round that needs to alter any of them MUST first amend the TASK-019 design contract through a separate Charles-authorized round.

---

## §20.3 Cost Record Selection Authority (binding, contract-frozen)

### §20.3.1 Current state (frozen, recoverable from this file + repository)

| Selection aspect | Current authority (case_02) | Repository evidence |
|---|---|---|
| Static curated fixture subset | **NOT PRESENT** in case_02 | `case_02_materials_mass_mechanical.json` has no `input.cost_records_bridge` sub-block |
| Explicitly provided records | **NOT PRESENT** in case_02 | `case_02_materials_mass_mechanical.json` has no `input.cost_records_bridge_bindings` sub-block |
| Fixture-bound selection input | **NOT PRESENT** in case_02 | case_02 has no cost-related input sub-block |
| Deterministic selection | NOT APPLICABLE in case_02 (no cost-record selection exists yet) | — |
| `cost_records_bridge` (case_03 reference) | PRESENT in case_03 (3 records: C0 material, C0 labor, C1 total) | `case_03_cost_lifecycle_envelope.json` `input.cost_records_bridge` |

### §20.3.2 TASK-020 target (binding, future Slices A + B)

§20 declares the following **target** state for the case_02 cost-record selection. These are **contract targets**, not implementation commitments; the implementation is gated on Slice A + Slice B per §20.8.

| Target aspect | Required by §20 | Implementation in |
|---|---|---|
| Complete required record set for case_02 | REQUIRED (exact field set pending Slice A source) | Slice A (input contract) + Slice B (selection logic) |
| Explicit record-role mapping (per record: identity, role, purpose, necessity) | REQUIRED (one record per required cost-stack field, derived from the 6 deferred fields in §17.2 + the curated-subset fields in `selected_cost_model` per case_03 pattern) | Slice A |
| Deterministic record ordering | REQUIRED (the order is the explicit ordering of records in `input.cost_records_bridge`; no implicit sort; no timestamp-based ordering) | Slice A + Slice B |
| No implicit fallback | REQUIRED (if a record is missing or malformed, the chain reports `WIRED_VIA_CHAIN_PARTIAL` + `selection_blockers` entries, NOT a default / placeholder / first-valid-record) | Slice B |
| No hidden runtime discovery | REQUIRED (no filesystem scan, no network lookup, no plugin resolution, no heuristic matching) | §20.4 + Slice B |

### §20.3.3 Record-role mapping rule (binding)

For every cost record that case_02 will require, the Slice A authoring round MUST declare, at minimum:

- **Identity**: a stable `record_id` (string; case-bound; no reuse across cases; no reuse across amendments).
- **Role**: one of `{C0_material, C0_labor, C1_total, life_cycle_energy_record, discount_record, salvage_record}`. Discount / salvage records are explicitly DEFERRED to TASK-020+ per §20.4 and are NOT included in Slice A.
- **Purpose**: a one-sentence statement of what cost-stack field this record supports (mapping to one of the 6 §17.2 deferred fields, or to the curated-subset `selected_cost_model.*` fields).
- **Necessity**: a `mandatory` / `optional` flag. Mandatory records are required for the chain to report `WIRED_VIA_CHAIN_FULL`; optional records contribute only if present.
- **Source**: which future real production chain (per §17.7 item 2) is authorized to derive the record's content. **No record source may be "TBD" / "to be invented" / "agent-decided" / "placeholder".**

If any of the above five attributes is **SOURCE_MISSING** (no Charles-provided text, no committed repo hook, no future production chain identified), the record is **deferred to CHARLES_SOURCE_REQUIRED** status and is **NOT** authored in Slice A.

### §20.3.4 Status register for record-role coverage

The following record roles are tracked for case_02. Statuses are the formal states defined in §20.9.

| Record role | Current status (case_02) | Required by §20.3.2 | Notes |
|---|---|---|---|
| `C0_material` | SOURCE_MISSING | YES (Slice A) | Maps to `c0_subtotal.component_breakdown[]` per §17.2 |
| `C0_labor` | SOURCE_MISSING | YES (Slice A) | Maps to `c0_subtotal.component_breakdown[]` per §17.2 |
| `C1_total` | SOURCE_MISSING | YES (Slice A) | Maps to `c1_subtotal.component_breakdown[]` per §17.2 |
| `life_cycle_energy_record` | SOURCE_MISSING | YES (Slice A) | Maps to `life_cycle_energy_envelope.P_intake_kW` / `P_total_kW` / `P_cooling_kW` / `P_loop_kW` per §17.2 |
| `discount_record` | DEFERRED | NO (excluded per §20.4) | TASK-020+ scope |
| `salvage_record` | DEFERRED | NO (excluded per §20.4) | TASK-020+ scope |

---

## §20.4 Catalog Traversal Boundary (binding, contract-frozen)

### §20.4.1 In-scope (binding; Slice B may authorize ONLY these)

The following operations are **in scope** for the future case_02 cost-record selection implementation, and ONLY these:

- **Deterministic traversal over an authorized catalog input**: a pre-authored `input.cost_records_bridge` array (case-bound, frozen, audit-traceable) is read in array order. No sort, no shuffle, no implicit reordering.
- **Explicit filtering rules**: filtering is permitted only by attribute values that are themselves explicitly listed in the bridge (e.g. `record_id`, `record_role`, `currency_ISO_4217`, `date_ISO_8601`). No attribute inference.
- **Stable ordering**: the order of records in the `cost_records_bridge` array is the authoritative order. The output selection preserves this order.
- **Reproducible selection**: given the same `cost_records_bridge` input, the chain MUST produce the same selection output byte-for-byte (no time-of-day, no random seed, no env-var dependency).
- **Traceable record provenance**: every selected record carries an explicit `provenance_amendment_id` (case-bound; cross-references the TASK-019 amendment that froze the bridge value, e.g. `"TASK-019-DESIGN-AMENDMENT-002-J"` for §20-authored content).

### §20.4.2 Out-of-scope / Deferred (binding; explicitly forbidden)

The following operations are **out of scope** for the future case_02 cost-record selection implementation. They are **NOT** authorized by §20. Any future round that wishes to authorize any of them MUST be a separate Charles-authorized amendment, not a §20 action.

- **Unrestricted runtime catalog scan** (e.g. scanning a directory tree for `*.json` files at execution time).
- **Ambient filesystem discovery** (e.g. walking `os.environ` paths to find a catalog).
- **Network catalog lookup** (any HTTP / HTTPS / FTP / SFTP / WebSocket call to a remote cost database).
- **Dynamic plugin resolution** (e.g. `importlib` dynamic import of cost catalog modules).
- **Hidden fallback records** (e.g. "if no record matches, use the first record in the catalog").
- **Heuristic record matching** (e.g. fuzzy string match, regex match, ML-based match).
- **Discount logic** (any computation involving `discount_rate` or `escalation_rule`).
- **Salvage logic** (any computation involving `salvage_fraction`).
- **Runtime resolver invention** (any new function, method, or callable that produces a cost record from sources other than the explicit `cost_records_bridge` input).

§20.4.2 explicitly forbids writing the phrase "dynamic catalog integration is authorized" anywhere in §20 implementation artifacts. Per §20.10, "current fixture subset ≠ complete catalog" and "current selector output ≠ complete cost stack" are anti-fabrication facts.

### §20.4.3 Boundary statement (binding)

§20 establishes that case_02 cost-record selection is **fixture-bound static curated**, analogous to case_03's `cost_records_bridge` pattern (per §15.3.2 Q2) and case_02's `material_catalog_bridge` pattern (per 002-G). The selection input is **authored at design time**, **frozen at fixture-freeze time**, and **consumed verbatim at execution time**. There is no "TASK-020 catalog service"; there is no "TASK-020 catalog database". There is only a `cost_records_bridge` block on the case_02 fixture, authored by Slice A and consumed by Slice B.

---

## §20.5 Expected Output Contract (binding, contract-frozen)

### §20.5.1 Status classification (per field, case_02 only)

Every expected_output field for case_02 is classified into exactly one of the following five states. The classification is the **single source of truth** for what may be written into the fixture by any future round.

| State | Definition | Authoritative write timing | Invention allowed? |
|---|---|---|---|
| `EXISTING_FROZEN` | Field is already present in the case_02 fixture; central value is fixed; tolerance is fixed. | Already written (001 / 002-F / 002-G). No re-write permitted. | NO (frozen) |
| `REQUIRED_MISSING` | Field is required by §20.5.2 / §17.2 but the central value is not yet present in the case_02 fixture. | Slice C (after Slice B's production-chain execution). | NO (only derived from production chain) |
| `DERIVED_VIA_CHAIN` | Field's value MUST be derived from a real production-chain run on the same fixture input, reproducibly, on a clean checkout. | Slice C (only). | NO (only via chain output) |
| `DEFERRED` | Field is required by §20.5.2 but the underlying algorithm is NOT yet contract-frozen (e.g. discount / salvage). | TASK-020+ future round. | NO (this contract) |
| `PROHIBITED_MANUAL` | Field is required by §20.5.2 but is FORBIDDEN from manual invention under any circumstance; may only be authored by §20.5.3 (chain capture). | Slice C (only). | NO (strict) |

### §20.5.2 Field-by-field contract (case_02 only; case_01 / case_03 untouched)

The following table enumerates every expected_output field that §20 contractually addresses. Fields already at `EXISTING_FROZEN` are listed for completeness; the table does NOT re-author them. Fields at `REQUIRED_MISSING` / `DERIVED_VIA_CHAIN` / `DEFERRED` / `PROHIBITED_MANUAL` are the future Slice targets.

| Field path | State | Authority | Derivation source | Write timing | Assertion purpose | Currently missing? |
|---|---|---|---|---|---|---|
| `expected_output.mass_kg.shell_mass_kg` | `EXISTING_FROZEN` | 002-G frozen | case_01 geometry × SS304 8000 kg/m^3 (002-G derivation) | already written | Regression baseline for mass_kg | NO |
| `expected_output.mass_kg.tube_mass_kg` | `EXISTING_FROZEN` | 002-G frozen | same | already written | Regression baseline for mass_kg | NO |
| `expected_output.mass_kg.total_mass_kg` | `EXISTING_FROZEN` | 002-G frozen | same | already written | Regression baseline for mass_kg | NO |
| `expected_output.mass_kg.fluid_mass_kg` | `EXISTING_FROZEN` (DEFERRED status marker) | 002-F baseline; 002-G DEFER | 002-F baseline (1.05); future real fluid-volume × fluid-density chain | already written (value); produced_field status DEFERRED | Marker-only; not a current production produced_field | NO (value) |
| `expected_output.preliminary_mechanical_check.status` | `EXISTING_FROZEN` | 001 frozen | SS304 allowable_stress_mpa_at_design_temperature = 137.0 (002-F bridge) | already written | Categorical pass / fail | NO |
| `expected_output.selected_material_ids.shell_material_id` | `EXISTING_FROZEN` | 002-F frozen | descriptive string from 002-F bridge | already written | Audit / description only (per 002-F) | NO |
| `expected_output.selected_material_ids.tube_material_id` | `EXISTING_FROZEN` | 002-F frozen | descriptive string from 002-F bridge | already written | Audit / description only (per 002-F) | NO |
| `expected_output.cost_components_C0_C1.cost_components.C0_material_minor_units` | `REQUIRED_MISSING` | §20 / §17.2 G1 | Real production chain on case_02 fixture (per §20.6) | Slice C | CAPEX C0 material value | **YES** |
| `expected_output.cost_components_C0_C1.cost_components.C0_labor_minor_units` | `REQUIRED_MISSING` | §20 / §17.2 G1 | Real production chain on case_02 fixture | Slice C | CAPEX C0 labor value | **YES** |
| `expected_output.cost_components_C0_C1.cost_components.C1_total_minor_units` | `REQUIRED_MISSING` | §20 / §17.2 G1 | Real production chain on case_02 fixture | Slice C | CAPEX C1 total value | **YES** |
| `expected_output.cost_components_C0_C1.currency_ISO_4217` | `REQUIRED_MISSING` | §20 | Real production chain on case_02 fixture | Slice C | Currency code | **YES** |
| `expected_output.cost_components_C0_C1.cost_components.C0_material.component_breakdown[]` | `REQUIRED_MISSING` | §17.2 G1 | Real production chain on case_02 fixture | Slice C | C0 material component breakdown | **YES** |
| `expected_output.cost_components_C0_C1.cost_components.C0_labor.component_breakdown[]` | `REQUIRED_MISSING` | §17.2 G1 | Real production chain on case_02 fixture | Slice C | C0 labor component breakdown | **YES** |
| `expected_output.cost_components_C0_C1.cost_components.C1_total.component_breakdown[]` | `REQUIRED_MISSING` | §17.2 G2 | Real production chain on case_02 fixture | Slice C | C1 total component breakdown | **YES** |
| `expected_output.life_cycle_energy_envelope.P_intake_kW` | `REQUIRED_MISSING` | §17.2 G3 | Real production chain on case_02 fixture | Slice C | Life-cycle intake power | **YES** |
| `expected_output.life_cycle_energy_envelope.P_total_kW` | `REQUIRED_MISSING` | §17.2 G4 | Real production chain on case_02 fixture | Slice C | Life-cycle total power | **YES** |
| `expected_output.life_cycle_energy_envelope.P_cooling_kW` | `REQUIRED_MISSING` | §17.2 G5 | Real production chain on case_02 fixture | Slice C | Life-cycle cooling power | **YES** |
| `expected_output.life_cycle_energy_envelope.P_loop_kW` | `REQUIRED_MISSING` | §17.2 G6 | Real production chain on case_02 fixture | Slice C | Life-cycle loop power | **YES** |
| `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.annual_operating_hours` | `REQUIRED_MISSING` | §20 | Real production chain on case_02 fixture | Slice C | Hours per year | **YES** |
| `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.design_life_years` | `REQUIRED_MISSING` | §20 | Real production chain on case_02 fixture | Slice C | Design life in years | **YES** |
| `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.annual_energy_MJ` | `REQUIRED_MISSING` | §20 | Real production chain on case_02 fixture | Slice C | Annual energy MJ | **YES** |
| `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.total_lifecycle_energy_MJ` | `REQUIRED_MISSING` | §20 | Real production chain on case_02 fixture | Slice C | Total lifecycle energy MJ | **YES** |
| `expected_output.life_cycle_energy_envelope.blocker_codes` | `REQUIRED_MISSING` | §20 | Real production chain on case_02 fixture | Slice C | Per-field blocker codes (e.g. `P_intake_kW` not yet derivable) | **YES** |
| `expected_output.selected_cost_model.selected_model_id` | `REQUIRED_MISSING` | §20 | Real production chain on case_02 fixture | Slice C | Selected cost-model identifier | **YES** |
| `expected_output.selected_cost_model.selection_blockers[]` | `REQUIRED_MISSING` | §20 | Real production chain on case_02 fixture | Slice C | Selection blocker list | **YES** |
| `expected_output.discounted_total_minor_units` | `DEFERRED` | TASK-018 §5.3 / §20.4.2 | Discount formula not yet contract-frozen | TASK-020+ future round | Discounted total (TASK-020+) | **YES** (and stays missing) |
| `expected_output.salvage_minor_units` | `DEFERRED` | TASK-018 §5.3.2 / §20.4.2 | Salvage formula not yet contract-frozen | TASK-020+ future round | Salvage value (TASK-020+) | **YES** (and stays missing) |
| `expected_output.unspecified_blocker.*` | `EXISTING_FROZEN` (case_03 only; case_02 may mirror) | case_03 / §20 | n/a in §20 | n/a | Audit marker for unknown blockers | n/a (case_02 may add in Slice C if chain reports unspecified blockers) |
| `expected_output.slice3a_blocked_field_paths.*` | `EXISTING_FROZEN` (case_02) | 002-G frozen | n/a | already written (case_02) | Slice-3A / Slice-3B field path status markers | NO (case_02) |
| `expected_output.provenance.*` (record provenance / selection trace) | `REQUIRED_MISSING` | §20.4.1 / Slice A | Slice A: explicit `provenance_amendment_id` per record | Slice A + Slice C | Per-record traceability | **YES** (block until Slice A) |

**Reading the table**:
- Rows marked "Currently missing = **YES**" are gated on Slice C. None of them may be authored by §20 itself.
- Rows marked "Currently missing = NO" are already present and frozen; do NOT modify.
- Rows in `DEFERRED` state are explicitly out of scope for §20; do NOT author them.

### §20.5.3 Anti-invention discipline (binding)

Per §17.7 item 2 and §20.10, the following is the **only** allowed write sequence for any `REQUIRED_MISSING` / `DERIVED_VIA_CHAIN` / `PROHIBITED_MANUAL` field:

1. Run the real production chain on the case_02 fixture input.
2. Capture the deterministic output.
3. Write the captured value into the `expected_output` field.
4. Commit the fixture change.

**Reverse order is forbidden** (write-then-verify). **Hand-calculation is forbidden**. **Copy from a documentation example is forbidden**. **Use of a mocked production output as fixture authority is forbidden**. **Modification of `expected_output` before the production output exists is forbidden**.

The "deterministic" qualifier in step 1 means: the production chain run MUST be reproducible on a clean checkout given the same fixture input. If the chain output is non-deterministic (e.g. time-of-day, random seed, env-var dependency), the run MUST be reported as a non-determinism discovery and the field MUST remain `REQUIRED_MISSING` until the non-determinism is resolved.

---

## §20.6 Fixture Derivation Protocol (binding, contract-frozen)

### §20.6.1 The only allowed derivation sequence (binding)

Any future round that wishes to populate a `REQUIRED_MISSING` / `DERIVED_VIA_CHAIN` / `PROHIBITED_MANUAL` expected_output field on case_02 MUST follow this exact sequence, in this exact order. Skipping any step or reordering any step is a §20.10 violation.

1. **Prepare authorized fixture inputs**: confirm the case_02 fixture has the required `input.cost_records_bridge` (Slice A), `input.cost_model_selection` (Slice A), and any other Slice A–authored input sub-blocks. If any required input is missing, STOP and return to Slice A — do NOT proceed.
2. **Execute the real production chain**: run the production chain on the case_02 fixture input. The chain MUST be the case_02 selection / cost-stack production chain (per the contract pattern in §15.3.2 Q2 and §20.4). It MUST NOT be a mock, a stub, a hand-rolled script, or a partial re-implementation.
3. **Capture actual deterministic output**: record the chain's output as a structured value. Record the chain invocation timestamp, the input snapshot, and the chain version (commit SHA) for traceability.
4. **Verify internal reconciliation**: confirm the captured output is internally consistent (e.g. C0_material + C0_labor = C1_total within tolerance; annual_energy_MJ × design_life_years ≈ total_lifecycle_energy_MJ; selected_model_id corresponds to the actual selection logic; selection_blockers list is non-empty iff the chain actually reported blockers).
5. **Write captured values into `expected_output`**: for each captured field, write the value into the case_02 fixture. Add or update the `slice3a_blocked_field_paths` markers per the existing pattern (case_03 is the reference; case_02 mirrors it).
6. **Add or update assertions**: add focused assertions that bind the new `expected_output` fields to the chain's actual output (i.e. a `tests/.../test_case_02_cost_stack.py::test_expected_output_matches_chain_output` style assertion). DO NOT add assertions that bind `expected_output` to hand-calculated values.
7. **Re-run focused tests**: run the test suite. Confirm that (a) the case_02 chain still reports `WIRED_VIA_CHAIN_FULL` (or the appropriate partial status), (b) the new assertions pass, (c) no existing test (especially the hard-coded `test_expected_output_unchanged_across_adapter_runs`) regresses.
8. **Commit fixture and test changes separately from production changes**: the fixture change and the test change are committed in one commit; any production change (if Slice B is in flight) is in a separate commit. The two commits reference each other in the commit message body.

### §20.6.2 Explicitly forbidden (binding)

The following are forbidden at every step of §20.6.1, regardless of author intent or round authorization:

- **Reverse-engineering expected values from desired assertions**: writing a `test_case_02_*.py` assertion first, then writing `expected_output` to satisfy it, then claiming the chain "happens to" produce the asserted value. This is a §20.10 anti-fabrication violation.
- **Hand-calculating placeholders**: writing a number into `expected_output` that was computed by hand (e.g. "C1_total = C0_material + C0_labor") without running the production chain. This is a §20.10 anti-fabrication violation, even if the hand calculation is correct.
- **Copying values from documentation examples**: writing a number into `expected_output` that was copied from a §20 / §17 / §15 / §16 example, a PR description, an Issue body, or any other prose artifact. Examples in prose are NOT authority for `expected_output` per §20.10.
- **Using mocked production outputs as fixture authority**: writing a number into `expected_output` that was produced by a mock, a stub, a partial re-implementation, or any chain variant that is NOT the real production chain. This is a §20.10 anti-fabrication violation.
- **Modifying `expected_output` before the production output exists**: writing any number into `expected_output` when no real production chain run has been performed in the current round. This is a §20.10 anti-fabrication violation.

### §20.6.3 Determinism guarantee (binding)

The production chain output captured in step 2 of §20.6.1 MUST be deterministic with respect to the fixture input. "Deterministic" means: given the same fixture input bytes, the chain produces the same output bytes on a clean checkout, modulo the following explicitly-allowed variations:

- Floating-point rounding error (within the existing `_tolerance_metadata.json` tolerances).
- External system clock (used for `provenance.amendment_id` timestamps; not for any numeric value).
- External file system listing order (NOT used by the chain; if the chain uses file listing, it is a chain non-determinism that MUST be reported).

If the chain output varies in any other way (e.g. different `record_id` ordering, different `selected_model_id`, different `selection_blockers` set), the round MUST report the non-determinism and STOP. The field MUST remain `REQUIRED_MISSING` until the non-determinism is resolved.

---

## §20.7 Thermal and Pressure-Drop Exclusion Boundary (binding, contract-frozen)

### §20.7.1 Items NOT in scope for TASK-020 (binding)

The following are **explicitly excluded** from TASK-020. They are NOT implementation targets under §20. They are NOT future Slices A–D targets. They are NOT to be authored in any §20 implementation artifact.

- **Pressure-drop calculation** (any algorithm, any formula, any method).
- **TEMA method** (any TEMA configuration schema, TEMA tube layout, TEMA shell diameter, TEMA tube-side rating).
- **Kern method** (any Kern screening, Kern correlation, Kern formula).
- **Bell-Delaware method** (any Bell-Delaware correlation, Bell-Delaware formula).
- **Thermal rating** (any thermal-method computation, any thermal-method acceptance criteria, any thermal expansion screening).
- **Exchanger hydraulic sizing** (any hydraulic-network computation, any pump / compressor curve integration).
- **Correlation selection** (any new correlation ID, any correlation registry mutation).
- **Empirical coefficient authoring** (any new constant, any new curve fit, any new vendor data).

The above items belong to the M3 milestone per `docs/TASK_BACKLOG.md` line 59 ("TASK-020 through TASK-039 cover TEMA configuration schemas, tube layout, shell diameter, tube-side rating, Kern screening, Bell–Delaware, pressure-drop decomposition, thermal expansion screening, preliminary mechanical boundaries, materials, costing, optimization, API, report and Golden validation"). They are NOT TASK-020's responsibility; they are TASK-020+'s responsibility.

### §20.7.2 Forbidden content (binding)

§20 implementation artifacts (PRs, commits, fixture files, test files, documentation) MUST NOT contain any of the following:

- Pressure-drop formulas (C4 / TEMA / Kern / Bell-Delaware / equivalent).
- Bell-Delaware formulas.
- Kern formulas.
- TEMA formulas.
- Thermal implementation content (thermal-method computation, thermal expansion screening, thermal-method acceptance criteria).
- Empirical coefficient values (new constants, new curve fits, new vendor data).
- Correlation selection logic.
- Any code, pseudo-code, formula, or algorithm hint for any of the above.

§20.7.2 is a §20.10 anti-fabrication guard. Violation is a hard STOP. The future TASK-020+ design cards for thermal / pressure-drop are the correct place for this content.

### §20.7.3 Cross-references (binding)

The exclusion boundary in §20.7 is consistent with the TASK-019 design contract:

- §6 of TASK-019 design contract (`pressure drop remains NOT_COMPUTABLE`).
- §15.8 of TASK-019 design contract (Amendment 002-H does NOT authorize pressure-drop / thermal).
- §16.8 of TASK-019 design contract (Amendment 002-I does NOT authorize pressure-drop / thermal).
- §17.5 of TASK-019 design contract (pressure-drop / thermal-method exclusion boundary).
- `pressure_drop_excluded_from_taska_019: true` marker on `case_01_heat_balance_rating.json` / `case_02_materials_mass_mechanical.json` / `case_03_cost_lifecycle_envelope.json`.

---

## §20.8 Implementation Slices and Gates (binding, contract-frozen)

The TASK-020 implementation is split into **four slices**, each with explicit **entry conditions** and **exit conditions**. Each slice is a separate Charles-authorized round. No slice may begin until the previous slice's exit conditions are met. No slice may combine with another slice.

### §20.8.1 Slice A — Fixture / Input Authority

| Field | Value |
|---|---|
| Scope | Author the case_02 `input.cost_records_bridge` sub-block + the case_02 `input.cost_model_selection` sub-block + the case_02 `input.lifecycle_inputs` sub-block (where applicable). |
| Does NOT | Author any expected_output numeric value. Author any algorithm. Modify any production code. Modify any test. |
| Entry conditions | (1) §20 is merged into `main`. (2) §17 is merged into `main`. (3) Charles explicitly authorizes Slice A. |
| Exit conditions | (1) The case_02 fixture has `input.cost_records_bridge` (one entry per required record per §20.3.3, with all 5 attributes populated). (2) The case_02 fixture has `input.cost_model_selection` (with explicit `currency_ISO_4217`, `date_ISO_8601`, `escalation_rule_id`, `region_id`). (3) The case_02 fixture has `input.lifecycle_inputs` (with explicit `annual_operating_hours`, `design_life_years`, `discount_rate_input`, `fouling_energy_penalty_factor`, `salvage_fraction_input`). (4) `_provenance_metadata.json` is updated with Slice A provenance entries. (5) The fixture contract test (`test_expected_output_unchanged_across_adapter_runs`) still passes (no regression in the `mass_kg.fluid_mass_kg == 1.05` assertion). |
| Forbidden write | Any `expected_output.*` numeric value, any `actual_output.*` value, any production code change, any test change, any algorithm hint. |

### §20.8.2 Slice B — Production Cost-Stack Coverage

| Field | Value |
|---|---|
| Scope | Implement the case_02 cost-record selection / traversal logic (per §20.4.1) and the case_02 cost-stack production chain (per §20.3.2). |
| Does NOT | Modify `expected_output` to mask a chain error. Author any runtime catalog scan / resolver. Author any pressure-drop / thermal / discount / salvage logic. |
| Entry conditions | (1) Slice A exit conditions met. (2) Charles explicitly authorizes Slice B. |
| Exit conditions | (1) The case_02 production chain executes end-to-end on the case_02 fixture input. (2) The chain reports `WIRED_VIA_CHAIN_FULL` (or the appropriate partial status with explicit `selection_blockers` entries). (3) The chain output is deterministic per §20.6.3. (4) No production code path mutates `expected_output`. (5) The chain output is logged to `/tmp/case_02_chain_output_<commit_sha>.json` for traceability. |
| Forbidden write | Any `expected_output` mutation. Any runtime catalog scan. Any runtime resolver. Any pressure-drop / thermal / discount / salvage logic. |

### §20.8.3 Slice C — Fixture Capture

| Field | Value |
|---|---|
| Scope | Run the Slice B production chain on the case_02 fixture. Capture the deterministic output. Write the captured values into case_02 `expected_output` per §20.5.2. |
| Does NOT | Re-author the production chain. Author any value not produced by the chain. Modify the chain's output. |
| Entry conditions | (1) Slice B exit conditions met. (2) Charles explicitly authorizes Slice C. |
| Exit conditions | (1) Every `REQUIRED_MISSING` field in §20.5.2 is populated with the captured value. (2) The captured value matches the chain output byte-for-byte (no manual overwrite, no hand-calculated substitution). (3) `_provenance_metadata.json` is updated with Slice C provenance entries. (4) `_tolerance_metadata.json` is updated with the new field tolerances (preserving existing 001 / 002-F / 002-G tolerance values for the 4 mass_kg fields + preliminary_mechanical_check.status). (5) The fixture contract test still passes. |
| Forbidden write | Any value not produced by the Slice B production chain run. Any reverse-order write (assertion-first, expected_output-second). |

### §20.8.4 Slice D — Assertions and Reconciliation

| Field | Value |
|---|---|
| Scope | Add focused tests that bind `expected_output` to the Slice C captured values. Verify component sum / total consistency. Verify record provenance. Verify deterministic ordering. |
| Does NOT | Add assertions that bind `expected_output` to hand-calculated values. Re-author any existing test. |
| Entry conditions | (1) Slice C exit conditions met. (2) Charles explicitly authorizes Slice D. |
| Exit conditions | (1) New tests added under `tests/validation_report/test_case_02_cost_stack.py` (or equivalent). (2) C0_material + C0_labor = C1_total within tolerance assertion exists. (3) annual_energy_MJ × design_life_years ≈ total_lifecycle_energy_MJ within tolerance assertion exists. (4) Per-record `provenance_amendment_id` assertion exists. (5) Deterministic ordering assertion exists (e.g. record order in `selected_cost_model.selection_blockers` is stable across reruns). (6) The fixture contract test still passes. (7) All new tests pass. |
| Forbidden write | Any assertion that binds `expected_output` to hand-calculated values. Any modification to existing tests. Any pressure-drop / thermal / discount / salvage assertion. |

### §20.8.5 Inter-slice discipline (binding)

- Slices MUST be executed in order A → B → C → D. Out-of-order execution is a §20.10 anti-fabrication violation.
- Each Slice is a separate Charles-authorized round. Combining Slices is a §20.10 anti-fabrication violation.
- Each Slice's commit message MUST name the Slice (e.g. `docs(task-020): slice A — fixture authority`).
- The four Slices' commits MAY be in the same branch but MUST be separate commits with separate provenance entries.

### §20.8.6 Business Cost Source Availability Gate (binding, contract-frozen)

TASK-020 implementation requires traceable case_02 business cost Source before Slice A may begin. This subsection codifies the business-source availability gate as a hard precondition for any TASK-020 implementation slice.

**Acceptable Source types** (case_02 business cost Source, in priority order):

- approved cost catalog (TASK-013 governed; case_02-bound entries with stable `cost_record_id` and `cost_record_version`; documented `source_*` fields; `provenance_chain_hash` reproducible from canonical-JSON of `{source_record_ids, correlation_ids, case_input_field, license_class, schema_version}` per TASK-018 §7 / §10);
- supplier quotation (with quote ID, effective date, currency, region, escalation rule, validity period, vendor contact);
- contract or purchase record (with contract ID, line-item breakdown, effective date, party identification);
- formally approved internal cost baseline (with approval ID, approver chain, effective date, scope statement);
- another Charles-confirmed, traceable business Source (must be explicitly named by Charles in a separate authorization message).

**Current state** (binding, governance-only):

```
TASK020_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE
```

While this state applies, the following are ALL **explicitly forbidden**:

- Slice A is blocked.
- Slice B is blocked.
- Slice C is blocked.
- Slice D is blocked.
- fixture mutation is forbidden.
- expected_output capture is forbidden.
- production mutation is forbidden.
- cost-related test mutation is forbidden.

**Implementation authorization cannot be inferred** from:

- Issue #120 (`TASK-020: case_02 cost-stack coverage and fixture authority`) as a tracking artifact;
- the TASK-020 design contract itself (governance-only);
- any prior Slice entry condition being individually met;
- any §20.10 anti-fabrication check passing (passing anti-fabrication checks is necessary but NOT sufficient for business-source authorization).

The state `TASK020_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE` is lifted only by a future Charles-authorized round that:
1. identifies the specific case_02 business cost Source (per the 5 acceptable types above);
2. documents the Source identity, version, effective date, and authority chain;
3. explicitly states that the Source is sufficient for Slice A entry (and downstream slices);
4. updates the §20.9 register status of the relevant R-items (R2 / R9 / R10 / R11 / R22 / R23) from `REPO_SOURCE_REQUIRED` to `RESOLVED` (or to a new state) with provenance recorded in `_provenance_metadata.json`.

Until that round, **no TASK-020 implementation slice is authorized**, regardless of any other gate status.

---

## §20.9 Source-Missing Register (binding, contract-frozen)

The following table is the **formal register** of source-missing items. Each item is classified by ID, missing authority, why required, blocked downstream work, acceptable source type, anti-fabrication rule, and status. Status is one of: `SOURCE_MISSING` / `CHARLES_SOURCE_REQUIRED` / `REPO_SOURCE_REQUIRED` / `DEFERRED` / `RESOLVED`. Items with no current source MUST NOT be marked `RESOLVED`.

| ID | Missing authority | Why required | Blocked downstream work | Acceptable source type | Anti-fabrication rule | Status |
|---|---|---|---|---|---|---|
| R1 | case_02 full cost-stack source authority (6 deferred fields per §17.2) | Required by §20.5.2 (`REQUIRED_MISSING` rows) | Slice C fixture capture (cannot run chain without a contract-frozen cost-stack source) | Real production chain on case_02 fixture input (per §20.6) | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible on a clean checkout | `SOURCE_MISSING` |
| R2 | case_02 cost-record selection authority (per §20.3.2) | Required by §20.3.3 record-role mapping | Slice A (cannot author `input.cost_records_bridge` without record-role mapping) | `input.cost_records_bridge` (case-bound, frozen, audit-traceable) authored in Slice A | MUST NOT be inferred; MUST be explicitly declared per §20.3.3 (5 attributes per record) | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R3 | case_02 expected_output authority for `cost_components_C0_C1.*` | Required by §20.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R4 | case_02 expected_output authority for `life_cycle_energy_envelope.*` | Required by §20.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R5 | case_02 expected_output authority for `selected_cost_model.*` | Required by §20.5.2 | Slice C | Real production chain output (case_03 pattern reference) | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R6 | case_02 catalog traversal authority (per §20.4) | Required by §20.4.1 (in-scope) and §20.4.2 (out-of-scope) | Slice B (cannot implement selection without a traversal boundary) | `input.cost_records_bridge` traversal (case-bound, deterministic, no runtime discovery) | MUST NOT be runtime scan; MUST NOT be network lookup; MUST NOT be plugin resolution; MUST be `cost_records_bridge` array iteration only | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R7 | Discount formula / calculation authority | Required by `expected_output.discounted_total_minor_units` (case_03 pattern) | TASK-020+ future design card (NOT in §20 scope) | Future TASK-020+ design card | MUST NOT be invented under §20; MUST be a separate Charles-authorized round | `DEFERRED` |
| R8 | Salvage formula / calculation authority | Required by `expected_output.salvage_minor_units` (case_03 pattern) | TASK-020+ future design card (NOT in §20 scope) | Future TASK-020+ design card | MUST NOT be invented under §20; MUST be a separate Charles-authorized round | `DEFERRED` |
| R9 | case_02 `input.cost_records_bridge` (the sub-block itself) | Required by §20.4.1 and §20.3.2 | Slice A (cannot start Slice A without the contract-frozen sub-block shape) | Slice A authoring | MUST NOT be invented under §20; MUST be authored in Slice A | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R10 | case_02 `input.cost_model_selection` (the sub-block itself) | Required by §20.3.2 (case_03 pattern: `currency_ISO_4217`, `date_ISO_8601`, `escalation_rule_id`, `region_id`) | Slice A | Slice A authoring | MUST NOT be invented under §20; MUST be authored in Slice A | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R11 | case_02 `input.lifecycle_inputs` (the sub-block itself) | Required by §20.5.2 (`life_cycle_energy_envelope.life_cycle_energy_summary.*`) | Slice A | Slice A authoring | MUST NOT be invented under §20; MUST be authored in Slice A | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R12 | case_02 expected_output authority for `cost_components_C0_C1.cost_components.C0_material.component_breakdown[]` | Required by §17.2 G1 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R13 | case_02 expected_output authority for `cost_components_C0_C1.cost_components.C0_labor.component_breakdown[]` | Required by §17.2 G1 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R14 | case_02 expected_output authority for `cost_components_C0_C1.cost_components.C1_total.component_breakdown[]` | Required by §17.2 G2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R15 | case_02 expected_output authority for `life_cycle_energy_envelope.life_cycle_energy_summary.annual_operating_hours` | Required by §20.5.2 | Slice C | Real production chain output (case_03 pattern reference) | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R16 | case_02 expected_output authority for `life_cycle_energy_envelope.life_cycle_energy_summary.design_life_years` | Required by §20.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R17 | case_02 expected_output authority for `life_cycle_energy_envelope.life_cycle_energy_summary.annual_energy_MJ` | Required by §20.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R18 | case_02 expected_output authority for `life_cycle_energy_envelope.life_cycle_energy_summary.total_lifecycle_energy_MJ` | Required by §20.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R19 | case_02 expected_output authority for `life_cycle_energy_envelope.blocker_codes` | Required by §20.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R20 | case_02 expected_output authority for `selected_cost_model.selected_model_id` | Required by §20.5.2 | Slice C | Real production chain output (case_03 pattern reference) | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R21 | case_02 expected_output authority for `selected_cost_model.selection_blockers[]` | Required by §20.5.2 | Slice C | Real production chain output | MUST NOT be invented; MUST be derived from a real chain run; MUST be reproducible | `SOURCE_MISSING` |
| R22 | case_02 expected_output authority for `provenance.*` (record provenance / selection trace) | Required by §20.4.1 | Slice A | Slice A authoring (`provenance_amendment_id` per record) | MUST NOT be invented; MUST be a stable case-bound identifier | `REPO_SOURCE_REQUIRED` (via Slice A) |
| R23 | case_02 fixture `amendment_id` and `amendment_status` update for §20 | Required by governance sync | After §20 is merged, governance sync may update case_02 `amendment_id` to `"TASK-020-DESIGN-AMENDMENT-..."` (post-merge, separate round) | Post-§20-merge governance sync | MUST NOT be updated under §20 itself; MUST be a separate post-merge round | `REPO_SOURCE_REQUIRED` (via post-merge governance sync) |
| R24 | TASK-020 GitHub Issue | Required for Slice A / B / C / D tracking | Slice A entry condition #3 (Charles explicit authorization) | Future Charles-authorized round | MUST NOT be opened under §20 itself; MUST be opened in a separate Charles-authorized round | `CHARLES_SOURCE_REQUIRED` |
| R25 | Pressure-drop / thermal-method / TEMA / Kern / Bell-Delaware implementation authority | Excluded from §20 (per §20.7); belongs to TASK-020+ | n/a (out of §20 scope) | Future TASK-020+ design card | MUST NOT be authored under §20; MUST be a separate Charles-authorized round | `DEFERRED` |

**Status transition rule (binding)**: a register item's status MAY transition from `SOURCE_MISSING` / `REPO_SOURCE_REQUIRED` / `CHARLES_SOURCE_REQUIRED` to `RESOLVED` ONLY in the round that actually produces the missing authority. The status transition MUST be recorded in `_provenance_metadata.json` and the §20.9 register (in a future round, not this round). A `RESOLVED` item in this round's register is a §20.10 anti-fabrication violation.

**§20.9 register-level note (governance amendment, 2026-07-10)**: The R1–R25 item statuses remain unchanged in this amendment. The overall TASK-020 implementation state is blocked by unavailable business cost Source (per §20.8.6 `TASK020_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE`). Concretely:

- R24 governance tracking (the TASK-020 GitHub Issue) is now represented by **Issue #120** (`TASK-020: case_02 cost-stack coverage and fixture authority`). The Issue is a tracking / authorization artifact only. **Creating the Issue does NOT resolve the business Source blockers** identified in this round.
- No R-item becomes `RESOLVED` in this round. R1–R25 retain their existing statuses (`SOURCE_MISSING` × 14 / `REPO_SOURCE_REQUIRED` × 7 / `CHARLES_SOURCE_REQUIRED` × 1 / `DEFERRED` × 3 / `RESOLVED` × 0). The blocked state `TASK020_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE` does NOT transition any R-item to `RESOLVED`; a future Charles-authorized round with a real business cost Source is the only valid path to lift the blocked state and transition R-items (R2 / R9 / R10 / R11 / R22 / R23 in particular) to `RESOLVED`.
- The blocked state applies to the implementation slices (Slice A / B / C / D), NOT to the §20 governance amendment itself. This amendment is governance-only and does not require a business cost Source to be authored.

---

## §20.10 Non-Actions and Anti-Fabrication Guard (binding, contract-frozen)

### §20.10.1 Non-action declarations (binding)

The following declarations are **explicitly non-actions** of §20. Each is a §20.10 anti-fabrication fact that any future round (Slice A / B / C / D or any other) MUST honor.

- **§20 design document does NOT authorize implementation.** §20 is a design contract. Any implementation under §20 alone is a §20.10 violation. Implementation requires Slice A → B → C → D, each with its own Charles-authorized round.
- **A skeleton is NOT an implementation approval.** §20.8's four Slices are skeletons, not approvals. Each Slice's entry condition #3 ("Charles explicitly authorizes Slice N") is a hard gate.
- **A missing field is NOT an invitation to supply a default.** A `REQUIRED_MISSING` field in §20.5.2 stays missing until the production chain run in Slice C captures the value. No default, no placeholder, no first-valid-record, no copy from a sibling case.
- **The current fixture subset is NOT a complete catalog.** case_02 currently has mass-chain bridges (002-F / 002-G) but no cost-stack bridges. The absence of a cost-stack bridge is NOT a license to invent one under §20. The cost-stack bridge is gated on Slice A.
- **The current selector output is NOT a complete cost stack.** case_03's `CostModelSelector.select` (per §15.3.2 Q2) consumes the case_03 `cost_records_bridge` and emits a curated-subset output. That output is NOT a "complete" cost stack. The 6 §17.2 deferred fields are NOT covered by case_03's selector output.
- **The existence of `total cost` is NOT a license to claim component breakdown is authorized.** If a future round writes `expected_output.cost_components_C0_C1.cost_components.C1_total_minor_units` it MUST also write `C0_material_minor_units` and `C0_labor_minor_units` (and the component breakdowns per §17.2 G1 / G2). A total without components is a §20.10 anti-fabrication violation.
- **A documentation example is NOT `expected_output` authority.** Numbers appearing in §20 / §17 / §15 / §16 prose are examples, not authority. Authority is the production chain output captured in Slice C.
- **A test convenience is NOT business authority.** A test asserting `assert expected_output.cost_components_C0_C1.cost_components.C1_total_minor_units == 12345` does NOT make 12345 the business authority for that field. The business authority is the production chain output.

The following additional anti-fabrication rules apply to the `TASK020_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE` state (per §20.8.6) and are **explicitly forbidden** while that state is in effect:

- **No synthetic cost records.** Creating artificial cost records (whether via a hand-written loop, a generated sequence, a test fixture, a mock, or any other method) to satisfy schema or test requirements is a §20.10 anti-fabrication violation. A `cost_records_bridge` list may remain empty; it MUST NOT be populated with invented records.
- **No placeholder monetary values.** Writing `0` (or any non-real number) into `cost_value_minor_units` to satisfy schema or test requirements is a §20.10 anti-fabrication violation. The schema requires an integer; the integer MUST be the real value from a business Source. An empty list is the correct representation while the business Source is unavailable.
- **No zero values used merely to satisfy schema or tests.** A `0` in `cost_value_minor_units` is interpreted as "this catalog entry states that the cost is zero minor units", which is a positive business claim. Zero is NEVER to be used as a placeholder.
- **No random or example record IDs.** Inventing IDs such as `EXAMPLE-001`, `TEST-RECORD`, `PLACEHOLDER`, or any non-traceable identifier is a §20.10 anti-fabrication violation. Real `cost_record_id` values come from the catalog and follow a documented naming convention.
- **No copying case_03 cost records into case_02.** Case_03's `cost_records_bridge` (TASK-019-AMEND-002H-C0-MATERIAL-SS304-TUBE-V1, TASK-019-AMEND-002H-C0-LABOR-ASME-V1, TASK-019-AMEND-002H-C1-INSTALLATION-V1) is case_03-specific and bound to its `provenance_amendment_id = TASK-019-DESIGN-AMENDMENT-002-H`. Copying these records or their `cost_value` fields into case_02 would mis-attribute the source. The two cases share the bridge PATTERN, not the bridge CONTENT.
- **No copying case_03 monetary values into case_02.** Even if a case_02 record role is similar to a case_03 record role (e.g. both have a `C0_material` record), the `cost_value_minor_units` MUST come from a case_02-specific business Source. case_03's `cost_value_minor_units` are 412000 / 188000 / 0 (per `case_03_cost_lifecycle_envelope.json`); none of these are valid for case_02.
- **No deriving component costs by reversing a target total.** Computing `C0_material` or `C0_labor` from a guessed `C1_total` (or vice versa) is a §20.10 anti-fabrication violation. The reverse derivation is a hidden source-fabrication technique that produces numbers without a corresponding business Source.
- **No deriving costs from equipment mass without an authorized cost Source.** Multiplying `case_02.expected_output.mass_kg.shell_mass_kg` (1.18) by a guessed USD/kg is a §20.10 anti-fabrication violation. Equipment mass is a derived quantity, not a unit price.
- **No filling required fields solely to make tests pass.** A test that asserts `cost_records_bridge` is non-empty MUST NOT be satisfied by inventing a record. The test itself is the wrong test if it requires invented data; the test MUST be updated to assert the empty state (per §20.10.2 #2 anti-fabrication check).
- **No treating `null` / empty string / empty list as a completed business Source.** A `null` value in a required field is an explicit "not yet sourced" marker, not a value. An empty list (`[]`) is an explicit "no records yet" marker, not a completed `cost_records_bridge`. The blocked state `TASK020_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE` is the correct representation of these empty structures while the business Source is unavailable.

**Schema existence is not business-value authority.** A field being required in the §20.5.2 contract (or in any subsequent §20.x contract update) does NOT authorize invention of its value. The contract declares the SHAPE of the field; the business Source provides the VALUE. The two are independent.

**A field being required does not authorize invention of its value.** The required status is a contract declaration; the value is a separate Charles-supplied or production-chain-derived input. Until the value is supplied, the field's required status means "must be filled when a Source is available", NOT "must be filled now with any number".

### §20.10.2 Anti-fabrication checks (binding)

The following checks MUST be performed by any future round that authors an artifact in the TASK-020 lineage (Slice A / B / C / D, governance sync, fixture update, test update, production change):

1. **No invented numeric expected values**: any number in `expected_output` MUST be traceable to a real production chain run. The chain run MUST be in the same round's commit log. The chain invocation timestamp + commit SHA MUST be in `_provenance_metadata.json`.
2. **No TODO-as-authorized-scope**: any `TODO` / `FIXME` / `placeholder` / `to-be-determined` in a Slice A / B / C / D commit MUST be flagged as a §20.10 violation. Slice A / B / C / D commits MUST be either complete or explicitly aborted.
3. **No pressure-drop / Bell-Delaware / Kern / TEMA / thermal implementation content**: per §20.7. Any such content in a TASK-020 lineage commit is a hard STOP.
4. **No runtime catalog scan authorization**: per §20.4.2. Any code that performs a runtime catalog scan in a TASK-020 lineage commit is a hard STOP.
5. **No production implementation claims**: §20 lineage commits MUST NOT claim that any production capability is "implemented" or "available" beyond the existing TASK-019 frozen baseline. Slice B is a future round, not this round.
6. **No cross-Slice scope creep**: a Slice A commit MUST NOT include Slice B / C / D content. A Slice C commit MUST NOT include Slice A / B / D content. The four Slices are separate commits.
7. **No fixture contract test regression**: the hard-coded `test_expected_output_unchanged_across_adapter_runs` (asserting `fixture_02["expected_output"]["mass_kg"]["fluid_mass_kg"] == 1.05`) MUST NOT regress under any TASK-020 lineage change.

### §20.10.3 STOP conditions (binding)

The following conditions are hard STOPS. Any TASK-020 lineage round that encounters any of these MUST stop immediately and report the violation to Charles. The violation is binding and may not be silently fixed.

- A `RESOLVED` status in the §20.9 register that was authored in the same round (i.e. the round both added the missing authority and marked the item `RESOLVED`).
- A `expected_output` numeric value in a TASK-020 lineage commit that is NOT traceable to a real production chain run.
- A pressure-drop / Bell-Delaware / Kern / TEMA / thermal implementation in a TASK-020 lineage commit.
- A runtime catalog scan / resolver in a TASK-020 lineage commit.
- A combined-slice commit (e.g. one commit that includes both Slice A and Slice B content).
- A TASK-020 lineage commit that does not name the Slice (A / B / C / D) in the commit message subject.

---

## §20 Change Log (binding)

| Date | Change | Author |
|---|---|---|
| 2026-07-10 | Initial §20 design contract authored (this file). All 10 sections (§20.1 – §20.10) created from TASK-020 preparation report synthesis + TASK-019 frozen design cross-reference. Status: DESIGN FROZEN / MERGE-NOT-AUTHORIZED. | Charles-authorized design-only round |
| 2026-07-10 | **Business-Source Availability Gate amendment.** Recorded `TASK020_BLOCKED_BUSINESS_COST_DATA_UNAVAILABLE`; added the §20.8.6 business-source availability gate and the §20.10.1 anti-fabrication boundary (no synthetic records / no placeholder monetary values / no zero placeholders / no random IDs / no case_03 record copying / no reverse-derivation / no mass-based price guessing / no test-driven invention / no treating `null` / `[]` / `""` as completed Source); added the §20.9 register-level note (R1–R25 statuses unchanged; Issue #120 is tracking only; blocked state does not transition R-items to `RESOLVED`); no R-item status change; no implementation authorization. **Authority**: Charles confirmation that no traceable case_02 business cost data is currently available. **Scope**: governance-only. **Implementation**: NOT AUTHORIZED. | Charles-authorized governance-only round (this amendment) |

---

**Final declaration**:

> **TASK-020 DESIGN CONTRACT AUTHORED LOCALLY.**
> **IMPLEMENTATION NOT AUTHORIZED.**
> **FIXTURE MUTATION NOT AUTHORIZED.**
> **EXPECTED OUTPUT VALUES NOT INVENTED.**
> **NO REMOTE MUTATION PERFORMED.**

This document is a **design contract** (governance-only). It does not authorize production implementation, fixture mutation, test mutation, or any algorithm authoring. The implementation is gated on Slices A → B → C → D per §20.8, each requiring its own Charles-authorized round.
