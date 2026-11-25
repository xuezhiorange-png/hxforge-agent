"""V08-06 kernel version acceptance (targeted)."""

from prototypes.v08_thermal_rating.v08_06_kernel_version_acceptance import (
    run_v08_06_kernel_version_acceptance,
)


def test_kernel_matrix_minimum_e2e_cases() -> None:
    payload = run_v08_06_kernel_version_acceptance()
    assert payload["SUCCESSFUL_INDEPENDENT_E2E_CASE_COUNT"] >= 4
    assert payload["P1_STATUS"] == "KERNEL_JOINT_E2E_PASS"
    assert payload["P2_STATUS"] == "KERNEL_JOINT_E2E_PASS"
    assert payload["R0_STATUS"] == "REGRESSION_PASS"
    assert payload["FALSE_FEASIBLE_COUNT"] == 0
    assert payload["NEW_KERNEL_CONTRACT_VALIDATION_STATUS"] == "PASS"
    assert payload["DETERMINISM_STATUS"] is True


def test_n1_n2_not_false_feasible() -> None:
    payload = run_v08_06_kernel_version_acceptance()
    assert payload["N1_STATUS"] in ("INVALID_INPUT", "EXPECTED_BLOCKED")
    assert payload["N2_STATUS"] == "NO_FEASIBLE_DESIGN"