# V07 General Rating + Sizing End-to-End MVP (R1 / R2)

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
  --input prototypes/v07_general_rating_sizing_mvp/cases/mvp_water_water_physical_r2.json \
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

For positive `target_duty_w`, `hot_side.inlet_temperature_k` must exceed `cold_side.inlet_temperature_k` (checked via `physical_consistency_status()`). The legacy R1 JSON case is retained for evidence but is blocked at workflow time when temperatures are inverted.

Runtime sizing requests are built via `hexagent` implementation-validation producers (`implementation_validation_request.py`); the MVP CLI does **not** import `tests.*`.

## Capability inventory

See `FUNCTIONALITY_INVENTORY.md` for IMPLEMENTED / REUSABLE / MISSING / BLOCKED against Task168–174 and R19–R22.

## Evidence runner

```bash
uv run python prototypes/v07_general_rating_sizing_mvp/run_mvp_r1.py --execute
```
