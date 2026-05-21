"""Unified diff must pair LHS/RHS per logical staff, not consecutive staves."""

import os
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from musescore_score_diff.compute_diff import compute_diff_with_alignment
from musescore_score_diff.display_diff import (
    _unified_lhs_rhs_staff_pairs,
    compare_musescore_files,
    merge_musescore_files_for_diff,
    mark_diffs_unified,
)
from musescore_score_diff.utils import State


def _extract_main_mscx(mscz_path: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(mscz_path, "r") as zf:
        zf.extractall(dest_dir)
    for root, _, files in os.walk(dest_dir):
        for name in files:
            if name.endswith(".mscx") and "Excerpt" not in root.replace("\\", "/"):
                return os.path.join(root, name)
    raise FileNotFoundError(f"No main .mscx in {mscz_path}")


def _measure_has_highlight(measure: ET.Element) -> bool:
    for color in measure.iter("color"):
        r = color.get("r")
        g = color.get("g")
        if r and g and int(r) > 150 and int(g) < 80:
            return True
        if g and r and int(g) > 150 and int(r) < 80:
            return True
    return False


def test_unified_pairing_two_staff_piano():
    fixture = "tests/fixtures/merge-scores/merge-conflict-single-measure"
    with tempfile.TemporaryDirectory() as work:
        head_mscx = _extract_main_mscx(
            f"{fixture}/head.mscz", os.path.join(work, "head")
        )
        user_mscx = _extract_main_mscx(
            f"{fixture}/user.mscz", os.path.join(work, "user")
        )
        diffs, alignment = compute_diff_with_alignment(head_mscx, user_mscx)
        assert len(alignment.rows) == 2
        assert diffs[2] == [State.UNCHANGED] * len(diffs[2])

        tree, _ = merge_musescore_files_for_diff(head_mscx, user_mscx)
        score = tree.getroot().find("Score")
        pairs = _unified_lhs_rhs_staff_pairs(score.findall("Staff"))
        assert len(pairs) == 2
        assert pairs[0][0] is score.findall("Staff")[0]
        assert pairs[0][1] is score.findall("Staff")[2]
        assert pairs[1][0] is score.findall("Staff")[1]
        assert pairs[1][1] is score.findall("Staff")[3]

        mark_diffs_unified(score, diffs)
        staves = score.findall("Staff")
        treble_rhs = staves[2]
        bass_rhs = staves[3]
        assert _measure_has_highlight(treble_rhs.findall("Measure")[1])
        assert not _measure_has_highlight(bass_rhs.findall("Measure")[1])


def _is_empty_rest_measure(measure: ET.Element) -> bool:
    voice = measure.find("voice")
    if voice is None:
        return False
    children = [c for c in voice if c.tag not in ("eid", "linkedMain")]
    return len(children) == 1 and children[0].tag == "Rest"


def test_measure_added_syncs_insert_index_across_piano_staves():
    """Inserted bar must pad every staff in the part at the same measure index."""
    fixture = "tests/fixtures/merge-scores/measure-added"
    with tempfile.TemporaryDirectory() as work:
        head_mscx = _extract_main_mscx(f"{fixture}/head.mscz", os.path.join(work, "head"))
        user_mscx = _extract_main_mscx(f"{fixture}/user.mscz", os.path.join(work, "user"))

        diffs, alignment = compute_diff_with_alignment(head_mscx, user_mscx)
        assert len(alignment.rows) == 2
        insert1 = [i for i, s in enumerate(diffs[1]) if s == State.INSERTED]
        insert2 = [i for i, s in enumerate(diffs[2]) if s == State.INSERTED]
        assert insert1 == insert2 and len(insert1) == 1
        insert_at = insert1

        out = os.path.join(work, "diff.mscx")
        compare_musescore_files(head_mscx, user_mscx, out)
        staves = ET.parse(out).getroot().find("Score").findall("Staff")
        assert all(len(s.findall("Measure")) == 5 for s in staves)
        idx = insert_at[0]
        for staff in (staves[0], staves[1]):
            assert _is_empty_rest_measure(staff.findall("Measure")[idx])


def test_compare_musescore_piano_conflict_output(tmp_path):
    fixture = "tests/fixtures/merge-scores/merge-conflict-single-measure"
    with tempfile.TemporaryDirectory() as work:
        head_mscx = _extract_main_mscx(
            f"{fixture}/head.mscz", os.path.join(work, "head")
        )
        user_mscx = _extract_main_mscx(
            f"{fixture}/user.mscz", os.path.join(work, "user")
        )
        out = tmp_path / "diff.mscx"
        compare_musescore_files(head_mscx, user_mscx, str(out))
        tree = ET.parse(out)
        staves = tree.getroot().find("Score").findall("Staff")
        assert not _measure_has_highlight(staves[3].findall("Measure")[1])
