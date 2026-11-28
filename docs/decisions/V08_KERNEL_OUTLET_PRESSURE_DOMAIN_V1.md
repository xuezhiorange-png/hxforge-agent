# V08 kernel outlet pressure domain (atmospheric service)

| Field | Value |
|-------|-------|
| **Authority** | `V08-KERNEL-JOINT-HYDRAULIC-INTEGRATION-V1` |
| **Applies to** | Experimental kernel joint path only (not V07 production full-path gate) |

## Issue

`engineering_hydraulic_path_physical_consistency._outlet_domain_ok` requires outlet pressure ≥ **100000 Pa**.  
For **101325 Pa** inlet with allowed full-path drop (~1.7 kPa), shell outlet ≈ **99603 Pa** is valid liquid water in CoolProp but fails the legacy floor.

## V08 kernel adjustment

`v08_kernel_outlet_domain_ok` uses:

- Minimum: **50000 Pa** (above water triple-point envelope; documented atmospheric lower bound for single-phase liquid queries)
- Maximum: **10 MPa** (unchanged)
- Phase: liquid single-phase only (same as production)

## Evidence

CoolProp `Water` at 302 K, 99603 Pa → liquid density ~996 kg/m³ (verified in V08-04 integration run).

## Non-expansion

- Does **not** change V07 Golden or production `_outlet_domain_ok`
- Does **not** authorize two-phase or sub-triple-point boiling
- Does **not** relax 1–3 m/s nozzle band or case Δp limits