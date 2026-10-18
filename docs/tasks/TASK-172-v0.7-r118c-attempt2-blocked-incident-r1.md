# TASK172 R118-C Attempt 2 Blocked Incident R1

Task: TASK172_V0_7_R118B_NATIVE_PUBLIC_PROJECTION_ORACLE_AMENDMENT_AND_R118C_ATTEMPT2_INCIDENT_R1

## Disposition

Attempt 2 result: BLOCKED_R118C_R2_TASK021_NATIVE_PROJECTION_MISMATCH. It is permanently non-authoritative, non-reusable, and may not be resumed.

## Governed stage history

- TASK014: PASS_IN_MEMORY_DISCARDED
- TASK020: VALID_IN_MEMORY_DISCARDED
- TASK021: VALID_IN_MEMORY_253_POSITIONS_DISCARDED
- TASK022: NOT_INVOKED
- TASK024: NOT_INVOKED
- TASK025: NOT_INVOKED
- Run B: NOT_EXECUTED

No downstream producer was invoked before its preceding gate passed. No sequence violation occurred.

## Failed oracle

Actual TASK021 public x lexeme was -0.1524; the then-expected string was -0.152400000000. The values are numerically equal as Decimals but not equal canonical public lexemes. The old expected string retained quantized Decimal scale without applying TASK021 decimal_string, which strips insignificant trailing zeroes.

This correction does not turn Attempt 2 into a pass. All Attempt-2 objects are discarded and non-reusable. No TASK022+ producer, R2 success artifact, success registry extension, commit, or repository mutation occurred.

Attempt 1 remains a separate incident: it disclosed a premature exploratory TASK025 invocation. Attempt 2 did not invoke TASK025 and has no sequence violation.

No R118-C retry is started or authorized here. TASK171, production mesh, TASK172 runtime, TASK174, TASK173, TASK175, Ready, and merge remain out of scope.
