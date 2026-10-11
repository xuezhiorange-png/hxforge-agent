# V07_TASK172_CONSTITUTIVE_ACCELERATOR_POC_R1

Non-authoritative experiment: memoize duplicate `_eval_trial` evaluations inside the
existing production `task172_local_runtime._solve` TRF/Dogbox path.

Production Task172 / Task173 code is **not** modified.

## Run

```bash
.venv/bin/python prototypes/v07_task172_constitutive_accelerator_poc_r1/benchmark.py \
  --output docs/tasks/evidence/V07-TASK172-constitutive-accelerator-poc-r1-<UTC>.json
```

Budget: harvest ≤25s, total benchmark ≤10 minutes, per-case timing repeats=2 on reference
fixtures plus up to three harvested Candidate B local requests.

## Tests

```bash
.venv/bin/pytest prototypes/v07_task172_constitutive_accelerator_poc_r1/test_accelerator_poc.py -q
```
