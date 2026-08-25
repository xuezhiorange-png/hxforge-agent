"""Independent frozen Bayram-Sevilgen oracle vector bindings."""

from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_pressure_drop.formulas import evaluate_pressure_drop

ORACLE_DECIMAL_PRECISION = 120
ORACLE_VECTOR_RUNTIME_EXTERNAL_DEPENDENCY = False
ORACLE_VECTOR_PRODUCTION_FORMULA_DERIVATION = False

ORACLE_VECTORS = (
    (
        "T034-ORACLE-001",
        ("12000", "1250", "998", "1.2", "0.041", 12, "0.001", "0.00082"),
        "86505.427",
    ),
    ("T034-ORACLE-002", ("500", "310", "995", "1.1", "0.038", 8, "0.0011", "0.00095"), "6732.209"),
    (
        "T034-ORACLE-003",
        ("500000", "2100", "980", "1.4", "0.050", 18, "0.0009", "0.00075"),
        "171537.113",
    ),
    (
        "T034-ORACLE-004",
        ("400.0001", "275", "997", "1.0", "0.035", 6, "0.0010", "0.00090"),
        "4259.184",
    ),
    ("T034-ORACLE-005", ("400", "275", "997", "1.0", "0.035", 6, "0.0010", "0.00090"), None),
    ("T034-ORACLE-006", ("399.9999", "275", "997", "1.0", "0.035", 6, "0.0010", "0.00090"), None),
    (
        "T034-ORACLE-007",
        ("999999.9", "2300", "975", "1.6", "0.060", 24, "0.0008", "0.00060"),
        "223867.994",
    ),
    ("T034-ORACLE-008", ("1000000", "2300", "975", "1.6", "0.060", 24, "0.0008", "0.00060"), None),
    (
        "T034-ORACLE-009",
        ("1000000.1", "2300", "975", "1.6", "0.060", 24, "0.0008", "0.00060"),
        None,
    ),
    (
        "T034-ORACLE-010",
        ("18000", "900", "1000", "1.25", "0.043", 10, "0.0014", "0.00025"),
        "28131.623",
    ),
    (
        "T034-ORACLE-011",
        ("24000", "1125", "990", "1.2", "0.041", 24, "0.0010", "0.00080"),
        "118665.189",
    ),
    (
        "T034-ORACLE-012",
        ("36000", "1450", "1005", "2.0", "0.055", 14, "0.00095", "0.00070"),
        "132491.214",
    ),
)


def _evaluate(values):
    names = ("Re_s", "G_s", "rho_s", "D_s", "D_e", "N_b", "mu_b", "mu_w")
    return evaluate_pressure_drop(
        **{
            name: value if name == "N_b" else Decimal(value)
            for name, value in zip(names, values, strict=True)
        }
    )


def test_x004_external_oracle_vector_set():
    assert len(ORACLE_VECTORS) == 12
    for vector_id, inputs, expected in ORACLE_VECTORS:
        assert vector_id.startswith("T034-ORACLE-")
        if expected is not None:
            assert _evaluate(inputs).public == Decimal(expected)


def test_x011_success_oracle_output_binding():
    assert _evaluate(ORACLE_VECTORS[0][1]).public == Decimal(ORACLE_VECTORS[0][2])
