# R27H engineering report

TASK_ID: `V07_R27H_CANDIDATE_SPACE_EXTENSION_AND_SHELL_PRESSURE_OPTIMIZATION`

## R27G 0.65 m classification correction (frozen R27G JSON unchanged)

| Prefix | Correct class | Mechanism |
|--------|---------------|-----------|
| 6ec6323f, 5b75a185, 8988992a | THERMAL_MODEL_BLOCKED | THERMAL_CORRELATION_TRANSITION_GAP (Task174-ready) |
| c20fb684 | THERMAL_MODEL_BLOCKED | PROPERTY_ENTHALPY_DOMAIN_EXIT |

## Task168 extension results

- **Table rows:** 10 (1 control + 9 proposed).
- **New structurally legal (Phase A):** **3** — shell **0.56 m** only, tube/baffle pairs (5.15/1.03), (5.35/1.07), (5.50/1.10).
- **Blocked before rating:** shell **0.58 m** and **0.60 m** — `TASK168_CHAIN_BLOCKED` / **BAFFLE_GEOMETRY** (Task024 layout).
- **Control 0.56/4.85/0.97:** not re-meshed; reference mid_band min margin **−70.87 Pa** (R27G sealed).

## Full mesh + mid_band (computed)

| Prefix | L (m) | B (m) | Q (kW) | mid_band min margin (Pa) |
|--------|-------|-------|--------|--------------------------|
| 7b124afe | 5.15 | 1.03 | 430.6 | **−29.2** |
| 90b9faad | 5.35 | 1.07 | 437.6 | **−4.0** |
| 5e78f6a8 | 5.50 | 1.10 | 442.6 | **~0** (tube ~0, shell ~0.0007) |

- **mid_band authorized full-path feasible @330 kW:** **0**
- **Best extension geometry:** 0.56 m shell, **337** tubes, **L=5.50 m**, **4** baffles @ **1.10 m** — still **not** robust positive margin; authorized full-path gate **not** satisfied (numerical edge only).

## Answers to task questions

1. **New legal geometries:** **3** (plus **6** table rows blocked at Task168 baffle geometry for 0.58/0.60 m shells).
2. **N1/N2/N4 completed:** **3** (new 0.56 m ladder variants).
3. **mid_band full-path feasible:** **No (0)**.
4. **Best:** shell **0.56 m**, **337** tubes, **L=5.50 m**, **baffle_count=4**, **spacing=1.10 m**.
5. **Max confirmed margins (mid_band, band-edge model):** tube **~0 Pa**, shell **~0.0007 Pa** on best row — **not** engineering-robust positive margin.
6. **Blockers:** (a) **0.58/0.60 m** — Task168 **BAFFLE_GEOMETRY**; (b) mid_band — remaining **shell-side full-path deficit** until knife-edge; (c) **baffle_count** sweep **not executed** (requires Task024 re-validation).

Evidence: `tests/fixtures/R27H_CANDIDATE_SPACE_EXTENSION.json`.
