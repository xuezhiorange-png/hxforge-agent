# V08-07 — Version integration & release candidate closeout (r1)

| Field | Value |
|-------|-------|
| **TASK_ID** | `V08-07` |
| **TASK_NAME** | `VERSION_INTEGRATION_AND_RELEASE_CANDIDATE_CLOSEOUT` |
| **REPOSITORY** | `xuezhiorange-png/hxforge-agent` |
| **TARGET_VERSION** | `V0.8` release candidate (not tagged until `RELEASE_AUTHORIZED=true`) |

## Scope

Integrate V08-01 through V08-06 artifacts without new feature work. Preserve all V07 Golden and historical failure experiments. Document authorized independent rating kernel architecture; do not claim Task172/173 production pass.

## Supported product statement (RC)

- Single-phase **water–water** shell-and-tube automatic sizing MVP
- Thermal rating authority: `V08-INDEPENDENT-ENGINEERING-RATING-KERNEL-V1`
- Full-path hydraulics + four-port nozzle co-selection on **kernel** outlet states
- **Not** claimed: mechanical strength code compliance, manufacturing design approval, or vendor K-value authority

## Architecture (authorized)

See `docs/decisions/V08_03_INDEPENDENT_RATING_KERNEL_ARCHITECTURE.md` and outlet domain note `docs/decisions/V08_KERNEL_OUTLET_PRESSURE_DOMAIN_V1.md`.

| Layer | Authority | V07 boundary |
|-------|-----------|--------------|
| Live V08 design thermal | Kernel V1 | Task172/173 frozen read-only |
| V08 joint E2E | Kernel + V08-04 hydraulics | No Task173 `RATING_SUCCESS` |
| V07 production gate | Unchanged | Golden regressions required |

## Install & run (local)

```bash
cd /path/to/hxforge-agent
python3 -m pip install -e ".[dev]"   # or project-documented install
export PYTHONPATH=src:.

# V08-06 full acceptance matrix (~2–3 min)
python3 prototypes/v08_thermal_rating/run_v08_06_kernel_version_acceptance.py

# V08-07 integration gate (pytest + manifest + ruff scoped set)
python3 prototypes/v08_thermal_rating/run_v08_07_version_integration_closeout.py

# Web MVP (kernel mode)
python3 prototypes/v08_thermal_rating/web/server.py
# POST with rating_engine=kernel_v1 for authorized kernel path
```

## User workflow

1. **General design input** — `prototypes/v08_general_user_case/` JSON + validation pipeline (V08-01).
2. **Structure generation** — Task168 catalog path (V08-02).
3. **Kernel rating + hydraulics** — runners `run_v08_03_*`, `run_v08_04_*`, `run_v08_05_*` and tests under `tests/prototypes/test_v08_*`.
4. **Top-N report** — `v08_05_qualified_top_n_engineering_report.py` (default prescreen; kernel bridge when configured).
5. **Independent acceptance** — `run_v08_06_kernel_version_acceptance.py`.

Default CLI `v08_autonomous_*` paths may still use hydraulic prescreen unless explicitly bridged to kernel outputs.

## Four charter E2E design cases (kernel joint)

Evidence artifacts (regenerate locally):

| Case | Basis | Typical layout evidence |
|------|-------|-------------------------|
| 250 kW | Fixture `FIXTURE_250` | V08-04 matrix + P1 V08-06 |
| 220 kW | Fixture `FIXTURE_220` | V08-04 matrix + P2 V08-06 |
| 330 kW | Fixture `FIXTURE_330` | R3 shortlist T235/T241 × L5.5/L6.0 |
| P3 independent | `tests/fixtures/v08_user_case_p3_kernel_acceptance_v1.json` | 11/19 kg/s, 275 kW, 44/23 °C (amended from empty-mesh 10/18 per register) |

R0 uses **live** `rate_candidate_engineering_kernel_v1` + `evaluate_kernel_joint_hydraulics`, not historical Task173 replay.

## Engineering input examples

- `tests/fixtures/v08_user_case_p3_kernel_acceptance_v1.json`
- V08 general case fixtures under `tests/fixtures/` and `prototypes/v08_general_user_case/examples/` (as present in tree)

## Version change summary (V08 → RC)

- V08-01/02: general input + autonomous structure generation
- V08-03: independent LMTD×F kernel + acceptance contract
- V08-04: kernel-fed full-path hydraulics joint E2E
- V08-05: Top-N engineering report chain
- V08-06: R0/P1–P3/N1/N2/M matrix + V07 golden smoke in runner
- V08-07: integration closeout runner, manifest shard `v08-kernel-rating-integration`, RC documentation

## Known limitations

- Kernel duty iteration may overshoot target Q within contract tolerances
- Outlet pressure domain uses engineering acceptance floor (see domain doc); production 100 kPa checks remain on legacy paths
- N1/N2/N4 Task173 mesh labels are historical only
- Web/API default entry may differ from kernel runners until unified entry is authorized post-RC

## Acceptance evidence paths

- `docs/tasks/evidence/V08-06-P3-kernel-acceptance-spec-r1.md`
- `docs/tasks/evidence/V08-06-independent-acceptance-fixture-register-r1.md`
- Artifacts: `/opt/cursor/artifacts/v08_06_kernel_version_acceptance.json`, `v08_07_version_integration_closeout.json`

## CI note

Full PR-head / merge-ref / **main CI** runs only after `COMMIT_AUTHORIZED=true`. Local closeout runs targeted pytest, scoped ruff, and manifest verify. Prior CI failures on frozen Task173/TRF experiments are **not** equivalent to this kernel integration regression.

## Authorization flags (this document)

`COMMIT_AUTHORIZED=false` · `MERGE_AUTHORIZED=false` · `RELEASE_AUTHORIZED=false`