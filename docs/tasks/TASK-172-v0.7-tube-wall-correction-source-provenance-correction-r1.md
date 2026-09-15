# TASK172 R1 — source-provenance metadata correction for the tube wall candidate

## 1. Correction receipt and scope

This is an append-only bibliographic source-metadata correction.  It corrects
one author-initial transcription in the effective source projection.  It does
not rewrite the R23/R24 payloads, their canonical hashes, or the engineering
review conclusion.

```ini
TASK_ID=TASK172_V0_7_TUBE_WALL_CORRECTION_SOURCE_PROVENANCE_CORRECTION_R1
PR_NUMBER=277
EXPECTED_START_HEAD=1f3641c985f8ce66c290abd19e8f208cc2b29481
MODE=SOURCE_PROVENANCE_METADATA_CORRECTION_ONLY
AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
SOURCE_ID=SRC-T172-RELAP7-TUBE-GNIELINSKI-WALL-R3
CORRECTION_TYPE=BIBLIOGRAPHIC_SOURCE_METADATA_ONLY
SOURCE_AUTHOR_RECORDED=E.J. Hansel
SOURCE_AUTHOR_CORRECT=J.E. Hansel
SOURCE_AUTHOR_CORRECTION_REQUIRED=true
SOURCE_PROVENANCE_CORRECTED=true
```

The official source identifies the last author as `J.E. Hansel`.  The prior
R24 review document and evidence recorded `E.J. Hansel`; those records remain
immutable historical evidence of the review input and are not silently
rewritten.  The registry's effective source projection is corrected through
the R25 overlay below.

## 2. Source identity retained

The correction remains bound to the same source and acquisition identity:

```ini
SOURCE_TITLE=RELAP-7 Theory Manual
SOURCE_REVISION=INL/EXT-14-31366 Revision 3
SOURCE_PRINTED=March 2018
SOURCE_BYTES_SHA256=ff25dc788b5fbefd91e9dda2e643332c35ff2e2f9acce7f9bfcb2bc8e2d48c75
SOURCE_ACCESS_PATH=https://inldigitallibrary.inl.gov/content/uploads/50/2026/04/Sort_4964.pdf
SOURCE_RIGHTS=Unlimited Release; approved for public release; further dissemination unlimited
SOURCE_AUTHOR_EXPECTED=J.E. Hansel
```

No source bytes, revision, equation location, rights status, authority ID, or
source ID changed.  This correction does not add a new source or substitute a
different source.

## 3. Engineering semantics are unchanged

```ini
ENGINEERING_SEMANTICS_CHANGED=false
EQUATION_CHANGED=false
EXPONENT_CHANGED=false
DOMAIN_CHANGED=false
TRANSFERABILITY_CHANGED=false
STATE_MAPPING_CHANGED=false
COMBINATION_RULE_CHANGED=false
INDEPENDENT_REVIEW_ENGINEERING_CONCLUSION_CHANGED=false
```

The following R24 conclusions remain effective without alteration:

```ini
INDEPENDENT_REVIEW_RESULT=PASS_FOR_SCOPED_TUBE_WALL_CORRECTION_AUTHORITY
INDEPENDENT_REVIEW_SCOPE=MODEL_LEVEL_TUBE_TURBULENT_WALL_PROPERTY_CORRECTION_ONLY
BASE_FORMULA_ALGEBRAIC_EQUIVALENCE=PASS_EXACT
FRICTION_CONVENTION_MAPPING_VALID=true
TURBULENT_BRANCH_SEPARABLE=true
RELAP_SYSTEM_ORCHESTRATION_TRANSFER_REQUIRED=false
TRANSFERABILITY_ESTABLISHED=true
```

The correction does not change Eq. (741)–(744), exponent `0.11`, the
`Pr_liq/Pr_w` orientation, ratio `[0.05,20]`, effective transfer domain
`3000<Re<5000000`, native Pr admission, heating/cooling semantics, state
mapping, roughness precondition, or pure-water admission scope.

## 4. Lifecycle and blocker state

This metadata repair does not perform lifecycle promotion or remove the
correction authority blocker:

```ini
TUBE_WALL_CORRECTION_STATUS=PROPOSED_AUTHORITY
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=PENDING
LIFECYCLE_PROMOTION_PERFORMED=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The corrected effective source metadata is not an external scoped acceptance,
an engineering sign-off, or production permission.  The next gate remains:

```ini
NEXT_GATE=EXTERNAL_INDEPENDENT_REVIEWER_CONFIRM_OR_REJECT_SCOPED_TUBE_WALL_CORRECTION_ACCEPTANCE
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

## 5. Historical-record boundary

```ini
HISTORICAL_R23_R24_PAYLOADS_REWRITTEN=false
EFFECTIVE_SOURCE_PROJECTION_CORRECTED=true
CORRECTION_OVERLAY_REQUIRED=true
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK026_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
```

The machine-readable evidence and registry overlay bind the old effective
metadata to the corrected effective metadata and preserve the source
fingerprint and all engineering-review identities.
