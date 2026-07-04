# TASK-011 — Frozen Contract Metadata

## Status

```text
TASK-011 design contract: DESIGN FROZEN
TASK-011 implementation: NOT AUTHORIZED
Benchmark cases: NOT IMPLEMENTED
Production code changes: NOT AUTHORIZED
Test changes: NOT AUTHORIZED
CI workflow changes: NOT AUTHORIZED
TASK-012+: NOT AUTHORIZED
```

## Authority

```text
Issue: #36 — TASK-011 — Collect and approve the first 20 benchmark cases
Design PR: #37 — docs(task-011): draft benchmark case governance design
Design PR state: MERGED
Reviewed Head / Frozen Contract Authority SHA: 7cfdb4f0989b6d384533c7a29e9a2156c731bd0f
Design merge commit: bee6b57b8004b6c257ec81738430781fe0b7ee19
Post-merge backlog governance commit: 2e2c703f10e665264467dfdcdd7d4353f61034ec
Latest accepted review: 4628651936 — PASS
```

## Frozen contract file

```text
docs/tasks/TASK-011-benchmark-case-governance.md
```

The frozen contract content is the content of
`docs/tasks/TASK-011-benchmark-case-governance.md` at commit
`7cfdb4f0989b6d384533c7a29e9a2156c731bd0f`.

This metadata file records post-merge authority state without changing
the frozen contract body. The frozen contract body contains historical
pre-freeze labels in its local status block; those labels are superseded
for governance purposes by Issue #36, PR #37, and this metadata record.

## Implementation boundary

No TASK-011 implementation work is authorized by this metadata file.
A later implementation may start only after a separate explicit user
authorization step.

Until then, the following remain forbidden:

- `benchmarks/`
- `benchmarks/cases/`
- `benchmarks/manifests/`
- `tests/benchmark/`
- `src/hexagent/benchmark_cases/`
- production code changes
- test code changes
- CI workflow changes
- TASK-012+
- C4
- pressure-drop
- materials / cost / new solver features
