from mscz_formatter.mscx.lines import MEASURES_PER_LINE, generate_lines
from mscz_formatter.mscx.models import RenderedMeasure, SourceMeasure


def _measure(
    num: int,
    *,
    is_mm_rest: bool = False,
    mm_rest_span: int | None = None,
    has_double_bar: bool = False,
    has_rehearsal_mark: bool = False,
) -> RenderedMeasure:
    return RenderedMeasure(
        num=num,
        width=100,
        height=10,
        source_measure_hash=num,
        source_measure=SourceMeasure(num=num, hash_key=num, is_rest=False),
        has_double_bar=has_double_bar,
        has_existing_line_break=False,
        has_rehearsal_mark=has_rehearsal_mark,
        is_mm_rest=is_mm_rest,
        mm_rest_hashes=[],
        mm_rest_span=mm_rest_span,
    )


def _line_c_counts(lines) -> list[int]:
    return [line.c_count for line in lines]


def test_regular_measures_break_at_mpl():
    measures = [_measure(i) for i in range(13)]
    lines = generate_lines(measures)

    assert len(lines) == 3
    assert _line_c_counts(lines) == [MEASURES_PER_LINE, MEASURES_PER_LINE, 1]


def test_trailing_measures_are_not_dropped():
    measures = [_measure(i) for i in range(4)]
    lines = generate_lines(measures)

    assert len(lines) == 1
    assert lines[0].c_count == 4
    assert len(lines[0].measures) == 4


def test_consecutive_mm_rests_at_line_start_do_not_break():
    measures = [
        _measure(1, is_mm_rest=True, mm_rest_span=4),
        _measure(5, is_mm_rest=True, mm_rest_span=2),
        _measure(7),
        _measure(8),
    ]
    lines = generate_lines(measures)

    assert len(lines) == 1
    assert lines[0].c_count == 8
    assert len(lines[0].measures) == 4


def test_mm_rest_multiple_of_mpl_breaks_at_line_start():
    measures = [
        _measure(1, is_mm_rest=True, mm_rest_span=MEASURES_PER_LINE),
        _measure(7),
    ]
    lines = generate_lines(measures)

    assert len(lines) == 2
    assert lines[0].c_count == MEASURES_PER_LINE
    assert lines[1].c_count == 1


def test_mm_rest_at_end_of_score_is_included():
    measures = [_measure(1), _measure(2, is_mm_rest=True, mm_rest_span=3)]
    lines = generate_lines(measures)

    assert sum(line.c_count for line in lines) == 4
    assert lines[-1].measures[-1].is_mm_rest


def test_rehearsal_mark_starts_new_line():
    measures = [_measure(i) for i in range(3)] + [
        _measure(3, has_rehearsal_mark=True),
        _measure(4),
    ]
    lines = generate_lines(measures)

    assert len(lines) == 2
    assert lines[0].c_count == 3
    assert lines[1].measures[0].has_rehearsal_mark


def test_mm_rest_mid_line_breaks_before_when_misaligned():
    measures = [_measure(i) for i in range(5)] + [
        _measure(5, is_mm_rest=True, mm_rest_span=2),
    ]
    lines = generate_lines(measures)

    assert len(lines) == 2
    assert lines[0].c_count == 5
    assert lines[1].c_count == 2


def test_mm_rest_mid_line_breaks_after_when_span_aligns_to_four():
    measures = [_measure(i) for i in range(5)] + [
        _measure(5, is_mm_rest=True, mm_rest_span=3),
    ]
    lines = generate_lines(measures)

    assert len(lines) == 1
    assert lines[0].c_count == 8
