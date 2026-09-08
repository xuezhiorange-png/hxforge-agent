# TASK-167 — Shell-and-Tube Engineering Screening

Status: implementation contract for the v0.6 TASK-167 primary PR.  This
document is an engineering-screening authority, not a mechanical design or
standards-compliance authority.

## 1. Scope and ownership

TASK-167 implements deterministic preliminary screening for one already
authoritative shell-and-tube configuration.  Its aggregate result is exactly
`PASS`, `WARN`, or `BLOCKED`.  It consumes TASK-020 configuration, the
producer-owned TASK-166 Bell--Delaware result, and the producer-owned TASK-026
tube-side thermal result.  It composes and projects those results; it does
not recalculate Bell--Delaware, tube hydraulics, UA, duty, outlet
temperatures, LMTD, or F-factor.

The screens are tube velocity, shell velocity, optional nozzle velocity,
erosion risk, fouling/cleanability, thermal-expansion risk, construction-family
suitability, and preliminary flow-induced-vibration (FIV) diagnostics.
Detailed mechanical design, tubesheet stress, pressure-vessel design,
fatigue, seismic/wind design, detailed vibration, FEA, CFD, CAD, and
TASK-168/TASK-169 candidate generation or ranking are out of scope.

## 2. Authority boundary

The only standard-specific numeric authority is the existing TASK-012/TASK-020
`APPROVED_RULE_PACK` path.  `INTERNAL_GENERIC` diagnostics have
`standard_claim=false`; a generic `PASS` never means TEMA, API, ISO, or ASME
compliance.  No anonymous velocity, erosion, vibration, or mechanical limit
is embedded in this package.  A diagnostic without a bound authority is a
deterministic `WARN`.

The existing construction vocabulary is reused unchanged:
`FIXED_TUBESHEET`, `U_TUBE`, and `FLOATING_HEAD`.  Existing TASK-033 and
TASK-034 Kern authorities remain separate and are not renamed or modified.

## 3. Public contract

The sole business entry point is:

```python
engineering_screening.validate_request(raw: object) -> Task167ValidationResult
```

The typed request carries exact producer-owned `Task166Result` and
`TubeSideThermalResult` objects, a validated TASK-020 configuration, explicit
screening requirements, a source-bound property snapshot, optional nozzle
geometry authority, and request metadata.  Raw replacement UA, Cdot, inlet
temperature, pressure-drop, or expected-result values are not accepted.

Validation is ordered as raw admission, typed admission, TASK-020 replay,
TASK-166 replay, TASK-026 replay, authority/rule-pack checks, screening, then
canonical identity and provenance.  A later stage cannot convert an earlier
failure into success.  A blocked screen produces no partial success result.

## 4. Source set

The public sources are used only for the role that their accessible evidence
supports:

* Pettigrew and Taylor, *Vibration analysis of shell-and-tube heat
  exchangers*, Part 1, Journal of Fluids and Structures 18 (2003), DOI
  `10.1016/S0889974603001208`, and Part 2, DOI
  `10.1016/S088997460300121X`: method scope and required dimensionless FIV
  diagnostics.  No critical-velocity coefficient is guessed when a complete
  public coefficient authority is not available.
* NIST/Bureau of Standards Circular 486, Eq. 1: source-transparent linear
  thermal expansion diagnostic, available at
  <https://www.govinfo.gov/content/pkg/GOVPUB-C13-be29bf9d79f4605d85ee2b3e8b840df3/pdf/GOVPUB-C13-be29bf9d79f4605d85ee2b3e8b840df3.pdf>.
* Bell & Gossett U-tube engineering documentation for removable-bundle and
  U-bend access characteristics, available at
  <https://www.bellgossett.org/Heat-Exchangers/Shell-and-Tube/U-Tube.html>.
* The Chemical Engineer shell-and-tube overview and the Elsevier
  shell-and-tube overview for construction/maintenance cross-checks:
  <https://www.thechemicalengineer.com/features/getting-started-part-1-shell-and-tube-heat-exchangers/>
  and <https://www.sciencedirect.com/topics/engineering/shell-and-tube-exchangers>.

The Pettigrew/Taylor accessible abstract states the flow-velocity and
mass-damping dimensionless variables; it does not authorize a fabricated
critical-velocity coefficient.  The construction sources support qualitative
screening only.  Source conflicts block the affected screen.

## 5. Screen semantics

Every screen records `screen_id`, status, authority mode, source/rule
identity, diagnostic values, authoritative limits when present, reason code,
standard-claim flag, applicability, and evidence references.

Tube velocity is the accepted TASK-026 `bulk_velocity_m_s`.  Shell bulk and
crossflow velocities are accepted only from the source-bound screening
snapshot because TASK-166's public result does not expose a substitute shell
velocity field.  Nozzle velocity is computed only when authoritative area,
mass flow, and density exist; an optional missing nozzle geometry is a WARN,
not an aggregate blocker.

Erosion has no generic allowable in v1 and therefore remains a diagnostic
WARN.  Cleanability distinguishes fixed-tubesheet shell-side access,
U-tube bend limitations/removable bundle, and broad floating-head
removability.  A declared hard cleaning requirement that the construction
cannot meet is BLOCKED; a fouling tendency without a hard requirement is a
WARN.  Thermal expansion is either a qualitative construction result or a
source-transparent `alpha * length * delta_temperature` diagnostic.  It is
not a stress or code-compliance calculation.  Fixed-tubesheet differential
expansion without an approved allowable remains a WARN.

FIV exposes available crossflow velocity, span, tube OD, pitch, density,
effective mass, reduced velocity, and mass-damping parameter.  Critical
velocity and critical ratio remain absent in this version because the admitted
public source set has no complete coefficient authority.  FIV status is WARN
with `numeric_limit_not_guessed=true`.

Aggregate semantics are deterministic: any required BLOCKED screen gives
`BLOCKED`; otherwise any WARN gives `WARN`; otherwise `PASS`.  Optional
nozzle absence alone never gives BLOCKED.

## 6. Identity and provenance

Decimal diagnostics remain Decimal-only and are serialized lexically without
normalization.  Mapping identity is sorted by UTF-8 key bytes; no clock,
random value, process hash, float representation, `repr`, or arbitrary-object
state is used.  TASK-167 uses task-specific SHA-256 domains and UUIDv5
namespaces, while reusing the repository's framing primitive.

Success identity commits to the configuration, TASK-166 and tube-side
producer identities, source-bound requirements/properties, every screen,
aggregate status, applicability, completeness, warnings, and semantic
provenance inputs.  The final graph is excluded from its own preimage.  The
success graph has source/configuration/producer/screen evidence nodes feeding
`TASK167_CALCULATION_RUN`, which produces `TASK167_RESULT`; it has zero
self-edges and zero cycles.  Typed and raw blocked results have deterministic
identities but no provenance graph.

## 7. Acceptance test matrix

Targeted tests cover exact typed admission, source/rule-pack boundaries,
producer identity replay and tamper rejection, all construction families,
velocity/nozzle/erosion/cleanability/expansion/FIV semantics, aggregate
status, Decimal-context independence, canonical permutation invariance,
raw-depth/node/scalar/Unicode hostile inputs, deterministic blocked/success
identity, and acyclic provenance.  TASK-020, TASK-032, TASK-033, TASK-034,
and TASK-166 regressions remain in their existing tests and are not modified
by TASK-167.

The implementation does not start TASK-168 or TASK-169 and does not expose a
standard-compliance claim.
