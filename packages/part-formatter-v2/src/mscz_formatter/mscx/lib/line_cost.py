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


def _reasonable_early_break(line: Line) -> bool:
    """
    Soft: early break before an RM/MM rest is cheap only for a sensible
    chunk. Orphans (c=1–2) stay expensive so we prefer an earlier 4-break
    (drum 4+4 vs 6+2) instead of a stub line before the landmark.
    """
    c = line.c_count
    if line.measures[-1].has_double_bar:
        return True
    return (
        conceptual_length_fits(c)
        or c >= ALTERNATE_LINE_LENGTH - 1  # allow 3+
        or any(m.is_mm_rest for m in line.measures)
    )


def get_length_penalty(line: Line, next_measure: RenderedMeasure) -> float:
    """
    Prefer packing non-final lines to mpl.

    Breaking early before an MM rest or rehearsal mark (when the line isn't
    mpl-aligned) is allowed with only a mild penalty — that matches the
    "break before" rules for those landmarks.
    """
    c = line.c_count
    if c == MEASURES_PER_LINE:
        return 0.0

    # Flush before a mid-line MM rest when misaligned — but not for orphans
    # (lone [M7R] before M8*(2) was almost free and fragmented Reed 2).
    if (
        next_measure.is_mm_rest
        and c % MEASURES_PER_LINE != 0
        and _reasonable_early_break(line)
    ):
        return 0.2 * abs(c - MEASURES_PER_LINE) / MEASURES_PER_LINE

    # Prefer break-before-RM over burying the mark (soft RM score also
    # rewards opening the next line on the mark; keeps 4+4 over 6+2).
    if next_measure.has_rehearsal_mark and _reasonable_early_break(line):
        return 0.2 * abs(c - MEASURES_PER_LINE) / MEASURES_PER_LINE

    if any(m.is_mm_rest for m in line.measures):
        # MM-rest lines may exceed mpl (width still gates). Prefer aligned
        # overage; allow a mild non-aligned overage so short MM rests can
        # keep trailing music on the same line (e.g. lead-in+3MM+3 = c=7).
        over = max(0, c - MEASURES_PER_LINE) / MEASURES_PER_LINE
        if conceptual_length_fits(c):
            return 0.5 * abs(c - MEASURES_PER_LINE) / MEASURES_PER_LINE + 2.0 * over
        return 1.5 * abs(c - MEASURES_PER_LINE) / MEASURES_PER_LINE + 2.5 * over

    if conceptual_length_fits(c):
        # e.g. length 4 on a non-final regular line — discouraged vs mpl
        return 2.0

    return 5.0


def get_rehearsal_mark_penalty(line: Line, next_measure: RenderedMeasure) -> float:
    """
    Soft preference for rehearsal marks starting lines (not required).
    - Significant boost when the line opens on an RM
    - Significant cost for burying a non-consecutive RM mid-line
    - Mild cost for consecutive mid-line RMs (they can't both open a line)
    - Prefer breaking immediately before a rehearsal mark
    """
    penalty = 0.0
    if line.measures[0].has_rehearsal_mark:
        penalty -= 1.5
    for i, m in enumerate(line.measures):
        if not m.has_rehearsal_mark or i == 0:
            continue
        if line.measures[i - 1].has_rehearsal_mark:
            penalty += 0.5
        else:
            penalty += 2.5
    if next_measure.has_rehearsal_mark and _reasonable_early_break(line):
        penalty -= 1.0
    return penalty


def get_double_bar_boost(line: Line, next_measure: RenderedMeasure) -> float:
    """Prefer ending a line on a double bar (unless a slur/tie crosses it)."""
    last = line.measures[-1]
    if last.has_double_bar and not last.has_slur_or_tie_into_next:
        return 1.0
    return 0.0


