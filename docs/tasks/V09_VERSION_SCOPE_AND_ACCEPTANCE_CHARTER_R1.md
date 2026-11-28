# HXForge V0.9 — Version Scope and Acceptance Charter R1

| Field | Value |
|-------|-------|
| **Document status** | `FINAL_SCOPE_REVIEW_PREPARED` — awaiting owner approval before `FROZEN` |
| **Planning TASK_ID** | `V09-00-VERSION_SCOPE_AND_ACCEPTANCE_FREEZE` |
| **Preparation TASK_ID** | `V09-00-FINAL_SCOPE_REVIEW_PREPARATION` |
| **Repository** | `xuezhiorange-png/hxforge-agent` |
| **Baseline tag** | `v0.8.0-rc.1` |
| **Baseline SHA** | `cdd48e361205dd3df1f24007aca36ca3ee048488` |
| **Baseline main CI** | run `46094612999`, `final-gate` = **success** |
| **Target release train** | `v0.9.0-rc.1` (tag/release not authorized by this document) |
| **Version objective** | **工程实用化与计算精度验证** |
| **Thermal/hydraulic authority** | `V08-INDEPENDENT-ENGINEERING-RATING-KERNEL-V1` + `V08-KERNEL-JOINT-HYDRAULIC-INTEGRATION-V1` (inherited; not replaced in V0.9) |
| **Domain envelope** | Steady-state, single-phase **water/water** shell-and-tube automatic sizing / rating within declared catalogs — **no** expansion to other fluids, phases, or exchanger topologies in V0.9 |

---

## 0. Purpose and authority chain

This charter is the **sole scope and acceptance authority** for V0.9 planning and implementation. It supersedes draft planning notes but **does not** modify V0.8 tag `v0.8.0-rc.1`, V07 Golden, or production engineering gates.

**Approval chain**

1. Owner reviews this document (`FINAL_SCOPE_REVIEW_PREPARED`).
2. On approval → status `FROZEN` via **V09-00 docs-only** PR (only after explicit authorization).
3. V09-01+ implementation requires per-task `IMPLEMENTATION_AUTHORIZED` after freeze.

**Independence rule (binding)**

- **HxForge computed outputs SHALL NOT** be used as the independent reference answer for any A-tier or external benchmark row.
- Independent references MUST be: closed-form/analytical derivation, independently hand-calculated spreadsheets with cited formulas, **published** engineering examples with stated inputs, **commercial software exports** with version disclosure, or **owner-supplied device data** with provenance.
- Regression against V0.8 **pinned hashes** (R-tier) is **internal regression**, not an independent accuracy proof.

---

## 1. Version goal and deliverables

### 1.1 Outcome statement

By `v0.9.0-rc.1`, HXForge SHALL provide:

1. **One official engineering compute service** (`run_official_v08_rating_compute` successor boundary) feeding CLI, sync API, stream API, and browser with **field-identical authoritative payloads**.
2. **Installable software** whose **Python package version matches the git tag** and documents what is inside vs outside the wheel.
3. **Frozen acceptance matrix** execution (§5) including accuracy tiers **A1–A4** minimum; **A5** only when device data is supplied.
4. **Engineering calculation book** template with correlation ID, source, envelope, warnings — no compliance sign-off.
5. **Explicit limitations** retained (legacy solver boundary, IPC observables, assumption-K hydraulics, LMTD F table scope).

### 1.2 Inherited from V0.8 (non-negotiable)

| Topic | Rule |
|-------|------|
| V07 Task172/173 / mesh replay | Historical / CI regression; not live design authority |
| Kernel V1 | Live thermal rating authority for V0.8/V0.9 water–water design path |
| Prescreen ε-NTU | Experimental; cannot populate formal production-qualified lists |
| Legacy mesh budget | Subprocess + parent `observables=None` — document, not “fix” via silent IPC |
| Outlet domain (kernel) | 50 kPa floor per `docs/decisions/V08_KERNEL_OUTLET_PRESSURE_DOMAIN_V1.md`; production 100 kPa unchanged on V07 paths |
| Golden files | No mutation |

### 1.3 Prohibited scope extensions (V0.9)

