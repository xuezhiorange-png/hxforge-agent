# HXForge V0.9 — Version Scope and Acceptance Charter R2

| Field | Value |
|-------|-------|
| **Document status** | `DRAFT_PR_PENDING` — **FROZEN** effective only after this docs-only PR is **merged**; `SCOPE_FREEZE_AUTHORIZED` set at merge approval |
| **Charter revision** | **R2** (corrects R1 per `V09-00-CHARTER_FINAL_CORRECTION_R2`) |
| **Planning TASK_ID** | `V09-00-VERSION_SCOPE_AND_ACCEPTANCE_FREEZE` |
| **Correction TASK_ID** | `V09-00-CHARTER_FINAL_CORRECTION_R2` |
| **Repository** | `xuezhiorange-png/hxforge-agent` |
| **Baseline tag** | `v0.8.0-rc.1` |
| **Baseline SHA** | `cdd48e361205dd3df1f24007aca36ca3ee048488` |
| **Baseline main CI** | run `46094612999`, `final-gate` = **success** |
| **Target release train** | `v0.9.0-rc.1` |
| **Version objective** | **工程实用化与计算精度验证** (`VERSION_OBJECTIVE_APPROVED=true`) |
| **Task allocation** | V09-00 … V09-07, eight tasks (`VERSION_TASK_ALLOCATION_APPROVED=true`) |
| **Domain envelope** | Steady-state, single-phase **water/water** shell-and-tube — no fluid/topology expansion |

**Authorization flags (this revision)**

`SCOPE_FREEZE_AUTHORIZED=false` · `IMPLEMENTATION_AUTHORIZED=false` · `COMMIT_AUTHORIZED=false` · `RELEASE_AUTHORIZED=false` · `TAG_AUTHORIZED=false` · `RELEASE_ELIGIBILITY_AUTHORIZED=unset` · `RELEASE_WITH_A5_DEFERRED=unset`

---

## 0. Authority, independence, and dual regression policy

### 0.1 Chain

1. Owner approves R2 → `FROZEN` via V09-00 docs-only PR **only** when `SCOPE_FREEZE_AUTHORIZED=true`.
2. V09-01+ requires `IMPLEMENTATION_AUTHORIZED=true` per task.
3. **Release eligibility** (acceptance PASS) is **separate** from **Tag/Release creation** (requires explicit `RELEASE_AUTHORIZED` + `TAG_AUTHORIZED`).

### 0.2 Independence (unchanged, binding)

- **HxForge outputs SHALL NOT** be independent reference answers for A-tier or external benchmarks.
- Independent references: hand derivation, blind-transcribed published examples (`LIT`), commercial exports (`COM`), owner device data (`DEV`).
- **Static hydrostatic / proof-pressure tests SHALL NOT** be used as **operating** full-path Δp references (A4/A5).

### 0.3 Dual-track regression (P1-03 — R0 vs V0.9 engineering)

| Track | ID | Purpose | Golden / hash rule |
|-------|-----|---------|-------------------|
| **Historical exact replay** | `R0-V08` | Bit-stable replay of `v0.8.0-rc.1` behavior on frozen fixture | Pinned hashes from tag `v0.8.0-rc.1`; **V07/V08 Golden files immutable** |
| **V0.9 engineering acceptance** | `R0-V09`, P*, N*, M*, A*, I* | Legitimate model/interface improvements | New pins recorded at freeze; **must not overwrite** `R0-V08` pins |

When V0.9 model changes invalidate `R0-V08` byte identity, **both** tracks run: `R0-V08` MUST still PASS on replay branch/config (or documented frozen runner); `R0-V09` MAY adopt new canonical hash with charter amendment only.

---

## 1. Version goal (unchanged scope)

Deliver unified compute service, installable package, **Sizing + Rating + Off-design + multi-objective optimization**, accuracy verification (A1–A4 mandatory), product surfaces (I1–I5), calc book exports (JSON/HTML/PDF). Inherit kernel V1 authority; retain legacy boundaries (G-12).

---

## 2. Eight version tasks (fixed)

