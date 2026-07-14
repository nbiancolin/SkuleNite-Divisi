import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mscz_formatter.mscx.load import (
    load_in,
    load_mpos_file,
    load_mscx_file,
    measure_is_mm_rest_start,
)
from mscz_formatter.mscx.models import (
    Line,
    Page,
    SourceMeasure,
    MAX_LINE_WIDTH,
    MAX_PAGE_HEIGHT,
    TITLE_BOX_OFFSET,
)

TEST_DATA_DIR = Path(__file__).resolve().parents[1] / "test-data"
SAMPLE_MSCX_DIR = TEST_DATA_DIR / "sample-mscx"
MM_RESTS_MSCX = SAMPLE_MSCX_DIR / "Test_Regular_Line_Breaks_with_mm_rests.mscx"
LINE_BREAKS_MSCX = SAMPLE_MSCX_DIR / "Test_Regular_Line_Breaks.mscx"


def _visible_source_measures(source_measures):
    return [sm for sm in source_measures if not sm.is_hidden_by_mm_rest]


def test_load_mscx_regular_line_breaks():
    _tree, measures_by_hash, source_measures = load_mscx_file(str(LINE_BREAKS_MSCX))

    assert len(source_measures) == 32
    assert len(measures_by_hash) == 32
    assert source_measures[0].num == 1
    assert source_measures[-1].num == 32
    assert all(not sm.is_mm_rest_span for sm in source_measures)
    assert all(not sm.is_hidden_by_mm_rest for sm in source_measures)

    for sm in source_measures:
        assert sm.hash_key in measures_by_hash
        assert isinstance(measures_by_hash[sm.hash_key], ET.Element)


def test_load_mscx_with_mm_rests():
    _tree, measures_by_hash, source_measures = load_mscx_file(str(MM_RESTS_MSCX))

    assert len(source_measures) == 34
    assert len(measures_by_hash) == 34

    mm_spans = [sm for sm in source_measures if sm.is_mm_rest_span]
    hidden = [sm for sm in source_measures if sm.is_hidden_by_mm_rest]

    assert len(mm_spans) == 2
    assert {sm.mm_rest_count for sm in mm_spans} == {4, 8}
    assert len(hidden) == 10

    assert source_measures[9].is_mm_rest_span and source_measures[9].mm_rest_count == 4
    assert all(source_measures[i].is_hidden_by_mm_rest for i in range(10, 13))
    assert source_measures[13].num == 11

    assert source_measures[18].is_mm_rest_span and source_measures[18].mm_rest_count == 8
    assert all(source_measures[i].is_hidden_by_mm_rest for i in range(19, 26))

    visible = _visible_source_measures(source_measures)
    assert len(visible) == 24
    assert visible[-1].num == 24


def test_measure_is_mm_rest_start():
    root = ET.parse(MM_RESTS_MSCX).getroot()
    staff = root.find("Score").findall("Staff")[0]
    measures = staff.findall("Measure")

    assert measure_is_mm_rest_start(measures[0]) == 0
    assert measure_is_mm_rest_start(measures[9]) == 4
    assert measure_is_mm_rest_start(measures[18]) == 8


def test_source_measure_detects_nested_barline():
    root = ET.parse(MM_RESTS_MSCX).getroot()
    staff = root.find("Score").findall("Staff")[0]
    measure_with_barline = next(
        measure for measure in staff.findall("Measure") if measure.find(".//BarLine") is not None
    )

    assert SourceMeasure.get_has_double_bar(measure_with_barline)


def _measure_with_spanner(spanner_xml: str) -> ET.Element:
    measure = ET.fromstring(
        f"""
        <Measure>
          <voice>
            <Chord>
              <durationType>quarter</durationType>
              {spanner_xml}
              <Note>
                <pitch>60</pitch>
                <tpc>14</tpc>
              </Note>
            </Chord>
          </voice>
        </Measure>
        """
    )
    return measure


