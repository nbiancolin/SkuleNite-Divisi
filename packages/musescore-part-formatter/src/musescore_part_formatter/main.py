import shutil
import argparse
import sys

import xml.etree.ElementTree as ET

from .utils import Style, FormattingParams, FORMATTING_STEP_KEYS
from .utils import set_score_properties
from .formatting import add_styles_to_score_and_parts
from .formatting import (
    prep_mm_rests,
    add_rehearsal_mark_line_breaks,
    add_double_bar_line_breaks,
    add_regular_line_breaks,
    final_pass_through,
    new_add_page_breaks,
    cleanup_mm_rests,
    add_broadway_header,
    add_part_name,
)
from .file_processing import unpack_mscz_to_tempdir
from .file_inspect import (
    ScoreInfo,
    get_all_properties,
    set_all_properties,
)

from logging import getLogger


LOGGER = getLogger("PartFormatter")


def merge_formatting_step_defaults(params: dict) -> None:
    """Ensure every apply_* key exists (mutates). Omitted keys default to True."""
    for key in FORMATTING_STEP_KEYS:
        if key not in params:
            params[key] = True


def format_mscx(
    mscx_path: str, params: FormattingParams, is_part: bool = False
) -> bool:
    """
    Takes in an (uncompressed) musescore file, processes it, and outputs it in place
    This is usually only used internally by `format_mscz()`, but if the user wants to format a mscx file, why not let them?

    Returns:
    - True if processing completed successfully
    - False if an error occurred

    """
    try:
        parser = ET.XMLParser()
        tree = ET.parse(mscx_path, parser)
        root = tree.getroot()
        score = root.find("Score")
        if score is None:
            raise ValueError("No <Score> tag found in the XML.")

        merge_formatting_step_defaults(params)

        # prep_mm_rests marks measures for multimeasure-aware line breaks; cleanup_mm_rests
        # removes those marks. Prep only runs when at least one line-break insertion step is on
        # (otherwise prep would only add temporary attrs). If prep ran, always cleanup so _mm
        # is never left in the saved XML.
        if params.get("apply_score_metadata", True):
            score_properties = {
                "albumTitle": params["show_title"],
                "trackNum": params["show_number"],
                "versionNum": params["version_num"],
            }
            set_score_properties(score, score_properties)

        staves = score.findall("Staff")

        staff = staves[0]  # noqa  -- only add layout breaks to the first staff
        needs_mm_marks = (
            params.get("apply_rehearsal_line_breaks", True)
            or params.get("apply_double_bar_line_breaks", True)
            or params.get("apply_measure_count_line_breaks", True)
        )
        run_mm_prep = (
            params.get("apply_multimeasure_rest_prep", True) and needs_mm_marks
        )
        if run_mm_prep:
            prep_mm_rests(staff)
        if params.get("apply_rehearsal_line_breaks", True):
            add_rehearsal_mark_line_breaks(staff)
        if params.get("apply_double_bar_line_breaks", True):
            add_double_bar_line_breaks(staff)
        if params.get("apply_measure_count_line_breaks", True):
            if is_part:
                add_regular_line_breaks(staff, params["num_measures_per_line_part"])
            else:
                add_regular_line_breaks(staff, params["num_measures_per_line_score"])
        if params.get("apply_line_break_balancing", True):
            final_pass_through(staff)
        #TODO: fix this
        # new_add_page_breaks(staff, params["num_lines_per_page"])
        if run_mm_prep:
            cleanup_mm_rests(staff)
        if (
            params.get("apply_broadway_vbox_header", True)
            and params["selected_style"] == Style.BROADWAY
        ):
            add_broadway_header(staff, params["show_number"], params["show_title"])
        if params.get("apply_part_name_in_header", True):
            add_part_name(staff)

        with open(mscx_path, "wb") as f:
            ET.indent(tree, space="  ", level=0)
            tree.write(f, encoding="utf-8", xml_declaration=True)
        LOGGER.info(f"Output written to {mscx_path}")
        return True

    except FileNotFoundError:
        LOGGER.warning(f"Error: File '{mscx_path}' not found.")
        return False


