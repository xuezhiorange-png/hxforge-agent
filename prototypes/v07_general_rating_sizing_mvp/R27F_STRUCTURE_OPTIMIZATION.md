# R27F structure optimization note

TASK_ID: `V07_R27F_FULL_PATH_PRESSURE_BUDGET_AND_ROBUSTNESS`

## Pressure budget verdict (eight rated structures @ R27E `9795e18`)

- **mid_band / high_loss:** **0 / 8** authorized full-path feasible.
- **low_loss:** **1 / 8** full-path feasible (`9c4b84db` only).
- **330 kW thermal:** `40d78e67` **below** 330 kW (328.4 kW) — retained with reason, excluded from thermal-feasible set.

## 9c4b84db nozzle margin (computed, not assumed)

| Mode | Shell margin (Pa) | Notes |
|------|-------------------|--------|
| Optimizer **minimum** nozzle @ low_loss K | **~0.00049** | Matches prior ~0.0005 Pa “critical pass” |
| **v = 1.0 m/s** (largest allowed nozzle) @ low_loss K | **~34.3** | Band scan in `margin_curves` |

**Conclusion:** The ~0.0005 Pa value is the **min-diameter cooptimization objective**, not proof that **no** useful margin exists in **1–3 m/s**. Meaningful low_loss margin **is** available at the **slowest allowed velocity**, but **mid_band** remains infeasible even at band max for this geometry.

## Can nozzle adjustment alone fix the portfolio?

**No** for a **robust mid_band design** — fixed shell Bell-Delaware + transition losses exceed budget for **`09dac82a`** and most reference shells even at **maximum allowed nozzle** (see negative `best_margin_in_band.shell_margin_pa` on mid_band curves).

## Next structure parameters (physics-backed)

1. **Priority:** reduce **shell-side bundle / transition** Δp (`baffle_spacing_m`, `shell_inside_diameter_m`, tube count/layout).
2. **Secondary:** tube friction via `tube_length_m` (coupled to duty).
3. **Local search:** Pareto on **`shell_inside_diameter_m × baffle_spacing_m`** within Task174-ready envelope; skip 0.65 m transition-blocked family.

Full tables: `tests/fixtures/R27F_FULL_PATH_PRESSURE_BUDGET.json`.