def test_source_measure_detects_cross_bar_slur_and_tie():
    same_bar_slur = _measure_with_spanner(
        """
        <Spanner type="Slur">
          <Slur/>
          <next>
            <location>
              <fractions>1/2</fractions>
            </location>
          </next>
        </Spanner>
        """
    )
    cross_bar_slur = _measure_with_spanner(
        """
        <Spanner type="Slur">
          <Slur/>
          <next>
            <location>
              <measures>1</measures>
              <fractions>1/4</fractions>
            </location>
          </next>
        </Spanner>
        """
    )
    cross_bar_tie = ET.fromstring(
        """
        <Measure>
          <voice>
            <Chord>
              <durationType>quarter</durationType>
              <Note>
                <Spanner type="Tie">
                  <Tie/>
                  <next>
                    <location>
                      <measures>2</measures>
                    </location>
                  </next>
                </Spanner>
                <pitch>60</pitch>
                <tpc>14</tpc>
              </Note>
            </Chord>
          </voice>
        </Measure>
        """
    )
    hairpin_cross_bar = _measure_with_spanner(
        """
        <Spanner type="HairPin">
          <HairPin>
            <subtype>0</subtype>
          </HairPin>
          <next>
            <location>
              <measures>1</measures>
            </location>
          </next>
        </Spanner>
        """
    )

    assert SourceMeasure.get_outgoing_slur_or_tie_span(same_bar_slur) == 0
    assert SourceMeasure.get_outgoing_slur_or_tie_span(cross_bar_slur) == 1
    assert SourceMeasure.get_outgoing_slur_or_tie_span(cross_bar_tie) == 2
    assert SourceMeasure.get_outgoing_slur_or_tie_span(hairpin_cross_bar) == 0


