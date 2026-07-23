from mscz_formatter.mscx.models import (
    MAX_PAGE_HEIGHT,
    SYSTEM_DISTANCE,
    Line,
    RenderedMeasure,
    SourceMeasure,
)
from mscz_formatter.mscx.pages import (
    FIRST_PAGE_BUDGET,
    LATER_PAGE_BUDGET,
    add_page_breaks,
    pages_from_lines,
)

# First-page validity double-counts TITLE_BOX_OFFSET (once in height, once in is_valid).
_FIRST_PAGE_HEIGHT_BUDGET = FIRST_PAGE_BUDGET
_LATER_PAGE_HEIGHT_BUDGET = LATER_PAGE_BUDGET


def _advance(content_height: float) -> float:
    """Match Line.height: content bbox + min system distance."""
    return content_height + SYSTEM_DISTANCE


def _measure(
    num: int,
    *,
    height: float = 10_000,
    is_rest: bool = False,
    is_mm_rest: bool = False,
    mm_rest_span: int | None = None,
) -> RenderedMeasure:
    return RenderedMeasure(
        num=num,
        width=100,
        height=height,
        source_measure_hash=num,
        source_measure=SourceMeasure(num=num, hash_key=num, is_rest=is_rest),
        has_double_bar=False,
        has_existing_line_break=False,
        has_rehearsal_mark=False,
        is_mm_rest=is_mm_rest,
        mm_rest_hashes=[],
        mm_rest_span=mm_rest_span if is_mm_rest else None,
    )


def _line(
    num: int,
    *,
    height: float = 10_000,
    is_rest: bool = False,
    is_mm_rest: bool = False,
) -> Line:
    measure = _measure(
        num,
        height=height,
        is_rest=is_rest,
        is_mm_rest=is_mm_rest,
        mm_rest_span=4 if is_mm_rest else None,
    )
    return Line(
        measures=[measure],
        rm_count=1,
        c_count=measure.mm_rest_span if measure.is_mm_rest else 1,
    )


def _flatten(pages) -> list[Line]:
    return [line for page in pages if not page.is_blank_vs for line in page.lines]


def test_empty_input_returns_no_pages():
    assert add_page_breaks([]) == []


def test_lines_that_fit_return_single_first_page():
    lines = [_line(i) for i in range(3)]
    pages = add_page_breaks(lines)

    assert len(pages) == 1
    assert pages[0].is_first_page
    assert pages[0].lines == lines
    assert pages[0].is_valid()


