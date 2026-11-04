"""Load versioned V08 user design case JSON."""

from __future__ import annotations

import json
from typing import Any

from prototypes.v08_general_user_case.user_design_case import (
    GENERAL_USER_DESIGN_CASE_SCHEMA_V1,
    GeneralUserDesignCaseV1,
)


def load_general_user_design_case(data: dict[str, Any]) -> GeneralUserDesignCaseV1:
    version = data.get("schema_version")
    if version != GENERAL_USER_DESIGN_CASE_SCHEMA_V1:
        raise ValueError(f"unsupported user design case schema_version: {version!r}")
    return GeneralUserDesignCaseV1.model_validate(data)


def load_general_user_design_case_json(text: str) -> GeneralUserDesignCaseV1:
    return load_general_user_design_case(json.loads(text))
