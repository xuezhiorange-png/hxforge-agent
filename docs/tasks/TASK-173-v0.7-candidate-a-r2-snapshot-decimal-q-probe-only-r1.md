# Candidate A R2 snapshot Decimal-q probe-only recovery R1

## Disposition

`NOT_FOUND_IN_BOUNDED_PROBES`. The original Candidate A n=32/support:2 state was rehydrated from the preserved R2 execution artifacts and its frozen endpoint identities replayed. No full n=32 reconstruction, Candidate Full Rating, or public Sizing was run. Sixty-five bounded Decimal-q probes each returned native `Task172LocalResult` with `VALIDATED`, but none met the unchanged ordinary point-root condition `abs(F(q)) <= 1e-6 W`. This finite search does not establish that a root is mathematically absent.

The evidence also exposes a cross-run identity discrepancy that must remain visible: the saved R2 RIGHT Task172 request projection/hash and provider PH input signature exactly match the first R3 probe, but their Task172 result projections differ in three numeric output fields (plus the derived hash and ID). All 65 R3 probes are internally stable for their repeated identical request. The evidence does not establish the cause of the R2-to-R3 numeric difference; it must be investigated before relying on cross-run Task172 result identity.

## Frozen inputs and provenance

| Item | Identity |
|---|---|
| Required/start/execution HEAD | `bfe4566229e7f70b234f6d1dcf9874cea4b1068f` |
| Runtime source HEAD / tree | `21386a88f8290538172e9389ed46f50c3697a426` / `ce61a818b82f908729d2bdf4553cc27012354952` |
| Candidate A ID / hash | `adeab5b1-a339-5eb3-aa66-011ffe49bac0` / `f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767` |
| Candidate Rating request hash | `1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7` |
| Completion request hash | `5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae` |
| TASK168 candidate-space hash | `aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea` |
| R2A authority hash | `25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e` |
| Failed physical support | `urn:hxforge:task171:candidate:f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767:support:2` |

The R2 originals were verified read-only before probing:

| Original R2 artifact | Bytes | SHA-256 |
|---|---:|---|
| execution JSON | 471,057,121 | `59e4e8218f61551ae00421ebcc88cf4ea8870cadd5bbca22420caa9c8930c6fe` |
| checkpoint JSON | 471,036,749 | `87f0391c4ae26008a6bfe93c6e7a1f1657e1925658550dbd0ca55da96e9f138f` |
| append-only trace | 311,208,673 | `e8c719c48842ecb5369a63a375c5004af81152c260c07dbc96a218c9113d1618` |

R2 snapshot replay confirmed 144,217 Task172 validations, 27 numerical holes, and 749 target-cell request/result identity records. It also replayed the selected shooting enthalpy and the target cell's upstream state, support, topology, wall-interface, endpoint request/result, and provider-snapshot identities. The preflight's twelve checks passed, including native JSON request/valid-result/blocked-result rehydration, non-empty valid/blocked Decimal-probe replay fixtures, `ReferencePlanePair` restoration, fail-closed unknown type handling, and frozen endpoint identities. The original R2 files were not modified or copied into this R3 execution directory.

## Frozen endpoint and target-cell identities

| Field | Saved LEFT | Saved RIGHT |
|---|---|---|
| binary64 q | `268.4228547695099 W` | `268.42285476950997 W` |
| Task172 request hash | `4fa675e1a36bd49c67957d2ed0a9dbef808529ffef7f2bdc6b51153da421c754` | `b2472ec62e4a9e53517cdb5cc3a3f6c8d70106cd2cf34663ed2191bdaa9ce072` |
| Task172 result hash | `748819390174c8a2fa88f980b5073366817cce9d158c8bf9c56c52dd66e07ee9` | `ea8869a56cdd300ba42631aa967958aa01daa7e462ed7e5134b10d3d19893573` |
| saved F(q) | `-0.0000053178744 W` | `+0.00001519025227 W` |

Other R2 cell bindings replayed from the stored source include mesh `n=32`, subdivision/support index `21`, outer iteration `24`, tube-cell ID `urn:hxforge:task173:candidate-cell:tube:e9548de1732d080e5843b5f1c8ef85bd85e73efd593ed68cdbfe21b75deb2b07`, shell-cell ID `urn:hxforge:task173:candidate-cell:shell:42c2126675fde297b6f4474e16add0f8200d308d1ce2b600c0ca620a69b02fae`, and wall-interface ID `urn:hxforge:task173:candidate-wall-interface:a22cf4ea8e56f7eeb5f05bd1e118fc78574b639aac96e687642841b8a242f519`. Selected shooting enthalpy was `107518.9165931962933844840526580810546875 J/kg`. Provider identity was CoolProp `8.0.0`, revision `ae81610e7d23efc57f9d051c8e70a4d66e87537f`, `HEOS::Water`, reference state `DEF`, fingerprint `8d37dea32044ee8d`.