| Task | Responsibility delta (R2) | Terminal gate |
|------|---------------------------|---------------|
| **V09-00** | Freeze R2; ε annex with **sourced** thresholds | Owner `SCOPE_FREEZE_AUTHORIZED` |
| **V09-01** | Unified service + DTO; CLI/sync/stream parity | I1–I3 PASS |
| **V09-02** | **Engineering F model** (P1-01); A1–A4 harness; ≥3 full benchmarks | A1–A4 PASS; F model registered |
| **V09-03** | **Mandatory:** Sizing, fixed Rating, Off-design, multi-objective; Top-N policy; close G-08–G-10 | P + functional features PASS |
| **V09-04** | Browser **full** E2E (I4) | I4 PASS |
| **V09-05** | **Package contains engineering modules** (G-04); clean install I5 | I5 PASS |
| **V09-06** | Full matrix including P4–P7 | All mandatory rows PASS |
| **V09-07** | Release **eligibility** report only; tag/release需单独授权 | MG-* + eligibility doc |

**Global termination (P1-06):** Unauthorized scope; two consecutive task gate failures without charter amendment; use of HXForge as A-tier reference; attempt to weaken ε post-implementation → **halt** and reopen V09-00.

---

## 3. P1-01 — LMTD F correction model (V09-02 obligation)

V09-02 SHALL **implement** an engineering F-correction model on the **formally supported** flow arrangement envelope, not merely audit the current `_f_factor_tema_v1` constants.

### 3.1 Model requirements

| Item | Requirement |
|------|-------------|
| Temperature driving function | Use **actual** inlet/outlet temperatures from rating solution (or declared iteration state); document counterflow vs arrangement |
| Flow arrangement | Register shell passes, tube passes, arrangement ID; map to F correlation |
| Engineering source | Cite standard or textbook (edition frozen in correlation register) |
| Applicability envelope | Valid range on R, P, cross-flow factors — outside → `MODEL_BLOCKED` |
| Block conditions | No driving force, cross, unsupported pass combo → structured block, no silent F=1 |
| Prohibited | **`NOT_APPLICABLE` inside the charter supported 1-shell water–water catalog** to avoid building the model |

### 3.2 A2 linkage

A2 validates the **implemented** F model against `LIT` table points — not the legacy three constants alone.

**G-05 closure:** F model shipped + A2 PASS on registered pass combos within envelope.

---

## 4. P1-02 — Independent engineering accuracy (A1–A5)

Evidence taxonomy: `REG`, `ANL`, `LIT`, `COM`, `DEV` (see R1 §3). **Thresholds SHALL be frozen in V09-00 ε annex before the owning model code merges** — each threshold cites source (standard, textbook equation, or instrument uncertainty).

### 4.1 A1 — Analytical reference (enhanced)

| Element | Requirement |
|---------|-------------|
| Reference | **Independent** closed-form: true **countercurrent** LMTD Q = U·A·ΔT_lm·F with F=1 or registered F from hand calc |
| Semantic audit | Verify `analytic_parallel_flow_q` / kernel pairing: document whether reference is counterflow, parallel, or mixed; **A1 FAIL** if implementation label contradicts reference physics |
| Compare | Kernel scalar/toy geometry fixture frozen **before** code |
| ε_Q, ε_energy | Inherit `V08_KERNEL_RATING_ACCEPTANCE_V1` until annex supersedes with citation |

### 4.2 A2 — F model (covers P1-01)

| Compare | Implemented F vs **LIT** table at ≥3 registered {(N_shell, N_tube_pass)} points in supported envelope |
| ε_F | From cited table uncertainty or **0.02** absolute max — whichever is **stricter**; source recorded |

### 4.3 A3 — Full thermal audit

| Quantities | Each benchmark case must compare independently: h_tube, h_shell, R-stack (wall, fouling in/out), **U**, **UA**, **Q**, **T_out,tube**, **T_out,shell** |
| Evidence | `ANL` hand audit + `LIT`/`COM` third-party where available |
| ε set | Per-quantity frozen in annex (default proposal: U 2% rel; Q per V08 contract; T_out 0.1 K abs for water near 300 K — **must be approved at freeze**) |

### 4.4 A4 — Hydraulic audit

| Quantities | Component Δp (tube, shell, nozzle segments) **and** full-path totals, both sides |
| Prohibited reference | Hydrostatic proof test Δp as operating benchmark |
| ε_Δp | Annex: max(50 Pa, 5% rel) per component unless literature tighter |

