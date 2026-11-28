# Engineering shortlist robustness (235/241 tubes)

- **Final decision:** ENGINEERING_AUTHORITY_PENDING: shortlist T235_L5.5 qualifies for placement-envelope approval review only (not production validated).
- **Identity binding:** T241_L5.5: same tube_count/length across scales yields 4 distinct Task021 layout_hash values — not one physical structure.; T241_L5.5: shared candidate_spec_id=6d78897b-77b7-545d-8b49-38a569b1c86e with 4 geometry_v2 values (envelope/clearance projection); no catalog identity mixing detected.; T241_L6.0: same tube_count/length across scales yields 4 distinct Task021 layout_hash values — not one physical structure.; T241_L6.0: shared candidate_spec_id=92187d45-ae76-5fdb-bf91-28f9dfca682b with 4 geometry_v2 values (envelope/clearance projection); no catalog identity mixing detected.
- **Clean 330 kW contract:** MET_CLEAN_CONTRACT
- **Fouled T039_DEMO:** FOULED_BELOW_330KW_T039_DEMO

## Canonical shortlist (4 physical layouts)

- **T235_L5.5** @ envelope 0.815: clean Q=330558.3 W (Δ=558.3); high tube margin=51.261 Pa; Re=4128.0309 (margin 128.0309); joint_prescreen_pass=True
- **T235_L6.0** @ envelope 0.815: clean Q=343704.5 W (Δ=13704.5); high tube margin=8.011 Pa; Re=4128.0309 (margin 128.0309); joint_prescreen_pass=True
- **T241_L5.5** @ envelope 0.82: clean Q=336332.7 W (Δ=6332.7); high tube margin=74.895 Pa; Re=4025.2584 (margin 25.2584); joint_prescreen_pass=True
- **T241_L6.0** @ envelope 0.82: clean Q=349716.1 W (Δ=19716.1); high tube margin=33.465 Pa; Re=4025.2584 (margin 25.2584); joint_prescreen_pass=True

## Pareto priorities

- **THERMAL:** T241_L6.0 — Highest baseline clean Q (349716.1 W); fouled T039_DEMO Q=322050.3 W.
- **HYDRAULIC:** T235_L5.5 — Largest worst-case high-K min-side margin (43.511 Pa) across exploratory sensitivities.
- **REGIME:** T235_L5.5 — Best minimum Re margin vs Task027 lower bound across sensitivities (128.0309); blocked in sweep=True.
- **RECOMMENDED:** T235_L5.5 — Joint prescreen pass at baseline; balances Re robustness, high-K margin, and clean thermal (330558.3 W). Authority remains EXPERIMENTAL_SHADOW_ONLY / PENDING.

## Authority

User case HXFORGE_330KW_STRICT_DP sets target_duty_w=330000 W; joint/prescreen gates compare CLEAN ε-NTU Q to 330 kW. T039_DEMO fouling is demo sensitivity only.

Fouling: T039_DEMO_FOULING_SENSITIVITY_ONLY; evidence ISSUE_214/R2/SUCCESS_VECTOR/INSIDE_FOULING, ISSUE_214/R2/SUCCESS_VECTOR/OUTSIDE_FOULING; not plant fouling authority.

Task173 production rating: **BLOCKED**

Placement envelope approval **required**; new tube catalog record **not_proven**.