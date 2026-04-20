import pytest
import warnings
import tempfile
import shutil
import zipfile
import xml.etree.ElementTree as ET
import os
import hashlib
import re

from musescore_part_formatter import format_mscz, format_mscx, FormattingParams
from musescore_part_formatter.utils import _measure_has_line_break

OUTPUT_DIRECTORY = "tests/processing"


def _assert_no_layout_breaks_in_any_measure(mscx_path: str) -> None:
    tree = ET.parse(mscx_path)
    score = tree.getroot().find("Score")
    assert score is not None
    locations: list[str] = []
    for staff_idx, staff in enumerate(score.findall("Staff")):
        for measure_idx, measure in enumerate(staff.findall("Measure")):
            if measure.find("LayoutBreak") is not None:
                locations.append(f"staff={staff_idx} measure_index={measure_idx}")
    assert not locations, (
        "Expected no <LayoutBreak> inside <Measure> elements; found in: "
        + ", ".join(locations)
    )


@pytest.mark.parametrize("style", ("jazz", "broadway"))
def test_mscz_formatter_works(style):
    input_path = "tests/test-data/New-Test-Score.mscz"
    output_path = f"tests/test-data/New-Test-Score-{style}-processed.mscz"

    params: FormattingParams = {
        "selected_style": style,
        "show_number": "1",
        "show_title": "TEST Show",
        "version_num": "1.0.0",
        "num_measures_per_line_part": 6,
        "num_measures_per_line_score": 4,
        "num_lines_per_page": 7,
    }

    res = format_mscz(input_path, output_path, params)
    assert res
    warnings.warn("Inspect processed files and confirm they look good! :sunglasses: ")

    # check that the style mss file has a value set (not the placeholder)
    # unzio output file, find mss file,
    with tempfile.TemporaryDirectory() as tempdir:
        with zipfile.ZipFile(output_path, "r") as zf:
            zf.extractall(tempdir)

            for root, _, files in os.walk(tempdir):
                for filename in files:
                    if not filename.lower().endswith(".mss"):
                        continue

                    full_path = os.path.join(root, filename)

                    with open(full_path, "r") as f:
                        f_contents = f.read()
                        assert "DIVISI:staff_spacing" not in f_contents, (
                            "Staff Spacing not properly set"
                        )


@pytest.mark.parametrize("case", ("apply_scrub_existing_line_breaks",))
def test_mscz_formatter_works_individual_cases(case):
    input_path = "tests/test-data/New-Test-Score.mscz"
    output_path = f"tests/test-data/New-Test-Score-jazz-processed-{case}.mscz"

    params: FormattingParams = {
        "selected_style": "jazz",
        "show_number": "1",
        "show_title": "TEST Show",
        "version_num": "1.0.0",
        "num_measures_per_line_part": 6,
        "num_measures_per_line_score": 4,
        "num_lines_per_page": 7,
        case: True,
    }
    if case == "apply_scrub_existing_line_breaks":
        # Scrub only removes breaks; other steps would insert <LayoutBreak> again.
        params.update(
            {
                "apply_rehearsal_line_breaks": False,
                "apply_double_bar_line_breaks": False,
                "apply_measure_count_line_breaks": False,
                "apply_line_break_balancing": False,
            }
        )

    res = format_mscz(input_path, output_path, params)
    assert res
    warnings.warn("Inspect processed files and confirm they look good! :sunglasses: ")

    # check that the style mss file has a value set (not the placeholder)
    # unzio output file, find mss file,
    with tempfile.TemporaryDirectory() as tempdir:
        with zipfile.ZipFile(output_path, "r") as zf:
            zf.extractall(tempdir)

            for root, _, files in os.walk(tempdir):
                for filename in files:
                    if not filename.lower().endswith(".mss"):
                        continue

                    full_path = os.path.join(root, filename)

                    with open(full_path, "r") as f:
                        f_contents = f.read()
                        assert "DIVISI:staff_spacing" not in f_contents, (
                            "Staff Spacing not properly set"
                        )

            if case == "apply_scrub_existing_line_breaks":
                matches = []
                for root, _, files in os.walk(tempdir):
                    if "New-Test-Score.mscx" in files:
                        matches.append(os.path.join(root, "New-Test-Score.mscx"))
                assert len(matches) == 1, (
                    "Expected exactly one New-Test-Score.mscx in extracted mscz; "
                    f"found {matches!r}"
                )
                _assert_no_layout_breaks_in_any_measure(matches[0])

