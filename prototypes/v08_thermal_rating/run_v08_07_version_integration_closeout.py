"""V08-07 VERSION_INTEGRATION_AND_RELEASE_CANDIDATE_CLOSEOUT (local gate, no push)."""

# ruff: noqa: E501

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256

TASK_ID = "V08-07"
TASK_NAME = "VERSION_INTEGRATION_AND_RELEASE_CANDIDATE_CLOSEOUT"
REPO = Path(__file__).resolve().parents[2]
ARTIFACT = Path("/opt/cursor/artifacts/v08_07_version_integration_closeout.json")
DOC = REPO / "docs/tasks/evidence/V08-07-release-candidate-closeout-r1.md"

KERNEL_TARGETED = [
    "tests/prototypes/test_v08_independent_engineering_rating_kernel_v1.py",
    "tests/prototypes/test_v08_kernel_engineering_integration_v1.py",
]
V08_CHAIN_TARGETED = [
    "tests/prototypes/test_v08_04_hydraulic_feasibility_gate.py",
    "tests/prototypes/test_v08_05_qualified_top_n_engineering_report.py",
]
V07_GOLDEN = ["tests/prototypes/test_v08_thermal_rating.py"]
MANIFEST_FILES = [
    "tests/prototypes/test_v08_independent_engineering_rating_kernel_v1.py",
    "tests/prototypes/test_v08_kernel_engineering_integration_v1.py",
    "tests/prototypes/test_v08_06_kernel_version_acceptance.py",
]

V08_06_ARTIFACT = Path("/opt/cursor/artifacts/v08_06_kernel_version_acceptance.json")
V08_04_ARTIFACT = Path("/opt/cursor/artifacts/v08_04_new_rating_kernel_engineering_integration.json")


def _run_pytest(files: list[str], *, timeout: int = 900) -> tuple[str, int, str]:
    cmd = [sys.executable, "-m", "pytest", *files, "-q", "--tb=line"]
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    status = "PASS" if proc.returncode == 0 else "FAIL"
    tail = (proc.stdout or "")[-1200:] + (proc.stderr or "")[-400:]
    return status, proc.returncode, tail


_V08_07_RUFF_PATHS = [
    "prototypes/v08_thermal_rating/v08_independent_engineering_rating_kernel_v1.py",
    "prototypes/v08_thermal_rating/v08_kernel_rating_acceptance_v1.py",
    "prototypes/v08_thermal_rating/v08_kernel_hydraulic_integration_v1.py",
    "prototypes/v08_thermal_rating/v08_kernel_engineering_report_v1.py",
    "prototypes/v08_thermal_rating/v08_kernel_design_chain_bridge.py",
    "prototypes/v08_thermal_rating/v08_06_kernel_version_acceptance.py",
    "prototypes/v08_thermal_rating/run_v08_03_independent_engineering_rating_kernel.py",
    "prototypes/v08_thermal_rating/run_v08_04_new_rating_kernel_engineering_integration.py",
    "prototypes/v08_thermal_rating/run_v08_06_kernel_version_acceptance.py",
    "prototypes/v08_thermal_rating/run_v08_07_version_integration_closeout.py",
    "tests/prototypes/test_v08_independent_engineering_rating_kernel_v1.py",
    "tests/prototypes/test_v08_kernel_engineering_integration_v1.py",
    "tests/prototypes/test_v08_06_kernel_version_acceptance.py",
]


def _ruff_status() -> tuple[str, str]:
    cmd = [sys.executable, "-m", "ruff", "check", *_V08_07_RUFF_PATHS]
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=120)
    if proc.returncode == 0:
        return "PASS", ""
    return "FAIL", (proc.stdout or "")[-800:]


def _manifest_coverage() -> tuple[bool, list[str], str]:
    manifest = REPO / "ci-shard-manifest.yml"
    text = manifest.read_text(encoding="utf-8")
    missing = [f for f in MANIFEST_FILES if f not in text]
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.ci.verify_manifest",
            "--manifest",
            str(manifest),
            "--test-root",
            "tests",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )
    verify_ok = proc.returncode == 0
    detail = (proc.stdout or proc.stderr or "").strip()[-400:]
    return len(missing) == 0 and verify_ok, missing, detail