- Two-phase, non-water fluids, plate / air-cooler / microchannel.
- Pressure vessel code compliance, stamped drawings, vendor K authority.
- Full solver rewrite; lowering V07/V08 tolerances; moving `v0.8.0-rc.1`.
- Production hosting, multi-tenant product ops, V0.10 work.
- **Any V09-01…V09-07 code** before charter `FROZEN` + task authorization.

---

## 2. Version task packages (eight tasks — fixed)

| Task | ID | Responsibility (finite) | Depends on | Terminal gate |
|------|-----|-------------------------|------------|---------------|
| V09-00 | Scope & acceptance freeze | This charter → `FROZEN`; ε annex; gap ownership | `v0.8.0-rc.1` | Owner sign-off; docs PR merged |
| V09-01 | Unified compute service & API | Official entry, public DTO, CLI/API parity | V09-00 | I1–I3 automated PASS |
| V09-02 | Model & accuracy verification | Formula registration; A1–A4 harness; literature/public refs | V09-01 | A1–A4 PASS or BLOCKED with disclosure |
| V09-03 | Design, rating, off-design | Fixed-geometry rating; kernel Top-N; mdot on kernel path | V09-01, V09-02 | P-tier + G-08/09/10 closure |
| V09-04 | Engineering UI | Kernel-native browser rendering | V09-01 | I4 PASS |
| V09-05 | Calculation book & packaging | `0.9.0rc1` metadata, entry points, install docs | V09-01–04 | I5 PASS |
| V09-06 | Integrated acceptance | Full matrix runner + CI shard | V09-02–05 | R/P/N/M + A + I all mandatory rows |
| V09-07 | Version integration & release | Tag `v0.9.0-rc.1`, release notes, main CI | V09-06 | Release gate §10 |

**Stop rule (global):** If two consecutive implementation tasks miss terminal gate without charter amendment → **halt V0.9** and reopen V09-00 scope review only.

---

## 3. Verification evidence taxonomy

All acceptance rows MUST declare **one primary evidence class**. Mixed claims are forbidden without layering (e.g. R0 + A3 on same fixture is allowed; using R0 hash as A3 reference is **forbidden**).

| Class | Code | Meaning | Typical source | V0.9 use |
|-------|------|---------|----------------|----------|
| Internal regression | `REG` | Compare to **pinned** prior release/tag hash or approved golden JSON | V0.8 RC baselines, V07 Golden | R-tier |
| Analytical verification | `ANL` | Closed-form or independently derived hand calculation | Textbook LMTD, resistance network algebra, enthalpy balance | A1, parts of A3 |
| Independent literature benchmark | `LIT` | Published example with inputs/outputs in open literature or standards text | TEMA F tables, academic HX examples, ASHRAE/Perry cited problems | A2, A4 (spot) |
| Commercial software benchmark | `COM` | HTRI, STHE, Xphe, etc. export with version + correlation flags | Owner/licensee exports | Optional A3/A4; **not required** if LIT/public substitute registered |
| Actual device validation | `DEV` | Plant test, shop test, OEM data sheet operating point | User-provided (§8) | A5 only |

**Substitute rule:** If `COM` is unavailable, **published engineering worked examples** (`LIT`) with independently stated geometry and boundary conditions MAY satisfy A3/A4 **provided** the example is not generated by HXForge and inputs are transcribed blindly.

**A5 rule:** Without `DEV` data → row status **`NOT_EVALUATED`** — **never PASS**. Release with only `NOT_EVALUATED` A5 requires **separate owner approval** at V09-07 (`RELEASE_WITH_A5_DEFERRED` flag).

---

## 4. Engineering gap register (G-01 … G-12)

