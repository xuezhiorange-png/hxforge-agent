# TASK172 R115 — Project-Internal Geometry Source and Rule Authority Bundle

## Disposition

RESULT=PROJECT_INTERNAL_GEOMETRY_AUTHORITY_BUNDLE_CANDIDATE_COMPLETED

This append-only candidate freezes one narrowly scoped project-designed tube geometry source, one TASK-021 layout rule, and one TASK-022 shell/bundle rule. It is not an approval, a native geometry run, or a case identity. R116 independent review is required before any authority promotion; R117 is the earliest proposed stage for materializing runtime snapshots and designing the project reference case.

The repository main used as the base was independently fetched at 15ff79ee39bbf6d162cc50e14a95f682a2f8b8a8, matching the requested expected base. The candidate branch is docs/v0-7-task172-internal-geometry-authority-r115.

## Authority bundle and boundary

| Field | Candidate value |
|---|---|
| Bundle | V07-T172-INTERNAL-GEOMETRY-SOURCE-RULE-BUNDLE-R1 |
| Class | PROJECT_INTERNAL_ENGINEERING_AUTHORITY |
| Lifecycle | PROPOSED_AUTHORITY_REVIEW_PENDING |
| Project-designed | true |
| External standard/vendor/as-built source claimed | false |
| Codex self-approval / independent review complete | false / false |

The only proposed applicability is the TASK172 project-designed engineering reference-case family on profile V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1: fixed tubesheet, E-shell, one shell pass, one declared straight-through tube pass, explicit countercurrent paths, steady, single-phase, Newtonian service. This does not create a global geometry standard, TEMA/ASME compliance, vendor equivalence, or authority for other configurations, equipment families, materials, mechanics, or operating domains.

No shell catalog is introduced. The proposed TASK-022 mode is CALLER_SUPPLIED_EXPLICIT; a later case must still provide and validate its explicit shell inside diameter against the computed native bundle envelope and both candidate minimums.

## Frozen project design values

### A. Tube geometry source

V07-T172-INTERNAL-TUBE-GEOMETRY-R1 proposes geometry identity tube/v07-t172-engineering-reference/od01905-id01575/r1, revision R1:

| Dimension | Value | Basis |
|---|---:|---|
| OD | 0.01905 m | Explicit project design input; no standard/vendor claim |
| ID | 0.01575 m | Explicit project design input; no standard/vendor claim |
| Wall | 0.00165 m | Exact Decimal result (OD - ID) / 2 |

The deterministic project geometric derivation uses Decimal arithmetic and the explicitly frozen project pi representation 3.141592653589793:

A_metal = pi * (OD^2 - ID^2) / 4
A_flow = pi * ID^2 / 4
D_h = ID

This yields cross_section_area_m2=0.00009019512508456295703, flow_area_m2=0.000194827831907779506515625, and hydraulic_diameter_m=0.01575. Decimal strings are normalized without redundant trailing zeros. These are candidate geometry projections, not pressure, material, mechanical, thermal, procurement, or compliance authority. TASK-016's catalog record stores these fields and validates positivity and wall consistency; its current producer does not derive areas from OD/ID. The project therefore records the explicit circular-section formulas and precision rule as this candidate's deterministic design derivation rather than misattributing an unstated TASK-016 runtime calculation.

Candidate source binding is V07-T172-INTERNAL-TUBE-GEOMETRY-SOURCE-R1, source type PROJECT_INTERNAL_ENGINEERING_DESIGN, revision R1, located at this R115 artifact and the tube candidate payload. Approval is not effective. Future materialization maps approved_by to the R116 independent-review receipt ID, approved_at to its recorded review timestamp, and runtime state to approved; R115 does not populate or consume those runtime approval fields.

### B. TASK-021 layout rule

V07-T172-INTERNAL-TUBE-LAYOUT-RULE-R1 freezes profile hxforge.shell_tube.tube_layout.v1, mode INTERNAL_GENERIC, rule V07-T172-LAYOUT-TRIANGULAR-02540-R1 revision R1:

| Rule input | Value |
|---|---:|
| Pattern | TRIANGULAR |
| Pitch | 0.0254 m |
| Edge clearance | 0.003175 m |
| Origin mode | CENTER_ON_LATTICE_POINT only |
| Axis orientation | PRIMARY_AXIS_X only |
| Exclusion-zone types | AXIS_ALIGNED_RECTANGLE, CIRCLE |
| Maximum candidate positions | 10000 |
| Rule-pack identity | null |

The frozen inequality is pitch_m >= outer_diameter_m; here 0.0254 >= 0.01905. The maximum is below TASK-021's schema ceiling of 100000. The exclusion-zone capability is an allowed closed set only; it does not require an exclusion zone in a later case and does not assign tube-pass membership.

