"""
File for formatting measures into lines
"""
from mscz_formatter.mscx.models import Line, RenderedMeasure

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mscz_formatter.mscx.load import MusescoreFileData

# TODO[SC-XX]: allow for this to be set by the user
MEASURES_PER_LINE = 6
# Hard-coded fallback when mpl does not divide evenly (see formatting-rules.md)
ALTERNATE_LINE_LENGTH = 4


def _new_line() -> Line:
    return Line(measures=[], rm_count=0, c_count=0)


def _flush_line(lines: list[Line], line: Line) -> Line:
    if line.measures:
        lines.append(line)
    return _new_line()


def _conceptual_length_fits(c_count: int) -> bool:
    return (
        c_count % MEASURES_PER_LINE == 0
        or c_count % ALTERNATE_LINE_LENGTH == 0
    )



def generate_lines(rendered_measures: list[RenderedMeasure]) -> list[Line]:
    res: list[Line] = []
    i = 0
    ub = len(rendered_measures)
    curr_line = _new_line()

    while i < ub:
        m = rendered_measures[i]

        if m.is_mm_rest:
            span = m.mm_rest_span or 0
            if not curr_line.measures:
                if i + 1 < ub and rendered_measures[i + 1].is_mm_rest:
                    curr_line.add_measure(m)
                    curr_line.add_measure(rendered_measures[i + 1])
                    i += 2
                elif span % MEASURES_PER_LINE == 0:
                    curr_line.add_measure(m)
                    i += 1
                    curr_line = _flush_line(res, curr_line)
                else:
                    curr_line.add_measure(m)
                    i += 1
            elif curr_line.c_count % MEASURES_PER_LINE == 0:
                curr_line.add_measure(m)
                i += 1
                if _conceptual_length_fits(curr_line.c_count):
                    curr_line = _flush_line(res, curr_line)
            elif _conceptual_length_fits(curr_line.c_count + span):
                curr_line.add_measure(m)
                i += 1
                curr_line = _flush_line(res, curr_line)
            else:
                curr_line = _flush_line(res, curr_line)
                curr_line.add_measure(m)
                i += 1
        elif m.has_rehearsal_mark:
            curr_line = _flush_line(res, curr_line)
            curr_line.add_measure(m)
            i += 1
        elif m.has_double_bar:
            curr_line.add_measure(m)
            i += 1
            if _conceptual_length_fits(curr_line.c_count):
                curr_line = _flush_line(res, curr_line)
        else:
            curr_line.add_measure(m)
            i += 1
            if curr_line.c_count % MEASURES_PER_LINE == 0:
                curr_line = _flush_line(res, curr_line)

    _flush_line(res, curr_line)
    return res




def balance_and_validate_lines(lines: list[Line]):
    pass
