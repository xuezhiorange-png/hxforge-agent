# HXForge V08 — Version Scope and Acceptance Charter R1

Status: `DRAFT_FOR_REVIEW` (not effective until the docs-only PR is approved and merged)
Task ID: `V08-00-VERSION-SCOPE-FREEZE`
Issue: https://github.com/xuezhiorange-png/hxforge-agent/issues/318
Target train: `V08`; intended future release train `v0.8.0` (release/tag/version bump NOT authorized by this document)
Baseline: published `v0.7.0-rc.1`, Git tag at `64b2ee3734395878e97a46e63c2ef505da4148d5`
Baseline CI: https://github.com/xuezhiorange-png/hxforge-agent/actions/runs/41658353072 (SUCCESS)

## 1. Version-level product outcome

**The user supplies a thermal-hydraulic design case, not an existing exchanger manufacturing drawing. HXForge automatically proposes bounded, catalog/discrete shell-and-tube structures, performs live thermal/hydraulic and nozzle checks, and returns ranked, traceable feasible designs or an explicit evidenced failure.**

This is **calculation-first automatic sizing and candidate generation**, not rating-only and not a lookup for the V07 330 kW acceptance fixture.

The V08 supported domain is the **declared steady-state, single-phase water/water engineering envelope** supported by validated properties, correlations, geometry catalog and hydraulic model. Widening fluid families/phase regimes/pressure-vessel approval is NOT implicitly authorized.

## 2. Public user-case contract (minimum)

User supplies:
- Hot-side and cold-side **fluid identity** (water/water for this version), inlet temperatures, and mass flows (or explicitly convertible units with recorded property basis).
- Requested heat duty and independently specified allowable **tube-side and shell-side full-path pressure drops**.
- Applicable project limits when known (e.g. shell envelope/maximum length, nozzle velocity band, preferred allowed discrete geometry). Missing optional constraints must be explicit defaults with provenance and auditable source; no unstated fixture defaults.

**The user need not supply:** a fabricated exchanger drawing, tube count, shell diameter, baffle configuration, nozzle diameters, or both outlet temperatures. The algorithm must derive/select those or declare a blocked/under-specified case with a specific reason.

A case has an immutable input snapshot and canonical SI units. Existing versioned schemas and provenance must remain compatible or be explicitly versioned.

## 3. Engineering computation contract

1. Validate units, fluid/phase/model envelope, property availability, thermodynamic driving-force feasibility, data completeness, and independent side-specific constraints before proposing designs.
2. Generate multiple **bounded discrete** shell-and-tube geometry candidates from the supported catalog/rules: shell ID, tube OD/ID/wall, length, layout/pitch/count, pass count, baffle arrangement/spacing and feasible nozzle diameters. The output is preliminary engineering geometry, not fabrication-authorized geometry.
3. Screen cheaply before expensive live rating; run authorized N1→N2→N4 rating to the extent the applicable model and convergence criteria require. Do not silently substitute a frozen case result.
4. For each candidate calculate energy balance, duty, outlet temperatures, tube-side and shell-side transfer and internal pressure losses, nozzle velocities, and **full-path** pressure losses with itemized components.
5. Report the assumed local-loss `K` set and `low_loss` / `mid_band` / `high_loss` scenarios separately. A candidate feasible only under a designated assumption scenario is **conditional**, not a verified robust or production-approved design. Never promote unvalidated `K` coefficients into validated engineering authority.
6. Enforce hard constraints rather than allowing a weighted score to overrule failed duty/Δp/nozzle/geometry/model applicability. Return at most the number of truly qualified top designs; do not fabricate Top-N results.
7. Reject impossible/unsupported/no-feasible cases with structured `INVALID_INPUT`, `OUT_OF_ENVELOPE`, `NO_FEASIBLE_DESIGN`, `MODEL_BLOCKED`, or a more precise stable enumerated code. Include rejected candidate reasons and decisive evidence. Do not conceal warnings or force a recommendation.
8. Deterministic numeric kernel only. Keep input snapshot, correlation/version, fluid provider/version, bounds, constraints, convergence status, assumptions, candidate IDs and output hash. Retain V07 public behavior and frozen Golden results.

## 4. User-facing delivery

One supported CLI and a version-compatible API (or an explicit documented service boundary), both driving the **same deterministic sizing pipeline**.

Outputs include:
- Final classification: feasible conditional/robust within declared assumptions, no feasible candidate, or blocked.
- Ranked candidates with shell diameter, tube specification/count/length/passes/pitch, baffles, both nozzle sizes, calculated Q/UA/outlet conditions, internal and full-path Δp, velocity, hard-constraint margins, uncertainty/assumption flags.
- Ranking rationale, per-candidate rejection reasons, and alternative choices where actually available.
- Structured, reproducible JSON and human-readable engineering design summary, with warnings and complete provenance.

No requirement for an input drawing or fabrication drawing. Any conceptual geometry visualization must be labeled schematic, NOT manufacturing-grade CAD.

## 5. Independent acceptance and decision thresholds (set BEFORE coding)

