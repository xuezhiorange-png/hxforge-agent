# V08-03 Layered Acceptance RFC (review only)

| Field | Value |
|-------|-------|
| **TASK_ID** | `V08_03_ACCEPTANCE_RFC_AND_SHADOW_VALIDATION` |
| **PR** | 325 (Draft) |
| **HEAD** | `dbfc2137de5c1b061d621f33150541de0f5c2ac4` |
| **CI #1574** | See decision doc; lint/manifest/resolve-authority green; some shards timeout or pending |
| **DECISION** | `C_REVIEW_ONLY` |
| **PRODUCTION_CONTRACT_CHANGE_AUTHORIZED** | `false` |
| **ENGINEERING_ACCEPTANCE** | `BLOCKED` |
| **ORIGINAL_PRODUCTION_ACCEPTANCE** | unchanged |

## Purpose

Provide a **reviewable** split between local numerical closure, property consistency, whole-exchanger balance, and equipment design acceptance — **without** changing production thresholds in this PR.

Decision C means: **start formal re-argument of acceptance layering**; it does **not** prove the current C-ULP contract must be relaxed.

## Evidence anchor (e1, Cell 0, frozen-neighbour)

Single production gate at best-known triple (no new root search):

| Quantity | Value |
|----------|-------|
| q (W) | 152845.44912345504 |
| Twi / Two (K) | 308.26850752129053 / 306.52793869715185 |
| R1 / R2 / R3 ratio | 0.9885 / 0.7611 / 22.4251 |
| Task172 gate | BLOCKED |
| `DISTINCT_FULLY_CONVERGED` | 0 |

Error attribution (corrected):

- **Decimal replay (frozen Gi/Go/Rwall)** measures residual **formula** sensitivity at fixed conductances; Δr3/bound3 ≈ 0.02 — **not** proof that CoolProp is dominant.
- **Twi +1 ULP probe with zero Δr3** only shows **insensitivity at that point**; **does not** prove zero property quantization.
- **PRIMARY_NUMERICAL_LIMIT** | **UNRESOLVED** until property uncertainty budget and full-path energy closure are measured.

Artifacts: `/opt/cursor/artifacts/v08_03_acceptance_rfc_shadow_validation.json`

---

## Layer definitions

### L1 — Local heat-transfer equation closure

**Intent:** Verify the three Task172 residual equations at a **single cell / support** with locked request identity.

**Checks (per equation):**

1. Tube-side film: `r1` vs bound1 (C-ULP, W).
2. Wall conduction: `r2` vs bound2.
3. Shell-side film: `r3` vs bound3.

**Identity:** `request_hash`, tube/shell bulk property snapshot IDs, `Gi`, `Go`, `Rwall`.

**Current production source:**

- `eval_trial_residual_gate` — `src/hexagent/exchangers/shell_tube/task172_local_runtime/service.py`
- Roundoff bounds — `recompute_task172_local_roundoff_bounds` (same module)

**C-ULP meaning:** Acceptance bound derived from ULP-scale rounding of **W** residuals; nanowatt-scale at O(10⁵) W duty.

**Known limit:** Binary64 triple `(q,Twi,Two)` may satisfy scalar root brackets without passing L1 on r3.

**Proposed review method (no new constants):** Report `|ri|/boundi` per equation; PASS only if all ≤ 1 under **existing** production bounds until contract is explicitly revised.

---

### L2 — Thermal state and property consistency

**Intent:** Trace enthalpy→temperature→HTC paths and **quantization** separately from L1.

**Checks:**

- Enthalpy reconstruction when `q` changes (BVP cell builder).
- Bulk snapshot at cell mean vs wall HTC corrections (C3, shell correlation).
- Perturbation probes (`q`, `Twi`, `Two` ±1 ULP) with **rebuilt requests** where required.

**Status:** Property uncertainty budget **UNRESOLVED** — insufficient probes for CoolProp P-H plateaus and shell-side state.

