import pytest
import warnings
import tempfile
import shutil
import zipfile
import xml.etree.ElementTree as ET
import os

from musescore_part_formatter import format_mscz, format_mscx, FormattingParams
from musescore_part_formatter.utils import _measure_has_line_break

OUTPUT_DIRECTORY = "tests/processing"


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


def test_params_incorrect():
    pass


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
