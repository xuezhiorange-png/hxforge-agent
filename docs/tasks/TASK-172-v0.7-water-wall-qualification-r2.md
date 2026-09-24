# TASK172 R2 — water qualification and clean wall-surface review

## 1. Decision, scope and preserved history

```ini
TASK_ID=TASK172_V0_7_WATER_AND_WALL_SURFACE_QUALIFICATION_R2
PREVIOUS_HEAD_SHA=6ca1e2df3114937db149fa8ee1ce2d033cac8da7
ISSUE=276
PR=277
REVIEW_STATUS=PROPOSED_AUTHORITY
SUPPORTED_FLUID_PROFILE_APPROVED=false
WATER_PROFILE_INDEPENDENT_REVIEW_PENDING=true
WALL_SURFACE_NETWORK_INDEPENDENT_REVIEW_PENDING=true
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

This is a bounded documentation/evidence refinement of
[R1](TASK-172-v0.7-entry-authority-closure-r1.md), not production implementation.
The [registry](TASK-172-v0.7-authority-registry-r1.json) appends an `r2_extension`;
all R1 source/proposal/checkpoint records and their hashes remain historical and
unchanged. The registry root hash necessarily changes. A record's status as
VERIFIED_SOURCE or a successful qualification run is **not independent approval**.
No active wall correction, convergence threshold, hydraulic/FIV capability or
Golden reference is added. User authorization is the R2 instruction associated
with [Issue276](https://github.com/xuezhiorange-png/hxforge-agent/issues/276).

The targeted outcome is: water domain and checkpoint packages PROPOSED_COMPLETE;
clean-network derivation PROPOSED_COMPLETE **as a conditional relation with
qualified inputs**, but no executable wall material profile is qualified.
`MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN` remains a specific evidence blocker.
Overall TASK172 entry remains BLOCKED, not restarted or self-approved.

## 2. Water proposal: deliberately narrow fixed envelope

Identity: `V07-T172-WATER-PROPERTY-PROFILE-R2`, version v2.
Domain proof: `V07-T172-WATER-DOMAIN-PROOF-R2`.

No reviewed v0.7 intended operating rectangle was found in the pinned TASK170
registry or TASK172 R1 contract: their production bounds were explicitly UNBOUND.
This new rectangle is a **PROJECT ADMISSION RULE PROPOSAL**, not an IAPWS
recommendation and not permission for the backend's full domain. Its deterministic
selection rule is the smallest closed T/P rectangle containing:

* the independently tabulated stable-liquid SR6-08 Table8 checkpoint,
  298.15 K, 100000 Pa;
* the already pinned native DEF Water probe, 300 K, 101325 Pa,
  `_REF_VERIFY_STATE_POINTS` in `properties/coolprop_provider.py`.

The 300 K EOS program check independently covers this temperature; its
density-specified pressure is **not substituted** for the native probe pressure.
The R3 ID `POINT1MPA` actually describes 0.1 MPa, not 1 MPa; R2 preserves its
historical ID but never interprets the label as a pressure authority.
This gives an intentionally small qualification-first scope (1.85 K and 1325 Pa
wide), not a useful envelope for every future Rating case. A wider industrial
range requires a separately reviewed version; neither the source maxima nor
successful backend calls widen this one. Reviewer may reject this scope as too
narrow without disputing the source proof.

| Bound | Literal SI value | Selection origin |
| --- | --- | --- |
| T_min | 298.15 K | SR6-08 Table8 liquid check |
| T_max | 300 K | Pinned native DEF probe; IAPWS95 Table7 temperature |
| P_min | 100000 Pa | SR6-08 reference pressure |
| P_max | 101325 Pa | Pinned native DEF probe; SR6-08 §2.4 atmospheric pressure |

### 2.1 Whole-rectangle phase/domain proof

This proof uses primary sources; backend phase strings are not evidence of
admission. New source byte hashes are in the registry. Publications remain
outside Git; only attributed metadata, limited check values and derivation are
recorded.

1. **EOS/transport intersection.** IAPWS95 §5 admits stable fluid from the
   melting curve through 1273 K/1000 MPa in this pressure branch. R12-08 Eq9
   and R15-11 Eq14 admit melting-to-1173.15 K for respectively p≤300 MPa and
   p≤100 MPa. Our p is above each release's triple pressure, below both ceilings;
   T is below every applicable upper limit. No extrapolation clause is invoked.
   [EOS](https://iapws.org/technical-guidance/release/IAPWS-95.download),
   [viscosity](https://iapws.org/technical-guidance/release/viscosity.download),
   [conductivity](https://iapws.org/technical-guidance/release/ThCond.download).
2. **Melting/solid exclusion.** R14-08(2011) §3.1 Eq1 has positive a_i,b_i,
   so dp_melt/dT=−(p*/T*) sum(a_i b_i theta^(b_i−1))<0 on ice Ih.
   p*=611.657 Pa at T*=273.16 K; our pressures exceed that endpoint and are
   far below the first high-pressure ice triple pressure, 208.566 MPa (§3.2,
   Table1). Thus T_m(p)<273.16 K throughout our pressure interval, and
   T−T_m(p)>24.99 K. The source's 2% melting-pressure uncertainty (Table2)
   does not make an atmospheric-pressure point reach the normal triple
   endpoint or a high-pressure ice branch. This is a conservative temperature
   separation, not an invented melting tolerance.
   [R14-08](https://iapws.org/documents/release/MeltSub.download).
3. **Saturation exclusion.** SR6-08 §2.3 explicitly locates the stable liquid
   interval at 0.1 MPa between approximately 273.15 and 372.76 K. The proposed
   T range is interior; increasing p to 101325 Pa does not cross the liquid-vapor
   line. Independently, SR1-86(1992) Eq1 provides an auditable pressure bound,
   not a CoolProp-derived oracle. Write F(tau)=sum(a_i tau^b_i),
   tau=1−T/647.096, p_sat=22064000 exp((647.096/T)F). On this T interval,
   bound each positive term at tau_max and each negative term at tau_min.
   Their sum F_upper=−3.99662846866884485...<0. Hence
   p_sat≤22064000 exp((647.096/300)F_upper)<3979 Pa (outward-rounded reporting
   bound). Therefore P−p_sat>96021 Pa for the entire rectangle within this
   source formulation. The nominal Eq1 value at 300 K is about 3536.718 Pa;
   the conservative bound does not assume numerical sampling proves an interior.
   Source equation validity is triple-to-critical (§6). Its §7 uncertainty is
   inherited from the IAPWS Skeleton Tables, **not** converted into a fabricated
   statistical confidence limit here. The pressure separation is a formulation
   bound and the independent SR6 stable-liquid statement supplies the physical
   classification; it is not a claim of zero source uncertainty.
   [SR1-86](https://iapws.org/technical-guidance/release/Supp-sat.download),
   [SR6-08](https://iapws.org/technical-guidance/release/LiquidWater.download).
4. **Critical exclusion.** The nearest temperature to T_c=647.096 K is separated
   by 347.096 K; p_c−P_max=21962675 Pa. The entire rectangle is also at least
   345.91 K below R12-08 Eq13's near-critical temperature interval. No
   `near_critical_margin=UNBOUND` remains in this rectangle's predicate. These
   are derived separations, not a global near-critical classifier or a license
   to suppress enhancement terms. The general backend formulations stay intact.

The companion evidence includes the Decimal calculation used to check the
saturation bound at two arithmetic precisions. Its digits are diagnostics for
this documented inequality, not a TASK172 convergence preset. None of these
calculations implement a runtime domain classifier or alter production physics.

### 2.2 Executable-review admission contract

Before any future property evaluation require all of:

* exact reviewed R2 profile hash (currently proposed, thus production disabled);
* pure ordinary `Water`, no composition override; backend HEOS, version8.0.0,
  git revision `ae81610e7d23efc57f9d051c8e70a4d66e87537f`;
* a qualified build fingerprint and the unchanged native DEF reference baseline;
* finite SI T/P within all four inclusive bounds above;
* stable-single-phase-liquid request, no imposed metastable, saturated, vapor,
  solid, supercritical or two-phase branch.

Envelope endpoints are admitted physical interior states; **phase boundaries
are not envelope endpoints**. No backend phase string repairs an out-of-range
request. The documentary predicate has no property call. Glycol, mixtures,
other HEOS fluids and reference-state mutation remain rejected. Admission has
no epsilon, hidden margin or numerical rounding-to-inside policy.

rho/cp/h/mu/k come from the same qualified HEOS state/profile. Pr=cp*mu/k is a
derived quantity of that snapshot, not a separately sourced property. Retain
IAPWS95 §6, transport §2.5 and AN1 uncertainty distinctions, including absolute h
versus Delta-h. Combined uncertainty remains UNBOUND; no RSS or global backend
percentage is introduced. All general critical terms stay as implemented.

## 3. Actual backend qualification (not heat-exchanger Golden)

Receipt: [dual-runtime evidence](evidence/TASK-172-water-backend-qualification-r2.json).
Identity: `V07-T172-WATER-BACKEND-QUALIFICATION-R2`.
The self-contained one-off runner is embedded as evidence text with a byte hash;
it is not an installed adapter. Extract to a temporary file and run with each
locked environment from this repository to reproduce. Native provider and
canonical code are imported unchanged. Each process has isolated CoolProp state.

Actual runtimes: CPython3.11.15 and3.12.13, macOS arm64, distinct interpreter
executables and extension binaries, same CoolProp8.0.0 source revision. Both
observations bind interpreter SHA256, extension SHA256, platform, native provider
hash, repository HEAD/tree and runner hash. Qualification was performed against
R1 head's unchanged production tree; the final documentation diff proves those
source files did not change. This is **not** final-PR CI evidence or a claim
that every OS/build is qualified. New binary/platform combinations need replay.

| Check | Independent expectation | Acceptance / actual result |
| --- | --- | --- |
| WATER-EOS-T300-RHO996556 | IAPWS95 Table7: p=0.0992418352 MPa | Published digit reproduction PASS on both; low-pressure footnote retained, no tolerance loosened |
| WATER-MU-T298-RHO998 | R12-08 Table4: 889.735100 microPa s | Published digit reproduction PASS; backend term not disabled |
| WATER-K-T298-RHO998 | R15-11 Table4: 607.712868 mW/(m K) | Published digit reproduction PASS; source liquid enhancement condition recorded |
| WATER-LIQUID-T298-P01 | SR6-08 Table8 rho/cp/mu/k and Table3 h=g+Ts | Executed cross-check with signed/relative differences; NOT HEOS exact reproduction PASS |
| WATER-REFERENCE-DEF | IAPWS95 Eq8: h_triple=0.611782 J/kg | Published digit reproduction PASS; native fingerprint unchanged, mutation detected |
| WATER-DOMAIN-NEGATIVE | R2 project predicate + source phase/domain proof | 18 rejection cases PASS on each interpreter |

The proposed program-check rule rounds the **unmodified observation** to the
printed decimal place, nearest/half-even, and compares to the printed number.
The evidence also records the half-quantum interval. This is a versioned project
verification rule tied to source precision, not an IAPWS-prescribed universal
tolerance. No physical uncertainty is used to relax reproduction. The four exact
checks reproduce all printed digits on these builds. Density-specified and
triple-point formulation checks may be outside the production rectangle; they
do not enlarge admission. SR6's approximate formula remains a different model:
its h computed from independent g,s is recorded, but no exact HEOS h/Delta-h
accuracy oracle or combined uncertainty is asserted.

Nine corner/edge/center snapshots exercise both inclusive boundaries and the
interior. These are consistency observations, **not** independent expected
values and not proof by sampling. The analytical/source phase proof is separate.
All properties are finite; no backend substitution or fluid profile approval
is inferred. Negative cases include one binary representable step outside each
T/P bound (test generation, not tolerance), saturation, wrong fluid/composition/
backend/version/revision/profile/reference, metastable, two-phase, vapor, solid,
supercritical and actual reference-fingerprint mutation.

The native DEF fingerprint is `8d37dea32044ee8d` on both builds. The controlled
initialization and fingerprint method are inherited; diagnostic probes of R134a
and R717 are legacy fingerprint components, **not new supported fluids**.
NBP mutation occurs only in the isolated negative-test process and is detected;
restoring DEF is test cleanup, not permission for runtime silent repair.
The complete semantic observations have identical shared canonical hash
`59e659da63e58013c466836e04810b4c484fc7a3c3784bb17128996b2eff170b`.
Binary hashes differ as expected. Cross-runtime equality is observed on these
two builds, not a caller-supplied parity declaration.

## 4. Clean wall-surface network proposal

Identities: `V07-T172-CLEAN-WALL-SURFACE-NETWORK-R2` and
`V07-T172-LOCAL-CYLINDRICAL-MAPPING-R2`.

### 4.1 Source, project interface and limitations

**Source-derived physics:** inherit TASK037's DOE-HDBK-1012/2-92 HT-02,
Eqs2-7/2-8 (pp12–13) and Eq2-10 (p22), reviewed source revision R3_FROZEN.
The [official DOE PDF](https://www.energy.gov/sites/default/files/2026-04/DOE-HDBK-1012-92_VOL2.pdf)
was fetched, hashed and its original equation pages inspected; no new empirical
constant is introduced. It supplies cylindrical conduction and series film/wall
resistance, not a material's temperature domain or active wall correction.

**Project interface rules:** apply only to TASK171's admitted native straight
tube support and explicit area map. No deposit, contact layer or extra interface
resistance exists in this initial profile. Thus the tube fluid-facing boundary
is the metal inner boundary, and the shell fluid-facing boundary is the metal
outer boundary. These are shared physical identities with different state roles,
not two surfaces equated by an unexplained zero resistance. Fouled service is
not admitted; no legacy fouling authority is changed or assigned a default zero.

**Implementation deferred:** no wall-state producer, film evaluation, viscosity
correction, averaging, interpolation, property evaluation or iteration is added.
Given supplied qualified positive films and qualified constant material k, this
is a reviewable governing relation only. No axial-conduction extension, contact
model, variable-k metal model or full Rating is implied.

### 4.2 Nodes, signs, units and exact local equations

For one explicit wall support j, bind native tube d_i,d_o (m), local tube-count
and length/area authority, A_i,j,A_o,j (m²), k (W/(m K)), h_i,h_o (W/(m² K)).
Require d_o>d_i>0, positive areas/films/k, and the same native area ratio
A_o,j/A_i,j=d_o/d_i; sum local areas equals the corresponding authoritative area
in each basis. No Ai=Ao thin-wall simplification is made.

Let T_tb,T_si,T_so,T_sb be tube bulk, inner metal, outer metal, shell bulk (K).
The fluid-facing wall temperatures are respectively T_si and T_so **only in
this clean profile**. q_j>0 means HOT→COLD. Define Q_ts=+q_j when tube is HOT,
and Q_ts=−q_j when shell is HOT. Preserve signed values; never abs(q_j).

```text
R_i,j = 1/(h_i A_i,j)                              [K/W]
R_w,j = d_i ln(d_o/d_i)/(2 k A_i,j)                 [K/W]
      = ln(d_o/d_i)/(2 pi k n_j L_j)
