import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from musescore_score_diff.merge_three_way import (
    MergeConflict,
    load_score_tree,
    merge_three_way_musescore,
)
from musescore_score_diff.utils import _hash_measure, _sanitize_measure, extract_measures


_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "single-staff"
FIXTURE = _FIXTURES / "test-score" / "test-score.mscx"
FIXTURE2 = _FIXTURES / "test-score2" / "test-score2.mscx"
_MERGE_SCORES = Path(__file__).resolve().parent / "fixtures" / "merge-scores" / "measure-added"
_CUTAWAY_SCORE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "single-staff"
    / "test_score_output"
    / "test-score.mscx"
)

# ---------------------------------------------------------------------------
# End-to-end (manual): set all three paths, then run:
#   pytest tests/merge_three_way_test.py::test_merge_three_way_end_to_end -v
# Leave empty strings to keep the test skipped in CI / default runs.
#
# .mscx and .mscz inputs are supported. For E2E_MERGE_OUTPUT ending in .mscz,
# E2E_MERGE_OURS must be .mscz (that archive is copied; only the main .mscx is
# replaced). Paths can be absolute or relative to the process cwd.
# ---------------------------------------------------------------------------
E2E_MERGE_BASE = "packages/musescore-score-diff/tests/fixtures/merge-scores/measure-added/base.mscz"
E2E_MERGE_OURS = "packages/musescore-score-diff/tests/fixtures/merge-scores/measure-added/user.mscz"
E2E_MERGE_THEIRS = "packages/musescore-score-diff/tests/fixtures/merge-scores/measure-added/head.mscz"
E2E_MERGE_OUTPUT = ""


def _e2e_merged_output_path() -> Path:
    if E2E_MERGE_OUTPUT.strip():
        return Path(E2E_MERGE_OUTPUT)
    return Path(__file__).resolve().parent / "merge_three_way_test.e2e_merged_output.mscz"


def _first_pitch_in_measure(staff: ET.Element, measure_index_one_based: int) -> ET.Element | None:
    measures = staff.findall("Measure")
    m = measures[measure_index_one_based - 1]
    _sanitize_measure(m)
    pitch = m.find(".//pitch")
    return pitch


def _set_first_pitch_in_measure(path: Path, measure_index_one_based: int, pitch: str) -> None:
    tree = ET.parse(path)
    staff = tree.find(".//Score/Staff")
    assert staff is not None
    measures = staff.findall("Measure")
    m = measures[measure_index_one_based - 1]
    pitch_el = m.find(".//pitch")
    assert pitch_el is not None
    pitch_el.text = pitch
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def test_merge_three_way_identity():
    base = str(FIXTURE)
    merged = merge_three_way_musescore(base, base, base)
    staff = merged.getroot().find(".//Score/Staff")
    assert staff is not None
    h0 = _hash_measure(extract_measures(staff)[6][2])  # measure 7
    tree_b = ET.parse(base)
    staff_b = tree_b.find(".//Score/Staff")
    assert staff_b is not None
    h1 = _hash_measure(extract_measures(staff_b)[6][2])
    assert h0 == h1


def test_merge_three_way_only_theirs_changed(tmp_path: Path):
    base = tmp_path / "base.mscx"
    ours = tmp_path / "ours.mscx"
    theirs = tmp_path / "theirs.mscx"
    shutil.copy(FIXTURE, base)
    shutil.copy(FIXTURE, ours)
    shutil.copy(FIXTURE, theirs)
    _set_first_pitch_in_measure(theirs, 7, "72")

    merged = merge_three_way_musescore(str(base), str(ours), str(theirs))
    staff_m = merged.getroot().find(".//Score/Staff")
    assert staff_m is not None
    pitch_m = _first_pitch_in_measure(staff_m, 7)
    assert pitch_m is not None and pitch_m.text == "72"


