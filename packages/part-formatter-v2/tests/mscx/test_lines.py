from mscz_formatter.mscx.lines import (
    ALTERNATE_LINE_LENGTH,
    MEASURES_PER_LINE,
    generate_lines,
)
from mscz_formatter.mscx.models import RenderedMeasure, SourceMeasure


def _measure(
    num: int,
    *,
    is_mm_rest: bool = False,
    mm_rest_span: int | None = None,
    has_double_bar: bool = False,
    has_rehearsal_mark: bool = False,
    has_slur_or_tie_into_next: bool = False,
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
        has_slur_or_tie_into_next=has_slur_or_tie_into_next,
    )


def _line_c_counts(lines) -> list[int]:
    return [line.c_count for line in lines]


def _assert_rehearsal_marks_start_lines(lines) -> None:
    """Prefer: every non-consecutive RM opens its line (soft, not hard)."""
    for line in lines:
        for i, m in enumerate(line.measures):
            if not m.has_rehearsal_mark:
                continue
            if i == 0:
                continue
            assert line.measures[i - 1].has_rehearsal_mark, (
                f"M{m.num}R is mid-line without a preceding RM"
            )


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
    """Consecutive MM rests at a line start stay together; when they sum to
    mpl the paired boost prefers ending there rather than absorbing trailing
    music onto the same line."""
    measures = [
        _measure(1, is_mm_rest=True, mm_rest_span=4),
        _measure(5, is_mm_rest=True, mm_rest_span=2),
        _measure(7),
        _measure(8),
    ]
    lines = generate_lines(measures)

    assert lines[0].c_count == MEASURES_PER_LINE
    assert [m.is_mm_rest for m in lines[0].measures] == [True, True]
    assert lines[1].c_count == 2
    assert not any(m.is_mm_rest for m in lines[1].measures)


def test_paired_mm_rests_share_line_when_combined_span_is_multiple_of_mpl():
    """Two consecutive MM rests whose spans sum to 2*mpl should share a line
    (boost) rather than splitting after an alternate-aligned first rest."""
    measures = [
        _measure(1, is_mm_rest=True, mm_rest_span=8),
        _measure(9, is_mm_rest=True, mm_rest_span=4),
        *[_measure(i) for i in range(13, 19)],
    ]
    lines = generate_lines(measures)

    assert lines[0].c_count == MEASURES_PER_LINE * 2
    assert len(lines[0].measures) == 2
    assert all(m.is_mm_rest for m in lines[0].measures)


def test_paired_mm_rests_at_mpl_sum_prefer_own_line():
    """4+2 MM rests (c=mpl) should sit alone on a line, then music at mpl."""
    measures = [
        _measure(1, is_mm_rest=True, mm_rest_span=4),
        _measure(5, is_mm_rest=True, mm_rest_span=2),
        *[_measure(i) for i in range(7, 19)],
    ]
    lines = generate_lines(measures)

    assert lines[0].c_count == MEASURES_PER_LINE
    assert [m.is_mm_rest for m in lines[0].measures] == [True, True]
    assert _line_c_counts(lines) == [
        MEASURES_PER_LINE,
        MEASURES_PER_LINE,
        MEASURES_PER_LINE,
    ]


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
    _assert_rehearsal_marks_start_lines(lines)


def test_rehearsal_mark_after_near_mpl_mm_rest_starts_new_line():
    """5-bar MM rest must not absorb the next bar just to reach mpl=6 when
    that next bar has a rehearsal mark (violin M6*(5)+M7R bug)."""
    measures = [
        _measure(6, is_mm_rest=True, mm_rest_span=5),
        _measure(7, has_rehearsal_mark=True),
        _measure(8),
        _measure(9),
        _measure(10),
        _measure(11),
        _measure(12),
    ]
    lines = generate_lines(measures)

    assert lines[0].c_count == 5
    assert lines[0].measures[0].is_mm_rest
    assert lines[1].measures[0].has_rehearsal_mark
    assert lines[1].measures[0].num == 7
    _assert_rehearsal_marks_start_lines(lines)