def format_mscz(
    input_path: str, output_path: str, params: dict[str, str], predict: bool = False
) -> bool:
    """
    Takes in a (compressed) musescore file, processes it, and outputs it to the path specified by `output_path`

    Returns:
    - True if processing completed successfully
    - False if an error occurred

    If predict is true, if a value is not passed in, the predicted value is used. if values are passed in they are used
    if predict is false, if a value is not passed in, a default vlue is used
    """

    # unpack params
    style_name = (
        params["selected_style"] if params.get("selected_style") else "broadway"
    )

    if predict:
        prepped_params: FormattingParams = {
            "selected_style": Style(style_name),
            "show_title": params.get("show_title", ""),  # title of song from header
            "show_number": params.get("show_number", ""),  # empty
            "version_num": params.get("version_num", ""),  # v1.0?
            "num_measures_per_line_part": params.get(
                "num_measures_per_line_part", 6
            ),  # predict part
            "num_measures_per_line_score": params.get(
                "num_measures_per_line_score", 4
            ),  # predict score
            "num_lines_per_page": params.get(
                "num_lines_per_page", 8
            ),  # predict? this could pob be fixed tho
        }
    else:
        prepped_params: FormattingParams = {
            "selected_style": Style(style_name),
            "show_title": params.get("show_title", ""),
            "show_number": params.get("show_number", ""),
            "version_num": params.get("version_num", ""),
            "num_measures_per_line_part": params.get("num_measures_per_line_part", 6),
            "num_measures_per_line_score": params.get("num_measures_per_line_score", 4),
            "num_lines_per_page": params.get("num_lines_per_page", 8),
        }

    for key in FORMATTING_STEP_KEYS:
        if key in params:
            prepped_params[key] = params[key]  # type: ignore[literal-required]
    merge_formatting_step_defaults(prepped_params)

    # do prediction logic

    shutil.copyfile(input_path, output_path)

    score_info = get_score_attributes(input_path)

    try:
        with unpack_mscz_to_tempdir(output_path) as (work_dir, mscx_files):
            if prepped_params.get("apply_mss_style", True):
                add_styles_to_score_and_parts(
                    prepped_params["selected_style"],  # type-ignore
                    work_dir,
                    score_info=score_info,
                )

            if not mscx_files:
                LOGGER.warning("No .mscx files found in the provided mscz file.")
                return False

            for mscx_path in mscx_files:
                LOGGER.info(f"Processing {mscx_path}...")
                if "Excerpts" in mscx_path:
                    format_mscx(mscx_path, prepped_params, is_part=True)
                else:
                    format_mscx(mscx_path, prepped_params, is_part=False)

    except Exception:
        LOGGER.exception("Failed to process %s", input_path)
        return False

    return True


def get_score_attributes(input_path: str) -> ScoreInfo:
    """
    Takes in a mscz file, and parses the score
    """

    res = {}

    with unpack_mscz_to_tempdir(input_path, repack=False) as (work_dir, mscx_files):
        try:
            parser = ET.XMLParser()
            target = ""
            for mscx_path in mscx_files:
                if "Excerpts" not in mscx_path:
                    target = mscx_path
                    break
            tree = ET.parse(target, parser)
            root = tree.getroot()
            score = root.find("Score")
            if score is None:
                raise ValueError("No <Score> tag found in the XML.")

            res = get_all_properties(score)

        except Exception:
            raise

    return res  # noqa


def set_score_attributes(input_path: str, score_properties: ScoreInfo) -> None:
    with unpack_mscz_to_tempdir(input_path) as (work_dir, mscx_files):
        try:
            target = ""
            for mscx_path in mscx_files:
                if "Excerpts" not in mscx_path:
                    target = mscx_path
                    break
            # TODO: Remove any instances of ET.parse(target, parser), as we do not need our own parser
            tree = ET.parse(target)
            root = tree.getroot()
            score = root.find("Score")
            if score is None:
                raise ValueError("No <Score> tag found in the XML.")

            set_all_properties(score, score_properties)

            with open(target, "wb") as f:
                ET.indent(tree, space="  ", level=0)
                tree.write(f, encoding="utf-8", xml_declaration=True)
            LOGGER.info(f"Output written to {mscx_path}")
            print("Made it here")

        except Exception:
            raise


def main():
    """
    Command-line interface for formatting MuseScore files (.mscz).
    Example:
        python -m musescore_part_formatter.main input.mscz output.mscz \
            --style broadway \
            --show-title "My Song" \
            --show-number "01" \
            --num-measures-per-line-score 4 \
            --num-measures-per-line-part 6 \
            --num-lines-per-page 7
    """
    parser = argparse.ArgumentParser(description="Format a MuseScore file (.mscz).")

    parser.add_argument("input", help="Path to input .mscz file")
    parser.add_argument("output", help="Path to output .mscz file")
    parser.add_argument(
        "--style",
        dest="selected_style",
        default="broadway",
        help="Style to apply (default: broadway)",
    )
    parser.add_argument(
        "--show-title", dest="show_title", default=None, help="Title to display"
    )
    parser.add_argument(
        "--show-number", dest="show_number", default=None, help="Number to display"
    )
    parser.add_argument(
        "--version-num", dest="version_num", default=None, help="Version Num to display"
    )
    parser.add_argument(
        "--num-measures-per-line-score",
        type=int,
        default=4,
        help="Number of measures per line in the full score (default: 4)",
    )
    parser.add_argument(
        "--num-measures-per-line-part",
        type=int,
        default=6,
        help="Number of measures per line in parts (default: 6)",
    )
    parser.add_argument(
        "--num-lines-per-page",
        type=int,
        default=7,
        help="Number of lines per page (default: 7)",
    )

    args = parser.parse_args()

    params: FormattingParams = {
        "selected_style": args.selected_style,
        "show_title": args.show_title,
        "show_number": args.show_number,
        "version_num": args.version_num,
        "num_measures_per_line_score": args.num_measures_per_line_score,
        "num_measures_per_line_part": args.num_measures_per_line_part,
        "num_lines_per_page": args.num_lines_per_page,
    }

    try:
        success = format_mscz(args.input, args.output, params)
        if success:
            print(f"✅ Successfully formatted score: {args.output}")
        else:
            print("⚠️ Formatting failed. See logs for details.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
