# TASK173 v0.7 Sizing authority closure package R2

```ini
TASK_ID=STAGE3_TASK173_SIZING_RESIDUAL_PROJECT_TRANSFER_ADJUDICATION_R1
MODE=OWNER_PROJECT_TRANSFER_AUTHORITY_FREEZE_AND_R2_PACKAGE_CANDIDATE
RESULT=PASS_SIZING_RESIDUAL_PROJECT_TRANSFER_ADJUDICATION_AND_R2_PACKAGE_CANDIDATE
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
SOURCE_HEAD=e44fd8bcbc38468717b7f383cfcd19be46280562
AUTHORITY_PACKAGE_ID=V07-T173-SIZING-AUTHORITY-PACKAGE-R2
AUTHORITY_PACKAGE_CANONICAL_HASH=750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9
EVIDENCE_CANONICAL_HASH=8c3755fb0738a5f65e9a040b0e3e30e15af69bbb919dc2fb4ab8fb6308a0b76d
AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
AUTHORITY_ACCEPTED=false
RESIDUAL_SOURCE_GAP_COUNT=0
TASK173_RATING_COMPLETE=true
TASK173_SIZING_COMPLETE=false
TASK173_COMPLETE=false
STOP=true
```

This is the unified candidate package following the two owner-directed
project-transfer adjudications. It is not a production implementation or
candidate execution result. The four already specified R1 contract shapes
were carried forward from the local-only handoff without re-audit; all six
sub-authorities below are proposed and await the single independent package
review.

## Restricted initial Sizing domain

| Dimension | Frozen R2 candidate scope |
| --- | --- |
| Construction / shell | `FIXED_TUBESHEET` / `E_SHELL` |
| Pass arrangement | One shell pass; one declared straight-through tube pass; countercurrent |
| Unsupported topology | `U_TUBE`, `FLOATING_HEAD`, multi-tube-pass and multi-shell-pass remain BLOCKED pending separate topology authority |
| Service | Steady-state, single-phase, Newtonian, pure ordinary water; clean surfaces only |
| Profile / backend | `V07-T172-WATER-PROPERTY-PROFILE-R2`; reviewed CoolProp 8.0.0 profile |
| Mass flow | Tube 12.000000 kg/s; shell 20.000000 kg/s |
| State domain | 298.15–300.00 K; 100000–101325 Pa |
| Candidate inputs | Only approved catalog, rule pack, source-bound discrete set or owner-approved project-defined discrete set |
| Enumeration limits | At most 32 values per role, 4096 theoretical combinations and 4096 materialized candidates; excess blocks, never truncates |
| Mesh | Explicit transfer of `V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1`; each candidate runs its own sequence 1,2,4,8,16,32,64; reference n=32 is not forced |

No continuous optimizer, post-calculation catalog snapping, unsupported
topology coercion, new fluid, fouling profile, flow range, temperature/pressure
domain or physical equation is admitted.

## Six ordered sub-authorities

The package hash binds these exact ordered identities and hashes:

| # | Authority | Canonical hash | Proposed scope |
| --- | --- | --- | --- |
| 1 | `V07-T173-SIZING-TASK171-CANDIDATE-BINDING-R1` | `bf014e7ca44eb5f9a3a2abec7c41f44b39a2590e7efaf31d77c70c892bcd1a9e` | Candidate-native TASK020/021/022/024 identities; derive topology, physical supports/events, ownership and mapping from selected geometry; numerical mesh cells do not create physical events; unsupported topology remains BLOCKED. |
| 2 | `V07-T173-SIZING-TASK172-CANDIDATE-THERMAL-R1` | `fc7afcc9c51ed5920e3258b2a5683f1274d45df6c7d7e624be29614f97691483` | Candidate geometry/support identities only through reviewed applicability intersections; depends on Jμ project-transfer authority; preserves R94, R98, C_round=1.0, fail-only dogbox R3, exact-zero/portability semantics and local properties. |
| 3 | `V07-T173-SIZING-TASK174-CANDIDATE-HYDRAULIC-R1` | `4d0f83b8ab1777ba6516dfc607c7accc814ef8a521d26c25c8cf0adc1b264023` | Candidate TASK029 and TASK166 closure under component completeness/absence, exact-once Bell event allocation and outlet pressure guard; depends on the candidate TASK174 project-transfer authority. |
| 4 | `V07-T173-SIZING-CANDIDATE-RATING-R1` | `a5536ba8e93dcf9a94f26a8c5274672494dd53b9391a9dad60553067967f49aa` | Separate candidate Rating sibling using full v0.7 physics, producers, mesh, headroom, deterministic replay and energy closure; strict reference Rating API remains unchanged. |
| 5 | `V07-T173-SIZING-REQUIREMENT-CONTRACT-R1` | `e060ecc37f95286de6487a2ef683fcc295004086a3ef4152d1518216b0128a3c` | Every request carries source-bound requirement identity, duty and both DP limits, allowed family, screening and candidate-discrete authorities; no anonymous numeric defaults. |
| 6 | `V07-T173-SIZING-RANKING-POLICY-R1` | `0d9f6c410414f5a556e92dad15b86fabc4c28c07416513a71645160a0349fba6` | New v0.7 identity; Top-N 3, WARN penalty 10, minimize shell DP with weight 1/scale 100, Decimal precision 50 / HALF_EVEN, candidate-hash UTF-8 ascending tie-break. Not the v0.6 policy identity. |