### 4.5 Joint benchmark suite (A3 + A4)

**Minimum three** independent **complete** engineering cases (`BENCH-001`, `BENCH-002`, `BENCH-003`):

- Each: full geometry + boundary conditions transcribed blind from `LIT` or `COM` (not HXForge).
- Each: A3 thermal + A4 hydraulic rows both PASS or release blocked.
- Registration sheet: bibliography/version, input checksum, expected value provenance.

### 4.6 A5 — Device (unchanged policy)

| Rule | Detail |
|------|--------|
| No DEV data | `NOT_EVALUATED` only — **never PASS** |
| RC release | `RELEASE_WITH_A5_DEFERRED=true` required for RC with NOT_EVALUATED A5 |
| R&D prep | A5 **does not block** V09-01…V09-06 implementation or release eligibility dry-runs |
| Operating data | Performance test / field log only; not hydrostatic test as Δp reference |

---

## 5. P1-03 — Acceptance cases and metamorphic rules

### 5.1 Historical V0.8 design cases (retained)

| ID | Fixture | Notes |
|----|---------|-------|
| **R0-V08** | `tests/fixtures/v08_user_case_hxforge_330kw_strict_dp.json` | Historical hash replay track |
| **P1** | `v08_user_case_no_geometry_task174_admissible.json` | 250 kW |
| **P2** | `v08_user_case_no_geometry_task174_admissible_alt.json` | 220 kW |
| **P3** | `v08_user_case_p3_kernel_acceptance_v1.json` | 275 kW |

### 5.2 New independent V0.9 cases (P4–P7)

**Four** new cases MUST be pre-registered (fixtures created in V09-06, not retrofitted from solver):

| ID | Coverage obligation (each case differs from others) |
|----|---------------------------------------------------|
| **P4** | Distinct **duty** band (e.g. 180–200 kW class) |
| **P5** | Distinct **flow** balance (unequal mdot emphasis) |
| **P6** | Distinct **temperature approach** / ΔT |
| **P7** | Distinct **pressure + geometry** limits (tight Δp and/or max shell/length) |

Each P4–P7: live kernel joint E2E; ≥1 qualified or honest blocked outcome with trace; **independent** of P1–P3 inputs.

`NEW_INDEPENDENT_CASE_COUNT = 4` (P4–P7).

### 5.3 R0-V09 (engineering regression)

After legitimate V0.9 model changes, new pin hash on same 330 kW fixture under **`R0-V09`** track; does not replace `R0-V08` artifacts.

### 5.4 Negative (N1, N2) — unchanged

### 5.5 Metamorphic M1–M4 (physics-based — P1-03)

**PASS requires demonstrated physical response**, not merely hash ≠ control:

| ID | Perturbation | Required observable |
|----|--------------|---------------------|
| **M1** | Duty ×1.10 | Q_actual or feasibility moves toward/at target; or qualified count decreases with physics-consistent reason |
| **M2** | Both flows ×1.05 | Approach/LMTD or outlet state shifts consistent with capacitance change |
| **M3** | Tin +2 K (recorded side) | Driving force and/or duty margin changes directionally correct |
| **M4** | Δp limits ×0.80 | Hydraulically marginal candidates drop; **no** spurious new qualification under tighter Δp |

**FAIL** if only hash changes without attributable engineering delta in declared observables.

---

## 6. P1-04 — V09-03 engineering functional closure

### 6.1 Mandatory capabilities

| Capability | Acceptance |
|------------|--------------|
| **Sizing** | Autonomous discrete candidate generation + kernel joint qualification |
| **Fixed-structure Rating** | Given frozen bindings JSON → kernel thermal + hydraulics (G-09) |
| **Off-design** | Same **fixed geometry**; vary mdot, inlet T, fouling scenario (CLEAN vs declared fouling) |
| **Multi-objective optimization** | Pareto or ranked trade-off on declared objectives within catalog — deterministic, traceable |

### 6.2 G-10 (mandatory close — no deferral)

**G-10 MUST close in V09-03/04:** off-design on kernel path exposed via CLI/API/Web with fixed geometry invariants enforced.

### 6.3 Top-N (G-08)

