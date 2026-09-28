# TASK172 Stage-2 Runtime and TASK174 Hydraulics

**Task:** `TASK172_V0_7_STAGE2_TASK172_RUNTIME_AND_TASK174_HYDRAULICS_R1`
**Result:** `STAGE2_PARTIAL_TASK172_COMPLETE_TASK174_BLOCKED`
**PR:** #283, remains Open + Draft
**Predecessor:** `31bf0429eea3f65f744367b3a5f36e982f07cd41`

## Stage-1 review and effective inputs

The supplied external Stage-1 independent-review PASS is recorded at [the review receipt](evidence/TASK-172-stage1-independent-review-r1.json). Its source is `USER_SUPPLIED_EXTERNAL_INDEPENDENT_REVIEW_DECISION`; `SELF_APPROVAL=false` and `CODEX_SELF_APPROVAL_CLAIMED=false`. The Stage-1 authority bundle is accepted with all 12 owner decisions complete. Its production-mesh policy is reviewed, but real-case mesh convergence has not been executed and mesh admission remains false.

The runtime binds to the validated TASK171 topology, selected Variant A (`TUBE_HOT_SHELL_COLD`), reviewed TASK171 mesh/physical-ownership identities, Stage-1 water property profile, 316L clean-wall package, the reviewed R94/R98 case profile, and the reviewed local shell Jμ authority. No aggregate `GEOMETRY_ID` is required or synthesized.

## TASK172 local runtime

Added the public production API under `src/hexagent/exchangers/shell_tube/task172_local_runtime/`. It accepts a strict, closed request and returns a canonicalized valid local constitutive result or typed blocked result. It uses the CoolProp HEOS Water source identity/version/reference-state checks and Stage-1 temperature, pressure, and liquid-phase domain; the native TASK026 tube selector; native TASK166 Bell heat-transfer factors with one local shell Jμ factor; native TASK037 cylindrical wall resistance with distinct inside/outside areas; and the reviewed signed-q/R94/R98 behavior.

Refined numerical supports are generated only within the five accepted physical intervals. Physical event boundaries and ownership are unchanged; support, mesh, cell, and wall identities replay deterministically. No partial result is returned as authoritative. A negative physical heat-transfer direction is typed as blocked; q is not clamped, absolutized, or role-swapped.

The focused TASK172 tests exercise the production runtime using strict native model-shaped lower-level test inputs. They are API/constitutive tests, not a new TASK031/TASK166 real-case materialization receipt and not a whole-exchanger solution. The TASK173-owned integrated boundary solution and real-case mesh-convergence execution were not fabricated.

## TASK174 orchestration and consolidated disposition

Added a strict TASK174 request/result API under `src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration/`. The orchestrator consumes and identity-replays lower-level TASK029, TASK034, and TASK166 results; it retains physical-event multiplicity once, refuses partial tube-side totals, refuses unmatched Bell physical-event allocations, and keeps FIV diagnostic-only without guessing a numeric limit.

The current reviewed case cannot close TASK174. One consolidated blocker package covers three missing authority scopes: (1) source-bound tube-side component/exclusion coverage for a complete TASK029 modeled boundary, (2) the one-to-one TASK171 physical-event to Bell pressure-region allocation and complete TASK034/TASK166 shell aggregation, and (3) reviewed pressure-state coupling with exact location-bound pressure/property snapshots. No K value, physical absence, pressure path, event allocation, or pressure-drop total was invented.

## Validation and remaining boundary

The two new focused test files pass (15 tests). The full shell-and-tube regression set passes when excluding the existing repository-isolation assertion that checks the physical checkout path: it fails in this macOS `/private/tmp/...` worktree because that resolved path contains the substring `/tmp`; the existing test was not changed. Ruff, formatting, CI-scope mypy, manifest D==M, locked sync, and pip-audit pass. The local pip-audit excludes the unpublished project package and reports no known vulnerabilities in audited dependencies.

The real-case mesh profile remains `n=1,2,4,8,16,32,64`, but convergence requires the integrated exchanger boundary state. It is deferred to Stage 3 and `REAL_CASE_MESH_ADMISSIBLE=false` remains unchanged.

```text
TASK172_RUNTIME_IMPLEMENTATION=true
TASK172_RUNTIME_VALIDATION=PASS
TASK174_RUNTIME_IMPLEMENTATION=true
TASK174_CLOSURE=false
STAGE2_HYDRAULIC_AUTHORITY_BLOCKER_COUNT=3
TASK173_SOLVE_PERFORMED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_MAJOR_STAGE=STAGE_2_CONSOLIDATED_TASK174_HYDRAULIC_AUTHORITY_CLOSURE
STOP=true
```
