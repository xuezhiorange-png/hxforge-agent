# V07_TASK173_NONINTRUSIVE_TELEMETRY_R1

Non-solving telemetry prototype for TASK173 long-run observability.

- **Contract:** `EVENT_CONTRACT.md`
- **Frozen hashes:** `FROZEN_IDENTITY_REFERENCES.md` (Candidate B success `1cecb402…`)
- **Recovery scope:** `LOG_RECOVERY_NOT_CHECKPOINT.md` (not solver resume)
- **Library:** `telemetry.py`
- **Simulator:** `mock_runner.py`
- **Future hooks:** `PRODUCTION_HOOK_INTEGRATION.md`

## Run mock (no Rating/Sizing)

```bash
cd prototypes/v07_task173_nonintrusive_telemetry_r1
python3 mock_runner.py --artifact-dir /opt/cursor/artifacts/task173_telemetry_r1
python3 mock_runner.py --artifact-dir /opt/cursor/artifacts/task173_telemetry_r1_abort --abort-mid-candidate
```

## Tests

```bash
cd /workspace
.venv/bin/pytest prototypes/v07_task173_nonintrusive_telemetry_r1/test_telemetry_prototype.py -q
```

Telemetry is **not** part of engineering canonical hashes.

## Delivery bundle (off-VM)

```bash
chmod +x pack_delivery.sh
./pack_delivery.sh /opt/cursor/artifacts
```

Produces `V07_TASK173_NONINTRUSIVE_TELEMETRY_R1_<timestamp>/` with `MANIFEST.sha256`, `.tar.gz`, and `.tar.gz.sha256`.
