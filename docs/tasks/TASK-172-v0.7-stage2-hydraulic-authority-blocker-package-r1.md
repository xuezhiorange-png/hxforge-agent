# TASK174 Consolidated Hydraulic Authority Blocker Package

**Task:** `TASK172_V0_7_STAGE2_TASK172_RUNTIME_AND_TASK174_HYDRAULICS_R1`
**Disposition:** TASK172 local runtime is implemented and validated; TASK174 closure remains blocked.
**Blocker count:** 3 authority scopes, grouped in this single package.

This package is the current TASK174 disposition, not three micro-gates. The TASK174 API returns a deterministic typed blocked result and will not publish a partial or unconditional pressure-drop total. The accepted TASK171 physical events remain the once-only physical ledger. Numerical subcells do not multiply event or local-loss counts. FIV remains `DIAGNOSTIC_SCREENING_ONLY`; a missing numeric critical-velocity authority is reported diagnostically and is not guessed.

| # | Scope | Required missing authority/binding | Native consumer and fail-closed consequence |
|---|---|---|---|
| 1 | `TUBE_SIDE_TASK029_PATH` | Complete source-bound TASK028 component results and authority/reference-plane bindings, or explicit reviewed physical-absence exclusions, covering `ENTRANCE`, `EXIT`, `CHANNEL_HEAD`, `NOZZLE`, `CONTRACTION`, and `EXPANSION`. | TASK029 completeness partition. Until all six are covered exactly once and a complete native TASK029 result replays, TASK174 returns `BLOCKED_INCOMPLETE_MODELED_BOUNDARY`; no partial total, invented K, or implicit K=0. |
| 2 | `SHELL_SIDE_TASK034_BELL_AGGREGATION` | Reviewed one-to-one mapping from the 19 TASK171 physical events/compartments to native Bell pressure regions, with a complete source-bound TASK034 result tied to the accepted TASK031/TASK020 geometry lineage. | TASK034/TASK166 shell aggregation. Until every physical event is assigned once and the native shell total replays, TASK174 returns `BLOCKED_INCOMPLETE_PHYSICAL_EVENT_AGGREGATION`; Bell/event factors are not duplicated over mesh cells. |
| 3 | `CASE_PRESSURE_PATH` | Reviewed pressure-state coupling authority plus exact support/location pressure values and matching property-snapshot identities, constrained to 100000–101325 Pa. | TASK172 property provider and TASK027/TASK034 pressure-dependent inputs. Until this is bound, no pressure iteration or clamping is permitted and TASK174 returns `BLOCKED_PROPERTY_PRESSURE_COUPLING_AUTHORITY`. |

These are all current blockers. No fluid, pressure path, component geometry, absence, K value, Bell allocation, or pressure-drop result is inferred from fixtures or engineering convention. If later work supplies the source-bound authorities together, the existing orchestrator can consume the native TASK029/TASK034/TASK166 outputs and replay their identities without reimplementing their physics.

```text
TASK174_RUNTIME_IMPLEMENTATION=true
TASK174_CLOSURE=false
STAGE2_HYDRAULIC_AUTHORITY_BLOCKER_COUNT=3
TASK172_RUNTIME_IMPLEMENTATION=true
FIV_REQUIREMENT_MODE=DIAGNOSTIC_SCREENING_ONLY
TASK173_SOLVE_PERFORMED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
STOP=true
```
