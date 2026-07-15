from mscz_formatter.mscx.models import (
    MAX_PAGE_HEIGHT,
    TITLE_BOX_OFFSET,
    Line,
    RenderedMeasure,
    SourceMeasure,
)
from mscz_formatter.mscx.pages import (
    FIRST_PAGE_BUDGET,
    LATER_PAGE_BUDGET,
    add_page_breaks,
)

# First-page validity double-counts TITLE_BOX_OFFSET (once in height, once in is_valid).
_FIRST_PAGE_HEIGHT_BUDGET = FIRST_PAGE_BUDGET
_LATER_PAGE_HEIGHT_BUDGET = LATER_PAGE_BUDGET


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
    return [line for page in pages for line in page.lines]


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
    line_height = 10_000
    max_first = _FIRST_PAGE_HEIGHT_BUDGET // line_height
    lines = [_line(i, height=line_height) for i in range(max_first + 1)]

    pages = add_page_breaks(lines)

    assert len(pages) == 2
    assert pages[0].is_first_page
    assert not pages[1].is_first_page
    assert sum(len(page.lines) for page in pages) == len(lines)
    assert all(page.is_valid() for page in pages)


def test_all_input_lines_preserved_in_order():
    line_height = 40_000
    lines = [_line(i, height=line_height) for i in range(5)]

    pages = add_page_breaks(lines)

    assert _flatten(pages) == lines
    assert sum(len(page.lines) for page in pages) == len(lines)


def test_only_first_page_is_marked_first():
    line_height = 40_000
    lines = [_line(i, height=line_height) for i in range(7)]

    pages = add_page_breaks(lines)

    assert len(pages) >= 2
    assert pages[0].is_first_page
    assert all(not page.is_first_page for page in pages[1:])


def test_short_chart_packs_first_page_when_alike():
    """2-page short chart: whitespace prefers a fuller first page when turns equal."""
    line_height = 10_000
    max_first = _FIRST_PAGE_HEIGHT_BUDGET // line_height
    lines = [_line(i, height=line_height) for i in range(max_first + 3)]

    pages = add_page_breaks(lines)

    assert len(pages) == 2
    assert len(pages[0].lines) == max_first
    assert all(page.is_valid() for page in pages)


def test_long_chart_first_page_then_spread():
    """3+ pages: page 1 is alone; remaining lines form a facing spread split near mid."""
    line_height = 10_000
    max_first = _FIRST_PAGE_HEIGHT_BUDGET // line_height
    max_later = _LATER_PAGE_HEIGHT_BUDGET // line_height
    # Enough for page 1 + more than one later page (forces 3+ pages).
    lines = [_line(i, height=line_height) for i in range(max_first + max_later + 1)]

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
    line_height = 40_000
    # 4 lines → 2 pages. Height mid wants k=2; MM rest only helps k=1.
    lines = [
        _line(0, height=line_height, is_mm_rest=True),
        _line(1, height=line_height),
        _line(2, height=line_height),
        _line(3, height=line_height),
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
    line_height = 40_000
    # 8 lines: over 2-page budget so we take page 1 alone, then a spread.
    lines = [
        _line(0, height=line_height),
        _line(1, height=line_height),
        _line(2, height=line_height, is_mm_rest=True),  # good turn after page 1
        _line(3, height=line_height),
        _line(4, height=line_height),
        _line(5, height=line_height),
        _line(6, height=line_height),
        _line(7, height=line_height),
    ]

    pages = add_page_breaks(lines)

    assert len(pages) >= 3
    assert pages[0].lines[-1].measures[-1].is_mm_rest
    assert _flatten(pages) == lines
