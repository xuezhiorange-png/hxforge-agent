# TASK173 v0.7 Sizing residual physical-source authority closure R1

```ini
TASK_ID=STAGE3_TASK173_SIZING_RESIDUAL_PHYSICAL_SOURCE_AUTHORITY_CLOSURE_R1
MODE=DUAL_RESIDUAL_SOURCE_CLOSURE_AND_UMBRELLA_PACKAGE_REISSUE_IF_PASS
RESULT=BLOCKED_SIZING_RESIDUAL_PHYSICAL_SOURCE_AUTHORITY
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
PREDECESSOR_HEAD=698b543e1b41b4c7099cb9ac2a028b25a28c5b00
PREDECESSOR_CLOSEOUT_EVIDENCE_HASH=ca6b37c400b1e15dbe0cbf5e15e45ce38303178952c35955caabc91070ed43f4
OWNER_REPORTED_BLOCKED_PACKAGE_HASH=22c8b55e50eb259136658105ec2c42a74b02b84a3f238ac7716b9294902db0a5
OWNER_REPORTED_BLOCKED_PACKAGE_STATUS=NOT_COMMITTED_LOCAL_EVIDENCE_INPUT_ONLY
EVIDENCE_CANONICAL_HASH=a362e37a61b8c67abc915a455b03f378d1d844af4454d3f417d69132b05ce4ab
AUTHORITY_PACKAGE_ISSUED=false
PRODUCTION_CODE_CHANGED=false
TESTS_CHANGED=false
RATING_REEXECUTED=false
CANDIDATE_RATING_EXECUTED=false
PRODUCTION_MESH_REEXECUTED=false
SIZING_EXECUTED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
STOP=true
```

## Decision

The accepted reference Rating remains frozen and unchanged. This closeout did
not revisit the other four gaps from the local, uncommitted R1 package. It
examined only the two named residual physical-transfer questions.

The complete Jamil et al. article provides meaningful evidence that a
Bell–Delaware model containing the Jμ factor was used while some exchanger
geometry varied. In particular, the article reports a baffle-count study and
an optimization using geometry variables. That closes neither a project
candidate transfer envelope nor a TASK172 local-support transfer on its own:
the available source does not establish a finite, matching intersection for
the project's fixed-tubesheet/E-shell/one-shell-pass domain and its
candidate-derived physical supports. It is recorded as relevant method
evidence, not promoted to a candidate authority.

The accepted Stage-2 TASK174 closure is explicitly for the R2 reference case.
It validates one-way frozen reference pressure at 101325 Pa, using that
case's exact native geometry, pressure snapshots, TASK029 result and Bell
event allocation. The current TASK174 request still requires the
`V07-T174-REFERENCE-PRESSURE-COUPLING-R1` literal and exact reference
snapshots. No existing reviewed source/project authority was found that
transfers that pressure/property coupling to changed candidate geometry. The
task's explicit condition forbids inferring that transfer from the smallness
of reference pressure drops or from the arithmetic `reference pressure - DP`.

Because both residual transfers are not closed, the umbrella
`V07-T173-SIZING-AUTHORITY-PACKAGE-R2` and its dependent sub-authority hashes
are not issued. No source-domain expansion, formula, candidate result, or
reference Rating identity was invented.

## Frozen reference Rating boundary

| Field | Value |
| --- | --- |
| Rating scope | `ACCEPTED_V07_REFERENCE_CASE_ONLY` |
| Request hash | `77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed` |
| Result hash | `fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b` |
| Result ID | `urn:hxforge:task173:fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b` |
| Identity changed | `false` |
| Re-executed in this task | `false` |

## Lane A — TASK172 candidate Jμ geometry/local-state transfer

### Source identity and reviewability

The primary body inspected was Jamil, Goraya, Shahzad and Zubair, “Exergoeconomic
optimization of a shell-and-tube heat exchanger,” *Energy Conversion and
Management* 226 (2020), article 113462, DOI
`10.1016/j.enconman.2020.113462`. Northumbria University's research portal
identifies it as a peer-reviewed journal article and lists the accepted author
manuscript under CC BY-NC-ND. The institutional repository copy is 59 PDF
pages. Existing repository lineage records the acquired-body SHA-256 as
`a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970`.