1. **Hard constraint filter first:** duty, full-path Δp both sides, nozzle band, geometry limits, model applicability.
2. **Then rank** by pre-declared engineering objectives (duty margin, min pressure margin, compactness proxy) — documented in runner output.
3. Prescreen ranks **cannot** populate formal qualified list.

### 6.4 Off-design invariants

- Geometry IDs and structural bundle **immutable** across off-design scenarios.
- Allowed knobs: mdot (per side or both), inlet temperatures, fouling authorities (within registered enums).

---

## 7. P1-05 — Software delivery (V09-05)

### 7.1 G-04 closure (mandatory)

Wheel/sdist MUST ship **official engineering entry modules** (or documented namespace package) so customer install does **not** require a checkout `prototypes/` tree. `pyproject` packages list updated in V09-05 — acceptance = **artifact contents test**, not prose only.

### 7.2 I5 — Clean install

| Step | Requirement |
|------|-------------|
| Environment | **Fresh venv** on supported Python; **no** repo checkout; **no** `PYTHONPATH` |
| Install | `pip install` wheel from release artifact at tag |
| Smoke | Import official entry; run version check == `0.9.0rc1` |
| Functional smoke | Sizing, Rating, Off-design minimal case from bundled example JSON |

### 7.3 Export surfaces (V09-05 / V09-06)

CLI, Web, Sizing, Rating, Off-design each produce **JSON**; report chain produces **HTML** and **PDF** sample — automated export tests in I5/V09-06.

### 7.4 I4 — Browser full loop (P1-05)

| Step | Requirement |
|------|-------------|
| Real browser | Automated UI drive (not curl-only) |
| Flow | Load preset → run design → **see kernel thermal/hydraulic panels** → export JSON → export report |
| FAIL | HTTP 200 alone, static HTML without compute, or prescreen-only blanks |

---

## 8. Engineering gap register — unified closure (P1-06)

| ID | Disposition | Owner | Closure |
|----|-------------|-------|---------|
| **G-01** | **MUST resolve** | V09-01, V09-04 | I4 full loop; unified DTO |
| **G-02** | **MUST resolve** | V09-01 | I1–I3 hash parity |
| **G-03** | **MUST resolve** | V09-05 | I5 version match tag |
| **G-04** | **MUST resolve** | V09-05 | Package ships engineering modules; install test |
| **G-05** | **MUST resolve** | V09-02 | Engineering F model + A2 |
| **G-06** | **MUST resolve** | V09-02 | DTO naming + A3 |
| **G-07** | **Document boundary** | V09-02, V09-03 | Assumption-K stays experimental; labels in all exports |
| **G-08** | **MUST resolve** | V09-03 | Top-N policy §6.3 |
| **G-09** | **MUST resolve** | V09-03 | Rating-only API/CLI |
| **G-10** | **MUST resolve** | V09-03, V09-04 | Off-design §6.1 — **no deferral** |
| **G-11** | **Document boundary** | V09-02 | Dual outlet domain warnings; no merge |
| **G-12** | **Retain limitation** | V09-05 calc book | IPC observables=None documented |

---

## 9. Full acceptance matrix (R2)

### 9.1 Functional / regression

| ID | Mandatory | Pass summary |
|----|-----------|--------------|
| R0-V08 | Yes | Exact replay vs `v0.8.0-rc.1` pin |
| R0-V09 | Yes | V0.9 engineering pin on 330 kW fixture |
| P1–P3 | Yes | V0.8 historical cases |
| P4–P7 | Yes | New independent cases §5.2 |
| N1, N2 | Yes | Blocked outcomes |
| M1–M4 | Yes | Physics observables §5.5 |

### 9.2 Accuracy

| ID | Mandatory for RC eligibility | Notes |
|----|------------------------------|-------|
| A1–A4 | **Yes — all PASS** | §4; ≥3 bench cases |
| A5 | No (NOT_EVALUATED default) | Separate RC approval |

### 9.3 Interface / product

| ID | Mandatory |
|----|-----------|
| I1–I5 | **Yes — all PASS** |

### 9.4 Feature gates (V09-03/05)

Sizing, Rating, Off-design, multi-objective, JSON/HTML/PDF exports — **all PASS** before V09-07 eligibility.

