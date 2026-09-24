# TASK172 R3 — independent R2 receipt and bounded material/correction audit

## 1. Decision and immutable predecessor

TASK_ID=TASK172_V0_7_MATERIAL_AND_ACTIVE_WALL_CORRECTION_R3

This documentation-only closeout continues Draft PR277 / Issue276 at
`c3f1d9223e4731c5cc12621603695e0aa57ff770`. Overall entry remains BLOCKED.
The user independently approved the five exact R2 payloads below in the R3
instruction. Codex records that decision; it does not supply independent approval.
The [registry](TASK-172-v0.7-authority-registry-r1.json) adds `r3_extension`.
Original R1/R2 records, evidence bytes and proposal hashes remain unchanged.
Their historical PROPOSED statuses are not overwritten: this receipt is the
effective, scope-limited review overlay. It authorizes no runtime implementation.

| Authority ID | Approved canonical hash | Effective status |
| --- | --- | --- |
| V07-T172-WATER-PROPERTY-PROFILE-R2 | 8407227452b519483fbccbc686d3e8fcb2ca54866a8a8f01114addb5ca5a37de | REVIEWED_AUTHORITY |
| V07-T172-WATER-DOMAIN-PROOF-R2 | 0111a6353000159977ae7271a9f397d280ca88e25ece3714b6d2d5c9bd530d53 | REVIEWED_AUTHORITY |
| V07-T172-WATER-BACKEND-QUALIFICATION-R2 | 4cccb3122a6ae03badd1bc814523338435977c8324333c804fc1c96b8de10884 | REVIEWED_AUTHORITY |
| V07-T172-CLEAN-WALL-SURFACE-NETWORK-R2 | e493999a1a6f8e83140e62ed71755af877a451bb9525f1e0791cddf174150b29 | REVIEWED_AUTHORITY |
| V07-T172-LOCAL-CYLINDRICAL-MAPPING-R2 | 49f902ce096f57381057a6d3631ef4b30355526dae8187112ae04fa703dda63c | REVIEWED_AUTHORITY |

Review origin: user-provided independent R2 review accompanying the R3 task,
not a fabricated GitHub review ID. Scope is PURE_ORDINARY_WATER, HEOS,
CoolProp8.0.0, DEF, stable single-phase liquid, inclusive 298.15–300 K and
100000–101325 Pa. No general-water, glycol, mixture, fouled-wall or variable-k
profile is approved. Clean-network approval is conditional on qualified films
and material. It is not material qualification or active-correction approval.
The [R2 evidence](evidence/TASK-172-water-backend-qualification-r2.json) and
[R2 derivation](TASK-172-v0.7-water-wall-qualification-r2.md) are not rerun or
rederived here. Qualification checks are not exchanger Golden references.

Water domain/phase qualification, backend checkpoint qualification, water
independent review, clean-network independent review and local cylindrical
mapping review are CLOSED_FOR_TASK172_ENTRY. TASK172 entry itself remains false.

## 2. Material identity: missing, not a license to select a metal

MATERIAL_PROFILE=BLOCKED_MISSING_MATERIAL_IDENTITY

Audit at the predecessor revision:

* TASK020 `shell_tube/models.py`, TASK021 `tube_layout/models.py`, TASK022
  `shell_bundle_geometry/models.py` and TASK023 `shell_geometry_catalogs/models.py`
  do not bind a qualified TASK172 tube material grade and temperature domain.
* TASK037 `overall_heat_transfer_resistance/models.py` defines
  `TubeWallMaterialAuthority` and `TubeWallThermalConductivityAuthority`.
  A typed field is not a selected, source-qualified material.
* TASK037 `authority.py::validate_conductivity_authority` checks positive k and
  evaluation temperature, matching material ID and authority metadata. It does
  not establish an interval over which a point value is constant.
* The actual repository constructor in
  `release_demo/v0_4/task039.py::_build_task037_request` binds T039-MAT-001,
  FIXTURE-GRADE, 16 W/(m K) at 300 K, FIXED_RELEASE_DEMO_INPUT. The corresponding
  TASK037 test constructor also uses FIXTURE-GRADE. These are scoped historical
  fixtures, not a physical alloy specification for TASK172. Their validity and
  historical identities remain untouched.

No material is selected and no external material table is substituted. Required
next evidence is the authorized tube grade/specification and its source-bound
conductivity/evaluation basis, followed by justified constant-k treatment across
298.15–300 K. The reviewed passive temperature hull does not supply those data.
`V07-T172-WALL-MATERIAL-CONSTANT-K-R3` is not issued.

## 3. Actual tube base correlation and transfer boundary

Repository source: `tube_side_thermal/nusselt_selector.py`, frozen R6–R7 §§5.2,6;
`single_phase.py::compute_single_phase`. The turbulent base uses its admitted
logarithmic friction relation and Gnielinski Nu; Re 3000–5e6 and Pr 0.5–2000.
Laminar CWT/CHF constants remain a separate branch; transition remains blocked.
These are inherited values, not new R3 coefficients or extended domains.
Neither function accepts wall properties. The absence of an argument alone is
not evidence that an extension is physically invalid or transferable.