The exact acquired bytes were not present in the checkout or the checked
temporary source locations. The current direct byte-download attempt failed
at TLS negotiation; therefore this receipt does not claim a new byte-for-byte
SHA verification. The full article was inspected through the same official
Northumbria repository URL already bound in the project source record. No
copyrighted body was copied into the repository.

### What the full article establishes

* §2.1 and Table 2 (PDF pp. 8–9) describe a liquid-phase, segmental-baffle
  water exchanger and a fixed baseline geometry.
* §2.2.2 (PDF p. 11), Eq. (6), places `J_mu` in the Bell–Delaware shell-side
  heat-transfer product with the other correction factors.
* §3.4.2 (PDF pp. 32–33) varies baffle count from 2 to 15 and reports the
  Bell–Delaware shell heat-transfer coefficient and pressure-drop response.
* §3.5 and Table 7 (PDF pp. 38–39) list layout, shell diameter, tube OD, baffle
  cut, baffle spacing, tube passes and tube count as optimization variables;
  the table gives the published bounds. The text says the optimization is
  performed for Kern, Bell–Delaware and Wills–Johnston. The stated bounds are
  selected from cited literature, so they are evidence of the study's tested
  design envelope, not a universal Jμ validity range.

These observations answer the narrow question “was the Jμ-containing
Bell–Delaware model used across actual geometry variation?” affirmatively for
the variables the study reports. They do not establish every row of the
project transfer matrix below, or prove that Jamil's unspecified exchanger
construction/shell-pass context is identical to the project's reviewed
fixed-tubesheet E-shell topology. Nor does the source describe the project's
candidate-derived physical-support/local-state mapping. The project-local
bulk and shell-fluid wall/interface state semantics remain unchanged; this
receipt does not replace them with the paper's state convention.

### Jμ geometry transfer matrix

`JMU_ACTIVE_IN_SAME_MODEL=YES` means the Jamil Bell–Delaware model contains
Jμ; it is not blanket candidate permission. `SOURCE_SUPPORTED_VARIABLE_DOMAIN`
is only the source observation for that row. The complete candidate domain
must still have a source-supported intersection with the reviewed project
topology, Task166 method domain, local-state mapping and approved discrete
candidate space.

