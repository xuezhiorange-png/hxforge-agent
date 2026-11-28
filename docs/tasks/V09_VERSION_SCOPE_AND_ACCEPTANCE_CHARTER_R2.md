# HXForge V0.9 — Version Scope and Acceptance Charter R2

| Field | Value |
|-------|-------|
| **Document status** | `DRAFT_PR_PENDING` — **FROZEN** effective only after this docs-only PR is **merged**; `SCOPE_FREEZE_AUTHORIZED` set at merge approval |
| **Charter revision** | **R2** (corrects R1 per `V09-00-CHARTER_FINAL_CORRECTION_R2`) |
| **Planning TASK_ID** | `V09-00-VERSION_SCOPE_AND_ACCEPTANCE_FREEZE` |
| **Correction TASK_ID** | `V09-00-CHARTER_FINAL_CORRECTION_R2`; PR #326 amendments `V09-00-PR326_FINAL_GATE_CORRECTION` (P1-07…P1-09) |
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

Evidence taxonomy: `REG`, `ANL`, `LIT`, `COM`, `DEV` (see R1 §3). **External reference data, ε thresholds, and calculation basis SHALL be frozen before the corresponding model/function code development begins** — not merely before charter merge. V09-02 MAY publish a **专项精度验收附件** (accuracy annex) prior to formal implementation coding; this charter PR is **not** required to contain all engineering numbers.

### 4.1 A1 — Analytical reference (P1-08)

| Element | Requirement |
|---------|-------------|
| Reference | **Independent** closed-form **ε-NTU** and/or equivalent analytical rating equations with **declared arrangement** (countercurrent, parallel, crossflow limits as applicable) |
| Physical meaning | Each arrangement used in A1 MUST state inlet/outlet pairing, effectiveness definition, and temperature driving force; **FAIL** if kernel arrangement label contradicts reference physics (including legacy `analytic_parallel_flow_q` naming audit) |
| Compare | Toy fixtures frozen **before** implementation; no HXForge output as expected value |
| ε_Q, ε_energy | Frozen in V09-02 accuracy annex with citation; default inherit `V08_KERNEL_RATING_ACCEPTANCE_V1` until superseded |

### 4.2 A2 — F model and P/R coverage (P1-01 + P1-08)

| Compare | Implemented F vs **LIT**; **≥3** distinct **P/R temperature relations** (including boundary / near-boundary points) within formally supported flow arrangement envelope |
| Coverage | Multiple tube-pass/shell-pass combos in supported catalog; document blocked points outside envelope |
| ε_F | From cited table uncertainty or **0.02** absolute max — whichever is **stricter**; frozen in annex **before** F model code |

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

**Four** new **positive engineering** cases MUST be pre-registered **before** V09-02/V09-03 model and candidate-selection work (registry owned by V09-06):

| ID | Coverage obligation (each case differs from others) |
|----|---------------------------------------------------|
| **P4** | Distinct **duty** band (e.g. 180–200 kW class) |
| **P5** | Distinct **flow** balance (unequal mdot emphasis) |
| **P6** | Distinct **temperature approach** / ΔT |
| **P7** | Distinct **pressure + geometry** limits (tight Δp and/or max shell/length) |

Each registry row MUST include **frozen**: inputs (SI), thermodynamic feasibility justification, allowed geometry envelope, expected **hard-constraint** set, and pass observables — **not** retrofitted after implementation.

### 5.2.1 P1-07 — Positive engineering acceptance (P4–P7)

| Rule | Requirement |
|------|-------------|
| **PASS** | Each of P4–P7 MUST yield **≥1 real computed candidate** satisfying **all applicable hard constraints** (duty, both full-path Δp, nozzle band, declared geometry limits, model applicability) under kernel joint authority |
| **BLOCKED** | Valid for **N-tier** cases only; **`BLOCKED` SHALL NOT count as PASS** for P4–P7 |
| Anti-gaming | Fixtures SHALL NOT be reverse-engineered from implemented catalog/solver outputs to force success |
| Execution | **V09-06** runs P4–P7 as **independent acceptance** with pre-registered expected observables; V09-03 provides capability but does not author case intent |

