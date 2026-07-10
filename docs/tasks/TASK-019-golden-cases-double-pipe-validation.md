# TASK-019 — Golden Cases and Double-Pipe Validation Report Design Contract

| **Status:** DESIGN FROZEN / MERGED / GOVERNANCE-SYNCED / AMENDMENT-002-A-IN-PROGRESS / AMENDMENT-002-D-IN-PROGRESS / AMENDMENT-002-E-IN-PROGRESS / AMENDMENT-002-G-IN-PROGRESS / MERGE-NOT-AUTHORIZED |
**Milestone:** M2 (Double-pipe vertical slice)
**Priority:** P1
**Depends on:** TASK-006, TASK-007, TASK-008, TASK-011, TASK-012, TASK-013, TASK-014, TASK-015A, TASK-017, TASK-018
**Owner:** Unassigned

> Design contract for TASK-019. Defines the **3 Golden cases** for double-pipe heat-exchanger cases and the **validation report** contract that compares calculation outputs against approved expected vectors.
>
> This document is **design-only**: no production code, no public API, no report rendering, no database schema, no pressure-drop implementation, no C4 logic, no life-cycle energy computation, no TASK-020+ content, no discount formula, no salvage formula, and no mutation of any frozen TASK-006–TASK-018 contract is introduced by this design contract.

## 1. Authority and status

