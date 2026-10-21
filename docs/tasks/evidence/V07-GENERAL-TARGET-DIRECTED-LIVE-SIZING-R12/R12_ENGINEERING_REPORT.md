# R12 Target-directed sizing — mvp-target-directed-r12

## Search policy

- Selection mode: **MIN_NOMINAL_TUBE_AREA_SEARCH**
- Selection reason: `MIN_NOMINAL_TUBE_AREA_SEARCH_EXCLUDING_BASELINE_GEOMETRIES`
- Task174-ready in space: **4**
- Live n=1 ratings this run: **2**

## R10 frozen baseline (reference only)

- Candidate A nominal area: 73.4356786094391222873825 m²
- Candidate A duty: 38387.018185484473 W

## Live-rated candidates (this run)

- `f288aa61-0725-5942-a4fa-d5e16e1cd706`: L=3.0 m, area proxy 45.424131098622137497350 m², duty 29882.751196130037 W, mesh NUMERIC_VALID, duty constraint SATISFIED, wall 212.775 s, Task172 evals 4079
- `071b9c82-f24a-53dd-b03b-a267f5f8d3c3`: L=3.5 m, area proxy 52.994819615059160413575 m², duty 32561.768761137928 W, mesh NUMERIC_VALID, duty constraint SATISFIED, wall 285.459 s, Task172 evals 5182

## Evaluated-set sizing decision

- Target constraint status: **PRELIMINARY_CONSTRAINT_SATISFIED_IN_EVALUATED_SET**
- Best evaluated candidate: `f288aa61-0725-5942-a4fa-d5e16e1cd706`
- Area reduction vs R10 A: 38.14432989690721649484536082 %
- Hydraulic scope: **HYDRAULIC_REFERENCE_MODEL_PREVIEW**
- Preference among live-rated candidates in this run only; not a global optimum over the full discrete candidate space.

## Not production approved

- full_rating_converged: false
- production_sizing_verified: false
