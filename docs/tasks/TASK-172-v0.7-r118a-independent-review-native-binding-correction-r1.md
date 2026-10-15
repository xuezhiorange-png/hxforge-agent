# TASK172 R118-A Independent Review Native-Binding Correction R1

**Task:** `TASK172_V0_7_R118A_INDEPENDENT_REVIEW_NATIVE_BINDING_CORRECTION_R1`
**Result:** `R118A_INDEPENDENT_REVIEW_NATIVE_BINDING_FINDINGS_CORRECTED`
**PR:** #283 (OPEN, Draft)
**Predecessor HEAD:** `ea44d10b8eadc25f8d86d533a173a16c5b346f02`

## Scope

This correction addresses only the two machine-readable/native-binding findings from independent review. It does not change engineering values, authority scope, or production code. R118-A remains a candidate with lifecycle `PROPOSED_AUTHORITY_REVIEW_PENDING`; this receipt is not the independent review promotion.

## Finding 1 — TASK025 ReferencePlanePair shape

The R118-A candidate now represents each TASK025 length authority using the exact native field names `start_plane` and `end_plane`. Each field is a `ReferencePlanePair` projection with `start` and `end` members. The projection matches the current native `ReferencePlanePair` object and its canonical pair producers. No `start_plane_pair` or `end_plane_pair` request fields remain.

The native `internal_flow_authority_length_hash(...)` and `heat_transfer_authority_length_hash(...)` functions were replayed with `Decimal("6")`, the native canonical pair objects, and `INTERNAL_ARITHMETIC_FROM_LENGTH`. The results remain respectively `90be8f8eea712434cb3372c9b46d04020153d2d6c1595e3b4d56617ce4549b35` and `e57442dd4c4d23e10578899639c3694f311ee64fb9eda196d288df3d1eb173da`; hash semantics did not change.

The native-input completeness matrix now expresses the four fields as `internal_flow_authority.start_plane`, `internal_flow_authority.end_plane`, `heat_transfer_authority.start_plane`, and `heat_transfer_authority.end_plane`, with the exact object projections. The corrected candidate has zero native field-name mismatches and zero object-shape mismatches.

## Finding 2 — TASK024 orientation rationale

The candidate value remains `["BOTTOM", "BOTTOM", "BOTTOM", "BOTTOM"]`. Its rationale now identifies the sequence as a project-design choice in **baffle-index semantic order**: all four candidate baffles intentionally use `BOTTOM`. It does not claim that TASK024 requires lexical sorting, and does not apply automatic alternation or infer orientation from equipment orientation. The repeated-token sequence remains compatible with the native sorted-token guard without using sorting as its design rule.

## TASK025 `profile-001` classification

The native `SUPPORTED_PROFILE_IDS` constant includes `profile-001`, so it is native-supported. Repository authority search found no separate reviewed engineering-profile authority for that ID. The matrix therefore classifies it as `NATIVE_CONTRACT_CONSTANT_ONLY`, not `ALREADY_BOUND_REVIEWED_PROFILE`. The four ReferencePlanePair rows use the same classification for their native closed-contract constants; no reviewed-profile authority is implied.

## Preserved design and governance

All R118-A engineering inputs and prospective geometry outputs remain unchanged. Both TASK025 length hashes are unchanged. No TASK020–TASK025 production result producer was invoked. No configuration, layout, bundle, baffle, area/length result, or case identity was materialized. `CASE_ID`, `CONFIGURATION_ID`, and `GEOMETRY_ID` remain `UNBOUND`; the production mesh profile remains `UNBOUND`; real-case mesh admission remains false.

R1–R117 historical reviewed payloads are unchanged. The current unreviewed R118-A candidate/evidence and its registry bindings are corrected, and a separate correction extension is appended. The registry's two pre-existing duplicate keys are preserved; no historical duplicate-key repair is performed.

The predecessor R118-A CI history is retained: run `36242834553` attempt 1 was cancelled; attempt 2 succeeded on the same predecessor HEAD (50 total jobs, 45 success, 5 skipped, 0 failed/cancelled, final gate success). That CI does not cover this correction HEAD. Exact-final-head CI is recorded after the correction commit and must target the final SHA.

## Validation and disposition

Native model/field-shape inspection, the two native length-hash replays, profile classification, orientation semantics, artifact/canonical hash linkage, historical immutability, append-only registry checks, and static/repository validation are recorded in [the correction evidence](evidence/TASK-172-r118a-independent-review-native-binding-correction-r1.json). Exact-final-head CI is a separate final-head gate.

The candidate remains `PROPOSED_AUTHORITY_REVIEW_PENDING`; `INDEPENDENT_REVIEW_COMPLETE=false`. R118-B is not started. No production code, native geometry materialization, TASK172 runtime, TASK174 solve, TASK173 Rating/Sizing, or TASK175 release acceptance is authorized or performed. The next gate after successful correction validation is `R118B_INPUT_AUTHORITY_INDEPENDENT_REVIEW_ONLY`.