The candidate carries canonical JSON license evidence with authority_class=PROJECT_INTERNAL_ENGINEERING_RULE, standard_claim_status=NO_STANDARD_CLAIM, and false external-standard, restricted-source, and vendor-proprietary-use flags. Its TASK-012 token projection is project_internal_authority; it is not a TASK-012 approved rule pack. Provenance edge IDs and evidence references are non-empty, sorted, and unique. Approval remains ineffective; a future TASK-021 snapshot may have approval_status=approved only after the R116 receipt is accepted and R117 materializes it.

### C. TASK-022 bundle geometry rule

V07-T172-INTERNAL-SHELL-BUNDLE-GEOMETRY-RULE-R1 freezes schema task022.shell-bundle-rule-authority.v1, profile hxforge.shell_tube.shell_bundle_geometry.v1, mode INTERNAL_GENERIC, rule V07-T172-SHELL-BUNDLE-INTERNAL-R1 revision R1:

| Rule input | Value |
|---|---:|
| Allowed shell authority mode | CALLER_SUPPLIED_EXPLICIT only |
| Minimum bundle peripheral allowance | 0.00635 m |
| Minimum radial clearance | 0.00635 m |
| Maximum position count | 10000 |
| Rule-pack identity | null |

The two 6.35 mm values are explicit project engineering design decisions, not external-standard derivations. No approved shell catalog is required or created. A future explicit shell ID is not automatically acceptable: TASK-022 must compute the envelope from the accepted TASK-021 positions and validate both minimums. No nearest-size selection or hidden shell default is authorized.

## Provenance, candidate state, and future materialization

The three candidate payloads bind their own immutable design values with `hexagent.canonical_json.canonical_sha256`. The bundle evidence binds the source-contract identities and digests, design revision/algorithm, payload paths/hashes, scope, prospective checks, and non-actions. The registry's `r115_extension` binds the document and all payload/evidence file and canonical hashes. The design is a fixed declarative choice, not an optimizer or a hidden search: the values are explicitly selected project inputs and only the derived circular dimensions are computed deterministically.

The source class and license statements describe project-authored candidate content only. No external standard text, vendor content, as-built record, or measured project data was used. Future TASK-021/TASK-022 runtime snapshots must be generated only after independent review and must carry the reviewed approval provenance; candidate hashes are not approval signatures.

## Prospective schema compatibility only

The validation stage loaded one temporary in-memory TASK-016 tube record with `approval_state=pending`; TASK-016 computed its prospective record hash and its approved-only selector returned zero records. Separate TASK-021/TASK-022 prospective authority snapshots used explicit R116_PENDING approval placeholders only in memory to exercise schema shape, enums, decimal lexical checks, candidate hash references, internal-generic mode, null rule-pack identity, NO_STANDARD_CLAIM, pitch/OD, shell-mode, and count bounds. Nothing was persisted or admitted as approved, and no TASK-021 layout enumeration, TASK-022 bundle geometry computation, TASK-020 configuration, TASK-024 baffle geometry, or case output was created.

The following remain false/unbound after R115:

- APPROVED_TUBE_GEOMETRY_AUTHORITY_EFFECTIVE=false
- APPROVED_LAYOUT_RULE_AUTHORITY_EFFECTIVE=false
- APPROVED_BUNDLE_RULE_AUTHORITY_EFFECTIVE=false
- R114_NATIVE_GEOMETRY_PREREQUISITE_RESOLVED=false
- CASE_ID=UNBOUND
- CONFIGURATION_ID=UNBOUND
- GEOMETRY_ID=UNBOUND
- PRODUCTION_MESH_PROFILE_AUTHORITY_ID=UNBOUND
- TASK020_CONFIGURATION_MATERIALIZED=false
- TASK021_LAYOUT_EXECUTED_AS_AUTHORITY=false
- TASK022_BUNDLE_GEOMETRY_EXECUTED_AS_AUTHORITY=false
- TASK024_BAFFLE_GEOMETRY_EXECUTED=false
- TASK172_RUNTIME_IMPLEMENTATION_STARTED=false

R115 does not select a shell diameter, tube count, bundle diameter, baffle geometry, operating state, production mesh, or mesh/convergence policy. R116 independent review is the next gate; no step implies the next.

## Artifacts

- Main evidence: docs/tasks/evidence/TASK-172-project-internal-geometry-source-rule-authority-bundle-r1.json
- Tube candidate: docs/tasks/evidence/TASK-172-internal-tube-geometry-authority-r1.json
- Layout candidate: docs/tasks/evidence/TASK-172-internal-tube-layout-rule-authority-r1.json
- Bundle candidate: docs/tasks/evidence/TASK-172-internal-shell-bundle-rule-authority-r1.json
- Registry extension: r115_extension in docs/tasks/TASK-172-v0.7-authority-registry-r1.json

READY_AUTHORIZED=false · MERGE_AUTHORIZED=false · NO_STEP_IMPLIES_THE_NEXT=true · STOP=true