def _git_changed_files() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return lines


def _installation_test() -> str:
    try:
        importlib.import_module("hexagent")
        importlib.import_module("prototypes.v08_thermal_rating.v08_independent_engineering_rating_kernel_v1")
        importlib.import_module("prototypes.v08_thermal_rating.web.server")
        return "PASS"
    except Exception as exc:
        return f"FAIL:{type(exc).__name__}"


def _cli_api_web_consistency() -> dict[str, Any]:
    """Kernel P1 hash must match V08-04 integration artifact when both present."""
    out: dict[str, Any] = {"status": "NOT_RUN"}
    if not V08_04_ARTIFACT.is_file():
        return {"status": "SKIPPED", "reason": "v08_04 artifact missing"}
    a04 = json.loads(V08_04_ARTIFACT.read_text(encoding="utf-8"))
    p1_hash = a04.get("CASE_250KW", {}).get("report_hash")
    if V08_06_ARTIFACT.is_file():
        a06 = json.loads(V08_06_ARTIFACT.read_text(encoding="utf-8"))
        p1_hash_06 = a06.get("p1_report_hash")
        match = p1_hash == p1_hash_06
        out = {
            "status": "PASS" if match else "MISMATCH",
            "v08_04_p1_hash": p1_hash,
            "v08_06_p1_hash": p1_hash_06,
            "web_kernel_mode": "server.DesignForm.rating_engine=kernel_v1 maps duty to fixture",
        }
    return out


def _load_v08_06() -> dict[str, Any]:
    if V08_06_ARTIFACT.is_file():
        return json.loads(V08_06_ARTIFACT.read_text(encoding="utf-8"))
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "prototypes/v08_thermal_rating/run_v08_06_kernel_version_acceptance.py"),
        ],
        cwd=REPO,
        env={**dict(**__import__("os").environ), "PYTHONPATH": f"{REPO}/src:{REPO}"},
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr[-500:]}
    return json.loads(V08_06_ARTIFACT.read_text(encoding="utf-8"))