`NEW_INDEPENDENT_CASE_COUNT = 4` (P4–P7).

### 5.3 R0-V09 (engineering acceptance on 330 kW)

| Track | Requirement |
|-------|-------------|
| Pin update | May update canonical hash after legitimate V0.9 model change; **never** overwrites `R0-V08` pins |
| **P1-07** | `R0-V09` PASS requires **engineering observables** (duty, energy balance, hard constraints, declared margins) meeting same criteria as P-tier — **hash equality alone is insufficient** |
| Basis | Pre-registered acceptance sheet for 330 kW V0.9 engineering track, distinct from historical replay |

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

## 7. P1-05 + P1-09 — Software delivery (V09-05)

### 7.1 G-04 closure (mandatory)

Wheel/sdist MUST ship **official engineering entry modules** (or documented namespace package) so customer install does **not** require a checkout `prototypes/` tree. `pyproject` packages list updated in V09-05 — acceptance = **artifact contents test**, not prose only.

### 7.2 I5 — Candidate artifact install (P1-09)

| Phase | Requirement |
|-------|-------------|
| **Pre-release (mandatory)** | Build wheel/sdist from **release candidate commit** (same tree intended for tag); install in **isolated** env: **no** source checkout, **no** `PYTHONPATH` |
| Start | **Formal CLI** and **formal Web** (packaged entry points, not dev-only module paths) |
| Modes | Execute **Sizing**, **Rating**, **Off-design** each to completion on bundled example inputs |
| Exports | **JSON**, **HTML**, and **PDF** report outputs verified (file hash + schema smoke) |
| **Post-release (tag only)** | Verify tag SHA, package version, and **published artifact digest** consistency — **no** re-run of full I5 on customer site to certify engineering (avoids circular dependency) |

### 7.3 Export surfaces (V09-05 / V09-06)

CLI and Web for all three engineering modes; export tests are part of **I5 pre-release**, not optional smoke.

### 7.4 I4 — Browser full loop (P1-05 + P1-09)

| Step | Requirement |
|------|-------------|
| Real browser | Automated UI drive on **candidate install** or CI-staged equivalent (not curl-only) |
| **Sizing** | Full form → run → kernel panels → JSON export |
| **Rating** | Fixed-geometry rating flow via UI or documented UI entry → results + export |
| **Off-design** | Same geometry, perturbed boundary → results + export |
| Reports | HTML and PDF download paths exercised |
| FAIL | HTTP 200 alone, static page, prescreen-only blanks, or skipping any of the three modes |

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
| R0-V09 | Yes | Engineering observables on 330 kW §5.3 — not hash-only |
| P1–P3 | Yes | V0.8 historical cases |
| P4–P7 | Yes | Each **≥1 hard-qualified candidate** §5.2.1 — **BLOCKED = FAIL** |
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
| MG-2 | R0-V08, R0-V09 (engineering observables), P1–P7 (P4–P7 each **hard-qualified**), N1–N2, M1–M4 PASS |
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

### 11.1 Retained from R1 (not weakened)

The following R1 provisions remain in force unchanged in V0.9:

- **Performance budgets** (V09-06 full matrix ~30 min local initial; V09-02 A-suite ~10 min; browser manual ~15 min; CI shard timeouts unchanged).
- **Engineering applicability domain** (single-phase water/water shell-and-tube within declared catalog; no silent extrapolation).
- **Historical evidence protection** (V07 Golden immutable; `R0-V08` exact replay; no HXForge-as-reference for A-tier).
- **Task kill switches** (§2 global termination; unauthorized scope; self-reference rejection).

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
| **P1-07** | P4–P7 allowed BLOCKED pass | Each P4–P7 requires **≥1** hard-qualified candidate; registry freeze; R0-V09 not hash-only |
| **P1-08** | ε at merge; LMTD-only A1 | ε-NTU A1; A2 P/R set; freeze **before model code**; V09-02 annex allowed pre-coding |
| **P1-09** | Generic `pip install` at tag | Pre-release **candidate** wheel I5 + three modes; I4 all modes; post-release digest verify only |

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