| ID | Issue (V0.8 baseline) | Owner task | Closure standard (all required) |
|----|------------------------|------------|----------------------------------|
| **G-01** | Default `kernel_v1` stream API returns `kernel_web_payload`; UI (`web/static/app.js`) renders `design_specification.thermal_experimental_prescreen` | V09-04, V09-01 | I4 PASS: default run shows kernel duty, outlets, U or R-stack, full-path Δp; JSON schema unified; **no blank prescreen panel** |
| **G-02** | Multiple CLI/runner entry paths; prescreen chain not identical to `run_official_v08_rating_compute` | V09-01 | I1–I3: same case JSON → **identical** canonical report hash on official CLI, `POST /api/design/run`, stream `result` event |
| **G-03** | Git tag `v0.8.0-rc.1` vs `pyproject.toml` `0.7.0rc1` | V09-05 | I5: installed `importlib.metadata.version` == `0.9.0rc1` and matches tag at release commit |
| **G-04** | Hatch wheel ships `src/hexagent` only; V08 under `prototypes/` | V09-05 | Documented install paths; either package entry points for official CLI **or** explicit unsupported boundary in calc book — no silent breakage |
| **G-05** | LMTD F: `_f_factor_tema_v1` = 0.98/0.90/0.85 by tube pass; single shell pass literal | V09-02 | A2 executed for registered pass combos OR documented `NOT_APPLICABLE` with citation gap; F sources cited in correlation register |
| **G-06** | U/fouling naming: outer-basis `u_clean_outer_w_m2_k` vs prescreen `overall_ua_w_per_k`; T039 demo fouling | V09-02 | Public DTO documents basis; A3 PASS on hand-audit rows; T039 never in formal qualification class |
| **G-07** | Assumption-K full-path scenarios; `EXPERIMENTAL_ASSUMPTION_K_FULL_PATH_NOT_DESIGN_APPROVAL` | V09-02, V09-03 | Reports label robust vs conditional per scenario; no promotion to “validated K” |
| **G-08** | V08-05 Top-N uses prescreen ranks; `PRODUCTION_RATING_VALIDATED=false`; kernel sort separate | V09-03 | Single authoritative Top-N for kernel path; formal vs experimental lists **consistent** with qualification class definitions |
| **G-09** | No unified product **rating-only** (fixed geometry) CLI/API | V09-03 | Registered rating-only fixture: given bindings JSON → kernel result + hash; documented vs sizing |
| **G-10** | `mdot_verdicts` in autonomous tool only; absent on kernel stream | V09-03, V09-04 | Off-design policy: either kernel mdot tier in matrix **or** explicit `NOT_IN_SCOPE` with owner sign-off in frozen charter |
| **G-11** | Dual outlet pressure domain (kernel 50 kPa vs production 100 kPa) | V09-02 | Calc book + API warnings; no silent merge of domains |
| **G-12** | Legacy mesh IPC `observables=None` | — (retain) | Documented in calc book §limitations; **no closure code required** |

---

## 5. Full acceptance matrix

### 5.0 Cross-cutting rules

| Rule | Detail |
|------|--------|
| Execution authority | Kernel V1 + V08-04 joint hydraulics for P/R/M/I functional tiers unless row says otherwise |
| Property backend | CoolProp version pinned in CI behavior-environment; recorded in each artifact |
| Duty | `Q_actual >= Q_target` within ε_Q (below) unless row expects BLOCKED |
| Full-path Δp | Tube and shell **full-path** each ≤ case limit (not internal-only) |
| Nozzle velocity | 1.0–3.0 m/s on four ports when hydraulics run |
| Independence | No HXForge self-reference for A-tier expected values |
| Hash reproducibility | Same input snapshot + versions → same canonical result hash (± declared drift only on REG rows) |

### 5.1 Functional matrix — R0 / P / N / M

Evidence class: functional tiers use `REG` (R0) or live kernel E2E (P/N/M).

