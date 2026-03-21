from __future__ import annotations

import dataclasses
import json
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

import scoreforge.models as models
from scoreforge.models import Score
from scoreforge.parser import _to_canonical_dict, canonical_hash, canonical_json


_DATACLASS_REGISTRY = {
    name: cls
    for name, cls in vars(models).items()
    if isinstance(cls, type) and dataclasses.is_dataclass(cls)
}

_ENUM_REGISTRY = {
    name: cls
    for name, cls in vars(models).items()
    if isinstance(cls, type) and issubclass(cls, Enum)
}


def _decode_typed(value: Any, expected_type: Any) -> Any:
    if expected_type is Any:
        return value

    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if expected_type is Fraction and isinstance(value, list) and len(value) == 2:
        return Fraction(int(value[0]), int(value[1]))

    if isinstance(expected_type, type) and issubclass(expected_type, Enum):
        return expected_type(value)

    if origin is tuple and isinstance(value, list):
        inner = args[0] if args else Any
        return tuple(_decode_typed(v, inner) for v in value)

    if origin is list and isinstance(value, list):
        inner = args[0] if args else Any
        return [_decode_typed(v, inner) for v in value]

    if origin is dict and isinstance(value, dict):
        k_t, v_t = args if len(args) == 2 else (Any, Any)
        return {
            _decode_typed(k, k_t): _decode_typed(v, v_t)
            for k, v in value.items()
        }

    if origin in (set, frozenset) and isinstance(value, list):
        inner = args[0] if args else Any
        items = [_decode_typed(v, inner) for v in value]
        return set(items) if origin is set else frozenset(items)

    if origin is not None and str(origin).endswith("Union"):
        non_none = [a for a in args if a is not type(None)]
        if value is None:
            return None
        if isinstance(value, dict) and "__type__" in value:
            return _from_canonical_obj(value)
        for candidate in non_none:
            try:
                return _decode_typed(value, candidate)
            except Exception:
                continue
        return value

    if isinstance(value, dict) and "__type__" in value:
        return _from_canonical_obj(value)

    if isinstance(value, list):
        return [_from_canonical_obj(v) if isinstance(v, dict) else v for v in value]

    return value


def _from_canonical_obj(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    if isinstance(obj, list):
        if len(obj) == 2 and all(isinstance(x, int) for x in obj):
            return Fraction(obj[0], obj[1])
        return tuple(_from_canonical_obj(x) for x in obj)

    if isinstance(obj, dict):
        type_name = obj.get("__type__")
        if type_name is None:
            return {k: _from_canonical_obj(v) for k, v in obj.items()}

        if type_name in _ENUM_REGISTRY:
            return _ENUM_REGISTRY[type_name](obj["value"])

        cls = _DATACLASS_REGISTRY.get(type_name)
        if cls is None:
            return {k: _from_canonical_obj(v) for k, v in obj.items() if k != "__type__"}

        type_hints = get_type_hints(cls)
        kwargs = {}
        for f in dataclasses.fields(cls):
            if f.name not in obj:
                continue
            expected = type_hints.get(f.name, Any)
            kwargs[f.name] = _decode_typed(obj[f.name], expected)
        return cls(**kwargs)

    return obj


def save_canonical(score: Score, path: Path) -> None:
    """Save a Score object to canonical JSON format."""
    canonical = _to_canonical_dict(score)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(canonical, f, indent=2, sort_keys=True, ensure_ascii=False)


def load_score_from_json(path: Path) -> Score:
    """Load a Score object from canonical JSON format."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    score = _from_canonical_obj(data)
    if not isinstance(score, Score):
        raise TypeError("JSON did not decode into a Score object.")
    return score


__all__ = ["save_canonical", "load_score_from_json", "canonical_json", "canonical_hash"]

