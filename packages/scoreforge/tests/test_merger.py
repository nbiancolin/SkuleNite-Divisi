"""Tests for score merging functionality."""

from pathlib import Path

import pytest

from scoreforge.io import extract_mscx
from scoreforge.merger import MergeConflict, three_way_merge_scores
from scoreforge.parser import parse_score


def _load_score(mscz_path: Path):
    """Load a Score from an MSCZ file."""
    tree = extract_mscx(mscz_path)
    return parse_score(tree)


def default_merge_data():
    """Path to default merge test data (base, head, user)."""
    return Path(__file__).parent / "test-data" / "merge-scores" / "default"


def measure_added_merge_data():
    """Path to default merge test data (base, head, user)."""
    return Path(__file__).parent / "test-data" / "merge-scores" / "measure-added"


@pytest.fixture
def conflict_merge_data():
    """Path to merge conflict test data."""
    return (
        Path(__file__).parent
        / "test-data"
        / "merge-scores"
        / "merge-conflict-single-measure"
    )


class TestThreeWayMerge:
    """Tests for 3-way merge (base, head, user)."""

    @pytest.mark.parametrize(
        "merge_data", [default_merge_data(), measure_added_merge_data()]
    )
    def test_three_way_merge_default_no_conflict(self, merge_data):
        """3-way merge of base, head, user should succeed when no conflicts exist."""
        base_path = merge_data / "base.mscz"
        head_path = merge_data / "head.mscz"
        user_path = merge_data / "user.mscz"

        base_score = _load_score(base_path)
        head_score = _load_score(head_path)
        user_score = _load_score(user_path)

        merged = three_way_merge_scores(
            user_score=user_score,
            base_score=base_score,
            head_score=head_score,
        )

        assert merged is not None
        assert len(merged.parts) > 0

    def test_three_way_merge_conflict_raises(self, conflict_merge_data):
        """3-way merge should raise MergeConflict when both head and user modified same measure."""
        base_path = conflict_merge_data / "base.mscz"
        head_path = conflict_merge_data / "head.mscz"
        user_path = conflict_merge_data / "user.mscz"

        base_score = _load_score(base_path)
        head_score = _load_score(head_path)
        user_score = _load_score(user_path)

        with pytest.raises(MergeConflict) as exc_info:
            three_way_merge_scores(
                user_score=user_score,
                base_score=base_score,
                head_score=head_score,
            )

        exc = exc_info.value
        assert len(exc.conflicts) >= 1
        for (part_id, measure_num), (m1, m2) in exc.conflicts.items():
            assert part_id is not None
            assert measure_num > 0
            assert m1 is not None
            assert m2 is not None
