# TASK172 R117 — Case Design Source-Binding Correction R1

## Result

This is a provenance-linkage correction to the current, not-yet-independently-reviewed R117 case-design payload. The TASK022 input `maximum_position_count` remains the reviewed value `10000`; only its machine-readable authority `source_id` is corrected.

```text
OLD_SOURCE_ID=V07-T172-INTERNAL-SHELL-BUNDLE-GEOMETRY-R1
NEW_SOURCE_ID=V07-T172-INTERNAL-SHELL-BUNDLE-GEOMETRY-RULE-R1
VALUE_CHANGED=false
ENGINEERING_SEMANTICS_CHANGED=false
AUTHORITY_SCOPE_CHANGED=false
PRODUCTION_CODE_CHANGED=false
```

The prior source identifier did not resolve to the R116-reviewed shell/bundle rule. The corrected identifier is the exact authority ID used by the R116 review, R117 runtime snapshot, and the other TASK022 case-design inputs.

## Identity chain

The correction is based on PR #283 head `4909599ed963469111eae6f5f2bbf9acc7381d09`. The case-design payload retains its stable design ID and all engineering values. Its prior file SHA-256 was `e04e025a918abf7fc08c7e5acb9b9d773222eed0281a30a5f4b4e74a1514d3a9` and prior canonical hash was `fa0c660cef237103a5ca93066107f37b7067bd14abd4207428fa7bd32753c616`. After the one-field correction, its file SHA-256 is `04524496a53506b54b31df45da43c49374ce32ea3b8a7bd36aa418210496a989` and its shared `hexagent.canonical_json.canonical_sha256` is `563e76ef594006a205759484f17c141f3daee969d2691baf9bb472d138f848d9`.

R115/R116 values and the three native runtime snapshots are unchanged. In particular, the runtime tube catalog-record hash (`e98cd8639bc2e1bfcfbd2664bbd4779cbf5983b9e06ca5540178bf49d5ee524d`) is distinct from the TASK021 runtime tube snapshot hash (`ad70e011946ce47e81fdfd5abe7b6376beeb4f4f438bc83e92a703d6f9ee23e2`). The layout and bundle snapshot hashes remain `a4f7383fc5cd865592a766be245aae0ba063136970e905d56681314cac600319` and `cb3bd64b809a3460a0e205650927585a61b46713bb565d45b480387fd7702df8` respectively.

The R117 evidence, its current unreviewed `r117_extension`, and the registry root are rebound to the corrected case-design identities. The correction evidence records the predecessor identities and the corrected field; it does not rewrite R115 or R116 history. The approval-provenance sidecar is unchanged: the shared canonical helper excludes `canonical_hash` from hash input, and its replayed canonical hash remains `2dfdb450f202ebc145063c60c6c648258f4fe76a074715197ba88e647e306bb2`.

## Semantic source validation

Every `BOUND_FROM_REVIEWED_AUTHORITY` input is checked against a field- and stage-specific reviewed authority mapping. The TASK022 maximum-position limit now resolves to `V07-T172-INTERNAL-SHELL-BUNDLE-GEOMETRY-RULE-R1`. Reviewed-profile-bound inputs resolve to `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1`. No unknown or invalid reviewed-authority source binding remains.

## Preserved boundary

This correction does not change any value, classification, case scope, runtime snapshot, or authority lifecycle. It does not materialize or execute TASK020/021/022/024/025, create a `CASE_ID`, define a production mesh profile, resolve reference policy, or run TASK172/TASK174/TASK173/TASK175. `R118_STARTED=false`; PR #283 remains OPEN + Draft; Ready and Merge remain unauthorized.

The prior local full-regression statuses are not relabeled. No new full local regression is claimed by this correction; correction-specific semantic/linkage checks and static checks are reported separately from the exact-final-head CI receipt.