| Row | Source ID / location | Source value or range | Variable or fixed | Jμ active in same model | Transfer status |
| --- | --- | --- | --- | --- | --- |
| `SHELL_FAMILY` | Jamil 2020, §2.1, PDF p. 8 | Segmental-baffle STHX; E-shell designation not stated | Fixed/unspecified | Yes, for the study's Bell–Delaware calculations | `NOT_STATED` |
| `CONSTRUCTION_FAMILY` | Jamil 2020, §2.1 and Table 2, PDF pp. 8–9 | Mechanical construction family not stated | Fixed/unspecified | Yes, but not varied or identified | `NOT_STATED` |
| `SHELL_PASS_COUNT` | Jamil 2020, §2.1/Table 2 and optimization section | No shell-pass count stated | Fixed/unspecified | Yes, but not varied or identified | `NOT_STATED` |
| `TUBE_PASS_COUNT` | Jamil 2020, Table 2, PDF p. 9; §3.5/Table 7, PDF pp. 38–39 | Baseline 2; optimization bounds 1–8 | Variable in optimization | Yes; one pass lies in source table bounds | `SOURCE_SUPPORTED_VARIABLE_DOMAIN` |
| `BAFFLE_FAMILY` | Jamil 2020, §2.1, PDF p. 8 | Segmental baffles | Fixed context | Yes | `SOURCE_SUPPORTED_FIXED_CONTEXT` |
| `BAFFLE_SPACING` | Jamil 2020, Table 2, PDF p. 9; §3.5/Table 7, PDF p. 39 | Baseline 0.356 m; optimization bounds 0.05–0.5 m | Variable in optimization | Yes | `SOURCE_SUPPORTED_VARIABLE_DOMAIN` |
| `BAFFLE_CUT` | Jamil 2020, Table 2, PDF p. 9; §3.5/Table 7, PDF p. 39 | Baseline 25%; bounds 0.20–0.35 | Variable in optimization | Yes | `SOURCE_SUPPORTED_VARIABLE_DOMAIN` |
| `BAFFLE_COUNT` | Jamil 2020, §3.4.2, PDF pp. 32–33 | 2–15 | Variable in parametric study | Yes | `SOURCE_SUPPORTED_VARIABLE_DOMAIN` |
| `TUBE_LAYOUT` | Jamil 2020, Table 2, PDF p. 9; §3.5/Table 7, PDF p. 39 | Baseline 30°; bounds 30°–90° | Variable in optimization | Yes | `SOURCE_SUPPORTED_VARIABLE_DOMAIN` |
| `TUBE_PITCH` | Jamil 2020, Table 2, PDF p. 9 | 0.025 m | Fixed context; not an optimization variable | Yes | `SOURCE_SUPPORTED_FIXED_CONTEXT` |
| `TUBE_OD` | Jamil 2020, Table 2, PDF p. 9; §3.5/Table 7, PDF p. 39 | Baseline 0.020 m; bounds 0.015–0.051 m | Variable in optimization | Yes | `SOURCE_SUPPORTED_VARIABLE_DOMAIN` |
| `TUBE_ID_OR_WALL` | Jamil 2020, Table 2, PDF p. 9 | Baseline ID 0.016 m and OD 0.020 m; no ID/wall-thickness range stated | Fixed context | Yes; ID/wall not varied in Table 7 | `SOURCE_SUPPORTED_FIXED_CONTEXT` |
| `TUBE_LENGTH` | Jamil 2020, Table 2, PDF p. 9 | 4.83 m | Fixed context; not an optimization variable in this study | Yes | `SOURCE_SUPPORTED_FIXED_CONTEXT` |
| `TUBE_COUNT` | Jamil 2020, Table 2, PDF p. 9; §3.5/Table 7, PDF p. 39 | Baseline 918; bounds 900–2000 | Variable in optimization | Yes | `SOURCE_SUPPORTED_VARIABLE_DOMAIN` |
| `SHELL_DIAMETER` | Jamil 2020, Table 2, PDF p. 9; §3.5/Table 7, PDF p. 39 | Baseline 0.894 m; bounds 0.1–1.5 m | Variable in optimization | Yes | `SOURCE_SUPPORTED_VARIABLE_DOMAIN` |
| `RE_S` | Jamil 2020, §2.2.2 and §3.4.1 | Shell Reynolds number is used; flow study spans 1–50 kg/s, but no Jμ-specific Re range is stated | Operating variable studied; Jμ Re applicability not bounded | Yes, with no Jμ-specific Re interval | `NOT_STATED` |
| `PR_S` | Jamil 2020, §2.2.2, PDF p. 11 | Pr appears in the ideal-bank coefficient; no Jμ-specific Pr range | No Jμ-specific range stated | Yes | `NOT_STATED` |
| `MU_BULK_OVER_MU_WALL` | Jamil 2020, §2.2.2, PDF p. 11, Eq. (6) | Jμ factor uses bulk/wall viscosity; no numerical ratio interval | State-dependent; no interval stated | Yes | `NOT_STATED` |
| `TEMPERATURE` | Jamil 2020, Table 2, PDF p. 9 | Shell water inlet/outlet 95/40 °C for its baseline; no Jμ temperature envelope stated | Fixed baseline context | Yes | `SOURCE_SUPPORTED_FIXED_CONTEXT` |
| `PRESSURE` | Jamil 2020, Table 2, PDF p. 9 | Allowable operating pressure is listed as 100 kPa; no Jμ property-evaluation pressure rule stated | Fixed context/semantics not stated | Yes | `NOT_STATED` |
| `FLUID` | Jamil 2020, §2.1 and Table 2, PDF pp. 8–9 | Water on shell and tube sides; purity/property backend not specified | Fixed context | Yes | `SOURCE_SUPPORTED_FIXED_CONTEXT` |
| `PHASE` | Jamil 2020, §2.1, PDF p. 8 | Liquid-phase exchanger | Fixed context | Yes | `SOURCE_SUPPORTED_FIXED_CONTEXT` |

### Lane A disposition

`JMU_GEOMETRY_VARIATION_OBSERVED=true` is not equivalent to
`JMU_CANDIDATE_TRANSFER_DOMAIN_CLOSED=true`. A usable authority would need to
freeze a finite project candidate intersection and a fail-closed predicate
for the source-supported rows, while binding the existing local-support
semantics to the candidate-derived supports. The available body does not
identify enough of the source shell/construction context or the local support
transfer to establish that intersection without assuming a method-domain
equivalence. Accordingly:

```ini
JMU_CANDIDATE_TRANSFER_CLOSED=false
JMU_CANDIDATE_TRANSFER_AUTHORITY_ID=NOT_ISSUED
JMU_CANDIDATE_TRANSFER_AUTHORITY_HASH=NOT_ISSUED
JMU_GEOMETRY_TRANSFER_MATRIX_HASH=e34ef8010e1a6650ccb088fcf5b11baebbe312fc2d00f9eda44e75f433c6da92
JMU_EQUATION_OR_EXPONENT_REOPENED=false
PROJECT_LOCAL_STATE_SEMANTICS_CHANGED=false
TASK166_APPLICABLE_USED_AS_AUTOMATIC_JMU_PROOF=false
```

## Lane B — TASK174 candidate hydraulic closure transfer

### Reference-case closure replayed

The Stage-2 closeout and machine evidence establish a successful reference-case
closure only:

* TASK029 has one TASK027 distributed-friction member, zero TASK028 members,
  and explicit reference-case exclusions; its modeled boundary is the
  reference case's tube-internal start-to-end path.
* TASK166's native Bell total reconciles the reference case's central
  crossflow, window and inlet/outlet end-zone regions.
* The reference case's 19 TASK171 physical events are allocated exactly once
  (9 additive, 10 support/correction); this is not a candidate event map.
* TASK174 is `VALIDATED` for the exact reference case with
  `V07-T174-REFERENCE-PRESSURE-COUPLING-R1`, one-way frozen reference pressure,
  and exact tube/shell 101325 Pa snapshots. Outlet pressures remain inside
  100000–101325 Pa. FIV remains diagnostic-only.

The Stage-2 evidence's canonical hash is
`778f0417f82e59a2a3d5b04f344bc052a473a486454cbfba138b6d26a261041d`; the
validated TASK174 result hash is
`e8ce04e6e48120ff8d655c16a4aa07a1ddd32f8bc22afbc1bb750291a35dae0e`.

### Transfer decision

The reference closeout does not establish candidate-bound pressure/property
coupling. The current request model pins the coupling authority to
`V07-T174-REFERENCE-PRESSURE-COUPLING-R1`; the runtime checks that exact ID
and the exact reference-pressure bindings before accepting the pressure path.
Its post-DP outlet-domain guard is necessary but does not itself authorize
using the same inlet-pressure semantics for changed candidate geometry.

The reference TASK029 exclusions and 19-event Bell allocation likewise remain
reference-case evidence. Candidate closure would require the owner-specified
candidate-native completeness/exclusion and exact-once event mapping rules to
be bound to newly materialized TASK020/021/022/024 and TASK171 identities.
The source and current reviewed artifacts do not supply a geometry-independent
pressure-coupling authority that permits the candidate pressure/property
snapshots required by TASK172/TASK027/TASK166. Small reference pressure drops
and arithmetic subtraction are not treated as a substitute for that authority.

```ini
TASK174_REFERENCE_CASE_CLOSURE_REPLAYED=true
TASK029_REFERENCE_CASE_COMPLETENESS=PASS
TASK029_CANDIDATE_COMPLETENESS_TRANSFER=NOT_AUTHORIZED
TASK029_CANDIDATE_PHYSICAL_ABSENCE_RULE_BOUND=false
BELL_REGION_MAPPING_REFERENCE_CASE=EXACT_ONCE
BELL_REGION_MAPPING_CANDIDATE_TRANSFER=NOT_AUTHORIZED
BELL_EVENT_COVERAGE_RULE_BOUND=REFERENCE_CASE_ONLY
PRESSURE_COUPLING_AUTHORITY_ID=V07-T174-REFERENCE-PRESSURE-COUPLING-R1
PRESSURE_COUPLING_TRANSFER=BLOCKED_REFERENCE_CASE_ONLY
REFERENCE_PRESSURE_PA=101325
TASK174_CANDIDATE_HYDRAULIC_TRANSFER_CLOSED=false
TASK174_CANDIDATE_TRANSFER_AUTHORITY_ID=NOT_ISSUED
TASK174_CANDIDATE_TRANSFER_AUTHORITY_HASH=NOT_ISSUED
```

## Consolidated residual-gap ledger