R_o,j = 1/(h_o A_o,j)                              [K/W]
R_sum,j = R_i,j + R_w,j + R_o,j
T_tb - T_sb = Q_ts R_sum,j
T_si = T_tb - Q_ts R_i,j
T_so = T_si - Q_ts R_w,j = T_sb + Q_ts R_o,j
```

The length form is valid only for the same explicitly bound n_j,L_j support;
it must not invent tube count from mesh count. DOE's 2*pi*r*L area and Eq2-8
give the local form by substitution, not by dividing a whole-exchanger result.
All three branch temperature drops equal the same signed Q_ts times their
resistance; their sum telescopes to the bulk difference. Multiplying K/W by W
produces K. For positive passive resistances and Q_ts>0:
T_tb≥T_si≥T_so≥T_sb, strictly for nonzero duty; inequalities reverse for Q_ts<0.
All nodes lie in the bulk-temperature hull. If q_j=0, compatible passive closure
requires equal bulk/surface temperatures; q=0 with unequal supplied bulk
temperatures is an inconsistent input, not a solved state. No numerical
acceptance threshold is inferred from this algebra.

### 4.3 Mesh split and local/global mapping proof

For disjoint sub-supports s of one original support, unchanged diameters/k and
sum(A_i,s)=A_i give C_w,s=1/R_w,s=2k A_i,s/[d_i ln(d_o/d_i)]. Thus
sum(C_w,s)=C_w and the **parallel**, not series, equivalent wall resistance is
unchanged. Equal-area split into N makes each R_w,s=N R_w, never R_w/N.
No equal split is required; positive area fractions sum to one. Outer areas
obey the same native ratio and their own exact accounting.

If films and driving surface temperatures are common, the parallel network
reproduces the original heat rate. If local films/states differ, sum the local
signed heat events: no single uniform-temperature equivalent or arithmetic
average is inferred. Mesh refinement changes approximation resolution, not
physical conduction geometry. It neither creates a baffle/window/end event nor
crosses a native event boundary. TASK174's Bell aggregation remains untouched.

### 4.4 Constant-k qualification: unresolved, not defaulted

Require a material record with material ID/grade, positive constant k, explicit
evaluation basis, reviewed source and a stated temperature domain covering the
entire local bulk/wall hull [298.15,300] K for this proposed water scope.
`CONSTANT_K_WALL_PER_QUALIFIED_MATERIAL_AUTHORITY` is the policy, not a supplied
material. A point evaluation cannot silently authorize an interval.

Pinned TASK037 `TubeWallThermalConductivityAuthority` has evaluation temperature,
context, applicability hash and approval metadata. Its validator verifies
positive scalars and material binding; it does **not** establish a temperature
interval from those fields. The inspected TASK037 contract fixtures and TASK039
demo are project test/example authorities, not independent metal-domain evidence.
The DOE stainless-steel worked example is not a transferable material profile.
No reviewed material/value/domain covering this new hull was established in this
bounded inheritance audit. Consequently:

```ini
LOCAL_CYLINDRICAL_MAPPING_QUALIFIED=true
CONSTANT_K_POLICY_QUALIFIED=false
MATERIAL_CONSTANT_K_TEMPERATURE_DOMAIN=OPEN
WALL_SURFACE_NETWORK_PROPOSED_COMPLETE=true
WALL_EXECUTABLE_MATERIAL_PROFILE_QUALIFIED=false
```

The first and fourth fields mean derivation/conditional review-package
completeness, not executable capability or independent approval. A reviewer can
approve the network structure while leaving material admission blocked. R2 does
not open a broad materials search or assign k from a fixture.

## 5. Focused review matrix and remaining blockers

| Item | R2 evidence state | Independent decision / limitation |
| --- | --- | --- |
| Water rectangle / phase proof | PROPOSED_COMPLETE | Review selected narrow project scope and source mapping |
| Water backend checks | PROPOSED_COMPLETE | Review the two build receipts and printed-digit rule |
| Clean network and local cylinder | PROPOSED_COMPLETE, conditional on qualified films/k | Independent wall-network review; material-domain evidence still missing |
| Constant-k material admission | OPEN | MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN |
| Tube active correction | OPEN, R1 unchanged | TUBE-WALL-CORRECTION-AUTHORITY |
| Shell active correction | OPEN, R1 unchanged | SHELL-WALL-CORRECTION-AUTHORITY |
| Numerical / mesh | PARTIALLY_CLOSED, R1 unchanged | Three R1 numerical qualification/review blockers |

Remaining TASK172 entry blockers:
`WATER-PROFILE-INDEPENDENT-REVIEW`,
`WALL-SURFACE-NETWORK-INDEPENDENT-REVIEW`,
`MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN`,
`TUBE-WALL-CORRECTION-AUTHORITY`, `SHELL-WALL-CORRECTION-AUTHORITY`,
`LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION`,
`NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW`,
`MESH-CONVERGENCE-QUALIFICATION`.

```ini
NUMERICAL_EXECUTABLE_QUALIFICATION_DEFERRED_UNTIL_PROPERTY_AND_ACTIVE_CORRELATION_AUTHORITY_FIXED=true
NUMERICAL_PROFILE_STATUS=PARTIALLY_CLOSED
MESH_CONVERGENCE_PROFILE_STATUS=PARTIALLY_CLOSED
NUMERICAL_TOLERANCES_BOUND=false
MESH_CONVERGENCE_RULE_BOUND=false
SOURCE_CONFLICT_POLICY=FAIL_CLOSED
```

Review checklist: verify R1 hashes unchanged; verify source/checkpoint byte
bindings; replay runner on both real interpreters; distinguish cross-check from
reproduction; reject profile approval by callback/CI; audit clean surface
identity, role swap, units and parallel split proof; do not approve an absent
material profile. Local documentation/evidence validation and unchanged full
regression precede the single review-fix push. Final exact-head CI belongs in the
PR receipt, not a circular self-hash. PR277 remains Draft; all downstream work
and Ready/Merge require separate authorization.
