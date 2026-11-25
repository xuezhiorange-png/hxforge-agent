# V08-03 — Independent engineering rating kernel (authorized architecture change)

| Field | Value |
|-------|-------|
| **TASK_ID** | `V08-03` |
| **EXECUTION_STAGE** | `INDEPENDENT_ENGINEERING_RATING_KERNEL` |
| **OWNER_ARCHITECTURE_CHANGE_AUTHORIZED** | `true` |
| **KERNEL_AUTHORITY_ID** | `V08-INDEPENDENT-ENGINEERING-RATING-KERNEL-V1` |
| **ACCEPTANCE_CONTRACT** | `V08_KERNEL_RATING_ACCEPTANCE_V1` |

## Authorization

User authorized replacement of the **live design-path thermal rating** for V08 single-phase water–water shell-and-tube automatic sizing with an independent ε-NTU / LMTD–F engineering kernel. V07 production Task172/173, historical Golden, and all frozen experiment routes remain in the repository as **read-only reference**.

## Frozen legacy routes (do not re-run for V08 delivery)

- Task172/173 production shooting and C-ULP mesh sequence (N1/N2/N4 historical only)
- TRF, joint BVP, cache expansion experiments
- Outer enthalpy numerical representation prototype (Task173 patch path)
- Layered shadow acceptance as **production** gate (remains experimental contract)

## New kernel scope

- Fluids: `PURE_ORDINARY_WATER` mapped to CoolProp `Water` at declared evaluation pressure
- Geometry: manufacturable candidates with validated Task166 (Bell–Delaware), Task026 (tube), Task037 (wall/fouling), Task025 (area)
- Thermal model: series resistance network on **outer surface area basis**; **LMTD × TEMA-type F** (function of tube pass count), **not** ideal counterflow ε-NTU for all layouts
- Iteration: scalar **Q** with enthalpy outlet reconstruction and independent enthalpy-difference energy audit (not Q reused as proof)

## Out of scope (this kernel)

- New fluids, phases, or exchanger topologies
- Replacing V07 `validate_candidate_rating` or editing Golden fixtures
- Claiming Task173 `RATING_SUCCESS` / NUMERIC_VALID mesh labels

## V08 chain integration

Kernel outlet states feed V08-04 full-path hydraulics (no prescreen outlet reuse). V08-05 may rank on kernel thermal pass + existing hydraulic prescreen until authorized merge.

## Acceptance

See `v08_kernel_rating_acceptance_v1.py` — analytical LMTD check, property roundtrip, negative temperature-cross control; tolerances from contract constants, **not** back-solved from failed Task173 runs.