| Unresolved lane | Missing source or transfer authority | Sources searched | Why existing source is insufficient | Minimum additional source/authority needed |
| --- | --- | --- | --- | --- |
| `TASK172_CANDIDATE_JMU_GEOMETRY_AND_LOCAL_STATE_TRANSFER` | A source-backed finite geometry/local-support transfer envelope for the project candidate intersection | Full Jamil 2020 institutional accepted manuscript; existing Jamil/Thome transfer and segment-local convention records; existing TASK166 and property-profile authorities | Jamil shows Jμ active during reported geometry variation, but does not bind the project's exact E-shell/fixed-tubesheet/shell-pass context or show the project's candidate-derived local physical-support mapping across that geometry. Source-unreported rows cannot be filled by inheriting TASK166 applicability. | A legally reviewable, hash-bound method source or explicitly reviewed project transfer authority that names the matching shell/construction/topology context, finite geometry roles/ranges, and candidate physical-support/local-state transfer predicate; all outside the intersection remain blocked. |
| `TASK174_CANDIDATE_HYDRAULIC_CLOSURE_TRANSFER` | Reviewed geometry-independent candidate pressure/property coupling authority, with candidate-bound pressure-state semantics | Stage-2 TASK029/TASK174 reference closeout and evidence; consolidated TASK174 blocker package; current TASK174 strict request/runtime source; existing pressure-domain authority | The only validated authority is `V07-T174-REFERENCE-PRESSURE-COUPLING-R1`, using exact reference geometry and 101325 Pa snapshots. No existing authority states it transfers to changed geometry. Reference component exclusions and Bell event allocation do not become candidate-native evidence. | An explicitly reviewed source/project authority authorizing the candidate pressure path and the exact pressure/property snapshot producer or binding rule across the frozen same-service envelope, while preserving 100000–101325 Pa fail-closed bounds and candidate-native TASK029/event identities. |

## Source hierarchy and boundaries

| Source | Role | Rights/reviewability | Use in this decision |
| --- | --- | --- | --- |
| Jamil et al. (2020), DOI `10.1016/j.enconman.2020.113462`; Northumbria accepted manuscript | `PEER_REVIEWED_SECONDARY_METHOD_SOURCE` | Institutional repository; accepted author manuscript lists CC BY-NC-ND; 59-page PDF; previous acquired SHA-256 is recorded above | Full-body method/geometry observations only; no body copied into this repository and no universal transfer claimed |
| Fettaka, Thibault & Gupta (2013), DOI `10.1016/j.ijheatmasstransfer.2012.12.047` | `BIBLIOGRAPHIC_ONLY` in this gate | ScienceDirect record/abstract accessible; complete lawful reviewable body not acquired here | Abstract is not used to close Jμ transfer |
| Stage-2 TASK029/TASK174 receipt and code | `PROJECT_REFERENCE_CASE_EVIDENCE` | Committed project documents, machine evidence and source | Establishes the reference-case path only, not geometry-independent candidate pressure coupling |

## Final disposition

```ini
UNRESOLVED_LANE=TASK172_CANDIDATE_JMU_GEOMETRY_AND_LOCAL_STATE_TRANSFER;TASK174_CANDIDATE_HYDRAULIC_CLOSURE_TRANSFER
RESIDUAL_SOURCE_GAP_COUNT=2
AUTHORITY_PACKAGE_ISSUED=false
AUTHORITY_PACKAGE_ID=V07-T173-SIZING-AUTHORITY-PACKAGE-R2
AUTHORITY_PACKAGE_CANONICAL_HASH=NOT_ISSUED_RESIDUAL_SOURCE_GAPS
AUTHORITY_LIFECYCLE=NOT_ISSUED
AUTHORITY_ACCEPTED=false
TASK173_RATING_COMPLETE=true
TASK173_SIZING_COMPLETE=false
TASK173_COMPLETE=false
RATING_REEXECUTED=false
CANDIDATE_RATING_EXECUTED=false
PRODUCTION_MESH_REEXECUTED=false
SIZING_EXECUTED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
NEXT_GATE=OWNER_DIRECTION_REQUIRED_FOR_SPECIFIC_RESIDUAL_SOURCE
NEXT_GATE_EXECUTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
STOP=true
```

The machine-readable findings, source identities and full Jμ transfer matrix
are in [the evidence receipt](evidence/TASK-173-v0.7-sizing-residual-physical-source-authority-closure-r1.json).
