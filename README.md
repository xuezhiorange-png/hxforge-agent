# Heat Exchanger Design Agent

Engineering-grade scaffold for a heat exchanger design assistant.

## Current state

This repository is a starter architecture. It includes:
- domain schemas;
- property provider abstraction;
- calculation provenance;
- LMTD utility;
- a minimal double-pipe rating example;
- FastAPI endpoints;
- tests and GitHub Actions.

It does **not** yet provide code-compliant pressure-vessel design or production-ready exchanger selection.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn hexagent.api.main:app --reload
```

## Main documentation

- `docs/MASTER_DEVELOPMENT_SPEC.md`
- `docs/ARCHITECTURE.md`
- `AGENTS.md`

## Repository policy

Do not commit copyrighted standards, licensed REFPROP files, confidential vendor catalogs, customer cases, credentials, meshes or large simulation results.
