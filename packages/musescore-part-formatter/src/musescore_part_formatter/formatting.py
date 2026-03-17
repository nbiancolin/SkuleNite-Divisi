import xml.etree.ElementTree as ET
import os, shutil

from .utils import (
    _make_part_name_text,
    _make_show_number_text,
    _make_show_title_text,
    _add_line_break_to_measure_opt,
    _add_page_break_to_measure,
    _measure_has_line_break,
    _measure_has_double_bar,
    _measure_has_rehearsal_mark,
)

from .utils import (
    CONDUCTOR_SCORE_PART_NAME,
    BROADWAY_PART_STYLE_PATH,
    BROADWAY_SCORE_STYLE_PATH,
    JAZZ_PART_STYLE_PATH,
    JAZZ_SCORE_STYLE_PATH,
)
from .utils import Style

from .file_inspect import set_style_params
from .estimating_formatting_params import predict_style_params

from logging import getLogger

LOGGER = getLogger("PartFormatter")


# UTIL FNS -- Broadway Specific Formatting
def add_broadway_header(staff: ET.Element, show_number: str, show_title: str) -> None:
    for elem in staff:
        # find first VBox
        if elem.tag == "VBox":
            elem.append(_make_show_number_text(show_number))
            elem.append(_make_show_title_text(show_title))
            return


def add_part_name(
    staff: ET.Element, part_name: str = CONDUCTOR_SCORE_PART_NAME
) -> None:
    for elem in staff:
        if elem.tag == "VBox":
            for child in elem.findall("Text"):
                style = child.find("style")
                if style is not None and style.text == "instrument_excerpt":
                    return
            elem.append(_make_part_name_text(part_name))
            return


# -- LayoutBreak formatting --
def prep_mm_rests(staff: ET.Element) -> ET.Element:
    """
    Go through each measure in score.
    if measure n has a "len" attribute: then mark that measure and the next m (m = measure->multiMeasureRest -1) measures with the "_mm" attribute
    """
    measure_to_mark = 0
    for elem in staff:
        if elem.tag == "Measure":
            if measure_to_mark > 0:
                # mark measure
                elem.attrib["_mm"] = str(measure_to_mark)  # value is dummy, never used
                measure_to_mark -= 1
            if elem.attrib.get("len"):
                measure_to_mark = int(elem.find("multiMeasureRest").text) - 1
    return staff


def cleanup_mm_rests(staff: ET.Element) -> ET.Element:
    """
    Go through entire staff, remove any "_mm" attributes
    """
    for elem in staff:
        if elem.attrib.get("_mm") is not None:
            del elem.attrib["_mm"]
    return staff


def add_rehearsal_mark_line_breaks(staff: ET.Element) -> ET.Element:
    """
    Go through each measure in the score. If there is a rehearsal mark at measure n, ad a line break to measure n-1
    if measure n-1 has a _mm attribute, go backwards until the first measure in the chain, and also add a line break

    add a line break by calling `_add_line_break_to_measure()`
    """
    for i in range(len(staff)):
        elem = staff[i]
        if elem.tag != "Measure":
            continue

        voice = elem.find("voice")
        if voice is None:
            continue

        if voice.find("RehearsalMark") is not None:
            assert i > 0
            prev_elem = staff[i - 1]
            (f"Adding Line Break to rehearsal mark at bar {i - 1}")
            _add_line_break_to_measure_opt(prev_elem)

            if prev_elem.attrib.get("_mm") is not None:
                for j in range(i - 1, -1, -1):
                    if staff[j].attrib.get("len") is not None:
                        LOGGER.debug(
                            f"Adding Line Break to start of multimeasure rest at bar {j}"
                        )
                        _add_line_break_to_measure_opt(staff[j])
                        break
    return staff


