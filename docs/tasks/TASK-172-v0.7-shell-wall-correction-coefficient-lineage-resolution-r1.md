# TASK172 R1 — shell wall-correction coefficient-lineage resolution

## 1. Receipt and decision boundary

This append-only record resolves the coefficient-definition lineage behind
the native TASK166 shell-side ideal-bank `ji`. It is a source/adjudication
record only. It does not modify TASK166, create a TASK172 production
implementation, or authorize a wall-property correction.

```text
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_COEFFICIENT_LINEAGE_RESOLUTION_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
PREVIOUS_HEAD_SHA=b33bf9060e32c13458a34066ccb5219e3ab78be8
MODE=TARGETED_BELL_COEFFICIENT_LINEAGE_RESOLUTION_ONLY
SUBJECT_BLOCKER=SHELL-WALL-CORRECTION-AUTHORITY
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The resolved identity is deliberately scoped to the native **Jamil
parameter-table representation consumed by TASK166**. It is not a claim
that every Bell--Delaware publication uses the same definition, and it is
not an approval to add a factor to the native equation.

## 2. Native TASK166 coefficient fingerprint

The production comparator was inspected at the predecessor commit. The
current implementation has one explicit coefficient table, five explicit
Reynolds rows, and three layout branches. There is no runtime lookup,
interpolation, or coefficient-generation step.

```text
NATIVE_JI_COEFFICIENT_SOURCE=SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS
NATIVE_JI_COEFFICIENT_TABLE=Jamil accepted manuscript Appendix Table A.1, a1-a4 rows
NATIVE_JI_COEFFICIENT_SOURCE_HASH=a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970
NATIVE_JI_EQUATION=ji=a1*(1.33/(tube_pitch/tube_diameter))^a*Re^a2; a=a3/(1+0.14*Re^a4)
NATIVE_JI_DEFINITION=TASK166 ideal_h=ji*cp*G*Pr^(-2/3)
NATIVE_JI_COEFFICIENT_FINGERPRINT_BOUND=true
NATIVE_JI_COEFFICIENT_FINGERPRINT_SHA256=b6e0b32a794b43d43e6a976e42683f271c2ed25de5c055645b325f9c514bead0
```

The fingerprint preimage is the canonical JSON object containing the table
label, row identifiers and row bounds, and every `(a1,a2,a3,a4)` lexical
value for each layout. The exact preimage is reproduced in the companion
evidence JSON. Its values are:

| Layout | Re row order | `(a1,a2,a3,a4)` values in source order |
| --- | --- | --- |
| 30 degrees | `<10`, `10-<100`, `100-<1000`, `1000-<10000`, `10000-100000` | `(1.400,-0.667,1.450,0.519)`; `(1.360,-0.657,1.450,0.519)`; `(0.593,-0.477,1.450,0.519)`; `(0.321,-0.388,1.450,0.519)`; `(0.321,-0.388,1.450,0.519)` |
| 45 degrees | same five rows | `(1.550,-0.667,1.930,0.500)`; `(0.498,-0.656,1.930,0.500)`; `(0.730,-0.500,1.930,0.500)`; `(0.370,-0.396,1.930,0.500)`; `(0.370,-0.396,1.930,0.500)` |
| 90 degrees | same five rows | `(0.970,-0.667,1.187,0.370)`; `(0.900,-0.631,1.187,0.370)`; `(0.408,-0.460,1.187,0.370)`; `(0.107,-0.266,1.187,0.370)`; `(0.370,-0.395,1.187,0.370)` |

The repository source identities are also bound without changing them:

| Native role | Repository identity | Exact location | SHA-256 |
| --- | --- | --- | --- |
| Equation authority | `SRC-AICHE-GONCALVES-COSTA-BAGAJEWICZ-2019-BELL-DELAWARE` | Gonçalves 2019 Eqs. 36--43, PDF p.4 | `fd39834253245f49609b42340e89ca8c652fed83f7cd7803d6c660bddfd6ca54` |
| Parameter authority | `SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS` | Jamil Appendix Table A.1, accepted manuscript PDF p.57 | `a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970` |
| Native code table | `bell_delaware/heat_transfer.py` | `_A_TABLE` and `calculate_heat_transfer` | `bc442493dbdc52ca0a8c52361276becc2e2e73a246ea5e7f6ab3cecb0306c2ad` |

## 3. Citation-directed source chain

### 3.1 Jamil: exact operational representation

The accepted Jamil manuscript is the decisive source for the current
parameter-table representation. Its public institutional copy is
`https://nrl.northumbria.ac.uk/45157/1/sthx.pdf`, with body hash
`a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970`.
In §2.2.2, PDF p.11, Eqs. (6)--(9):

