# Cost helpers for page / page-group pagination (DP minimizes cost).
from collections.abc import Callable

from mscz_formatter.mscx.models import MAX_PAGE_HEIGHT, Line, Page


def get_whitespace_penalty(page: Page, next_line: Line | None = None) -> float:
    """Prefer fuller pages (0 = full, 1 = empty)."""
    fullness = min(1.0, page.height / MAX_PAGE_HEIGHT)
    return 1.0 - fullness


def get_group_whitespace_penalty(height: float, capacity: float) -> float:
    """Prefer fuller groups relative to their 1× or 2× page capacity."""
    if capacity <= 0:
        return 1.0
    fullness = min(1.0, height / capacity)
    return 1.0 - fullness


def get_page_turn_quality(end_measure_line: Line, next_line: Line) -> float:
    """
    Quality of a page turn between end_measure_line and next_line.

    1.0  — MM rest at end of this page or start of next
    0.5  — full-measure rest at end or start of next
    0.0  — no helpful rest
    """
    next_line_measure = next_line.measures[0]
    end_of_page_measure = end_measure_line.measures[-1]

    if end_of_page_measure.is_mm_rest or next_line_measure.is_mm_rest:
        return 1.0
    if end_of_page_measure.is_rest or next_line_measure.is_rest:
        return 0.5
    # TODO: half-measure rest quality later
    return 0.0


def get_good_page_turn_boost(page: Page, next_line: Line) -> float:
    """Legacy name: turn quality in [0, 1] (higher is better)."""
    return get_page_turn_quality(page.lines[-1], next_line)


def get_bad_page_turn_penalty(end_line: Line, next_line: Line) -> float:
    """Penalty in [0, 1]: 0 for a perfect MM-rest turn, 1 when no rest help."""
    return 1.0 - get_page_turn_quality(end_line, next_line)


WHITESPACE_WEIGHT = 10.0
TURN_WEIGHT = 100.0

# Kept for callers that still score a single Page (tests / debugging).
MULTIPLIERS_AND_FUNCTIONS: list[tuple[float, Callable[[Page, Line], float]]] = [
    (WHITESPACE_WEIGHT, get_whitespace_penalty),
    # Negative: good turns lower total cost under minimization.
    (-TURN_WEIGHT, get_good_page_turn_boost),
]


def page_cost(page: Page, next_line: Line | None) -> float:
    if next_line is None:
        return WHITESPACE_WEIGHT * get_whitespace_penalty(page)

    cost = 0.0
    for multiplier, func in MULTIPLIERS_AND_FUNCTIONS:
        cost += multiplier * func(page, next_line)
    return cost


def group_cost(
    *,
    height: float,
    capacity: float,
    turn_end_line: Line | None,
    next_line: Line | None,
    turn_required: bool,
) -> float:
    """Cost of a page group: fullness, plus turn penalty only when a turn follows."""
    cost = WHITESPACE_WEIGHT * get_group_whitespace_penalty(height, capacity)
    if turn_required:
        if turn_end_line is None or next_line is None:
            cost += TURN_WEIGHT
        else:
            cost += TURN_WEIGHT * get_bad_page_turn_penalty(turn_end_line, next_line)
    return cost
