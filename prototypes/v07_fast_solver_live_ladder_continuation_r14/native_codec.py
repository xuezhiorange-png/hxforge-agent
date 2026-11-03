"""Canonical native projection and strict rehydration for CandidateRatingRequest."""

from __future__ import annotations

import collections.abc
import types
import typing
from dataclasses import MISSING, fields, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    ReferencePlanePair,
    ReferencePlaneToken,
)


def _restore_pairs(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("__task173_type__") == "ReferencePlanePair":
            return _pair_from_projection(value)
        return {key: _restore_pairs(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_pairs(item) for item in value]
    return value


def _pair_from_projection(value: Any) -> ReferencePlanePair:
    if type(value) is ReferencePlanePair:
        return value
    if (
        isinstance(value, dict)
        and {"start", "end"} <= set(value)
        and set(value) <= {"__task173_type__", "start", "end", "kind"}
        and value.get("__task173_type__", "ReferencePlanePair") == "ReferencePlanePair"
    ):
        pair = ReferencePlanePair(
            start=ReferencePlaneToken(value["start"]),
            end=ReferencePlaneToken(value["end"]),
        )
        if "kind" in value and value["kind"] != pair.kind:
            raise ValueError("ReferencePlanePair kind does not match its tokens")
        return pair
    raise TypeError("malformed ReferencePlanePair projection")


def _rehydrate_typed(expected: Any, value: Any) -> Any:
    if value is None:
        return None
    if expected is Any or expected is typing.Any:
        return _restore_pairs(value)
    if expected is ReferencePlanePair:
        return _pair_from_projection(value)

    origin = get_origin(expected)
    args = get_args(expected)
    if origin in (typing.Union, types.UnionType):
        failures: list[Exception] = []
        for option in args:
            if option is type(None):
                continue
            try:
                return _rehydrate_typed(option, value)
            except (TypeError, ValueError, KeyError) as exc:
                failures.append(exc)
        if type(None) in args:
            return None
        raise TypeError(f"cannot rehydrate union {expected}: {failures!r}")
    if origin is typing.Literal:
        if value not in args:
            raise ValueError(f"literal value {value!r} is outside {args!r}")
        return value
    if origin in (tuple, list, collections.abc.Sequence, collections.abc.MutableSequence):
        item_type = args[0] if args else Any
        values = [_rehydrate_typed(item_type, item) for item in value]
        return tuple(values) if origin is tuple else values
    if origin in (dict, collections.abc.Mapping, collections.abc.MutableMapping):
        key_type, value_type = args if args else (Any, Any)
        return {
            _rehydrate_typed(key_type, key): _rehydrate_typed(value_type, item)
            for key, item in value.items()
        }
    if expected is Decimal:
        return value if type(value) is Decimal else Decimal(str(value))
    if isinstance(expected, type) and issubclass(expected, Enum):
        return value if type(value) is expected else expected(value)
    if isinstance(expected, type) and issubclass(expected, BaseModel):
        if type(value) is expected:
            return expected.model_validate(value, strict=True)
        restored = _restore_pairs(value)
        return expected.model_validate(restored, strict=False)
    if isinstance(expected, type) and is_dataclass(expected):
        if type(value) is expected:
            return value
        hints = typing.get_type_hints(expected)
        if not isinstance(value, dict):
            raise TypeError(f"expected mapping for {expected.__name__}")
        kwargs = {
            field.name: _rehydrate_typed(hints.get(field.name, field.type), value[field.name])
            for field in fields(expected)
            if field.name in value
        }
        missing = {field.name for field in fields(expected) if field.name not in kwargs}
        required_missing = {
            field.name
            for field in fields(expected)
            if field.name in missing
            and field.default is MISSING
            and field.default_factory is MISSING
        }
        if required_missing:
            raise ValueError(
                f"missing required {expected.__name__} fields: {sorted(required_missing)}"
            )
        return expected(**kwargs)
    if expected in (str, int, float, bool):
        return expected(value)
    return _restore_pairs(value)


def native_projection(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if type(value) is ReferencePlanePair:
        return {
            "__task173_type__": "ReferencePlanePair",
            "start": value.start.value,
            "end": value.end.value,
        }
    if isinstance(value, BaseModel):
        return {name: native_projection(getattr(value, name)) for name in type(value).model_fields}
    if is_dataclass(value):
        return {
            field.name: native_projection(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, collections.abc.Mapping):
        return {str(key): native_projection(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [native_projection(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported native evidence type: {type(value).__name__}")


def candidate_request_from_projection(projection: dict[str, Any]) -> CandidateRatingRequest:
    from hexagent.exchangers.shell_tube.tube_side.valid_result import Task025ValidResult
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
        Task029SuccessResult,
    )

    restored = dict(projection)
    restored["task025_result"] = _rehydrate_typed(Task025ValidResult, restored["task025_result"])
    restored["task029_result"] = _rehydrate_typed(Task029SuccessResult, restored["task029_result"])
    request = CandidateRatingRequest.model_validate(restored, strict=False)
    request = CandidateRatingRequest.model_validate(request, strict=True)
    if type(request) is not CandidateRatingRequest:
        raise TypeError("candidate Rating request did not rehydrate to exact native model")
    return request
