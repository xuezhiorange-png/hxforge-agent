"""Load versioned general engineering case JSON."""

from __future__ import annotations

from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_input import (
    GENERAL_ENGINEERING_CASE_SCHEMA,
    GENERAL_ENGINEERING_CASE_SCHEMA_V2,
    GeneralEngineeringCaseV1,
    GeneralEngineeringCaseV2,
)

EngineeringCase = GeneralEngineeringCaseV1 | GeneralEngineeringCaseV2


def load_general_engineering_case(data: dict[str, Any]) -> EngineeringCase:
    version = data.get("schema_version")
    if version == GENERAL_ENGINEERING_CASE_SCHEMA_V2:
        return GeneralEngineeringCaseV2.model_validate(data)
    if version in (GENERAL_ENGINEERING_CASE_SCHEMA, None):
        return GeneralEngineeringCaseV1.model_validate(data)
    raise ValueError(f"unsupported engineering case schema_version: {version}")


def load_general_engineering_case_json(text: str) -> EngineeringCase:
    import json

    return load_general_engineering_case(json.loads(text))
