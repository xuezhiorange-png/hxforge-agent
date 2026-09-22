# TASK172 v0.7 — shell J_mu open-access transfer authority resolution R1

## Receipt boundary

```ini
TASK_ID=TASK172_V0_7_SHELL_JMU_OPEN_ACCESS_TRANSFER_AUTHORITY_RESOLUTION_R1
MODE=TARGETED_OPEN_ACCESS_SHELL_JMU_TRANSFER_AUTHORITY_RESOLUTION_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=ceb4a38aeba7bef9034f34b10549ea41a97ee563
HEAD_PRECONDITION_VERIFIED=true
RESULT=RESOLVED_SHELL_JMU_OPEN_ACCESS_TRANSFER_CANDIDATE
```

This gate resolves only a scoped, proposed transfer candidate for the
shell-side Bell–Delaware wall-viscosity factor. It does not create reviewed
physical authority, executable authority, a real case, a property snapshot, or
a production implementation. The source bodies were inspected temporarily
from publisher-controlled URLs and were not vendored into the repository.

The historical R1–R88 documents, evidence payloads, and registry extensions
remain immutable. This document is the R89 append-only resolution record.

## 1. Source acquisition and identity

The primary body is the publisher PDF for:

> Bayram, Halil; Sevilgen, Gökhan. “Numerical Investigation of the Effect of
> Variable Baffle Spacing on the Thermal Performance of a Shell and Tube Heat
> Exchanger.” *Energies* 2017, 10(8), 1156.
> DOI: `10.3390/en10081156`.

The target is §2.1.2, printed page 4 of 19, Equations (18) and (19). The
publisher PDF title page, authors, journal/volume/article identity, DOI, and
the target section were verified. The rendered target page was visually
inspected in addition to text extraction.

The published correction was also acquired and inspected:

> Bayram, Halil; Sevilgen, Gökhan. “Correction: Halil, B.; Gökhan, S.
> Numerical Investigation of the Effect of Variable Baffle Spacing on the
> Thermal Performance of a Shell and Tube Heat Exchanger.” *Energies* 2017,
> 10(12), 2181. DOI: `10.3390/en10122181`.

Its body says that the correction changes only Equation (8) on page 3, the
tube-side Petukhov–Kirillov relation. It does not amend Equations (18) or
(19), and it does not amend the target viscosity ratio.

Both bodies carry the publisher’s CC BY 4.0 notice. The recorded hashes,
access paths, page counts, format, and review-use boundary are machine-bound
in the evidence JSON and registry extension. No external PDF is redistributed
by this commit.

The Bayram paper cites Kakaç, Liu, and Pramuanjaroenkij, *Heat Exchangers:
Selection, Rating, and Thermal Design* (CRC Press, 2012), pp. 361–425, ISBN
`978-1-4398-4991-0`, as reference [1] and directs the reader to it for method
details. That book body was not acquired. It is recorded as bibliographic
lineage only; no restricted text is used as evidence in this gate.

## 2. Exact Bell–Delaware extraction

The following is a short transcription of the target equations, not a claim
that the whole Bayram implementation is imported:

```text
Eq. (18), printed p. 4:
h_o = h_id · J_c · J_l · J_b · J_s · J_r

Eq. (19), printed p. 4:
h_id = j_i · c_p,s · Φ · (m_dot_s / A_s)
       · (k_s / (c_p,s · μ_s))^(2/3)
       · (μ_s / μ_s,w)^0.14
```

The surrounding text identifies `h_id` as the ideal heat-transfer coefficient
for pure crossflow in an ideal tube bank; `j_i` is the Colburn j-factor;
`J_c`, `J_l`, `J_b`, `J_s`, and `J_r` are the Bell–Delaware correction factors.
The nomenclature defines `s` as shell, `w` as wall, `b` as bulk mean, and `id`
as ideal. It defines:

```text
μ_s   = shell-fluid dynamic viscosity at average temperature
μ_s,w = shell-fluid dynamic viscosity at wall temperature
```

Therefore the target ratio is explicitly shell-fluid bulk/average-temperature
viscosity divided by shell-fluid wall-temperature viscosity, raised to 0.14.
The source does not identify the wall temperature as a metal centerline or as
an arbitrary outer surface; the supported semantics are
`SHELL_FLUID_AT_WALL_TEMPERATURE`.

