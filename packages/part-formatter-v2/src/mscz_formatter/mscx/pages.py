from functools import lru_cache
from math import inf

from mscz_formatter.mscx.lib.page_cost import page_cost
from mscz_formatter.mscx.models import Line, Page


def add_page_breaks(lines: list[Line]) -> list[Page]:
    @lru_cache(maxsize=None)
    def solve(start_idx: int) -> tuple[float, list[Page]]:
        # Base case: no lines remaining
        if start_idx >= len(lines):
            return 0, []

        best_cost = inf
        best_pages = []

        current_lines = []

        # Try every possible page starting at start_idx
        for end_idx in range(start_idx, len(lines)):
            current_lines.append(lines[end_idx])

            candidate_page = Page(
                lines=current_lines.copy(),
                is_first_page=(start_idx == 0),
            )

            # Once a page overflows, all larger pages will overflow too
            if not candidate_page.is_valid():
                break

            # This is the first line of the following page, if one exists
            next_line = None
            if end_idx + 1 < len(lines):
                next_line = lines[end_idx + 1]

            current_page_cost = page_cost(
                candidate_page,
                next_line,
            )

            remaining_cost, remaining_pages = solve(end_idx + 1)

            total_cost = current_page_cost + remaining_cost

            if total_cost < best_cost:
                best_cost = total_cost
                best_pages = [candidate_page] + remaining_pages

        return best_cost, best_pages

    _, pages = solve(0)
    return pages
