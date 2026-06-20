# GitHub Milestones and Initial Issues

## Milestone 0 — Requirements freeze

1. Define terminology and unit dictionary.
2. Define supported fluids and property backends.
3. Define standard/rule-set matrix.
4. Collect 20 benchmark cases.
5. Approve validation tolerances.
6. Approve product disclaimer and review workflow.

## Milestone 1 — Foundation

1. Implement unit parser and SI normalization.
2. Implement immutable design-case revisions.
3. Implement property-provider protocol and CoolProp adapter.
4. Implement correlation registry.
5. Implement calculation provenance graph.
6. Implement structured warnings and failure modes.
7. Add `/validate` and `/properties` APIs.
8. Add report skeleton.
9. Configure CI and branch protection.
10. Add security and dependency scanning.

## Milestone 2 — Double-pipe vertical slice

1. Implement heat-balance solver.
2. Implement LMTD and epsilon-NTU.
3. Implement circular-tube heat-transfer correlations.
4. Implement annulus heat-transfer correlations.
5. Implement tube and annulus pressure drop.
6. Implement geometry catalog and hairpin enumeration.
7. Implement iterative sizing.
8. Implement rating.
9. Implement materials and weight.
10. Implement C0/C1 cost.
11. Add optimization and comparison.
12. Add 3 golden cases and validation report.

## Definition of Done for every calculation issue

- Formula has a registry ID and bibliographic source.
- Applicability envelope is encoded.
- Units are tested.
- Nominal, boundary and failure tests exist.
- Numerical tolerance is documented.
- Warnings are returned for extrapolation.
- Provenance is serialized.
- Documentation and changelog are updated.