def get_paired_mm_rest_boost(line: Line, next_measure: RenderedMeasure) -> float:
    """
    Prefer packing exactly two consecutive MM rests on one line when the
    conceptual length is a multiple of mpl (e.g. 8+4 → c=12, not 8 | 4+…).
    """
    if len(line.measures) != 2:
        return 0.0
    a, b = line.measures
    if not (a.is_mm_rest and b.is_mm_rest):
        return 0.0
    if line.c_count % MEASURES_PER_LINE != 0:
        return 0.0
    return 1.0


def get_slur_tie_across_break_penalty(
    line: Line, next_measure: RenderedMeasure
) -> float:
    """
    Discourage breaking a line across a slur or tie that continues into the
    next measure (see formatting-rules: slur across measures → avoid break).
    """
    if line.measures[-1].has_slur_or_tie_into_next:
        return 1.0
    return 0.0


def get_mm_rest_penalty(line: Line, next_measure: RenderedMeasure) -> float:
    """
    MM-rest preferences:
    - Don't split consecutive MM rests
    - Prefer packing following music onto the same line while under mpl
      (avoids orphan music after short MM rests like 3+3 → one line)
    - Once already at/above mpl, don't nudge to absorb more (keeps
      mpl-sized MM rests on their own line)
    """
    last = line.measures[-1]
    penalty = 0.0

    if last.is_mm_rest and next_measure.is_mm_rest:
        penalty += 1.0

    if (
        last.is_mm_rest
        and not next_measure.is_mm_rest
        and line.c_count < MEASURES_PER_LINE
        and conceptual_length_fits(line.c_count)
    ):
        # e.g. lead-in + 3-bar MM (c=4): nudge to take following music
        # rather than orphan a short music line. Skip misaligned underfills
        # (c=5) so we don't grab one bar just to reach mpl and leave a stub.
        penalty += 0.35

    return penalty


MULTIPLIERS_AND_FUNCTIONS: list[
    tuple[float, Callable[[Line, RenderedMeasure], float]]
] = [
    (15, get_length_penalty),
    (30, get_rehearsal_mark_penalty),
    (-25, get_double_bar_boost),
    (-25, get_paired_mm_rest_boost),
    (30, get_mm_rest_penalty),
    (40, get_slur_tie_across_break_penalty),
]


def line_is_candidate(line: Line) -> bool:
    """
    Structural filter used by the DP loop (in addition to width).

    Regular content may not exceed mpl. Past mpl is only allowed when the
    line contains an MM rest (alignment is preferred via soft length cost,
    not required — otherwise lead-in + short MM + music that fits width
    but lands on c=7 can never share a line).

    Mid-line rehearsal marks are allowed here; soft cost prefers RMs
    that open a line.
    """
    if not line.measures:
        return False
    if not line.is_valid():
        return False
    if line.c_count > MAX_LINE_C_COUNT:
        return False
    if line.c_count <= MEASURES_PER_LINE:
        return True
    return any(m.is_mm_rest for m in line.measures)


def _last_line_cost(line: Line) -> float:
    """Mild underfull / misalignment cost so we still prefer packed endings."""
    c = line.c_count
    if c == MEASURES_PER_LINE:
        return 0.0
    if conceptual_length_fits(c):
        # Prefer fuller aligned endings (e.g. 8 over 6+2)
        return abs(MEASURES_PER_LINE - c) * 0.05
    if c > MEASURES_PER_LINE:
        # Non-aligned overage (e.g. mpl MM + 1 music → c=7) is worse than
        # leaving a short final line after a clean mpl break.
        return (c - MEASURES_PER_LINE) * 3.0
    return abs(MEASURES_PER_LINE - c) * 0.5


def line_cost(line: Line, next_measure: RenderedMeasure | None) -> float:
    if next_measure is None:
        return _last_line_cost(line)

    cost = 0.0
    for multiplier, func in MULTIPLIERS_AND_FUNCTIONS:
        cost += multiplier * func(line, next_measure)
    return cost