def add_double_bar_line_breaks(staff: ET.Element) -> ET.Element:
    """
    Go through each measure in the score. If there is a double bar on measure n, add a line break to measure n.
    If measure n-1 has a "_mm" attribute, go backwards until the first measure in the chain, and also add a line break.

    add a line break by calling `_add_line_break_to_measure()`

    TODO: Move this to a balancing function -- NOT here
    Additionally, set it up s.t. if there are 2 multimeasure rests together, only keep the second line break, remove the first one
        TODO: This should onlt do this if the entire section before the next rehearsal mark is a multimeasure rest
    """
    for i in range(len(staff)):
        elem = staff[i]
        if elem.tag != "Measure":
            continue

        voice = elem.find("voice")
        if voice is None:
            continue

        if voice.find("BarLine") is not None:
            assert i > 0
            prev_elem = staff[i]
            LOGGER.debug(f"Adding Line Break to double Bar line at bar {i}")
            _add_line_break_to_measure_opt(prev_elem)

    return staff


# TODO[SC-37]: make it acc work
def balance_mm_rest_line_breaks(staff: ET.Element) -> ET.Element:
    """
    Scenario: We have:
    (NewLine) RehearsalMark ->MM Rest: Rehearsal Mark: MM Rest

    We don't need a line break in the middle one, we can allow 2 MM rests in a line.
    Removes unnecessary line breaks between consecutive multi-measure rests.
    """
    prev_mm = False
    for elem in staff:
        if elem.tag != "Measure":
            continue
        is_mm = elem.attrib.get("_mm") is not None
        has_lb = elem.find("LayoutBreak") is not None
        if prev_mm and is_mm and has_lb:
            # Remove the line break from this measure
            lb = elem.find("LayoutBreak")
            if lb is not None:
                elem.remove(lb)
        prev_mm = is_mm

    return staff


def add_regular_line_breaks(staff: ET.Element, measures_per_line: int) -> ET.Element:
    """
    Go through entire score and add a line break every `measures_per_line` measures.
    Count starts at first measure and continues until an existing line break is hit, or until we reach `measures_per_line` measures,
        at which point a line break is added and the count is reset
    if a MM rest is encountered, treat the whole MM rest as a single measure

    """

    mpl_count = 0

    for measure in staff.findall("Measure"):
        mpl_count += 1

        if _measure_has_line_break(measure):
            mpl_count = 0
            continue

        if mpl_count == measures_per_line:
            mpl_count = 0
            _add_line_break_to_measure_opt(measure)
            continue

        if measure.attrib.get("_mm", False):
            mpl_count -= 1
            continue

    return staff


