"""
File for formatting measures into lines via dynamic programming.
"""
from functools import lru_cache
from math import inf

from mscz_formatter.mscx.lib.line_cost import (
    ABSOLUTE_MAX_LINE_C_COUNT,
    ALTERNATE_LINE_LENGTH,
    MAX_LINE_C_COUNT,
    MEASURES_PER_LINE,
    allows_over_soft_c_count,
    line_cost,
    line_is_candidate,
)
from mscz_formatter.mscx.models import Line, RenderedMeasure

# Re-export for callers / tests
__all__ = [
    "ALTERNATE_LINE_LENGTH",
    "MEASURES_PER_LINE",
    "add_line_breaks",
    "generate_lines",
    "balance_and_validate_lines",
]


def add_line_breaks(measures: list[RenderedMeasure]) -> list[Line]:
    @lru_cache(maxsize=None)
    def solve(start_idx: int) -> tuple[float, tuple[Line, ...]]:
        if start_idx >= len(measures):
            return 0.0, ()

        best_cost = inf
        best_lines: tuple[Line, ...] = ()

        current = Line(measures=[], rm_count=0, c_count=0)

        for end_idx in range(start_idx, len(measures)):
            current.add_measure(measures[end_idx])

            # Width only grows; stop. Soft c_count ceiling still allows MM
            # lines to grow toward an aligned length (e.g. 15+1 → 16) and
            # lone oversized MM rests (cannot be split across lines).
            if not current.is_valid():
                break
            if current.c_count > ABSOLUTE_MAX_LINE_C_COUNT and not (
                len(current.measures) == 1 and current.measures[0].is_mm_rest
            ):
                break
            if (
                current.c_count > MAX_LINE_C_COUNT
                and not allows_over_soft_c_count(current)
            ):
                break

            # Hard rule: never end a line mid multi-measure % repeat.
            # Keep growing until the group completes (do not break).
            if current.measures[-1].continues_measure_repeat:
                continue

            if not line_is_candidate(current):
                continue

            candidate = Line(
                measures=current.measures.copy(),
                rm_count=current.rm_count,
                c_count=current.c_count,
            )

            next_measure = (
                measures[end_idx + 1] if end_idx + 1 < len(measures) else None
            )
            current_cost = line_cost(candidate, next_measure)
            remaining_cost, remaining_lines = solve(end_idx + 1)
            total_cost = current_cost + remaining_cost

            if total_cost < best_cost:
                best_cost = total_cost
                best_lines = (candidate,) + remaining_lines

        return best_cost, best_lines

    _, lines = solve(0)
    return list(lines)


# Backwards-compatible alias for tests
generate_lines = add_line_breaks
