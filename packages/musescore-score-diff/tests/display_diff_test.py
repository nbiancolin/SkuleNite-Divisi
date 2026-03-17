from musescore_score_diff import compare_musescore_files, compare_mscz_files

from musescore_score_diff.display_diff import (
    merge_musescore_files_for_diff,
    new_merge_musescore_files,
)

import warnings
import pytest

FILE1_MSCZ_PATH = "tests/fixtures/Test-Score.mscz"
FILE2_MSCZ_PATH = "tests/fixtures/Test-Score-2.mscz"

FILE1_UNCOMPRESSED_PATH = "tests/fixtures/Test-Score/Test-Score.mscx"
FILE2_UNCOMPRESSED_PATH = "tests/fixtures/Test-Score-2/Test-Score-2.mscx"

TEST_SCORE1_PATH = "tests/fixtures/single-staff/test-score/test-score.mscx"
TEST_SCORE2_PATH = "tests/fixtures/single-staff/test-score2/test-score2.mscx"
TEST_SCORE_OUTPUT_PATH = "tests/fixtures/single-staff/test_score_output/test-score-{}.mscx"


# def test_mscz_compare_visually():
#     compare_mscz_files(
#         FILE1_MSCZ_PATH,
#         FILE2_MSCZ_PATH,
#         "tests/fixtures/_sample_output/Test-Score.mscz",
#     )
#     warnings.warn("Check the outputted file that output looks correct!")

def test_initial_diff_score_generated_properly():
    diff_score_tree, _ = merge_musescore_files_for_diff(
        TEST_SCORE1_PATH, TEST_SCORE2_PATH
    )
    diff_score_tree.write(
        TEST_SCORE_OUTPUT_PATH.format("1"),
        encoding="UTF-8",
        xml_declaration=True,
    )
    warnings.warn("Check the outputted file that output looks correct!")

#test whole thing with just this score to ensure things are marked correctly. 
# Test each phase (computing diff, displaying diff) indepenently
def test_mscx_single_staff_compare_visually():
    compare_musescore_files(
        "tests/fixtures/single-staff/test-score/test-score.mscx",
        "tests/fixtures/single-staff/test-score2/test-score2.mscx",
        "tests/fixtures/single-staff/test_score_output/test-score-2.mscx",
    )

    warnings.warn(
        "Check the outputted file to ensure that output looks correct "
    )



