"""
Page breaks via DP over page groups (singles + two-page spreads).

Real page turns only happen at the end of odd pages. We search over groups
whose trailing boundary is a turn (when more music follows), then split
facing spreads at a height midpoint.

When an even page can end on a good rest but continuing onto the facing odd
page would force a bad later turn, we may emit that even page of music plus a
blank odd page with a full-page "V.S." frame (volti subito).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import inf
from typing import Literal

from mscz_formatter.mscx.lib.page_cost import group_cost
from mscz_formatter.mscx.models import (
    MAX_PAGE_HEIGHT,
    TITLE_BOX_OFFSET,
    Line,
    Page,
)

# Match Page.is_valid(): first-page height + is_valid both add TITLE_BOX_OFFSET.
FIRST_PAGE_BUDGET = MAX_PAGE_HEIGHT - 2 * TITLE_BOX_OFFSET
LATER_PAGE_BUDGET = MAX_PAGE_HEIGHT

GroupKind = Literal["single", "spread", "music_plus_blank"]


@dataclass(frozen=True)
class PageGroup:
    lines: tuple[Line, ...]
    kind: GroupKind
    is_first_page: bool
    turn_required: bool
    # For short-chart spreads where the turn is the mid split, pin the cut.
    split_after: int | None = None

    @property
    def capacity(self) -> float:
        if self.kind == "single":
            return FIRST_PAGE_BUDGET if self.is_first_page else LATER_PAGE_BUDGET
        # spread and music_plus_blank occupy two page slots
        if self.is_first_page:
            return FIRST_PAGE_BUDGET + LATER_PAGE_BUDGET
        return 2 * LATER_PAGE_BUDGET

    @property
    def height(self) -> float:
        return sum(line.height for line in self.lines)


def _page(lines: list[Line], is_first: bool) -> Page:
    return Page(lines=lines, is_first_page=is_first)


def _lines_fit_page(lines: list[Line], is_first: bool) -> bool:
    return bool(lines) and _page(lines, is_first).is_valid()


def _height_mid_split(
    lines: list[Line],
    *,
    left_is_first: bool,
    split_after: int | None = None,
) -> tuple[list[Line], list[Line]] | None:
    """
    Bipartition where both sides are valid pages.

    If split_after is set, use that cut (must be valid).
    Otherwise pick the cut closest to half the group height.
    If everything fits on one page, right is empty.
    """
    if not lines:
        return None
    if _lines_fit_page(lines, left_is_first):
        return lines, []

    if split_after is not None:
        left, right = lines[:split_after], lines[split_after:]
        if (
            left
            and right
            and _lines_fit_page(left, left_is_first)
            and _lines_fit_page(right, is_first=False)
        ):
            return left, right
        return None

    total = sum(line.height for line in lines)
    best: tuple[list[Line], list[Line]] | None = None
    best_dist = inf

    for k in range(1, len(lines)):
        left, right = lines[:k], lines[k:]
        if not _lines_fit_page(left, left_is_first):
            continue
        if not _lines_fit_page(right, is_first=False):
            continue
        left_h = sum(line.height for line in left)
        dist = abs(left_h - total / 2.0)
        if dist < best_dist:
            best_dist = dist
            best = (left, right)

    return best


def _spread_is_partitionable(lines: list[Line], *, left_is_first: bool) -> bool:
    return _height_mid_split(lines, left_is_first=left_is_first) is not None


def _blank_vs_page() -> Page:
    return Page(lines=[], is_first_page=False, is_blank_vs=True)


def _split_group(group: PageGroup) -> list[Page]:
    if group.kind == "single":
        return [_page(list(group.lines), group.is_first_page)]

    if group.kind == "music_plus_blank":
        return [
            _page(list(group.lines), group.is_first_page),
            _blank_vs_page(),
        ]

    parts = _height_mid_split(
        list(group.lines),
        left_is_first=group.is_first_page,
        split_after=group.split_after,
    )
    if parts is None:
        return []
    left, right = parts
    pages = [_page(left, group.is_first_page)]
    if right:
        pages.append(_page(right, is_first=False))
    return pages


def _group_total_cost(
    group: PageGroup,
    next_line: Line | None,
) -> float:
    turn_end: Line | None = None
    turn_next: Line | None = next_line

    if group.kind == "music_plus_blank":
        # Blank odd page is the turn: no rest penalty after the frame.
        return group_cost(
            height=group.height,
            capacity=group.capacity,
            turn_end_line=None,
            next_line=None,
            turn_required=False,
        )

    if group.turn_required:
        if (
            group.kind == "spread"
            and group.split_after is not None
            and 0 < group.split_after < len(group.lines)
        ):
            # Short chart: turn sits at the pinned mid split.
            turn_end = group.lines[group.split_after - 1]
            turn_next = group.lines[group.split_after]
        else:
            turn_end = group.lines[-1]

    return group_cost(
        height=group.height,
        capacity=group.capacity,
        turn_end_line=turn_end,
        next_line=turn_next,
        turn_required=group.turn_required,
    )


def add_page_breaks(lines: list[Line]) -> list[Page]:
    n = len(lines)
    if n == 0:
        return []

    @lru_cache(maxsize=None)
    def solve(start_idx: int, page_num: int) -> tuple[float, tuple[PageGroup, ...]]:
        if start_idx >= n:
            return 0.0, ()

        best_cost = inf
        best_groups: tuple[PageGroup, ...] = ()
        is_first = page_num == 1
        page_budget = FIRST_PAGE_BUDGET if is_first else LATER_PAGE_BUDGET
        rem_h = sum(line.height for line in lines[start_idx:])

        def consider(group: PageGroup, end_idx: int) -> None:
            nonlocal best_cost, best_groups
            next_line = lines[end_idx + 1] if end_idx + 1 < n else None
            # When turn is internal (short spread), next_line after group is unused.
            cost = _group_total_cost(group, next_line)
            remaining_cost, remaining = solve(
                end_idx + 1, page_num + _emitted_page_count(group)
            )
            total = cost + remaining_cost
            if total < best_cost:
                best_cost = total
                best_groups = (group,) + remaining

        # --- Short chart (≤2 pages from the start): consume all remaining lines ---
        # If nothing partitions cleanly (height fits 2× budget but lines don't),
        # fall through to the 3+ page path.
        if is_first and rem_h <= FIRST_PAGE_BUDGET + LATER_PAGE_BUDGET:
            chunk = lines[start_idx:]
            end_idx = n - 1

            if _lines_fit_page(chunk, is_first=True):
                consider(
                    PageGroup(
                        lines=tuple(chunk),
                        kind="single",
                        is_first_page=True,
                        turn_required=False,
                    ),
                    end_idx,
                )
            else:
                # Prefer fuller first pages on ties (iterate high → low).
                for k in range(len(chunk) - 1, 0, -1):
                    left, right = chunk[:k], chunk[k:]
                    if not _lines_fit_page(left, is_first=True):
                        continue
                    if not _lines_fit_page(right, is_first=False):
                        continue
                    consider(
                        PageGroup(
                            lines=tuple(chunk),
                            kind="spread",
                            is_first_page=True,
                            turn_required=True,
                            split_after=k,
                        ),
                        end_idx,
                    )
            if best_cost < inf:
                return best_cost, best_groups

        # --- Last page: remaining content fits on this page ---
        if rem_h <= page_budget and _lines_fit_page(lines[start_idx:], is_first):
            group = PageGroup(
                lines=tuple(lines[start_idx:]),
                kind="single",
                is_first_page=is_first,
                turn_required=False,
            )
            return _group_total_cost(group, None), (group,)

        # --- Page 1 alone when chart needs 3+ pages ---
        if is_first:
            for end_idx in range(start_idx, n - 1):
                chunk = lines[start_idx : end_idx + 1]
                if not _lines_fit_page(chunk, is_first=True):
                    break
                consider(
                    PageGroup(
                        lines=tuple(chunk),
                        kind="single",
                        is_first_page=True,
                        turn_required=True,
                    ),
                    end_idx,
                )
            return best_cost, best_groups

        # --- Later pages ---
        # Facing spreads are even|odd pairs only (2|3, 4|5, …). Starting a
        # "spread" on an odd page would straddle a real page turn without
        # scoring it. Odd pages are singles; turn_required when more follows.
        on_even = page_num % 2 == 0

        for end_idx in range(start_idx, n):
            chunk = lines[start_idx : end_idx + 1]
            chunk_h = sum(line.height for line in chunk)
            more_after = end_idx + 1 < n

            if chunk_h > 2 * LATER_PAGE_BUDGET:
                break

            if _lines_fit_page(chunk, is_first=False):
                # Physical turns are only after odd pages.
                turn_required = more_after and not on_even
                consider(
                    PageGroup(
                        lines=tuple(chunk),
                        kind="single",
                        is_first_page=False,
                        turn_required=turn_required,
                    ),
                    end_idx,
                )

                # Even page ending on a rest + blank odd "V.S." page. Occupies
                # two page numbers so the next music starts after a free turn.
                # Require the rest on this page (not only on the next line) so
                # the player has turn time before the blank / V.S.
                end_m = chunk[-1].measures[-1]
                if on_even and more_after and (end_m.is_mm_rest or end_m.is_rest):
                    consider(
                        PageGroup(
                            lines=tuple(chunk),
                            kind="music_plus_blank",
                            is_first_page=False,
                            turn_required=False,
                        ),
                        end_idx,
                    )

            # Facing spread (even|odd only).
            if (
                on_even
                and len(chunk) >= 2
                and _spread_is_partitionable(chunk, left_is_first=False)
            ):
                consider(
                    PageGroup(
                        lines=tuple(chunk),
                        kind="spread",
                        is_first_page=False,
                        turn_required=more_after,
                    ),
                    end_idx,
                )

        return best_cost, best_groups

    def _emitted_page_count(group: PageGroup) -> int:
        pages = _split_group(group)
        return max(1, len(pages))

    _, groups = solve(0, 1)
    pages: list[Page] = []
    for group in groups:
        pages.extend(_split_group(group))
    return pages
