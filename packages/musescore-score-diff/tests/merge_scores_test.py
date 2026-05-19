import os
import warnings

import pytest

from musescore_score_diff.merge import (
    MergeConflictException,
    three_way_merge_mscz,
)

from .test_utils import assert_scores_match

MERGE_FIXTURES_DIR = "tests/fixtures/merge-scores"
MERGE_OUTPUT_DIR = "tests/fixtures/_sample_output/merge-scores"


def _merge_paths(scenario: str) -> tuple[str, str, str, str]:
    fixture_dir = f"{MERGE_FIXTURES_DIR}/{scenario}"
    return (
        f"{fixture_dir}/base.mscz",
        f"{fixture_dir}/head.mscz",
        f"{fixture_dir}/user.mscz",
        f"{fixture_dir}/merged.mscz",
    )


def _run_merge(scenario: str, output_name: str = "output.mscz", assert_score: bool = False) -> str:
    """Run merge for manual/visual verification in MuseScore."""
    base_path, head_path, user_path, merged_path = _merge_paths(scenario)
    output_path = f"{MERGE_OUTPUT_DIR}/{scenario}/{output_name}"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    three_way_merge_mscz(base_path, head_path, user_path, output_path)
    if assert_score:
        assert_scores_match(output_path, merged_path)
    return output_path


def test_default_merge_visual():
    output_path = _run_merge("default", assert_score=False)
    warnings.warn(f"Open in MuseScore and verify the default merge looks correct: {output_path}")

def test_measure_deleted_merge_visual():
    output_path = _run_merge("measure-deleted", assert_score=False)
    warnings.warn(f"Open in MuseScore and verify the default merge looks correct: {output_path}")

def test_measure_added_merge_visual():
    output_path = _run_merge("measure-added")
    warnings.warn(f"Open in MuseScore and verify the measure-added merge looks correct: {output_path}")


def test_merge_conflict_single_measure_raises():
    base_path, head_path, user_path, merged_path = _merge_paths("merge-conflict-single-measure")
    output_path = f"{MERGE_OUTPUT_DIR}/merge-conflict-single-measure/merged.mscz"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with pytest.raises(MergeConflictException):
        three_way_merge_mscz(base_path, head_path, user_path, output_path)

    warnings.warn(
        "Merge conflict was raised as expected. Open in MuseScore and verify the "
        f"unified conflict score looks correct: {output_path}"
    )


def test_big_testcase_merges_without_conflict():
    """Head matches base on musical content; user edits merge cleanly."""
    output_path = _run_merge("big-testcase", assert_score=False)
    assert os.path.isfile(output_path)


@pytest.mark.xfail
def test_merge_conflict_measure_added_raises():
    # This test fails when generating a merge score ...
    base_path, head_path, user_path, merged_path = _merge_paths("merge-conflict-measure-added")
    output_path = f"{MERGE_OUTPUT_DIR}/merge-conflict-single-measure/merged.mscz"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with pytest.raises(MergeConflictException):
        three_way_merge_mscz(base_path, head_path, user_path, output_path)

    warnings.warn(
        "Merge conflict was raised as expected. Open in MuseScore and verify the "
        f"unified conflict score looks correct: {output_path}"
    )