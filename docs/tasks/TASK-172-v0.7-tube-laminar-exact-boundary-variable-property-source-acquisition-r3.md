# TASK172 R3 — exact-boundary laminar variable-property source acquisition

## 1. Scope and inherited boundary

This is a documentation-only, targeted acquisition for the unresolved
`TUBE-WALL-CORRECTION-AUTHORITY` blocker on Draft PR277.  It is the R3
follow-up to the R2 acquisition and is deliberately limited to the two exact
native TASK026 laminar branches:

* `tube_laminar_chf@1.0.0`, `CONSTANT_HEAT_FLUX`, native `Nu_D = 4.36`;
* `tube_laminar_cwt@1.0.0`, `CONSTANT_WALL_TEMPERATURE`, native `Nu_D = 3.66`.

It does not modify TASK026, its selector, constants, domains, the accepted
turbulent C3 correction, or any production module.  It does not infer a
wall-property correction, an omission rule, or a transfer from one boundary
condition to the other.

```ini
TASK_ID=TASK172_V0_7_TUBE_LAMINAR_EXACT_BOUNDARY_VARIABLE_PROPERTY_SOURCE_ACQUISITION_R3
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
EXPECTED_START_HEAD=538b47b15882d0c536cbc8e8520ca6aafe0eb1df
PREVIOUS_HEAD_SHA=538b47b15882d0c536cbc8e8520ca6aafe0eb1df
MODE=TARGETED_EXACT_BOUNDARY_VARIABLE_PROPERTY_PRIMARY_SOURCE_ACQUISITION_ONLY
PARENT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
RESULT=PASS_WITH_BLOCKER_RETAINED
PRODUCTION_CODE_CHANGED=false
ENGINEERING_RULES_CHANGED=false
TASK026_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
TURBULENT_C3_AUTHORITY_CHANGED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The acquisition target is not merely a paper mentioning variable properties.
For either exact branch, a usable authority body would have to bind the
equation, property ratio and its state locations, heating/cooling semantics,
validity domain, geometry/roughness assumptions, and the combination rule
with the native TASK026 correlation.  A complete body that omits any of those
items is not sufficient for production admission.

## 2. Exact acquisition decision

The official publisher records for Herwig 1985 and Herwig/Voigt/Bauhaus 1989
were verified.  Their abstracts identify the relevant constant-heat-flux and
constant-wall-temperature variable-property studies, respectively.  The
official ScienceDirect article/PDF endpoints returned access-controlled
responses.  The official Elsevier TDM XML endpoints returned only core
metadata and explicitly reported `openaccess=0`; they did not deliver an
article body.  No access control was bypassed and no equation was transcribed
from an abstract, snippet, or secondary source.

Because both Herwig bodies remained unavailable, the narrow Koppel/Smith 1962
fallback was also checked through the official ASME record and Crossref
metadata.  Its official article and PDF endpoints likewise returned HTTP 403;
no complete body was acquired.  This fallback therefore cannot close either
native branch.

The previously acquired NACA TN 2410 body remains a verified government
source, but its declared analytical fluid families are gases and liquid
metals.  It does not establish transfer to the reviewed pure-water profile or
an exact TASK026 CWT/CHF combination rule.  Yang 1962 remains bibliographic
discovery only because its complete body was not acquired.

The correct result is therefore:

```ini
HERWIG_1985_BODY_ACQUIRED=false
HERWIG_1989_BODY_ACQUIRED=false
KOPPEL_1962_BODY_ACQUIRED=false
YANG_1962_BODY_ACQUIRED=false
DEISSLER_TO_TASK172_WATER_TRANSFER_ESTABLISHED=false
HERWIG_TO_TASK026_TRANSFER_ESTABLISHED=false
KOPPEL_TO_TASK026_TRANSFER_ESTABLISHED=false
CWT_BRANCH_DISPOSITION=SOURCE_EVIDENCE_STILL_INSUFFICIENT
CHF_BRANCH_DISPOSITION=SOURCE_EVIDENCE_STILL_INSUFFICIENT
```

No active-correction candidate and no explicit-omission candidate is created
for either branch.  Production variable-property use remains fail-closed.

## 3. Primary target — Herwig 1985, constant heat flux

| Field | Bound value |
| --- | --- |
| Source target | `HERWIG-1985-CHF-VARIABLE-PROPERTIES` |
| DOI | [`10.1016/0017-9310(85)90075-4`](https://doi.org/10.1016/0017-9310(85)90075-4) |
| Official record | [ScienceDirect article record](https://www.sciencedirect.com/science/article/pii/0017931085900754) |
| Title | *The effect of variable properties on momentum and heat transfer in a tube with constant heat flux across the wall* |
| Author | H. Herwig |
| Journal | *International Journal of Heat and Mass Transfer* |
| Publication | Volume 28, Issue 2, February 1985, pp. 423–431 |
| Crossref metadata SHA-256 | `f68dd67ba02b407152af49e3f5711b786b72d5fb79915ca7216d0b7c5f33e7e0` |
| Official TDM endpoint | `https://api.elsevier.com/content/article/PII:0017931085900754?httpAccept=text/xml` |
| TDM response SHA-256 | `ead9b0b5e31f87680488b09427cfc219d2eff9049d5058d24ac09a812b39b58e` |
| TDM response | Core metadata only; `openaccess=0`; no article body |
| Direct publisher response | HTTP 403; response SHA-256 `892d0d1a2f84388e4fdea4666373962e1168f14f45a0995326591ad7e711f01e` |
| Full source body | `NOT_ACQUIRED` |
| Rights status | `OFFICIAL_METADATA_AND_ABSTRACT_ONLY;FULL_BODY_ACCESS_CONTROLLED` |