| ID | Class | Evidence | Fixture / construction | Pass criteria | Engineering basis |
|----|-------|----------|------------------------|---------------|---------------------|
| **R0** | Regression | `REG` | `tests/fixtures/v08_user_case_hxforge_330kw_strict_dp.json` | Report + qualification hash **equals** pin at `v0.8.0-rc.1` **or** documented tolerance amendment in charter only | Prevents V0.9 drift on sealed 330 kW envelope (12/20 kg/s, 310/295 K, 1150/1180 Pa) |
| **P1** | Independent design | Live E2E | `tests/fixtures/v08_user_case_no_geometry_task174_admissible.json` (250 kW) | ≥1 candidate `KERNEL_JOINT_E2E_SUCCESS` or documented conditional class with three-K disclosure; duty + both full-path Δp | Independent duty/flow vs R0; charter V08-06 register |
| **P2** | Independent design | Live E2E | `tests/fixtures/v08_user_case_no_geometry_task174_admissible_alt.json` (220 kW) | Same as P1 | Second independent operating point |
| **P3** | Independent design | Live E2E | `tests/fixtures/v08_user_case_p3_kernel_acceptance_v1.json` (275 kW, 11/19 kg/s) | Same as P1; spec `V08-06-P3-kernel-acceptance-spec-r1.md` | Pre-registered acceptance spec |
| **N1** | Negative | Live | Synthetic `V08_06_N1_THERMODYNAMIC_INVALID` (358.15/353.15 K) | `INVALID_INPUT` or thermodynamic block; **no** feasible design emitted | First law / driving force |
| **N2** | Negative | Live | `tests/fixtures/v08_user_case_infeasible_duty_5mw.json` | `NO_FEASIBLE_DESIGN` or empty qualified set with trace | Bounded catalog cannot meet duty |
| **M1** | Metamorphic | Live | R0 schema; `target_duty_w` ×1.10 | Feasible set or margins change consistently; hashes ≠ unchanged R0 | Duty scaling monotonicity |
| **M2** | Metamorphic | Live | R0 schema; both flows ×1.05 | LMTD/capacity response consistent; no silent fixture lock | Flow sensitivity |
| **M3** | Metamorphic | Live | R0 schema; Tin shift +2 K (recorded) | Classification or ranking changes with physics direction | Temperature driving force |
| **M4** | Metamorphic | Live | R0 schema; both Δp limits ×0.80 | Hydraulic feasibility set weakens (never strengthens under tighter Δp) | Constraint monotonicity |

**ε_Q (functional duty)** — inherit V08 kernel contract unless V09-00 annex amends:

- `Q_RELATIVE_TOL = 1e-6`
- `Q_ABSOLUTE_TOL_W = 1.0 W`

**ε_energy** — inherit:

- `ENERGY_RELATIVE_TOL = 1e-4`
- `ENERGY_ABSOLUTE_TOL_W = 10.0 W`

**Metamorphic pass:** At least one of {qualified count, best margin, outcome class, ranking head} must change vs control unless row documents physics-degenerate case (must then BLOCK with reason).

### 5.2 Accuracy matrix — A1 … A5

| ID | Class | Evidence | What is compared | Pass threshold | Engineering basis |
|----|-------|----------|------------------|----------------|-------------------|
| **A1** | Analytical LMTD×F=1 | `ANL` | Kernel scalar loop vs `analytic_parallel_flow_q` / hand LMTD on **synthetic micro geometry** with fixed U, area, cp (fixture frozen **before** code) | \|ΔQ\| ≤ max(1 W, 1e-6·\|Q\|); energy residual per `convergence_pass` | `V08_KERNEL_RATING_ACCEPTANCE_V1`; textbook counterflow LMTD with constant cp |
| **A2** | F factor table | `LIT` | `_f_factor_tema_v1` vs **cited** TEMA/Kern table entries for registered {shell passes, tube passes} | \|ΔF\| ≤ **0.02** absolute **or** stated table uncertainty if wider | TEMA Standards / Kern & Kraus (edition cited in V09-02 register) |
| **A3** | Resistance network | `ANL` + `LIT` | Logged R_i, R_fo, R_fi, R_wall → hand U_o vs `u_clean_outer_w_m2_k` | \|ΔU/U\| ≤ **2%** relative | Series resistance on outer area; Task037 binding |
| **A4** | Hydraulic spot | `LIT` or `COM` | Component Δp breakdown vs public example **or** licensed export | Each component within **5% relative** or **50 Pa** absolute (max) | Darcy–Weisbach / Bell-Delaware itemization; public worked example ID required |
| **A5** | Device | `DEV` | Plant/shop point vs HXForge at **transcribed** conditions | Owner-approved band documented per dataset (e.g. Q ±X%, ΔT ±Y K, Δp ±Z Pa) — **not** auto PASS | Field uncertainty; **if no data → `NOT_EVALUATED` only** |

**A-tier mandatory for V09-07 release:** **A1, A2, A3, A4** must each be **PASS** or formally **BLOCKED** with disclosed gap blocking release (not silent skip).

