# TASK-019 — Golden Cases and Double-Pipe Validation Report Design Contract

**Status:** DRAFT / NOT YET FROZEN
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