The abstract is retained only for source identification and high-level
lineage.  It is not sufficient to bind a CHF correction equation, property
ratio, state definitions, domain, or TASK026 combination rule.  In
particular, any exponents or correction factors that may be associated with
the paper are not copied from the abstract or inferred from memory.

The required CHF fields remain unbound:

```ini
CHF_CORRECTION_EQUATION_BOUND=false
CHF_PROPERTY_RATIO_BOUND=false
CHF_BULK_STATE_BOUND=false
CHF_WALL_STATE_BOUND=false
CHF_HEATING_COOLING_SCOPE_BOUND=false
CHF_RE_DOMAIN_BOUND=false
CHF_PR_DOMAIN_BOUND=false
CHF_GEOMETRY_ROUGHNESS_DOMAIN_BOUND=false
CHF_COMBINATION_RULE_BOUND=false
```

## 4. Primary target — Herwig/Voigt/Bauhaus 1989, constant wall temperature

| Field | Bound value |
| --- | --- |
| Source target | `HERWIG-1989-CWT-VARIABLE-PROPERTIES` |
| DOI | [`10.1016/0017-9310(89)90160-9`](https://doi.org/10.1016/0017-9310(89)90160-9) |
| Official record | [ScienceDirect article record](https://www.sciencedirect.com/science/article/pii/0017931089901609) |
| Title | *The effect of variable properties on momentum and heat transfer in a tube with constant wall temperature* |
| Authors | H. Herwig, M. Voigt, F.-J. Bauhaus |
| Journal | *International Journal of Heat and Mass Transfer* |
| Publication | Volume 32, Issue 10, October 1989, pp. 1907–1915 |
| Crossref metadata SHA-256 | `51633c98541409a20b2fbaf71cc5f82b2ef26a147be08b4f2c84b398188e082a` |
| Official TDM endpoint | `https://api.elsevier.com/content/article/PII:0017931089901609?httpAccept=text/xml` |
| TDM response SHA-256 | `02ea21ac3e76ce07496459cea3ef40d6264fb7a5d74932a253d7f480858e9a4d` |
| TDM response | Core metadata only; `openaccess=0`; no article body |
| Direct publisher response | HTTP 403; response SHA-256 `3b5f0e453e48032609a79f38ff0e75a0621dc1358764bafcc289199d128dbfc4` |
| Full source body | `NOT_ACQUIRED` |
| Rights status | `OFFICIAL_METADATA_AND_ABSTRACT_ONLY;FULL_BODY_ACCESS_CONTROLLED` |

The abstract is retained only for source identification.  It does not provide
the exact CWT equation, property ratio, bulk/wall state definitions,
heating/cooling branch semantics, validity domain, or combination rule needed
to authorize a variable-property extension of `tube_laminar_cwt@1.0.0`.
The CWT fields therefore remain unbound:

```ini
CWT_CORRECTION_EQUATION_BOUND=false
CWT_PROPERTY_RATIO_BOUND=false
CWT_BULK_STATE_BOUND=false
CWT_WALL_STATE_BOUND=false
CWT_HEATING_COOLING_SCOPE_BOUND=false
CWT_RE_DOMAIN_BOUND=false
CWT_PR_DOMAIN_BOUND=false
CWT_GEOMETRY_ROUGHNESS_DOMAIN_BOUND=false
CWT_COMBINATION_RULE_BOUND=false
```

The CWT and CHF source lineages remain separate.  No CWT rule is copied to
CHF, and no CHF rule is copied to CWT.

## 5. Narrow fallback — Koppel/Smith 1962

| Field | Bound value |
| --- | --- |
| Source target | `KOPPEL-SMITH-1962-VARIABLE-PROPERTIES` |
| DOI | [`10.1115/1.3684320`](https://doi.org/10.1115/1.3684320) |
| Official ASME record | [ASME Journal of Heat Transfer record](https://asmedigitalcollection.asme.org/heattransfer/article/84/2/157/413498/Laminar-Flow-Heat-Transfer-for-Variable-Physical) |
| Title | *Laminar Flow Heat Transfer for Variable Physical Properties* |
| Authors | L. B. Koppel, J. M. Smith |
| Publication | *Journal of Heat Transfer*, Volume 84, Issue 2, May 1962, pp. 157–162 |
| Crossref search-response SHA-256 | `901ec84cd508169c8a364f857cdc84afb56b25ec7850806c4caa16b14bcb545c` |
| Official ASME record response | HTTP 403; response SHA-256 `516d19b51a6a8141a2ca4cbd0ca668406a0651a039f8e997d548c6248daa34e1` |
| Official PDF response | HTTP 403; response SHA-256 `737bb4596be4cbdad6fc125e1e3e0a66ec5a48397c646666e2fb98e90df89c5e` |
| Full source body | `NOT_ACQUIRED` |
| Disposition | `BIBLIOGRAPHIC_DISCOVERY_ONLY;NO_EQUATION_USE` |

Koppel/Smith was checked only as the explicitly permitted narrow fallback after
the two Herwig bodies remained unavailable.  The accessible metadata does not
provide a complete body, equation/domain table, state-location semantics, or
combination rule.  It is therefore not promoted to a correction or omission
authority.

## 6. Existing evidence retained without transfer

| Evidence | Disposition |
| --- | --- |
| NACA TN 2410 full body | `VERIFIED_SOURCE_NOT_TASK172_TRANSFER_AUTHORITY`; complete body but gases/liquid-metals scope and no exact pure-water TASK026 transfer |
| Yang 1962 official record/abstract | `BIBLIOGRAPHIC_DISCOVERY_ONLY`; complete body unavailable |
| Herwig 1985/1989 official records and abstracts | `PRIMARY_METADATA_AND_ABSTRACT_ONLY`; full bodies unavailable; no equation transcription |
| Koppel/Smith 1962 official metadata | `BIBLIOGRAPHIC_DISCOVERY_ONLY`; full body unavailable |
| NASA secondary mentions | `SOURCE_DISCOVERY_AND_CROSS_CHECK_ONLY`; no formula or exponent use |
| Sieder–Tate memory or anonymous property-ratio factors | `NOT_USED` |
| Accepted turbulent C3 correction | `NOT_TRANSFERRED` |
| Neutral factor `1.0` | `NOT_USED` |

HTTP 403/access-control response hashes in this receipt identify access
attempts only.  They are not represented as source-body hashes and cannot be
used as equation authority.

## 7. Branch disposition and blocker state

| Field | CWT | CHF |
| --- | --- | --- |
| Native correlation | `tube_laminar_cwt@1.0.0` | `tube_laminar_chf@1.0.0` |
| Boundary condition | `CONSTANT_WALL_TEMPERATURE` | `CONSTANT_HEAT_FLUX` |
| Complete qualifying body acquired | `false` | `false` |
| Variable-property use authorized | `false` | `false` |
| Active correction rule | `UNRESOLVED_BY_REVIEWED_AUTHORITY` | `UNRESOLVED_BY_REVIEWED_AUTHORITY` |
| Explicit omission rule | `UNRESOLVED_BY_REVIEWED_AUTHORITY` | `UNRESOLVED_BY_REVIEWED_AUTHORITY` |
| Exact disposition | `SOURCE_EVIDENCE_STILL_INSUFFICIENT` | `SOURCE_EVIDENCE_STILL_INSUFFICIENT` |
| Authority type | `NONE` | `NONE` |
| Candidate status | `NOT_CREATED` | `NOT_CREATED` |

```ini
ALL_ADMITTED_TUBE_BRANCHES_AUTHORITY_COVERED=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
TURBULENT_C3_CORRECTION_STATUS=REVIEWED_AUTHORITY
TURBULENT_C3_CORRECTION_INDEPENDENT_REVIEW=ACCEPTED

REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
NEXT_GATE=AWAIT_COMPLETE_LAMINAR_PRIMARY_SOURCE_AUTHORITY
```

This result does not claim that a variable-property correction is physically
impossible.  It records that no complete, rights-cleared, exact-boundary,
water-transferable source package was acquired.  Production admission must
therefore remain fail-closed rather than selecting an unverified correction or
silently omitting one.

## 8. Governance and immutable boundaries

```ini
HISTORICAL_RECORDS_REWRITTEN=false
TASK026_FILES_CHANGED=false
TASK026_EQUATIONS_CHANGED=false
TASK026_CONSTANTS_CHANGED=false
TASK026_DOMAINS_CHANGED=false
TURBULENT_C3_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
NEW_AUTHORITY_SELF_APPROVAL=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_ACCESS_CONTROL_BYPASS=true
NO_EQUATION_TRANSCRIPTION_FROM_ABSTRACT_OR_SNIPPET=true
```

No active-correction or omission candidate is created because neither exact
branch has a complete source-body package.  The next gate may continue only
with a lawful complete primary source body or a separately reviewed exact
branch disposition; it must not transfer NACA's non-water result, infer an
omission from the native selector flag, or change TASK026.
