# TASK-025 v0.6 Construction-Family Applicability Correction

## Purpose

This narrow correction removes a stale fixed-tubesheet-only admission rule from
the TASK-025 tube-side hydraulic scheduler. The v0.6 configuration and layout
authorities already validate the selected construction family before TASK-025
is invoked.

## Frozen applicability

TASK-025 accepts the following construction-family values at its configuration
and layout admission stages:

- `FIXED_TUBESHEET`
- `U_TUBE`
- `FLOATING_HEAD`

The existing TASK-025 constraints remain unchanged, including shell pass count,
tube pass count, authority mode, identity binding, upstream blocker handling,
and all later hydraulic participation checks.

TASK-021 remains the authority for U-tube pairing. TASK-025 does not infer or
construct a pairing plan, calculate a U-bend radius, or make a mechanical
fabrication or code-compliance determination. TASK-025 consumes the already
validated TASK-020/TASK-021 result path and runs its existing tube-side
hydraulic stages.

## Change boundary

```text
TASK025_FORMULA_CHANGE=false
TASK025_GEOMETRY_EQUATIONS_CHANGED=false
TASK025_APPLICABILITY_CONTRACT_CHANGED=true
TASK025_SUPPORTED_FAMILY_SET_CHANGED=true
TASK025_AUTHORITY_APPLICABILITY_RULE_CHANGED=true
CHANGE_SCOPE=U_TUBE_AND_FLOATING_HEAD_APPLICABILITY_ONLY
UTUBE_PAIRING_CONTRACT_CHANGED=false
UTUBE_PAIRING_INFERENCE_ADDED=false
UTUBE_BEND_GEOMETRY_MODEL_ADDED=false
FLOATING_HEAD_MECHANICAL_MODEL_ADDED=false
PULL_CLEARANCE_MODEL_ADDED=false
FORMULA_CHANGE=false
TOLERANCE_CHANGE=false
IDENTITY_CONTRACT_CHANGED=false
```

## Evidence

The correction is required by the TASK-169 Golden gate trace for G03, which
reaches TASK-025 with matching TASK-020 and TASK-021 identities and is blocked
only by the historical fixed-tubesheet allowlist:

- TASK-165 authority: Issue #253
- TASK-169 authority: Issue #265
- TASK-169 Golden gate: PR #266
- G03 blocker evidence: `BL_013_INVALID_TASK020_CONFIGURATION` and
  `BL_014_INVALID_TASK021_LAYOUT` on `construction_family`

This document does not authorize TASK-169, Golden approval, Ready, or Merge.
