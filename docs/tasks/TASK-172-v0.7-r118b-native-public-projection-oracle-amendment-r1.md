# TASK172 R118-B Native Public Projection Oracle Amendment R1

Task: TASK172_V0_7_R118B_NATIVE_PUBLIC_PROJECTION_ORACLE_AMENDMENT_AND_R118C_ATTEMPT2_INCIDENT_R1

## Disposition

This append-only amendment changes output-comparison semantics only. The R118-B project-engineering authority remains REVIEWED_AUTHORITY; no engineering input or authority scope changed. R118-C Attempt 2 remains blocked and permanently non-authoritative.

## Predecessor

PR #283 was OPEN_DRAFT at HEAD fb3a5ea5dc32653d55b7b275717d56df9e963af0. Exact-head CI 36288843849 completed successfully: 50 jobs, 45 success, 5 skipped, 0 failed, 0 cancelled; final-gate success.

Shared canonical replay passed for the R118-B receipt, original R118-B extension, first quantization amendment, Attempt-1 incident, and predecessor registry root.

## Native public-output semantics

TASK021 quantizes coordinates at 1e-12 with precision 50 and ROUND_HALF_EVEN, then calls decimal_string, which strips insignificant trailing zeroes. The quantization resolution is fixed; the public lexical scale is not. For limiting lattice index (u=-3, v=-6), pre-projection x=-0.1524 and y=-0.13198227153674844976679141122274747436104176034035 become public strings x=-0.1524 and y=-0.131982271537. The former expected x string -0.152400000000 represented post-quantization Decimal scale, not final public canonical lexical form.

TASK022 reuses TASK021 decimal_string. Reviewed caller lexemes remain shell ID 0.500 and allowances 0.010; exact native output lexemes are 0.5 and 0.01. Pure replay over the 253 TASK021 public positions reproduced the frozen long Decimal bundle, envelope, radial-clearance, and margin expectations exactly.

TASK024 quantizes coordinate-like outputs at 1e-12 and uses scale-preserving canonical_decimal_string. Exact public values therefore include baffle diameter 0.497000000000, baffle-hole diameter 0.020050000000, chord offset 0.120984710000, and four center coordinates with 12 fractional places. Classification fields are canonicalized from their actual Decimal values; the limiting classification hole radius is 0.010025 and its margin is 0.000972561537.

TASK025 numeric members are Decimal and must be compared by exact Decimal equality and the native result/hash projection, not by an invented fixed lexical scale. IDs/hashes use exact string equality; tokens, integers, and ordered sequences use their native type equality. No tolerance is introduced.

The machine-readable oracle matrix is docs/tasks/evidence/TASK-172-r118b-native-public-projection-oracle-matrix-r1.json: 87 gate fields, zero unresolved oracle bindings, zero hand-formatted output oracles.

## Attempt 2 incident

R118-C Attempt 2 stopped at the TASK021 exact-public-projection gate. TASK014 passed in memory; TASK020 was valid; TASK021 was valid with 253 positions. TASK022, TASK024, and TASK025 were not invoked; Run B was not executed. Actual x was -0.1524 versus then-expected -0.152400000000. The Decimal values are equal, but canonical public lexemes differ.

The governed sequence was respected: no downstream producer ran before a gate passed; sequence_violation=false. All in-memory objects were discarded. No success artifact, success registry extension, commit, repository file change, or volatile identity promotion resulted from Attempt 2.

## Governance boundary

This amendment invoked no TASK014/020/021/022/024/025 materialization producer. It used only pure schema parsing, enumeration, coordinate projection, Decimal arithmetic, and canonical helpers.

R118-C R3 was not started or authorized. TASK171, production mesh, TASK172 runtime, TASK174, TASK173, and TASK175 remain unexecuted. READY_AUTHORIZED=false; MERGE_AUTHORIZED=false. The next gate is R118C_R3_CLEAN_TASK014_AND_NATIVE_GEOMETRY_MATERIALIZATION_RETRY.

R118-B original receipt, prior quantization amendment, Attempt-1 incident, and R1–R118B historical payloads remain immutable. Existing duplicate registry keys remain untouched.
