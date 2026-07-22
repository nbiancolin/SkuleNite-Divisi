# Dynamic Programming approach to solving line breaks
from collections.abc import Callable

from mscz_formatter.mscx.models import Line, RenderedMeasure

MEASURES_PER_LINE = 6
ALTERNATE_LINE_LENGTH = 4
# Absolute ceiling so the DP loop terminates even when width still fits
MAX_LINE_C_COUNT = MEASURES_PER_LINE * 2


def conceptual_length_fits(c_count: int) -> bool:
    return (
        c_count % MEASURES_PER_LINE == 0
        or c_count % ALTERNATE_LINE_LENGTH == 0
    )


def get_length_penalty(line: Line, next_measure: RenderedMeasure) -> float:
    """
    Prefer packing non-final lines to mpl.

    Breaking early before an MM rest (when the line isn't mpl-aligned) is
    allowed with only a mild penalty — that matches the "break before"
    MM-rest rule.
    """
    c = line.c_count
    if c == MEASURES_PER_LINE:
        return 0.0

    # Greedy-equivalent: flush before a mid-line MM rest when misaligned
    if next_measure.is_mm_rest and c % MEASURES_PER_LINE != 0:
        return 0.2 * abs(c - MEASURES_PER_LINE) / MEASURES_PER_LINE

    if conceptual_length_fits(c) and any(m.is_mm_rest for m in line.measures):
        return 0.5 * abs(c - MEASURES_PER_LINE) / MEASURES_PER_LINE

    if conceptual_length_fits(c):
        # e.g. length 4 on a non-final regular line — discouraged vs mpl
        return 2.0

    return 5.0


def get_rehearsal_mark_penalty(line: Line, next_measure: RenderedMeasure) -> float:
    """
    Rehearsal marks should start new lines.
    - Penalize RMs that appear mid-line
    - Prefer breaking immediately before a rehearsal mark
    """
    penalty = 0.0
    for i, m in enumerate(line.measures):
        if m.has_rehearsal_mark and i != 0:
            penalty += 1.0
    if next_measure.has_rehearsal_mark:
        penalty -= 1.0
    return penalty


def get_double_bar_boost(line: Line, next_measure: RenderedMeasure) -> float:
    """Prefer ending a line on a double bar."""
    if line.measures[-1].has_double_bar:
        return 1.0
    return 0.0


def get_mm_rest_penalty(line: Line, next_measure: RenderedMeasure) -> float:
    """
    MM-rest preferences:
    - Don't split consecutive MM rests
    - Prefer keeping an aligned MM-rest run with following measures when
      the combined conceptual length still fits (unless the line already
      has a pair of MM rests — those should end cleanly)
    """
    last = line.measures[-1]
    penalty = 0.0
    mm_count = sum(1 for m in line.measures if m.is_mm_rest)

    if last.is_mm_rest and next_measure.is_mm_rest:
        penalty += 1.0

    # Prefer not breaking right after MM rests when the next measures
    # would still fit on an aligned over-mpl line
    if (
        last.is_mm_rest
        and not next_measure.is_mm_rest
        and mm_count < 2
        and conceptual_length_fits(line.c_count)
        and line.c_count < MAX_LINE_C_COUNT
    ):
        # Mild nudge to keep going when remaining room exists
        penalty += 0.25

    return penalty


def get_paired_mm_rest_boost(line: Line, next_measure: RenderedMeasure) -> float:
    """
    Prefer ending a line that places two MM rests together.

    Rewards a clean break after the pair (line ends on an MM rest) so
    trailing music is not absorbed just to fill space.
    """
    if not line.measures[-1].is_mm_rest:
        return 0.0
    mm_count = sum(1 for m in line.measures if m.is_mm_rest)
    return 1.0 if mm_count >= 2 else 0.0


MULTIPLIERS_AND_FUNCTIONS: list[
    tuple[float, Callable[[Line, RenderedMeasure], float]]
] = [
    (100, get_length_penalty),
    (50, get_rehearsal_mark_penalty),
    (-50, get_double_bar_boost),
    (80, get_mm_rest_penalty),
    (-80, get_paired_mm_rest_boost),
]


def _is_unsplittable_mm_rest_line(line: Line) -> bool:
    """A lone MM rest cannot be subdivided, even if its span exceeds the soft ceiling."""
    return (
        len(line.measures) == 1
        and line.measures[0].is_mm_rest
        and (line.measures[0].mm_rest_span or 0) > 0
    )


def line_is_candidate(line: Line) -> bool:
    """
    Soft structural filter used by the DP loop (in addition to width).

    Regular content may not exceed mpl. Past mpl is only allowed when the
    conceptual length aligns and the line contains an MM rest.
    A single MM rest may exceed MAX_LINE_C_COUNT (unsplittable).
    """
    if not line.measures:
        return False
    if not line.is_valid():
        return False
    if line.c_count > MAX_LINE_C_COUNT:
        return _is_unsplittable_mm_rest_line(line)
    if line.c_count <= MEASURES_PER_LINE:
        return True
    return conceptual_length_fits(line.c_count) and any(
        m.is_mm_rest for m in line.measures
    )


def _last_line_cost(line: Line) -> float:
    """Mild underfull / misalignment cost so we still prefer packed endings."""
    c = line.c_count
    if c == MEASURES_PER_LINE:
        return 0.0
    if conceptual_length_fits(c):
        # Prefer fuller aligned endings (e.g. 8 over 6+2)
        return abs(MEASURES_PER_LINE - c) * 0.05
    return abs(MEASURES_PER_LINE - c) * 0.5


def line_cost(line: Line, next_measure: RenderedMeasure | None) -> float:
    if next_measure is None:
        return _last_line_cost(line)

    cost = 0.0
    for multiplier, func in MULTIPLIERS_AND_FUNCTIONS:
        cost += multiplier * func(line, next_measure)
    return cost