## Bounded Decimal-q probe outcome

The exact q endpoints were constructed with `Decimal.from_float`; Decimal q remained in the enthalpy propagation and F calculation. Provider calls retained the original binary64 PH interface, and Task172 used the native solver, acceptance criteria, and result contract. There were 64 uniform intervals/65 unique probes, no adaptive-bisection phase, and 65 native Task172 validations total (67 accounting units including the two saved-endpoint identity replay units), below the 140-validation cap.

* All 65 probes were `VALIDATED` and had ordinary tolerance decision `false`.
* `MIN_ABS_F_W=0.00001519025221096600773744285106658935546875`, at q `268.42285476950991096600773744285106658935546875`.
* The probe grid's largest absolute F was `0.00001519025226780942659825086593627929687500 W`; the probes remained positive and did not bracket a root.
* All probes had one provider PH input signature and one Task172 request hash (`b2472ec62e4a9e53517cdb5cc3a3f6c8d70106cd2cf34663ed2191bdaa9ce072`). All R3 probe Task172 results were `VALIDATED` with result hash `7e0512079ac5f28765f5685ff9ba761d56e0db277698b25ae6c26dc9984b8acc`.
* `PROVIDER_PLATEAU_CLASSIFICATION=SINGLE_PH_INPUT_SIGNATURE_ACROSS_BOUNDED_GRID`. This describes the sampled q grid only; it is not a global continuity or plateau proof.
* `TASK172_RESULT_DISCONTINUITY_CLASSIFICATION=NO_TASK172_RESULT_DISCONTINUITY_OBSERVED_IN_BOUNDED_PROBES`, with the separate cross-run discrepancy below.

The conversion convention mattered. At the LEFT endpoint, `Decimal.from_float(268.4228547695099)` is `268.42285476950991096600773744285106658935546875`, whereas the historical `Decimal(str(float_q))` is `268.4228547695099`; their difference is `1.096600773744285106658935546875E-14`. The Decimal-from-float evaluation mapped to the sampled RIGHT-side provider signature (`tube_midpoint_h=0x1.a80b3f77bb4a0p+16`), while the saved historical LEFT endpoint had `tube_midpoint_h=0x1.a80b3f77bb4a1p+16`. The other three provider PH coordinate hex values matched. This was recorded as an actual representation/provider-input difference, not hidden or treated as evidence that the physical endpoint identities were interchangeable.

The four-coordinate R3 probe signature, in `(tube_downstream_h, shell_next_face_h, tube_midpoint_h, shell_midpoint_h)` order, was `(0x1.a800104a63b6cp+16, 0x1.9a5c6a3c39df8p+16, 0x1.a80b3f77bb4a0p+16, 0x1.9a6320243b37dp+16)`. The historical LEFT signature differs only at the third value, which is `0x1.a80b3f77bb4a1p+16`.

## Cross-run Task172 result identity discrepancy

The independent R3 replay compared the saved R2 RIGHT native request/result preimage with the first R3 probe:

* request projection and request hash are exactly equal (`b2472ec62e4a9e53517cdb5cc3a3f6c8d70106cd2cf34663ed2191bdaa9ce072`);
* provider PH input signature is exactly equal;
* both native results are `VALIDATED`;
* result projection is not equal: the differing keys are `shell_htc_w_m2_k`, `shell_j_mu`, `tube_htc_w_m2_k`, and their derived `result_hash` / `result_id`.

The saved R2-to-R3 values make the numeric scope explicit:

| Result field | Saved R2 RIGHT | R3 repeated-request probe |
|---|---|---|
| `tube_htc_w_m2_k` | `1284.409189857944244339715589` | `1284.40918985794424433971558902184991434893026809460361181916021395943959445284221102690192` |
| `shell_htc_w_m2_k` | `1433.396604198664029577749721` | `1433.396604198664029577749720822386205347310097630323602491665904883062142563471379577699277529535260` |
| `shell_j_mu` | `1.0010497254643006322937466456526065865480095666270264713648517124895580298512252` | `1.0010497254643006322937466457144755173085672206745961636619929392816714419687746` |

