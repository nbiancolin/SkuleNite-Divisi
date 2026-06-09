import xml.etree.ElementTree as ET

import pytest

from musescore_part_formatter.formatting import (
    _multimeasure_rest_span_count,
    prep_mm_rests,
)


def _staff_xml(inner: str) -> ET.Element:
    return ET.fromstring(f"<Staff>{inner}</Staff>")


def test_multimeasure_rest_span_count_from_tag():
    staff = _staff_xml(
        """
        <Measure><voice><Rest><duration>4/4</duration></Rest></voice></Measure>
        <Measure len="16/4"><multiMeasureRest>4</multiMeasureRest></Measure>
        """
    )
    mm_measure = staff.findall("Measure")[1]
    assert _multimeasure_rest_span_count(mm_measure, staff) == 4


def test_multimeasure_rest_span_count_from_len_when_tag_missing():
    staff = _staff_xml(
        """
        <Measure><voice><Rest><duration>4/4</duration></Rest></voice></Measure>
        <Measure len="16/4"><voice><Rest><duration>16/4</duration></Rest></voice></Measure>
        """
    )
    mm_measure = staff.findall("Measure")[1]
    assert _multimeasure_rest_span_count(mm_measure, staff) == 4


def test_prep_mm_rests_marks_following_measures_without_multimeasure_rest_tag():
    staff = _staff_xml(
        """
        <Measure><voice><Rest><duration>4/4</duration></Rest></voice></Measure>
        <Measure len="12/4"><voice><Rest><duration>12/4</duration></Rest></voice></Measure>
        <Measure><voice><Rest><duration>4/4</duration></Rest></voice></Measure>
        <Measure><voice><Rest><duration>4/4</duration></Rest></voice></Measure>
        <Measure><voice><Rest><duration>4/4</duration></Rest></voice></Measure>
        """
    )
    prep_mm_rests(staff)
    measures = staff.findall("Measure")
    assert "_mm" not in measures[0].attrib
    assert measures[1].attrib.get("len") == "12/4"
    assert measures[2].attrib.get("_mm") is not None
    assert measures[3].attrib.get("_mm") is not None
    assert "_mm" not in measures[4].attrib