# TASK-001 — Engineering requirements baseline

**Status:** READY  
**Milestone:** M0  
**Priority:** P0  
**Depends on:** TASK-000

## Objective

Freeze the v0.1 engineering scope, terminology, input/output dictionary, assumptions and explicit exclusions before additional solver development.

## In scope

- Supported services, fluid classes and operating modes.
- Sizing versus rating definitions.
- Temperature, pressure, duty and pressure-drop specifications.
- Required user inputs, defaults and forbidden defaults.
- Result confidence levels and engineering review requirements.
- v0.1 exclusions and `NOT_IMPLEMENTED` behavior.

## Expected files

- `docs/PRODUCT_REQUIREMENTS.md`
- `docs/ENGINEERING_GLOSSARY.md`
- `docs/INPUT_OUTPUT_DICTIONARY.md`
- updates to `docs/MASTER_DEVELOPMENT_SPEC.md`

## Acceptance criteria

- [ ] Every v0.1 workflow has a complete minimum input set.
- [ ] Ambiguous terms such as design pressure, operating pressure and allowable pressure drop are defined.
- [ ] Unit ownership and missing-value behavior are explicit.
- [ ] Safety and compliance disclaimers are approved.
- [ ] Engineering and software reviewers approve the baseline.

## Test plan

Create at least five example cases and verify each can be represented without undocumented fields.

## Risks

Premature implementation against ambiguous requirements causes incompatible schemas and invalid assumptions. Do not code around an unresolved definition.