The source’s Eq. (19) also contains `Φ`, which its nomenclature and Eq. (27)
identify as a CFD dissipation function. That source-specific symbol is not
reassigned to `J_mu`, is not silently dropped from the exact source record,
and is not imported into the native TASK166/Jamil representation. This gate
transfers only the independently identifiable viscosity-ratio factor and its
multiplicative placement.

The nearby Kern Eq. (16),
`φ_s=(μ_b/μ_w)^0.14`, is a shell-side viscosity correction in the Kern
pressure-drop subsection (§2.1.1). It is explicitly excluded as the Bell
authority. The R89 Bell finding comes from Eq. (18)/(19), not from Eq. (16),
memory, or a pressure-drop formula.

## 3. Method scope versus study scope

The method text establishes a Bell–Delaware ideal crossflow/tube-bank
structure and names the correction factors. It does not state a universal
fluid, phase, temperature, viscosity-ratio, or heating/cooling domain for the
viscosity factor. The paper’s study scope is narrower and is not generalized:

| Dimension | Paper study scope | R89 transfer treatment |
| --- | --- | --- |
| Fluid | Water on both shell and tube sides | `CASE_ONLY`; candidate narrowed to existing admitted water scope |
| Phase | Water study at ordinary liquid conditions | `CASE_ONLY`; no broad phase claim |
| Reynolds number | Shell `Re` reported about 2773; text gives `J_r` handling for `Re<100` and `Re>100` | `CASE_ONLY`/source rule only; no new universal Re domain |
| Prandtl number | Not separately bounded for transfer | `NOT_EXPLICITLY_STATED` |
| Viscosity ratio | Ratio appears; no admissible ratio interval stated | `NOT_EXPLICITLY_STATED` |
| Temperature | Shell supply 10 °C, tube supply 50 °C; property table is at mean temperature | `CASE_ONLY`; no new temperature operator |
| Geometry | One-pass E-shell, 19 tubes, 7 baffles, 44 mm shell ID, 4 mm tube ID, 221 mm effective length | `CASE_ONLY`; no geometry broadening |
| Heating/cooling | Hot tube water and cold shell water in the study | `NOT_EXPLICITLY_STATED`; no universal heating/cooling claim |

The candidate is therefore limited to single-phase liquid pure ordinary water,
the existing TASK166/native Bell geometry and admitted base-correlation domain,
the reviewed water-property authority, and a clean shell-fluid wall/interface
mapping. The source does not prove segmented local execution, but it also does
not require a whole-exchanger inlet/outlet mean. Under the already reviewed
R84 runtime architecture, local bulk mapping is compatible without importing a
new whole-exchanger mean rule.

## 4. Existing HXForge lineage replay

R40 is replayed without modification:

```ini
J_FACTOR_LINEAGE_IDENTITY_BOUND=true
J_FACTOR_NORMALIZATION_CONTAINS_WALL_VISCOSITY=false
NATIVE_JAMIL_REPRESENTATION=hc=ji*cp*G*Pr^(-2/3);Jmu=(mu/mu_wall)^m
```

The native j-factor path therefore does not already contain the wall-viscosity
normalization. Under that identity boundary, the Bayram factor can be
decomposed as an independent multiplicative factor:

```text
Bayram shell factor:
  [native ideal-bank base factors] × (μ_s / μ_s,w)^0.14

Native TASK166/Jamil form:
  [native ideal-bank base factors] × J_mu

Transfer identity:
  J_mu = (μ_bulk / μ_wall)^0.14
```

The algebraic equivalence is asserted only for this isolated factor, with the
same shell bulk viscosity identity, shell-fluid wall viscosity identity,
exponent, and multiplicative placement. It is not a claim that the source’s
entire Eq. (19), including `Φ`, replaces the native Jamil base coefficient.

Double counting is rejected: an implementation may not import Bayram’s whole
`h_id` expression and also multiply the native base by the same viscosity
factor. The admitted representation must contain the wall-viscosity factor
exactly once.

## 5. TASK172 mapping and pressure boundary

The source’s bulk/wall distinction maps as follows for the proposed scope:

```ini
JMU_RUNTIME_GRANULARITY=SEGMENT_LOCAL_CONSTITUTIVE_EVALUATION_STATE
MU_BULK_SOURCE=LOCATED_LOCAL_SHELL_BULK_PROPERTY_STATE
MU_WALL_SOURCE=LOCATED_LOCAL_SHELL_FLUID_WALL_INTERFACE_PROPERTY_STATE
SOURCE_TO_TASK172_SHELL_WALL_PROPERTY_MAPPING_COMPATIBLE=true
SOURCE_TO_TASK172_SHELL_WALL_PROPERTY_MAPPING_BOUND=true
WALL_MAPPING_SCOPE=CLEAN_SURFACE_ONLY
FOULED_INTERFACE_TRANSFER=BLOCKED_PENDING_SEPARATE_WALL_LOCATION_AUTHORITY
SOURCE_REQUIRES_BULK_PROPERTY=true
SOURCE_REQUIRES_WALL_PROPERTY=true
SOURCE_EXPLICITLY_REQUIRES_WHOLE_EXCHANGER_MEAN=false
TASK172_LOCAL_BULK_MAPPING_COMPATIBLE=true
```

The source’s pressure-drop equations and its study boundary pressures do not
define a pressure convention for local property evaluation. R84 remains the
effective owner boundary:

```ini
LOCAL_PROPERTY_PRESSURE_SOURCE=LOCATED_LOCAL_SHELL_PRESSURE_STATE
TASK172_GENERATES_HYDRAULIC_PRESSURE_FIELD=false
MEAN_PRESSURE_RULE_REQUIRED_FOR_LOCAL_RUNTIME=false
PRESSURE_SEMANTICS=NO_CONFLICT
```

No inlet pressure, outlet pressure, arithmetic-mean pressure, representative
pressure, pressure-insensitivity assumption, or new pressure authority is
introduced here.

## 6. Candidate decision

The exact target equation, exponent, shell/wall symbol semantics, multiplicative
placement, correction status, rights, and compatibility with the existing
native Jamil lineage are sufficient for a narrow transfer candidate. Bayram
and Sevilgen is classified as an
`OPEN_ACCESS_PEER_REVIEWED_SECONDARY_METHOD_SOURCE`, not as the primary Bell
authority and not as a replacement for the native Jamil source lineage.

The candidate is proposed only for the scoped shell-side J_mu factor:

```ini
SHELL_JMU_TRANSFER_AUTHORITY_CANDIDATE_CREATED=true
SHELL_JMU_TRANSFER_CANDIDATE_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
JMU_EQUATION_TRANSFER_BOUND=true
JMU_EXPONENT_TRANSFER_BOUND=true
JMU_MULTIPLICATIVE_COMBINATION_BOUND=true
JMU_SHELL_WALL_PROPERTY_MAPPING_BOUND=true
JMU_DOUBLE_COUNTING_REJECTED=true
JMU_RUNTIME_LOCAL_STATE_MAPPING_COMPATIBLE=true
JMU_EXECUTABLE_AUTHORITY_BOUND=false
NEW_AUTHORITY_SELF_APPROVAL=false
```

This is not independent review or lifecycle promotion. The shell-wall
correction blocker remains open as `PROPOSED_AUTHORITY_REVIEW_PENDING`; its
canonical blocker is not removed. R88’s numerical-method state and the
numerical-error-budget and mesh branches remain unchanged.

## 7. Preserved downstream and governance state

```ini
JMU_BULK_PRESSURE_RULE_BOUND=false
WHOLE_EXCHANGER_SOURCE_MEAN_PATH_SELECTED_FOR_TASK172_RUNTIME=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
REAL_JMU_BULK_PROPERTY_SNAPSHOT_PRESENT=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=3
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The remaining parent blockers are:

1. `SHELL-WALL-CORRECTION-AUTHORITY` — proposed transfer candidate awaiting
   independent review;
2. `NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW`;
3. `MESH-CONVERGENCE-QUALIFICATION`.

No production code, engineering calculation, dependency, lockfile, TASK166,
or TASK171 artifact changed. No J_mu execution, wall solve, numerical
experiment, real case, property snapshot, Q work, or mesh study occurred.

## 8. Next gate

```ini
NEXT_GATE=AUTHORIZE_TASK172_SHELL_JMU_OPEN_ACCESS_TRANSFER_AUTHORITY_INDEPENDENT_REVIEW_R1_ONLY
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
LOCKFILE_CHANGED=false
TASK166_CHANGED=false
TASK171_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