def test_rehearsal_mark_after_eight_bars_prefers_four_and_four():
    """8 bars between RMs should be 4+4, not mpl=6 then a 2-bar orphan."""
    measures = [
        _measure(1, has_double_bar=True),
        _measure(2, has_rehearsal_mark=True),
        *[_measure(i) for i in range(3, 10)],
        _measure(10, has_rehearsal_mark=True),
        *[_measure(i) for i in range(11, 16)],
    ]
    lines = generate_lines(measures)

    _assert_rehearsal_marks_start_lines(lines)
    m10_idx = next(
        i for i, line in enumerate(lines) if line.measures[0].num == 10
    )
    assert lines[m10_idx].measures[0].has_rehearsal_mark
    assert lines[m10_idx - 1].measures[-1].num == 9
    assert lines[m10_idx - 1].c_count >= ALTERNATE_LINE_LENGTH - 1
    # Pickup double bar before M2R should be its own line or continued —
    # but M2R should still open a line under the soft RM preference.
    m2_line = next(
        line for line in lines if any(m.num == 2 for m in line.measures)
    )
    assert m2_line.measures[0].num == 2


def test_rm_between_mm_rests_keeps_marks_starting_lines():
    """Reed-2: no buried RMs; over-mpl only when a line contains an MM rest."""
    measures = [
        _measure(6, is_mm_rest=True, mm_rest_span=5),
        _measure(7, has_rehearsal_mark=True),
        _measure(8, is_mm_rest=True, mm_rest_span=2, has_rehearsal_mark=True),
        _measure(9, has_slur_or_tie_into_next=True),
        _measure(10),
        _measure(11),
        _measure(12, is_mm_rest=True, mm_rest_span=2, has_double_bar=True),
        _measure(13, has_rehearsal_mark=True),
        _measure(14, is_mm_rest=True, mm_rest_span=4, has_rehearsal_mark=True),
        _measure(15),
        _measure(16),
    ]
    lines = generate_lines(measures)

    _assert_rehearsal_marks_start_lines(lines)
    for line in lines:
        if line.c_count > MEASURES_PER_LINE:
            assert any(m.is_mm_rest for m in line.measures)
    m7_line = next(line for line in lines if any(m.num == 7 for m in line.measures))
    assert m7_line.measures[0].num == 7


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


def test_short_mm_rest_packs_trailing_music_even_if_not_aligned():
    """Reed 3: [RM + 3-bar MM] | [3 music w/ slur] should share one line.

    Combined c=7 is past mpl and not 4-aligned, but width fits and breaking
    at mpl would cut the slur — so over-mpl MM packing must be allowed.
    """
    measures = [
        _measure(4, has_rehearsal_mark=True),
        _measure(5, is_mm_rest=True, mm_rest_span=3, has_rehearsal_mark=True),
        _measure(6),
        _measure(7, has_slur_or_tie_into_next=True),
        _measure(8, has_double_bar=True),
        _measure(9, has_rehearsal_mark=True),
        *[_measure(i) for i in range(10, 13)],
    ]
    lines = generate_lines(measures)

    packed = next(line for line in lines if any(m.num == 5 for m in line.measures))
    assert [m.num for m in packed.measures] == [4, 5, 6, 7, 8]
    assert packed.c_count == 7
    assert packed.measures[1].is_mm_rest
    assert not any(
        line.measures[-1].has_slur_or_tie_into_next for line in lines[:-1]
    )
    _assert_rehearsal_marks_start_lines(lines)


def test_avoids_line_break_across_slur_or_tie():
    """mpl would split after M6; a slur into M7 should prefer 4+4 instead."""
    measures = [
        *[_measure(i) for i in range(1, 6)],
        _measure(6, has_slur_or_tie_into_next=True),
        _measure(7),
        _measure(8),
    ]
    lines = generate_lines(measures)

    assert _line_c_counts(lines) == [4, 4]
    assert lines[0].measures[-1].num == 4
    assert not any(
        line.measures[-1].has_slur_or_tie_into_next for line in lines[:-1]
    )


def test_slur_across_double_bar_overrides_double_bar_boost():
    """Double bars normally invite a break; a slur across that barline wins."""
    measures = [
        *[_measure(i) for i in range(1, 6)],
        _measure(6, has_double_bar=True, has_slur_or_tie_into_next=True),
        _measure(7),
        _measure(8),
    ]
    lines = generate_lines(measures)

    assert _line_c_counts(lines) == [4, 4]
    assert lines[0].measures[-1].num == 4