The TASK170 source ledger traces Gnielinski (1976), *New Equations for Heat and
Mass Transfer in Turbulent Pipe and Channel Flow*, Int. Chem. Eng. 16(2), 359–368,
and Petukhov (1970). This audit did not acquire the original equation pages and
complete wall-correction domain. The [bibliographic entry](https://cir.nii.ac.jp/crid/1571980075607043456)
returned a browser verification page; search discovery was not equation evidence.
The [Sieder–Tate publisher PDF](https://pubs.acs.org/doi/pdf/10.1021/ie50324a027)
was also unavailable to this audit. SIEDER_TATE_TRANSFER_AUTHORITY=UNAVAILABLE.
No remembered exponent, library default or secondary formula is admitted.

## 4. Bell/source-chain check and bounded result

The [Gonçalves primary copy](https://www.ou.edu/class/che-design/pub-papers/Linear%20method%20for%20the%20design%20of%20shell%20and%20tube%20heat%20exchangers%20using%20the%20Bell-Delaware%20Method%28Goncalves%20et%20al%29-19.pdf)
was checked visually on PDF pages4 and6, against the R1 source hash. Section2.1
Eqs36–39 supply the ideal-bank relation and geometric corrections, not an active
wall-property multiplier. Section2.2 Eq75 has no requested wall ratio; its regime
and friction choices are not identical to native TASK026. Eq77 is a separate
laminar relation, not permission to multiply Eq75. Section2.1 identifies Taborek
as its equation basis. These observations do not prove all Bell literature lacks
such a correction; they establish that this acquired source does not close it.

TASK166 `authority.py::SOURCE_ROLE_BY_ID` limits Bell1963 to method origin,
Gonçalves to primary equations, Jamil TableA.1 to a/b parameters, and Saif/Tariq
Eq21 to Js. `heat_transfer.py` preserves those roles. None is an approved active
wall-property supplement. Complete Bell1963/Taborek correction pages with domain
and transfer evidence were not obtained; bibliographic lineage is not numerical
authority. The existing Martin/Gnielinski crossflow candidate is not promoted.

| Required extension field | Tube | Shell |
| --- | --- | --- |
| Exact base binding | Native TASK026 Gnielinski/laminar selector | Native TASK166 source-definition V1 |
| Active equation/coefficient/exponent | NOT_QUALIFIED | NOT_QUALIFIED |
| Bulk and fluid-facing wall evaluation rule | NOT_QUALIFIED | NOT_QUALIFIED |
| Property ratio and ratio domain | NOT_QUALIFIED | NOT_QUALIFIED |
| Heating/cooling branch | NOT_QUALIFIED | NOT_QUALIFIED |
| Extension Re/Pr limits | NOT_QUALIFIED; base range is not extension authority | NOT_QUALIFIED |
| Geometry/roughness/developing limitations | NOT_QUALIFIED | NOT_QUALIFIED |
| Combination and transfer rule | NOT_QUALIFIED | NOT_QUALIFIED |
| Decision | OPEN_NO_TRANSFERABLE_AUTHORITY | OPEN_NO_TRANSFERABLE_AUTHORITY |

The exact missing evidence is a lawfully reviewable primary equation plus its
complete domain and explicit compatibility with each native base. No new R3
correction identity is issued. Existing R1 proposal IDs remain historical OPEN
specifications. Factor1 and narrow-water omission are explicitly rejected.
No new equation is transcribed, so no fabricated unit/sign audit is reported;
existing R2 signed network and TASK026/TASK166 equations are unchanged.

## 5. Effective blockers and verification boundary

1. MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN
2. TUBE-WALL-CORRECTION-AUTHORITY
3. SHELL-WALL-CORRECTION-AUTHORITY
4. LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION
5. NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW
6. MESH-CONVERGENCE-QUALIFICATION

The last three are deliberately not researched. Numerical and mesh profiles
remain PARTIALLY_CLOSED; tolerances and mesh convergence rules remain unbound.
SOURCE_CONFLICT_POLICY=FAIL_CLOSED. This is a completed bounded audit, not an
exhaustive literature search or authority closure. New research findings are
not self-approved. TASK172/174/173/175 implementation is not started.

Change allowlist: this document and the registry's appended R3 extension/root
hash only. All preceding records and all production, tests, dependencies and
locks are preserved. Local JSON/hash/identity/link/diff checks and the full local
regression precede any push. Exact-final-head CI evidence is recorded in PR277's
receipt after execution; green CI does not close any engineering blocker.

READY_AUTHORIZED=false; MERGE_AUTHORIZED=false; NO_STEP_IMPLIES_THE_NEXT=true.