def test_overflow_splits_across_pages():
    content_h = 10_000
    max_first = int(_FIRST_PAGE_HEIGHT_BUDGET // _advance(content_h))
    lines = [_line(i, height=content_h) for i in range(max_first + 1)]

    pages = add_page_breaks(lines)

    assert len(pages) == 2
    assert pages[0].is_first_page
    assert not pages[1].is_first_page
    assert sum(len(page.lines) for page in pages) == len(lines)
    assert all(page.is_valid() for page in pages)


def test_all_input_lines_preserved_in_order():
    content_h = 40_000
    lines = [_line(i, height=content_h) for i in range(5)]

    pages = add_page_breaks(lines)

    assert _flatten(pages) == lines
    assert sum(len(page.lines) for page in pages) == len(lines)


def test_only_first_page_is_marked_first():
    content_h = 40_000
    lines = [_line(i, height=content_h) for i in range(7)]

    pages = add_page_breaks(lines)

    assert len(pages) >= 2
    assert pages[0].is_first_page
    assert all(not page.is_first_page for page in pages[1:])


def test_short_chart_packs_first_page_when_alike():
    """2-page short chart: whitespace prefers a fuller first page when turns equal."""
    content_h = 10_000
    advance = _advance(content_h)
    max_first = int(_FIRST_PAGE_HEIGHT_BUDGET // advance)
    max_later = int(_LATER_PAGE_HEIGHT_BUDGET // advance)
    # Overflow first page but still fit in two pages total.
    n = max_first + min(3, max_later)
    assert n <= max_first + max_later
    lines = [_line(i, height=content_h) for i in range(n)]

    pages = add_page_breaks(lines)

    assert len(pages) == 2
    assert len(pages[0].lines) == max_first
    assert all(page.is_valid() for page in pages)


def test_long_chart_first_page_then_spread():
    """3+ pages: page 1 is alone; remaining lines form a facing spread split near mid."""
    content_h = 10_000
    advance = _advance(content_h)
    max_first = int(_FIRST_PAGE_HEIGHT_BUDGET // advance)
    max_later = int(_LATER_PAGE_HEIGHT_BUDGET // advance)
    # Enough for page 1 + more than one later page (forces 3+ pages).
    lines = [_line(i, height=content_h) for i in range(max_first + max_later + 1)]

    pages = add_page_breaks(lines)

    assert len(pages) == 3
    assert pages[0].is_first_page
    assert len(pages[0].lines) == max_first
    # Facing spread is height-balanced, not greedily packed.
    assert abs(len(pages[1].lines) - len(pages[2].lines)) <= 1
    assert _flatten(pages) == lines
    assert all(page.is_valid() for page in pages)


def test_oversized_line_yields_no_valid_pages():
    """A single line taller than the page budget cannot form a valid page."""
    lines = [_line(0, height=MAX_PAGE_HEIGHT + 1)]

    assert add_page_breaks(lines) == []


def test_prefers_mm_rest_at_short_chart_turn():
    """For a 2-page chart, prefer a turn with an MM rest over a pure height mid."""
    # Content height chosen so 4 lines fit in 2 pages, and k=1 (MM) is valid.
    content_h = 25_000
    lines = [
        _line(0, height=content_h, is_mm_rest=True),
        _line(1, height=content_h),
        _line(2, height=content_h),
        _line(3, height=content_h),
    ]

    pages = add_page_breaks(lines)

    assert len(pages) == 2
    assert pages[0].lines[-1].measures[-1].is_mm_rest
    assert len(pages[0].lines) == 1
    assert _flatten(pages) == lines


def test_long_chart_scores_turn_after_first_page_not_mid_spread():
    """
    After page 1, a facing spread may place a playable boundary mid-pair
    without requiring a rest there; the scored turn is end of page 1.
    """
    content_h = 25_000
    # Over 2-page budget → page 1 alone, then a spread. MM at end of page 1.
    lines = [
        _line(0, height=content_h),
        _line(1, height=content_h),
        _line(2, height=content_h, is_mm_rest=True),  # good turn after page 1
        _line(3, height=content_h),
        _line(4, height=content_h),
        _line(5, height=content_h),
        _line(6, height=content_h),
        _line(7, height=content_h),
    ]

    pages = add_page_breaks(lines)

    assert len(pages) >= 3
    assert pages[0].lines[-1].measures[-1].is_mm_rest
    assert _flatten(pages) == lines


def test_inserts_blank_vs_when_even_page_ends_on_rest():
    """
    Long chart: good rest at end of an even page, but continuing onto the
    facing odd page would force a bad turn later → blank odd page with V.S.
    """
    content_h = 25_000
    # Page 1: lines 0-2 (MM at end). Page 2: lines 3-5 ending MM.
    # Remaining lines have no rests → cannot turn after an odd music page.
    lines = [
        _line(0, height=content_h),
        _line(1, height=content_h),
        _line(2, height=content_h, is_mm_rest=True),
        _line(3, height=content_h),
        _line(4, height=content_h),
        _line(5, height=content_h, is_mm_rest=True),
        _line(6, height=content_h),
        _line(7, height=content_h),
        _line(8, height=content_h),
        _line(9, height=content_h),
        _line(10, height=content_h),
        _line(11, height=content_h),
    ]

    pages = add_page_breaks(lines)

    assert any(page.is_blank_vs for page in pages)
    blank_idx = next(i for i, page in enumerate(pages) if page.is_blank_vs)
    assert blank_idx % 2 == 0  # 0-based index of odd page number
    assert pages[blank_idx - 1].lines[-1].measures[-1].is_mm_rest
    assert _flatten(pages) == lines
    assert all(page.is_valid() for page in pages)


def test_pages_from_lines_skips_page_turns_when_disabled():
    """Without turn optimization, all lines stay on one page (line breaks only)."""
    content_h = 40_000
    lines = [_line(i, height=content_h) for i in range(7)]

    pages = pages_from_lines(lines, optimize_for_page_turns=False)

    assert len(pages) == 1
    assert pages[0].is_first_page
    assert pages[0].lines == lines
    assert not pages[0].is_blank_vs


def test_pages_from_lines_empty_when_disabled():
    assert pages_from_lines([], optimize_for_page_turns=False) == []


def test_pages_from_lines_delegates_to_add_page_breaks_when_enabled():
    content_h = 40_000
    lines = [_line(i, height=content_h) for i in range(5)]

    assert pages_from_lines(lines, optimize_for_page_turns=True) == add_page_breaks(lines)