def test_params_incorrect():
    pass


def _first_score_spatium_from_mscz(mscz_path: str) -> float:
    with zipfile.ZipFile(mscz_path, "r") as zf:
        names = [n for n in zf.namelist() if n.endswith("score_style.mss")]
        assert names, f"No score_style.mss in {mscz_path}"
        txt = zf.read(names[0]).decode("utf-8")
    m = re.search(r"<spatium>([^<]+)</spatium>", txt)
    assert m is not None, txt[:400]
    return float(m.group(1).strip())


def test_staff_spacing_override_sets_score_spatium():
    input_path = "tests/test-data/New-Test-Score.mscz"
    base_params: FormattingParams = {
        "selected_style": "broadway",
        "show_number": "1",
        "show_title": "TEST Show",
        "version_num": "1.0.0",
        "num_measures_per_line_part": 6,
        "num_measures_per_line_score": 4,
        "num_lines_per_page": 7,
        "staff_spacing_strategy": "override",
        "staff_spacing_value": "1.88777",
    }
    with tempfile.NamedTemporaryFile(suffix=".mscz", delete=False) as tmp:
        output_path = tmp.name
    try:
        assert format_mscz(input_path, output_path, base_params)
        assert abs(_first_score_spatium_from_mscz(output_path) - 1.88777) < 1e-5
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def test_staff_spacing_preserve_keeps_input_score_spatium():
    input_path = "tests/test-data/New-Test-Score.mscz"
    expected = _first_score_spatium_from_mscz(input_path)
    base_params: FormattingParams = {
        "selected_style": "broadway",
        "show_number": "1",
        "show_title": "TEST Show",
        "version_num": "1.0.0",
        "num_measures_per_line_part": 6,
        "num_measures_per_line_score": 4,
        "num_lines_per_page": 7,
        "staff_spacing_strategy": "preserve",
    }
    with tempfile.NamedTemporaryFile(suffix=".mscz", delete=False) as tmp:
        output_path = tmp.name
    try:
        assert format_mscz(input_path, output_path, base_params)
        assert abs(_first_score_spatium_from_mscz(output_path) - expected) < 1e-5
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def _score_style_mss_sha256(mscz_path: str) -> str:
    with zipfile.ZipFile(mscz_path, "r") as zf:
        names = [n for n in zf.namelist() if n.endswith("score_style.mss")]
        assert names, f"No score_style.mss in {mscz_path}"
        return hashlib.sha256(zf.read(names[0])).hexdigest()


def test_apply_mss_style_false_leaves_score_style_mss_unchanged():
    input_path = "tests/test-data/New-Test-Score.mscz"
    with tempfile.NamedTemporaryFile(suffix=".mscz", delete=False) as tmp:
        output_path = tmp.name
    try:
        input_hash = _score_style_mss_sha256(input_path)
        params: FormattingParams = {
            "selected_style": "jazz",
            "show_number": "1",
            "show_title": "TEST Show",
            "version_num": "1.0.0",
            "num_measures_per_line_part": 6,
            "num_measures_per_line_score": 4,
            "num_lines_per_page": 7,
            "apply_mss_style": False,
        }
        assert format_mscz(input_path, output_path, params)
        assert _score_style_mss_sha256(output_path) == input_hash
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def test_apply_measure_count_line_breaks_false_skips_regular_breaks():
    filename = "Test_Regular_Line_Breaks.mscx"
    params: FormattingParams = {
        "num_measures_per_line_part": 4,
        "num_measures_per_line_score": 4,
        "num_lines_per_page": 7,
        "selected_style": "broadway",
        "show_title": "TEST Show",
        "show_number": "1",
        "version_num": "1.0.0",
        "apply_rehearsal_line_breaks": False,
        "apply_double_bar_line_breaks": False,
        "apply_measure_count_line_breaks": False,
        "apply_line_break_balancing": False,
        "apply_broadway_vbox_header": False,
        "apply_part_name_in_header": False,
    }
    with tempfile.TemporaryDirectory() as workdir:
        shutil.copy(f"tests/test-data/sample-mscx/{filename}", workdir)
        temp_mscx = os.path.join(workdir, filename)
        format_mscx(temp_mscx, params)
        tree = ET.parse(temp_mscx)
        score = tree.getroot().find("Score")
        assert score is not None
        staff = score.find("Staff")
        assert staff is not None
        measures = staff.findall("Measure")
        assert not any(_measure_has_line_break(m) for m in measures)