```text
JAMIL_PUBLIC_ACCESS_PATH=https://nrl.northumbria.ac.uk/45157/1/sthx.pdf
JAMIL_BODY_SHA256=a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970
JAMIL_RIGHTS_STATUS=INSTITUTIONAL_ACCEPTED_MANUSCRIPT_PUBLIC_ACCESS_RIGHTS_SCOPE_RECORDED_IN_TASK166_AUTHORITY
```

* Eq. (6) writes the shell coefficient as the ideal cross-flow coefficient
  times `J_C J_L J_B J_S J_R J_mu`.
* Eq. (7) defines the ideal cross-flow coefficient as
  `h_c = j_i c_p G Pr^(-2/3)`.
* Eqs. (8)--(9) define `j_i` from the four `a` coefficients and the
  Reynolds-dependent exponent `a`.
* Appendix Table A.1, PDF p.57, is titled “Empirical coefficients for `j_i`
  and `f_i` [9]” and contains exactly the rows used by TASK166.
* Appendix Table A.2, PDF pp.58--59, lists wall viscosity `J_mu` as a
  separate correction factor, with the source form
  `J_mu = (mu/mu_wall)^m`.
* Reference [9] identifies the cited source for this Bell--Delaware
  equation/table family as `Thome JR. Engineering Data Book III. Wolverine
  Tube, Inc.; 2004.`

This is not a reconstruction from a symbol or a common engineering
practice. It is the source's own equation placement: the coefficient table
feeds `j_i` in Eq. (7), while `J_mu` is a separate factor in Eq. (6).
Accordingly, the native Jamil representation is an **unnormalized `j_i`
representation with respect to the wall-viscosity factor**. This statement
does not claim that the original underlying experiments were refit by Jamil;
it binds the equation/table definition actually published and adopted as
TASK166's parameter supplement.

### 3.2 Gonçalves: equation authority, not an unverified SI table

The public Gonçalves article body, PDF pp.4--5, Eqs. (36)--(43), gives the
ideal coefficient in the same functional form and gives the coefficient
parameters as being in Supporting Information. Its shell equation has no
`J_mu` term in the accepted TASK166 mapping. The official Wiley article
record confirms that `aic16602-sup-0001-Supinfo.docx` contains the ideal-tube-
bank parameter table, but the body could not be obtained in this audit:

`https://aiche.onlinelibrary.wiley.com/doi/10.1002/aic.16602`

```text
GONCALVES_EQUATION_PROVENANCE_BOUND=true
GONCALVES_SUPPORTING_INFORMATION_BODY_ACQUIRED=false
GONCALVES_SUPPORTING_INFORMATION_TABLE_CONTENT_VERIFIED=false
GONCALVES_COEFFICIENT_PROVENANCE_BOUND=false
```

```text
GONCALVES_PUBLIC_ARTICLE_PATH=https://aiche.onlinelibrary.wiley.com/doi/10.1002/aic.16602
GONCALVES_AUTHORS_COPY_PATH=https://www.ou.edu/class/che-design/pub-papers/Linear%20method%20for%20the%20design%20of%20shell%20and%20tube%20heat%20exchangers%20using%20the%20Bell-Delaware%20Method%28Goncalves%20et%20al%29-19.pdf
GONCALVES_RIGHTS_STATUS=ARTICLE_RECORD_AND_AUTHORIZED_COPY_RECORDED_NO_SI_REPUBLICATION
```

The last field means that the exact Gonçalves SI byte body and its coefficient
preimage are not claimed. It does not invalidate the current TASK166 table:
TASK166 explicitly binds its `a1-a4` values to the separately reviewed Jamil
Table A.1 supplement. The current native coefficient fingerprint is therefore
bound to Jamil, while Gonçalves remains the functional-form authority.

