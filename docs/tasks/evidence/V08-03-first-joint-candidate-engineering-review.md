# First Joint Candidate — Engineering Review (Experimental Prescreen Only)

**Status:** `EXPERIMENTAL_PRESCREEN_ONLY` — not manufacturing acceptance.

## Structure

- Shell ID **0.52 m**, tube length **6.00 m**, **223** tubes, **1** passes, layout `LAYOUT_30_DEG`.
- Tube **OD 0.01905 m** / **ID 0.01575 m**, pitch **0.0254 m**, segmental baffles cut **0.35**, count **4**, spacing **1.20 m**.
- Task021 placement envelope diameter **0.4160000000 m** (scale **0.80** of shell ID — not baffle spacing).

## How this geometry was produced

- Bounded recovery on frozen 0.52 m shell catalog with constrained Task021 envelope overrides.
- Six local combinations (5.5/6.0 m × 0.80/0.85/0.90) only; search frozen after first mid joint pass.
- Candidate `92187d45-ae76-5fdb-bf91-28f9dfca682b` / geometry_v2 `dff4ddcb29abbc15…`.

## Thermal (indicative ε-NTU)

- **CLEAN:** Q=330961.9 W, UA=34253.69 W/K, status=INDICATIVE_PASS.
- **T039_DEMO fouling:** Q=304206.3 W, status=INDICATIVE_FAIL.
- NTU=0.683, Cr=0.5995, ε=0.4400 (counterflow idealization).
- CoolProp water properties at stated inlets; Task037 wall/fouling authorities are experimental V08-03 packs.
- Q_clean - target = 961.9 W is computational prescreen slack only, not a verified thermal design margin.

## Hydraulics (assumption-based full path)

- Mid band: tube Δp=1082.188 Pa (margin 67.812 Pa), shell Δp=1179.998631023644509985811160 Pa (margin 0.001368976355490014188840 Pa).
- High loss shell Δp=1330.494631023644509985811160 Pa — **BLOCKED** vs user limit.
- Only **mid_band** achieves mathematical PASS; high shell loss fails primarily on shell-side budget.
- Nozzle authority: **PROVISIONAL**; `UNRESOLVED`.

## Why only mid K passes

- Mid loss vector sits at tube/shell limits simultaneously; shell margin is numerically ~0 Pa.
- High loss adds ~150 Pa shell excess (see high_loss shell breakdown in JSON spec).

## Experimental inputs still unresolved

- Standard-series nozzle bore and reinforcement not verified.
- Local K vectors and Bell-Delaware calibration are prototype bridges, not licensed rule-pack output.
- Fouling T039_DEMO is sensitivity-only, not plant fouling guarantee.

## Gap to manufacturing release

- Production Task172/173 rating, licensed compliance pack, and verified nozzle/manufacturing authority.
- Independent fouling/cleaning margin and field velocity limits.
- BVP production route remains **STOP** for this prototype.

## Sensitivity (analysis-only)

- mid_band shell full-path Δp within 0.01 Pa of user limit; numerical prescreen pass is not manufacturing margin.
- high_loss_sensitivity shell excess 150.49 Pa; largest listed component=R27B-ASSUMP-SHELL-INLET-NOZZLE (429.717 Pa).
- Nozzle bore authority is PARAMETRIC_CALCULATED, not standard-series; ±5% bore perturbation would shift port velocity ~±10% and local K losses scale ~velocity² (analysis only — K vectors not altered).
- Placement envelope scale 0.80 is Task021 tube-center envelope fraction of shell ID, not baffle spacing.
- HYDRAULIC_ENGINEERING_VALIDATION=UNRESOLVED

Robustness: `SCENARIO_DEPENDENT`; scenario_robustness not met because high K fails.