def test_load_mpos_marks_slur_or_tie_into_next(tmp_path):
    """Multi-measure slur span propagates across intervening rendered bars."""
    mscx_path = tmp_path / "slur.mscx"
    mscx_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
        <museScore>
          <Score>
            <Staff>
              <Measure>
                <voice>
                  <Chord>
                    <durationType>whole</durationType>
                    <Spanner type="Slur">
                      <Slur/>
                      <next>
                        <location>
                          <measures>2</measures>
                        </location>
                      </next>
                    </Spanner>
                    <Note><pitch>60</pitch><tpc>14</tpc></Note>
                  </Chord>
                </voice>
              </Measure>
              <Measure>
                <voice>
                  <Chord>
                    <durationType>whole</durationType>
                    <Note><pitch>62</pitch><tpc>16</tpc></Note>
                  </Chord>
                </voice>
              </Measure>
              <Measure>
                <voice>
                  <Chord>
                    <durationType>whole</durationType>
                    <Spanner type="Slur">
                      <prev>
                        <location>
                          <measures>-2</measures>
                        </location>
                      </prev>
                    </Spanner>
                    <Note><pitch>64</pitch><tpc>18</tpc></Note>
                  </Chord>
                </voice>
              </Measure>
              <Measure>
                <voice>
                  <Rest durationType="measure"/>
                </voice>
              </Measure>
            </Staff>
          </Score>
        </museScore>
        """,
        encoding="utf-8",
    )
    _tree, measures_by_hash, source_measures = load_mscx_file(str(mscx_path))
    mpos_path = tmp_path / "slur.mpos"
    _write_mpos(mpos_path, len(source_measures))

    rendered = load_mpos_file(str(mpos_path), measures_by_hash, source_measures)

    assert [m.has_slur_or_tie_into_next for m in rendered] == [
        True,
        True,
        False,
        False,
    ]


def test_load_mscx_raises_without_score(tmp_path):
    invalid = tmp_path / "invalid_no_score.mscx"
    invalid.write_text('<?xml version="1.0"?><museScore><notScore/></museScore>', encoding="utf-8")

    with pytest.raises(ValueError, match="No <Score> tag"):
        load_mscx_file(str(invalid))


def _write_mpos(path: Path, count: int) -> None:
    elements = "\n".join(
        f'    <element id="{i}" x="0" y="0" sx="{1000 + i}" sy="3968.01" page="0"></element>'
        for i in range(count)
    )
    path.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<score><elements>\n{elements}\n  </elements></score>',
        encoding="utf-8",
    )


def test_load_mpos_file_matches_visible_measures(tmp_path):
    _tree, measures_by_hash, source_measures = load_mscx_file(str(MM_RESTS_MSCX))
    visible_count = len(_visible_source_measures(source_measures))

    mpos_path = tmp_path / "sample.mpos"
    _write_mpos(mpos_path, visible_count)

    rendered = load_mpos_file(str(mpos_path), measures_by_hash, source_measures)

    assert len(rendered) == visible_count
    assert rendered[0].width == 1000.0
    assert rendered[0].source_measure.num == 1
    assert rendered[9].is_mm_rest
    assert rendered[9].mm_rest_span == 4
    assert len(rendered[9].mm_rest_hashes) == 3
    assert rendered[9].width == 1009.0


def test_load_mpos_file_raises_when_too_many_elements(tmp_path):
    _tree, measures_by_hash, source_measures = load_mscx_file(str(LINE_BREAKS_MSCX))

    mpos_path = tmp_path / "too_many.mpos"
    _write_mpos(mpos_path, 40)

    with pytest.raises(ValueError, match="more rendered measures"):
        load_mpos_file(str(mpos_path), measures_by_hash, source_measures)


def test_load_in(tmp_path):
    _tree, measures_by_hash, source_measures = load_mscx_file(str(MM_RESTS_MSCX))
    visible_count = len(_visible_source_measures(source_measures))

    mpos_path = tmp_path / "sample.mpos"
    _write_mpos(mpos_path, visible_count)

    data = load_in(str(MM_RESTS_MSCX), str(mpos_path))

    assert len(data["source_measures"]) == 34
    assert len(data["rendered_measures"]) == visible_count
    assert data["rendered_measures"][0].source_measure_hash in data["measures_by_hash"]
    assert data["tree"].getroot() is not None


def test_line_width_and_validity():
    from mscz_formatter.mscx.models import RenderedMeasure

    narrow = RenderedMeasure(
        num=0,
        width=100,
        height=10,
        source_measure_hash=1,
        source_measure=SourceMeasure(num=1, hash_key=1, is_rest=False),
        has_double_bar=False,
        has_existing_line_break=False,
        has_rehearsal_mark=False,
        is_mm_rest=False,
        mm_rest_hashes=[],
    )
    fits_exactly = RenderedMeasure(
        num=1,
        width=MAX_LINE_WIDTH - 100,
        height=10,
        source_measure_hash=2,
        source_measure=SourceMeasure(num=2, hash_key=2, is_rest=False),
        has_double_bar=False,
        has_existing_line_break=False,
        has_rehearsal_mark=False,
        is_mm_rest=False,
        mm_rest_hashes=[],
    )
    too_wide = RenderedMeasure(
        num=2,
        width=MAX_LINE_WIDTH + 1,
        height=10,
        source_measure_hash=3,
        source_measure=SourceMeasure(num=3, hash_key=3, is_rest=False),
        has_double_bar=False,
        has_existing_line_break=False,
        has_rehearsal_mark=False,
        is_mm_rest=False,
        mm_rest_hashes=[],
    )

    line = Line(measures=[narrow, fits_exactly], rm_count=2, c_count=2)
    assert line.width == MAX_LINE_WIDTH
    assert line.height == 10
    assert line.is_valid()

    assert not Line(measures=[too_wide], rm_count=1, c_count=1).is_valid()


def test_page_height_and_validity():
    from mscz_formatter.mscx.models import RenderedMeasure

    small_measure = RenderedMeasure(
        num=0,
        width=100,
        height=400,
        source_measure_hash=1,
        source_measure=SourceMeasure(num=1, hash_key=1, is_rest=False),
        has_double_bar=False,
        has_existing_line_break=False,
        has_rehearsal_mark=False,
        is_mm_rest=False,
        mm_rest_hashes=[],
    )
    oversized_measure = RenderedMeasure(
        num=1,
        width=100,
        height=MAX_PAGE_HEIGHT + 1,
        source_measure_hash=2,
        source_measure=SourceMeasure(num=2, hash_key=2, is_rest=False),
        has_double_bar=False,
        has_existing_line_break=False,
        has_rehearsal_mark=False,
        is_mm_rest=False,
        mm_rest_hashes=[],
    )
    line = Line(measures=[small_measure], rm_count=1, c_count=1)

    first_page = Page(lines=[line, line], is_first_page=True)
    assert first_page.height == 800 + TITLE_BOX_OFFSET
    # height already includes TITLE_BOX_OFFSET; is_valid adds it again
    assert first_page.is_valid()

    later_page = Page(lines=[line, line], is_first_page=False)
    assert later_page.height == 800
    assert later_page.is_valid()

    oversized = Page(
        lines=[Line(measures=[oversized_measure], rm_count=1, c_count=1)],
        is_first_page=False,
    )
    assert not oversized.is_valid()