**A5:** Optional; `NOT_EVALUATED` allowed for RC **only** with `RELEASE_WITH_A5_DEFERRED=true` at V09-07.

**Public substitute for A4 when COM missing:** Register `LIT-PUB-Δp-001…` with bibliographic pointer + blind input transcription checksum; must not be HXForge output.

### 5.3 Product / interface matrix — I1 … I5

| ID | Surface | Evidence | Pass criteria | Engineering basis |
|----|---------|----------|---------------|---------------------|
| **I1** | CLI official entry | `REG` + contract | Exit 0; stdout JSON hash == service hash | Single operator path for reproducible studies |
| **I2** | `POST /api/design/run` | `REG` | HTTP 200; body hash == I1 | Sync automation |
| **I3** | `POST /api/design/run-stream` | `REG` | Final SSE `result` hash == I1 | UI + progressive clients |
| **I4** | Browser default | Manual + auto | Checklist §6.2 all **PASS** | Human product acceptance |
| **I5** | Package install | `REG` | Version string + smoke import official entry | Release hygiene G-03 |

**I-tier:** All **mandatory** for V09-07.

---

## 6. Acceptance tier summary table

| Tier | IDs | Mandatory for `v0.9.0-rc.1` | Primary evidence |
|------|-----|-----------------------------|------------------|
| Regression / functional | R0 | Yes | REG / live |
| Independent design | P1–P3 | Yes | Live kernel E2E |
| Negative | N1–N2 | Yes | Live kernel |
| Metamorphic | M1–M4 | Yes | Live kernel |
| Accuracy | A1–A4 | Yes (PASS or blocking gap) | ANL / LIT / COM |
| Device accuracy | A5 | No (NOT_EVALUATED default) | DEV |
| Interface | I1–I5 | Yes | REG / manual |

---

## 7. Mandatory vs conditional release gates

### 7.1 Mandatory gates (all required — no waiver)

| Gate | Condition |
|------|-----------|
| **MG-1** | Charter status = `FROZEN` on release commit |
| **MG-2** | R0, P1–P3, N1–N2, M1–M4 → **PASS** on V09-06 runner |
| **MG-3** | A1–A4 → **PASS** (BLOCKED = release blocked) |
| **MG-4** | I1–I5 → **PASS** |
| **MG-5** | G-01, G-02, G-03, G-08 → **closed** per §4 |
| **MG-6** | `final-gate` **success** on main CI for release SHA |
| **MG-7** | No V07 Golden file changes in release diff |
| **MG-8** | Tag `v0.9.0-rc.1` created once at release SHA; no tag move |
| **MG-9** | Release notes state all §1.3 prohibitions and §4 limitations |

### 7.2 Conditional gates (owner decision)

| Gate | Condition | Default if unmet |
|------|-----------|-------------------|
| **CG-1** | A5 device validation | **`NOT_EVALUATED`**; RC allowed **only** if `RELEASE_WITH_A5_DEFERRED=true` |
| **CG-2** | A4 commercial benchmark | Use `LIT` public substitute; if none registered → **A4 BLOCKED** → blocks release |
| **CG-3** | G-10 mdot on kernel | If deferred → charter records `NOT_IN_SCOPE` + manual off-design disclaimer in release |
| **CG-4** | COM benchmark sponsorship | Optional enhancement; never substitutes for A1–A3 |

---

## 8. External reference and user data

### 8.1 Currently available (no owner shipment)

- V0.8 fixtures (`tests/fixtures/v08_*`) — **REG only**
- `V08_KERNEL_RATING_ACCEPTANCE_V1` tolerances — **ANL**
- CoolProp water (CI-pinned) — property round-trip
- HexAgent correlation registrations (Task025/026/037/166) — **internal documentation**, not independent proof alone
- Open literature for LMTD, F-factor, Darcy–Weisbach — **LIT** (must cite edition)
- Published academic/industry worked examples — **LIT-PUB-*** registration slots (transcription audit)

### 8.2 User / owner data request list (for A5 / optional COM)

Provide at least one dataset with redaction boundary agreed up front:

