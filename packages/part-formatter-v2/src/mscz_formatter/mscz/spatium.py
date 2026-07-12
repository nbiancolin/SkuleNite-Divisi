"""Spatium (staff spacing) prediction for .mss style templates."""

from __future__ import annotations

from typing import Final

NUM_INSTS_TO_SPATIUM_MAP = {
    1: 1.75,
    2: 1.75,
    3: 1.75,
    4: 1.70,
    5: 1.65,
    6: 1.65,
    7: 1.60,
    8: 1.55,
    9: 1.65,
    10: 1.65,
    11: 1.60,
}

STAFF_SPACING_STRATEGIES: Final[tuple[str, ...]] = ("predict", "preserve", "override")


def normalize_staff_spacing_strategy(strategy: str | None) -> str:
    if strategy in STAFF_SPACING_STRATEGIES:
        return strategy
    return "predict"


def _predict_staff_spacing(num_staves: int) -> float:
    if num_staves in NUM_INSTS_TO_SPATIUM_MAP:
        return NUM_INSTS_TO_SPATIUM_MAP[num_staves]
    res = (
        (NUM_INSTS_TO_SPATIUM_MAP[11] - NUM_INSTS_TO_SPATIUM_MAP[9])
        / (11 - 9)
        * (num_staves - 9)
        + NUM_INSTS_TO_SPATIUM_MAP[9]
    )
    return round(res, 4)


def predict_style_params(score_info: dict | None) -> dict[str, str]:
    score_info = score_info or {}
    if num_staves := score_info.get("num_staves"):
        return {"staff_spacing": str(_predict_staff_spacing(int(num_staves)))}
    return {}
