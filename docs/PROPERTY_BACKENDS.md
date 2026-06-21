# HXForge Property Backends

## v0.1 policy

HXForge uses an injectable `PropertyProvider` contract. CoolProp with the HEOS backend is the approved default for v0.1. Property calculations are deterministic engineering-core operations; an LLM must never invent or interpolate property values.

## Approved Tier-1 fluids

TASK-003 validates these single-phase fluids:

- Water;
- Air;
- R134a;
- R717 (alias: Ammonia).

Other CoolProp fluids and custom mixtures are rejected by default. They require an explicit `allow_unvalidated_fluids=True` opt-in and their results carry `UNVALIDATED` provenance.

## Supported queries

### TP

Inputs are absolute temperature in kelvin and absolute pressure in pascal. The provider returns temperature, pressure, density, constant-pressure heat capacity, dynamic viscosity, thermal conductivity, specific enthalpy, specific entropy and phase classification.

### PH

Inputs are absolute pressure in pascal and specific enthalpy in joule per kilogram. States inside the saturated-liquid/saturated-vapor enthalpy interval are rejected as two-phase.

### Saturation at pressure

The provider returns separate saturated-liquid (`Q=0`) and saturated-vapor (`Q=1`) states. This supports pure and pseudo-pure fluids; mixtures may have different bubble and dew temperatures.

### Saturation at temperature

The provider returns separate saturated-liquid and saturated-vapor states. Mixtures may have different bubble and dew pressures.

## Phase and saturation safety

CoolProp may report ambiguity or errors very close to saturation. HXForge therefore performs an explicit saturation-distance check before a TP query. The default relative tolerance is `1e-6` and is part of the cache key.

The provider never silently converts a two-phase or ambiguous state into a single-phase result:

- TP states close to saturation return `property_near_saturation`;
- PH states near a saturation endpoint return `property_near_saturation`;
- PH states inside the two-phase enthalpy interval return `property_two_phase_state`;
- unavailable saturation states return `property_saturation_unavailable`.

## Structured errors

The public error codes are:

- `property_invalid_fluid`;
- `property_unvalidated_fluid`;
- `property_invalid_input`;
- `property_state_out_of_range`;
- `property_near_saturation`;
- `property_two_phase_state`;
- `property_saturation_unavailable`;
- `property_unsupported_backend`;
- `property_unsupported_query`;
- `property_backend_failure`;
- `property_non_finite_result`.

Errors include context such as fluid identity, query type, inputs and the original backend message.

## Provenance

Every result records:

- backend name;
- CoolProp version;
- CoolProp git revision;
- canonical fluid identifier;
- Tier-1 or unvalidated status;
- query type;
- exact SI inputs;
- cache-policy version.

## Cache design

The cache is provider-instance scoped and bounded. Its key contains:

- backend name, version and git revision;
- canonical fluid identifier and composition;
- query type;
- exact input values;
- near-saturation tolerance;
- unvalidated-fluid policy;
- cache-policy version.

No ambient pressure, reference state, locale or hidden global engineering default is used in the key. Cache statistics and explicit clearing are available through the provider API.

## Scope boundary

This service does not implement heat balances, heat-transfer correlations, pressure-drop correlations, exchanger geometry, materials, costing or mechanical-code checks. PH and saturation support does not imply that downstream two-phase exchanger solvers are implemented.
