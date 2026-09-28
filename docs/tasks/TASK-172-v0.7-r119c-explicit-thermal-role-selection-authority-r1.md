# TASK172 R119-C — Explicit Thermal Role Selection Authority

**Result:** EXPLICIT_THERMAL_ROLE_SELECTION_AUTHORITY_RECORDED
**Authority:** V07-T172-R119C-THERMAL-ROLE-SELECTION-R1
**Selected variant:** TUBE_HOT_SHELL_COLD
**PR:** #283, open Draft; predecessor `d3c7ae279caf836f62c72d004f742ecb6e365eed`

## Decision and scope

This record captures the explicit project-engineering reference-case decision delegated by the project owner: the tube side is HOT and the shell side is COLD. The decision selects the already-reviewed R119-A Variant A; it creates no geometry, mesh, thermal model, or standard claim. Its authority class is `EXPLICIT_PROJECT_ENGINEERING_DECISION`, its source class is `PROJECT_OWNER_EXPLICITLY_DELEGATED_DECISION`, and its standard-claim status is `NO_STANDARD_CLAIM`.

Variant A is selected as the effective case-bound TASK171 Definition. Variant B remains a reviewed selectable variant, not effective. The R119-A variant artifacts and R119-B review artifacts are unchanged.

## Role binding

- Tube side: HOT; hot stream path `urn:hxforge:r119a:flow-path:tube:88243c8545466b6536a6101ac505f149b0fd6c6f3adaf562a3ceb77090d17e76`.
- Shell side: COLD; cold stream path `urn:hxforge:r119a:flow-path:shell:7032f11f5e02a4547ab0c463ed22235db7b0779066f39887b79f66ac3abab3ed`.
- Selected source: `docs/tasks/evidence/TASK-172-r119a-task171-definition-variant-a-r1.json`, canonical hash `062f7110f5a9ac14ff0a5f9272008cef2682ba244d40ce9c7656863b44c0ffcc`.

The role-only audit against the other reviewed variant found no non-role engineering delta: geometry, mesh, area ownership, length ownership, and physical events are unchanged. Canonical side-path orientation remains tube 0→6 m and shell 6→0 m. This is a project-internal graph orientation only; it is not a physical plant nozzle-direction claim and creates no nozzle-location authority.

## Retained boundaries

The reviewed flow-path, physical-compartment, area-ownership, length-ownership, and TASK171 structural-mesh authority IDs remain unchanged. Fluid identity remains unbound, and `PROPERTY_PROFILE_AUTHORITY_ID` remains `UNBOUND`.

R119-C does not execute TASK171. `TOPOLOGY_ID` and `TOPOLOGY_AUTHORITY_ID` remain `UNBOUND`; no aggregate `GEOMETRY_ID` is created; production mesh remains unadmitted and the real case remains inadmissible. TASK172 runtime and TASK174/TASK173/TASK175 remain unstarted. Ready and Merge remain unauthorized.

**Next gate:** R119D_CASE_BOUND_TASK171_NATIVE_MATERIALIZATION_ONLY
**Stop:** true