**Shadow:** `SHADOW_LAYERED_ACCEPTANCE` records probes only; does not return VALIDATED.

---

### L3 — Whole-exchanger energy and numerical convergence

**Intent:** Independent of L1:

- Tube-side total enthalpy drop vs cell sum of `q`.
- Shell-side total enthalpy rise.
- Axial profile consistency with frozen neighbour policies in PoC.
- N1 / N2 / N4 mesh convergence per existing Task173 rules.

**Current status:** Both candidates **BLOCKED** at Task173; no full axial VALIDATED profile.

**Rule:** **Never** promote L1 local minima to L3 PASS.

---

### L4 — Equipment engineering acceptance

**Intent:** Design-level outcomes (duty, outlet T, Δp, nozzle velocity, LMTD cross, manufacturability).

**Current status:** **BLOCKED** — requires L3 VALIDATED Rating under **ORIGINAL_PRODUCTION_ACCEPTANCE**.

---

## Dual modes

| Mode | Behaviour |
|------|-----------|
| `ORIGINAL_PRODUCTION_ACCEPTANCE` | `validate_candidate_rating` only; existing gates |
| `SHADOW_LAYERED_ACCEPTANCE` | Prototype `shadow_layered_acceptance.py`; all rows `EXPERIMENTAL_NOT_APPROVED`; no production writes |

Implementation: `prototypes/v08_thermal_rating/run_acceptance_rfc_shadow_validation.py`

---

## Dual candidate shadow summary

| Candidate | Original Task173 | Shadow L1 (cell 0) | Shadow L2 | L3/L4 |
|-----------|------------------|-------------------|-----------|-------|
| e1baa795… | BLOCKED `BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED` @ mesh 1 | L1 BLOCKED r3≈22.4× | probes informative; budget UNRESOLVED | L3/L4 BLOCKED |
| 9277ebb8… | BLOCKED `BLOCKED_TASK172_LOCAL_CONSTITUTIVE_CLOSURE` @ mesh 4 | cell0 UNRESOLVED (no frozen triple) | UNRESOLVED | L3/L4 BLOCKED |

---

## Proposed contract changes (require explicit approval)

| # | Current clause (location) | Suggested direction | Evidence | Golden/hash impact | Rollback |
|---|---------------------------|-------------------|----------|-------------------|----------|
| 1 | C-ULP `passes_original_residual_gate` (`service.py` ~775-787) | **No change until approved** | r3≈22× at best cell-0 triple | Any change invalidates Task172 golden gates | Revert single function |
| 2 | (Optional) Layered reporting | Add **read-only** diagnostic export separate from VALIDATED | Shadow JSON | None if not in hash path | Delete prototype |
| 3 | Property uncertainty | Define **measurable** envelope before binding thresholds | UNRESOLVED | TBD | N/A |
| 4 | L3 energy gate | Keep mandatory for ENGINEERING_ACCEPTANCE | 0 full converged | N/A | N/A |

**Numerical kernel change:** Not authorized. Option A (extended-precision `_eval_trial`) remains a **separate** approval from Option C (layering).

---

## Risks if contract relaxed without L2/L3

- Local nanowatt closure while global enthalpy imbalance remains.
- Two geometries with distinct `geometry_projection_hash` may diverge under undocumented tolerance slack.
- Golden Task172/173 replay hashes drift without versioned acceptance schema.

---

## Rollback

1. Revert PR #325 decision docs and prototype runners only (no production edits in this task).
2. Continue `ORIGINAL_PRODUCTION_ACCEPTANCE` exclusively.
3. Discard shadow JSON artifacts.

---

## Approval checklist

- [ ] User sets `PRODUCTION_CONTRACT_CHANGE_AUTHORIZED=true` with clause IDs.
- [ ] Property uncertainty budget measured or explicitly waived with engineering sign-off.
- [ ] Both candidates re-rated under any new L3 rule before ENGINEERING_ACCEPTANCE.

**RFC_READY_FOR_APPROVAL:** `true` (for **process** review, not for merge or tolerance change).
