# R27G shell geometry local Pareto

TASK_ID: `V07_R27G_SHELL_GEOMETRY_LOCAL_PARETO_OPTIMIZATION`

## Discrete search scope (Task168 authority)

`tube_length_m` and `baffle_spacing_m` are **paired** on the authorized ladder (3.0/0.6 … 4.85/0.97). Local search is **shell_inside_diameter_m ∈ {0.54, 0.56} × four ladder pairs** (8 rated) plus **0.65 m** shell for Phase-A block only (12 records, ≤12 rating budget).

## Verdict @ Q≥330 kW, mid_band K

| Question | Answer |
|----------|--------|
| Joint shell ID + ladder adjustment → **mid_band positive full-path margin**? | **No** |
| Best min margin in search | **−70.87 Pa** shell-side @ **9c4b84db** (0.56 m, 4.85 m, 0.97 m), v=1.0 m/s band edge |
| mid_band formal authorized feasible | **0 / 8** |
| Primary vs reference | **9c4b84db** beats **7357afdf** (−133 Pa at same ladder top) |
| Negative control **09dac82a** | **−296 Pa** mid_band min margin @ band max nozzle |

## Next engineering step

Owner-approved **Task168 dimension extension** (independent baffle spacing and/or additional shell–ladder combos) or **shell bundle** resistance reduction beyond current discrete envelope—not nozzle-only tuning.

Evidence: `tests/fixtures/R27G_SHELL_GEOMETRY_LOCAL_PARETO.json`.
