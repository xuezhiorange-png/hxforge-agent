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

## 3. v0.1 supported equipment families

- double-pipe / hairpin;
- shell-and-tube preliminary single-phase workflows;
- plate heat exchanger technology screening and later single-phase workflows;
- air cooler architecture boundary;
- microchannel architecture boundary.

Only capabilities explicitly marked implemented may return engineering results.

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

- `VALIDATED_INPUT`: input is complete and internally consistent.
- `PRELIMINARY`: calculation completed but requires engineering review.
- `REVIEW_REQUIRED`: result exists but one or more material assumptions or warnings require approval.
- `BLOCKED`: a safety, applicability, property or specification problem prevents calculation.
- `NOT_IMPLEMENTED`: the requested workflow is outside the implemented capability.
- `VERIFIED`: reserved for results that pass approved benchmark and review rules.

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
