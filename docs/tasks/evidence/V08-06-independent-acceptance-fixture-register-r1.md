# V08-06 independent acceptance fixture register (R1)

Status: `PRE_REGISTERED_PENDING_FORMAL_REVIEW` (not retrofitted from solver outputs)

**V08-07 RC official thermal authority:** CLI/API/web default `kernel_v1` via `run_official_v08_rating_compute` (`V08_INDEPENDENT_KERNEL_V1`). R0/P3 rows below are acceptance fixtures for that kernel matrix (`v08_06_kernel_version_acceptance.py`), not legacy ε-NTU prescreen.

| Slot | Fixture | Engineering case ID | Duty | Flows (kg/s) | Tin tube/shell (K) | Δp limits (Pa) | Intent |
|------|---------|---------------------|------|--------------|-------------------|----------------|--------|
| R0 | `tests/fixtures/v08_user_case_hxforge_330kw_strict_dp.json` | `HXFORGE_330KW_STRICT_DP` | 330 kW | **12 / 20** | **310 / 295** | 1150 / 1180 | V08 R0 strict Δp envelope; fixture is source of truth (not V07 13.9/26.21 cousin flows) |
| P1 | `tests/fixtures/v08_user_case_no_geometry_task174_admissible.json` | `v08-example-mid-duty-no-geometry-task174-admissible` | 250 kW | distinct from R0 | per fixture | per fixture | Independent non-reference |
| P2 | `tests/fixtures/v08_user_case_no_geometry_task174_admissible_alt.json` | `v08-example-alt-water-water-task174-admissible` | **220 kW** | 12 / 20 | 319.15 / 294.15 | 40000 / 35000 | Second independent case (Issue #324 closeout notes) |
| P3 | `tests/fixtures/v08_user_case_p3_kernel_acceptance_v1.json` | `V08_06_P3_KERNEL_ACCEPTANCE_V1` | **275 kW** | **11 / 19** | 317.15 / 296.15 | 40000 / 35000 | Pre-registered spec `V08-06-P3-kernel-acceptance-spec-r1.md` |
| N1 | Synthetic (runner) | `V08_06_N1_THERMODYNAMIC_INVALID` | — | — | 358.15 / 353.15 (no driving force) | — | Expect `INVALID_INPUT` / thermodynamic block |
| N2 | `tests/fixtures/v08_user_case_infeasible_duty_5mw.json` | `HXFORGE_INFEASIBLE_TINY_ENVELOPE_PROBE` | 5 MW | valid | valid | tight envelope | `NO_FEASIBLE_DESIGN` / empty geometry |
| M1–M4 | Derivatives of R0 | same schema | duty ±10% / flow ±5% / Tin shift / Δp ×0.8 | — | Metamorphic response on report hashes and classifications |

**220 kW heavy live Task173 path:** prior V08-03 closeout documented convergence/acceptance blockers. V08-06 reuses identity + historical attribution (`docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r3.json`); does **not** re-run multi-hour Task173 campaigns.

**Success definition (V08 charter):** live end-to-end **design** success requires hard-constraint-qualified candidate with disclosed assumptions — not merely `BLOCKED` with correct cause. Experimental prescreen Top-N is tracked separately.