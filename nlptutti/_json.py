"""Strict JSON decoding shared by transcript and comparison inputs."""

import json
import math
from typing import Dict, List, Tuple


def _unique_object(pairs: List[Tuple[str, object]]) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key {!r}".format(key[:80]))
        result[key] = value
    return result


def _reject_constant(value: str) -> float:
    raise ValueError("JSON numbers must be finite: {}".format(value))


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON numbers must be finite")
    return number


def load_json(text: str) -> object:
    """Reject duplicate keys and non-finite numbers before information is lost."""
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            "invalid JSON at line {}, column {}".format(error.lineno, error.colno)
        ) from error