Thus `WITHIN_R3_DETERMINISTIC_REQUEST_RESULT_REPLAY=PASS`, but `CROSS_R2_TO_R3_DETERMINISTIC_RESULT_IDENTITY=FAIL`. The cause is not established by this probe task. It is not valid to call the R2-to-R3 output identity replay a pass or to infer provider PH variation: the recorded provider signature is the same. A separate environment/decimal-context/numerical reproducibility investigation is needed before using cross-run Task172 result hashes as interchangeable.

## Replayable artifacts

| R3 artifact | Bytes | SHA-256 / canonical identity |
|---|---:|---|
| probe-only runner (`...r1.py`) | 78,436 | SHA-256 `266a274f5528733cac2279ceacfc1b7b1dd71af00fcc380055f77a8f708f92ef` |
| standalone replay runner (`...r1-replay.py`) | 12,973 | SHA-256 `c9eacaec954249daddaad07b125ca1bc89ec352b7c997f195d8b13e81c637b79` |
| preflight receipt (`...preflight-r3.json`) | 1,832,241 | raw SHA-256 `40ce7915d950be3d036d9f7c4a44c162046dc8cd52fa42118accd741f1134cde`; canonical hash `61b90171fe32902244421b2cb36a42ccedec55f1a8c66467974b2be05f12b92a` |
| probe execution receipt (`...r1.json`) | 15,785,230 | raw SHA-256 `1c325d57ddbd30282851d84a87aac358beae38fb146989d1d10c62119ebde8ac`; canonical hash `1e6b545eed5080b15b70143d33dc5f2fdd1e940e2d1298aab70bc6da6f441538` |
| R3 checkpoint | 300,630 | SHA-256 `4a58fd20b67ae3b153eb68c94dff6eb9f57e69bff1bb288f8187e923f4ddfdb9` |
| R3 append-only trace (912 events) | 18,810,685 | SHA-256 `a7b06777c05c73fc4be8cef053709356bed3b775c3c4dc53763c3959a4974ce4` |
| standalone replay receipt (`...replay-r2.json`) | 6,766 | raw SHA-256 `a6cc2da4c2451c4e7826074a355e5253c3cce92d5ea663f4e0bcb642d52437a2`; canonical hash `47d8fc754131323cc63912a93b1bf1da3db8c593c5a6b007ecc56791214fcd06` |

The final standalone replay revalidated the frozen completion request, raw R2 receipt hashes, all 749 target identities, original endpoints, all 65 probe request/result hashes, provider snapshot hashes, and R3 checkpoint/trace identity. It explicitly records the cross-run result discrepancy rather than conflating it with within-R3 stability.

Reproduction of the evidence-only checks:

```bash
uv run --locked --no-sync python docs/tasks/evidence/TASK-173-v0.7-candidate-a-r2-snapshot-decimal-q-probe-only-r1-replay.py
```

No probe or solver call is made by this replay. It reads the preserved R2 originals at their recorded repository paths; those large historical files are deliberately not copied, rewritten, or included in this evidence commit.

## Scope and next action

`PRODUCTION_CODE_CHANGED=false`; `TASK172_CONTRACT_CHANGED=false`; `R2A_AUTHORITY_CHANGED=false`; `NUMERICAL_TOLERANCE_CHANGED=false`; `CANDIDATE_SPACE_CHANGED=false`; `FROZEN_COMPLETION_REQUEST_CHANGED=false`; `FULL_N32_RECONSTRUCTION_EXECUTED=false`; `PUBLIC_FULL_RATING_REEXECUTED=false`; `PUBLIC_SIZING_REEXECUTED=false`; `TASK175_EXECUTED=false`.

`PROPOSED_NEXT_PRODUCTION_ACTION=NONE_PENDING_OWNER_DIRECTION`. Preserve the R2/R3 receipts and first investigate why an identical Task172 request/provider signature yields slightly different high-precision HTC/Jmu output across runs. No production Decimal-q implementation is recommended from this probe alone. `NEW_NUMERICAL_AUTHORITY_REQUIRED=NOT_ESTABLISHED`; this evidence neither changes nor expands R2A authority. Do not infer mathematical root nonexistence from the bounded search.

PR #283 remains OPEN/Draft. `READY_AUTHORIZED=false`; `MERGE_AUTHORIZED=false`; `NEXT_GATE=OWNER_DIRECTION_REQUIRED_AFTER_R2_SNAPSHOT_DECIMAL_Q_PROBE`; `NEXT_GATE_EXECUTED=false`; `STOP=true`.