1. As-built data sheet (geometry, materials, nozzles, design/operating state)
2. Performance test log (T, P, flow, duty, uncertainty)
3. Segment or full-path hydrotest Δp
4. Commercial software export (version, correlation flags) — **COM**
5. Third-party engineering consultant calculation package — **LIT/COM** if independently authored

**Prohibited as “device data”:** prior HXForge JSON/PDF exports used as expected values.

---

## 9. Performance budgets and task termination

| Activity | Budget | Termination if exceeded |
|----------|--------|-------------------------|
| V09-06 local full matrix | 30 min wall (initial) | Split shard only via charter amendment |
| V09-02 A1–A4 suite | 10 min | No ε relaxation without V09-00 reopen |
| Single CI shard | Existing manifest timeouts | Infra retry per policy; **no** gate weakening |
| Browser manual I4 | 15 min human | Blocks V09-04 gate |

**Task kill switches**

- Unauthorized scope (new fluid, new HX type) → **stop**, V09-00 reopen.
- Two failed terminal gates same task → **stop** pending owner review.
- Attempt to use HXForge output as A-tier reference → **reject test registration**.

---

## 10. V09-07 release gate checklist (technical)

1. All **MG-1…MG-9** satisfied.
2. Conditional **CG-1…CG-4** explicitly recorded in release notes.
3. `pyproject` / wheel / tag version alignment (G-03 closed).
4. Pre-release flag set on GitHub Release.
5. **No** V0.9 implementation commit before MG-1.

---

## 11. Product delivery and browser acceptance (I4 detail)

### 11.1 Install / run (target)

```bash
git checkout v0.9.0-rc.1
pip install -e ".[dev]"   # after V09-05 packaging decision
export PYTHONPATH=src:.
python3 -m prototypes.v08_thermal_rating.web.server   # or consolidated entry from V09-05
```

### 11.2 Browser checklist (each must PASS for I4)

1. Default engine = **kernel_v1** without hidden query params.
2. Thermal panel shows **kernel** Q, outlet temperatures, resistance or U·A — not ε-NTU prescreen-only labels.
3. Hydraulic panel shows **full-path** Δp and four-port velocities.
4. Export JSON includes unified schema id + `rating_engine` + provenance block.
5. Visible disclaimer: not code compliance / not manufacturing approval.

---

## 12. Engineering formula registry (verification ownership V09-02)

| Mechanism | Implementation pointer | Correlation / source claim |
|-----------|-------------------------|---------------------------|
| LMTD | `v08_independent_engineering_rating_kernel_v1._lmtd_k` | Log-mean temperature difference definition |
| F correction | `_f_factor_tema_v1` | TEMA 1-shell-pass table (partial) |
| Shell HTC | Task166 / Bell-Delaware | HexAgent registration |
| Tube HTC | Task026 | HexAgent registration |
| Wall + fouling | Task037 authorities | Outer-basis network |
| Duty iteration | Kernel loop + enthalpy audit | `V08_KERNEL_RATING_ACCEPTANCE_V1` |
| Full-path Δp | V08-04 + authorized full path | Assumption-K experimental |
| Nozzle velocity | 1–3 m/s band | V08 joint record |

---

## 13. Document control

| Version | Status | Note |
|---------|--------|------|
| R1 draft | `DRAFT_FOR_SCOPE_REVIEW` | Initial V09-00 planning |
| R1 prepared | `FINAL_SCOPE_REVIEW_PREPARED` | V09-00-FINAL_SCOPE_REVIEW_PREPARATION |
| R1 frozen | `FROZEN` | Pending owner + V09-00 docs PR |

**Authorization flags (this revision)**

`COMMIT_AUTHORIZED=false` · `IMPLEMENTATION_AUTHORIZED=false` · `RELEASE_AUTHORIZED=false` · `V09-01_AUTHORIZED=false` · `RELEASE_WITH_A5_DEFERRED=unset`

---

## Appendix A — Baseline verification (read-only, V09-00)

| Check | Result |
|-------|--------|
| Tag `v0.8.0-rc.1` → commit | `cdd48e361205dd3df1f24007aca36ca3ee048488` ✓ |
| `origin/main` HEAD | same ✓ |
| PR #325 merged | ✓ |
| Main CI `46094612999` | success, `final-gate` success ✓ |
| Tag overwrite | none ✓ |