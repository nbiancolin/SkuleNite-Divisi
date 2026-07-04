"""
File for formatting measures into lines
"""
from mscz_formatter.mscx.models import Line, RenderedMeasure

from typing import TYPE_CHECKING
from logging import getLogger

if TYPE_CHECKING:
    from mscz_formatter.mscx.load import MusescoreFileData

#TODO[SC-XX]: allow for this to be set by the user
MEASURES_PER_LINE = 6

LOGGER = getLogger(__name__)


def generate_optimal_line(rendered_measures: list[RenderedMeasure]) -> tuple[Line, int]:
    """ 
    Second attempt to see if we can do this better
    Build a preliminary optimal line from the start of rendered_measres
    """

    res = Line(measures=[], rm_count=0, c_count=0)
    i = 0
    while i < len(rendered_measures):
        m = rendered_measures[i]
        if m.is_mm_rest and res.c_count == 0:
            if rendered_measures[i +1].is_mm_rest and rendered_measures[i +1].mm_rest_span % MEASURES_PER_LINE == 0:
                res.add_measure(m)
                res.add_measure(rendered_measures[i +1])
                i += 1
                break
            else:
                res.add_measure(m)
                break
        if m.is_mm_rest is False: 
            res.add_measure(m)
            if res.rm_count == MEASURES_PER_LINE:
                #done
                break
            else:
                i += 1
                continue

                
            


    return (res, i +1)



def generate_lines(rendered_measures: list[RenderedMeasure]) -> list[Line]:
    res: list[Line] = []

    i = 0
    c_counter = 0
    ub = len(rendered_measures)

    curr_line = Line(measures=[], rm_count=0, c_count=0)

    while i < ub:
        m = rendered_measures[i]
        if m.is_mm_rest:
            if len(curr_line.measures) == 0:
                try:
                    next_measure = rendered_measures[i +1]
                except Exception as e:
                    # at end of show, don't add line break
                    LOGGER.warning(f"Encountered key error, this is likely because we hit the end of the mscx: {e}")
                    break
            
                if next_measure.is_mm_rest:
                    curr_line.add_measure(m)
                    curr_line.add_measure(next_measure)

                    i += 2

                    #line break
                    res.append(curr_line)
                    curr_line = Line(measures=[], rm_count=0, c_count=0)
                
                elif m.mm_rest_span % MEASURES_PER_LINE == 0:
                    curr_line.add_measure(m)

                    i += 1
                    # line break
                    res.append(curr_line)
                    curr_line = Line(measures=[], rm_count=0, c_count=0)

                else:
                    #don't add break
                    curr_line.add_measure(m)
                    i += 1
                    #continue
            # Else: not on a new line
            else:
                if (curr_line.c_count + m.mm_rest_span) % MEASURES_PER_LINE == 0 or (curr_line.c_count + m.mm_rest_span) % 4 == 0:
                    curr_line.add_measure(m)
                    i += 1
                    #line break
                    res.append(curr_line)
                    curr_line = Line(measures=[], rm_count=0, c_count=0)
                else:
                    # add line break before and start this on ne line (we can balance it later)
                    res.append(curr_line)
                    if len(curr_line.measures) != 0:
                        # add line break
                        res.append(curr_line)
                        curr_line = Line(measures=[], rm_count=0, c_count=0)

                    curr_line.add_measure(m)
                    i += 1
        
        # Else: Not a MM Rest
        else:
            # if line is double bar or rehearsal mark, add line breaks
            if m.has_rehearsal_mark:
                # line break then add on new line
                res.append(curr_line)
                curr_line = Line(measures=[], rm_count=0, c_count=0)

                curr_line.add_measure(m)
                i += 1
            
            elif m.has_double_bar:
                curr_line.add_measure(m)
                i += 1

                if curr_line.c_count % MEASURES_PER_LINE == 0 or curr_line.c_count % 4 == 0:
                    # add the line break
                    res.append(curr_line)
                    curr_line = Line(measures=[], rm_count=0, c_count=0)


            # if length of line is mpl, then add line break, otherwise continue
            else:
                curr_line.add_measure(m)
                i += 1
                if curr_line.c_count % MEASURES_PER_LINE == 0:
                    res.append(curr_line)
                    curr_line = Line(measures=[], rm_count=0, c_count=0)

    return res




def balance_and_validate_lines(lines: list[Line]):
    pass