The V08 acceptance matrix MUST be authored and reviewed as a **distinct pre-implementation fixture/specification**, not generated by copying V07 outputs or tuning against the final solver:
- **R0:** Existing frozen 330 kW water/water case; regression only, not evidence of general-case capability.
- **P1–P3 (at least three):** independent non-reference, engineering-feasible water/water cases varying at least **duty**, **one or both mass flows**, and **temperature driving force** across the set; at least one also varies full-path pressure limits. Pre-register numerical inputs, units, thermodynamic feasibility justification, allowed geometry envelope, expected independent physical behavior, and tolerance basis. These must yield at least one *live-rated* candidate satisfying hard constraints under the disclosed scenario — no fixture selection, precomputed bypass, or hardcoded candidate.
- **N1:** thermodynamically impossible/invalid case: explicit blocked classification, not a fabricated feasible design.
- **N2:** physically valid input but infeasible within deliberately restrictive design/pressure bounds: explicit `NO_FEASIBLE_DESIGN` plus reason, rather than constraint relaxation.
- **M1–M4:** metamorphic checks: varying target duty, flow, temperature driving force, and permitted Δp changes the relevant calculation/feasible set without reusing fixed 330 kW decisions.

At least **4 successful live end-to-end paths** in total (R0 + P1–P3), plus N1/N2; test authors must independently review case construction before implementation. A valid blocked result alone does not count as a successful design for P1–P3.

Per-case acceptance requires, as applicable:
- Physical heat balance, finite properties, valid single-phase state, valid temperature approach and model applicability.
- `Q_actual >= Q_target` (accounting only for an independently declared numerical tolerance).
- Tube and shell **full-path** pressure drops each at or under their respective case limits; internal-only Δp cannot substitute.
- Nozzle velocities within the declared band; allowed discrete geometry constraints satisfied.
- Explicit, non-promoted assumption-K scenario labels, margin and robust/conditional classification.
- Identical case+config+versions produces the same canonical ranked result and hash; bounded runtime and no silent numeric fallback.
- Each failing candidate has a traceable cause; no false feasible status.

Numerical tolerances, geometry bounds and performance budgets must be **documented before** implementing each acceptance fixture, supported by engineering or reproducibility reasoning, not relaxed after seeing failures.

## 6. Version task packages — finite scope

| Task | Deliverable and terminal gate | Depends on |
|---|---|---|
| V08-00 | Freeze this charter, input/output contract, independent case plan and stop rules; docs-only PR. | Published V07 baseline |
| V08-01 | General-case input/validation/units and user-case-to-solver mapping; no hardcoded 330 kW or forced geometry. | V08-00 |
| V08-02 | Bounded catalog-driven geometry generation with meaningful candidate diversity, deterministic pruning and reasons. | V08-01 |
| V08-03 | Unified live thermal sizing/rating and convergence over generated candidates; independent full energy balance and envelope checks. | V08-02 |
| V08-04 | Tube/shell internal + full-path budgets, nozzle velocity/co-selection, assumption-K scenarios, hard feasibility and margins. | V08-03 |
| V08-05 | Feasible candidate Top-N selection and traceable CLI/API structured engineering report; explicit no-feasible path. | V08-04 |
| V08-06 | Independent R0/P1–P3/N1/N2/M1–M4 live E2E evidence, reproducibility, performance and regression gates. | V08-05 |
| V08-07 | Version-level closeout, packaging/release candidate decision only after V08-06 and exact-head/merge-ref/main CI success. | V08-06 |

One engineering objective and one task PR at a time. Fix defects within the owning task where possible; **do not start an unbounded series of R27-style exploratory sub-PRs**. A cross-cutting redesign or scope expansion requires explicit version-level approval.

## 7. Scope exclusions and release safety

NOT included in V08 acceptance:
- Arbitrary fluids, two-phase boiling/condensing, refrigeration-phase design or unsupported exchanger topologies.
- Code-compliant pressure vessel design, ASME/TEMA sign-off, tubesheet strength certification, thermal/vibration mechanical approval or fabrication drawings.
- Guaranteed pressure-drop robustness based on unvalidated local-loss K.
- Licensed standards, vendor catalogs or customer cases committed to Git.
- Frontend product redesign, server deployment, procurement authority or production engineering certification.

Keep V07 release tag, package artifacts, Golden evidence and historical audit unchanged. Explicitly reject out-of-scope requests rather than returning success.

## 8. Gate and implementation authorization

**V08-00 is docs/planning-only.** No solver edits, Golden rewrites, release/version changes, new tags, server deployment or main merge in this task.

The charter is effective only after review and merge of the scope-freeze PR. Implementation starts at **V08-01** under separately authorized task execution after V08-00 is frozen.

V08 version DONE requires V08-01..06 acceptance passing on a new, reviewable integration HEAD; both PR-head/merge-ref and post-merge main CI, Golden and release gate must pass. Experimental release still carries engineering caveats and requires separate release authorization.

## 9. Status vocabulary

- `V08_SCOPE_STATUS=DRAFT_FOR_REVIEW` until V08-00 PR is merged.
- `V08_IMPLEMENTATION_STARTED=false` during scope freeze.
- `V08_VERSION_ACCEPTANCE=NOT_RUN` until independent E2E evidence exists.
- `V08_RELEASE_AUTHORIZED=false` until separately approved.