# TODO[SC-84]: Fix this
def new_add_page_breaks(staff: ET.Element, num_lines_per_page: int) -> ET.Element:
    """
    Add page breaks to staff to improve vertical readability.
    - Aim for NUM_LINES_PER_PAGE +/- 1 line(s) per page: NUM -1 / NUM for the first page, NUM / NUM +1 for all others
    - Favor breaks before multimeasure rests or rehearsal marks.

    Full Decision Tree: (upon encountering a line break / the end of the line)

    Are we in a multimeasure rest? (alt: Are we at the END of a multimasure rest, dont want to add a line break in the middle)
    Yes:
        Is it another MM rest after this?
        Yes:
            Iterate backwards until the start of the MM rest is reached (initial, could be well before) -- and make that one a page breal
        No:
            Add Line Break here

    No: (Not in a MM Rest)
        Is there a MM Rest after this?
        Yes:
            Add Line break here (TODO: Add V.S Text here (fast or time depending on length of MM rest))
        No:
            Is there a double bar / Rehearsal Mark here?
            Yes:
                Add Page Break here
            No:
                Do next or prev have a double bar/Rehearsal Mark?
                Yes:
                    Add page break to next/prev (whichever has the barline)
                No:
                    Add page break to prev (some default, can be changed later)


    Note about MM Rests:
    - Eyeball scenario: like 5/6 lines of notes, then 2+ lines of MM rests
        - The MM rests should go on a new page, even though
    """

    lines: list[list[ET.Element]] = [[]]

    # Build list of lines

    for measure in staff.findall("Measure"):
        lines[-1].append(measure)
        if _measure_has_line_break(measure):
            lines.append([])

    # start at 1, since first page should have 1 less line on it
    lines_on_this_page = 1
    for i in range(len(lines)):
        if i >= (len(lines) - 3):
            # Don't add a page break for the last couple lines of the score, breaks all the "looking into the future stuff"
            break

        if lines_on_this_page != num_lines_per_page:
            lines_on_this_page += 1
            continue

        lines_on_this_page = 0
        # Begin Decision Tree

        measure = lines[i][-1]

        if measure.attrib.get("_mm") is not None:
            if lines[i + 1][0].attrib.get("mm") is not None:
                for j in range(i):
                    line = lines[j]
                    for m in line:
                        if m.attrib.get("_mm") is None:
                            # Finally found a line that doesnt h
                            # add page break to last bar in eseries
                            _add_page_break_to_measure(line[-1])

            else:
                _add_page_break_to_measure(measure)

        else:
            next_line = lines[i + 1]
            if next_line[0].attrib.get("_mm") is not None:
                _add_page_break_to_measure(measure)
                # TODO[SC-XXX]: Add "V.S." Text to this measure

            else:
                if _measure_has_double_bar(measure) or _measure_has_rehearsal_mark(
                    lines[i + 1][0]
                ):
                    _add_page_break_to_measure(measure)

                else:
                    if _measure_has_double_bar(
                        lines[i + 1][-1]
                    ) or _measure_has_rehearsal_mark(lines[i + 2][0]):
                        _add_page_break_to_measure(lines[i + 1][-1])
                    elif _measure_has_double_bar(
                        lines[i - 1][-1]
                    ) or _measure_has_rehearsal_mark(lines[i][0]):
                        _add_page_break_to_measure(lines[i][-1])
                    else:
                        LOGGER.info(
                            "[add_page_breaks] Reached default case for adding page breaks"
                        )
                        # TODO: Define default case somewhere?
                        _add_page_break_to_measure(measure)

    return staff


def add_page_breaks(staff: ET.Element) -> ET.Element:
    """
    Add page breaks to staff to improve vertical readability.
    - Aim for 7–9 lines per page: 7–8 for first page, 8–9 for others.
    - Favor breaks before multimeasure rests or rehearsal marks.
    """

    def is_line_break(measure):
        return (
            measure.find("LayoutBreak") is not None
            and measure.attrib.get("_mm") is None
        )

    def has_rehearsal_mark(measure):
        voice = measure.find("voice")
        return (
            voice is not None
            and voice.find("RehearsalMark") is not None
            and measure.attrib.get("_mm") is not None
        )

    def choose_best_break(
        first_elem, second_elem, first_index, second_index, lines_on_page
    ):
        LOGGER.debug(f"Page had {lines_on_page} lines before break.")
        next_first = staff[first_index + 1] if first_index + 1 < len(staff) else None
        next_second = staff[second_index + 1] if second_index + 1 < len(staff) else None

        # Prefer break before a rehearsal mark
        if next_second is not None and has_rehearsal_mark(next_second):
            _add_page_break_to_measure(second_elem)
            LOGGER.debug("1")
            return 0
        elif next_first is not None and has_rehearsal_mark(next_first):
            _add_page_break_to_measure(second_elem)
            LOGGER.debug("2")
            return 0
        # Prefer multimeasure rest (BarLine is a proxy for that)
        elif first_elem.find("BarLine") is not None:
            _add_page_break_to_measure(first_elem)
            LOGGER.debug("3")
            return 1
        elif second_elem.find("BarLine") is not None:
            _add_page_break_to_measure(second_elem)
            LOGGER.debug("4")
            return 0
        else:
            _add_page_break_to_measure(first_elem)
            LOGGER.debug("3")
            return 1

        LOGGER.debug("added page break")

    num_line_breaks_per_page = 0
    first_page = True
    first_elem, second_elem = None, None
    first_index, second_index = -1, -1

    for i, elem in enumerate(staff):
        if elem.tag != "Measure":
            LOGGER.debug("non-measure tag")
            continue

        cutoff = 7 if first_page else 8

        if is_line_break(elem):
            num_line_breaks_per_page += 1

        if num_line_breaks_per_page == cutoff:
            if first_elem is None:
                first_elem, first_index = elem, i
                num_line_breaks_per_page -= 1  # Keep counting for second option
                continue
            else:
                second_elem, second_index = elem, i
                res = choose_best_break(
                    first_elem,
                    second_elem,
                    first_index,
                    second_index,
                    num_line_breaks_per_page + 1,
                )

                # Reset state
                num_line_breaks_per_page = res
                first_page = False
                first_elem = second_elem = None
                first_index = second_index = -1
    return staff


