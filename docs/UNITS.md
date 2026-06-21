# HXForge Unit and Quantity Policy

## Purpose

HXForge accepts unit-bearing quantities at public boundaries and converts them to SI before deterministic calculations. Bare engineering numbers are not accepted unless a field is explicitly documented as dimensionless.

## Typed quantities

Public schemas use dimension-specific Pydantic models rather than a generic unchecked `{value, unit}` object.

| Type | SI unit | Typical accepted units |
|---|---|---|
| `MassFlow` | kg/s | kg/s, kg/h, g/s, lb/s, lb/h |
| `VolumeFlow` | m³/s | m³/s, m³/h, L/s, L/min, cfm, gpm |
| `AbsoluteTemperature` | K | K, °C, °F, °R |
| `TemperatureDifference` | K | K, delta_degC, delta_degF, delta_degR |
| `AbsolutePressure` | Pa | Pa, kPa, MPa, bar(a), psia, atm |
| `PressureDifference` | Pa | Pa, kPa, MPa, bar, psi and explicit delta aliases |
| `Power` | W | W, kW, MW, Btu/h, refrigeration ton |
| `Area` | m² | m², cm², mm², ft², in² |
| `Length` | m | m, cm, mm, µm, ft, in |
| `Velocity` | m/s | m/s, m/min, ft/s, ft/min |
| `FoulingResistance` | m²·K/W | m²·K/W, h·ft²·Δ°F/Btu |
| `SpecificEnthalpy` | J/kg | J/kg, kJ/kg, MJ/kg, Btu/lb |
| `Dimensionless` | 1 | dimensionless, fraction, percent |

The allowlist is intentionally finite. Pint may understand many additional units, but HXForge rejects units that are not explicitly approved for a quantity kind.

## Absolute temperature and temperature difference

Absolute temperatures and temperature differences are separate types.

- `AbsoluteTemperature(value=0, unit="degC")` converts to 273.15 K.
- `TemperatureDifference(value=10, unit="delta_degC")` converts to 10 K.
- Plain `degC` or `degF` is rejected for `TemperatureDifference`; an explicit delta unit is required.

This prevents offset errors in LMTD, approach-temperature and convergence calculations.

## Absolute pressure and pressure difference

Pressure values use separate public types even though both reduce to pascals dimensionally.

- `AbsolutePressure` accepts aliases such as `bar(a)` and `psia`.
- `PressureDifference` represents losses or allowable drops and accepts `kPa`, `bar`, `psi` and explicit delta aliases.
- Gauge pressure is not converted automatically because it requires an explicit atmospheric reference.

## Canonicalization

Input aliases are canonicalized before serialization and hashing. Examples:

- `°C` → `degC`
- `bar(a)` → `bar` within an `AbsolutePressure` object
- `kPa(d)` → `kPa` within a `PressureDifference` object
- `m²·K/W` → `m^2*K/W`

The quantity type preserves engineering semantics after the unit string is canonicalized.

## SI boundary

`quantity.to_si()` returns the same typed quantity in its canonical SI unit. `quantity.si_value` returns its SI magnitude for internal solver use. Display conversion uses `quantity.to(target_unit)`.

The legacy helper `to_si(quantity, target_unit=None)` remains available for existing internal code, but it requires a typed quantity and validates the requested target unit against the same quantity kind.

## Errors

Validation errors use stable structured codes, including:

- `quantity_kind_required`
- `quantity_non_finite_value`
- `quantity_empty_unit`
- `quantity_unit_not_allowed`
- `quantity_undefined_unit`
- `quantity_dimension_mismatch`
- `quantity_conversion_failed`

Errors include context such as quantity kind, received unit and allowed units. They can be serialized by Pydantic/FastAPI without parsing human-readable messages.

## Engineering defaults

Unit conversion does not introduce engineering defaults. Fouling resistance, area margin, corrosion allowance and similar quantities must be explicitly supplied or resolved by a separately approved rule/catalog source.