### 3.3 Thome/Wolverine: corroborating later implementation, not primary

A public copy of *Engineering Data Book III*, Chapter 3, was fetched only as
a cross-check. Its file identity is:

```text
THOME_EDB_CROSSCHECK_BODY_ACQUIRED=true
THOME_EDB_CROSSCHECK_BYTES_SHA256=326cf8a5c26d6010b701acc9459424391a59a67c08e28e0a41c699c5b9146ea4
THOME_EDB_CROSSCHECK_ACCESS=https://files.engineering.com/files/e01daa74-5d7f-4923-a8fc-fa05132408b2/WOLVERINE_Single_Phase_Shell-Side_Flow_and_Heat_Transfer.pdf
THOME_EDB_CROSSCHECK_RIGHTS=PUBLIC_COPY_DOWNLOADED;COPY_RESTRICTED;RIGHTS_UNVERIFIED
THOME_EDB_CROSSCHECK_AUTHORITY_ROLE=SECONDARY_CROSS_CHECK_ONLY
```

The cross-check reproduces the later representation: §3.4.6 places
`J_mu=(mu/mu_wall)^m` outside the ideal-bank relation, while §3.4.7 gives
the `alpha_I=j_I c_p G Pr^(-2/3)` relation and points to Taborek's table.
This corroborates, but does not replace, the accepted Jamil body. It is not
used as a primary source, and its body is not relabeled as the exact
Taborek/HEDH body.

### 3.4 Bell 1960 and unacquired ancestors

The acquired Bell 1960 scan remains valid for its own source variant:

```text
BELL_1960_DIMENSIONLESS_J_RATIO=(mu_w/mu)^0.14
BELL_1960_COEFFICIENT_RECONSTRUCTION_RATIO=(mu/mu_w)^0.14
BELL_1960_FACTOR_SCOPE=SOURCE_VARIANT_SPECIFIC_IDEAL_OR_NON_LEAKAGE_TUBE_BANK_J_NORMALIZATION
```

Bell 1960 does not identify the current Jamil Table A.1 coefficient
preimage. The citation-directed primary bodies remain unacquired:

| Target | Body status | Consequence |
| --- | --- | --- |
| Bell, *Final Report ...*, Delaware Bulletin No. 5 (1963) | `BELL_1963_BODY_ACQUIRED=false` | Cannot extend Bell 1960's normalization to the final report. |
| Bergelin et al., Delaware Bulletin No. 4 (1958) | `BERGELIN_1958_BODY_ACQUIRED=false` | Cannot bind an upstream ideal-bank fit definition from the bulletin. |
| Taborek/HEDH exact body | `TABOREK_BODY_ACQUIRED=false` | Jamil's [9] citation is bibliographic lineage only; exact handbook rights/body are not claimed. |

The current result does not require those bodies to decide the native Jamil
variant, because Jamil itself explicitly separates `J_mu` from `j_i`. They
remain relevant if a future task tries to claim ancestry all the way back to
Bell/Bergelin or to transfer a source-specific wall factor into TASK166.

### 3.5 Variant-difference matrix

The following matrix records only what the acquired source bodies actually
bind. `UNAVAILABLE` and `UNDETERMINED` are deliberate evidence states, not
permission to fill a gap from a similarly named Bell--Delaware method.