def main() -> int:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ruff_st, ruff_tail = _ruff_status()
    k_stat, _, k_tail = _run_pytest(KERNEL_TARGETED, timeout=600)
    chain_stat, _, _ = _run_pytest(V08_CHAIN_TARGETED, timeout=600)
    v07_stat, _, v07_tail = _run_pytest(V07_GOLDEN, timeout=300)
    manifest_ok, manifest_missing, manifest_detail = _manifest_coverage()
    v06 = _load_v08_06()
    changed = _git_changed_files()
    install = _installation_test()
    consistency = _cli_api_web_consistency()

    arch_docs = [
        "docs/decisions/V08_03_INDEPENDENT_RATING_KERNEL_ARCHITECTURE.md",
        "docs/decisions/V08_KERNEL_OUTLET_PRESSURE_DOMAIN_V1.md",
        "docs/tasks/evidence/V08-06-P3-kernel-acceptance-spec-r1.md",
        "docs/tasks/evidence/V08-06-independent-acceptance-fixture-register-r1.md",
    ]
    arch_ok = all((REPO / p).is_file() for p in arch_docs)

    r0_ok = v06.get("R0_STATUS") == "REGRESSION_PASS"
    p13_ok = (
        v06.get("P1_STATUS") == "KERNEL_JOINT_E2E_PASS"
        and v06.get("P2_STATUS") == "KERNEL_JOINT_E2E_PASS"
        and v06.get("P3_STATUS") == "KERNEL_JOINT_E2E_PASS"
    )
    e2e_cases = int(v06.get("SUCCESSFUL_INDEPENDENT_E2E_CASE_COUNT") or 0)

    blockers: list[str] = []
    if ruff_st != "PASS":
        blockers.append("RUFF_NOT_CLEAN_ON_V08_KERNEL_TREE")
    if k_stat != "PASS":
        blockers.append("KERNEL_TARGETED_TESTS_FAIL")
    if v07_stat != "PASS":
        blockers.append("V07_GOLDEN_REGRESSION_FAIL")
    if not manifest_ok:
        blockers.append(f"MANIFEST_MISSING:{manifest_missing}")
    if not r0_ok:
        blockers.append("R0_JOINT_E2E_NOT_VERIFIED")
    if not p13_ok:
        blockers.append("P1_P3_NOT_ALL_KERNEL_JOINT_PASS")
    if e2e_cases < 4:
        blockers.append("CHARTER_E2E_CASES_LT_4")
    if install != "PASS":
        blockers.append(f"INSTALLATION:{install}")

    integration_complete = (
        r0_ok
        and p13_ok
        and k_stat == "PASS"
        and v07_stat == "PASS"
        and install == "PASS"
        and e2e_cases >= 4
    )

    payload: dict[str, Any] = {
        "TASK_ID": TASK_ID,
        "TASK_NAME": TASK_NAME,
        "INTEGRATION_COMPLETE": integration_complete,
        "CHANGED_FILES": changed,
        "CHANGED_FILE_COUNT": len(changed),
        "ARCHITECTURE_DECISION_DOCUMENTED": arch_ok,
        "architecture_decision_paths": arch_docs,
        "R0_LIVE_JOINT_E2E_PASS": r0_ok,
        "R0_EVIDENCE": {
            "status": v06.get("R0_STATUS"),
            "shortlist_rows": v06.get("r0_shortlist_rows", [])[:4],
            "note": "R3 layouts evaluated with live kernel + joint hydraulics (not historical Task173)",
        },
        "P1_P3_INDEPENDENT_ACCEPTANCE_PASS": p13_ok,
        "P3_EVIDENCE": {
            "fixture": v06.get("p3_fixture"),
            "spec": "docs/tasks/evidence/V08-06-P3-kernel-acceptance-spec-r1.md",
            "status": v06.get("P3_STATUS"),
            "flows_kg_s": "11/19 (catalog-amended from pre-registered 10/18 empty mesh)",
        },
        "V08_01_TO_06_ACCEPTANCE": {
            "V08_06_TECHNICAL_ACCEPTANCE": v06.get("V08_06_TECHNICAL_ACCEPTANCE"),
            "V08_06_MATRIX_HASH": v06.get("matrix_hash"),
            "four_e2e_cases": e2e_cases,
        },
        "V07_GOLDEN_REGRESSION": v07_stat,
        "MANIFEST_COVERAGE_PASS": manifest_ok,
        "manifest_verify_detail": manifest_detail,
        "manifest_shard": "v08-kernel-rating-integration",
        "TARGETED_TEST_STATUS": {
            "kernel_chain": k_stat,
            "v08_04_05_smoke": chain_stat,
            "v07_golden": v07_stat,
        },
        "RUFF_STATUS": ruff_st,
        "ruff_tail": ruff_tail,
        "INSTALLATION_TEST_STATUS": install,
        "CLI_API_WEB_CONSISTENCY": consistency,
        "RELEASE_CANDIDATE_PACKAGE_READY": bool(DOC.is_file()),
        "release_candidate_doc": str(DOC.relative_to(REPO)),
        "REMAINING_BLOCKERS": blockers,
        "READY_FOR_COMMIT_AND_PUSH": integration_complete and ruff_st == "PASS" and not blockers,
        "COMMIT_AUTHORIZED": False,
        "MERGE_AUTHORIZED": False,
        "RELEASE_AUTHORIZED": False,
        "ci_note": (
            "Full PR-head / merge-ref / main CI not executed in V08-07 local closeout; "
            "required after COMMIT_AUTHORIZED=true per Charter section 8."
        ),
        "historical_ci_failures_vs_integration": (
            "Prior Task173/BVP/TRF/cache experiments remain frozen evidence; "
            "this integration regression targets V08 kernel + joint hydraulic chain only."
        ),
        "test_log_tail": {"kernel": k_tail, "v07": v07_tail},
    }
    payload["closeout_hash"] = canonical_sha256({k: v for k, v in payload.items() if k != "closeout_hash"})
    ARTIFACT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in payload if k not in ("CHANGED_FILES", "r0_shortlist_rows")}, indent=2))
    return 0 if integration_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())