# TODO: Quickly test what jappens if you pass in bogus params and ensure that its caught


@pytest.mark.parametrize(
    "barlines, nmpl",
    [
        (True, 4),
        (True, 6),
        (False, 4),
        (False, 6),
    ],
)
def test_regular_line_breaks(barlines, nmpl: int):
    # eg, 32 bar file with notes, barline at bar 16.
    # set num measures per line to be 4
    # assert that the XML is formatted correctly
    # use format mscx

    filename = "Test_Regular_Line_Breaks.mscx"
    params: FormattingParams = {
        "num_measures_per_line_part": nmpl,
        "num_measures_per_line_score": nmpl,
        "num_lines_per_page": 7,
        "selected_style": "broadway",
        "show_title": "TEST Show",
        "show_number": "1",
        "version_num": "1.0.0",
    }

    if barlines:
        original_mscx_path = f"tests/test-data/sample-mscx/{filename}"
    else:
        original_mscx_path = f"tests/test-data/sample-mscx/{filename}"

    if nmpl == 4:
        bars_with_line_breaks = [4, 8, 12, 16, 20, 24, 28]
    elif nmpl == 6:
        bars_with_line_breaks = [6, 12, 16, 22, 28]

    else:
        bars_with_line_breaks = [-1]

    with tempfile.TemporaryDirectory() as workdir:
        # process mscx
        shutil.copy(original_mscx_path, workdir)
        temp_mscx = os.path.join(workdir, filename)
        format_mscx(temp_mscx, params)

        try:
            parser = ET.XMLParser()
            tree = ET.parse(temp_mscx, parser)
            root = tree.getroot()
            score = root.find("Score")
            if score is None:
                raise ValueError("No <Score> tag found in the XML.")

            staff = score.find("Staff")
            assert staff is not None, "I made a mistake in this test ... :/"
            measures = staff.findall("Measure")
            assert len(measures) == 32, "Something is wrong ith sample score"
            measures_with_line_breaks = [
                (i + 1)
                for i in range(len(measures))
                if _measure_has_line_break(measures[i])
            ]

            for i in bars_with_line_breaks:
                assert _measure_has_line_break(measures[i - 1]), (
                    f"Measure {i} should have had a line break, but it did not :(\n Measures with line breaks: {measures_with_line_breaks}"
                )

        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            assert False


def test_part_and_score_line_breaks():
    FILE_NAME = "tests/test-data/Test-Parts-NMPL.mscz"
    PROCESSED_FILE_NAME = f"{OUTPUT_DIRECTORY}/Test-Parts-NMPL-processed.mscz"

    params: FormattingParams = {
        "num_measures_per_line_part": 6,
        "num_measures_per_line_score": 4,
        "selected_style": "broadway",
        "show_title": "TEST Show",
        "show_number": "1",
        "num_lines_per_page": 7,
        "version_num": "1.0.0",
    }

    assert format_mscz(FILE_NAME, PROCESSED_FILE_NAME, params)

    with tempfile.TemporaryDirectory() as work_dir:
        with zipfile.ZipFile(PROCESSED_FILE_NAME, "r") as zip_ref:
            zip_ref.extractall(work_dir)
            names = zip_ref.namelist()

        mscx_files = [os.path.join(work_dir, f) for f in names if f.endswith(".mscx")]

        assert mscx_files, "No MSCX files found in processed MSCZ"

        for mscx_path in mscx_files:
            if "Excerpts" in mscx_path:
                expected_breaks = [6, 12, 16, 22, 28]
            else:
                expected_breaks = [4, 8, 12, 16, 20, 24, 28, 32]

            tree = ET.parse(mscx_path)
            score = tree.getroot().find("Score")
            assert score is not None

            staff = score.find("Staff")
            assert staff is not None

            measures = staff.findall("Measure")
            assert len(measures) == 32

            actual_breaks = [
                i + 1 for i, m in enumerate(measures) if _measure_has_line_break(m)
            ]

            assert actual_breaks == expected_breaks, (
                f"{os.path.basename(mscx_path)}:\n"
                f"Expected breaks: {expected_breaks}\n"
                f"Actual breaks:   {actual_breaks}"
            )


def test_page_breaks_added_correctly():
    pass
