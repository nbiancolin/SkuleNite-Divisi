# Dynamic Programming approach to solving page turns
from collections.abc import Callable

from mscz_formatter.mscx.models import Page, Line
from mscz_formatter.mscx.models import MAX_PAGE_HEIGHT


def get_whitespace_penalty(page: Page, next_line: Line) -> float:
    """Want to prefer pages that are full over those that are empty"""
    fullness = page.height / MAX_PAGE_HEIGHT
    return 1.0 - fullness


def get_good_page_turn_boost(page: Page, next_line: Line) -> float:
    """
    Want to prefer pages that have good page turns:

    Highest prio (1)
    - a MM rest at the start of the next line
    (or) a MM rest at the end of this line

    Lower prio but still better than nothing: (0.5)
    - a full measure of rest at the start of the next line
    (or) a full measure of rest at the end of this line

    Even lower prio
    - half a measure (or some amont of rest) a start/end (0.1)
    """
    next_line_measure = next_line.measures[0]
    end_of_page_measure = page.lines[-1].measures[-1]


    if end_of_page_measure.is_mm_rest or next_line_measure.is_mm_rest:
        return 1
    if end_of_page_measure.is_rest or next_line_measure.is_rest:
        return 0.5
    #TODO: Add the "half measure" of rest feature later. Benefit outweights evelopment cost rn
    return 0.
    

MULTIPLIERS_AND_FUNCTIONS: list[tuple[int, Callable[[Page, Line], float]]] = [
    (10, get_whitespace_penalty),
    (100, get_good_page_turn_boost),
]

def page_cost(page: Page, next_line: Line | None) -> float:
    if next_line is None:
        return 0. #TODO: Should this be INF? instead of 0?

    cost = 0
    for multiplier, func in MULTIPLIERS_AND_FUNCTIONS:
        cost += multiplier * func(page, next_line)
    
    return cost