def final_pass_through(staff: ET.Element) -> ET.Element:
    """
    Adjusts poorly balanced lines. If a line has only 2 measures and the previous has 4+:
    - If prev has 4: remove the break before it.
    - If prev has >4: remove the break and move it to the midpoint.
    """
    lines = []
    current_line = []

    for elem in staff:
        if elem.tag != "Measure":
            continue
        current_line.append(elem)
        if any(child.tag == "LayoutBreak" for child in elem):
            lines.append(current_line)
            current_line = []
    if current_line:
        lines.append(current_line)

    for idx in range(1, len(lines)):
        this_line = lines[idx]
        prev_line = lines[idx - 1]
        if len(this_line) <= 2:
            if len(prev_line) == 4:
                for elem in reversed(prev_line):
                    lb = next(
                        (child for child in elem if child.tag == "LayoutBreak"), None
                    )
                    if lb is not None:
                        elem.remove(lb)
                        break
            elif len(prev_line) > 4:
                for elem in reversed(prev_line):
                    lb = next(
                        (child for child in elem if child.tag == "LayoutBreak"), None
                    )
                    if lb is not None:
                        elem.remove(lb)
                        break
                split_index = len(prev_line) // 2
                _add_line_break_to_measure_opt(prev_line[split_index])
    return staff


# TODO[SC-43]: Modify it so that the score style is selected based on the # of instruments
# UPDATE TO ABOVE: Instead of hardcoding values, load in the styles file, and using the # of instruments
#   Determine a staff spacing value wrt the page size (letter), orientation (vertical or horizontal), # of instruments, and
def add_styles_to_score_and_parts(style: Style, work_dir: str, score_info=None) -> None:
    """
    Depending on what style enum is selected, load either the jazz or broadway style file.

    Go through temp directory, replace any "style" .mss parts with the selected style file.
    This includes both the main score and individual part style files.
    """

    # Determine style files
    if style == Style.BROADWAY:
        score_style_path = BROADWAY_SCORE_STYLE_PATH
        part_style_path = BROADWAY_PART_STYLE_PATH
    elif style == Style.JAZZ:
        score_style_path = JAZZ_SCORE_STYLE_PATH
        part_style_path = JAZZ_PART_STYLE_PATH
    else:
        raise ValueError(f"Unsupported style: {style}")

    # Walk through files in temp directory
    for root, _, files in os.walk(work_dir):
        for filename in files:
            if not filename.lower().endswith(".mss"):
                continue

            full_path = os.path.join(root, filename)
            # Get relative path from work_dir to check if it's inside "excerpts/"
            rel_path = os.path.relpath(full_path, work_dir)
            is_excerpt = "Excerpts" in rel_path

            if is_excerpt:
                #For now, assuming all parts contain 1 instrument
                source_style = part_style_path
                style_params = predict_style_params({
                    "num_staves": 1,
                })
            else:
                source_style = score_style_path
                style_params = predict_style_params(score_info)
            
            with open(source_style, "r") as f:
                style_text = f.read()
                style_text = set_style_params(
                    style_text, 
                    **style_params
                )  

                with open(full_path, "w") as out_f:
                    out_f.write(style_text)

            LOGGER.info(
                f"Replaced {'part' if is_excerpt else 'score'} style: {full_path}"
            )
