# V07 General Rating + Sizing End-to-End MVP (R1)

Experimental workflow: **general engineering JSON → Task168 candidates → Task173 integrated rating/hydraulic/sizing → engineering report**.

This is **not** production design approval. Outputs are tagged `NUMERICAL_AUTHORITY_STATUS=CANDIDATE` and `PRODUCTION_DESIGN_APPROVED=false`.

## Quick start

```bash
# Preflight only (Task168 enumeration, seconds)
uv run python -m prototypes.v07_general_rating_sizing_mvp \
  --input prototypes/v07_general_rating_sizing_mvp/cases/mvp_district_heating_water_water_r1.json \
  --output /tmp/mvp_case_preflight \
  --preflight-only

# Full integrated sizing (Task173 rating per admitted candidate — may take tens of minutes)
uv run python -m prototypes.v07_general_rating_sizing_mvp \
  --input prototypes/v07_general_rating_sizing_mvp/cases/mvp_district_heating_water_water_r1.json \
  --output /tmp/mvp_case_full
```

Artifacts include `ENGINEERING_REPORT.json`, `ENGINEERING_REPORT.md`, `TASK168_PREFLIGHT.json`, and (when rated) `TASK173_SIZING_OUTCOME.json`.

## Input schema

See `engineering_input.py` (`hxforge.general-engineering-case.v1`). The MVP enforces the **reviewed Task173 R2 water service envelope**:

- Tube side 12 kg/s, shell side 20 kg/s
- Inlet temperatures 298.15–300 K
- Inlet pressures 100000–101325 Pa
- Single-phase water, fixed tubesheet E-shell

Values outside this envelope are rejected at parse time (fail closed).

## Capability inventory

See `FUNCTIONALITY_INVENTORY.md` for IMPLEMENTED / REUSABLE / MISSING / BLOCKED against Task168–174 and R19–R22.

## Evidence runner

```bash
uv run python prototypes/v07_general_rating_sizing_mvp/run_mvp_r1.py --execute
```