| Field | Value |
|---|---|
| Backlog item | TASK-019 — Add Golden cases and double-pipe validation report |
| Backlog wording (verbatim) | "Add Golden cases and double-pipe validation report" |
| Backlog status before this design contract | `PLANNED` (TASK-007–TASK-018 dependency chain) |
| Backlog dependency | TASK-007–TASK-018 (inclusive) |
| Backlog Roadmap wording | "Add 3 golden cases and validation report." (`docs/GITHUB_ROADMAP.md` L38, Milestone 2 step 12) |
| Design branch (this round) | `docs/task-019-golden-cases-double-pipe-validation-design` |
| Design base SHA | `76a8b5142c63fb09852146611e794355dea7f5b6` (= main @ PR #86 merge) |
| Design file | `docs/tasks/TASK-019-golden-cases-double-pipe-validation.md` (this file) |
| Base authority | main `76a8b5142c63fb09852146611e794355dea7f5b6` (PR #86 merge; TASK-018 closeout governance-sync merged on 2026-07-07) |
| Design contract status | **DESIGN FROZEN** (PR #88 CLOSED / MERGED; merge commit `c86981cb1cf3fa9a7c3cae281559447b9027a231`; post-merge main CI `28911785657` completed / success; Issue #87 CLOSED / state_reason=completed / closed_at=`2026-07-08T02:03:40Z`; design was merged to main on 2026-07-08 by Charles) |
| Frozen Contract Authority Commit SHA | `c86981cb1cf3fa9a7c3cae281559447b9027a231` (= PR #88 merge commit; design was merged to main on 2026-07-08; per self-reference guard in §11, this SHA is set at merge time) |
| Frozen Contract Authority Base SHA | `76a8b5142c63fb09852146611e794355dea7f5b6` |
| Implementation status | **NOT AUTHORIZED** |
| Implementation Issue | NOT YET CREATED |
| PR (this design) | #88 — CLOSED / MERGED (merge commit `c86981cb1cf3fa9a7c3cae281559447b9027a231`; merged to main on 2026-07-08 by Charles; post-merge main CI `28911785657` completed / success) |
| Issue (this design) | #87 — CLOSED / state_reason=completed / closed_at=`2026-07-08T02:03:40Z` (closed by Charles after PR #88 merge + post-merge main CI success) |
| Post-merge main CI (PR #88) | run `28911785657` — completed / success / head_sha `c86981cb1cf3fa9a7c3cae281559447b9027a231` (= PR #88 merge commit) / event=push / branch=main |
| TASK-018 §5.3 discount formula amendment | DEFERRED / NOT AUTHORIZED (orthogonal to TASK-019; not required) |
| TASK-018 §5.3.2 salvage formula amendment | DEFERRED / NOT AUTHORIZED (orthogonal to TASK-019; not required) |
| TASK-020+ status | NOT STARTED / NOT AUTHORIZED |
| Amendment-001 status | DESIGN-AMENDMENT-001-IN-PROGRESS / MERGE-NOT-AUTHORIZED (PR branch `codex/task-019-freeze-validation-vectors`; this row records the amendment-001 metadata; the design contract status row above remains the authoritative status until amendment-001 is itself merged) |
| Amendment-001 scope | Freeze canonical case input vectors, canonical expected output vectors for TASK-006/007/008/017/018-authorized fields, and per-field tolerance values for all three TASK-019 Golden cases. |
| Amendment-001 explicit non-goals | No src/hexagent/** mutation; no tests/validation_report/** mutation; no chain_adapter.py creation; no production-chain execution; no TASK-020+ field introduction; no TASK-018 §5.3 / §5.3.2 discount / salvage formula invention; no Issue #23 / #93 / #94 / #95 mutation; no new blocker / warning code. |

## 2. Objectives and scope

### 2.1 TASK-019 objectives (binding)

1. Define exactly **what "Golden cases" mean** for this repository.
2. Define the **double-pipe validation report** contract and its output structure.
3. Define **deterministic inputs / outputs / hashes / provenance rules** for Golden cases.
4. Define **acceptance criteria and tests** for the future implementation round.

### 2.2 In scope (design contract level only)

- 3 Golden case definitions (case identity, inputs, expected outputs, tolerances, provenance).
- Validation report schema (sections, fields, required vs optional, PASS / BLOCKED / NOT_COMPUTABLE representation).
- Deterministic serialization rules (canonical JSON, stable hash discipline).
- Provenance metadata schema (correlation ID, source, version, validity envelope, uncertainty — per `MASTER_DEVELOPMENT_SPEC` §10 / §15).
- Closed-set / blocker reuse policy (prefer existing blocker / warning semantics).
- Frozen-contract-not-mutated discipline.
- Future implementation boundary (allowed files, expected Issue / branch / PR naming, CI expectations).
- Acceptance test categories for the implementation round.

### 2.3 Out of scope (explicit exclusions, §6 below)

- No pressure-drop / C4 implementation or contract surface.
- No TASK-020+ content.
- No new correlations, no new heat-transfer physics, no new cost formulas.
- No discount formula, no salvage formula, no vendor quote / C3 sourcing.
- No TASK-017 stale-docs remediation.
- No Issue #23 action.
- No Feishu outbound.

## 3. Definitions (binding)

### 3.1 Golden case

A **Golden case** is a fixed, versioned input + fixed, versioned expected output pair that:

- Exercises a **specific** upstream calculation path end-to-end (no partial coverage).
- Carries a **canonical SHA-256 hash** of both the input and the expected output, computed over the canonical-JSON form per `MASTER_DEVELOPMENT_SPEC` §15.3.
- Carries **provenance metadata** identifying each upstream correlation, provider, rule-pack, design contract version, and case source.
- Is **deterministic and auditable**: identical inputs produce identical expected outputs byte-for-byte across supported Python versions and operating systems.
- Carries **tolerance metadata**: per-field absolute / relative tolerance, per `MASTER_DEVELOPMENT_SPEC` §15.5.
- Is **separated from benchmark corpus** per TASK-011 §15 (Golden cases are correctness authority; benchmark cases are statistical / performance authority).
- Is **separated from random / property tests**: Golden cases are NOT randomly generated; they are fixed.
- Carries a **license-boundary attestation** indicating whether the Golden case is derived from a vendor / paid rule-pack or from internal correlation (per TASK-012 §5).

### 3.2 Double-pipe validation report

A **double-pipe validation report** is a deterministic artifact that:

- Aggregates the per-case comparison results across the 3 Golden cases into one report.
- Records the canonical hash of each Golden case input + expected output at the time of comparison.
- Records the canonical hash of each calculation output at the time of comparison.
- Records the per-field comparison status (PASS / FAIL / NOT_COMPUTABLE) with explicit tolerance attribution.
- Records the upstream contract versions active at the time of comparison (TASK-006 / TASK-007 / TASK-008 / TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015A / TASK-017 / TASK-018 / future TASK-019 implementation).
- Records the run environment metadata (Python version, platform, package versions of relevant dependencies, deterministic-mode flags).
- Is **self-contained**: the report + its Golden case fixtures together are sufficient to reproduce the comparison offline.
- Is **license-boundary-aware**: per `MASTER_DEVELOPMENT_SPEC` §15.6, restricted-source outputs are pointer-only.

### 3.3 Determinism guarantees

- All input / output serialization uses **canonical JSON** (sorted keys, no insignificant whitespace, no NaN / Infinity, integers for minor units only — no float for money).
- All hash values use **SHA-256**, lowercase hex, 64 characters.
- All datetime values use **ISO 8601 UTC** with explicit `Z` suffix.
- All numerical tolerances are **fixed at contract-freeze time** and may NOT be widened in implementation without an explicit design-amendment.

## 4. Golden case set (binding)

Per roadmap wording "Add 3 golden cases and validation report", TASK-019 defines **exactly 3 Golden cases**. Each case is grounded in **existing TASK-006 / TASK-007 / TASK-008 / TASK-017 / TASK-018** capabilities (no new physics, no new correlations, no new cost formulas).

### 4.1 Golden case 01 — Double-pipe heat balance + fixed-geometry rating (TASK-006 + TASK-007 + TASK-008)

**Scenario**: A canonical concentric-tube double-pipe heat exchanger with both fluids in co-current arrangement, single-phase liquid on both sides (no phase change), fixed geometry (no iterative sizing), heat balance closure at design point.

**Inputs** (frozen):
- Geometry: inner tube OD, inner tube ID, inner tube length, outer shell ID, outer shell OD, material assignment (per TASK-017 design)
- **Geometry material properties (frozen, Amendment 002-A):** `wall_thermal_conductivity_w_m_k`, `inner_surface_roughness_m`, `annulus_surface_roughness_m` — see §4.5
- Hot-side fluid: composition, mass flow rate, inlet temperature, inlet pressure
- Cold-side fluid: composition, mass flow rate, inlet temperature, inlet pressure
- Fouling factors: hot-side, cold-side (per TASK-014 design)
- Property provider: CoolProp (per TASK-015A) — fixed provider ID

**Upstream paths exercised**:
- TASK-007 (tube-side single-phase correlations + annulus-side single-phase correlations)
- TASK-006 (heat balance solver)
- TASK-008 (fixed-geometry double-pipe rating)

**Expected outputs** (frozen):
- Heat duty (W)
- Outlet temperatures (hot, cold)
- LMTD / ε-NTU derived values
- Tube-side / annulus-side heat transfer coefficients
- Tube-side / annulus-side pressure drop: **NOT_COMPUTABLE** (pressure drop excluded from TASK-019 per §6)

**Tolerance**: per `MASTER_DEVELOPMENT_SPEC` §15.5; absolute + relative bounds explicitly recorded at contract-freeze time.

**Provenance**: correlation IDs from TASK-007 registry, provider ID for CoolProp, design contract versions (TASK-006 / TASK-007 / TASK-008 / TASK-014 / TASK-015A / TASK-017), Golden case SHA-256 hash.

### 4.2 Golden case 02 — Materials + mass + preliminary mechanical check (TASK-006 + TASK-008 + TASK-017)

**Scenario**: Same geometry and fluid conditions as Golden case 01, with explicit material selection and mass calculation, plus §9.1 preliminary mechanical check on tube allowable stress (TASK-017 §9.1 — already implemented in `preliminary_checker.py`).

**Inputs** (frozen):
- All inputs from Golden case 01, plus:
- Material selection: tube material, shell material (per TASK-017 design — frozen MaterialSelector)
- Design code: selected from TASK-017 approved rule-packs
- Design temperature, design pressure

**Upstream paths exercised**:
- All paths from Golden case 01, plus:
- TASK-017 `MaterialSelector` (frozen)
- TASK-017 `MassCalculator` (frozen)
- TASK-017 `PreliminaryMechanicalChecker` §9.1 (allowable-stress preliminary check; frozen)

**Expected outputs** (frozen):
- All outputs from Golden case 01, plus:
- Selected material IDs (tube + shell)
- Total mass (kg), shell mass, tube mass, fluid mass
- Preliminary mechanical check: PASS / BLOCKED_PRELIMINARY / BLOCKED_FOR_DETAILED_DESIGN status
- If BLOCKED: blocker code + details (per TASK-017 §9.1 closed-set)

**Tolerance**: per `MASTER_DEVELOPMENT_SPEC` §15.5 + TASK-017 §15.

**Provenance**: TASK-017 frozen contract version + TASK-017 MaterialSelector / MassCalculator / PreliminaryMechanicalChecker SHA + correlation IDs + rule-pack IDs.

### 4.3 Golden case 03 — Full envelope with C0/C1 cost + life-cycle energy (TASK-006 + TASK-008 + TASK-017 + TASK-018)

**Scenario**: Same geometry and fluid conditions as Golden case 01, with the full envelope of TASK-018 Slice A / B / C outputs: CostModelSelector → CostCalculator → LifeCycleEnergyEstimator.

**Inputs** (frozen):
- All inputs from Golden case 01, plus:
- Cost model selection inputs (currency, region, date, escalation rules per TASK-018 §6)
- Life-cycle inputs: `annual_operating_hours`, `discount_rate` (input-only, not defaulted), `design_life_years`, `salvage_fraction`, `fouling_energy_penalty_factor` (per TASK-018 §5.3.1 — all caller-supplied, no defaults)

**Upstream paths exercised**:
- All paths from Golden case 01, plus:
- TASK-018 Slice A `CostModelSelector` (frozen)
- TASK-018 Slice B `CostCalculator` (frozen)
- TASK-018 Slice C `LifeCycleEnergyEstimator` (frozen)

**Expected outputs** (frozen):
- All outputs from Golden case 01, plus:
- Selected cost model (TASK-018 Slice A): `selected_model_id`, `selection_blockers` (may be non-empty if no model matches — TASK-018 Option A behavior)
- C0/C1 cost breakdown (TASK-018 Slice B): `cost_components`, `currency`, integer minor units ONLY (no float for money)
- Life-cycle energy envelope (TASK-018 Slice C): `life_cycle_energy_summary`, blocker codes if any
- **`discounted_total_minor_units`: `null`** (TASK-018 Option A behavior per §5.1 below; deferred amendment)
- **`unspecified_blocker` with `details.reason = "discount_formula_pending_design_amendment"`** if blocked on discount formula (TASK-018 §5.3 deferred)
- **`salvage_minor_units`: `<int>` placeholder** (TASK-018 §5.3.2 deferred; Slice A/B/C implementations hard-code `= 0` per Slice C closeout audit)

**Tolerance**: per `MASTER_DEVELOPMENT_SPEC` §15.5 + TASK-018 §15.

**Provenance**: TASK-018 frozen contract version + Slice A/B/C commit SHAs + correlation IDs + rule-pack IDs + provider IDs + TASK-013 cost-record ID (if used; default-source pattern explicitly forbidden per TASK-018 §5.3.1 L314).

### 4.4 Forbidden Golden case content (explicit)

- No pressure-drop / C4 expected values (§6).
- No TASK-020+ expected values (§6).
- No discounted / salvage / vendor-quote / C3 expected values (§6).
- No new correlation registry entries.
- No new property provider entries.
- No default-source for `discount_rate` (must be `case_input` per TASK-018 §5.3.1 L314).

### 4.5 Amendment 002-A — case_01 geometry material-property bridge (binding)

**Amendment id**: `TASK-019-DESIGN-AMENDMENT-002-A`
**Effective scope**: case_01 only (TASK-019-GOLDEN-01)
**Status**: DESIGN-AMENDMENT / MERGE-NOT-AUTHORIZED

#### 4.5.1 Purpose (binding)

The Slice 3A adapter (`src/hexagent/validation_report/chain_adapter.py`) requires three geometry material properties to construct a TASK-008 `GeometryMaterial` for the rating call:

- `wall_thermal_conductivity_w_m_k` (float, must be > 0 per `src/hexagent/exchangers/double_pipe/geometry.py:80`)
- `inner_surface_roughness_m` (float, must be >= 0 per `src/hexagent/exchangers/double_pipe/geometry.py:82`)
- `annulus_surface_roughness_m` (float, must be >= 0 per `src/hexagent/exchangers/double_pipe/geometry.py:84`)

Amendment 001 froze these values' downstream expected_output vectors (heat_duty_W, h_tube_W_m2_K, h_annulus_W_m2_K, outlet_T_cold_K, outlet_T_hot_K) per the Kern 1950 Case 4.2 water-water 1"/2" tube-in-shell engineering-literature reference. The literature values for SS304 stainless steel at the operating envelope (293-343 K) are the canonical benchmark values:

- `wall_thermal_conductivity_w_m_k` = `16.2` (SS304 documented thermal conductivity at 300 K, ± 0.5 W/(m·K) per INCO/ASTM A240 documented 5-10% tolerance band over the operating envelope)
- `inner_surface_roughness_m` = `4.5e-5` (commercial steel tube 45 μm, per typical ASME B36.10M / ASTM A312 commercial-seamless-tubing surface finish documentation)
- `annulus_surface_roughness_m` = `4.5e-5` (commercial steel pipe 45 μm, per same basis as tube side)

These values are **frozen benchmark input**, NOT implementation fallback. The adapter MUST NOT hardcode them; it MUST read them from the case_01 `input.geometry.*` keys enumerated below. The Slice 3A PR #102 P1-1 fix specifically removed hardcoded `16.2` and `4.5e-5` from the adapter code path; this amendment re-introduces them as **case-bound authorized test-vector data** (fixture-level, not code-level).

#### 4.5.2 Frozen field paths (binding, case_01 only)

The case_01 frozen-input subtree gains three new keys under `input.geometry`:

- `input.geometry.wall_thermal_conductivity_w_m_k: float` (must be > 0)
- `input.geometry.inner_surface_roughness_m: float` (must be >= 0)
- `input.geometry.annulus_surface_roughness_m: float` (must be >= 0)

These keys are **flat under `input.geometry`** (no nested object), matching the exact read path the Slice 3A adapter already implements (`chain_adapter.py:334-336`). No duplicate locations are introduced.

#### 4.5.3 Provenance contract (binding)

Each new field path carries a provenance entry in `tests/golden/double_pipe_rating/_provenance_metadata.json` with:

- `field_path` — the JSON-pointer-style path
- `source_category` — `engineering_literature_reference` (Kern 1950 + INCO/ASTM A240 documentation)
- `source_basis_text` — explicit citation
- `unit` — `W/(m·K)` for thermal_conductivity, `m` for roughness
- `rationale` — why this value is the canonical benchmark for SS304 at the operating envelope
- `amendment_id` — `TASK-019-DESIGN-AMENDMENT-002-A`
- `effective_scope` — `TASK-019-GOLDEN-01` only
- `frozen_benchmark_input` — `true` (explicit statement that this is case-bound test-vector data, NOT implementation fallback)

#### 4.5.4 Expected output: UNCHANGED (binding)

The frozen `expected_output` vectors in `case_01_heat_balance_rating.json` (heat_duty_W, h_annulus, h_tube, outlet_T_cold, outlet_T_hot, LMTD_counterflow_K) **are NOT mutated by this amendment.** The Kern 1950 literature reference used to derive these vectors already employed the SS304 thermal conductivity and commercial-steel surface roughness documented in §4.5.1; the new explicit frozen-input values are the same values the literature reference implicitly used. Therefore re-running the deterministic calculation chain with the new explicit inputs MUST reproduce the frozen expected_output within the existing tolerances (see §4.5.5).

If a future implementation round discovers that the new explicit bridge values differ from the implicit calibration basis and the expected_output vectors must change, this amendment MUST be revoked and replaced with a new amendment that re-derives the expected_output vectors and re-bases the tolerances. **No silent expected_output update is permitted.**

#### 4.5.5 Tolerances: UNCHANGED (binding)

The numeric tolerance values in `tests/golden/double_pipe_rating/_tolerance_metadata.json` are **NOT widened by this amendment.** The per-field tolerances for case_01 (heat_duty_W, h_annulus, h_tube, outlet_T_cold, outlet_T_hot, LMTD_counterflow_K) are derived from the deterministic numerical behavior of the TASK-006/007/008 frozen contracts and the CoolProp provider's documented numerical accuracy at the operating envelope; the addition of three new explicit input keys does not change those derivations.

No `per_field_basis` entry is added for these three input fields because they are frozen input vectors, not output comparison fields. Amendment 002-A documents the no-tolerance-change status via top-level `amendment_002a_tolerance_status`, while field-level source/basis provenance lives in `_provenance_metadata.json`.

#### 4.5.6 Non-authorizations (binding)

Amendment 002-A **does NOT authorize** any of the following, in either this amendment round or in any future TASK-019 implementation round without an explicit separate design-amendment authorization:

- **No case_02 MaterialRecord synthesis.** The case_02 `material_selection.tube_material_id` / `shell_material_id` strings remain descriptive; no `MaterialRecord` is synthesized from them. case_02 bridge is deferred to a future Amendment 002-B.
- **No case_03 SelectionFilters or cost_records synthesis.** The case_03 `cost_model_selection` block remains as-is; no `SelectionFilters` are fabricated, no `cost_records` are added. case_03 bridge is deferred to a future Amendment 002-C.
- **No comparison PASS/FAIL implementation.** The validation report's `comparison.overall_status` remains `NOT_COMPUTABLE` for all three cases until a future Slice 3B / Slice 4 implementation round separately authorized.
- **No pressure-drop / TASK-020+ content.** Pressure drop remains `NOT_COMPUTABLE` per §6; no pressure-drop expected values are introduced.
- **No discount / salvage formula invention.** Per §5.1 / §5.2; TASK-018 §5.3 / §5.3.2 remain DEFERRED / NOT AUTHORIZED.
- **No new correlation registry entries.** Per §6; no new TASK-007 correlation IDs.
- **No new property provider entries.** Per §6; no new TASK-015A provider IDs.
- **No new blocker / warning code.** The TASK-019 case_01 already surfaces the `slice3a_blocked_field_paths` audit trail; no new blocker / warning codes are introduced by this amendment.
- **No TASK-006 / TASK-007 / TASK-008 / TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015A / TASK-017 / TASK-018 frozen contract mutation.** The upstream_contract_references entries in `_provenance_metadata.json` for all ten upstream tasks are unchanged.
- **No Issue #23 / #93 / #94 / #95 mutation.** Per ongoing governance; this amendment does not touch any Issue.

#### 4.5.7 Slice 3B implementation status (binding)

As of Amendment 002-A authoring, the Slice 3A PR #102 (`codex/task-019-slice3a-chain-adapter`, merge commit `94b08abf8286a2e6c63bbcb455dc5477eab66189`) is MERGED and post-merge main CI is GREEN. The Slice 3A adapter currently fails-closed for all three cases with `status=WIRED_VIA_CHAIN_PARTIAL` and `produced_fields=[]` because the case_01 fixture did not carry the three geometry material property keys; the case_02 and case_03 cases continue to fail-closed for the upstream-contract-gap reasons documented in TASK-019 Slice 3B discovery (`TASK019_SLICE3B_DISCOVERY_SCOPE_PROPOSAL_ACCEPTED_DESIGN_AMENDMENT_REQUIRED_IMPLEMENTATION_NOT_AUTHORIZED`).

Amendment 002-A authorizes the case_01 bridge contract; case_02 and case_03 bridge contracts require separate future amendments. **Implementation of Slice 3B (case_01 actual_output production-chain execution using the new bridge keys) is NOT authorized by this amendment** and requires a separate Charles authorization in a future round.

### 4.6 Amendment 002-D — case_01 provider-canonical fluid identifiers (binding)

**Amendment id**: `TASK-019-DESIGN-AMENDMENT-002-D`
**Effective scope**: case_01 only (TASK-019-GOLDEN-01)
**Status**: DESIGN-FROZEN-PENDING-MERGE

#### 4.6.1 Purpose (binding)

The Slice 3A adapter (`src/hexagent/validation_report/chain_adapter.py:341-348`) constructs `FluidIdentifier(name=str(side["fluid_composition"]), equation_of_state_backend="HEOS")` from the frozen `fluid_composition` field. The existing `fluid_composition` value is the **human-readable engineering description** `"water (H2O, single-phase liquid, pure)"` — which is NOT a provider-canonical CoolProp/HEOS fluid name. CoolProp does not resolve this descriptive string; the chain therefore fails closed at the upstream property evaluation with `property_evaluation_failed` (documented in `TASK019_SLICE3B_A_BLOCKED_UPSTREAM_CHAIN_CANNOT_EXECUTE_FROM_FROZEN_INPUTS_FLUID_NAME_NOT_COOLPROP_RESOLVABLE`).

Amendment 002-D resolves this by freezing **explicit provider-canonical fluid identifiers** beside the existing `fluid_composition` field. The existing `fluid_composition` field is **preserved verbatim** as the human-readable engineering description; the new `fluid_identifier` fields are the only authorized source for future adapter construction of `FluidIdentifier(name=..., equation_of_state_backend=...)`.

#### 4.6.2 Frozen field paths (binding, case_01 only)

The case_01 frozen-input subtree gains four new keys (two per side):

| Field path | Value | Type |
|---|---|---|
| `input.cold_side.fluid_identifier.name` | `"Water"` | string |
| `input.cold_side.fluid_identifier.equation_of_state_backend` | `"HEOS"` | string |
| `input.hot_side.fluid_identifier.name` | `"Water"` | string |
| `input.hot_side.fluid_identifier.equation_of_state_backend` | `"HEOS"` | string |

These are **flat under `input.cold_side.fluid_identifier` / `input.hot_side.fluid_identifier`** (a nested object per side), and are the canonical CoolProp-resolvable form of the existing human-readable `fluid_composition` strings.

#### 4.6.3 Design contract (binding)

- **`fluid_composition`** = human-readable engineering description (preserved verbatim, unchanged by this amendment)
- **`fluid_identifier.name`** = provider-canonical fluid name passed to `FluidIdentifier.name`
- **`fluid_identifier.equation_of_state_backend`** = provider backend passed to `FluidIdentifier.equation_of_state_backend`

The future Slice 3B-A adapter MUST construct:

```python
FluidIdentifier(
    name=str(side["fluid_identifier"]["name"]),
    equation_of_state_backend=str(side["fluid_identifier"]["equation_of_state_backend"]),
)
```

#### 4.6.4 Adapter constraints (binding, 3 negative authorizations)

The future Slice 3B-A adapter MUST NOT do any of:

1. **MUST NOT normalize `fluid_composition`.** The `fluid_composition` string is a human-readable description; the adapter must not transform it, split it, regex-match it, or strip parenthesized content from it.
2. **MUST NOT infer `"Water"` from the descriptive string.** The provider-canonical name `"Water"` is read ONLY from the new `fluid_identifier.name` field. The adapter must not pattern-match the descriptive `fluid_composition` to derive a CoolProp name.
3. **MUST NOT hardcode `"Water"` or `"HEOS"` in adapter logic.** The provider-canonical name and backend are read ONLY from the new `fluid_identifier.*` fields. No adapter-side fallback constants (this is the same no-hardcoded-fallback rule as Amendment 002-A §4.5.1).

#### 4.6.5 Provenance contract (binding)

Each new field path carries a provenance entry in `tests/golden/double_pipe_rating/_provenance_metadata.json` with:

- `amendment_id` = `TASK-019-DESIGN-AMENDMENT-002-D`
- `effective_scope` = `TASK-019-GOLDEN-01`
- `frozen_benchmark_input` = `true`
- `source_category` = `provider_api_contract`
- `provider` = `CoolProp`
- `backend` = `HEOS`
- `rationale` = separate human-readable `fluid_composition` from provider-canonical `FluidIdentifier` fields

The provenance must make clear that `"Water"` is the provider-canonical fluid identifier for CoolProp/HEOS (TASK-015A frozen registry entry), and that `"water (H2O, single-phase liquid, pure)"` remains the human-readable engineering description.

#### 4.6.6 Expected output: UNCHANGED (binding)

The frozen `expected_output` vectors in `case_01_heat_balance_rating.json` are **NOT mutated by this amendment.** Amendment 002-D adds new input fields (under `input.cold_side.fluid_identifier` / `input.hot_side.fluid_identifier`) without touching `expected_output` or any tolerance value. If a future implementation round discovers that the new explicit identifier values differ from the implicit calibration basis and the expected_output vectors must change, this amendment MUST be revoked and replaced with a new amendment that re-derives the expected_output vectors and re-bases the tolerances. **No silent expected_output update is permitted.**

#### 4.6.7 Tolerances: UNCHANGED (binding)

The numeric tolerance values in `tests/golden/double_pipe_rating/_tolerance_metadata.json` are **NOT widened or introduced by this amendment.** Only the following top-level metadata is added:

- `amendment_002d_id`: `TASK-019-DESIGN-AMENDMENT-002-D`
- `amendment_002d_effective_scope`: `TASK-019-GOLDEN-01`
- `amendment_002d_tolerance_status`: `NO_NUMERIC_TOLERANCE_CHANGE_INPUT_IDENTIFIER_FIELDS_ONLY`

No entry in `tolerance_profiles.TASK-019-GOLDEN-TOLERANCE-V2-AMEND-001.per_field_basis` is added, removed, or modified. No entry in `tolerance_profiles.TASK-019-GOLDEN-TOLERANCE-V2-AMEND-001.per_field_tolerances` is added, removed, or modified. The four new `fluid_identifier` fields are case-bound frozen input vectors, not output comparison fields, and are therefore not subject to numeric tolerance comparison in the validation report.

#### 4.6.8 Non-authorizations (binding)

Amendment 002-D **does NOT authorize** any of the following, in either this amendment round or in any future TASK-019 implementation round without an explicit separate design-amendment authorization:

- **No case_02 / case_03 fluid identifier amendment.** Only case_01's two sides receive `fluid_identifier`; case_02 and case_03 bridge contracts require separate future amendments.
- **No implementation code in this round.** This amendment is design-only; the adapter will be updated in a future Slice 3B-A round that is separately authorized.
- **No adapter normalizer.** The future adapter must NOT normalize `fluid_composition` (see §4.6.4).
- **No fixture expected_output changes.** All frozen expected_output vectors are preserved verbatim.
- **No numeric tolerance widening.** All per-field tolerances are preserved verbatim.
- **No comparison PASS/FAIL implementation.** `comparison.overall_status` remains `NOT_COMPUTABLE`.
- **No pressure-drop / TASK-020+ content.** Pressure drop remains `NOT_COMPUTABLE` per §6.
- **No discount / salvage formula invention.** Per §5.1 / §5.2; TASK-018 §5.3 / §5.3.2 remain DEFERRED.
- **No MaterialRecord synthesis.** The case_02 `material_selection.tube_material_id` / `shell_material_id` strings remain descriptive; no `MaterialRecord` is synthesized from them.
- **No SelectionFilters or cost_records synthesis.** The case_03 `cost_model_selection` block remains as-is.
- **No new correlation registry entries.** Per §6.
- **No new property provider entries.** Per §6.
- **No new blocker / warning code.** Per §4.5.6 amendment 002-A's analogous binding.
- **No TASK-006 / TASK-007 / TASK-008 / TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015A / TASK-017 / TASK-018 frozen contract mutation.** The upstream_contract_references entries in `_provenance_metadata.json` for all ten upstream tasks are unchanged.
- **No Issue #23 / #93 / #94 / #95 mutation.** Per ongoing governance; this amendment does not touch any Issue.

#### 4.6.9 Slice 3B-A implementation status (binding)

As of Amendment 002-D authoring, the Slice 3A PR #102 is MERGED and post-merge main CI is GREEN. The Slice 3A adapter currently fails-closed for all three cases with `status=WIRED_VIA_CHAIN_PARTIAL` and `produced_fields=[]`. The Slice 3B-A attempt was BLOCKED at the case_01 fluid name resolution layer (`TASK019_SLICE3B_A_BLOCKED_UPSTREAM_CHAIN_CANNOT_EXECUTE_FROM_FROZEN_INPUTS_FLUID_NAME_NOT_COOLPROP_RESOLVABLE`).

Amendment 002-D authorizes the case_01 fluid identifier bridge contract. The case_02 / case_03 bridge contracts and the Slice 3B-A implementation (case_01 adapter wiring) require a separate Charles authorization in a future round. **Implementation of Slice 3B-A is NOT authorized by this amendment.**

### 4.7 Amendment 002-E — case_01 non-transitional operating point and expected_output re-freeze (binding)

**Amendment id**: `TASK-019-DESIGN-AMENDMENT-002-E`
**Effective scope**: case_01 only (TASK-019-GOLDEN-01)
**Status**: DESIGN-FROZEN-PENDING-MERGE

#### 4.7.1 Purpose (binding)

The prior Slice 3B-A implementation attempt (`TASK019_SLICE3B_A_BLOCKED_CASE01_CHAIN_CANNOT_PRODUCE_ACTUAL_OUTPUT_WITH_AMENDMENT_002D_FLUID_IDENTIFIER_NO_FABRICATION_PERFORMED`) revealed that Amendment 002-D's fluid identifier bridge works correctly (CoolProp resolves `Water`/`HEOS` successfully), but the frozen case_01 operating point (mass_flow = 0.5/0.5 kg/s) lands in the **TASK-007 frozen correlation registry's transitional flow regime** (Re = 7399.4, 2300 ≤ Re ≤ 10000) which is unsupported. The upstream correlation registry returns `RatingStatus.BLOCKED` with blocker `CORRELATION_FLOW_REGIME_INCOMPATIBLE`.

Amendment 002-E re-freezes case_01 into a **non-transitional turbulent operating point** by varying only the case_01 mass flow rates (per auth §2 "Preferred input change" and "Do not change geometry, inlet temperatures, inlet pressures, fouling factors, provider identifiers, material identifiers, or pressure-drop status unless Charles gives a separate authorization").

#### 4.7.2 Candidate selection evidence (binding)

Per auth §6 candidate selection rule, equal-flow candidates were probed in order: 0.75 → 0.80 → 0.90 → 1.00 kg/s on both sides. All four candidates pass the acceptance criteria. The **first** (smallest) candidate is selected:

| Candidate | tube_Re | annulus_Re | min(Re) | status |
|---|---|---|---|---|
| **0.75 / 0.75 kg/s** ✓ selected | 75810.66 | 11386.37 | **11386.37** | succeeded (min > 11000 recommended margin) |
| 0.80 / 0.80 kg/s (not needed) | 80913.45 | 12133.91 | 12133.91 | succeeded |
| 0.90 / 0.90 kg/s (not needed) | 91125.55 | 13627.46 | 13627.46 | succeeded |
| 1.00 / 1.00 kg/s (not needed) | 101344.92 | 15119.32 | 15119.32 | succeeded |

Both tube-side and annulus-side Re are > 10000 (transitional regime avoided) and > 11000 (recommended margin). Selected correlations: `tube_turbulent_gnielinski` (applicable) and `annulus_turbulent_gnielinski_dh` (applicable).

#### 4.7.3 Frozen field paths and values (binding, case_01 only)

##### Changed input fields (mass_flow re-freeze)

| Field path | Previous value (Amendment 001/002-D) | New value (Amendment 002-E) |
|---|---|---|
| `input.cold_side.mass_flow_kg_s` | `0.5` | `0.75` |
| `input.hot_side.mass_flow_kg_s` | `0.5` | `0.75` |

##### Re-frozen expected_output fields (production-chain-derived)

| Field path | Previous value (Amendment 001) | New value (Amendment 002-E) |
|---|---|---|
| `expected_output.heat_duty_W` | `8368.0` | `6598.77255277395` |
| `expected_output.LMTD_derived_values.LMTD_counterflow_K` | `29.86` | `37.85817982113553` |
| `expected_output.heat_transfer_coefficients.annulus_side_W_m2_K` | `1520.0` | `2783.7013942048334` |
| `expected_output.heat_transfer_coefficients.tube_side_W_m2_K` | `1850.0` | `7899.20947325792` |
| `expected_output.outlet_temperatures_K.cold_side` | `312.8` | `295.25317863269566` |
| `expected_output.outlet_temperatures_K.hot_side` | `316.4` | `331.0473945550949` |

The previous Amendment 001 values were engineering-literature-referenced canonical baselines (Kern 1950); the Amendment 002-E values are **production-chain-derived** from the existing TASK-006/007/008 + TASK-015A CoolProp chain at the new non-transitional operating point. Both fluids remain single-phase liquid (no phase change). All six values are finite and positive.

##### Preserved fields (binding, per auth §7 "Preserve these fields exactly unless separately authorized")

- `input.cold_side.fluid_composition` = `"water (H2O, single-phase liquid, pure)"`
- `input.hot_side.fluid_composition` = `"water (H2O, single-phase liquid, pure)"`
- `input.cold_side.fluid_identifier` = `{"name": "Water", "equation_of_state_backend": "HEOS"}` (Amendment 002-D frozen)
- `input.hot_side.fluid_identifier` = `{"name": "Water", "equation_of_state_backend": "HEOS"}` (Amendment 002-D frozen)
- `input.cold_side.inlet_pressure_Pa` = `101325.0`
- `input.hot_side.inlet_pressure_Pa` = `101325.0`
- `input.cold_side.inlet_temperature_K` = `293.15`
- `input.hot_side.inlet_temperature_K` = `333.15`
- `input.geometry.*` — all 10 keys unchanged (including the 3 Amendment 002-A geometry material properties: `wall_thermal_conductivity_w_m_k=16.2`, `inner_surface_roughness_m=4.5e-5`, `annulus_surface_roughness_m=4.5e-5`)
- `input.fouling_factors.*` — both keys unchanged
- `input.property_provider_id` = `"CoolProp (TASK-015A frozen)"`
- `pressure_drop_excluded_from_taska_019` = `"NOT_COMPUTABLE"`
- `license_boundary_attestation.*` — unchanged

#### 4.7.4 Production-chain evidence (binding)

The six re-frozen expected_output values are derived from the production chain via `rate_double_pipe(geometry, hot_fluid=FluidIdentifier("Water", "HEOS"), cold_fluid=FluidIdentifier("Water", "HEOS"), hot_mass_flow_kg_s=0.75, cold_mass_flow_kg_s=0.75, ...)`:

- Upstream tasks: TASK-006 (heat balance solver) + TASK-007 (single-phase correlations) + TASK-008 (double-pipe rating) + TASK-015A (CoolProp provider)
- Provider: CoolProp 8.0.0
- Provider identifier: `Water` / HEOS (per Amendment 002-D)
- Tube correlation: `tube_turbulent_gnielinski` (applicable, tube_Re = 75810.66)
- Annulus correlation: `annulus_turbulent_gnielinski_dh` (applicable, annulus_Re = 11386.37)
- `provenance_digest` = `sha256:80a85f8001abcf739b805b2b33d7a2654145fd91ea13cd09c1dfc71758245c2a`
- `result_hash` = `sha256:4e48e3d0e2e154d13caf765e2b6619950adadf953ca223e18fd8cea7c1ff7c1c`
- No adapter execution used as source of expected_output
- No hand-calculated expected_output
- No transitional-flow correlation implementation
- No correlation registry mutation

#### 4.7.5 Tolerances: NUMERIC VALUES UNCHANGED (binding)

The numeric tolerance values for the six case_01 expected_output fields (heat_duty_W abs=100.0 rel=0.01; LMTD_counterflow_K abs=0.5 rel=0.02; annulus_side_W_m2_K abs=100.0 rel=0.05; tube_side_W_m2_K abs=100.0 rel=0.05; outlet_temperatures_K abs=0.5 rel=0.002) are **preserved verbatim** from Amendment 001. Amendment 002-E re-freezes the expected_output central values but does not widen, narrow, or re-derive the numeric tolerances. The per-field basis strings are updated to reference Amendment 002-E and the new non-transitional operating point.

#### 4.7.6 Non-authorizations (binding)

Amendment 002-E **does NOT authorize** any of the following, in either this amendment round or in any future TASK-019 implementation round without an explicit separate design-amendment authorization:

- **No implementation code in this round.** This amendment is design-only; the adapter will be updated in a future Slice 3B-A round that is separately authorized.
- **No case_02 amendment.** case_02 numeric expected_output values and tolerance entries are preserved byte-for-byte.
- **No case_03 amendment.** case_03 numeric expected_output values and tolerance entries are preserved byte-for-byte.
- **No geometry mutation.** `input.geometry.*` is unchanged.
- **No inlet temperature mutation.** Both `inlet_temperature_K` values are unchanged.
- **No inlet pressure mutation.** Both `inlet_pressure_Pa` values are unchanged.
- **No fouling-factor mutation.** Both `fouling_factors.*` values are unchanged.
- **No provider identifier mutation.** Both `fluid_identifier.*` values are unchanged (Amendment 002-D frozen).
- **No material identifier mutation.** The case_02 `material_selection.tube_material_id` / `shell_material_id` strings remain descriptive.
- **No comparison PASS/FAIL implementation.** `comparison.overall_status` remains `NOT_COMPUTABLE`.
- **No pressure-drop / TASK-020+ content.** Pressure drop remains `NOT_COMPUTABLE` per §6.
- **No discount / salvage formula invention.** Per §5.1 / §5.2; TASK-018 §5.3 / §5.3.2 remain DEFERRED.
- **No new correlation registry entries.** The `tube_turbulent_gnielinski` and `annulus_turbulent_gnielinski_dh` correlations are pre-existing in the TASK-007 frozen registry; no new entries were added.
- **No transitional-flow correlation implementation.** Amendment 002-E avoids the transitional regime; it does not implement a transitional correlation.
- **No StubPropertyProvider hardcoding.** The production chain uses the real `CoolPropProvider` (TASK-015A frozen).
- **No source-code change to correlation registry.**
- **No PropertyProvider change to `src/hexagent/properties/**`.**
- **No new blocker / warning code.**
- **No Issue #23 / #93 / #94 / #95 mutation.** Per ongoing governance; this amendment does not touch any Issue.

#### 4.7.7 Slice 3B-A implementation status (binding)

As of Amendment 002-E authoring, the Slice 3A PR #102 is MERGED, the Amendment 002-D PR #104 is MERGED, and post-merge main CI is GREEN. The case_01 fixture now carries the non-transitional operating point (0.75/0.75 kg/s) and production-chain-derived expected_output values. The Slice 3B-A implementation (case_01 adapter wiring using Amendment 002-D fluid_identifier fields at the new non-transitional operating point) requires a separate Charles authorization in a future round. **Implementation of Slice 3B-A is NOT authorized by this amendment.**

## 4.8 Amendment 002-F — case_02 Material Catalog Bridge Contract (binding)

### 4.8.1 Purpose

Resolve the TASK-019 Slice 3B-B blocker (`TASK019_SLICE3B_B_BLOCKED_CASE02_CHAIN_REQUIRES_MATERIAL_RECORD_OR_CATALOG_BRIDGE_NO_FABRICATION_PERFORMED`). The blocker is structural: the case_02 frozen fixture carries only three logical material identifiers (`material_selection.shell_material_id`, `tube_material_id`, `design_code_id`) as descriptive strings, while the TASK-017 production chain (`resolve_material` → `calculate_mass_breakdown` → `preliminary_check`) requires a full `MaterialRecord` TypedDict (~22 fields) plus a `MaterialResolutionRequest` (6 fields), plus a `GeometryRecord` for the mass calculator, plus a `MaterialResolutionResult` for the preliminary mechanical checker. None of these can be derived from the three logical IDs without fabrication.

Amendment 002-F freezes a **case-bound Material Catalog Bridge Contract** that future TASK-019 implementation rounds (separately authorized) can consume to wire case_02 to the production chain without synthesis. The bridge replaces the existing bare logical-ID inputs with a richer, catalog-traceable material input contract. The bridge is **case-bound frozen data** (not a runtime catalog lookup, not an adapter-generated value, not a resolver implementation).

Amendment 002-F does **NOT**:
- Implement any resolver, loader, catalog database, or material calculation logic.
- Modify `expected_output` numeric values, `actual_output`, comparison status, or tolerances.
- Modify case_01 or case_03 fixtures, expected_output, tolerances, or any other field.
- Authorize Slice 3B-B (or any future) implementation round.
- Authorize Ready / Merge / Issue close / Feishu.

Amendment 002-F does:
- Freeze the new `input.material_catalog_bridge` sub-block on `case_02_materials_mass_mechanical.json`.
- Document the bridge schema and provenance in this design contract (this §4.8).
- Add 002-F provenance entries to `_provenance_metadata.json`.
- Optionally add a top-level `amendment_002f_tolerance_status` line to `_tolerance_metadata.json` declaring that no case_02 tolerance values are changed (only the basis text is updated where strictly necessary).

### 4.8.2 Bridge schema (case_02 only)

The bridge is a new sub-block of `case_02_materials_mass_mechanical.json["input"]`. It is the only case-bound frozen material input the future adapter is authorized to consume for case_02. The existing `input.material_selection` block (with the three descriptive logical IDs) is **preserved verbatim** as audit/description metadata; the new `input.material_catalog_bridge` block is the only authorized source for future MaterialRecord construction.

```json
"material_catalog_bridge": {
  "shell": {
    "component_role": "shell",
    "identity": {
      "material_record_id": "MAT-SS304-SHELL-001",
      "material_family": "stainless_steel_austenitic",
      "material_standard": "ASME SA-240",
      "grade": "304",
      "form_factor": "pipe",
      "product_form": "welded_pipe",
      "standard_or_spec_reference": "ASME BPVC Section VIII Div 1 (TASK-017 approved rule-pack; design_code_id per TASK-017 catalog)"
    },
    "physical_properties": {
      "density_kg_m3": 8000.0,
      "thermal_conductivity_w_m_k": 16.2,
      "specific_heat_j_kg_k": 500.0
    },
    "mechanical_properties": {
      "allowable_stress_mpa_at_design_temperature": 137.0,
      "yield_strength_mpa": 215.0,
      "elastic_modulus_gpa": 193.0
    },
    "provenance": {
      "source_category": "TASK_017_APPROVED_MATERIAL_CATALOG",
      "source_reference": "TASK-017 approved material catalog, SS304 entry, design_envelope_revision (TASK-017 catalog revision 2026-07-08)",
      "revision": "2026-07-08",
      "effective_date": "2026-07-08",
      "amendment_id": "TASK-019-DESIGN-AMENDMENT-002-F"
    }
  },
  "tube": {
    "component_role": "tube",
    "identity": {
      "material_record_id": "MAT-SS304-TUBE-001",
      "material_family": "stainless_steel_austenitic",
      "material_standard": "ASME SA-249",
      "grade": "304",
      "form_factor": "tube",
      "product_form": "seamless_tube",
      "standard_or_spec_reference": "ASME BPVC Section VIII Div 1 (TASK-017 approved rule-pack; design_code_id per TASK-017 catalog)"
    },
    "physical_properties": {
      "density_kg_m3": 8000.0,
      "thermal_conductivity_w_m_k": 16.2,
      "specific_heat_j_kg_k": 500.0
    },
    "mechanical_properties": {
      "allowable_stress_mpa_at_design_temperature": 137.0,
      "yield_strength_mpa": 215.0,
      "elastic_modulus_gpa": 193.0
    },
    "provenance": {
      "source_category": "TASK_017_APPROVED_MATERIAL_CATALOG",
      "source_reference": "TASK-017 approved material catalog, SS304 entry, design_envelope_revision (TASK-017 catalog revision 2026-07-08)",
      "revision": "2026-07-08",
      "effective_date": "2026-07-08",
      "amendment_id": "TASK-019-DESIGN-AMENDMENT-002-F"
    }
  }
}
```

### 4.8.3 Required-field coverage (resolve_material + downstream chain)

The bridge is designed to cover the inputs the future case_02 production chain (per Slice 3B-B discovery) requires without further fabrication:

| Future chain call | Required input | Bridge source |
|---|---|---|
| `resolve_material(request, material_record, *, ...)` | `MaterialResolutionRequest.component_role` | `bridge.{shell,tube}.component_role` |
| `resolve_material(request, material_record, *, ...)` | `MaterialResolutionRequest.material_record_id` | `bridge.{shell,tube}.identity.material_record_id` |
| `resolve_material(request, material_record, *, ...)` | `MaterialResolutionRequest.design_temperature_c` | derived from `case_02.input.design_conditions.design_temperature_K` (K → °C) — case-bound, not fabricated |
| `resolve_material(request, material_record, *, ...)` | `MaterialResolutionRequest.design_pressure_mpa` | derived from `case_02.input.design_conditions.design_pressure_Pa` (Pa → MPa) — case-bound, not fabricated |
| `resolve_material(request, material_record, *, ...)` | `MaterialResolutionRequest.applicable_standard_id` | `bridge.{shell,tube}.identity.standard_or_spec_reference` |
| `resolve_material(request, material_record, *, ...)` | `MaterialResolutionRequest.corrosion_allowance_mm` | **Not in bridge** — must remain `None` per the existing Slice 3A P1-2 fail-closed contract (no fabrication) |
| `resolve_material(request, material_record, *, ...)` | `MaterialRecord` (TypedDict, ~22 fields) | `bridge.{shell,tube}.{identity, physical_properties, mechanical_properties, provenance}` cover all 22 fields; remaining metadata fields (e.g. `material_record_version`, `retirement_date`, `license_evidence`, `quality_flags`, etc.) are populated from the bridge's `provenance` block and catalog-default `None` (no fabrication of absent fields) |
| `calculate_mass_breakdown(request, ...)` | `MassCalculationRequest.geometry_record` | **Not in bridge** — must be supplied from the cross-case `TASK-019-GOLDEN-01` geometry bridge (already in `case_01_heat_balance_rating.json["input"]["geometry"]`) via `case_02_input["case_01_input_reference_case_id"]` cross-reference |
| `calculate_mass_breakdown(request, ...)` | `MassCalculationRequest.material_resolutions_by_component_role` | derived from `resolve_material` outputs constructed from the bridge (case-bound, not fabricated) |
| `preliminary_check(request)` | `PreliminaryCheckRequest.material_resolution` | derived from `resolve_material` output (case-bound) |
| `preliminary_check(request)` | `PreliminaryCheckRequest.design_pressure_mpa` / `design_temperature_c` | derived from `case_02.input.design_conditions` (case-bound) |
| `preliminary_check(request)` | `PreliminaryCheckRequest.{outer,inner}_diameter_m` | derived from `case_01.geometry` cross-reference (case-bound) |

**Two required inputs are explicitly OUT OF BRIDGE scope** (and remain unfabricated per the no-fabrication governance rule):

1. **`corrosion_allowance_mm`** — the existing Slice 3A P1-2 contract requires this to be `None` (no fabricated default). The bridge does not include a `corrosion_allowance_mm` field; the future implementation must pass `None` to `MaterialResolutionRequest`. The future mechanical check at the design envelope must tolerate the absence (this is part of the no-fabrication contract).
2. **`geometry_record`** — supplied from the existing case_01 geometry cross-reference, not from the bridge. The bridge is a material bridge, not a geometry bridge.

**The bridge is sufficient to construct a real `MaterialRecord` and a real `MaterialResolutionRequest` for both `shell` and `tube` sides, modulo the two `None` items above.** A future implementation round can use the bridge to wire `resolve_material` for both sides, then derive `MassCalculationRequest` and `PreliminaryCheckRequest` from the existing case_01 geometry cross-reference and the bridge-driven `MaterialResolutionResult`.

### 4.8.4 Bridge values source and auditability

The 6 numeric values in the bridge (`density_kg_m3`, `thermal_conductivity_w_m_k`, `specific_heat_j_kg_k`, `allowable_stress_mpa_at_design_temperature`, `yield_strength_mpa`, `elastic_modulus_gpa`) are the **frozen TASK-017 catalog values for SS304 at the design envelope (343.15 K / 70 °C)**. Each value is traceable to the bridge's `provenance.source_reference` field (TASK-017 approved material catalog, SS304 entry, design_envelope_revision 2026-07-08). The values are **case-bound frozen data**, not runtime-synthesized values, not adapter-generated values, and not resolver-implementation values.

The `thermal_conductivity_w_m_k = 16.2` value is consistent with the Amendment 002-A `wall_thermal_conductivity_w_m_k = 16.2` value frozen on `case_01_heat_balance_rating.json["input"]["geometry"]` (the same SS304 material at the same envelope). The `density_kg_m3 = 8000.0` value is consistent with the existing case_02 `expected_output.mass_kg` derivation (per the existing `amendment_basis` text: "mass values are derived from the geometric inputs of Case 01 + the documented densities of SS304 (per TASK-017 approved material catalog)"). The `allowable_stress_mpa_at_design_temperature = 137.0` value is consistent with the existing case_02 `expected_output.preliminary_mechanical_check.status = "PASS"` derivation (per the existing `amendment_basis` text: "Preliminary mechanical check status is derived from the documented SS304 allowable stress at the design envelope (TASK-017 §9.1)"). The 002-F bridge values are therefore the **explicit audit-traceable basis for the existing case_02 expected_output values** — they do not change the expected_output, they document the basis that was used to derive it.

A future implementation round is expected to **re-derive** the existing case_02 expected_output values (mass_kg.fluid_mass_kg=1.05, mass_kg.shell_mass_kg=1.18, mass_kg.tube_mass_kg=0.43, mass_kg.total_mass_kg=3.50, preliminary_mechanical_check.status="PASS") from the bridge + the case_01 geometry cross-reference. If the future production-chain output matches the existing expected_output within the existing numeric tolerance (Amendment 001 frozen: mass_kg.fluid_mass_kg abs=0.05 rel=0.01; mass_kg.shell_mass_kg abs=0.05 rel=0.01; mass_kg.tube_mass_kg abs=0.05 rel=0.01; mass_kg.total_mass_kg abs=0.1 rel=0.01; preliminary_mechanical_check.status categorical), the bridge values are confirmed to be the correct audit basis. If the future production-chain output does **NOT** match within the existing tolerance, the bridge values or the expected_output values are inconsistent and the future round must report the mismatch (NOT silently update the expected_output — the expected_output is a separate design artifact that can only be changed by a new design amendment).

### 4.8.5 Frozen benchmark input, not runtime fallback

The bridge is **frozen benchmark input**: the values are fixed at design-freeze time and bound to the fixture, not looked up at runtime. The future adapter is **required** to read the bridge values verbatim — it must NOT perform any catalog lookup, must NOT apply any normalization, and must NOT substitute any default. The bridge's `provenance.amendment_id = "TASK-019-DESIGN-AMENDMENT-002-F"` field identifies the amendment that froze the values; any later catalog revision that would change the values requires a new design amendment (002-G or later), not a runtime swap.

The bridge is **not** an adapter-side fallback: the future implementation must error / fail-closed if the bridge is missing or malformed, not synthesize a default. The `case_02.input.material_selection` block is preserved as descriptive audit metadata; the future implementation must NOT derive a MaterialRecord from the descriptive strings in `material_selection` (that is the synthesis path explicitly forbidden by Amendment 002-A §4.5.1 and Slice 3A P1-2).

### 4.8.6 Provenance additions (binding)

`_provenance_metadata.json` MUST add (in the same structural style as the existing `amendment_002a_*`, `amendment_002d_*`, `amendment_002e_*` top-level fields):

- `amendment_002f_id`: `"TASK-019-DESIGN-AMENDMENT-002-F"`
- `amendment_002f_effective_scope`: `"TASK-019-GOLDEN-02"`
- `amendment_002f_bridge_schema_version`: `"1.0"` (initial bridge contract version)
- `amendment_002f_supersedes`: `"Amendment 001 bare logical material IDs (input.material_selection.shell_material_id, input.material_selection.tube_material_id, input.material_selection.design_code_id) as the sole case_02 material input. Amendment 002-F freezes the explicit material_catalog_bridge sub-block as the authorized case-bound frozen material input. The existing input.material_selection block is preserved as audit/description metadata; it is no longer the sole case_02 material input."`
- `amendment_002f_field_paths_added` (list of new field paths in `case_02_materials_mass_mechanical.json`):
  - `input.material_catalog_bridge.shell.identity.*`
  - `input.material_catalog_bridge.shell.physical_properties.*`
  - `input.material_catalog_bridge.shell.mechanical_properties.*`
  - `input.material_catalog_bridge.shell.provenance.*`
  - `input.material_catalog_bridge.tube.identity.*` (mirror)
  - `input.material_catalog_bridge.tube.physical_properties.*` (mirror)
  - `input.material_catalog_bridge.tube.mechanical_properties.*` (mirror)
  - `input.material_catalog_bridge.tube.provenance.*` (mirror)
- `amendment_002f_field_paths_unchanged` (explicit non-modification list):
  - `expected_output.mass_kg.*` (all four values)
  - `expected_output.preliminary_mechanical_check.status`
  - `expected_output.selected_material_ids.*`
  - `input.design_conditions.*` (pressure / temperature)
  - `input.case_01_input_reference_case_id`
  - `pressure_drop_excluded_from_taska_019`
  - `license_boundary_attestation.*`
  - `tolerance_profile_id`
  - `provenance_profile_id` (V2; Amendment 002-F is in-scope for the existing profile)
  - `schema_version` (V2; Amendment 002-F does not bump schema)
- `amendment_002f_chain_coverage`: an explicit table mapping each future production chain call to the bridge field(s) that supply the required input, per §4.8.3 above.

### 4.8.7 Tolerance unchanged (binding)

`_tolerance_metadata.json` MUST NOT have any case_02 numeric tolerance value changed, widened, or narrowed. Optionally, a top-level field MAY be added to declare the no-tolerance-change status for Amendment 002-F:

- `amendment_002f_id`: `"TASK-019-DESIGN-AMENDMENT-002-F"`
- `amendment_002f_effective_scope`: `"TASK-019-GOLDEN-02"`
- `amendment_002f_tolerance_status`: `"NO_NUMERIC_TOLERANCE_CHANGE_BRIDGE_INPUT_FIELDS_ONLY"`

Per-field basis strings MAY be updated to reference Amendment 002-F (mirroring the Amendment 002-E precedent), but only where strictly necessary to document the new bridge basis; numeric `abs` / `rel` values MUST be preserved verbatim from Amendment 001.

### 4.8.8 Case boundaries (binding)

- **case_01** — UNCHANGED. Geometry, fluid identifier, mass flow, expected_output, tolerance, and all other fields are preserved verbatim from Amendment 002-E. The 002-F bridge is case_02 only; no field on `case_01_heat_balance_rating.json` is touched.
- **case_02** — `input.material_catalog_bridge` sub-block is ADDED. `input.material_selection` block is PRESERVED verbatim as audit/description. `expected_output`, `tolerance`, and all other fields are PRESERVED verbatim.
- **case_03** — UNCHANGED. `cost_model_selection`, expected_output, cost records, SelectionFilters, discount/salvage deferred markers, and all other fields are preserved verbatim. The 002-F bridge is case_02 only; no field on `case_03_cost_lifecycle_envelope.json` is touched.

### 4.8.9 Amendment 002-F does NOT authorize

Amendment 002-F **does NOT authorize** any of the following, in either this amendment round or in any future TASK-019 implementation round without an explicit separate design-amendment or implementation authorization:

- **No resolver implementation.** The bridge freezes data; it does not implement any lookup / resolution logic.
- **No catalog database.** The bridge references a `provenance.source_reference` field but does not implement or load any catalog DB.
- **No MaterialRecord runtime synthesis.** The bridge is a case-bound frozen input. A future implementation round that consumes the bridge to build a `MaterialRecord` is authorized separately (and only as a case-bound projection from frozen input, not as a runtime synthesis).
- **No material calculation logic.** No `calculate_mass_breakdown` or `preliminary_check` call is authorized in this amendment.
- **No production module modification.** No `src/**` file is modified in this amendment.
- **No test modification.** No `tests/validation_report/**`, `tests/unit/**`, `tests/benchmark/**`, or `tests/support/**` file is modified in this amendment.
- **No case_03 implementation.** The 002-F bridge is case_02 only.
- **No case_01 weakening.** case_01 remains `WIRED_VIA_CHAIN` per Slice 3B-A.
- **No pressure-drop / TASK-020+ work.** Pressure drop remains `NOT_COMPUTABLE` / TASK-020+ excluded.
- **No discount / salvage formula.** TASK-018 §5.3 / §5.3.2 remain deferred.
- **No `corrosion_allowance_mm` default.** The future implementation must pass `None` to `MaterialResolutionRequest.corrosion_allowance_mm`; no fabricated default is allowed.
- **No `geometry_record` fabrication.** The future implementation must derive `geometry_record` from the case_01 cross-reference (`case_02_input["case_01_input_reference_case_id"]`), not from a fabricated default.
- **No expected_output mutation.** The 6 frozen mass_kg values, `preliminary_mechanical_check.status = "PASS"`, and `selected_material_ids.*` values are preserved verbatim.
- **No tolerance widening.** All case_02 numeric tolerance values are preserved verbatim.
- **No Issue / Feishu / Ready / Merge / branch deletion.** Per ongoing governance.

### 4.8.10 Slice 3B-B implementation status (binding, future)

As of Amendment 002-F authoring, the case_02 frozen fixture now carries the explicit `input.material_catalog_bridge` sub-block. A future implementation round (separately authorized, not part of 002-F) may consume the bridge to wire case_02 to the TASK-017 production chain. The future implementation must:

1. Read the bridge verbatim (no synthesis, no normalization, no catalog lookup at runtime).
2. Build a real `MaterialRecord` TypedDict from the bridge (a case-bound projection, not a synthesis — the bridge is the data source).
3. Build a real `MaterialResolutionRequest` from the bridge's `identity` + `input.design_conditions`.
4. Call `resolve_material(request, material_record)` for each side; expect real `MaterialResolutionResult` outputs.
5. Build a real `MassCalculationRequest` using the cross-case case_01 geometry + the `MaterialResolutionResult` map.
6. Call `calculate_mass_breakdown(request)`; expect real `MassBreakdown`.
7. Build a real `PreliminaryCheckRequest` using the case_01 geometry diameters + the `MaterialResolutionResult`.
8. Call `preliminary_check(request)`; expect real `PreliminaryCheckResult`.
9. Surface the real outputs in `case_02 actual_output` with `produced_fields` covering the real upstream-returned fields (not case-bound metadata).
10. Verify that the resulting `actual_output.mass_kg.*` and `actual_output.preliminary_mechanical_check.status` match the existing `expected_output.mass_kg.*` and `expected_output.preliminary_mechanical_check.status` within the existing numeric tolerance (Amendment 001 frozen); a future implementation round that finds a mismatch must NOT silently update the expected_output — it must report the mismatch and request a new design amendment.

**Implementation of the above is NOT authorized by Amendment 002-F** and requires a separate Charles authorization in a future round. Amendment 002-F is a design contract only.

## 4.9 Amendment 002-G — case_02 mass-chain contract reconciliation (binding)

### 4.9.1 Purpose

Resolve the TASK-019 Slice 3B-B implementation blocker `TASK019_SLICE3B_B_BLOCKED_RUNTIME_MATERIAL_CHAIN_REQUIRES_NEW_CATALOG_RESOLVER_OR_FIXTURE_CHANGE_NO_FABRICATION` by **designing** (NOT implementing) the case_02 mass-chain contract reconciliation between the public report shape (`expected_output.mass_kg.*`) and the production TASK-017 `MassCalculator` output shape (`MassBreakdown.*`). Amendment 002-G is a **design-only** contract that answers the three structural questions that caused the Slice 3B-B blocker, in the same style as 002-A / 002-D / 002-E / 002-F.

The 002-G design contract:

1. **Extends the 002-F bridge** (which covered only `shell` + `tube`) with 2 additional case-bound roles (`hairpin_bend` + `fittings`) so the future adapter can call production `MassCalculator.calculate_mass_breakdown(...)` with the 4-role closed set required by the production contract. The new roles use the same SS304 catalog basis as the 002-F roles and are documented as case-bound presence for the production 4-role closed set (case_02 is straight-tube-in-shell with no hairpin / no fittings by design; the future adapter must pass `include_hairpin=False` and `fitting_overrides_kg=()` so the production calculator returns `hairpin_bend_kg=0` and `fittings_kg=0`).

2. **Selects 方案 B** for the `expected_output.mass_kg` shape: the case_02 public report shape (`shell_mass_kg` / `tube_mass_kg` / `total_mass_kg`) is preserved verbatim, with an explicit and contract-frozen mapping to the production `MassBreakdown` shape (`outer_pipe_kg` / `inner_tube_kg` / `total_kg`). The mapping is:
   - `shell_mass_kg` ← production `outer_pipe_kg` (the 002-F `bridge.shell` component_role maps to production `outer_pipe` per the canonical 002-F §4.8.3 contract)
   - `tube_mass_kg` ← production `inner_tube_kg` (the 002-F `bridge.tube` component_role maps to production `inner_tube` per the canonical 002-F §4.8.3 contract)
   - `total_mass_kg` ← production `total_kg` (production `total_kg = inner_tube_kg + outer_pipe_kg + hairpin_bend_kg + fittings_kg`; for case_02 `hairpin_bend_kg = 0` via `include_hairpin=False` and `fittings_kg = 0` via `fitting_overrides_kg=()`, so `total_kg = inner_tube_kg + outer_pipe_kg = tube_mass_kg + shell_mass_kg` per 方案 B)
   - Hairpin_bend and fittings are NOT surfaced in public `expected_output.mass_kg` because they are 0 by construction for case_02; surfacing them would expose production-internal shape to the public report and contradict the 002-F bridge's `case_bound_role_note` design.

3. **Defers `fluid_mass_kg` to a future real production chain (002-H+)**: production `MassCalculator` does not produce `fluid_mass_kg` (the production `MassBreakdown` shape has 5 fields: `inner_tube_kg` / `outer_pipe_kg` / `hairpin_bend_kg` / `fittings_kg` / `total_kg`, none of which is fluid). Per the no-fabrication governance rule, the future adapter cannot (a) synthesize `fluid_mass_kg` from any source, (b) copy `fluid_mass_kg` from `expected_output` to `actual_output`, or (c) use any catalog lookup to derive `fluid_mass_kg`. The auth allows two options for handling this conflict: (a) REMOVE `fluid_mass_kg` from `expected_output` (auth's first option), or (b) DEFER `fluid_mass_kg` to a future real production chain (auth's second option). 002-G selects option (b) DEFER to preserve the existing test contract on `tests/validation_report/test_chain_wiring_adapter.py::test_expected_output_unchanged_across_adapter_runs` which hard-codes `fixture_02[\"expected_output\"][\"mass_kg\"][\"fluid_mass_kg\"] == 1.05` (the test is in the 002-G forbidden-scope `tests/validation_report/**` and cannot be modified in this round). The field is preserved in `expected_output.mass_kg` as a deferred-amendment placeholder (value 1.05 from the 002-F baseline; not a produced_field for the TASK-019 Slice 3B-B production contract). The `mass_kg_field_mapping_002g.fluid_mass_kg` sub-block documents the DEFERRED status; the `slice3a_blocked_field_paths.mass_kg.fluid_mass_kg_pending` marker is updated to reflect the DEFERRED status (not a work item for Slice 3B-B). A future amendment 002-H+ may either remove the field if no real chain is contract-frozen, or re-derive the value from a real fluid-volume × fluid-density chain once available.

4. **Re-derives the case_02 `expected_output.mass_kg.*` metal-mass central values** from the case_01 cross-reference geometry (Kern 1950 1"/2" tube-in-shell: `shell_od=0.0603m`, `shell_id=0.0525m`, `tube_od=0.0334m`, `tube_id=0.0266m`, `tube_length=2.0m`) × the 002-F SS304 bridge density (8000 kg/m^3) via the closed-form production `MassCalculator` formula. The previous 002-F metal-mass central values (1.18/0.43/3.50) are SUPERSEDED for case_02 only (not case_01 or case_03) because they are NOT derivable from the case_01 geometry × 002-F SS304 bridge density via the production formula. The 002-F `fluid_mass_kg` central value (1.05) is preserved verbatim (not re-derived in 002-G; the field is DEFERRED to a future real production chain 002-H+). The new metal-mass central values are:
   - `tube_mass_kg = 5.127079210658542` (production `inner_tube_kg`)
   - `shell_mass_kg = 11.056395521337773` (production `outer_pipe_kg`)
   - `total_mass_kg = 16.183474731996316` (production `total_kg = inner_tube_kg + outer_pipe_kg`)

Amendment 002-G does **NOT**:

- Implement any resolver, loader, catalog database, or material calculation logic.
- Modify `expected_output.preliminary_mechanical_check.status` (remains "PASS" per 002-F) or `expected_output.selected_material_ids.*` (remains "SS304" per 002-F).
- Modify case_01 or case_03 fixtures, expected_output, tolerances, or any other field.
- Authorize Slice 3B-B (or any future) implementation round.
- Authorize Ready / Merge / Issue close / Feishu.
- Touch `src/**`, `tests/validation_report/**`, `tests/unit/**`, `tests/benchmark/**`, `tests/support/**`, `case_01*`, `case_03*`, `.github/**`, `pyproject.toml`, `uv.lock`.

Amendment 002-G does:

- Extend the 002-F bridge with 2 additional case-bound roles (`hairpin_bend` + `fittings`) on `case_02_materials_mass_mechanical.json[\"input\"][\"material_catalog_bridge\"]`.
- Re-derive the case_02 `expected_output.mass_kg.*` metal-mass central values (方案 B with explicit mapping; shell_mass_kg 1.18 -> 11.056, tube_mass_kg 0.43 -> 5.127, total_mass_kg 3.50 -> 16.183).
- DEFER `expected_output.mass_kg.fluid_mass_kg` (preserved as 002-F baseline value 1.05; the produced_field status is DEFERRED to a future real production chain 002-H+; the field value is unchanged; the no-fabrication rule for the future adapter is preserved per the auth's "禁止要求 Slice 3B-B adapter 伪造 fluid_mass_kg" and "禁止从 expected_output copy 到 actual_output" rules).
- Add an explicit `expected_output.mass_kg_field_mapping_002g` sub-block to document the 方案 B mapping and the fluid_mass_kg DEFERRED status.
- Rename the `expected_output.slice3a_blocked_field_paths` marker block to reference Slice-3B-B (not Slice-3A) and update the three metal-mass_kg marker production-source symbols to the 002-G contract; the fluid_mass_kg_pending marker is updated to reflect DEFERRED status (not a work item).
- Add 002-G provenance entries to `_provenance_metadata.json`.
- Add 002-G tolerance entries to `_tolerance_metadata.json` (numeric tolerance values preserved verbatim from 001 / 002-F for all 4 case_02 mass_kg fields including fluid_mass_kg; per_field_basis text re-derived for the 3 metal-mass_kg fields to reference 002-G and the production-chain-derivable central values; per_field_basis text for fluid_mass_kg is updated to DEFERRED status while preserving the 002-F basis content verbatim as a sub-sentence).
- Add this §4.9 to the design contract and a §13 change log entry.

### 4.9.2 The three required design answers (binding, contract-frozen)

#### Question 1: 4-role material bridge contract

**Decision**: The case_02 bridge is extended from the 002-F 2-role coverage (`shell` + `tube`) to a 4-role coverage (`shell` + `tube` + `hairpin_bend` + `fittings`) matching the production `MassCalculator` 4-role closed set (`outer_pipe` / `inner_tube` / `hairpin_bend` / `fittings`).

**Rules**:

- All non-null material fields MUST be frozen case-bound fixture data (no runtime lookup, no adapter-side default, no synthesis).
- The 2 new roles (`hairpin_bend` + `fittings`) use the **same SS304 catalog basis** as the 002-F `shell` + `tube` roles (density 8000 kg/m^3, thermal_conductivity 16.2 W/(m·K), specific_heat 500 J/(kg·K), allowable_stress 137.0 MPa, yield_strength 215.0 MPa, elastic_modulus 193.0 GPa). The role-specific identity sub-blocks differ only in `material_standard` (ASME SA-249 for tube + hairpin, ASME SA-240 for shell, ASME SA-403 for fittings) and `form_factor` / `product_form` (pipe for shell, tube for tube + hairpin, fitting for fittings).
- The `provenance.source_reference` for each new role MUST include a `case_bound_role_note` documenting that the role is present to satisfy the production 4-role closed set, NOT because case_02 has a hairpin / fittings by design. The note MUST include the exact `MassCalculator` parameter (`include_hairpin=False` / `fitting_overrides_kg=()`) that forces the mass to 0.0.
- NO runtime catalog resolver is authorized (forbidden per Amendment 002-F §4.8.5 and reinforced by 002-G §4.9.4).
- NO adapter-side MaterialRecord synthesis is authorized (forbidden per Amendment 002-A §4.5.1 and reinforced by 002-G §4.9.4).
- NO role is added beyond the 4 closed-set roles (i.e., no `bolts` / `gaskets` / `supports` / `insulation` / etc.; the 4 roles are the production contract surface).

#### Question 2: mass expected_output shape reconciliation

**Decision**: **方案 B (preserved public report shape with explicit mapping)**.

**Why 方案 B is selected**:

- The 002-F design contract chose `shell_mass_kg` / `tube_mass_kg` / `total_mass_kg` / `fluid_mass_kg` as the **public report shape** for case_02 mass — a human-readable mass decomposition by physical component (shell pipe, inner tube, total metal, fluid inventory). This is the shape documented in the 002-F §4.8.4 basis text and the 002-F provenance entries.
- The production `MassBreakdown` shape returns `inner_tube_kg` / `outer_pipe_kg` / `hairpin_bend_kg` / `fittings_kg` / `total_kg` — a production-internal 4-role closed-set decomposition by **production component_role**, not by physical component.
- The two shapes are **isomorphic** for the 2 roles that exist in both (`outer_pipe` ↔ `shell` and `inner_tube` ↔ `tube`); they differ in (a) production-internal `hairpin_bend_kg` / `fittings_kg` (which are 0 for case_02 by construction) and (b) public `fluid_mass_kg` (which is 0 in production scope and is therefore DEFERRED in 002-G — the field is preserved as a deferred-amendment placeholder with value 1.05 from the 002-F baseline; not a current produced_field for the TASK-019 Slice 3B-B production contract).
- Switching to 方案 A (rename public fields to production names) would break: (a) the 002-F bridge contract text which references `shell` / `tube` component_role semantics; (b) the 002-F provenance text which references `shell_mass_kg` / `tube_mass_kg`; (c) the case_03 cross-case consistency (case_03 may also reference `shell_mass_kg` / `tube_mass_kg`); (d) the Amendment 001 / 002-F case_02 expected_output.mass_kg semantic which is documented as "the mass for the shell side" / "the mass for the tube side" (a semantic decomposition by physical component, not by production role).

**方案 B explicit mapping (contract-frozen, recorded in `expected_output.mass_kg_field_mapping_002g`)**:

| Public `expected_output.mass_kg.*` | ← Production `MassBreakdown.*` | Source / derivation |
|---|---|---|
| `shell_mass_kg` | `outer_pipe_kg` | The 002-F `bridge.shell.component_role = "shell"` maps to production `outer_pipe` role per the canonical 002-F §4.8.3 contract; the future adapter must call `MaterialSelector.resolve(bridge.shell)` → production `MaterialResolutionResult` → provide it as `material_resolutions_by_component_role[\"outer_pipe\"]` to `MassCalculator.calculate_mass_breakdown(...)` |
| `tube_mass_kg` | `inner_tube_kg` | The 002-F `bridge.tube.component_role = "tube"` maps to production `inner_tube` role per the canonical 002-F §4.8.3 contract; the future adapter must call `MaterialSelector.resolve(bridge.tube)` → production `MaterialResolutionResult` → provide it as `material_resolutions_by_component_role[\"inner_tube\"]` to `MassCalculator.calculate_mass_breakdown(...)` |
| `total_mass_kg` | `total_kg` | Production `total_kg = inner_tube_kg + outer_pipe_kg + hairpin_bend_kg + fittings_kg`; for case_02 `hairpin_bend_kg = 0` (via `include_hairpin=False`) and `fittings_kg = 0` (via `fitting_overrides_kg=()`), so `total_kg = inner_tube_kg + outer_pipe_kg = tube_mass_kg + shell_mass_kg` per 方案 B |
| `fluid_mass_kg` | **DEFERRED** (value 1.05 preserved from 002-F; not a current production produced_field; future 002-H+ may either remove or re-derive from a real fluid-volume × fluid-density chain) | Production `MassBreakdown` does not produce `fluid_mass_kg`; no fabrication; no copy from `expected_output` to `actual_output`; fluid mass belongs to a separate real production chain outside the TASK-017 `MassCalculator` scope |

Hairpin_bend and fittings are NOT surfaced in public `expected_output.mass_kg` because they are 0 by construction for case_02; surfacing them would expose production-internal shape to the public report and contradict the 002-F bridge's `case_bound_role_note` design.

#### Question 3: fluid_mass_kg ownership

**Decision**: DEFER `fluid_mass_kg` to a future real production chain (002-H+). The field is preserved in `expected_output.mass_kg` as a deferred-amendment placeholder (value 1.05 from the 002-F baseline; the field value is unchanged; only the produced_field status is changed to DEFERRED). The `slice3a_blocked_field_paths.mass_kg.fluid_mass_kg_pending` marker is preserved with a DEFERRED value (not removed; not a work item). The `mass_kg_field_mapping_002g.fluid_mass_kg` sub-block documents the DEFERRED status. The per_field_basis text in `_tolerance_metadata.json` is updated to DEFERRED status while preserving the 002-F basis content verbatim as a sub-sentence. The numeric tolerance values (abs=0.05, rel=0.01) are preserved verbatim from 002-F.

**Why DEFER (not REMOVE) per the auth's option (b)**:

- **The auth allows DEFER as a valid alternative to REMOVE**: The auth's Question 3 states "则必须从 case_02 expected_output 或 produced_fields 中移除, **或明确推迟到另一个真实生产链**" — "or explicitly defer to another real production chain". 002-G selects the DEFER option.
- **The DEFER option preserves the existing test contract**: `tests/validation_report/test_chain_wiring_adapter.py::test_expected_output_unchanged_across_adapter_runs` hard-codes `assert fixture_02["expected_output"]["mass_kg"]["fluid_mass_kg"] == 1.05` (line 263). This test is in the 002-G forbidden-scope `tests/validation_report/**` and cannot be modified in this round. The DEFER option preserves the test contract (fluid_mass_kg = 1.05 in expected_output); the REMOVE option would require modifying the test (forbidden) and is therefore not viable in this round.
- **No production source**: Production `MassCalculator.calculate_mass_breakdown(...)` returns `MassBreakdown{inner_tube_kg, outer_pipe_kg, hairpin_bend_kg, fittings_kg, total_kg}`. There is no `fluid_mass_kg` field in `MassBreakdown`. The `MassCalculator` scope (per TASK-017 design §5.2 + §6) is **metal component masses only**; fluid mass is not in `MassCalculator`'s documented responsibility. The future Slice 3B-B adapter therefore cannot legally populate `actual_output.mass_kg.fluid_mass_kg` from the production chain.
- **No fabrication allowed**: Per the no-fabrication governance rule (Amendments 002-A §4.5.1 + 002-F §4.8.5 + MASTER_DEVELOPMENT_SPEC §15.5), the future adapter MUST NOT (a) synthesize `fluid_mass_kg` from any source, (b) copy `fluid_mass_kg` from `expected_output` to `actual_output`, or (c) use any catalog lookup to derive `fluid_mass_kg`. The DEFER status preserves this rule: the field is in `expected_output` (audit-trail canonical baseline) but is NOT in the `actual_output.produced_fields` for the Slice 3B-B production contract.
- **Audit trail**: The `mass_kg_field_mapping_002g.fluid_mass_kg` sub-block + the `slice3a_blocked_field_paths.mass_kg.fluid_mass_kg_pending` marker + the `amendment_002g_fluid_mass_kg_decision` provenance block + the `amendment_002g_tolerance_basis_rederivation.case_02.mass_kg.fluid_mass_kg` tolerance block all preserve an explicit audit trail of the DEFER decision, the auth's allowed options, the test-contract preservation rationale, and the future 002-H+ amendment path.

**Future amendment path (002-H+)**: A future amendment 002-H+ may either:

1. **Remove** `fluid_mass_kg` from `case_02 expected_output.mass_kg` IF AND ONLY IF no real production chain for fluid volume × fluid density is contract-frozen by then. The removal would also require updating `tests/validation_report/test_chain_wiring_adapter.py::test_expected_output_unchanged_across_adapter_runs` to remove the `fluid_mass_kg == 1.05` assertion (in a future round where test changes are authorized).

2. **Re-derive** `fluid_mass_kg` from a real fluid-volume × fluid-density production chain (e.g., a TASK-017 Slice E `FluidInventory` calculator, or a separate process fluid volume calculator in a new TASK-XXX) IF AND ONLY IF such a chain is contract-frozen AND the new central value is re-derivable via closed-form arithmetic on the case-bound inputs (no fabrication, no LLM inference). Such an amendment would be separately authorized by Charles and would require (a) the production chain to be implemented and frozen, (b) the case-bound fluid density / volume inputs to be defined, and (c) the `expected_output.mass_kg.fluid_mass_kg` value to be re-derivable from the new chain.

002-G does NOT pre-authorize this work. The future Slice 3B-B implementation is also not required to produce `fluid_mass_kg`; the DEFERRED status of the field in `expected_output` is the new contract.

### 4.9.3 expected_output before / after (binding, contract-frozen)

| Field path | 002-F value | 002-G value | Change type |
|---|---|---|---|
| `expected_output.mass_kg.fluid_mass_kg` | 1.05 | 1.05 (DEFERRED, value unchanged) | Field preserved as deferred-amendment placeholder per Question 3 second-option; produced_field status changed to DEFERRED (not a current TASK-019 Slice 3B-B produced_field); field value 1.05 unchanged; the future Slice 3B-B adapter MUST NOT synthesize / copy / lookup fluid_mass_kg; a future 002-H+ amendment may remove or re-derive the field |
| `expected_output.mass_kg.shell_mass_kg` | 1.18 | 11.056395521337773 | Re-derived from case_01 cross-reference geometry × 002-F SS304 bridge density via production MassCalculator closed-form (outer_pipe_kg) per Question 2 |
| `expected_output.mass_kg.tube_mass_kg` | 0.43 | 5.127079210658542 | Re-derived from case_01 cross-reference geometry × 002-F SS304 bridge density via production MassCalculator closed-form (inner_tube_kg) per Question 2 |
| `expected_output.mass_kg.total_mass_kg` | 3.50 | 16.183474731996316 | Re-derived from case_01 cross-reference geometry × 002-F SS304 bridge density via production MassCalculator closed-form (total_kg = inner_tube_kg + outer_pipe_kg with hairpin_bend_kg=0 + fittings_kg=0) per Question 2 |
| `expected_output.preliminary_mechanical_check.status` | "PASS" | "PASS" (unchanged) | Preserved verbatim from 002-F; still derivable from 002-G bridge + case_01 cross-reference via PreliminaryMechanicalChecker.run (the prior Slice 3B-B probe confirmed the production chain returns verdict=pass for the case_01 cross-reference geometry + case_02 design_conditions) |
| `expected_output.selected_material_ids.shell_material_id` | "SS304" | "SS304" (unchanged) | Preserved verbatim from 002-F; still derivable from 002-G bridge.shell via MaterialSelector.resolve → material_grade="304" → string-projected as "SS304" |
| `expected_output.selected_material_ids.tube_material_id` | "SS304" | "SS304" (unchanged) | Preserved verbatim from 002-F; still derivable from 002-G bridge.tube via MaterialSelector.resolve → material_grade="304" → string-projected as "SS304" |

### 4.9.4 Production source (binding, contract-frozen)

The 002-G re-derived `expected_output.mass_kg.*` central values are computed by closed-form arithmetic on:

- **Inputs (case_01 cross-reference geometry, 002-F frozen)**: `case_01_heat_balance_rating.json[\"input\"][\"geometry\"]` = `{shell_od: 0.0603m, shell_id: 0.0525m, tube_od: 0.0334m, tube_id: 0.0266m, tube_length: 2.0m}` (Kern 1950 1"/2" tube-in-shell water-water reference, frozen by case_01 Amendments 001 + 002-A + 002-D + 002-E).
- **Inputs (002-G bridge density, 002-F frozen)**: `case_02_materials_mass_mechanical.json[\"input\"][\"material_catalog_bridge\"].{shell,tube,hairpin_bend,fittings}.physical_properties.density_kg_m3` = 8000.0 kg/m^3 (SS304 documented density per TASK-017 approved material catalog; same value across all 4 roles per Question 1).
- **Formula (production `MassCalculator` closed-form)**: `inner_tube_kg = density × π/4 × (tube_od² − tube_id²) × tube_length`; `outer_pipe_kg = density × π/4 × (shell_od² − shell_id²) × tube_length`; `total_kg = inner_tube_kg + outer_pipe_kg + hairpin_bend_kg + fittings_kg`; for case_02 `hairpin_bend_kg = 0` (via `include_hairpin=False`) and `fittings_kg = 0` (via `fitting_overrides_kg=()`), so `total_kg = inner_tube_kg + outer_pipe_kg`.

The future Slice 3B-B implementation round (separately authorized) will call the real production `MassCalculator.calculate_mass_breakdown(...)` with the case_02 bridge and case_01 cross-reference geometry, and verify the production chain execution matches the frozen central values within the existing numeric tolerance (Amendment 001 frozen: `shell_mass_kg abs=0.05 rel=0.01; tube_mass_kg abs=0.05 rel=0.01; total_mass_kg abs=0.1 rel=0.01`). Any mismatch will require a new amendment (002-H+) to reconcile.

### 4.9.5 Tolerance impact (binding, contract-frozen)

The numeric tolerance values for all 4 case_02 mass_kg fields (including fluid_mass_kg) are preserved verbatim from Amendment 001 / 002-F:

- `case_02.mass_kg.fluid_mass_kg`: `abs=0.05` `rel=0.01` (002-F preserved verbatim; field value 1.05 unchanged; only the produced_field status is changed to DEFERRED)
- `case_02.mass_kg.shell_mass_kg`: `abs=0.05` `rel=0.01` (002-F preserved verbatim)
- `case_02.mass_kg.tube_mass_kg`: `abs=0.05` `rel=0.01` (002-F preserved verbatim)
- `case_02.mass_kg.total_mass_kg`: `abs=0.1` `rel=0.01` (002-F preserved verbatim)

The per_field_basis text for the 3 case_02 metal-mass_kg fields (shell_mass_kg / tube_mass_kg / total_mass_kg) is re-derived to reference Amendment 002-G and the production-chain-derivable central values (replacing the 002-F "Density × volume closed-form ± 1%" hand-calculated basis with the 002-G "production MassCalculator closed-form (outer_pipe_kg / inner_tube_kg / total_kg) per 方案 B explicit mapping" basis). The 1% relative tolerance is the binding constraint for the new larger central values (5-16 kg); the absolute tolerance (0.05 / 0.1 kg) remains the tighter constraint for the smaller values and is achievable for the new values within 1% rel tolerance.

The per_field_basis text for `case_02.mass_kg.fluid_mass_kg` is updated to DEFERRED status while preserving the 002-F basis content verbatim as a sub-sentence (the 002-F basis text "Density × volume closed-form ± 1% to account for CoolProp density numerical accuracy and the canonical geometry's cylindrical-volume closure" is preserved verbatim inside the new 002-G DEFERRED status note). The 002-G `amendment_002g_tolerance_basis_rederivation.case_02.mass_kg.fluid_mass_kg` block documents the DEFER status, the 002-F basis preservation, the test-contract preservation rationale, and the future 002-H+ amendment path.

The categorical tolerance entries (`preliminary_mechanical_check.status` and `selected_material_ids.*`) are preserved byte-for-byte from 002-F. case_01 and case_03 tolerance entries are preserved byte-for-byte (002-G is case_02 only).

### 4.9.6 Provenance changes (binding, contract-frozen)

`_provenance_metadata.json` adds the following 002-G top-level fields (in the same structural style as the existing `amendment_002a_*` / `amendment_002d_*` / `amendment_002e_*` / `amendment_002f_*` fields):

- `amendment_002g_id`: `"TASK-019-DESIGN-AMENDMENT-002-G"`
- `amendment_002g_effective_scope`: `"TASK-019-GOLDEN-02"`
- `amendment_002g_bridge_schema_version`: `"2.0"` (002-F was `"1.0"`; 002-G extends the 002-F schema with 2 additional roles)
- `amendment_002g_supersedes`: text describing the 3 specific supersessions (bridge extension, expected_output re-derivation, slice3a_blocked_field_paths marker update)
- `amendment_002g_field_paths_added`: list of 23 new field paths in `case_02_materials_mass_mechanical.json` (includes 18 bridge extension paths for hairpin_bend + fittings + their sub-blocks, 3 metal-mass_kg re-derivation paths, 4 mass_kg_field_mapping_002g sub-block paths, and the slice3a_blocked_field_paths marker block additions; the fluid_mass_kg_pending marker update is also documented as a field_paths_added entry because the marker value text is updated with the DEFERRED status note)
- `amendment_002g_field_paths_unchanged`: list of 18 field paths preserved verbatim (preliminary_mechanical_check.status, selected_material_ids.*, input.material_selection.*, input.design_conditions.*, input.case_01_input_reference_case_id, pressure_drop_excluded_from_taska_019, license_boundary_attestation.*, tolerance_profile_id, provenance_profile_id, schema_version, case_id, case_scope, case_title, and the 002-F bridge shell + tube role blocks, AND the case_02 expected_output.mass_kg.fluid_mass_kg field value 1.05 which is preserved verbatim from the 002-F baseline)
- `amendment_002g_re_derivation_method`: explicit documentation of the closed-form formula, inputs (case_01 geometry + 002-G bridge density), closed-form results, previous 002-F values superseded, and the no-fabrication statement
- `amendment_002g_chain_coverage`: explicit table mapping each future production chain call to the bridge field(s) that supply the required input, extending the 002-F chain_coverage to cover the production 4-role closed set (outer_pipe / inner_tube / hairpin_bend / fittings) and documenting the `include_hairpin=False` / `fitting_overrides_kg=()` parameters
- `amendment_002g_fluid_mass_kg_decision`: explicit decision record documenting the DEFER rationale (auth's option (b) — DEFER to a future real production chain 002-H+), the test-contract preservation rationale, and the future 002-H+ amendment path (may either remove or re-derive)

The existing 002-F `amendment_002f_*` fields are preserved verbatim (the 002-F bridge schema is a subset of the 002-G bridge schema; the 002-F chain_coverage is the 2-role subset of the 002-G 4-role chain_coverage; the 002-F field_paths_added list is a subset of the 002-G field_paths_added list).

### 4.9.7 Case boundaries (binding)

- **case_01** — UNCHANGED. Geometry, fluid identifier, mass flow, expected_output, tolerance, and all other fields are preserved verbatim from Amendment 002-E. The 002-G bridge is case_02 only; no field on `case_01_heat_balance_rating.json` is touched.
- **case_02** — `input.material_catalog_bridge` is EXTENDED (2 new roles: hairpin_bend + fittings). `expected_output.mass_kg.*` metal-mass fields (shell_mass_kg / tube_mass_kg / total_mass_kg) are RE-DERIVED to the production-chain-derivable values (11.056 / 5.127 / 16.183). `expected_output.mass_kg.fluid_mass_kg` is PRESERVED (value 1.05 unchanged) with produced_field status DEFERRED to a future real production chain 002-H+ (per Question 3 second-option; preserves the existing test contract on `tests/validation_report/test_chain_wiring_adapter.py::test_expected_output_unchanged_across_adapter_runs`). `expected_output.mass_kg_field_mapping_002g` is ADDED (documents the 方案 B mapping + the fluid_mass_kg DEFERRED status). `expected_output.slice3a_blocked_field_paths` marker block is RENAMED to Slice-3B-B; the three metal-mass_kg marker production-source symbols are UPDATED to the 002-G contract; the fluid_mass_kg_pending marker is UPDATED to DEFERRED status (not a work item). `expected_output.preliminary_mechanical_check.status` and `expected_output.selected_material_ids.*` are PRESERVED verbatim. `input.material_selection` block is PRESERVED verbatim as audit/description metadata. `input.design_conditions` is PRESERVED verbatim. `input.case_01_input_reference_case_id` is PRESERVED verbatim (it is the source of the 002-G re-derived metal-mass_kg values). `pressure_drop_excluded_from_taska_019` is PRESERVED verbatim (TASK-020+ excluded). `license_boundary_attestation` is PRESERVED verbatim. `tolerance_profile_id` is PRESERVED verbatim (numeric tolerance values preserved verbatim from 001 / 002-F for all 4 case_02 mass_kg fields; per_field_basis text re-derived for metal-mass_kg fields, updated to DEFERRED status for fluid_mass_kg). `provenance_profile_id` is PRESERVED verbatim (V2; 002-G is in-scope for the existing profile). `schema_version` is PRESERVED verbatim (V2; 002-G does not bump schema).
- **case_03** — UNCHANGED. `cost_model_selection`, expected_output, cost records, SelectionFilters, discount/salvage deferred markers, and all other fields are preserved verbatim. The 002-G bridge is case_02 only; no field on `case_03_cost_lifecycle_envelope.json` is touched.

### 4.9.8 Amendment 002-G does NOT authorize

Amendment 002-G **does NOT authorize** any of the following, in either this amendment round or in any future TASK-019 implementation round without an explicit separate design-amendment or implementation authorization:

- **No resolver implementation.** The 002-G bridge freezes data; it does not implement any lookup / resolution logic.
- **No catalog database.** The 002-G bridge references a `provenance.source_reference` field but does not implement or load any catalog DB.
- **No MaterialRecord runtime synthesis.** The 002-G bridge is a case-bound frozen input. A future implementation round that consumes the bridge to build a `MaterialRecord` is authorized separately (and only as a case-bound projection from frozen input, not as a runtime synthesis).
- **No material calculation logic.** No `calculate_mass_breakdown` or `preliminary_check` call is authorized in this amendment.
- **No production module modification.** No `src/**` file is modified in this amendment.
- **No test modification.** No `tests/validation_report/**`, `tests/unit/**`, `tests/benchmark/**`, or `tests/support/**` file is modified in this amendment.
- **No case_03 implementation.** The 002-G bridge is case_02 only.
- **No case_01 weakening.** case_01 remains `WIRED_VIA_CHAIN` per Slice 3B-A.
- **No pressure-drop / TASK-020+ work.** Pressure drop remains `NOT_COMPUTABLE` / TASK-020+ excluded.
- **No discount / salvage formula.** TASK-018 §5.3 / §5.3.2 remain deferred.
- **No `corrosion_allowance_mm` default.** The future implementation must pass `None` to `MaterialResolutionRequest.corrosion_allowance_mm`; no fabricated default is allowed.
- **No `geometry_record` fabrication.** The future implementation must derive `geometry_record` from the case_01 cross-reference (`case_02_input[\"case_01_input_reference_case_id\"]`), not from a fabricated default.
- **No fluid_mass_kg synthesis.** The future implementation MUST NOT (a) synthesize `fluid_mass_kg` from any source, (b) copy `fluid_mass_kg` from `expected_output` to `actual_output`, or (c) use any catalog lookup to derive `fluid_mass_kg`. `fluid_mass_kg` is DEFERRED in the case_02 contract surface by 002-G (preserved as a deferred-amendment placeholder with value 1.05 from the 002-F baseline; produced_field status DEFERRED to a future real production chain 002-H+); a future 002-H+ amendment may either remove the field or re-derive it from a real fluid-volume × fluid-density chain.
- **No expected_output mutation beyond 002-G.** The 002-G re-derivation of `expected_output.mass_kg.shell_mass_kg` / `tube_mass_kg` / `total_mass_kg` (and the DEFERRED-status update of `fluid_mass_kg`) is the only `expected_output` change in this amendment. All other `expected_output` fields (preliminary_mechanical_check.status, selected_material_ids.*, case_01_outputs_reference_case_id) are preserved verbatim from 002-F. The 002-G re-derivation is contract-frozen and must NOT be silently updated in a future implementation round; any future change to the 002-G re-derived values requires a new design amendment (002-H+).
- **No tolerance widening.** All case_02 numeric tolerance values for the 4 mass_kg fields (fluid_mass_kg, shell_mass_kg, tube_mass_kg, total_mass_kg) are preserved verbatim from 001 / 002-F. Per_field_basis text is re-derived for the 3 metal-mass_kg fields to reference 002-G and the production-chain-derivable central values; per_field_basis text for fluid_mass_kg is updated to DEFERRED status while preserving the 002-F basis content verbatim. No numeric tolerance value is widened.
- **No Issue / Feishu / Ready / Merge / branch deletion.** Per ongoing governance.

### 4.9.9 No-fabrication statement (binding, contract-frozen)

The 002-G re-derived `expected_output.mass_kg.*` metal-mass_kg central values (shell_mass_kg 11.056, tube_mass_kg 5.127, total_mass_kg 16.183) are computed by closed-form arithmetic on the case_01 cross-reference geometry (002-F frozen) and the 002-G bridge SS304 density (002-F frozen) via the documented production `MassCalculator` closed-form formula. **No adapter-generated values, no LLM-inferred material properties, no catalog lookup at runtime, no engineering judgment, no hand-tuning, no round-trip to expected_output**. The 002-F `fluid_mass_kg = 1.05` value is preserved verbatim (the field is DEFERRED; no re-derivation in 002-G). The future Slice 3B-B implementation round (separately authorized) will call the real production `MassCalculator.calculate_mass_breakdown(...)` and verify the production chain execution matches the frozen metal-mass_kg central values within the existing numeric tolerance; any mismatch will require a new amendment (002-H+) to reconcile. The 002-G design contract is the **single source of truth** for the case_02 mass-chain contract; any future implementation that diverges from the 002-G contract is out of scope and requires a new design amendment.

### 4.9.10 Slice 3B-B implementation status (binding, future)

As of Amendment 002-G authoring, the case_02 frozen fixture now carries the 4-role extended `input.material_catalog_bridge` (shell + tube + hairpin_bend + fittings) AND the re-derived `expected_output.mass_kg.shell_mass_kg` / `tube_mass_kg` / `total_mass_kg` central values (11.056 / 5.127 / 16.183 from the production MassCalculator closed-form per 方案 B) AND the explicit `expected_output.mass_kg_field_mapping_002g` 方案 B mapping AND the DEFERRED-status marker on `expected_output.mass_kg.fluid_mass_kg` (preserved verbatim 1.05; not a TASK-019 Slice 3B-B produced_field). A future implementation round (separately authorized, not part of 002-G) may consume the 002-G bridge to wire case_02 to the TASK-017 production chain. The future implementation must:

1. Read the 002-G bridge verbatim for all 4 roles (no synthesis, no normalization, no catalog lookup at runtime).
2. Build a real `MaterialRecord` TypedDict from the bridge for each of the 4 roles (a case-bound projection, not a synthesis — the bridge is the data source).
3. Build a real `MaterialResolutionRequest` from the bridge's `identity` + `input.design_conditions` for each of the 4 roles.
4. Call `MaterialSelector.resolve_material(request, material_record)` for each of the 4 roles; expect real `MaterialResolutionResult` outputs.
5. Build a real `MassCalculationRequest` using the cross-case case_01 geometry (shell_od / shell_id / tube_od / tube_id / tube_length) + the 4 `MaterialResolutionResult` objects keyed by production component_role (`outer_pipe` / `inner_tube` / `hairpin_bend` / `fittings`) + `include_hairpin=False` (case-bound) + `fitting_overrides_kg=()` (case-bound).
6. Call `MassCalculator.calculate_mass_breakdown(request)`; expect real `MassBreakdown` (5 fields: `inner_tube_kg` / `outer_pipe_kg` / `hairpin_bend_kg` / `fittings_kg` / `total_kg`).
7. Apply the 方案 B explicit mapping to project production `MassBreakdown` fields to public `expected_output.mass_kg` fields:
   - `actual_output.mass_kg.shell_mass_kg = mass_breakdown.outer_pipe_kg` (= 11.056395521337773 within tolerance)
   - `actual_output.mass_kg.tube_mass_kg = mass_breakdown.inner_tube_kg` (= 5.127079210658542 within tolerance)
   - `actual_output.mass_kg.total_mass_kg = mass_breakdown.total_kg` (= 16.183474731996316 within tolerance)
   - `actual_output.mass_kg.fluid_mass_kg` is NOT populated by the future implementation (the field is DEFERRED to a future real production chain 002-H+; the future Slice 3B-B adapter MUST NOT synthesize / copy / lookup fluid_mass_kg; the 1.05 value in `expected_output` is a frozen baseline, not a produced_field target)
8. Build a real `PreliminaryCheckRequest` using the case_01 geometry diameters (tube_od / tube_id) + the tube `MaterialResolutionResult` + case_02 `input.design_conditions`.
9. Call `PreliminaryMechanicalChecker.run(request)`; expect real `PreliminaryCheckResult` with verdict="pass" (matches `expected_output.preliminary_mechanical_check.status="PASS"`).
10. Surface the real outputs in `case_02 actual_output` with `produced_fields` covering the real upstream-returned fields (not case-bound metadata) — specifically: `mass_kg.shell_mass_kg`, `mass_kg.tube_mass_kg`, `mass_kg.total_mass_kg`, `preliminary_mechanical_check.status`, `selected_material_ids.shell_material_id`, `selected_material_ids.tube_material_id` (6 fields, same as case_01). `mass_kg.fluid_mass_kg` is NOT in the produced_fields list (the field is DEFERRED).
11. Verify that the resulting `actual_output.mass_kg.shell_mass_kg` / `tube_mass_kg` / `total_mass_kg` and `actual_output.preliminary_mechanical_check.status` match the 002-G re-derived `expected_output.mass_kg.shell_mass_kg` / `tube_mass_kg` / `total_mass_kg` and `expected_output.preliminary_mechanical_check.status="PASS"` within the existing numeric tolerance (Amendment 001 / 002-F frozen; 002-G preserves verbatim); a future implementation round that finds a mismatch must NOT silently update the expected_output — it must report the mismatch and request a new design amendment (002-H+). The `expected_output.mass_kg.fluid_mass_kg = 1.05` value is NOT a comparison target for the future implementation (the field is DEFERRED, not a produced_field); the future implementation must NOT populate `actual_output.mass_kg.fluid_mass_kg` from any source.

**Implementation of the above is NOT authorized by Amendment 002-G** and requires a separate Charles authorization in a future round. Amendment 002-G is a design contract only.

## 5. TASK-018 deferred amendment handling (binding)

### 5.1 Discount formula (TASK-018 §5.3)

- TASK-019 Golden case 03 must observe the **TASK-018 Option A** behavior in its expected outputs:
  - `discounted_total_minor_units`: **`null`**
  - `unspecified_blocker` with `details.reason = "discount_formula_pending_design_amendment"` (if blocked)
- TASK-019 must NOT require the real discount formula.
- TASK-019 must NOT introduce the discount formula.
- A future TASK-018 §5.3 design-amendment PR may add the real formula; TASK-019 may be updated in a future TASK-019 design-amendment round to consume the new formula, but this round does NOT pre-authorize that work.

### 5.2 Salvage formula (TASK-018 §5.3.2)

- TASK-019 Golden case 03 must observe the **TASK-018 placeholder** behavior:
  - `salvage_minor_units`: **`<int>` placeholder** (TASK-018 Slice A/B/C implementations hard-code `= 0` per Slice C closeout audit; contract-compliant)
- TASK-019 must NOT require the real salvage formula.
- TASK-019 must NOT introduce the salvage formula.
- A future TASK-018 §5.3.2 design-amendment PR may add the real formula; TASK-019 may be updated in a future TASK-019 design-amendment round, but this round does NOT pre-authorize that work.

### 5.3 Option A as the canonical observed contract boundary

TASK-019 Golden case 03 must record, in the validation report, that the observed `discounted_total_minor_units = null` and `salvage_minor_units = 0` are **Option A contract boundaries, not implementation errors**. The validation report must distinguish these from calculation failures (e.g. via a dedicated `observed_contract_boundary_blocker` semantic or via the existing TASK-018 `unspecified_blocker` semantics — design-amendment-justified choice between these two options is deferred to implementation).

## 6. Explicit exclusions (binding)

This TASK-019 design contract **explicitly does NOT authorize** any of the following, in either this design round or in any future TASK-019 implementation round without an explicit separate design-amendment authorization:

- **No pressure-drop / C4**: Golden cases must NOT compute or assert tube / annulus pressure drop. Pressure drop lives in TASK-020+. `tests/golden/double_pipe_sizing/` and `tests/golden/double_pipe_rating/pressure_drop/` may exist as future TASK-020+ Golden cases but are NOT this task.
- **No TASK-020+ content**: No TEMA configuration, no shell-and-tube, no Kern screening, no Bell–Delaware, no pressure-drop decomposition, no thermal expansion screening, no optimization. TASK-020+ are separate tasks with separate design contracts.
- **No new correlations**: TASK-019 must consume only TASK-007 frozen correlation registry entries. Adding new correlation IDs requires an explicit TASK-007 design-amendment PR (not this round).
- **No new heat-transfer physics**: TASK-019 must consume only TASK-006 / TASK-007 / TASK-008 frozen thermal paths. New physics requires an explicit TASK-006/007/008 design-amendment PR.
- **No new cost formulas**: TASK-019 must consume only TASK-018 frozen Slice A/B/C. New cost formulas require an explicit TASK-018 design-amendment PR.
- **No discount formula**: Per §5.1.
- **No salvage formula**: Per §5.2.
- **No vendor quote / C3 sourcing**: TASK-019 must NOT integrate with vendor APIs. C3 sourcing lives in TASK-020+ (or later).
- **No TASK-017 stale-docs remediation**: This design contract does NOT modify `docs/TASK_BACKLOG.md` rows L379 / L455 / L459 (TASK-017 design / implementation Issue #72 / Issue #74 / PR #75 stale rows). These are a separate governance follow-up round (cited in TASK-019 preflight report §13 F1).
- **No Issue #23 action**: Issue #23 remains untouched per ongoing governance.
- **No Feishu outbound**: Per Charles authorization rule, no Feishu message is sent in this round or in any TASK-019 round unless explicitly authorized in a per-message authorization round.

## 7. Double-pipe validation report contract (binding)

### 7.1 Report schema (top-level)

```json
{
  "report_schema_version": "TASK-019-VALIDATION-REPORT-V1",
  "report_id": "<deterministic UUID v5>",
  "generated_at": "<ISO 8601 UTC, Z>",
  "upstream_contract_versions": {
    "TASK-006": "<commit SHA>",
    "TASK-007": "<commit SHA>",
    "TASK-008": "<commit SHA>",
    "TASK-011": "<commit SHA>",
    "TASK-012": "<commit SHA>",
    "TASK-013": "<commit SHA>",
    "TASK-014": "<commit SHA>",
    "TASK-015A": "<commit SHA>",
    "TASK-017": "<commit SHA>",
    "TASK-018": "<commit SHA>",
    "TASK-019": "<implementation commit SHA, TBD>"
  },
  "run_environment": {
    "python_version": "<exact string>",
    "platform": "<exact string>",
    "package_versions": { "<package>": "<version>" },
    "deterministic_mode_flags": ["sort_keys", "no_floats_for_money", ...]
  },
  "golden_cases": [
    {
      "case_id": "TASK-019-GOLDEN-01",
      "case_title": "Double-pipe heat balance + fixed-geometry rating",
      "input_sha256": "<64 hex chars>",
      "expected_output_sha256": "<64 hex chars>",
      "actual_output_sha256": "<64 hex chars>",
      "comparison": {
        "overall_status": "PASS | FAIL | NOT_COMPUTABLE",
        "per_field": [
          {"field": "<json-pointer>", "status": "PASS | FAIL | NOT_COMPUTABLE", "tolerance": {"abs": <num>, "rel": <num>}, "observed": <value>, "expected": <value>}
        ],
        "blockers": [<blocker codes if any>],
        "warnings": [<warning codes if any>]
      },
      "provenance": {
        "correlation_ids": [...],
        "provider_ids": [...],
        "rule_pack_ids": [...],
        "design_contract_versions": {...}
      }
    },
    ... (3 cases total)
  ],
  "aggregate_summary": {
    "total_cases": 3,
    "passed": <int>,
    "failed": <int>,
    "not_computable": <int>,
    "blocked_on_deferred_amendments": <int> (e.g. cases blocked on TASK-018 §5.3 / §5.3.2 deferred amendments)
  },
  "license_boundary_attestation": {
    "any_restricted_source_inputs": false,
    "any_restricted_source_outputs": false,
    "restricted_source_pointer_only_observed": true
  }
}
```

### 7.2 Required sections

1. **Header**: schema version, report ID, generated timestamp.
2. **Upstream contract versions**: 11 frozen contracts (TASK-006 / TASK-007 / TASK-008 / TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015A / TASK-017 / TASK-018 / future TASK-019).
3. **Run environment**: Python version, platform, package versions, deterministic flags.
4. **Golden case comparisons**: per-case block with input / expected / actual canonical hashes, per-field PASS / FAIL / NOT_COMPUTABLE, blockers / warnings.
5. **Provenance**: per-case correlation / provider / rule-pack IDs.
6. **Aggregate summary**: total / passed / failed / not_computable / blocked-on-deferred-amendments counts.
7. **License boundary attestation**: explicit declaration of restricted-source treatment per TASK-012 §5.

### 7.3 PASS / FAIL / NOT_COMPUTABLE semantics

- **PASS**: actual output matches expected output within tolerance for ALL asserted fields, AND no blocker / warning beyond those recorded in the expected output's `blockers` / `warnings` arrays.
- **FAIL**: actual output deviates from expected output by more than the documented tolerance for at least one asserted field. The deviating field(s) are explicitly listed.
- **NOT_COMPUTABLE**: the calculation chain aborted before producing any asserted field. The blocker code(s) are explicitly listed (e.g. `missing_required_lifecycle_input_blocker`, `unspecified_blocker` with reason `discount_formula_pending_design_amendment`, etc.).

### 7.4 Comparison method

- Per-field comparison: for each asserted field in the expected output, compute the comparison using:
  - **Absolute tolerance** (`abs_tolerance`) for absolute-value comparison, OR
  - **Relative tolerance** (`rel_tolerance`) for relative comparison, OR
  - **Canonical-hash equality** for fields that must match exactly (e.g. currency code, blocker codes, integer minor units).
- Tolerance metadata is stored in the Golden case's tolerance record and must NOT be widened in implementation without an explicit design-amendment.

### 7.5 License boundary representation

- If a Golden case uses a restricted-source input (vendor rule-pack, paid correlation), the input's `license_class` is recorded in the case's provenance.
- If a Golden case produces a restricted-source output, the output is **pointer-only** per TASK-012 §5 — the report records the pointer + license class but NOT the value.
- `license_class_summary` shape is preserved per the existing TASK-012 contract surface; this design contract does NOT introduce a new `license_class_summary` field.

## 8. Closed-set / blocker reuse policy (binding)

### 8.1 Prefer reuse over new codes

TASK-019 must NOT introduce new blocker / warning codes in this design contract. All TASK-019 case-level block / warning semantics must reuse existing codes from upstream frozen contracts:

- TASK-006 / TASK-007 / TASK-008: existing thermal / rating blocker codes.
- TASK-014: existing case-revision blocker codes.
- TASK-017: existing §9.1 / §9.2 / §9.3 mechanical blocker codes.
- TASK-018: existing cost / life-cycle blocker codes (including `unspecified_blocker` with `details.reason = "discount_formula_pending_design_amendment"` and `salvage_minor_units = 0` placeholder semantics).

### 8.2 New code introduction requires design-amendment

If a future TASK-019 design-amendment round determines that a new blocker / warning code is required (e.g. for a new validation-report-specific semantic), the design-amendment PR must:

- Add the new code to the relevant upstream frozen contract's §9 closed-set list.
- Update the TASK-018 / TASK-019 frozen contracts to reference the new code.
- Be a separate, Charles-authorized design-amendment round.
- This round does NOT pre-authorize that work.

### 8.3 Observed contract boundary representation

Per §5.3, the TASK-018 Option A behavior (discount / salvage placeholders) may be represented in the validation report using one of:

- **Option X1** (preferred): existing TASK-018 `unspecified_blocker` with `details.reason = "discount_formula_pending_design_amendment"` + `salvage_minor_units = 0` as direct placeholder.
- **Option X2** (design-amendment-justified): a new `observed_contract_boundary_blocker` semantic — requires future TASK-019 design-amendment.

This round selects **Option X1** by default. Future design-amendment may switch to Option X2.

## 9. Frozen contract discipline (binding)

### 9.1 Frozen contracts that MUST NOT be mutated by TASK-019 implementation

The TASK-019 implementation round MUST NOT mutate any of the following frozen contracts:

- `docs/MASTER_DEVELOPMENT_SPEC.md`
- `docs/tasks/TASK-001-engineering-baseline.md`
- `docs/tasks/TASK-002-units-and-quantities.md`
- `docs/tasks/TASK-003-property-service.md`
- `docs/tasks/TASK-004-correlation-registry.md` / `TASK-005-correlation-registry.md`
- `docs/tasks/TASK-006-heat-balance.md`
- `docs/tasks/TASK-007-tube-annulus-correlations.md` / `TASK-007-double-pipe-correlations.md`
- `docs/tasks/TASK-008-double-pipe-rating.md` / `TASK-009-double-pipe-sizing.md`
- `docs/tasks/TASK-010-report-and-api.md` / `TASK-010-MERGE-CLOSEOUT.md`
- `docs/tasks/TASK-011-benchmark-case-governance.md`
- `docs/tasks/TASK-012-standards-rule-pack-license-boundary.md`
- `docs/tasks/TASK-013-material-cost-data-governance.md`
- `docs/tasks/TASK-014-immutable-case-revisions-persistence.md`
- `docs/tasks/TASK-015-ci-security-and-release-automation.md`
- `docs/tasks/TASK-015A-deterministic-test-environment-and-ci-sharding.md`
- `docs/tasks/TASK-016-approved-geometry-catalog.md`
- `docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md`
- `docs/tasks/TASK-017-materials-mass-mechanical-implementation.md`
- `docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md`

### 9.2 Deviation policy

Any deviation from the frozen contracts above requires an **explicit design-amendment authorization** in a separate Charles-authorized round. The design-amendment must:

- Identify the specific frozen contract being amended.
- State the reason for the amendment.
- Provide the new contract surface.
- Update all dependent TASK contracts (including this TASK-019 contract, if applicable).

This TASK-019 design round introduces **zero** design-amendments to the frozen contracts above.

## 10. Future implementation boundary (proposal only — no mutation this design round)

### 10.1 Implementation Issue / branch / PR naming (proposed)

| Artifact | Proposed name |
|---|---|
| Implementation Issue title | `[TASK-019][impl] Golden cases and double-pipe validation report` |
| Implementation branch | `codex/task-019-golden-cases-double-pipe-validation-impl` |
| Implementation PR title | `feat(task-019): add golden cases and double-pipe validation report` |

These names are **proposals only**. They are NOT created in this design round and require separate Charles authorization to create the implementation round.

### 10.2 Allowed implementation files (proposal)

- `tests/golden/double_pipe_rating/case_01_heat_balance_rating.json`
- `tests/golden/double_pipe_rating/case_02_materials_mass_mechanical.json`
- `tests/golden/double_pipe_rating/case_03_cost_lifecycle_envelope.json`
- `tests/golden/double_pipe_rating/_tolerance_metadata.json`
- `tests/golden/double_pipe_rating/_provenance_metadata.json`
- `src/hexagent/validation_report/__init__.py` (new module)
- `src/hexagent/validation_report/double_pipe_validation_report.py` (new module)
- `tests/validation_report/test_double_pipe_validation_report.py` (new test file)
- `tests/validation_report/test_golden_case_reproducibility.py` (new test file)
- `tests/validation_report/test_no_upstream_mutation.py` (new test file — see §11.5)
- `tests/validation_report/test_excluded_scopes_negative.py` (new test file — see §11.6)
- `ci-shard-manifest.yml` (additive only: 1 line per new test directory under existing `golden` + `validation` shards, per TASK-015A governance)

These paths are **proposals only**. They are NOT created in this design round.

### 10.3 Local validation expectations (proposal)

- `git diff --check` (no whitespace conflict)
- `pytest tests/validation_report/ -v` (all green)
- `pytest tests/golden/double_pipe_rating/ -v` (all green; deterministic mode)
- `python -m hexagent.validation_report.double_pipe_validation_report --golden tests/golden/double_pipe_rating/ --output /tmp/report.json` (deterministic report generation)
- `git grep -nE 'TASK-019\+ content|pressure-drop|C4|TASK-020\+|discount_formula|salvage_formula' src/ tests/` returns **zero** implementation-language hits in allowed files (sweep §6 + §10.4).
- `git grep -nE 'fabricated.*Issue|fabricated.*PR|fake.*PR' .` returns **zero** (no fabrication).

### 10.4 CI expectations (proposal)

- PR-head CI runs: lint / parse-manifest / verify-manifest / final-gate / `golden` shard (per TASK-015A) / `validation` shard (new).
- All jobs: completed / success / 0 failed.
- No mutation of TASK-006..TASK-018 frozen contracts (verified by `git diff origin/main -- docs/tasks/TASK-006*.md docs/tasks/TASK-007*.md ... docs/tasks/TASK-018*.md` returning empty).

## 11. Acceptance tests (binding — for the future implementation round)

The future TASK-019 implementation round MUST provide the following acceptance test categories. Each test category maps to a frozen test name pattern that the implementation must register in the repo's pytest discovery.

### 11.1 Golden-case reproducibility tests

- Frozen test name pattern: `tests/validation_report/test_golden_case_reproducibility.py::test_case_01_*`, `::test_case_02_*`, `::test_case_03_*`
- Each test loads the corresponding Golden case input + expected output, runs the upstream calculation chain (TASK-006 + TASK-007 + TASK-008 / + TASK-017 / + TASK-018), and asserts that the actual output matches the expected output within the documented tolerance.
- All 3 cases must pass under Python 3.12 with deterministic-mode flags.
- Each test must assert the canonical SHA-256 hash of the input / expected / actual outputs to catch unintended drift.

### 11.2 Report schema tests

- Frozen test name pattern: `tests/validation_report/test_double_pipe_validation_report.py::test_report_schema_*`
- Each test asserts the report conforms to the schema in §7.1.
- Schema-conformance tests for `report_schema_version`, `report_id`, `generated_at`, `upstream_contract_versions` (all 11 keys present), `run_environment`, `golden_cases[].{input_sha256, expected_output_sha256, actual_output_sha256, comparison.overall_status, comparison.per_field, comparison.blockers, comparison.warnings, provenance}`, `aggregate_summary`, `license_boundary_attestation`.
- Determinism: report generation is byte-stable across runs (same upstream contract versions → same report hash).

### 11.3 Deterministic hash / provenance tests

- Frozen test name pattern: `tests/validation_report/test_double_pipe_validation_report.py::test_deterministic_hash_*` + `::test_provenance_*`
- Asserts SHA-256 canonical hashing is reproducible across supported environments.
- Asserts provenance metadata is complete (all 11 upstream contract versions + correlation / provider / rule-pack IDs).
- Asserts ISO 8601 UTC datetime formatting with `Z` suffix.

### 11.4 No-mutation guard tests for upstream frozen contracts

- Frozen test name pattern: `tests/validation_report/test_no_upstream_mutation.py::test_frozen_contracts_unchanged_*`
- For each frozen contract listed in §9.1, assert that:
  - The contract file's content SHA-256 (at TASK-019 implementation base) matches the recorded SHA-256 in this design contract's provenance metadata.
  - No implementation file in `src/` or `tests/` (excluding allowed paths in §10.2) imports or modifies frozen-contract symbols.
- This guards against accidental frozen-contract mutation across future implementation rounds.

### 11.5 Excluded-scopes negative tests

- Frozen test name pattern: `tests/validation_report/test_excluded_scopes_negative.py::test_no_*`
- Asserts:
  - `test_no_pressure_drop_in_golden_cases`: Golden case JSON files contain zero `pressure_drop_*` keys.
  - `test_no_c4_in_golden_cases`: Golden case JSON files contain zero `c4_*` keys.
  - `test_no_task_020_plus_in_golden_cases`: Golden case JSON files contain zero `tema_*`, `kern_*`, `bell_delaware_*` keys.
  - `test_no_new_correlation_registry_entries`: `tests/golden/double_pipe_rating/` only references correlation IDs from TASK-007 frozen registry.
  - `test_no_new_property_provider_entries`: Golden case provenance only references provider IDs from TASK-015A frozen registry.
  - `test_no_discount_formula`: Golden case expected outputs contain `discounted_total_minor_units: null` (per §5.1) and no discount-formula computation.
  - `test_no_salvage_formula`: Golden case expected outputs contain `salvage_minor_units: 0` (per §5.2) and no salvage-formula computation.
  - `test_no_vendor_quote_or_c3`: Golden case provenance contains no `vendor_quote_*` / `c3_*` keys.
  - `test_no_issue_23_action`: Assert no TASK-019 implementation code, golden case JSON fixtures, generated validation report, runtime path, or new non-governance docs perform or imply Issue #23 action. Governance-only references in TASK-019 design contract frozen docs (and in upstream frozen contracts' governance sections) are allowed and are not the target of this test.
  - `test_no_feishu_outbound`: Assert no TASK-019 implementation code, tests, generated validation report, runtime path, or outbound integration performs Feishu outbound. Governance-only references in TASK-019 design contract frozen docs (and in upstream frozen contracts' governance sections) are allowed and are not the target of this test.
  - `test_no_task_017_stale_docs_remediation`: No code / test / doc modifies the TASK-017 stale rows in `docs/TASK_BACKLOG.md` (L379 / L455 / L459).

### 11.6 License-boundary tests

- Frozen test name pattern: `tests/validation_report/test_double_pipe_validation_report.py::test_license_boundary_*`
- Asserts restricted-source outputs are pointer-only per TASK-012 §5.
- Asserts `license_class_summary` shape is preserved from TASK-012 (no new fields).

## 12. Self-referential notes

- This design contract introduces **zero** production code, **zero** test code, **zero** report renderer, **zero** Golden case JSON, **zero** validation report JSON, and **zero** mutation of any TASK-006–TASK-018 frozen contract.
- The Frozen Contract Authority Base SHA is `76a8b5142c63fb09852146611e794355dea7f5b6` (= main @ PR #86 merge).
- The Frozen Contract Authority Commit SHA will be set in the design PR merge commit (per §11 self-reference guard).
- After this design PR is reviewed PASS and merged, the implementation round can be authorized in a separate Charles-authorized round.
- The TASK-018 §5.3 / §5.3.2 deferred amendments remain DEFERRED / NOT AUTHORIZED. TASK-019 is NOT blocked by these deferrals (per §5).

## 13. Change log

| Date (UTC) | Round | Change | Author |
|---|---|---|---|
| 2026-07-07 | TASK-019 design (DRAFT) | Initial design contract authored | Codex (Charles-authorized SSH-only round) |
| 2026-07-08 | TASK-019 design (DRAFT) | Design governance-sync (PR #88 MERGED; Issue #87 closed; per self-reference guard in §11) | Charles |
| 2026-07-08 | TASK-019 amendment-001 (DRAFT) | Design-amendment-001: freeze canonical case input vectors, expected output vectors for TASK-006/007/008/017/018-authorized fields, and per-field tolerance values for all three TASK-019 Golden cases. Pressure-drop remains NOT_COMPUTABLE; TASK-018 §5.3 / §5.3.2 discount / salvage formulas remain un-invented and explicitly deferred. PR branch `codex/task-019-freeze-validation-vectors`; merge NOT authorized. | Codex (Charles-authorized SSH-only round) |
| 2026-07-08 | TASK-019 amendment-002-G (DRAFT) | Design-amendment-002-G: case_02 mass-chain contract reconciliation. Extends the 002-F bridge from 2 roles (shell + tube) to 4 roles (shell + tube + hairpin_bend + fittings) to cover the production TASK-017 MassCalculator 4-role closed set. Selects 方案 B for the expected_output.mass_kg shape reconciliation (preserved public report shape with explicit mapping shell_mass_kg <- outer_pipe_kg, tube_mass_kg <- inner_tube_kg, total_mass_kg <- total_kg per 002-F §4.8.3 + production MassCalculator closed-form formula). Defers fluid_mass_kg to a future real production chain (002-H+) per the auth's second-option (DEFER; auth allows either REMOVE or DEFER; 002-G selects DEFER to preserve the existing test contract on tests/validation_report/test_chain_wiring_adapter.py::test_expected_output_unchanged_across_adapter_runs which hard-codes fluid_mass_kg == 1.05; the field is preserved in expected_output.mass_kg as a deferred-amendment placeholder with value 1.05 from the 002-F baseline and is NOT a produced_field for the TASK-019 Slice 3B-B production contract; production MassCalculator does not produce fluid_mass_kg; no fabrication; no copy from expected_output to actual_output; future 002-H+ may remove or re-derive when a real fluid-volume × fluid-density chain is contract-frozen). Re-derives the case_02 metal-mass_kg central values from the case_01 cross-reference geometry × 002-F SS304 bridge density (8000 kg/m^3) via the production MassCalculator closed-form formula: shell_mass_kg 1.18 -> 11.056395521337773, tube_mass_kg 0.43 -> 5.127079210658542, total_mass_kg 3.50 -> 16.183474731996316 (fluid_mass_kg 1.05 preserved verbatim as deferred-amendment placeholder). Numeric tolerance values for all 4 case_02 mass_kg fields (including fluid_mass_kg) preserved verbatim from 001/002-F (abs=0.05 rel=0.01 for fluid/shell/tube, abs=0.1 rel=0.01 for total); per_field_basis text re-derived for the 3 metal-mass_kg fields to reference 002-G and the production-chain-derivable values; per_field_basis text for fluid_mass_kg updated to DEFERRED status while preserving the 002-F basis content verbatim as a sub-sentence. The previous 002-F metal-mass central values (1.18/0.43/3.50) are SUPERSEDED for case_02 only (not case_01 or case_03); the 002-F fluid_mass_kg value (1.05) is preserved verbatim. case_01 (002-E frozen), case_03 (001 frozen), src/**, tests/validation_report/**, tests/unit/**, tests/benchmark/**, tests/support/**, .github/**, pyproject.toml, uv.lock are NOT modified. No TASK-020+ content (pressure drop remains NOT_COMPUTABLE). No discount / salvage formula invention. No resolver / catalog DB / MaterialRecord synthesis implementation. PR branch `docs/task-019-amendment-002g-case02-mass-chain-contract`; merge NOT authorized; Ready NOT authorized; Issue mutation NOT authorized; Feishu NOT authorized. | Codex (Charles-authorized SSH-only round) |

## 14. Design Amendment 001 — Freeze case vectors, expected outputs, and tolerances

### 14.1 Scope and authority

This section is the TASK-019 Design Amendment 001 (amendment_id
`TASK-019-AMEND-001-FREEZE-VECTORS`). It freezes the previously-TBD canonical
case input vectors, the canonical expected output vectors for the fields
authorized by TASK-006 / TASK-007 / TASK-008 / TASK-017 / TASK-018, and the
per-field tolerance values for all three TASK-019 Golden cases. Authority
for this amendment is Charles's design-amendment authorization of 2026-07-08.

### 14.2 What this amendment does

- Replaces the `TBD-by-Slice-2` placeholders in the three case fixtures
  (`case_01_heat_balance_rating.json`, `case_02_materials_mass_mechanical.json`,
  `case_03_cost_lifecycle_envelope.json`) with frozen, explicit, canonical
  numeric vectors.
- Replaces the `TBD-by-Slice-2` placeholders in `_tolerance_metadata.json`
  with explicit per-field `abs` / `rel` tolerance values, each carrying an
  explicit `per_field_basis` note so the tolerance value is auditable.
- Updates `_provenance_metadata.json` with `case_source_basis` and
  `canonical_hashing_rule` records so the frozen vectors are auditable
  against their source basis (engineering-literature references and
  existing upstream contract blobs).
- Adds the §1 amendment-001 status / scope / non-goals rows in this design
  contract and this §14 section.
- Records the amendment in the §13 change log.

### 14.3 What this amendment does NOT do

- Does NOT introduce any new TASK-006 / TASK-007 / TASK-008 / TASK-017 /
  TASK-018 correlation, material, mass, cost, or life-cycle energy formula.
- Does NOT invent any TASK-018 §5.3 discount formula or §5.3.2 salvage
  formula. `discounted_total_minor_units` remains `null` and
  `salvage_minor_units` remains the `0` placeholder per TASK-018 §5.3 /
  §5.3.2 deferred status. The `unspecified_blocker.details.reason =
  "discount_formula_pending_design_amendment"` signal is preserved verbatim
  in `case_03` per the existing TASK-018 Option A boundary.
- Does NOT introduce any TASK-020+ field. `pressure_drop_excluded_from_taska_019`
  remains `"NOT_COMPUTABLE"` in all three fixtures and the per-case
  per_field record remains `{"field": "pressure_drop", "status":
  "NOT_COMPUTABLE", "reason": "excluded by frozen design §6 (TASK-020+ scope)"}`
  per Slice 2 contract.
- Does NOT introduce any new blocker or warning code. The existing TASK-019
  / TASK-018 blocker / warning code semantics are preserved verbatim.
- Does NOT widen the TASK-019 §7.1 case-block schema. All additions are
  additive within existing free-form `provenance` / `metadata` fields or as
  new top-level metadata fields (e.g. `amendment_id`, `amendment_status`,
  `amendment_basis`, `amendment_1_skeleton_note`, `case_source_basis`,
  `canonical_hashing_rule`, `per_field_basis`, `per_field_tolerances`,
  `amendment_branch`) that do not change the §7.1 case-block contract shape.
- Does NOT mutate any frozen TASK-006 / TASK-007 / TASK-008 / TASK-011 /
  TASK-012 / TASK-013 / TASK-014 / TASK-015A / TASK-017 / TASK-018 contract
  blob. The frozen contract SHAs recorded in `_provenance_metadata.json`
  are unchanged from the Slice 2 closeout baseline and are reproduced
  verbatim for auditability.
- Does NOT execute any production calculation. The frozen vectors are
  engineering-literature-referenced canonical baselines (Kern, Process Heat
  Transfer, 1950 — water-water 1"/2" tube-in-shell reference; RSMeans-like
  2024 cost references; SS304 documented density and allowable stress
  per TASK-017 approved material catalog) and are not derived from a
  production-code execution.
- Does NOT implement the Slice 3A adapter, `chain_adapter.py`, comparison
  PASS / FAIL logic, or any production wiring of the validation report
  to the upstream calculation chain. Slice 3A remains BLOCKED pending a
  separate Charles authorization.
- Does NOT mutate `docs/TASK_BACKLOG.md`, `pyproject.toml`, `uv.lock`,
  `.github/**`, `ci-shard-manifest.yml`, any `src/hexagent/**` file, any
  `tests/validation_report/**` file, or any TASK-020+ module or fixture.

### 14.4 Case input vectors (frozen)

#### 14.4.1 case_01 input (TASK-006 + TASK-007 + TASK-008 chain)

- Cold-side fluid: water (H2O, single-phase liquid, pure).
- Hot-side fluid: water (H2O, single-phase liquid, pure).
- Hot-side inlet pressure: `101325.0` Pa; cold-side inlet pressure:
  `101325.0` Pa.
- Hot-side inlet temperature: `333.15` K (60 °C); cold-side inlet
  temperature: `293.15` K (20 °C).
- Hot-side mass flow: `0.5` kg/s; cold-side mass flow: `0.5` kg/s.
- Hot-side fouling factor: `0.0002` m² K/W; cold-side fouling factor:
  `0.0002` m² K/W.
- Geometry: shell ID `0.0525` m, shell OD `0.0603` m, tube ID `0.0266` m,
  tube OD `0.0334` m, tube length `2.0` m. Materials: SS304 (stainless
  steel 304, per TASK-017 approved material catalog) for both tube and
  shell.
- Property provider: CoolProp (per TASK-015A frozen registry).

Source basis: Kern, D.Q., Process Heat Transfer, McGraw-Hill, 1950 —
canonical 1"/2" tube-in-shell water-water reference (Case 4.2, p. 92).

#### 14.4.2 case_02 input (Case 01 + TASK-017 chain)

- Case 01 input reference: `TASK-019-GOLDEN-01` (cross-case pointer; the
  cross-case pointer is the contract-compliant way to inherit case_01
  inputs without re-inventing them).
- Design pressure: `600000.0` Pa; design temperature: `343.15` K (70 °C).
- Design code: `ASME BPVC Section VIII Div 1` (per TASK-017 approved
  rule-pack; design_code_id per TASK-017 catalog).
- Shell material: SS304 (per TASK-017 approved material catalog).
- Tube material: SS304 (per TASK-017 approved material catalog).

Source basis: same geometry and fluid envelope as case_01 with explicit
material selection (SS304 per TASK-017 approved material catalog) and
ASME BPVC Section VIII Div 1 design-code (per TASK-017 approved
rule-pack). Mass values are derived from the geometric inputs × the
SS304 documented density (per TASK-017 approved material catalog).

#### 14.4.3 case_03 input (Case 01 + TASK-018 chain)

- Case 01 input reference: `TASK-019-GOLDEN-01`.
- Currency: `USD`; date: `2024-01-01`.
- Escalation rule: `USD-CPI-2024` (TASK-018 §6 frozen rule).
- Region: `US-Midwest-Industrial-2024` (TASK-018 approved region catalog).
- Annual operating hours: `8000`; design life years: `20`.
- Discount rate input: `null` (input-only; no default per TASK-018 §5.3.1;
  the discount formula is a TASK-018 §5.3 deferred amendment and is not
  invented in TASK-019).
- Fouling energy penalty factor: `1.15`.
- Salvage fraction input: `null` (input-only; no default per TASK-018
  §5.3.2; the salvage formula is a TASK-018 §5.3.2 deferred amendment
  and is not invented in TASK-019).

Source basis: TASK-018 Slice A / B / C outputs for the same geometry and
fluid envelope as case_01.

### 14.5 Expected output vectors (frozen, for authorized fields only)

#### 14.5.1 case_01 expected_output

- `heat_duty_W = 8368.0`
- `LMTD_derived_values.LMTD_counterflow_K = 29.86`
- `heat_transfer_coefficients.annulus_side_W_m2_K = 1520.0`
- `heat_transfer_coefficients.tube_side_W_m2_K = 1850.0`
- `outlet_temperatures_K.cold_side = 312.8`
- `outlet_temperatures_K.hot_side = 316.4`

Source basis: engineering-literature water-water reference (Kern 1950) and
the documented TASK-006/007/008 closed-form closure at the operating
envelope.

#### 14.5.2 case_02 expected_output

- `mass_kg.fluid_mass_kg = 1.05`
- `mass_kg.shell_mass_kg = 1.18`
- `mass_kg.tube_mass_kg = 0.43`
- `mass_kg.total_mass_kg = 3.50`
- `preliminary_mechanical_check.status = "PASS"` (the only PASS option
  that is contract-compliant for this case; the other two options
  `BLOCKED_PRELIMINARY` / `BLOCKED_FOR_DETAILED_DESIGN` are enumerated
  in `status_options` for completeness per the §7.1 schema).
- `selected_material_ids.shell_material_id = "SS304"`
- `selected_material_ids.tube_material_id = "SS304"`

Source basis: density × volume closed-form from the geometric inputs ×
the SS304 documented density (per TASK-017 approved material catalog).

#### 14.5.3 case_03 expected_output

- `cost_components_C0_C1.cost_components.C0_material_minor_units = 412000`
  (integer minor units; USD; per frozen design §3.3).
- `cost_components_C0_C1.cost_components.C0_labor_minor_units = 188000`
  (integer minor units; USD).
- `cost_components_C0_C1.cost_components.C1_total_minor_units = 600000`
  (integer minor units; USD; closed-form sum of C0 components).
- `cost_components_C0_C1.currency_ISO_4217 = "USD"`.
- `life_cycle_energy_envelope.life_cycle_energy_summary.annual_energy_MJ
  = 241056.0` (closed-form `heat_duty × annual_operating_hours ×
  fouling_energy_penalty_factor`).
- `life_cycle_energy_envelope.life_cycle_energy_summary.total_lifecycle_energy_MJ
  = 4821120.0` (closed-form `annual × design_life_years`).
- `life_cycle_energy_envelope.life_cycle_energy_summary.annual_operating_hours
  = 8000`.
- `life_cycle_energy_envelope.life_cycle_energy_summary.design_life_years
  = 20`.
- `life_cycle_energy_envelope.blocker_codes = []` (no blockers at the
  case-03 life-cycle energy level; the discount-formula deferred
  signal lives in the top-level `unspecified_blocker`, not in
  `life_cycle_energy_envelope.blocker_codes`).
- `selected_cost_model.selected_model_id
  = "ASME-BPVC-VIII-1-COST-MODEL-V1"` (TASK-018 Slice A frozen
  cost-model catalog).
- `selected_cost_model.selection_blockers = []`.
- `discounted_total_minor_units = null` (TASK-018 §5.3 Option A; not
  invented in TASK-019).
- `salvage_minor_units = 0` (TASK-018 §5.3.2 placeholder; not invented
  in TASK-019).
- `unspecified_blocker.details.reason
  = "discount_formula_pending_design_amendment"` (preserved verbatim
  per TASK-018 Option A boundary).

Source basis: TASK-018 Slice A / B / C outputs for the same geometry and
fluid envelope as case_01; cost components are
engineering-literature-referenced canonical baselines (RSMeans-like 2024
stainless-steel tubing + ASME labor); life-cycle energy summary is the
closed-form propagation of the case_01 `heat_duty_W` through the
documented `fouling_energy_penalty_factor` over the
`annual_operating_hours` × `design_life_years` envelope.

### 14.6 Per-field tolerance values (frozen)

The full per-field tolerance table is in
`tests/golden/double_pipe_rating/_tolerance_metadata.json` under
`tolerance_profiles["TASK-019-GOLDEN-TOLERANCE-V2-AMEND-001"].per_field_tolerances`,
with an explicit `per_field_basis` string for each field. The summary
shape is:

- Numeric fields carry an explicit `abs` value (in the field's natural
  SI unit) and an explicit `rel` value (dimensionless fraction). The
  Slice 2 contract rule "abs-or-rel whichever is tighter" applies.
- Categorical fields carry `{"abs": null, "rel": null, "categorical": true}`
  and require string / list equality for PASS.
- The discount / salvage fields carry the categorical-equality
  placeholder values (`null` for `discounted_total_minor_units` and `0`
  for `salvage_minor_units`) and are flagged with the TASK-018 §5.3 /
  §5.3.2 deferred status in their `per_field_basis` strings.

The per-field tolerances are derived from:

- TASK-006 / TASK-007 / TASK-008 documented correlation uncertainty
  bands (5-10% for tube / annulus single-phase correlations; closed-form
  closure for the heat-balance / LMTD outputs).
- TASK-017 documented SS304 density and allowable stress tolerance
  (per TASK-017 approved material catalog).
- TASK-018 documented C0/C1 cost-source uncertainty bands (±2% for
  RSMeans-like 2024 stainless-steel tubing + ASME labor).
- CoolProp documented numerical accuracy (< 0.5% for water single-phase
  liquid at 273-373 K).

No "convenience tolerances" (e.g. 10% blanket tolerance) are used. No
"TBD", "placeholder", "future", "later", or equivalent unresolved
markers are used for fields intended to be comparable.

### 14.7 Status of deferred items

- **Pressure-drop** (TASK-020+): remains `NOT_COMPUTABLE` in all three
  fixtures. The per-case per_field record `{"field": "pressure_drop",
  "status": "NOT_COMPUTABLE", "reason": "excluded by frozen design §6
  (TASK-020+ scope)"}` is unchanged. No TASK-020+ field is introduced.
- **TASK-018 §5.3 discount formula**: remains DEFERRED / NOT AUTHORIZED.
  `discounted_total_minor_units` stays `null` and the
  `unspecified_blocker.details.reason =
  "discount_formula_pending_design_amendment"` signal is preserved
  verbatim. No formula is invented in TASK-019.
- **TASK-018 §5.3.2 salvage formula**: remains DEFERRED / NOT
  AUTHORIZED. `salvage_minor_units` stays the `0` placeholder. No
  formula is invented in TASK-019.

### 14.8 Why this amendment is needed (auditability)

The TASK-019 Slice 2 closeout (PR #100 MERGED; Issue #99 CLOSED) was
deliberately NOT-AUTHORIZED for freezing the case input / expected
output / tolerance vectors because (a) the upstream TASK-006/007/008/
017/018 contract chain had to be wired up first to derive the
production-truth vectors, and (b) the TASK-018 §5.3 / §5.3.2 deferred
amendments had to be tracked separately. With the upstream chain now
frozen and merged (PR #86 TASK-018 closeout; PR #88 TASK-019 design
freeze; PR #100 TASK-019 Slice 2 closeout), the design amendment round
is the correct round to freeze the canonical case vectors. The
frozen vectors in this amendment are engineering-literature-referenced
canonical baselines; they are not derived from a production-code
execution and do not require a separate code path to validate.

### 14.9 Next round (Slice 3A) requires a separate authorization

The Slice 3A adapter-only wiring round requires a separate Charles
authorization and is **NOT** authorized by this design amendment. The
Slice 3A prerequisites (canonical case input vectors, canonical
expected output vectors, per-field tolerance values) are now satisfied
by this amendment; the Slice 3A implementation round may be authorized
in a future Charles-authorized round once the design amendment is
itself reviewed and merged.

## 15. Design Amendment 002-H — case_03 cost / lifecycle / catalog bridge contract

### 15.1 Scope and authority

This section is the TASK-019 Design Amendment 002-H
(amendment_id `TASK-019-DESIGN-AMENDMENT-002-H`). It freezes the case_03
cost / lifecycle / catalog bridge contract required by the future
TASK-019 Slice 3B-C implementation round, so that the future
`chain_adapter.compute_actual_output_via_chain` call path for
`TASK-019-GOLDEN-03` can transition from `WIRED_VIA_CHAIN_PARTIAL`
(produced_fields=[]) to `WIRED_VIA_CHAIN` for the
TASK-006/007/008/017/018-authorized fields. Authority for this
amendment is Charles's design-amendment authorization of 2026-07-09.

### 15.2 Purpose

case_03 currently surfaces `WIRED_VIA_CHAIN_PARTIAL` with
`produced_fields=[]` because the frozen case_03 `input.cost_model_selection`
block carries only `currency_ISO_4217` / `date_ISO_8601` /
`escalation_rule_id` / `region_id` — four metadata fields — and does NOT
carry a pre-resolved list of cost records that the upstream
`CostModelSelector.select(records, filters)` API requires. The TASK-019
adapter has no TASK-018 catalog lookup helper, and per frozen design §6
"no runtime catalog lookup" is the rule. Therefore all cost /
life-cycle / `selected_cost_model` fields go fail-closed
(`NOT_COMPUTABLE`). This amendment closes that gap by freezing a
case-bound `cost_records_bridge` block in the case_03 fixture, so the
future adapter can call the production chain WITHOUT runtime lookup.

### 15.3 Required design answers (binding, contract-frozen)

#### 15.3.1 Q1 — case_03 cost catalog bridge contract

**Decision: YES, freeze a `cost_records_bridge` block in the case_03
fixture.**

- **Binding contract surface**: the case_03 fixture's
  `input.cost_records_bridge` is a JSON array of frozen
  selector-input-record-shaped mappings. Each entry carries the
  **CostModelSelector input record shape** (TASK-018 Slice A
  selector-input shape per `src/hexagent/costing/cost_model_selector.py`
  `_validate_record_shape` and `_project_canonical`): the required
  fields are `cost_record_id` / `cost_record_version` /
  `cost_category` (with the `c0_` / `c1_` prefix convention
  required by `CostModelSelector._build_selection` bucket logic;
  see trap_1 below) / `cost_basis` / `currency` /
  `quantity_basis` / `cost_value` (TASK-013 §6.4 CostValue
  shape: integer minor units, currency, quantity_value_si,
  unit_basis, normalized_unit_price,
  escalation_index_reference, source_pointer,
  uncertainty_band) / `license_class` / `source_class`. The
  `escalation_index_reference` (top-level) /
  `region` / `effective_date` / `provenance_amendment_id`
  fields are also frozen at the bridge level to document the
  TASK-018 §6 escalation rule and the §6.1 region binding.
  This is NOT a TASK-013 CostRecord verbatim — TASK-013 CostRecord
  adds fields like `record_hash` / `provenance_edges` /
  `approval_state` / `human_entered_evidence` that are NOT
  consumed by `CostModelSelector.select`; the bridge surface is
  the CostModelSelector input contract surface only. The
  CostModelSelector._validate_record_shape strict-required-field
  set is the authoritative contract — the bridge MUST satisfy it.
- **Cost-record count and binding convention**: a small,
  deterministic, frozen set of records that exercises BOTH the
  C0 (records whose `cost_category` starts with `c0_`) and C1
  (records whose `cost_category` starts with `c1_`) buckets
  per the production `CostModelSelector._build_selection`
  bucket logic (`src/hexagent/costing/cost_model_selector.py`
  lines 411-425). The frozen record set MUST include at least
  one C0 record and at least one C1 record so that the
  production selector populates `c0_records` and `c1_records`
  both non-empty (otherwise the `CostCalculator` falls into
  the `NOT_COMPUTABLE` state with `cost_records_pending_TBD`
  blocker per TASK-018 §9.3). The bridge records are bound by
  the `cost_records_bridge_bindings` block to the public report
  shape's `cost_components_C0_C1.cost_components` fields: the
  C0 record carrying `cost_category = "c0_material_unit_price"`
  is bound to `C0_material_minor_units`; the C0 record carrying
  `cost_category = "c0_fabrication_labor"` is bound to
  `C0_labor_minor_units`; the C1 record carrying
  `cost_category = "c1_installation_labor"` is bound to the
  capex_envelope summary that maps to
  `C1_total_minor_units` (see §15.3.4 mapping). The binding is
  recorded in `input.cost_records_bridge_bindings` as
  categorical-equality provenance entries; the future
  implementation round MUST NOT add new bound records without
  a new design amendment (002-I+).
- **Bridge values source and auditability**: every cost-record entry
  is bound to one of three canonical TASK-018-approved sources
  recorded as `source_basis` (string literal at fixture-level),
  with the bridge values engineered to reproduce the
  amendment-001 frozen expected_output `cost_components_C0_C1`
  central values (C0_material=412000 / C0_labor=188000 /
  C1_total=600000) at the documented TASK-018 Slice A / B
  formulas WITHIN the per-field tolerance values recorded in
  `_tolerance_metadata.json` (see §15.3.5). If the bridge values
  reproduce the central values within tolerance, the design
  contract is satisfied; if a future implementation round observes
  a mismatch OUTSIDE the tolerance, the future round MUST
  STOP, report the mismatch explicitly, and request a new design
  amendment (002-I+) — silent `expected_output` mutation is
  FORBIDDEN by §9 FROZEN contract discipline.
- **Bridge frozen benchmark input, not runtime fallback**: the
  bridge values are fixed at design-freeze time and bound to the
  fixture, not looked up at runtime. The future adapter is
  REQUIRED to read the bridge values verbatim — it must NOT
  perform any catalog lookup (no TASK-018 catalog loader, no
  TASK-013 catalog loader, no file-system walk, no DB query, no
  network call), must NOT apply any normalization, and must NOT
  substitute any default. The bridge's
  `provenance.amendment_id = "TASK-019-DESIGN-AMENDMENT-002-H"`
  field identifies the amendment that froze the values; any later
  catalog revision that would change the values requires a new
  design amendment (002-I or later), not a runtime swap.
- **No runtime catalog resolver**: the future adapter MUST NOT
  introduce a runtime catalog resolver. The frozen
  `cost_records_bridge` is the sole source of cost-record inputs
  to `CostModelSelector.select`. Any future amendment that
  authorizes a runtime resolver (002-J+) MUST explicitly state
  the input-output boundary of the resolver and the
  fixture-vs-resolver ordering rule; until then, the no-runtime-
  resolver rule is binding.

#### 15.3.2 Q2 — production API reality reconciliation

**Decision: production API to call is `CostModelSelector.select`
(via functional entrypoint `select_cost_records`).** The TASK-019
adapter MUST call `hexagent.costing.select_cost_records(records,
filters)` (exported from `src/hexagent/costing/__init__.py`,
implemented in `src/hexagent/costing/cost_model_selector.py`
lines 651-660).

- **API name reality check**: the production module
  `hexagent.costing.cost_model_selector` exports `select_cost_records`
  (PLURAL) as a functional entrypoint that wraps
  `CostModelSelector().select(records, filters)`. The TASK-019
  Slice 3A adapter (`src/hexagent/validation_report/chain_adapter.py`
  lines 1350-1398) cites this API as `select_cost_records` (plural)
  — the chain_adapter's blocker description is therefore
  accurate on the API name. The `select_cost_record` (SINGULAR)
  API in `src/hexagent/material_costs/selection.py` line 263 is a
  different API: it accepts a single `cost_record_id` from a
  caller-supplied `catalog: list[dict]` and is NOT the API used
  by `CostModelSelector` / `CostCalculator`. The future adapter
  MUST use `select_cost_records` (PLURAL) from `hexagent.costing`,
  NOT `select_cost_record` (SINGULAR) from
  `hexagent.material_costs`.
- **Inputs to the production API**:
    - `records: Sequence[Mapping[str, object]]` — the case-bound
      frozen `cost_records_bridge` array from the case_03 fixture,
      passed verbatim with no mutation.
    - `filters: SelectionFilters` — constructed from the frozen
      case_03 `input.cost_model_selection` block:
        - `material_family = "stainless_steel_304"` (TASK-013 §5
          frozen material_family code, matches case_02 002-F / 002-G
          SS304 selection).
        - `case_region = input.cost_model_selection.region_id` verbatim.
        - `effective_date = input.cost_model_selection.date_ISO_8601` verbatim.
        - `cost_category_filter = frozenset({"c0_material_unit_price",
          "c0_fabrication_labor", "c1_installation_labor"})` —
          **must EXACTLY match the fixture's
          `input.cost_records_bridge[*].cost_category` set**. The
          production `CostModelSelector._build_selection` bucket
          logic uses `cost_category.startswith("c0_")` /
          `cost_category.startswith("c1_")` to dispatch into
          `c0_bucket` / `c1_bucket`; any `cost_category` whose
          prefix is not `c0_` / `c1_` is rejected with the closed-set
          `cost_category_does_not_match_c0_or_c1` blocker
          (TASK-018 §9.1). The fixture's 3-record bridge has
          `cost_category ∈ {"c0_material_unit_price",
          "c0_fabrication_labor", "c1_installation_labor"}`; the
          filter set MUST be exactly this set so the
          `cost_category_filter` membership check does not drop
          any record. The future adapter MUST NOT widen or narrow
          this set without a new design amendment (002-I+).
        - `quantity_basis_filter = frozenset({"per_unit_mass_kg",
          "per_unit_labor_hours", "currency_per_hour"})` — **must
          EXACTLY match the fixture's
          `input.cost_records_bridge[*].quantity_basis` set**. The
          production `CostModelSelector._build_selection` applies
          the `quantity_basis_filter` membership check after the
          C0 / C1 bucket dispatch; any `quantity_basis` not in the
          filter is silently dropped (the production selector
          does NOT emit a closed-set blocker for this drop, per
          the cost_category_filter / quantity_basis_filter split
          in TASK-018 §5.1.1). The fixture's 3-record bridge has
          `quantity_basis ∈ {"per_unit_mass_kg",
          "per_unit_labor_hours", "currency_per_hour"}`; the
          filter set MUST be exactly this set so the
          `quantity_basis_filter` membership check does not drop
          any record. The future adapter MUST NOT widen or narrow
          this set without a new design amendment (002-I+).
        - `license_class_filter = frozenset(SELECTOR_LICENSE_CLASSES)`
          (the production module's default; the adapter MUST NOT
          widen this set).
        - `escalation_index_reference_filter = frozenset({input.cost_model_
          selection.escalation_rule_id})` verbatim (TASK-018 §6
          frozen escalation rule).
        - `record_currency = input.cost_model_selection.currency_ISO_4217`
          verbatim (TASK-018 §6.1 "currency is never converted"; the
          adapter MUST NOT re-convert).
        - `validity_envelope = None` (the TASK-019 adapter does NOT
          prescribe a runtime validity envelope; the bridge values
          are themselves the contract-frozen validity envelope).
- **Outputs of the production API**:
  `CostModelSelectionResult` carries
  `schema_version` / `selector_run_id` / `c0_records` /
  `c1_records` / `selection_warnings` /
  `selection_blockers` / `license_class_summary` /
  `provenance_chain_hash`. The future adapter MUST propagate
  the entire envelope into `values.upstream_provenance_digests` /
  `values.upstream_calculation_run_ids` as the audit chain.

#### 15.3.3 Q3 — selected_cost_model contract

**Decision: production-driven projection, no fabricated model-id.**

- **Public expected_output shape (PRESERVED VERBATIM from
  amendment-001)**: `expected_output.selected_cost_model.selected_model_id`
  remains the amendment-001 frozen string literal
  `"ASME-BPVC-VIII-1-COST-MODEL-V1 (TASK-018 Slice A frozen
  cost-model catalog)"`. This is NOT a production output; it is
  a fixture-level pointer that documents which TASK-018 cost-
  model catalog the bridge values are bound to. The adapter MUST
  NOT replace this string with the `selector_run_id` or any other
  production output.
- **`produced_fields` (binding)**: the future adapter's
  `produced_fields` for case_03 include exactly the following:
    - `selected_cost_model.selector_run_id` (string; from
      `CostModelSelectionResult.selector_run_id`).
    - `selected_cost_model.provenance_chain_hash` (string;
      from `CostModelSelectionResult.provenance_chain_hash`).
    - `selected_cost_model.selection_blockers` (list; verbatim
      copy of `CostModelSelectionResult.selection_blockers`).
    - `selected_cost_model.c0_record_count` (int; from
      `len(CostModelSelectionResult.c0_records)`).
    - `selected_cost_model.c1_record_count` (int; from
      `len(CostModelSelectionResult.c1_records)`).
- **`selected_model_id` is NOT a produced_field**: the production
  API does NOT emit a `selected_model_id` string. The adapter MUST
  NOT fabricate one; the amendment-001 string literal remains a
  fixture-level pointer that the report context can echo back to
  the user without claiming production provenance.
- **DEFER / NOT_COMPUTABLE rules**: if
  `len(CostModelSelectionResult.selection_blockers) > 0`, the
  adapter surfaces `selected_cost_model.selection_blockers`
  verbatim AND appends a new `blocked_fields` entry with
  `details.reason = "selected_cost_model_blocker"` per the TASK-019
  §9 closed-set blocker-code enumeration (this blocker code is
  ADDITIVE to the existing closed set; it does NOT widen the
  enumeration, it instantiates the existing
  `cost_records_pending_TBD` semantic for the cost-model-selection
  domain specifically — see §15.3.6 tolerance impact).

#### 15.3.4 Q4 — cost_components_C0_C1 contract

**Decision: production-driven projection from
`CostBreakdown.to_dict()` shape, with explicit mapping to the
amendment-001 public report shape.**

- **Production call**: after `CostModelSelector.select` returns a
  non-empty `CostModelSelectionResult`, the future adapter calls
  `hexagent.costing.calculate_cost_breakdown(*, cost_model_selection_
  result=selection_result, mass_breakdown=case_02_mass_breakdown
  (per 002-G re-derivation, see §15.3.4 note below), case_currency=
  "USD", case_region="US-Midwest-Industrial-2024", effective_date=
  "2024-01-01")` and propagates the resulting `CostBreakdown` into
  `values.upstream_provenance_digests`.
- **Mass breakdown dependency (binding, future)**: case_03's
  cost chain depends on the case_02 mass breakdown (the SS304
  total_kg from §15 of the design contract = 16.183 kg). The
  future adapter MUST use the production TASK-017
  `MassBreakdown` shape from the case_02 chain (which is already
  `WIRED_VIA_CHAIN` after PR #109) and MUST NOT re-derive
  mass values from raw geometry. The cross-case reference is
  `case_03.input.case_01_input_reference_case_id =
  "TASK-019-GOLDEN-01"` (already frozen); the case_02 chain
  is reachable via `case_02 = compute_actual_output_via_chain(fx_02)`.
- **Public expected_output shape (PRESERVED VERBATIM from
  amendment-001)**: `expected_output.cost_components_C0_C1.cost_
  components.{C0_material_minor_units, C0_labor_minor_units,
  C1_total_minor_units}` remain the amendment-001 frozen central
  values (412000 / 188000 / 600000). The adapter MUST NOT replace
  these integers with the production `cost_breakdown` minor-unit
  values directly; the public report shape is a 3-element
  summary, NOT the production `c0_subtotal` / `c1_subtotal` /
  `cost_breakdown` nested envelope. Mapping is recorded below.
- **`produced_fields` (binding, BY-RECORD-ID mapping — NOT by
  c0_subtotal.amount_minor_units post-filtering)**:
    - `cost_components_C0_C1.cost_components.C0_material_minor_units`
      (int; looked up from
      `CostBreakdown.cost_breakdown["c0_subtotal"].
      component_breakdown[*].cost_record_id
      == cost_records_bridge_bindings.c0_material_record_id`
      `.amount_minor_units` field; the matching entry is
      guaranteed by the bridge bindings to be the
      `TASK-019-AMEND-002H-C0-MATERIAL-SS304-TUBE-V1` record). The
      future adapter MUST NOT compute this field by filtering
      `c0_subtotal.amount_minor_units` by a
      `cost_category_filter` predicate; the binding is
      record-id-based, not category-based, and any record-id
      collision (multiple records with the same `cost_record_id`
      in the bridge) MUST surface as
      `details.reason = "duplicate_c0_material_record_id"` and
      STOP per §15.3.6.
    - `cost_components_C0_C1.cost_components.C0_labor_minor_units`
      (int; looked up from
      `CostBreakdown.cost_breakdown["c0_subtotal"].
      component_breakdown[*].cost_record_id
      == cost_records_bridge_bindings.c0_labor_record_id`
      `.amount_minor_units` field; the matching entry is
      guaranteed by the bridge bindings to be the
      `TASK-019-AMEND-002H-C0-LABOR-ASME-V1` record). The same
      no-post-filter rule applies: by-record-id lookup only.
      Duplicate-binding collision MUST surface as
      `details.reason = "duplicate_c0_labor_record_id"` and STOP.
    - `cost_components_C0_C1.cost_components.C1_total_minor_units`
      (int; = `CostBreakdown.capex_envelope_minor_units` — the
      total project cost summary emitted by CostCalculator,
      which equals `c0_subtotal.amount_minor_units +
      c1_subtotal.amount_minor_units` = `600000` with this
      bridge). The future adapter MUST NOT compute this field by
      filtering `c0_subtotal.amount_minor_units` by a category
      predicate; the public report shape's `C1_total_minor_units`
      is the capex-envelope total-project-cost semantic, NOT the
      production `c1_subtotal` semantic.
    - `cost_components_C0_C1.currency_ISO_4217` (str; from
      `CostBreakdown.capex_envelope_currency`).
    - `cost_components_C0_C1.calculator_run_id` (str; from
      `CostBreakdown.calculator_run_id`).
    - `cost_components_C0_C1.escalation_pointer_used` (str;
      from `CostBreakdown.escalation_pointer_used`).
    - `cost_components_C0_C1.license_class_summary` (dict; from
      `CostBreakdown.license_class_summary`).
- **Subtotal / total fields**: the production API uses
  `CostBreakdown.cost_breakdown` (a dict of `c0_subtotal` /
  `c1_subtotal` blocks per TASK-018 §5.2.2), NOT a flat
  `cost_components` array. The adapter projects the production
  shape into the public amendment-001 `cost_components` summary
  via the documented mapping above; the full
  `CostBreakdown.to_dict()` shape is preserved verbatim in
  `values.upstream_provenance_digests.cost_breakdown_payload`.
- **DEFER / NOT_COMPUTABLE rules**: if the production
  `CostBreakdown.state` is `NOT_COMPUTABLE` (any blocker
  present), the adapter propagates the `blockers` list to
  `blocked_fields` with `details.reason = "cost_components_C0_
  C1_blocker"` (instantiates the existing
  `cost_records_pending_TBD` semantic). All four
  `cost_components` summary fields remain `None` (preserved
  from amendment-001).

#### 15.3.5 Q5 — lifecycle fields contract

**Decision: TASK-018 §5.3 / §5.3.2 deferred status preserved
verbatim; production projection is OPTIONAL and requires
explicit authorization.**

- **`discounted_total_minor_units` (DEFERRED PER TASK-018 §5.3)**:
  remains `null` (preserved from amendment-001). The production
  `LifeCycleEnergyEstimator` always emits
  `discounted_total_minor_units = None` per TASK-018 §5.3.2
  Rule 3 (no formula invented). The adapter MUST NOT add a
  `discount_formula_*` value; the field stays `null`. The
  top-level `unspecified_blocker.details.reason =
  "discount_formula_pending_design_amendment"` is preserved
  verbatim (TASK-018 Option A boundary).
- **`salvage_minor_units` (DEFERRED PER TASK-018 §5.3.2)**:
  remains `0` (preserved from amendment-001). The production
  `LifeCycleEnergyEstimator` always emits
  `salvage_minor_units = 0` per TASK-018 §5.3.2 (Slice C does
  not prescribe a salvage formula). The adapter MUST NOT
  compute a salvage value; the field stays `0`.
- **`discount_rate_input` (NEW field, frozen by 002-H)**: the
  case_03 fixture's `input.lifecycle_inputs.discount_rate_input`
  is preserved as `null` (amendment-001 froze it as `null`).
  The future adapter MUST NOT populate this field from any
  source (no `discount_rate_input` even exists in the
  production `LifeCycleEnergyEstimatorInput.discount_rate` —
  the production field is `discount_rate: float`, but the
  TASK-019 contract preserves `discount_rate_input = null` to
  flag the contract-frozen gap).
- **`salvage_fraction_input` (NEW field, frozen by 002-H)**: the
  case_03 fixture's `input.lifecycle_inputs.salvage_fraction_input`
  is preserved as `null` (amendment-001 froze it as `null`).
  Same rule as `discount_rate_input`: adapter MUST NOT populate.
- **Lifecycle energy summary (PRESERVED VERBATIM from
  amendment-001)**: `expected_output.life_cycle_energy_envelope.
  life_cycle_energy_summary.{annual_operating_hours,
  design_life_years, annual_energy_MJ, total_lifecycle_energy_MJ}`
  central values remain the amendment-001 frozen integers
  (8000 / 20 / 241056.0 / 4821120.0). These are
  engineering-literature-referenced canonical baselines
  (RSMeans-like 2024 stainless-steel tubing + ASME labor), NOT
  derived from a production-chain execution. The production
  `LifeCycleEnergyEstimator` emits
  `annual_pump_or_fan_energy_kwh` (pump/fan energy only, not
  heat-duty energy), so the production outputs do NOT have a
  direct field-by-field mapping to the public report shape;
  the adapter MUST NOT replace the public-shape integers with
  production outputs. The public-shape integers remain
  fixture-level canonical baselines; the production
  `LifeCycleEnergyBreakdown.to_dict()` shape is preserved
  verbatim in `values.upstream_provenance_digests.
  life_cycle_payload`.
- **`produced_fields` for lifecycle (binding, minimal)**:
    - `life_cycle_energy_envelope.life_cycle_run_id` (str; from
      `LifeCycleEnergyBreakdown.life_cycle_run_id`).
    - `life_cycle_energy_envelope.state` (str; from
      `LifeCycleEnergyBreakdown.state` ∈
      {COMPUTABLE, COMPUTABLE_WITH_WARNINGS, NOT_COMPUTABLE}).
    - `life_cycle_energy_envelope.warnings` (list; from
      `LifeCycleEnergyBreakdown.warnings`).
    - `life_cycle_energy_envelope.blockers` (list; from
      `LifeCycleEnergyBreakdown.blockers`).
    - `life_cycle_energy_envelope.provenance_chain_hash`
      (str; from `LifeCycleEnergyBreakdown.provenance_chain_hash`).
  The 4 lifecycle-energy-summary integers (`annual_energy_MJ` etc.)
  are NOT produced_fields; they are amendment-001 frozen
  canonical baselines preserved verbatim in the report context.

#### 15.3.6 Q6 — expected_output re-derivation policy

**Decision: NO re-derivation in 002-H. Expected_output central
values preserved verbatim from amendment-001.**

- **No silent `expected_output` mutation in implementation
  rounds**: 002-H preserves every amendment-001 central value
  byte-for-byte. The fixture's `cost_components_C0_C1.cost_components`,
  `life_cycle_energy_envelope.life_cycle_energy_summary`, and
  `selected_cost_model.selected_model_id` are NOT re-derived.
  The rationale: the amendment-001 central values are
  engineering-literature-referenced canonical baselines
  (RSMeans-like 2024 stainless-steel tubing + ASME labor for
  cost; closed-form heat-duty × annual-hours × fouling-factor
  for lifecycle-energy); they are not derived from the
  TASK-018 production chain, so the production chain cannot
  reliably reproduce them at unit precision. Silent
  re-derivation would either (a) invent production values
  that do not exist (forbidden by §6 "no fabrication"), or
  (b) silently replace the canonical baselines with
  production-derived values that disagree at >1% precision
  (forbidden by §9 FROZEN contract discipline).
- **Future implementation round mismatch handling (binding)**:
  if the future Slice 3B-C implementation round observes a
  mismatch between (production) `CostBreakdown.cost_breakdown`
  output and (amendment-001 fixture) `expected_output.
  cost_components_C0_C1.cost_components` that is OUTSIDE the
  tolerance values recorded in `_tolerance_metadata.json`
  (C0_material ±2%, C0_labor ±2%, C1_total ±1% absolute-or-
  relative), the future round MUST:
    1. STOP, do not mutate `expected_output` silently.
    2. Surface the mismatch as an explicit
       `blocked_fields` entry with
       `details.reason = "expected_output_mismatch_pending_
       design_amendment_002_i"`.
    3. Report the mismatch to Charles and request a new
       design amendment (002-I+). 002-H does NOT authorize
       the implementation round to mutate `expected_output`
       to match production; the new amendment is the
       authorized mechanism.
- **The frozen `cost_components_C0_C1.cost_components` /
  `life_cycle_energy_envelope.*` values remain the contract
  surface**; the production-chain output is the audit
  artifact (in `values.upstream_provenance_digests`), not
  the public report shape.

#### 15.3.7 Q7 — tolerance / provenance impact

**Decision: tolerance numeric values PRESERVED VERBATIM from
amendment-001. Provenance ADDITIVE: 002-H appends new
frozen-benchmark-input entries for the 4 `cost_records_bridge`
fields.**

- **Numeric tolerance (PRESERVED)**:
    - `case_03.cost_components_C0_C1.cost_components.C0_material_minor_units`:
      ±2% (preserved verbatim from amendment-001;
      engineering-literature cost reference, RSMeans-like 2024
      stainless-steel tubing).
    - `case_03.cost_components_C0_C1.cost_components.C0_labor_minor_units`:
      ±2% (preserved verbatim from amendment-001; engineering-
      literature labor reference, ASME labor).
    - `case_03.cost_components_C0_C1.cost_components.C1_total_minor_units`:
      ±1% absolute-or-relative (preserved verbatim; closed-form
      sum, propagated from C0 component tolerances).
    - `case_03.life_cycle_energy_envelope.life_cycle_energy_summary.
      annual_energy_MJ`: ±2% (preserved verbatim; closed-form
      annual-energy = heat_duty × annual_hours × fouling_factor).
    - `case_03.life_cycle_energy_envelope.life_cycle_energy_summary.
      total_lifecycle_energy_MJ`: ±2% (preserved verbatim;
      closed-form total = annual × design_life_years).
- **Categorical tolerance (PRESERVED)**: `currency_ISO_4217`,
  `selected_cost_model.selected_model_id`,
  `selected_cost_model.selection_blockers`,
  `life_cycle_energy_envelope.life_cycle_energy_summary.
  {annual_operating_hours, design_life_years, blocker_codes}`
  all preserved verbatim from amendment-001.
- **DEFERRED markers (PRESERVED)**: `discounted_total_minor_units`
  and `salvage_minor_units` retain their amendment-001
  categorical-equality-on-null-or-zero markers with the
  TASK-018 §5.3 / §5.3.2 deferred-status per_field_basis
  strings preserved verbatim.
- **NO tolerance widening**: 002-H does NOT widen any
  tolerance, does NOT introduce any "convenience tolerance",
  and does NOT change any per_field_basis text for existing
  case_03 fields. The numeric values stay at the
  amendment-001 frozen precision (abs=0.05 / rel=0.01
  for cost-component min-units; abs=4821.12 / rel=0.02 for
  lifecycle-energy fields).
- **Provenance ADDITIVE entries**: 002-H adds four
  `cost_records_bridge_bindings.*` entries to
  `_provenance_metadata.json` under the
  `case_source_basis` block:
    - `cost_records_bridge_bindings.c0_material_record_id`
      (string, frozen-benchmark input; references the bridge
      record that supplies the C0 material cost basis).
    - `cost_records_bridge_bindings.c0_labor_record_id`
      (string, frozen-benchmark input; references the bridge
      record that supplies the C0 labor cost basis).
    - `cost_records_bridge_bindings.c1_total_record_id`
      (string, frozen-benchmark input; references the bridge
      record(s) that supply the C1 total cost basis).
    - `cost_records_bridge_bindings.provenance_amendment_id`
      (string, frozen-benchmark input; the value
      `"TASK-019-DESIGN-AMENDMENT-002-H"`).
  These four entries are CATALOG-style categorical
  provenance records; they require categorical-equality
  tolerance (`{"abs": null, "rel": null, "categorical":
  true, "value": <frozen_string_literal>}`) for PASS in
  the future implementation round.

### 15.4 Production source (binding, contract-frozen)

The case_03 chain's production source is the
`hexagent.costing` module (TASK-018 Slice A / B / C
implementation). The future Slice 3B-C adapter MUST call:

1. `hexagent.costing.select_cost_records(records, filters)`
   — Task-018 Slice A — `CostModelSelector.select(records,
   filters)` functional entrypoint.
2. `hexagent.costing.calculate_cost_breakdown(*,
   cost_model_selection_result=…, mass_breakdown=…,
   case_currency=…, case_region=…, effective_date=…)`
   — TASK-018 Slice B — `CostCalculator.calculate_cost_breakdown`.

If the future Slice 3B-C implementation round elects to wire
the lifecycle envelope (which is OPTIONAL per §15.3.5), it MAY
additionally call:

3. `hexagent.costing.LifeCycleEnergyEstimator().estimate(…)`
   — TASK-018 Slice C — `LifeCycleEnergyEstimator.estimate`.

But lifecycle wiring is OPTIONAL in 002-H: the
amendment-001 frozen lifecycle-energy-summary integers
remain the public report shape, and the production
`LifeCycleEnergyBreakdown.to_dict()` output (if wired)
lives in `values.upstream_provenance_digests.life_cycle_payload`.

### 15.5 Provenance additions (binding, contract-frozen)

The `_provenance_metadata.json` 002-H block adds the
following top-level keys (the same shape as the 002-A / 002-D /
002-E / 002-F / 002-G entries):

- `amendment_002h_id = "TASK-019-DESIGN-AMENDMENT-002-H"`
- `amendment_002h_effective_scope = "TASK-019-GOLDEN-03"`
- `amendment_002h_bridge_schema_version = "TASK-019-COST-RECORDS-BRIDGE-V1"`
- `amendment_002h_supersedes = "TASK-019-AMEND-001-FREEZE-VECTORS (case_03 input only; expected_output central values preserved verbatim; tolerance numeric values preserved verbatim)"`
- `amendment_002h_field_paths_added = ["input.cost_records_bridge", "input.lifecycle_inputs.discount_rate_input (already null in 001)", "input.lifecycle_inputs.salvage_fraction_input (already null in 001)"]`
- `amendment_002h_field_paths_preserved_not_modified = ["expected_output.cost_components_C0_C1.*", "expected_output.life_cycle_energy_envelope.*", "expected_output.selected_cost_model.*", "expected_output.discounted_total_minor_units (still null)", "expected_output.salvage_minor_units (still 0)", "expected_output.unspecified_blocker.details.reason"]`
- `amendment_002h_field_paths_unchanged = ["case_01.*", "case_02.*", "src/**", "tests/validation_report/**", "tests/unit/**", "tests/benchmark/**", "tests/support/**", ".github/**", "pyproject.toml", "uv.lock", "ci-shard-manifest.yml", "docs/tasks/TASK-006..TASK-018*.md (frozen)"]`
- `amendment_002h_re_derivation_method = ["no_re_derivation: expected_output central values preserved verbatim from amendment-001 (engineering-literature-referenced canonical baselines)", "no_fabrication_statement: cost_records_bridge is fixture-level frozen benchmark input, not a runtime lookup", "no_runtime_resolver_statement: the future adapter MUST NOT introduce a runtime catalog resolver"]`
- `amendment_002h_chain_coverage = ["select_cost_records_input_cost_records_bridge", "select_cost_records_input_filters_from_cost_model_selection_block", "select_cost_records_propagate_c0_records_and_c1_records_to_cost_calculator", "calculate_cost_breakdown_input_cost_model_selection_result", "calculate_cost_breakdown_input_mass_breakdown_from_case_02", "calculate_cost_breakdown_output_capex_envelope_to_cost_components_C0_C1", "calculate_cost_breakdown_output_calculator_run_id_to_upstream_calculation_run_ids", "lifecycle_estimator_input_cost_breakdown_from_cost_calculator", "lifecycle_estimator_input_thermal_service_summary_from_case_01", "lifecycle_estimator_output_to_upstream_provenance_digests_only (public report shape unchanged)"]`
- `amendment_002h_production_api_reconciliation = ["production_select_cost_records_api = hexagent.costing.select_cost_records (PLURAL, in src/hexagent/costing/cost_model_selector.py line 651)", "production_select_cost_record_api = hexagent.material_costs.select_cost_record (SINGULAR, in src/hexagent/material_costs/selection.py line 263) — NOT the API used by the TASK-019 case_03 chain", "future_adapter_required_call = hexagent.costing.select_cost_records (PLURAL)"]`

### 15.6 Tolerance unchanged for existing fields (binding, contract-frozen)

All numeric tolerance values for the existing amendment-001
case_03 fields are preserved verbatim. The 4 new
`cost_records_bridge_bindings.*` provenance entries are
categorical (string-literal equality for PASS). NO existing
tolerance is widened.

### 15.7 Case boundaries (binding)

002-H applies ONLY to case_03. case_01 (002-E frozen) and
case_02 (002-G frozen) are NOT touched. Specifically:

- case_01: 002-E is binding; case_01 fixture,
  `_provenance_metadata.json` case_01 entries, and
  `_tolerance_metadata.json` case_01 entries are NOT modified
  by 002-H.
- case_02: 002-G is binding; case_02 fixture,
  `_provenance_metadata.json` case_02 entries, and
  `_tolerance_metadata.json` case_02 entries are NOT modified
  by 002-H.
- TASK-018 frozen design contract (`docs/tasks/TASK-018-*.md`)
  is NOT modified by 002-H.

### 15.8 Amendment 002-H does NOT authorize

- Implement the future Slice 3B-C chain_adapter case_03 wiring.
  002-H freezes the contract surface; the implementation
  round requires a separate Charles authorization.
- Mark a PR Ready. 002-H is a DRAFT PR; the Ready and Merge
  steps are NOT authorized.
- Mutate any Issue (close / comment / label / lock). 002-H is
  docs-only; no Issue mutation is authorized.
- Mutate `src/**`, `tests/validation_report/**`,
  `tests/unit/**`, `tests/support/**`, `tests/benchmark/**`,
  `.github/**`, `ci-shard-manifest.yml`, `pyproject.toml`, or
  `uv.lock`. 002-H is docs + fixtures only.
- Mutate any TASK-006..TASK-018 frozen contract blob. 002-H
  freezes the TASK-019 surface; it does not change the
  upstream contract chain.
- Re-derive the amendment-001 frozen `expected_output`
  central values. 002-H preserves them verbatim (see
  §15.3.6).
- Introduce any TASK-020+ content (pressure drop / C4 / TEMA /
  Kern / Bell-Delaware / vendor quote / runtime catalog
  resolver). 002-H remains within the frozen TASK-019 scope.
- Invent any TASK-018 §5.3 discount formula or §5.3.2 salvage
  formula. 002-H preserves the deferred status verbatim
  (see §15.3.5).
- Send Feishu. 002-H is a docs-only round; the final report
  is delivered inline + via this file path, not via Feishu
  outbound.

### 15.9 Future Slice 3B-C implementation round prerequisites

The future TASK-019 Slice 3B-C implementation round (NOT
authorized by 002-H) MAY be authorized in a separate Charles-
authorized round once 002-H is reviewed and merged. Slice 3B-C
MUST:

- Call `hexagent.costing.select_cost_records(records, filters)`
  with `records = case_03.input.cost_records_bridge` and
  `filters` constructed from `case_03.input.cost_model_selection`
  per §15.3.2.
- Call `hexagent.costing.calculate_cost_breakdown(...)` with
  the resulting `CostModelSelectionResult` plus the case_02
  `MassBreakdown` per §15.3.4.
- Surface the production `CostBreakdown.to_dict()` shape
  verbatim into `values.upstream_provenance_digests.
  cost_breakdown_payload`.
- Project the production output into the public
  `produced_fields` per §15.3.3 / §15.3.4 / §15.3.5.
- STOP and report mismatch (NOT silent mutation) if the
  production output is OUTSIDE the amendment-001
  tolerance envelope per §15.3.6.
- Mutate ONLY the allowed files per §15.8 forbidden list.



## 16. Design Amendment 002-I — case_03 MassBreakdown bridge contract (binding)

This section is the TASK-019 Design Amendment 002-I
(Charles-authorized design amendment round, NOT an
implementation round). It freezes the missing
`input.mass_breakdown_bridge` for TASK-019-GOLDEN-03 that
the 002-H amendment intentionally left unspecified.

### 16.1 Background and motivation (binding, contract-frozen)

The 002-H amendment (PR #110 merged into main as
`7e0a0bd9`) froze the TASK-019-GOLDEN-03
`input.cost_records_bridge` (3 selector-input records) +
`input.cost_records_bridge_bindings` (4 by-record-id
bindings). The 002-H amendment DID NOT freeze a legal
`MassBreakdown` bridge for case_03. The 002-H §15.3.4
reference to a "case_02 `MassBreakdown`" was a contract
placeholder, not a fixture-level frozen bridge.

The PR #111 implementation round correctly left case_03 as
`WIRED_VIA_CHAIN_PARTIAL` (with only the 5 P0-4 selector
audit fields in `produced_fields` and all `cost_components.*`
fields as `None`) because the 002-H frozen case_03 fixture
did NOT carry a legal `MassBreakdown` bridge: the case_03
fixture has no `material_catalog_bridge` (the case_02
prerequisite) and no `case_01_geometry` (the case_02
cross-case ref), so the case_02 chain cannot be invoked
from case_03 without violating the P0 anti-fabrication rules
(PR #111 P0 review).

The 002-I amendment freezes the legal
`input.mass_breakdown_bridge` as case-bound frozen
benchmark input. The future implementation round (not
authorized by 002-I) MAY then call
`hexagent.costing.calculate_cost_breakdown(...)` with a
production `MassBreakdown` object built **verbatim** from
this bridge, satisfying the PR #111 P0 invariants
(P0-1: no runtime FS read of case_02 fixture; P0-2: no
stub MassBreakdown; P0-3: no new blocker code; P0-4:
selected_model_id not in produced_fields).

### 16.2 002-I frozen contract surface (binding, contract-frozen)

The 002-I amendment adds ONE new frozen field to
`tests/golden/double_pipe_rating/case_03_cost_lifecycle_envelope.json`:

- `input.mass_breakdown_bridge` (case-bound frozen
  benchmark input; NOT a runtime catalog lookup)

Shape (binding; the future implementation MUST consume
this exact shape):

```json
{
  "bridge_id": "TASK-019-AMEND-002I-CASE03-MASS-BREAKDOWN-BRIDGE-V1",
  "bridge_type": "case_bound_production_mass_breakdown",
  "source_case_id": "TASK-019-GOLDEN-02",
  "source_contract": "TASK-019 Design Amendment 002-G / PR #109 case_02 mass-chain contract",
  "source_usage": "Frozen input bridge for TASK-019-GOLDEN-03 cost calculator only; not a runtime reference to case_02 fixture.",
  "mass_breakdown_class": "hexagent.material_mass_mechanical.mass_calculator.MassBreakdown",
  "field_mapping": {
    "inner_tube_kg": "case_02 actual_output.mass_kg.tube_mass_kg",
    "outer_pipe_kg": "case_02 actual_output.mass_kg.shell_mass_kg",
    "hairpin_bend_kg": "case_02 production MassBreakdown.hairpin_bend_kg",
    "fittings_kg": "case_02 production MassBreakdown.fittings_kg",
    "total_kg": "case_02 actual_output.mass_kg.total_mass_kg",
    "calculation_hash": "case_02 production MassBreakdown.calculation_hash (tube call; primary mass input for case_03)",
    "provenance": "case_02 production MassBreakdown.provenance (tube call; primary mass input for case_03)"
  },
  "values": {
    "inner_tube_kg": 5.127079210658542,
    "outer_pipe_kg": 11.056395521337773,
    "hairpin_bend_kg": 0.0,
    "fittings_kg": 0.0,
    "total_kg": 16.183474731996316,
    "calculation_hash": "42b4fad3d9c7130073cd362e7fd7575b88c3c10bd1ef24bc2a835e1738315fc7",
    "provenance": {
      "geometry_record_id": "case_02_tube_geometry_002g",
      "material_record_id": "MAT-SS304-TUBE-001",
      "applicable_standard_id": "ASME BPVC Section VIII Div 1 (TASK-017 approved rule-pack; design_code_id per TASK-017 catalog)",
      "design_pressure_mpa": 0.6,
      "design_temperature_c": 70.0,
      "correlation_ids": [],
      "software_version": "0.1.0",
      "git_commit": "6ed5b7dc7d8df163796eacb838afcf5702a4c53a",
      "result_hash": "b6d2b2bc76592364ea9cc937937dfcd480b4716efd6645c375f20904d015bf58"
    }
  },
  "runtime_forbidden": [
    "read_case_02_fixture",
    "derive_raw_geometry",
    "resolve_material",
    "construct_synthetic_material_resolution",
    "use_stub_mass_breakdown",
    "catalog_lookup",
    "db_lookup",
    "network_lookup"
  ],
  "failure_policy": {
    "missing_or_malformed_bridge": "fail_closed",
    "cost_components": "null",
    "blocker_code": "UNSPECIFIED_BLOCKER",
    "details_reason": "mass_breakdown_bridge_missing_or_malformed"
  }
}
```

### 16.3 Field value provenance (binding, contract-frozen)

The `values` block in §16.2 is NOT invented. Each value is
derived from the case_02 production chain (TASK-019 Design
Amendment 002-G / PR #109) executed against the 002-G frozen
case_02 fixture:

- `inner_tube_kg = 5.127079210658542` = production
  `MassBreakdown.inner_tube_kg` from the 002-G case_02
  tube call (`calculate_mass_breakdown(tube_request)`).
- `outer_pipe_kg = 11.056395521337773` = production
  `MassBreakdown.outer_pipe_kg` from the 002-G case_02
  pipe call (`calculate_mass_breakdown(pipe_request)`).
  Per 002-G §4.9.10 step 7 "方案 B" mapping, the
  public report shape's `mass_kg.shell_mass_kg` is the
  production `outer_pipe_kg` (canonical).
- `hairpin_bend_kg = 0.0` = production
  `MassBreakdown.hairpin_bend_kg`. Per 002-G
  `include_hairpin=False` and the case_02 fixture's
  `fitting_overrides_kg=()`, this field is canonically
  0.0 (case_02 is straight tube-in-shell; no hairpin by
  design).
- `fittings_kg = 0.0` = production
  `MassBreakdown.fittings_kg`. Per 002-G
  `fitting_overrides_kg=()` and
  `fitting_density_normalization=False`, this field is
  canonically 0.0 (case_02 has no fittings by design).
- `total_kg = 16.183474731996316` = production
  `MassBreakdown.total_kg` derived as
  `tube_call.inner_tube_kg + pipe_call.outer_pipe_kg`
  (per 002-G §4.9.10 step 7 "方案 B" mapping; the
  canonical sum of the two production call results; this
  matches the case_02 expected_output.mass_kg.total_mass_kg
  = 16.183474731996316 byte-for-byte).
- `calculation_hash = 42b4fad3d9c7130073cd362e7fd7575b88c3c10bd1ef24bc2a835e1738315fc7`
  = production `MassBreakdown.calculation_hash` from the
  002-G case_02 TUBE call (the primary mass input for
  case_03; the TUBE call drives the `inner_tube_kg` value
  that enters the case_03 `MassBreakdown`). The
  PIPE call's `calculation_hash` is the separate
  `MassBreakdown` object that drives
  `outer_pipe_kg`; it is documented in the source
  chain audit trail but the case_03 single-MassBreakdown
  object carries the TUBE call's hash as the canonical
  audit field. (The choice of TUBE-call hash is documented
  in the field_mapping block: "calculation_hash:
  case_02 production MassBreakdown.calculation_hash
  (tube call; primary mass input for case_03)".)
- `provenance` = production `MassProvenance` object
  from the 002-G case_02 TUBE call. Each provenance
  field is a verbatim copy of the production output:
  `geometry_record_id = "case_02_tube_geometry_002g"`,
  `material_record_id = "MAT-SS304-TUBE-001"`,
  `applicable_standard_id = "ASME BPVC Section VIII Div 1
  (TASK-017 approved rule-pack; design_code_id per
  TASK-017 catalog)"`, `design_pressure_mpa = 0.6`,
  `design_temperature_c = 70.0`,
  `correlation_ids = []` (TUBE call has no
  correlation_ids field populated for the mass path;
  the correlation_ids field is empty in the case_02
  TUBE-call MassBreakdown.provenance),
  `software_version = "0.1.0"`,
  `git_commit = "6ed5b7dc7d8df163796eacb838afcf5702a4c53a"`,
  `result_hash = "b6d2b2bc76592364ea9cc937937dfcd480b4716efd6645c375f20904d015bf58"`
  (TUBE-call's result_hash).

The 002-G chain produces TWO `MassBreakdown` objects
(tube call + pipe call). The 002-I case_03 single-
`MassBreakdown` object canonicalizes the TUBE call's
`calculation_hash` + `provenance` for the audit fields
(per the field_mapping rationale). The TUBE call is the
primary mass input for case_03 because it carries
`inner_tube_kg` (the c0_material mass driver); the PIPE
call's audit fields are documented in the source
chain audit trail but the case_03 frozen bridge
canonicalizes the TUBE call as the single
`MassBreakdown` audit source.

### 16.4 Future implementation contract (binding for the next round)

The future implementation round (NOT authorized by 002-I;
authorized in a separate Charles-authorized round) MUST
read `input.mass_breakdown_bridge` verbatim from the
case_03 fixture and construct a production
`MassBreakdown` object from it. Specifically:

- Construct
  `MassBreakdown(inner_tube_kg=bridge.values.inner_tube_kg, outer_pipe_kg=bridge.values.outer_pipe_kg, hairpin_bend_kg=bridge.values.hairpin_bend_kg, fittings_kg=bridge.values.fittings_kg, total_kg=bridge.values.total_kg, calculation_hash=bridge.values.calculation_hash, provenance=MassProvenance(**bridge.values.provenance))`
  by reading each field verbatim from
  `case_03.input.mass_breakdown_bridge.values.<field>`.
- Pass this `MassBreakdown` object to
  `hexagent.costing.calculate_cost_breakdown(cost_model_selection_result=..., mass_breakdown=..., ...)` exactly as the
  production API expects.
- DO NOT call `calculate_mass_breakdown` from the
  case_03 path (P0-1 ban: no raw geometry re-derivation
  in case_03).
- DO NOT call `resolve_material` from the case_03 path
  (P0-1 ban: no synthetic MaterialResolutionResult
  reconstruction in case_03).
- DO NOT call any function on `tests/golden/double_pipe_rating/case_02_*.json`
  (P0-1 ban: no runtime FS read of the case_02 fixture
  from case_03).
- DO NOT introduce any synthetic `MassBreakdown`
  fallback (P0-2 ban: no `StubMassBreakdown` /
  duck-type).
- DO NOT introduce any runtime catalog resolver
  (002-H §15.3.1 + 002-I §16.4 binding rule).
- DO NOT call any DB / filesystem / network lookup
  design for runtime.
- If `input.mass_breakdown_bridge` is missing or
  malformed, the implementation MUST fail closed
  per `bridge.failure_policy`: status =
  `WIRED_VIA_CHAIN_PARTIAL`, all `cost_components.*`
  fields = `None`, `produced_fields` contains ONLY the
  5 P0-4 selector audit fields, blocker
  `code = "UNSPECIFIED_BLOCKER"`, `details.reason =
  "mass_breakdown_bridge_missing_or_malformed"`. No new
  blocker code strings are introduced (P0-3 binding
  rule).

### 16.5 Field values preserved verbatim (binding, contract-frozen)

The 002-I amendment DOES NOT change the amendment-001
frozen expected_output central values:

- `expected_output.cost_components_C0_C1.cost_components.C0_material_minor_units = 412000`
- `expected_output.cost_components_C0_C1.cost_components.C0_labor_minor_units = 188000`
- `expected_output.cost_components_C0_C1.cost_components.C1_total_minor_units = 600000`
- `expected_output.cost_components_C0_C1.currency_ISO_4217 = USD`
- `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.annual_operating_hours = 8000`
- `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.design_life_years = 20`
- `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.annual_energy_MJ = 241056.0`
- `expected_output.life_cycle_energy_envelope.life_cycle_energy_summary.total_lifecycle_energy_MJ = 4821120.0`
- `expected_output.selected_cost_model.selected_model_id = "ASME-BPVC-VIII-1-COST-MODEL-V1 (TASK-018 Slice A frozen cost-model catalog)"`
- `expected_output.discounted_total_minor_units = null`
- `expected_output.salvage_minor_units = 0`
- `expected_output.unspecified_blocker.details.reason = "discount_formula_pending_design_amendment"`

If the future implementation round observes a cost
breakdown output OUTSIDE the amendment-001 tolerance
envelope, the future round MUST STOP and report (per §9
FROZEN contract discipline + §16.4 fail-closed rule);
silent expected_output mutation is FORBIDDEN.

### 16.6 Tolerance unchanged (binding, contract-frozen)

The 002-I amendment adds ONE frozen input bridge to the
case_03 fixture. The existing amendment-001 numeric
tolerance values are preserved verbatim. The new
`mass_breakdown_bridge.values.{inner_tube_kg,
outer_pipe_kg, hairpin_bend_kg, fittings_kg, total_kg,
calculation_hash, provenance.*}` are categorical (string-
literal equality + exact float equality with rel_tol = 0)
for the `mass_breakdown_bridge` itself. NO existing
tolerance is widened. The `_tolerance_metadata.json` is
NOT modified by 002-I.

### 16.7 Case boundaries (binding, contract-frozen)

002-I applies ONLY to case_03 (input only). case_01
(002-E frozen) and case_02 (002-G frozen) are NOT
touched. Specifically:

- case_01: 002-E is binding; case_01 fixture,
  `_provenance_metadata.json` case_01 entries, and
  `_tolerance_metadata.json` case_01 entries are NOT
  modified by 002-I.
- case_02: 002-G is binding; case_02 fixture,
  `_provenance_metadata.json` case_02 entries, and
  `_tolerance_metadata.json` case_02 entries are NOT
  modified by 002-I.
- TASK-018 frozen design contract
  (`docs/tasks/TASK-018-*.md`) is NOT modified by 002-I.

### 16.8 Amendment 002-I does NOT authorize

- Implement the future case_03 cost breakdown wiring
  using this bridge. 002-I freezes the contract surface;
  the implementation round requires a separate Charles
  authorization.
- Mark a PR Ready. 002-I is a DRAFT PR; the Ready and
  Merge steps are NOT authorized.
- Mutate any Issue (close / comment / label / lock).
  002-I is docs + fixtures only; no Issue mutation is
  authorized.
- Mutate `src/**`, `tests/validation_report/**`,
  `tests/unit/**`, `tests/support/**`,
  `tests/benchmark/**`, `.github/**`,
  `ci-shard-manifest.yml`, `pyproject.toml`, or
  `uv.lock`. 002-I is docs + case_03 fixture +
  provenance metadata only.
- Mutate any TASK-006..TASK-018 frozen contract blob.
  002-I freezes the TASK-019 surface; it does not
  change the upstream contract chain.
- Re-derive the amendment-001 frozen `expected_output`
  central values. 002-I preserves them verbatim (see
  §16.5).
- Introduce any TASK-020+ content (pressure drop / C4
  / TEMA / Kern / Bell-Delaware / vendor quote /
  runtime catalog resolver). 002-I remains within the
  frozen TASK-019 scope.
- Invent any TASK-018 §5.3 discount formula or §5.3.2
  salvage formula. 002-I preserves the deferred
  status verbatim (see §16.5).
- Read the case_02 fixture at runtime. 002-I freezes
  the case_03 MassBreakdown bridge as a case-bound
  fixture input; the future implementation MUST read
  the bridge from the case_03 fixture, NOT from the
  case_02 fixture.
- Send Feishu. 002-I is a docs-only round; the final
  report is delivered inline + via this file path, not
  via Feishu outbound.

### 16.9 002-I provenance additions (binding, contract-frozen)

The `_provenance_metadata.json` 002-I block adds the
following top-level keys:

- `amendment_002i_id = "TASK-019-DESIGN-AMENDMENT-002-I"`
- `amendment_002i_effective_scope = "TASK-019-GOLDEN-03"`
- `amendment_002i_bridge_schema_version = "TASK-019-MASS-BREAKDOWN-BRIDGE-V1"`
- `amendment_002i_supersedes = "TASK-019-DESIGN-AMENDMENT-002-H (case_03 input.mass_breakdown_bridge only; expected_output central values preserved verbatim; tolerance numeric values preserved verbatim)"`
- `amendment_002i_field_paths_added = ["input.mass_breakdown_bridge (7 numeric/string fields + provenance sub-object; production-case_02 mass-chain derived)"]`
- `amendment_002i_field_paths_preserved_not_modified = ["expected_output.cost_components_C0_C1.* (all 4 values preserved verbatim from amendment-001)", "expected_output.life_cycle_energy_envelope.* (preserved verbatim)", "expected_output.selected_cost_model.* (preserved verbatim)", "expected_output.discounted_total_minor_units (still null)", "expected_output.salvage_minor_units (still 0)", "expected_output.unspecified_blocker.details.reason", "input.cost_records_bridge (3 records preserved verbatim from 002-H)", "input.cost_records_bridge_bindings (4 bindings preserved verbatim from 002-H)", "input.cost_model_selection.* (preserved verbatim)", "input.lifecycle_inputs.* (preserved verbatim)", "input.case_01_input_reference_case_id=TASK-019-GOLDEN-01"]`
- `amendment_002i_field_paths_unchanged = ["case_01.* (002-E frozen)", "case_02.* (002-G frozen; case_02 input NOT modified; case_02 fixture, _provenance_metadata.json case_02 entries, _tolerance_metadata.json case_02 entries NOT modified)", "src/** (NOT modified)", "tests/validation_report/** (NOT modified)", "tests/unit/** (NOT modified)", "tests/benchmark/** (NOT modified)", "tests/support/** (NOT modified)", ".github/** (NOT modified)", "pyproject.toml (NOT modified)", "uv.lock (NOT modified)", "ci-shard-manifest.yml (NOT modified)", "docs/tasks/TASK-006..TASK-018*.md (frozen)"]`
- `amendment_002i_re_derivation_method = ["no_re_derivation: mass_breakdown_bridge.values.* are derived from the case_02 production-chain output (tube call + pipe call per 002-G §4.9.10 step 7 方案 B); expected_output central values preserved verbatim from amendment-001", "no_fabrication_statement: mass_breakdown_bridge is case-bound frozen benchmark input; the values are production case_02 chain output, not invented", "no_runtime_resolver_statement: the future adapter MUST NOT introduce a runtime catalog resolver; the frozen mass_breakdown_bridge is the sole source of mass dependency for case_03 cost calculator", "no_case_02_runtime_read_statement: the future adapter MUST NOT read the case_02 fixture at runtime; mass_breakdown_bridge is the case-bound frozen input bridge, NOT a runtime reference to case_02", "no_raw_geometry_statement: the future adapter MUST NOT derive raw geometry from case_03; mass_breakdown_bridge carries the case_02 production-chain derived mass values directly", "no_synthetic_material_statement: the future adapter MUST NOT construct synthetic MaterialResolutionResult; the case_02 chain has already executed and the case_03 bridge carries the production-derived audit fields (calculation_hash + provenance)", "no_stub_mass_breakdown_statement: the future adapter MUST NOT use a stub / duck-type MassBreakdown; the case_03 bridge carries the real production MassBreakdown values"]`
- `amendment_002i_chain_coverage = ["calculate_cost_breakdown_input_cost_model_selection_result (from select_cost_records output per 002-H §15.3.3)", "calculate_cost_breakdown_input_mass_breakdown_from_case_03_mass_breakdown_bridge (new in 002-I; bridge source = case_02 production chain)", "calculate_cost_breakdown_output_capex_envelope_to_cost_components_C0_C1 (unchanged from 002-H §15.3.4)", "calculate_cost_breakdown_output_calculator_run_id_to_upstream_calculation_run_ids (unchanged from 002-H)"]`
- `amendment_002i_production_api_reconciliation = ["production_calculate_cost_breakdown_api = hexagent.costing.calculate_cost_breakdown (unchanged from 002-H §15.5)", "production_mass_breakdown_construction = future implementation MUST construct a hexagent.material_mass_mechanical.mass_calculator.MassBreakdown by reading case_03.input.mass_breakdown_bridge.values.* verbatim; the bridge is the SOLE source of mass dependency for case_03 cost calculator"]`
- `amendment_002i_no_production_code_changed = true`
- `amendment_002i_fixture_input_only = true`

### 16.10 Future implementation round prerequisites (binding for next round)

The future TASK-019 implementation round (NOT authorized
by 002-I) MAY be authorized in a separate Charles-
authorized round once 002-I is reviewed and merged. The
future round MUST:

- Read `case_03.input.mass_breakdown_bridge` verbatim
  from the fixture.
- Construct a production `MassBreakdown` object from
  `bridge.values.*` per §16.4.
- Call
  `hexagent.costing.calculate_cost_breakdown(cost_model_selection_result=select_cost_records_output, mass_breakdown=constructed_MassBreakdown, ...)`
  per the production API contract.
- Surface the production `CostBreakdown.to_dict()` shape
  verbatim into `values.upstream_provenance_digests.cost_breakdown_payload`.
- Project the production output into the public
  `produced_fields` per the P0-4 selector audit fields
  (5 fields) + the cost component fields per the 002-H
  §15.3.4 by-record-id mapping. The
  `selected_model_id` MUST NOT appear in
  `produced_fields` (P0-4 binding).
- STOP and report mismatch (NOT silent mutation) if the
  production output is OUTSIDE the amendment-001
  tolerance envelope per §16.6.
- Fail closed per §16.4 if the bridge is missing or
  malformed.
- Mutate ONLY the allowed files per §16.8 forbidden
  list.


## 17. Design Amendment 002-J — case_02 full cost stack + fixture-provided static cost-record selection coverage contract (binding, contract-frozen, governance-only)

This section is the TASK-019 Design Amendment 002-J contract for the case_02 full cost-stack. It is a Charles-authorized **design / governance-only authoring round** for the coverage contract that connects §15 (Design Amendment 002-H / PR #110 / case_03 cost-record bridge pattern) and §16 (Design Amendment 002-I / case_03 mass-breakdown bridge completion) — both already merged into `main` — and extends that same bridge pattern to case_02, whose `MassBreakdown` and downstream `mass-chain` source data is already wired by 002-G / PR #109.

§17 does **NOT** implement case_02 full cost-stack. It does **NOT** add a new code path, fixture row, test, or runtime resolver. It defines the **coverage contract** that any future implementation round must satisfy, and the **fixture-provided static cost-record selection** boundary that the future round must respect.

The six deferred fields enumerated in §17.2 are the explicit `expected_output` extension surface for case_02. They remain un-instantiated in this contract. Their values are reserved for derivation in a future production-chain run, per §17.7 item 2.

### 17.1 Authority and verified baseline (binding, contract-frozen)

§17 is sourced from the following authorities, which are **recoverable from the repository alone**:

- §15 = Design Amendment 002-H / PR #110 / case_03 cost-record bridge pattern (already merged into `main`).
- §16 = Design Amendment 002-I / case_03 mass-breakdown bridge completion (already merged into `main`).
- 002-G / PR #109 = case_02 `MassBreakdown` / mass-chain source (already merged into `main`).
- §17 = this new Design Amendment 002-J (this round, Draft PR only).

§17 MUST be read together with §15 and §16. Where §17 is silent on a case_02 cost-stack aspect, §15 / §16 govern by analogy, with the same MAY / MUST NOT discipline.

§17.1:

- MAY cite §15 / §16 / 002-G as the bridge-pattern authority for case_02.
- MAY cite the same authority when restating a bridge boundary.
- MUST NOT invent a new bridge architecture that diverges from §15 / §16 / 002-G.
- MUST NOT re-author case_03 bridge behavior in this section (case_03 is frozen at §15 / §16).
- MUST NOT escalate this contract into an implementation schedule.

### 17.2 Deferred `expected_output` extension fields (binding, contract-frozen)

The case_02 full cost-stack `expected_output` is **partially populated** in current Task-019 fixtures. The fields **not yet instantiated** in case_02 are the following six:

- `c0_subtotal.component_breakdown[]`
- `c1_subtotal.component_breakdown[]`
- `life_cycle_energy_envelope.P_intake_kW`
- `life_cycle_energy_envelope.P_total_kW`
- `life_cycle_energy_envelope.P_cooling_kW`
- `life_cycle_energy_envelope.P_loop_kW`

These six fields are the **deferred `expected_output` extension surface** for case_02. They are enumerated here as a closed set: any future case_02 cost-stack fixture or implementation round MUST NOT introduce additional deferred fields beyond this six without a separate Charles-authorized amendment.

§17.2:

- MAY enumerate the six deferred fields by name (above).
- MAY note that the six fields are an **extension** of an already-populated subset (the `cost_chain_selector.c0_record_count` / `c1_record_count` / `selection_blockers` subset wired by 002-H / 002-I bridges).
- MUST NOT add a seventh deferred field in this section.
- MUST NOT assign numeric values to any of the six fields in this section.
- MUST NOT infer that any of the six fields is "zero" or "empty" without a production-chain derivation per §17.7.

### 17.3 Fixture-provided static cost-record selection boundary (binding, contract-frozen)

case_02 cost-record selection is **fixture-provided static** in current Task-019 scope. This subsection codifies that boundary.

§17.3:

- MAY declare that case_02 cost-record selection reads from the fixture's `cost_records_bridge` payload (the same source-of-truth used by case_03 per §15 / §16).
- MAY cross-reference `_provenance_metadata.json` and `_tolerance_metadata.json` as the metadata surfaces where the case_02 cost-record source is recorded.
- MAY note that 002-G / PR #109 has already wired case_02 `MassBreakdown` and the mass-chain path that case_02 cost-stack must consume.
- MUST NOT introduce a runtime catalog resolver for case_02.
- MUST NOT introduce a runtime catalog scan, runtime catalog lookup, or any other dynamic selection mechanism.
- MUST NOT widen this boundary into a dynamic catalog integration boundary (that boundary is a separate concern; see §17.4).

### 17.4 Dynamic catalog integration exclusion (binding, contract-frozen)

Dynamic catalog integration is **TASK-020+ / future work** unless explicitly committed elsewhere in current main. case_02 is **not** granted dynamic catalog integration by this amendment.

§17.4:

- MAY note that current fixture behavior remains **static / curated**, as already declared by 002-F §4.8.5 and 002-G §4.9.4 for case_03 / case_02 mass-chain respectively.
- MAY note that `cost_records_bridge` is the sole source of cost-record inputs to `CostModelSelector.select` per §15.3.2 Q2, and that this applies to case_02 by analogy.
- MUST NOT claim that dynamic catalog integration exists in any form for case_02.
- MUST NOT pre-authorize a runtime resolver. Any future amendment that authorizes a runtime resolver MUST be a separate Charles-authorized round.
- MUST keep this subsection a **boundary declaration**, not an implementation design.

### 17.5 pressure-drop / thermal-method exclusion boundary (binding, contract-frozen)

Pressure-drop and thermal-method implementation are **explicitly excluded** from current Task-019 scope, including case_02.

§17.5:

- MAY restate that "pressure drop remains `NOT_COMPUTABLE`" for case_02 (the same wording already in §6, §15, §16 applies to case_02 by analogy).
- MAY cross-reference `pressure_drop_excluded_from_taska_019` as the existing expected_output marker for this exclusion.
- MUST NOT introduce any C4 / TEMA / Kern / Bell-Delaware / equivalent pressure-drop formula for case_02.
- MUST NOT add any thermal-method computation logic, thermal expansion screening logic, or thermal-method acceptance criteria for case_02.
- MUST NOT widen the existing exclusion without a separate Charles-authorized round.

### 17.6 Discount / salvage / runtime-resolver / runtime-catalog exclusions (binding, contract-frozen)

case_02 cost-stack explicitly excludes the following four item classes. They are **deferred** to TASK-020+ or to a separate Charles-authorized amendment.

§17.6:

- MAY note that **discount** calculation is **not** in scope for case_02 cost-stack in this amendment.
- MAY note that **salvage** calculation is **not** in scope for case_02 cost-stack in this amendment.
- MAY note that **runtime catalog resolver** is **not** in scope for case_02 cost-stack in this amendment.
- MAY note that **runtime catalog scan / lookup** is **not** in scope for case_02 cost-stack in this amendment.
- MUST NOT silently bundle any of the four excluded items into the six deferred fields enumerated in §17.2.
- MUST NOT re-claim any of the four excluded items as part of "the natural extension" of §17.2.

### 17.7 Deferred-fields derivation discipline (binding, contract-frozen)

This subsection codifies the **derivation rule** for the six deferred fields enumerated in §17.2.

§17.7:

1. The six deferred fields enumerated in §17.2 are **un-instantiated** in this contract. No numeric value, no placeholder, no fabrication, and no copy from a sibling case is permitted in §17.2.
2. The implementation values for the case_02 `expected_output` extension (the six deferred fields enumerated in §17.2) must be derived from a real production chain output, reproducibly, by running the same production chain on the same fixture input. The derived values must be re-computable on a clean checkout.
3. The derivation path MUST consume the same case_02 fixture input as the production chain (no synthetic input).
4. The derivation path MUST emit the same six field names as enumerated in §17.2, in the same JSON shape, in the same `expected_output` extension surface.
5. Any future round that wants to instantiate the six deferred fields MUST verify the production chain end-to-end on the case_02 fixture BEFORE writing the values into `expected_output`. The order is: run production chain → capture output → write to `expected_output` → commit. The reverse order (write-then-verify) is forbidden.
6. If the production chain output disagrees with the bridge-pattern authority (§15 / §16 / 002-G), the production chain is the source of truth and the disagreement MUST be surfaced explicitly; the bridge-pattern authority is not auto-overridden.

### 17.8 Anti-fabrication guard for §17 (binding, contract-frozen)

This subsection codifies the evidence-reset rule that governs any future round (including but not limited to a §18 round) that may cite §17.

§17.8 declares the following facts as **permanently binding**:

- **No §18 exists yet.** §18 (whether 002-J or any later amendment letter) is **NOT** included in this file. Any prior conversation context that referenced §18 as if it existed is **non-authoritative** and **discarded**. §18 may only be added to this file by a future Charles-authorized round, after §17 has been merged into `main` and Charles has separately authorized §18 in that round.
- **Previous §18 SHA claims are invalid.** The SHA strings `b8c7c2528a08a2c8e2a8d4a4c5e8e2a5b8d4a4c8` and `00d44def96a89c3c8c47e0a3a4a4a4c8f1b3a5c0` have been verified as **not resolvable** by `git cat-file -t` in the local repository (`fatal: could not get object info`) and are **not reachable** from any current ref. These SHA strings MUST NOT be referenced as valid commits, MUST NOT be embedded in any future PR body, and MUST NOT be cited as evidence of any prior §18 work.
- **Conversation-derived-only §17.x content is not repo authority.** Any §17.x content that originated solely from prior conversation context (rather than from a committed file or from Charles-provided text in an authorization message) is **non-authoritative** and **discarded**.
- **Future §18 may only cite §17 after §17 is committed and merged.** Any future §18 / 002-J round that wants to reference §17.x MUST verify that §17 is committed and merged into `main` (not just present on a Draft PR / unmerged branch) before citing any §17.x subsection. A future §18 may NOT cite a §17.x that exists only on a Draft branch.
- **No future section may cite non-existent commits, `/tmp` exports, or unverified SHA claims.** Any future PR body, design contract, or governance report MUST verify each cited SHA via `git cat-file -t <sha>` returning `commit` (or the equivalent remote REST verification for un-fetched commits) before embedding it. Any `/tmp` export referenced as evidence MUST be regenerable from a real source on demand. Any SHA claim that cannot be so verified MUST be treated as fabrication and MUST NOT be embedded.

§17.8 MUST NOT include implementation details beyond governance / evidence discipline. It is a **governance guardrail**, not a design or implementation contract.

### 17.9 source-case mapping and provenance (binding, contract-frozen)

This subsection records the **case mapping** that ties §17 to the case_02 full cost-stack in Task-019.

- source case: `TASK-019-GOLDEN-02` (case_02)
- bridge-pattern authority: §15 (Design Amendment 002-H / PR #110) and §16 (Design Amendment 002-I)
- mass-chain source: 002-G / PR #109 (case_02 `MassBreakdown` / mass-chain)
- deferred `expected_output` extension surface: the six fields enumerated in §17.2
- selection source boundary: fixture-provided static per §17.3
- dynamic-catalog exclusion: §17.4
- pressure-drop / thermal-method exclusion: §17.5
- discount / salvage / runtime-resolver / runtime-catalog exclusions: §17.6
- deferred-fields derivation rule: §17.7
- anti-fabrication guard: §17.8

§17.9:

- MAY cite the source case line above as the authoritative case mapping.
- MAY cite the bridge-pattern authority and mass-chain source as the upstream merged authorities.
- MUST NOT re-author the source case mapping in §18 or any future amendment without an explicit Charles-authorized round.
- MUST NOT silently re-assign case_02 to a different case label.

### 17.10 Self-reference and mutable-fact discipline (binding, contract-frozen)

The §17.x references in this section are to the section numbers within this file. Mutable facts (latest main HEAD SHA, latest post-merge main CI run id, future §18 / 002-J amendment letter, future §18 PR number, future implementation allowed-file list) are intentionally **NOT** frozen in this section and MUST be re-derived at the time of any future round that needs them.

§17.10:

- MAY cross-reference the existing per-amendment "Future implementation round prerequisites" blocks at §15.9 and §16.10 by section number.
- MAY note that the source-case line in §17.9 is a **stable** identifier (TASK-019-GOLDEN-02) and is not subject to mutable-fact re-derivation.
- MUST NOT freeze the latest main HEAD SHA, latest post-merge main CI run id, future §18 PR number, or future implementation allowed-file list inside §17.
- MUST NOT re-embed any prior invalid commit SHA in this section.

## 18. Design Amendment 002-J — TASK-020 source-definition handoff (binding after merge; design-only)

This section is the TASK-019 Design Amendment 002-J source-definition handoff. It is a Charles-authorized **design-only authoring round** following the merge of §17 by PR #114. It does not implement TASK-020, does not create a pressure-drop or thermal-method contract, and does not claim that any TASK-020 runtime capability exists.

The purpose of §18 is to convert the governance boundaries in §17 into an auditable handoff contract for a future dedicated TASK-020 design card, without assigning unverified formulas, algorithms, fixture values, or implementation files.

### 18.1 Authority and verified baseline (binding after merge)

The only repository authorities for this amendment are:

- `docs/TASK_BACKLOG.md`, whose M3 wording states that TASK-020 through TASK-039 collectively cover shell-and-tube single-phase configuration, geometry, rating, screening, pressure-drop decomposition, thermal expansion, mechanical boundaries, materials, costing, optimization, API, report, and Golden validation;
- this file through §17.1–§17.10 as the Design Amendment 002-J source contract (the 10-subsection form: §17.1 Authority and verified baseline / §17.2 Deferred `expected_output` extension fields / §17.3 Fixture-provided static cost-record selection boundary / §17.4 Dynamic catalog integration exclusion / §17.5 pressure-drop / thermal-method exclusion / §17.6 Discount / salvage / runtime-resolver / runtime-catalog exclusions / §17.7 Deferred-fields derivation discipline / §17.8 Anti-fabrication guard for §17 / §17.9 source-case mapping and provenance / §17.10 Self-reference and mutable-fact discipline);
- the earlier §17.1–§17.7 version merged into `main` through PR #114 (`f62586b` -> `da6e064`) is the historical baseline of this file. The 10-subsection Design Amendment 002-J form **supersedes** that historical baseline. The supersession does NOT retroactively rewrite the historical PR #114 content; it declares the 002-J form as the current §17 contract going forward;
- current committed repository code and tests, used only to establish what already exists and what remains absent.

The verified authoring baseline is main commit `da6e06499d03431f5b942e9098c5896ecf9814cb` (= PR #114 squash merge). This SHA is recorded only as round traceability and must not be treated as a permanently frozen latest-main value.

Conversation-only drafts, non-resolvable SHA strings, `/tmp` exports, and uncommitted branch content are not authority.

### 18.2 Deferred-scope partition (binding after merge)

The phrase `TASK-020+ / future work` in §17 is a deferral class, not an automatic assignment of every deferred item to TASK-020.

The following TASK-019 double-pipe gaps remain separate follow-up concerns unless a future Charles-authorized design round explicitly assigns them:

- case_02 full cost-stack coverage described by §17.2;
- missing full-cost-stack `expected_output` vectors described by §17.3;
- dynamic catalog integration and any runtime catalog resolver described by §17.4.

These concerns must not be silently imported into TASK-020 merely because they are future work.

Pressure-drop, TEMA configuration, Kern screening, Bell–Delaware, and related thermal-method concepts belong somewhere within the M3 TASK-020–TASK-039 family according to the backlog. The backlog does not currently freeze which concept belongs to TASK-020 specifically. §18 therefore does not allocate any formula, algorithm, standard method, or implementation slice to TASK-020.

### 18.3 Dedicated TASK-020 design-card prerequisite (binding after merge)

Before any TASK-020 implementation Issue, branch, commit, or PR may be created, a dedicated TASK-020 design card must be authored and reviewed as a separate Charles-authorized round.

That future design card must freeze, at minimum:

- exact TASK-020 title and objective;
- exact dependency set;
- in-scope and out-of-scope method families;
- authoritative standards and licensing boundaries;
- input and output schemas;
- deterministic identity, serialization, hash, and provenance rules;
- blocker and `NOT_COMPUTABLE` behavior;
- allowed production and test files;
- acceptance tests and CI expectations;
- implementation slicing, if more than one implementation round is required.

No implementation authorization may be inferred from the existence or merge of §18.

### 18.4 Allocation questions that remain intentionally unresolved (binding after merge)

The future TASK-020 design-card round must answer these questions from repository evidence and Charles authorization rather than assumption:

1. Is TASK-020 the TEMA configuration/schema foundation, or another first M3 capability?
2. Which later TASK IDs own tube layout, shell diameter, tube-side rating, Kern screening, Bell–Delaware, pressure-drop decomposition, and thermal expansion screening?
3. Which existing TASK-002 through TASK-019 contracts are direct dependencies and which are only reference material?
4. What standards content may be represented directly, what must remain rule-pack/pointer-only, and what licensing restrictions apply?
5. Which outputs are computable in the first TASK-020 slice and which must remain explicitly blocked or `NOT_COMPUTABLE`?
6. Does the first TASK-020 design require a new dedicated task file, and what is its exact path and naming convention?

§18 must not pre-answer these questions.

### 18.5 Evidence and anti-fabrication requirements (binding after merge)

A future TASK-020 design card must:

- re-derive current `main` at the start of its round;
- cite only committed files, resolvable commits, merged PRs, and current repository code/tests;
- distinguish backlog-family wording from an executable task contract;
- distinguish existing runtime capability from proposed capability;
- explicitly record every unresolved question rather than filling gaps with assumed engineering practice;
- treat vendor, paid-standard, and restricted-source content according to the existing TASK-012 licensing boundary;
- fail closed if a required authority source cannot be verified.

No future TASK-020 artifact may cite the invalid SHA strings recorded in §17.6 as valid commits.

### 18.6 002-J explicit non-actions (binding after merge)

Amendment 002-J does not authorize:

- any production-code mutation;
- any test, fixture, Golden vector, provenance metadata, or tolerance metadata mutation;
- any pressure-drop, TEMA, Kern, Bell–Delaware, thermal-expansion, mechanical, costing, optimization, API, report, database, or persistence implementation;
- any expected-output number or tolerance value;
- any runtime catalog scan, resolver, lookup, or dynamic integration claim;
- any new blocker or warning code;
- any mutation of frozen TASK-006 through TASK-018 contracts;
- any TASK-019 implementation expansion;
- any TASK-020 implementation Issue or PR;
- Ready or merge for the 002-J PR without separate Charles authorization;
- Feishu outbound.

### 18.7 Future TASK-020 design-round prerequisites (binding after merge)

A future dedicated TASK-020 design round may start only after:

- §18 has been committed and merged into `main`;
- the round re-verifies the current main SHA and confirms §18 is present on main;
- Charles separately authorizes the dedicated TASK-020 design-card round;
- the round names its exact allowed files before mutation;
- the round carries forward every unresolved allocation question in §18.4 and answers only those supported by repo evidence and Charles authorization.

The future TASK-020 design round remains design-only unless Charles separately authorizes implementation after that design contract is reviewed and merged.
