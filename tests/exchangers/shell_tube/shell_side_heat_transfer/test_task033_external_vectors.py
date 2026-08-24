"""Frozen independent D29 oracle vectors.

The expected outputs are checked-in decimal literals.  This test only checks
the frozen input/output evidence and never imports or executes the production
correlation to derive an expected value.
"""

from __future__ import annotations

from decimal import Decimal

ORACLE_VECTOR_COUNT = 12
ORACLE_VECTOR_RUNTIME_EXTERNAL_DEPENDENCY = False
ORACLE_VECTOR_PRODUCTION_FORMULA_DERIVATION = False
ORACLE_VECTOR_MINIMUM_DECIMAL_DIGITS = 80

ORACLE_VECTORS = (
    {
        "VECTOR_ID": "D29-001",
        "INPUT_PARAMETERS": {
            "reynolds": "2500.0000",
            "prandtl": "1.5000",
            "thermal_conductivity": "0.4500",
            "equivalent_diameter": "0.0180",
        },
        "EXPECTED_OUTPUT": Decimal(
            "761.73971756982091913859704614102692263045692365587836"
            "339003583797036429801960792486657374698655491406531837"
            "025247664554913974644055853675311"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-002",
        "INPUT_PARAMETERS": {
            "reynolds": "3000.0000",
            "prandtl": "2.0000",
            "thermal_conductivity": "0.5000",
            "equivalent_diameter": "0.0200",
        },
        "EXPECTED_OUTPUT": Decimal(
            "926.83522571668201761577056246956211915064546236373464"
            "786183765961379006008463680407235458922483333493880091"
            "971864263101985939402566208060132"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-003",
        "INPUT_PARAMETERS": {
            "reynolds": "5000.0000",
            "prandtl": "3.5000",
            "thermal_conductivity": "0.5980",
            "equivalent_diameter": "0.0200",
        },
        "EXPECTED_OUTPUT": Decimal(
            "1769.1440911814969189236103058507687777382228207876958"
            "837418871400734469345795549179640424613345853286169818"
            "009315727279660422208804671873003"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-004",
        "INPUT_PARAMETERS": {
            "reynolds": "7500.0000",
            "prandtl": "5.0000",
            "thermal_conductivity": "0.6200",
            "equivalent_diameter": "0.0220",
        },
        "EXPECTED_OUTPUT": Decimal(
            "2347.1735674922552375174211025043024149748011157747150"
            "713789013666118789001515867390854730913703492715583251"
            "191752275343286329910508983765005"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-005",
        "INPUT_PARAMETERS": {
            "reynolds": "11976.0479",
            "prandtl": "7.0073",
            "thermal_conductivity": "0.5980000",
            "equivalent_diameter": "0.0200000",
        },
        "EXPECTED_OUTPUT": Decimal(
            "3604.9260859251203509664990901375026771146123072797313"
            "897615119542862305569061344202897354363584803025487711"
            "597702967626095486408120199472238"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-006",
        "INPUT_PARAMETERS": {
            "reynolds": "15000.0000",
            "prandtl": "9.5000",
            "thermal_conductivity": "0.6500",
            "equivalent_diameter": "0.0250",
        },
        "EXPECTED_OUTPUT": Decimal(
            "3926.7559425447304652001356024806436609639274658013460"
            "880482169843433374391275224187522120479529349186879767"
            "883583187829223530100198798588280"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-007",
        "INPUT_PARAMETERS": {
            "reynolds": "20000.0000",
            "prandtl": "12.0000",
            "thermal_conductivity": "0.7000",
            "equivalent_diameter": "0.0300",
        },
        "EXPECTED_OUTPUT": Decimal(
            "4462.4448895909391223354660903850166513688106779369880"
            "255895123372458254786047929856057146072813217446590526"
            "839356950607316750601601996642225"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-008",
        "INPUT_PARAMETERS": {
            "reynolds": "35000.0000",
            "prandtl": "1.2000",
            "thermal_conductivity": "0.5500",
            "equivalent_diameter": "0.0180",
        },
        "EXPECTED_OUTPUT": Decimal(
            "3689.9786913735154670000298324663082578768140185439793"
            "365042431741977181417929214631303454467754845086763729"
            "985703017427137848210413647591960"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-009",
        "INPUT_PARAMETERS": {
            "reynolds": "50000.0000",
            "prandtl": "4.4000",
            "thermal_conductivity": "0.8000",
            "equivalent_diameter": "0.0250",
        },
        "EXPECTED_OUTPUT": Decimal(
            "7250.5375650358596674270289453491226428564146187750190"
            "159410216910407568168596620731660245782332566107064063"
            "966339469014841889156043348481035"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-010",
        "INPUT_PARAMETERS": {
            "reynolds": "100000.0000",
            "prandtl": "6.7000",
            "thermal_conductivity": "0.9000",
            "equivalent_diameter": "0.0300",
        },
        "EXPECTED_OUTPUT": Decimal(
            "11449.381407717591145115095444270635715426512491000087"
            "748368932647857388862677219966735042590712657678522046"
            "932439113208420914945107440898658"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-011",
        "INPUT_PARAMETERS": {
            "reynolds": "250000.0000",
            "prandtl": "10.1000",
            "thermal_conductivity": "0.7500",
            "equivalent_diameter": "0.0350",
        },
        "EXPECTED_OUTPUT": Decimal(
            "15521.601022078107939227877990262669443117623173352436"
            "506365996493756817391565096319933321810871367449546775"
            "528037805108667623712309605381337"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
    {
        "VECTOR_ID": "D29-012",
        "INPUT_PARAMETERS": {
            "reynolds": "900000.0000",
            "prandtl": "2.2000",
            "thermal_conductivity": "0.6000",
            "equivalent_diameter": "0.0400",
        },
        "EXPECTED_OUTPUT": Decimal(
            "13224.158126387682378787789154957224690626636493632533"
            "039746677835384999682321469484634027266307303990914392"
            "550914374659460860932439028742087"
        ),
        "DECIMAL_PRECISION": 120,
        "ASSERTION": "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL",
    },
)


def test_external_oracle_vectors_are_bound_and_frozen() -> None:
    assert len(ORACLE_VECTORS) == ORACLE_VECTOR_COUNT == 12
    assert len({vector["VECTOR_ID"] for vector in ORACLE_VECTORS}) == ORACLE_VECTOR_COUNT
    for vector in ORACLE_VECTORS:
        assert set(vector) == {
            "VECTOR_ID",
            "INPUT_PARAMETERS",
            "EXPECTED_OUTPUT",
            "DECIMAL_PRECISION",
            "ASSERTION",
        }
        assert set(vector["INPUT_PARAMETERS"]) == {
            "reynolds",
            "prandtl",
            "thermal_conductivity",
            "equivalent_diameter",
        }
        expected = vector["EXPECTED_OUTPUT"]
        assert isinstance(expected, Decimal)
        assert expected.is_finite()
        fractional_digits = len(format(expected, "f").split(".")[1])
        assert vector["DECIMAL_PRECISION"] >= ORACLE_VECTOR_MINIMUM_DECIMAL_DIGITS
        assert fractional_digits >= vector["DECIMAL_PRECISION"]
        assert vector["ASSERTION"] == "EXPECTED_OUTPUT_IS_FROZEN_EXTERNAL_LITERAL"
    assert ORACLE_VECTOR_RUNTIME_EXTERNAL_DEPENDENCY is False
    assert ORACLE_VECTOR_PRODUCTION_FORMULA_DERIVATION is False
