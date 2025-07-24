import sys
import xml.etree.ElementTree as ET
import zipfile
import os
import shutil
from enum import Enum

from django.conf import settings

NUM_MEASURES_PER_LINE = (
    6  # TODO[SC-42]: Make this a function of the time signature somehow?
)

STYLES_DIR = f"{settings.STATIC_ROOT}/_styles"
TEMP_DIR = f"{settings.MEDIA_ROOT}/temp" 


class Style(Enum):
    BROADWAY = "broadway"
    JAZZ = "jazz"


SHOW_TITLE = "MyShow"
SHOW_NUMBER = "1-1"


SHOW_TITLE = "MyShow"
SHOW_NUMBER = "1-1"


# -- HELPER FUNCTIONS --
def _make_show_number_text(show_number: str) -> ET.Element:
    txt = ET.Element("Text")
    style = ET.SubElement(txt, "style")
    style.text = "user_2"
    text = ET.SubElement(txt, "text")
    text.text = show_number
    return txt


def _make_show_title_text(show_title: str) -> ET.Element:
    txt = ET.Element("Text")
    style = ET.SubElement(txt, "style")
    style.text = "user_3"
    text = ET.SubElement(txt, "text")
    text.text = show_title
    return txt


def _make_part_name_text(part_name: str) -> ET.Element:
    txt = ET.Element("Text")
    style = ET.SubElement(txt, "style")
    style.text = "instrument_excerpt"
    text = ET.SubElement(txt, "text")
    text.text = part_name
    return txt


def _make_line_break() -> ET.Element:
    lb = ET.Element("LayoutBreak")
    subtype = ET.SubElement(lb, "subtype")
    subtype.text = "line"
    return lb


def _make_page_break() -> ET.Element:
    pb = ET.Element("LayoutBreak")
    subtype = ET.SubElement(pb, "subtype")
    subtype.text = "page"
    return pb


def _make_double_bar() -> ET.Element:
    db = ET.Element("BarLine")
    subtype = ET.SubElement(db, "subtype")
    subtype.text = "double"
    linked = ET.SubElement(db, "Linked")
    linked.text = "\n"
    return db


def _add_line_break_to_measure(measure: ET.Element) -> None:
    index = 0
    for elem in measure:
        if elem.tag == "voice":
            break
        index += 1
    measure.insert(index, _make_line_break())


def _add_line_break_to_measure_opt(measure: ET.Element) -> None:
    if measure.find("LayoutBreak") is not None:
        return
    _add_line_break_to_measure(measure)

def _remove_line_break_from_measure(measure: ET.Element) -> None:
    lb = measure.find("LayoutBreak")
    if lb is not None:
        measure.remove(lb)


def _add_page_break_to_measure(measure: ET.Element) -> None:
    # if line break already there, replace with a page break
    if measure.find("LayoutBreak") is not None:
        measure.find("LayoutBreak").find("subtype").text = "page"
        return

    print("added a page break to a bar that did not have a line break!")
    index = 0
    for elem in measure:
        if elem.tag == "voice":
            break
        index += 1

    measure.insert(index, _make_page_break())


def _add_double_bar_to_measure(measure: ET.Element) -> None:
    # Add the double bar as the very last tag in the measure
    measure.append(_make_double_bar())


# -- Broadway specific formatting
def add_broadway_header(staff: ET.Element, show_number: str, show_title: str) -> None:
    for elem in staff:
        # find first VBox
        if elem.tag == "VBox":
            elem.append(_make_show_number_text(show_number))
            elem.append(_make_show_title_text(show_title))
            return


def add_part_name(staff: ET.Element, part_name: str = "CONDUCTOR SCORE") -> None:
    for elem in staff:
        if elem.tag == "VBox":
            for child in elem.findall("Text"):
                style = child.find("style")
                if style is not None and style.text == "instrument_excerpt":
                    return
            elem.append(_make_part_name_text(part_name))
            return


