from musescore_score_diff.compute_diff import compute_diff
from musescore_score_diff.utils import State

from musescore_score_diff.utils import _hash_measure, _sanitize_measure

import pytest

def test_hash_measure():
    pass


def test_diff_computes_correctly():
    file1 = "tests/fixtures/single-staff/test-score/test-score.mscx"
    file2 = "tests/fixtures/single-staff/test-score2/test-score2.mscx"

    res = compute_diff(file1, file2)[1] #1 since single staff
    for k in res:
        if k == 7:
            assert res[7] == State.MODIFIED, f"num: {k}, Res: {res}"
        elif k == 16:
            assert res[16] == State.INSERTED, f"num: {k}, Res: {res}"
        else:
            assert res[k] == State.UNCHANGED, f"num: {k}, Res: {res}"

    assert res == {}


