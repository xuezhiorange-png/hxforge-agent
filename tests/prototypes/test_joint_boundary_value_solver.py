from __future__ import annotations


def test_joint_bvp_solver_module_exposes_entrypoint() -> None:
    from prototypes.v08_thermal_rating import joint_boundary_value_axial_solver as mod

    assert callable(mod.solve_joint_boundary_value_mesh)