def test_merge_three_way_conflict(tmp_path: Path):
    base = tmp_path / "base.mscx"
    ours = tmp_path / "ours.mscx"
    theirs = tmp_path / "theirs.mscx"
    shutil.copy(FIXTURE, base)
    shutil.copy(FIXTURE, ours)
    shutil.copy(FIXTURE, theirs)
    _set_first_pitch_in_measure(ours, 7, "70")
    _set_first_pitch_in_measure(theirs, 7, "71")

    with pytest.raises(MergeConflict) as exc_info:
        merge_three_way_musescore(str(base), str(ours), str(theirs))
    assert exc_info.value.conflicts == [("1", 7)]


def test_merge_three_way_lcs_theirs_inserts_when_ours_is_base():
    """When ours == base, LCS merge should replay theirs' insertions (e.g. test-score2 vs test-score)."""
    base = str(FIXTURE)
    other = str(FIXTURE2)
    tree_t = ET.parse(other)
    staff_t = tree_t.find(".//Score/Staff")
    assert staff_t is not None
    expected_len = len(staff_t.findall("Measure"))

    merged = merge_three_way_musescore(base, base, other)
    staff_m = merged.getroot().find(".//Score/Staff")
    assert staff_m is not None
    assert len(staff_m.findall("Measure")) == expected_len


def test_merge_three_way_cutaway_after_last_measure() -> None:
    """MuseScore may place <cutaway> after the last measure; merged measures must stay before it."""
    if not _CUTAWAY_SCORE.is_file():
        pytest.skip("test_score_output fixture not present")

    merged = merge_three_way_musescore(
        str(_CUTAWAY_SCORE), str(_CUTAWAY_SCORE), str(_CUTAWAY_SCORE)
    )
    score = merged.getroot().find("Score")
    assert score is not None
    st2 = next(s for s in score.findall("Staff") if s.get("id") == "2")
    tags = [c.tag for c in st2]
    measure_idxs = [i for i, t in enumerate(tags) if t == "Measure"]
    assert measure_idxs
    assert tags[measure_idxs[-1] + 1] == "cutaway"


def test_merge_three_way_mscz_writes_zip(tmp_path: Path) -> None:
    base = _MERGE_SCORES / "base.mscz"
    ours = _MERGE_SCORES / "user.mscz"
    theirs = _MERGE_SCORES / "head.mscz"
    if not base.is_file():
        pytest.skip("merge-scores fixtures not present")

    out = tmp_path / "merged.mscz"
    tree = merge_three_way_musescore(
        str(base), str(ours), str(theirs), output_path=str(out)
    )
    assert out.is_file()
    written = load_score_tree(str(out))
    score = written.getroot().find("Score")
    assert score is not None
    assert tree.getroot().find("Score") is not None
    assert len(score.findall("Staff")) == len(
        tree.getroot().find("Score").findall("Staff")
    )


def test_merge_three_way_end_to_end() -> None:
    if not (E2E_MERGE_BASE.strip() and E2E_MERGE_OURS.strip() and E2E_MERGE_THEIRS.strip()):
        pytest.skip(
            "Set E2E_MERGE_BASE, E2E_MERGE_OURS, and E2E_MERGE_THEIRS at the top of "
            "merge_three_way_test.py, then re-run this test."
        )

    base = Path(E2E_MERGE_BASE)
    ours = Path(E2E_MERGE_OURS)
    theirs = Path(E2E_MERGE_THEIRS)
    for label, p in (("base", base), ("ours", ours), ("theirs", theirs)):
        assert p.is_file(), f"E2E path for {label} is not a file: {p}"

    out = _e2e_merged_output_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    tree = merge_three_way_musescore(
        str(base), str(ours), str(theirs), output_path=str(out)
    )

    assert out.is_file(), "merge wrote output_path"
    print(f"\n[E2E] Merged score written for inspection: {out.resolve()}\n")
    written = load_score_tree(str(out))
    score = written.getroot().find("Score")
    assert score is not None, "merged file has <Score>"

    staves = score.findall("Staff")
    assert staves, "merged score has no staves"
    assert any(len(s.findall("Measure")) > 0 for s in staves), "merged staves have no measures"

    assert tree.getroot().find("Score") is not None
    assert len(tree.getroot().find("Score").findall("Staff")) == len(staves)
