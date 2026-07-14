import xml.etree.ElementTree as ET

from mscz_formatter.mscx.apply import apply_pages_to_staff
from mscz_formatter.mscx.models import Line, Page, RenderedMeasure, SourceMeasure


def _measure_el(voice: bool = True) -> ET.Element:
    m = ET.Element("Measure")
    if voice:
        ET.SubElement(m, "voice")
    return m


def _rendered(
    hash_key: int,
    *,
    is_mm_rest: bool = False,
    mm_rest_hashes: list[int] | None = None,
) -> RenderedMeasure:
    return RenderedMeasure(
        num=hash_key,
        width=100,
        height=100,
        source_measure_hash=hash_key,
        source_measure=SourceMeasure(num=hash_key, hash_key=hash_key, is_rest=False),
        has_double_bar=False,
        has_existing_line_break=False,
        has_rehearsal_mark=False,
        is_mm_rest=is_mm_rest,
        mm_rest_hashes=mm_rest_hashes or [],
        mm_rest_span=1 + len(mm_rest_hashes or []) if is_mm_rest else None,
    )


def _line_break_subtype(measure: ET.Element) -> str | None:
    lb = measure.find("LayoutBreak")
    if lb is None:
        return None
    st = lb.find("subtype")
    return None if st is None else st.text


def test_line_break_on_normal_measure_only_targets_source():
    m1 = _measure_el()
    m2 = _measure_el()
    measures_by_hash = {1: m1, 2: m2}
    staff = ET.Element("Staff")
    staff.extend([m1, m2])

    pages = [
        Page(
            lines=[
                Line(measures=[_rendered(1)], rm_count=1, c_count=1),
                Line(measures=[_rendered(2)], rm_count=1, c_count=1),
            ],
            is_first_page=True,
        )
    ]

    apply_pages_to_staff(staff, pages, measures_by_hash)

    assert _line_break_subtype(m1) == "line"
    assert _line_break_subtype(m2) is None


def test_line_break_on_mm_rest_targets_visible_and_last_hidden():
    visible = _measure_el()
    hidden1 = _measure_el()
    hidden2 = _measure_el()
    hidden3 = _measure_el()
    next_bar = _measure_el()
    measures_by_hash = {
        10: visible,
        11: hidden1,
        12: hidden2,
        13: hidden3,
        14: next_bar,
    }
    staff = ET.Element("Staff")
    staff.extend([visible, hidden1, hidden2, hidden3, next_bar])

    mm_rest = _rendered(10, is_mm_rest=True, mm_rest_hashes=[11, 12, 13])
    pages = [
        Page(
            lines=[
                Line(measures=[mm_rest], rm_count=1, c_count=4),
                Line(measures=[_rendered(14)], rm_count=1, c_count=1),
            ],
            is_first_page=True,
        )
    ]

    apply_pages_to_staff(staff, pages, measures_by_hash)

    assert _line_break_subtype(visible) == "line"
    assert _line_break_subtype(hidden1) is None
    assert _line_break_subtype(hidden2) is None
    assert _line_break_subtype(hidden3) == "line"
    assert _line_break_subtype(next_bar) is None


def test_page_break_on_mm_rest_targets_visible_and_last_hidden():
    visible = _measure_el()
    hidden1 = _measure_el()
    hidden2 = _measure_el()
    next_bar = _measure_el()
    measures_by_hash = {10: visible, 11: hidden1, 12: hidden2, 20: next_bar}
    staff = ET.Element("Staff")
    staff.extend([visible, hidden1, hidden2, next_bar])

    mm_rest = _rendered(10, is_mm_rest=True, mm_rest_hashes=[11, 12])
    pages = [
        Page(
            lines=[Line(measures=[mm_rest], rm_count=1, c_count=3)],
            is_first_page=True,
        ),
        Page(
            lines=[Line(measures=[_rendered(20)], rm_count=1, c_count=1)],
            is_first_page=False,
        ),
    ]

    apply_pages_to_staff(staff, pages, measures_by_hash)

    assert _line_break_subtype(visible) == "page"
    assert _line_break_subtype(hidden1) is None
    assert _line_break_subtype(hidden2) == "page"
    assert _line_break_subtype(next_bar) is None
