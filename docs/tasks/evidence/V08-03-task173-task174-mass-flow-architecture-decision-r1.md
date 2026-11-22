# V08-03 Task173/Task174 mass-flow full-path binding — architecture decision (r1)

**Status:** EXPERIMENTAL_PRESCREEN_ONLY — `APPROVAL_REQUIRED` for any production contract change.  
**Task:** `V08_03_R3_CLOSEOUT_AND_TASK173_ARCHITECTURE_DECISION`  
**Does not supersede:** Task173 production numerical acceptance envelope (class B).

## 1. Binding chain (current)

| Stage | Identity anchor | Mass-flow role | Reuse on sensitivity |
|-------|-----------------|----------------|----------------------|
| Normalized user case + handoff | `normalized_input_hash`, handoff digest | Equipment **authority** for mdot, T, P | Rebuild handoff per perturbed case |
| Task168 request | `task168_request_hash_digest` | Envelope/discrete authority | Rebuild T168 per scenario inlet/mdot |
| Task021 layout | `tube_layout_hash`, `layout_id` | Geometry only | **Frozen** for shortlist replay |
| Task025 | `task025_result_id` | Flow area / parallel paths | **Frozen** with layout |
| Task026 | `task026_result_id`, Re | State at **scenario** mdot/T | **Recompute** on tube mdot/T perturbation |
| Task027 | raw `BL_T027_*` | Friction regime gate | Recompute with Task026; no wrapper override |
| Task029 | `task029_result` | Tube total Δp at enumeration mdot | **Must recompute** if mdot changes |
| Task174 | `task174_result_hash` | Bell–Delaware shell + partial tube hydraulic | **Must recompute** if mdot/T changes |
| Task173 integrated rating | N4 mesh, terminal enthalpy | Production thermal–hydraulic closure | **BLOCKED** (class B) |
| R27 full-path (V08 bridge) | `candidate_hash`, path_input binding | Nozzle K budget + postpass friction split | `run_autonomous_nozzle_full_path` |

### Rejection locus (class A — mass-flow binding)

1. **Primary:** `task174_hydraulic_postpass_from_bindings` reads **enumeration-frozen** `Task026/Task027/Task029` from `bindings.bundle.bundle` while `build_engineering_case_v2_from_v08(bindings.normalized)` carries **perturbed** equipment mass (`engineering_shortlist_robustness_v08._evaluate_layout_scenario` → `TASK173_MASS_BINDING_REJECTED`).
2. **Secondary:** `run_authorized_full_path_hydraulic_calculation` composes path_input (scenario mass) with postpass tube friction/totals (nominal-chain mass) → binding/physical consistency or upstream unusable.
3. **Not the blocker for V08 prescreen:** `experimental_thermal_boundary` allows variable tube/shell mdot when flags set (`axial_rating_engine_v1._thermal_boundary_token`).

## 2. Proposed formal replay (APPROVAL_REQUIRED prototype authority)

**Name:** `FIXED_LAYOUT_VARIABLE_MDOT_HYDRAULIC_REPLAY_V1`

Per sensitivity scenario `s` and frozen shortlist layout `L`:

1. Hold fixed: Task021 layout hash, Task025, geometry_v2, candidate_spec_id, Task168 structural admission record.
2. Build scenario case identity: `normalized_s`, `handoff_s`, `t168_s` (hashes recorded in audit).
3. Rerun: Task026 → Task027 (already implemented in V08-03 fixed-layout replay).
4. **New required step:** R19A-class live hydraulic postpass at scenario mass → fresh `postpass_s` with Task029/174 decomposition aligned to `normalized_s`.
5. Rebuild `CandidateRatingBindings` with `bundle_s` containing updated Task026/027/029 outputs **or** inject postpass-only override contract (see minimal scope).
6. Run R27 `_verify_full_path` with `(case_s, record_L, postpass_s)` — no reuse of 12/20 kg/s Task029 totals.
7. Label outcome `EXPERIMENTAL_PREScreen_HIGH_K` — never `PRODUCTION_RATING_VALIDATED`.

**Invariants:** Task027 transitional bounds unchanged; no hash stripping; no silent swap of layout.

## 3. Blocker classes

### A. `MASS_FLOW_FULL_PATH_BINDING`

| Field | Value |
|-------|-------|
| Root cause | Postpass/hydraulic template frozen at enumeration mass; full-path uses perturbed case mass |
| Modules | `v08_r27_hydraulic_bridge.task174_hydraulic_postpass_from_bindings`, `autonomous_nozzle_full_path_hydraulics_v08`, `authorized_full_path_hydraulic_calculation` |
| Minimal scope | Prototype-only: scenario postpass builder wired from `run_live_thermal_state_hydraulic_postpass` (R19A) or Task026 rerun + Task029 re-execution under fixed geometry |
| Authorization | New experimental authority ID + shortlist binding audit fields; **no** Task173 production tolerance change |
| Reuse tests | `test_r19a_live_hydraulic_mass_flow_rebind.py`, `test_engineering_shortlist_sensitivity_binding_v08.py`, new `mass_flow_postpass_alignment_v08` golden |
| Accept (+) | Perturbed mdot high-K dp computed; postpass `task026_input_mass_flow_kg_s` matches case; layout hash unchanged |
| Reject (−) | Reusing baseline Task029 dp under −3% tube mdot; marking `VERIFIED_ROBUST` without `high_k_dp_computed` |

### B. `PRODUCTION_THERMAL_NUMERICAL_ACCEPTANCE`

| Field | Value |
|-------|-------|
| Root cause | Task172/173 cell search, terminal enthalpy residuals, N4 convergence — independent of V08 prescreen |
| Modules | `task173_integrated_rating`, Task172 shooting, production acceptance gates |
| Minimal scope | Out of V08-03; licensed engineer + rule pack |
| Authorization | Production rating contract / golden revision |
| Reuse tests | V07 live rating shards, Task173 corpus — **not** satisfied by fixing class A |

**Do not conflate:** Fixing A does not validate B.

## 4. Next-phase minimal tasks (if approved)

1. **TASK-V08-04-MDOT-POSTPASS-REPLAY** — implement scenario postpass injection behind `EXPERIMENTAL_VARIABLE_MDOT_FULL_PATH` flag.
2. **TASK-V08-04-EVIDENCE-R4** — regenerate shortlist with mass-flow `high_k_dp_computed` where postpass aligns.
3. **CI** — commit lint fixes on `8ee0962` + R3; rerun shards (expect merge-ref toolchain baseline still separate).

## 5. Engineering authority

- Nominal 330 kW clean prescreen: **feasible** on 235-tube baselines (marginal on T235_L5.5).
- Robust design across mdot/Re/high-K: **not proven** (`ROBUST_DESIGN_PROVEN=false`).
- Task173 production rating: **BLOCKED**.
- Placement / manufacturing: **not approved**.