# -- LayoutBreak formatting --
def strip_existing_linebreaks(staff: ET.Element) -> ET.Element:
    """
    Go through each measure in score. If measure has a linebreak (or pagebreak), remove it, so that it doesnt interfere
    """
    #TODO[SC-XX]: Set this up so that it keeps these, and does the line break formatting around them
    for elem in staff:
        if elem.tag == "Measure":
            lb = elem.find("LayoutBreak")
            if lb is not None:
                elem.remove(lb)
    return staff


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
            print(f"Adding Line Break to rehearsal mark at bar {i - 1}")
            _add_line_break_to_measure_opt(prev_elem)

            if prev_elem.attrib.get("_mm") is not None:
                for j in range(i - 1, -1, -1):
                    if staff[j].attrib.get("len") is not None:
                        print(
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
            print(f"Adding Line Break to double Bar line at bar {i}")
            _add_line_break_to_measure_opt(prev_elem)

    return staff


# TODO[SC-37]: make it acc work
# TODO: I think this is broken, fix
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
    We want to add a line break every `measures_per_line` measures.
    This does not include multi measure rests, these should be ignored.
    """
    i = 0
    for elem in staff:
        if elem.tag != "Measure":
            print("Non measure tag encountered")
            continue

        if (
            elem.find("voice") is not None
            and elem.find("voice").find("RehearsalMark") is not None
        ):
            i = 1

        if (
            elem.find("voice") is not None
            and elem.find("voice").find("BarLine") is not None
        ):
            i = 0

        if elem.attrib.get("_mm") is not None:
            if i > 0:
                # TODO: add line break to bar before
                print(
                    "Could have added a line break"
                )  # Manual testing indicates otherwise ...
            i = 0
        else:
            if i == (measures_per_line) and elem.find("LayoutBreak") is None:
                print("Adding Regular Line Break")
                _add_line_break_to_measure(elem)
                i = 0
            else:
                i += 1

    return staff


def add_page_breaks(staff: ET.Element) -> ET.Element:
    """
    Add page breaks to staff to improve vertical readability.
    - Aim for 7–9 lines per page: 7–8 for first page, 8–9 for others.
    - Favor breaks before multimeasure rests or rehearsal marks.

    TODO: If chart is a piano chart (or something with miltiple staves), numbers should be smaller
    Need to also make it so that it hides empty staves
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
    
    def has_double_bar(measure):
        voice = measure.find("voice")
        return (
            voice is not None
            and voice.find("BarLine") is not None
            and measure.attrib.get("_mm") is not None
        )

    def choose_best_break(
        first_elem, second_elem, first_index, second_index, lines_on_page
    ):
        print(f"Page had {lines_on_page} lines before break.")
        next_first = staff[first_index + 1] if first_index + 1 < len(staff) else None
        next_second = staff[second_index + 1] if second_index + 1 < len(staff) else None

        first_option = (first_elem, next_first)
        second_option = (second_elem, next_second)

        #Check if line break would put a MM rest on new page (best case)
        if first_option[1] is not None and first_option[1].attrib.get("_mm") is not None:
            _add_page_break_to_measure(first_option[0])
            return 1
        elif second_option[1] is not None and second_option[1].attrib.get("_mm") is not None:
            _add_page_break_to_measure(second_option[0])
            return 0

        #then, prefer if we can put a rehearsal mark on a new page
        if first_option[1] is not None and (has_rehearsal_mark(first_option[1]) or has_double_bar(first_option[0])):
            _add_page_break_to_measure(first_option[0])
            return 1
        elif second_option[1] is not None and (has_rehearsal_mark(second_option[1]) or has_double_bar(second_option[0])):
            _add_page_break_to_measure(second_option[0])
            return 0
        
        else:
            print("Oops, couldn't find a good spot, adding a page break to first one")
            _add_page_break_to_measure(first_option[0])
            return 1


    num_line_breaks_per_page = 0
    first_page = True
    first_elem, second_elem = None, None
    first_index, second_index = -1, -1

    for i, elem in enumerate(staff):
        if elem.tag != "Measure":
            print("non-measure tag")
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

def new_final_pass_through(staff: ET.Element) -> ET.Element:
    """
    Adjusts poorly balanced lines. 
    Use 3 pointers, one points to the start of the first line (initial), 
    first points to the end of the "first" line, and 
    "second" points to the end of the second line

    if "first" has a double bar on it, or a rehearsal mark on the bar after it, we are skipping this iteration
    -> first is given the value of second, and continue looking until you find second

    if len from initial to first (line1_len) is >=4, and len from (first +1) to second (line2_len) is <= 2,
    - If prev has 4: remove the break before it.
    - If prev has >4: remove the break and move it to the midpoint.

    TODO: (future Ticket) as above, but if theres a slur going over the bar, remove current line brek

    len = second - first + 1
    """

    print("louygugkutyfgkytgfkytgfkjyt")

    initial = None
    first = None
    second = None

    for i in range(len(staff)):
        elem = staff[i]
        if elem.tag != "Measure":
            continue

        if initial == None:
            initial = i

        if any(child.tag == "BarLine" for child in elem) and first is not None:
            #reset the count, set initial to the bar after
            initial = i +1
            first = None
            second = None
            continue

        if any(child.tag == "RehearsalMark" for child in elem):
            #reset the count, set initial for current bar
            initial = i
            first = None
            second = None
            continue
        

        if second is None:
            #continue looking until we find a line break
            if any(child.tag == "LayoutBreak" for child in elem):
                if first is None:
                    first = i
                    continue
                else:
                    second = i
                    #dont contiue! go to the finally
            else:
                continue
        
        #first and second have been set correctly, 
        # time to to the balancing
        line1_len = first - initial +1
        line2_len = second - first +1

        print(f"Line 1: {line1_len}, Line 2 {line2_len}")

        if line1_len >= 4 and line2_len <= 2:
            print("Lines being balanced")
            _remove_line_break_from_measure(staff[first])
            if line1_len > 4:
                #Re-insert line break to midpoint of the two
                midpoint = (initial + second) // 2
                _add_line_break_to_measure_opt(staff[midpoint])

        initial = i+1
        first = None
        second = None

    return staff








def final_pass_through(staff: ET.Element) -> ET.Element:
    """
    Adjusts poorly balanced lines. If a line has only 2 measures and the previous has 4+:
    - If prev has 4: remove the break before it.
    - If prev has >4: remove the break and move it to the midpoint.

    TODO:
    When balancing, if line break to be removed is on a measure with Rehearsal Mark or Double Bar -- do not remove it, and instead remove the current break
     '' as above, but if theres a slur going over the bar, remove current line brek
    TODO:
    This breaks after like half the score. Maybe re-write it?
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
                _add_line_break_to_measure(prev_line[split_index])
    return staff


# TODO[SC-43]: Modify it so that the score style is selected based on the # of instruments
#TODO: Allow users to set page and staff spacing from the website
def add_styles_to_score_and_parts(style: Style, work_dir: str) -> None:
    """
    Depending on what style enum is selected, load either the jazz or broadway style file.

    Go through temp directory, replace any "style" .mss parts with the selected style file.
    This includes both the main score and individual part style files.
    """

    # Determine style files
    if style == Style.BROADWAY:
        score_style_path = os.path.join(STYLES_DIR, "broadway_score.mss")
        part_style_path = os.path.join(STYLES_DIR, "broadway_part.mss")
    elif style == Style.JAZZ:
        score_style_path = os.path.join(STYLES_DIR, "jazz_score.mss")
        part_style_path = os.path.join(STYLES_DIR, "jazz_part.mss")
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

            source_style = part_style_path if is_excerpt else score_style_path
            shutil.copyfile(source_style, full_path)

            print(f"Replaced {'part' if is_excerpt else 'score'} style: {full_path}")


def mscz_main(
    input_path,
    output_path,
    style_name,
    num_measure_per_line=NUM_MEASURES_PER_LINE,
    **kwargs,
):
    if not kwargs.get("movementTitle"):
        kwargs["movementTitle"] = ""
    if not kwargs.get("workNumber"):
        kwargs["workNumber"] = ""

    work_dir = TEMP_DIR + input_path.split("/")[-1]

    with zipfile.ZipFile(input_path, "r") as zip_ref:
        # Extract all files to "temp" and collect all .mscx files from the zip structure
        zip_ref.extractall(work_dir)

    selected_style = Style(style_name)

    add_styles_to_score_and_parts(selected_style, work_dir)

    mscx_files = [
        os.path.join(work_dir, f) for f in zip_ref.namelist() if f.endswith(".mscx")
    ]
    if not mscx_files:
        print("No .mscx files found in the provided mscz file.")
        shutil.rmtree(work_dir)
        return

    for mscx_path in mscx_files:
        print(f"Processing {mscx_path}...")
        process_mscx(
            mscx_path,
            selected_style,
            measures_per_line=num_measure_per_line,
            # workNumber=show_number,
            # movementTitle=show_title,
            **kwargs,
        )

    with zipfile.ZipFile(output_path, "w") as zip_out:
        for root, _, files in os.walk(work_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zip_out.write(file_path, os.path.relpath(file_path, work_dir))

    shutil.rmtree(work_dir)


def process_mscx(
    mscx_path, selected_style, measures_per_line, standalone=False, **kwargs
):
    try:
        parser = ET.XMLParser()
        tree = ET.parse(mscx_path, parser)
        root = tree.getroot()
        score = root.find("Score")
        if score is None:
            raise ValueError("No <Score> tag found in the XML.")

        # set score properties
        if kwargs.get("versionNum") is None:
            kwargs["versionNum"] = "1.0.0"

        if kwargs["arranger"] == "COMPOSER":
            for metaTag in score.findall("metaTag"):
                if metaTag.attrib.get("name") == "composer":
                    kwargs["arranger"] = metaTag.attrib.get("name")

        for metaTag in score.findall("metaTag"):
            for k in kwargs.keys():
                if metaTag.attrib.get("name") == k:
                    metaTag.text = kwargs[k]

        show_number = kwargs["workNumber"]
        show_title = kwargs["movementTitle"]

        staves = score.findall("Staff")

        staff = staves[0]  # noqa  -- only add layout breaks to the first staff
        strip_existing_linebreaks(staff)
        prep_mm_rests(staff)
        add_rehearsal_mark_line_breaks(staff)
        add_double_bar_line_breaks(staff)
        add_regular_line_breaks(staff, measures_per_line)
        new_final_pass_through(staff)
        add_page_breaks(staff)          #TODO: Only add page breaks if not working on conductor score
        cleanup_mm_rests(staff)
        if selected_style == Style.BROADWAY:
            add_broadway_header(staff, show_number, show_title)
        add_part_name(staff)

        if standalone:
            out_path = mscx_path.replace("test-data", "test-data-copy")

            with open(out_path, "wb") as f:
                ET.indent(tree, space="  ", level=0)
                tree.write(f, encoding="utf-8", xml_declaration=True)
            print(f"Output written to {out_path}")
        else:
            with open(mscx_path, "wb") as f:
                ET.indent(tree, space="  ", level=0)
                tree.write(f, encoding="utf-8", xml_declaration=True)
            print(f"Output written to {mscx_path}")

    except FileNotFoundError:
        print(f"Error: File '{mscx_path}' not found.")
        sys.exit(1)
