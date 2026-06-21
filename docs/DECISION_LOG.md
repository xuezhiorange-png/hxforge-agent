# HXForge Engineering Decision Log

This log records product and engineering decisions that affect schemas, defaults, calculations, warnings or compliance language. Coding tools must not convert a proposed item into code behavior until its status is `APPROVED`.

Status values: `PROPOSED`, `APPROVED`, `REJECTED`, `SUPERSEDED`.

| ID | Decision | Status | Owner | Rationale / consequence |
|---|---|---|---|---|
| DEC-001 | The first complete calculation vertical slice is single-phase double-pipe / hairpin service. | PROPOSED | Engineering owner | Limits early validation scope and proves the full input-to-report workflow before adding more exchanger families. |
| DEC-002 | Shell-and-tube and plate exchangers may appear in v0.1 screening before their detailed sizing/rating solvers are complete. | PROPOSED | Engineering owner | Allows technology comparison without falsely claiming validated detailed calculations. |
| DEC-003 | Condensation, evaporation and other two-phase services return `NOT_IMPLEMENTED` until approved correlations and validation cases are merged. | PROPOSED | Engineering owner | Prevents unvalidated refrigerant calculations from being presented as engineering results. |
| DEC-004 | Public engineering inputs never use hidden numerical defaults. Values such as fouling resistance, area margin, roughness, material, cost basis and corrosion allowance must be provided or explicitly selected from an approved rule set. | PROPOSED | Engineering owner | Makes assumptions visible and traceable. |
| DEC-005 | The deterministic calculation core uses SI units; API and reports may convert to user-selected display units. Absolute temperature and temperature difference are separate dimensions. | PROPOSED | Engineering owner | Avoids unit ambiguity and offset-temperature errors. |
| DEC-006 | Result states include `VALIDATED_INPUT`, `PRELIMINARY`, `REVIEW_REQUIRED`, `BLOCKED`, `NOT_IMPLEMENTED` and `VERIFIED`. | PROPOSED | Engineering + product owner | Separates successful computation from engineering approval and implementation availability. |
| DEC-007 | HXForge never claims certified ASME, TEMA, API or statutory compliance from preliminary calculations. | PROPOSED | Engineering owner | Code compliance requires licensed rules, complete inputs, qualified review and applicable legal processes. |
| DEC-008 | Every numerical output must include calculation provenance and structured warnings. | PROPOSED | Engineering + software owner | Supports reproducibility, review and regression control. |
| DEC-009 | Candidate generation is limited to approved, manufacturable catalog geometry; continuous optimization cannot invent arbitrary procurement dimensions. | PROPOSED | Engineering owner | Keeps optimized designs buildable and comparable. |
| DEC-010 | A blocking input, safety, property or applicability error prevents candidate recommendation and report-ready status. | PROPOSED | Engineering owner | Prevents the Agent from forcing a result through an invalid workflow. |

## Approval checklist

Before changing a row to `APPROVED`, record:

- approver name or role;
- approval date;
- affected task IDs and schemas;
- references or enterprise rule source;
- whether existing examples, tests or reports require revision.

## New decision template

```text
ID: DEC-XXX
Decision:
Status: PROPOSED
Owner:
Context:
Options considered:
Decision rationale:
Affected modules and task IDs:
Evidence / references:
Approval record:
```