---

## 10. Release gates (P1-06)

### 10.1 Mandatory (MG) — release **eligibility**

| Gate | Condition |
|------|-----------|
| MG-1 | Charter `FROZEN` |
| MG-2 | R0-V08, R0-V09, P1–P7, N1–N2, M1–M4 PASS |
| MG-3 | A1–A4 PASS |
| MG-4 | I1–I5 PASS |
| MG-5 | G-01–06, G-08–10 **resolved**; G-07, G-11 **documented**; G-12 **documented** |
| MG-6 | All mandatory **features** PASS |
| MG-7 | `final-gate` success on release SHA |
| MG-8 | No V07 Golden mutation |
| MG-9 | Eligibility report filed (separate from tag creation) |

### 10.2 Conditional (CG)

| Gate | Note |
|------|------|
| CG-1 | A5: `NOT_EVALUATED` OK for eligibility if `RELEASE_WITH_A5_DEFERRED` set at RC |
| CG-2 | A4: `LIT` substitutes allowed per §4.5 |
| CG-3 | COM optional |

### 10.3 Publication (explicit authorization)

| Action | Requires |
|--------|----------|
| Git tag `v0.9.0-rc.1` | `TAG_AUTHORIZED=true` |
| GitHub Release | `RELEASE_AUTHORIZED=true` |
| Eligibility alone | Does **not** auto-create tag/release |

---

## 11. External data

§8 R1 retained. Add: register `BENCH-001…003` bibliography before V09-02 coding. Hydrostatic tests excluded from A4/A5 Δp.

---

## 12. Document control

| Revision | Status |
|----------|--------|
| R1 | `FINAL_SCOPE_REVIEW_PREPARED` — superseded by R2 for review |
| R2 | `DRAFT_PR_PENDING` (→ `FROZEN` on merge) |

---

## Appendix A — R1 → R2 correction对照表

| Correction | R1 summary | R2 change |
|------------|------------|-----------|
| **P1-01** | A2 vs fixed F constants; NOT_APPLICABLE allowed | V09-02 **builds** engineering F model; envelope + blocks; no NOT_APPLICABLE in supported domain |
| **P1-02** | A1 toy; A3 U only; A4 spot; thresholds partial | A1 counterflow semantics audit; A2 on real F; A3 full thermal set; A4 component+total; **≥3** BENCH cases; ε frozen with **sources**; hydrostatic barred |
| **P1-03** | P1–P3 only; R0 single hash; M* hash change OK | **P4–P7** added; **R0-V08** vs **R0-V09** dual track; M* require **physics** observables |
| **P1-04** | G-10 optional defer | Sizing/Rating/Off-design/MOO **mandatory**; Top-N filter-then-rank; G-10 **must** close |
| **P1-05** | G-04 "document or entry points" | G-04 **package ship**; I5 clean install; exports; I4 **browser** E2E |
| **P1-06** | MG-5 subset gaps; mixed defer | Unified G table; split **eligibility** vs **tag/release**; A5 blocks RC only, not R&D |

---

## Appendix B — Baseline verification

| Check | Result |
|-------|--------|
| `v0.8.0-rc.1` @ `cdd48e361205dd3df1f24007aca36ca3ee048488` | ✓ |
| PR #325 merged | ✓ |
| Main CI `46094612999` | ✓ |

---

## Appendix C — Charter integrity

| Item | Value |
|------|-------|
| **R1 path** | `docs/tasks/V09_VERSION_SCOPE_AND_ACCEPTANCE_CHARTER_R1.md` |
| **R2 path** | `docs/tasks/V09_VERSION_SCOPE_AND_ACCEPTANCE_CHARTER_R2.md` |
| **R1 SHA256** | `d80d97693c3661fb2936418a1cdc2bc4935f275dfa19b2ab0c137164480b450e` |
| **R2 SHA256 (pre-governance)** | `eb70a1e642c9f16feebea45621be76003a52de5e75fb4a78e48a7a88b911eab8` (scope-review approved text) |
| **R2 SHA256 (this file)** | Run `sha256sum docs/tasks/V09_VERSION_SCOPE_AND_ACCEPTANCE_CHARTER_R2.md` on PR HEAD — see V09-00 PR body |