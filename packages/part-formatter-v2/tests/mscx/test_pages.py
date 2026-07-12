from mscz_formatter.mscx.models import (
    MAX_PAGE_HEIGHT,
    TITLE_BOX_OFFSET,
    Line,
    RenderedMeasure,
    SourceMeasure,
)
from mscz_formatter.mscx.pages import add_page_breaks

# First-page validity double-counts TITLE_BOX_OFFSET (once in height, once in is_valid).
_FIRST_PAGE_HEIGHT_BUDGET = MAX_PAGE_HEIGHT - 2 * TITLE_BOX_OFFSET
_LATER_PAGE_HEIGHT_BUDGET = MAX_PAGE_HEIGHT


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
    assert len(pages[0].lines) == max_first
    assert len(pages[1].lines) == 1
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


def test_packs_first_page_when_all_lines_are_alike():
    """Whitespace penalty prefers fuller pages when page-turn quality is equal."""
    line_height = 10_000
    max_first = _FIRST_PAGE_HEIGHT_BUDGET // line_height
    lines = [_line(i, height=line_height) for i in range(max_first + 3)]

    pages = add_page_breaks(lines)

    assert len(pages[0].lines) == max_first
    assert all(page.is_valid() for page in pages)


def test_later_pages_use_full_height_budget():
    line_height = 10_000
    max_first = _FIRST_PAGE_HEIGHT_BUDGET // line_height
    max_later = _LATER_PAGE_HEIGHT_BUDGET // line_height
    # Fill first page, then one more than a later page can hold.
    lines = [_line(i, height=line_height) for i in range(max_first + max_later + 1)]

    pages = add_page_breaks(lines)

    assert len(pages) == 3
    assert len(pages[0].lines) == max_first
    assert len(pages[1].lines) == max_later
    assert len(pages[2].lines) == 1


def test_oversized_line_yields_no_valid_pages():
    """A single line taller than the page budget cannot form a valid page."""
    lines = [_line(0, height=MAX_PAGE_HEIGHT + 1)]

    assert add_page_breaks(lines) == []
