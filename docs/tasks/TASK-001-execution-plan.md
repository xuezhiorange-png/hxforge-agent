# TASK-001 Execution Plan — Engineering Baseline

## Purpose

Convert the high-level HXForge concept into an approved engineering baseline that later coding tasks can implement without inventing scope, terminology, defaults or compliance claims.

## Subtasks

### TASK-001A — Product scope and release boundary

Deliver `docs/PRODUCT_REQUIREMENTS.md` with:

- target users and use scenarios;
- supported exchanger families;
- v0.1 supported workflows;
- explicit exclusions;
- preliminary / review-required / blocked result states;
- expected report outputs;
- human review responsibilities.

### TASK-001B — Engineering glossary

Deliver `docs/ENGINEERING_GLOSSARY.md` with controlled definitions for:

- sizing, rating and screening;
- operating, design and test conditions;
- duty, approach temperature, temperature cross and LMTD;
- allowable pressure drop and calculated pressure drop;
- fouling resistance and area margin;
- preliminary mechanical design and code compliance;
- candidate, recommendation, warning and blocker.

### TASK-001C — Input/output dictionary

Deliver `docs/INPUT_OUTPUT_DICTIONARY.md` defining every public field:

- business meaning;
- data type;
- unit dimension;
- required/optional/conditional status;
- valid range;
- source;
- default policy;
- validation rule;
- result confidence level.

### TASK-001D — Workflow and state matrix

Deliver `docs/WORKFLOW_MATRIX.md` defining:

- minimum input combinations for screening, sizing and rating;
- supported and unsupported service types;
- under-specified and over-specified cases;
- state transitions;
- warning and blocker behavior;
- output availability by workflow.

### TASK-001E — Review and acceptance

Create at least five representative cases and verify that every case can be expressed using the input dictionary without undocumented fields.

## Execution order

1. TASK-001A
2. TASK-001B
3. TASK-001C
4. TASK-001D
5. TASK-001E

TASK-002 must not start until TASK-001A through TASK-001D are reviewed.

## Required example cases

1. Water-to-water single-phase double-pipe sizing.
2. Water-to-water fixed-geometry rating.
3. Gas-to-liquid preliminary shell-and-tube screening.
4. Plate heat exchanger technology screening with sanitation constraints.
5. Unsupported two-phase refrigerant case returning an explicit blocked or not-implemented status.

## Acceptance criteria

- No public term has multiple meanings.
- No required engineering input is hidden in code.
- No numerical default is introduced without an owner and rationale.
- Supported and unsupported scopes are explicit.
- Every workflow has a minimum input set and output set.
- Compliance language cannot be confused with certified pressure-vessel design.
- Five examples pass a documentation-only representation review.

## Coding-tool instruction

This task is documentation and schema design, not solver implementation. Do not add engineering equations, correlations or numerical fallbacks. Record unresolved engineering decisions in `docs/DECISION_LOG.md` and mark them as blockers rather than guessing.
