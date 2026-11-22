# Intermediate tube count feasibility (design C frozen)

- **Design decision:** EXPERIMENTAL_PRESCREEN_PASS
- **High-K joint prescreen pass count:** 10
- **Model-supported variants:** 16
- **Frozen baseline tubes:** 223 @ scale 0.80

## Scan bounds

Finite grid: scales 0.80, 0.805, 0.81, 0.815, 0.82, 0.825, 0.83, 0.835, 0.84, 0.845, 0.85; lengths 5.5, 6.0 m; not a continuous exhaustive search.

## Discrete tube-count plateaus (Task021 effective parallel count)

- scale **0.80** → **223** tubes; Task027=PASS; Re=4350.1671
- scale **0.805** → **223** tubes; Task027=PASS; Re=4350.1671
- scale **0.81** → **223** tubes; Task027=PASS; Re=4350.1671
- scale **0.815** → **235** tubes; Task027=PASS; Re=4128.0309
- scale **0.82** → **241** tubes; Task027=PASS; Re=4025.2584
- scale **0.825** → **241** tubes; Task027=PASS; Re=4025.2584
- scale **0.83** → **241** tubes; Task027=PASS; Re=4025.2584
- scale **0.835** → **241** tubes; Task027=PASS; Re=4025.2584
- scale **0.84** → **253** tubes; Task027=BLOCKED; Re=3834.3370
- scale **0.845** → **253** tubes; Task027=BLOCKED; Re=3834.3370
- scale **0.85** → **253** tubes; Task027=BLOCKED; Re=3834.3370

## Evidence supersession

Supersedes wording in `docs/tasks/evidence/V08-03-high-k-tube-side-structural-feasibility-r1.json` (r1 preserved).

Fewer parallel tubes raise per-tube mass flow and Reynolds; increasing tube count (larger placement envelope) lowers per-tube flow. Larger tube ID is not a direct Re lever in the fixed catalog scan.

**New tube geometry authority:** not_proven

**Authority / next step:** APPROVAL_REQUIRED: Task168 placement envelope authority for scales 0.815–0.835 (235–241 tubes) as EXPERIMENTAL_SHADOW_ONLY until engineering sign-off; tube catalog OD19.05/ID15.75 unchanged; NOT_PROVEN that new tube record is required.

Status: EXPERIMENTAL_PRESCREEN_ONLY — not manufacturing acceptance.

## Best high-K joint-prescreen variant

- Tubes: 241 @ envelope scale 0.82, L=5.50 m
- geometry_v2: `ac60e2d983da6b271d57e7621e66fac531da40f324f17587229787a38a726ea1`
- clean Q: 336332.7 W; fouled Q: 308505.8 W
- high tube Δp: 1075.105 Pa; high shell Δp: 1146.422025078252712780829671 Pa