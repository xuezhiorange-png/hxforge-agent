# TASK173 Provider-Quantization Enclosure Hash Replay Contract Recovery R1

**Result:** `PASS_PROVIDER_QUANTIZATION_ENCLOSURE_HASH_REPLAY_CONTRACT_RECOVERY`

**Reviewed source head:** `0be1d8d596787bf3af57d90676b69cfb22dab454`

**PR:** #283, OPEN / Draft

**Parent authority:** `V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R1`

**Parent authority hash:** `c95b5bf23b15a9c93b6ef47c3ad2043708bef9ae66429116855a4306f8102ab2`

This is a replay-contract recovery only. The enclosure authority candidate and its numerical semantics are unchanged. No production code, tests, Sizing, candidate Rating, or TASK175 work was performed.

## Recovery and replay

The exact external diagnostic runner was recovered at `/tmp/task173_n1_diagnostic_runner.py` and SHA-256 matched `14dbbdb324e38bb1bf5d034f6ccf04637967d629354da763e02248dc04b5adfb`. The exact raw diagnostic log was recovered at `/tmp/task173_provider_quantization_n1_matrix_task166_version_replay.log` and matched `1e0ba509a895595137494df3fba1ee02747455412090b61eedfc34b1346f940d`. The pre-rating capture also matched the SHA recorded in the committed qualification matrix.

The diagnostic runner itself emits qualification records but does not compute the matrix or event hashes. The contemporaneous receipt builder was also recovered at `/tmp/task173_build_enclosure_receipt.py`; its exact bytes hash to `863fbcabbd757db3a1ec87b549fbf08b703c317239f9a814134e42dd71f287e4`. Inspection of that source establishes the original algorithm:

- At its event-hash assignment, the complete event object is passed to `canonical_sha256` before `quantization_enclosure_hash` is inserted. Replay therefore hashes the stored event with that one root field removed.
- The complete `qualification_matrix` object is passed directly to `canonical_sha256`, with no domain prefix or additional projection. The matrix's list of event hashes is included. The declared matrix hash is a sibling field and is not part of the matrix object.
- The authority hash is `canonical_sha256(authority_candidate.projection)`.

The pinned repository helper is `src/hexagent/canonical_json.py` at the reviewed source head (Git blob `8fcbcfdf376b0756766102ce5013defd7e1cbef0`, raw SHA-256 `ef964066780b5c662e553d5c86f5a52f7070c460dfae288993e3a8a156b5a2b6`). It removes `canonical_hash` and `mutable_review_comments` recursively, NFC-normalizes string keys and values, serializes with the locked RFC 8785 implementation (`rfc8785==0.1.4`), and hashes those bytes with SHA-256.

Independent replay from the exact committed evidence produced:

- Authority: `c95b5bf23b15a9c93b6ef47c3ad2043708bef9ae66429116855a4306f8102ab2` — PASS.
- Qualification matrix: `92cb9fa0a65041199f67ebe588b460bcef868c64fdd6044e990f4309b6af8840` — PASS.
- Enclosure events: 8 of 8 hashes — PASS.

The prior reviewer value `acade14b5227cbf6149e2bfbb521a8709b3f2465e1068e4672d759dc6fea8d0c` is reproducible as the SHA-256 of Python's default `json.dumps(matrix, sort_keys=True, separators=(',', ':')).encode()` output. That is not the pinned repository canonical helper. The review packet did not specify that alternative serializer, so this explains the differing value without characterizing the reviewer as wrong.

## Durable replay

Run from the repository root:

```sh
uv run --locked --no-sync python docs/tasks/evidence/TASK-173-v0.7-provider-quantization-enclosure-hash-replay-r1.py
```

The script reads only the committed qualification evidence beside it and the repository canonical-JSON helper. It prints the authority hash, matrix hash, all eight event hashes, and `ALL_REPLAY_PASS=true`. Script SHA-256: `0fb641c78c1358d4af7cc3b1cd99c860652a114ce01e5bea5fac39470fef6196`.

The machine-readable projection and source manifest are in [the evidence receipt](evidence/TASK-173-v0.7-provider-quantization-enclosure-hash-replay-contract-recovery-r1.json).

## Boundaries and next gate

`PARENT_AUTHORITY_HASH_CHANGED=false`; `PRODUCTION_CODE_CHANGED=false`; `TESTS_CHANGED=false`; the dirty parent implementation was not staged or committed. Its tracked patch hash remains `b5408a1e7cf62456cd36e6c3cb95e52d79838103e23ab68139b8b6006de21555`.

The required next gate is `STAGE3_TASK173_CELL_ROOT_PROVIDER_QUANTIZATION_ENCLOSURE_INDEPENDENT_REVIEW_R1_RETRY_AFTER_HASH_CONTRACT_RECOVERY`. It was not executed here. PR remains Draft; Ready and Merge are unauthorized.