| Dimension | TASK166/Jamil operational variant | Bell 1960 | Bell 1963 | Bergelin 1958 | Taborek/HEDH |
| --- | --- | --- | --- | --- | --- |
| Ideal HTC base | `h_i=j_i c_p G Pr^(-2/3)` | Source-specific j reconstruction | `UNAVAILABLE` | `UNAVAILABLE` | `alpha_I=j_I c_p G Pr^(-2/3)` in secondary cross-check |
| Viscosity correction | Separate `J_mu` in Jamil Eq. (6); absent in native TASK166 | In j definition/reconstruction | `UNAVAILABLE` | `UNAVAILABLE` | Separate `J_mu` in secondary cross-check |
| Ratio orientation | Jamil `J_mu=(mu/mu_wall)^m`; active transfer not bound | j syntax `(mu_w/mu)^0.14`, reconstruction `(mu/mu_w)^0.14` | `UNAVAILABLE` | `UNAVAILABLE` | `UNAVAILABLE` as primary body |
| Exponent | Jamil `m` is not promoted to a TASK166 transfer value | `0.14` | `UNAVAILABLE` | `UNAVAILABLE` | `m` shown in cross-check, primary body unavailable |
| Wall-state definition | Jamil names wall viscosity; TASK172 mapping open | absolute viscosity at heat-transfer surface | `UNAVAILABLE` | `UNAVAILABLE` | wall viscosity in cross-check |
| Fluid / Re / Pr domain | Native evaluator and table scope only; not wall-factor domain | Not complete for transfer in this record | `UNAVAILABLE` | `UNAVAILABLE` | secondary cross-check only |
| Geometry / layout | Jamil Table A.1 rows and 30/45/90 degree layouts | Source-variant scope not mapped to native table | `UNAVAILABLE` | `UNAVAILABLE` | TEMA E single-segmental context in cross-check |
| Combination position | `J_mu` is after `h_c`, before no native implementation because TASK166 omits it | Part of source-specific j normalization/reconstruction | `UNAVAILABLE` | `UNAVAILABLE` | outside ideal relation in cross-check |
| Source body complete | Jamil body acquired and hash-bound; cited Thome body not acquired | Yes | No | No | Public copy acquired, rights unverified; secondary only |

The matrix is intentionally asymmetric: the native operational definition is
well bound from Jamil, while the ancestry of its empirical rows beyond
Jamil's citation is not. An `EXACT_MATCH` of coefficient values therefore
does not, by itself, bind Bell 1960's normalized j definition.

## 4. Coefficient-definition identity test

The two required identity questions are answered separately:

| Question | Evidence | Result |
| --- | --- | --- |
| A. Are the values used by TASK166 descended from the table? | Exact byte-bound repository `_A_TABLE` matches every Jamil Table A.1 `a1-a4` layout/row value; TASK166 authority names Jamil as the parameter supplement. | `true` for the native Jamil table. |
| B. What `j` definition is attached to that table? | Jamil Eq. (7) defines `h_c=j_i c_p G Pr^(-2/3)`; Eq. (6) multiplies the independently named `J_mu` after `h_c`; Table A.2 defines `J_mu` separately. | `j_i` is unnormalized by the wall-viscosity factor in this representation. |

The exact primary coefficient-fit ancestry behind Thome's cited table is not
claimed beyond the Jamil operational definition. This avoids turning the
unacquired Bell 1963/Bergelin/Taborek bodies into implied evidence.

The resulting classification is:

```text
NATIVE_JAMIL_J_FACTOR_NORMALIZATION=WITHOUT_WALL_VISCOSITY_IN_JI
J_FACTOR_LINEAGE_IDENTITY_SCOPE=TASK166_NATIVE_JAMIL_OPERATIONAL_VARIANT
J_FACTOR_LINEAGE_IDENTITY_BOUND=true
J_FACTOR_NORMALIZATION_CONTAINS_WALL_VISCOSITY=false
CORRECTION_IS_PART_OF_NATIVE_TASK166_IDEAL_BANK_BASE=false
CORRECTION_IS_OPTIONAL_ENGINEERING_EXTENSION=false
BELL_1960_FACTOR_TRANSFER_REJECTED=true
COEFFICIENT_LINEAGE_CONFLICT=false
```

`COEFFICIENT_LINEAGE_CONFLICT=false` means no authoritative contradiction
between the selected native variant and Bell 1960 was found. They are
source-specific representations. `BELL_1960_FACTOR_TRANSFER_REJECTED=true`
means that Bell 1960's factor cannot be inserted into TASK166 merely because
the two variants use the same method family or a related exponent.

## 5. Transfer-contract boundary after resolution

The lineage decision must not be confused with an active shell correction
authority. Only the source syntax observations are bound at this stage:

| Field | Status | Meaning |
| --- | --- | --- |
| `CORRECTION_EQUATION_BOUND` | `false` | No new correction equation is authorized for TASK166. |
| `PROPERTY_RATIO_BOUND` | `true` | Ratio syntax is source-bound for Bell 1960/Jamil `J_mu` observations only; it is not a TASK166 transfer permission. |
| `EXPONENT_BOUND` | `true` | Bell 1960's `0.14` is source-bound; Jamil's `m` remains a separate source parameter and is not promoted here. |
| `BULK_STATE_BOUND` | `false` | Jamil's current equation placement does not complete the requested TASK172 local bulk-state mapping. |
| `WALL_STATE_BOUND` | `false` | The source wall surface is not yet bound to a TASK172 produced shell-fluid wall-interface state. |
| `RE_DOMAIN_BOUND` | `false` | The native evaluator range is not a wall-factor validity range. |
| `PR_DOMAIN_BOUND` | `false` | No transfer-domain Prandtl interval is established. |
| `FLUID_SCOPE_BOUND` | `false` | No complete active-correction fluid scope is established. |
| `HEATING_COOLING_SCOPE_BOUND` | `false` | No transfer direction contract is established. |
| `GEOMETRY_LAYOUT_DOMAIN_BOUND` | `false` | Coefficient-table layout identity does not by itself bind wall-factor transfer. |
| `COMBINATION_RULE_BOUND` | `false` | No production placement of an active factor is authorized. |

In particular, the accepted current TASK166 equation remains unchanged:

```text
ideal_h=ji*cp*G*Pr^(-2/3)
shell_h=ideal_h*Jc*Jl*Jb*Js*Jr
```

No `J_mu`, `(mu/mu_wall)^0.14`, or other wall-property field is added.

## 6. Final blocker and next gate

```text
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
SHELL_WALL_CORRECTION_TRANSFER_AUTHORITY_CANDIDATE_CREATED=false
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The coefficient identity question is resolved, but the shell blocker remains
because an active Jamil/Thome-variant `J_mu` transfer still lacks the
independent bulk/wall state, applicability, and combination contract. The
next gate is deliberately limited to that remaining contract:

```text
NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_JAMIL_THOME_ACTIVE_JMU_TRANSFER_AUTHORITY_R1_ONLY
```

That next gate must not modify TASK166 or infer any missing source domain.

## 7. Forbidden transfers and governance

```text
TASK034_WALL_AUTHORITY_REUSE=NO
TASK034_TRANSFER_TO_TASK166_HEAT_TRANSFER=false
TUBE_RELAP_CORRECTION_TRANSFER_TO_TASK166=false
MARTIN_GNIELINSKI_CROSSFLOW_TRANSFER_TO_TASK166=false
SECONDARY_TABOREK_TRANSFER_TO_TASK166=false
TRANSFER_BY_EQUAL_EXPONENT=false
```

The TASK034 `(mu_b/mu_w)^(7/50)` pressure-drop term remains a different
authority. Equal numerical exponent values do not establish equal physical
quantity, state locations, source domain, or coefficient identity.

No new authority was self-approved and no historical record was rewritten:

```text
RESULT=RESOLVED
REVIEW_STATUS=COEFFICIENT_LINEAGE_RESOLVED_NATIVE_VARIANT_SHELL_BLOCKER_RETAINED
LIFECYCLE_PROMOTION_PERFORMED=false
HISTORICAL_RECORDS_REWRITTEN=false
GOLDEN_APPROVED=false
```

The companion evidence and append-only registry extension are:

```text
EVIDENCE_PATH=docs/tasks/evidence/TASK-172-shell-wall-correction-coefficient-lineage-resolution-r1.json
REGISTRY_PATH=docs/tasks/TASK-172-v0.7-authority-registry-r1.json
```

## 8. Validation receipt

The final validation receipt is completed after the append-only evidence and
registry hashes are materialized:

```text
DOCUMENT_HASH_RECORD=RECORDED_IN_COMPANION_EVIDENCE
EVIDENCE_CANONICAL_HASH_RECORD=RECORDED_IN_COMPANION_EVIDENCE
REGISTRY_EXTENSION_CANONICAL_HASH_RECORD=RECORDED_IN_APPEND_ONLY_REGISTRY
REGISTRY_ROOT_CANONICAL_HASH_RECORD=RECORDED_IN_APPEND_ONLY_REGISTRY
```

Only documentation/evidence files are in scope. Exact-head CI, source hash
consistency, JSON/registry checks, and the diff allowlist are reported in the
final task receipt; they do not promote the shell blocker or authorize a
downstream task.