Each remains `PROPOSED_AUTHORITY_REVIEW_PENDING`, `authority_accepted=false`.
The full projection records and hashes are in the [machine package evidence](evidence/TASK-173-v0.7-sizing-authority-closure-package-r2.json).

## Residual project-transfer dependencies

The umbrella additionally binds four exact transfer candidates:

| Authority | Canonical hash | Transfer boundary |
| --- | --- | --- |
| `V07-T173-SIZING-JMU-CONDITIONAL-PROJECT-TRANSFER-R1` | `6d716f541c44aeaa6911efe5919ed2f1474f4af93a4c06fcb01a672c56d234cc` | Jμ is permitted only when all C1–C12 preconditions pass; its effective domain is the intersection of reviewed topology, candidate TASK166/TASK171 validity, water-property and clean-wall domains. It does not expand any of them. |
| `V07-T173-SIZING-BELL-EVENT-ALLOCATION-PROJECT-TRANSFER-R1` | `28c89b6c58fef6050f9a0f5d33b80ce686f875a4ba9350e254d43ff699dccc58` | Candidate TASK171 event producer plus TASK174 exact-once mapping to existing additive regions or non-additive correction/support; no event invention or Bell formula change. |
| `V07-T174-CANDIDATE-REFERENCE-PRESSURE-COUPLING-R1` | `7506d4217d27123cdec1a5d46813445a1a8b500ef24af39e10b7598ba163ce19` | Owner-scoped `PROJECT_MODELING_APPROXIMATION_AUTHORITY`: one-way frozen 101325 Pa thermal-property pressure; native candidate DP post-thermal; no pressure iteration, clamp or extrapolation; outlet pressure must remain 100000–101325 Pa. |
| `V07-T173-SIZING-TASK174-CANDIDATE-PROJECT-TRANSFER-R1` | `893a6c1644a940b27fbad85ef4d4fc402a7999971dc5e2ed3603fada0398b857` | Candidate TASK029 component coverage, physical-absence proof, candidate event ledger, TASK166 numeric regions, pressure guard and diagnostic-only FIV under the same restricted service/topology. |

All four are also proposed and unaccepted. The owner transfer is not described
as an external universal law. The Stage-2 source/engineering evidence remains
the reference instance; no candidate calculation has been run.

## Requirements, disposition and selection

Each Sizing request must carry source-bound positive finite Decimal values for
required duty and maximum tube/shell DP, the allowed construction families,
discrete candidate authorities, and required screening policy. Decisions use
exact Decimal comparisons without epsilon or pre-decision rounding:

* duty passes iff `rated_duty_w >= required_duty_w`;
* tube DP passes iff `modeled_total_tube_dp_pa <= max_tube_dp_pa`;
* shell DP passes iff `bell_total_shell_dp_pa <= max_shell_dp_pa`.

Every enumerated candidate remains in the ledger as PASS, WARN or BLOCKED.
Missing evidence is not PASS. Only complete PASS/WARN candidates without
blockers are recommendable; BLOCKED candidates are excluded from ranking but
retained with reasons. FIV stays `DIAGNOSTIC_SCREENING_ONLY`; a missing numeric
FIV limit is a diagnostic warning, not an invented hard criterion.

The new v0.7 selection policy is deterministic and intentionally limited to
this initial policy. It does not claim global optimum, economic optimum,
CAPEX/lifecycle-cost minimization or universal preference. If there are no
recommendable candidates, the outcome is `NO_RECOMMENDABLE_CANDIDATE`; no
winner is fabricated. Candidate order, full ledger, ranking trace,
recommendation, alternatives, exclusions and provenance are hash-bound in the
future Sizing result identity.

## Frozen reference Rating and status

The reference Rating API, request/result schemas and authority are unchanged.
Its exact identity remains request
`77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed`, result
`fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b`, and
ID `urn:hxforge:task173:fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b`.
TASK168 enumeration may be reused, but its v0.6 TASK162 thermal closure is not
an acceptable v0.7 final candidate Rating. TASK169 mechanics may be reused
only under the new v0.7 policy identity.

`TASK173_RATING_COMPLETE=true` remains reference-case-only;
`TASK173_SIZING_COMPLETE=false`; `TASK173_COMPLETE=false`. Package issuance
does not authorize implementation. No reference Rating, candidate Rating,
Sizing, production mesh or TASK175 execution was performed. The next and only
gate is `STAGE3_TASK173_SIZING_AUTHORITY_PACKAGE_R2_INDEPENDENT_REVIEW`.
