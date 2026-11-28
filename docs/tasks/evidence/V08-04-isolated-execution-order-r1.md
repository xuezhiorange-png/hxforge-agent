# V08-04 isolated execution order adjustment (R1)

**TASK_ID:** `V08-04`  
**Date:** 2025-11-25 (agent record)  
**Repository:** `xuezhiorange-png/hxforge-agent`  
**V08-03 PR:** #325  
**BASE_HEAD (V08-03 line):** `54b54c38de96eff4a2555c196af424e266788aeb`

## Authorized sequence adjustment

Per owner task message `TASK_ID=V08-04`, implementation proceeds **while V08-03 formal engineering acceptance remains blocked**:

| Gate | Status |
|------|--------|
| `V08_03_ENGINEERING_ACCEPTANCE` | **BLOCKED** (unchanged; Issue #324 criteria not satisfied) |
| `V08-04` hydraulic / nozzle / K-scenario package | **AUTHORIZED** in isolation |
| `PRODUCTION_RATING_VALIDATED` | **false** |
| V08 version scope charter | **unchanged** (`docs/tasks/V08_VERSION_SCOPE_AND_ACCEPTANCE_R1.md`) |
| V07 Golden / production Task173 | **not reopened** |

**Basis:** Explicit owner authorization to reorder execution only; acceptance thresholds, integration dependencies, and release gates in Issues **#318** and **#324** are not relaxed.

## Preservation

No overwrite of:

- V08-03 committed line and experimental records on PR #325
- `FIXED_LAYOUT_VARIABLE_MDOT_HYDRAULIC_REPLAY_V1`
- `V08_AUTONOMOUS_ENGINEERING_SELECTION_MVP`
- `V08_AUTONOMOUS_DESIGN_USER_INPUT_DELIVERY`
- Experimental user-trial web MVP

V08-04 adds **`v08_04_hydraulic_feasibility_gate.py`** as orchestration and evidence over existing R27 / autonomous full-path modules.

## Out of scope (this task)

- V08-05 ranking/report productization
- Production thermal rating sign-off
- Full CI matrix
- Unauthorized git push / merge / Ready