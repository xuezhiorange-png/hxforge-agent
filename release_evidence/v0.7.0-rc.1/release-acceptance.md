# v0.7.0-rc.1 Release Acceptance (local pre-PR)

- release_version: `0.7.0rc1`
- pep440_tag: `0.7.0rc1`
- git_tag: `v0.7.0-rc.1`
- integration_baseline_main_sha: `894498f1ebfd3869c3a1e8060512720338aee023`
- v07_acceptance_content_sha: `6f260196c19996b02ac256a468ec6f6e724f6e14`

## Checklist (release branch local run)

| Gate | Status |
|------|--------|
| `T070_META_001_PYPROJECT_VERSION_0_7_0RC1` | PASS |
| `T070_META_002_UV_LOCK_ALIGNMENT` | PASS |
| `T070_META_003_WHEEL_INSTALL_VERSION` | PASS (`0.7.0rc1`) |
| Ruff check / format | PASS |
| Golden double-pipe | PASS |
| R11 constraint-aware sizing | PASS |
| V07 delivery unit tests | PASS |
| V07 acceptance CLI (REPLAY fixture; not live recompute) | PASS (`FIXTURE_REPLAY_ONLY_NOT_LIVE_ACCEPTANCE`) |
| Wheel / sdist build | PASS |

## Artifact checksums (build @ release branch)

| Artifact | SHA-256 |
|----------|---------|
| `heat_exchanger_design_agent-0.7.0rc1-py3-none-any.whl` | `6c701e1bc4beaae56443582bc2b5b696f9fff1deff170496f1a819791a937e4d` |
| `heat_exchanger_design_agent-0.7.0rc1.tar.gz` | `f82327ab1e4842aebc1d43a38dabcff6daf17cf0e2271cf340375b39c84ec112` |

## Boundary

- Experimental V07 auto-design only; not manufacturing approval.
- Frozen acceptance JSON fixtures unchanged (no golden drift).
- PyPI publish: **not performed**.
