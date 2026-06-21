# HXForge Product Requirements — v0.1 Baseline Draft

## 1. Product objective

HXForge assists engineers with heat-exchanger technology screening, preliminary sizing, fixed-geometry rating, candidate comparison and traceable report generation.

It is an engineering decision-support tool. It does not replace licensed standards, manufacturer selection software, qualified pressure-vessel design or professional engineering approval.

## 2. Target users

- industrial refrigeration engineers;
- process and thermal engineers;
- equipment engineers;
- technical managers reviewing alternatives;
- software or AI tools executing approved engineering tasks.

## 3. v0.1 equipment coverage

Equipment types are classified into three coverage levels:

### Architecture coverage (no calculation code in v0.1)
- Air cooler
- Microchannel

These families appear in the domain model and screening taxonomy but return `NOT_IMPLEMENTED` for any sizing, rating or optimization workflow.

### Implemented calculation capability (partial)
- Shell-and-tube — screening only; sizing and rating deferred to later milestones
- Plate heat exchanger — screening only; sizing and rating deferred to later milestones

These families participate in technology screening but do not produce validated thermal or hydraulic results.

### Validated calculation capability (target for first vertical slice)
- Double-pipe / hairpin — single-phase liquid-liquid and gas-liquid sizing, rating, optimization and reporting

Only capabilities explicitly marked as validated may return engineering results that carry `verification_level = PRELIMINARY` or above.

## 4. v0.1 supported workflows

### 4.1 Technology screening

Rank suitable exchanger families using service conditions, pressure, temperature, pressure-drop, cleanliness, maintenance, footprint and cost constraints.

### 4.2 Preliminary sizing

Generate manufacturable candidates for supported single-phase services and evaluate duty, pressure drop, margin and basic cost indicators.

### 4.3 Fixed-geometry rating

Calculate performance of a user-specified geometry for supported models.

### 4.4 Comparison and report

Compare candidates and generate a traceable report with inputs, assumptions, warnings, provenance and limitations.

## 5. Initial technical scope

The first complete vertical slice is single-phase double-pipe service. It should support liquid-liquid and gas-liquid cases where the approved property backend returns valid single-phase properties.

## 6. Explicit exclusions for the first release

- certified ASME, TEMA, API or other code compliance;
- final pressure-vessel thickness, flange, tubesheet, fatigue or support design;
- automatic procurement approval;
- unvalidated phase-change calculations;
- automatic CFD, FEA or CAD production output;
- proprietary vendor-equivalent selection without licensed data;
- silent use of guessed material, fouling, cost or correlation values.

## 7. Result states

Every calculation result carries two independent fields: `status` and `verification_level`.

### 7.1 Status (execution state)

| Status | Meaning |
|---|---|
| `DRAFT` | Case created, not yet validated |
| `INPUT_VALIDATED` | Inputs pass schema and engineering validation |
| `THERMAL_SERVICE_RESOLVED` | Phase and service type identified |
| `TECHNOLOGIES_SCREENED` | Candidate families ranked |
| `CANDIDATES_GENERATED` | Geometry candidates produced |
| `CANDIDATES_RATED` | Candidates thermally and hydraulically rated |
| `ENGINEERING_CHECKED` | Mechanical, material and risk checks done |
| `COSTED` | Cost estimates attached |
| `VERIFIED` | Benchmark and regression verified |
| `REPORT_READY` | Report packaged |
| `BLOCKED` | Terminal: input, safety, applicability, property or specification failure |
| `NOT_IMPLEMENTED` | Terminal: capability not yet available |
| `NON_CONVERGED` | Terminal: iterative solver failed to converge |

### 7.2 Verification level (result maturity)

| Verification level | Meaning |
|---|---|
| `PRELIMINARY` | Calculation completed; requires engineering review |
| `REVIEW_REQUIRED` | Result exists but assumptions or warnings need approval |
| `VERIFIED` | Passes approved benchmark and review rules |
| `N/A` | Not applicable (status is BLOCKED, NOT_IMPLEMENTED, or NON_CONVERGED) |

The Agent must not advance the status merely to satisfy a user request.

## 8. User-facing outputs

- input summary;
- heat balance;
- technology-screening result;
- selected or supplied geometry;
- thermal performance;
- pressure-drop results;
- assumptions and margins;
- material and cost placeholders or implemented results;
- warnings and blockers;
- formula and property provenance;
- report-ready status.

## 9. Safety and review responsibility

Every report must state the software version, calculation status and limitations. A human engineer remains responsible for accepting assumptions, selecting standards, checking materials and approving procurement or fabrication use.

## 10. Open decisions

Items requiring engineering-owner approval must be logged in `docs/DECISION_LOG.md` and may not be converted into code defaults until approved.
