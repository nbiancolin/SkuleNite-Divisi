import xml.etree.ElementTree as ET

from musescore_score_diff.alignment import RowKind, align_staves, build_union_from_alignment
from musescore_score_diff.compute_diff import compute_diff
from musescore_score_diff.utils import State


def _minimal_score(parts: list[tuple[str, int, list[list[str]]]]) -> ET.Element:
    """
    Build a <Score> with parts and staves.

    parts: (trackName, part_id, list of staves; each staff is a list of measure XML strings)
    """
    score = ET.Element("Score")
    next_staff_id = 1
    for track_name, part_id, staves_measures in parts:
        part = ET.SubElement(score, "Part", id=str(part_id))
        track = ET.SubElement(part, "trackName")
        track.text = track_name
        for measures in staves_measures:
            ET.SubElement(part, "Staff", id=str(next_staff_id))
            staff = ET.SubElement(score, "Staff", id=str(next_staff_id))
            next_staff_id += 1
            for mx in measures:
                staff.append(ET.fromstring(mx.strip()))
    return score


_MEASURE_A = """
<Measure><voice>
  <Chord><durationType>quarter</durationType><Note><pitch>60</pitch></Note></Chord>
</voice></Measure>
"""

_MEASURE_B = """
<Measure><voice>
  <Chord><durationType>quarter</durationType><Note><pitch>62</pitch></Note></Chord>
</voice></Measure>
"""


def test_align_extra_part_on_right():
    s1 = _minimal_score([("Piano", 1, [[_MEASURE_A]])])
    s2 = _minimal_score([
        ("Piano", 1, [[_MEASURE_A]]),
        ("Flute", 2, [[_MEASURE_B]]),
    ])
    alignment = align_staves(s1, s2)
    kinds = [r.kind for r in alignment.rows]
    assert kinds.count(RowKind.MATCHED) == 1
    assert kinds.count(RowKind.RIGHT_ONLY) == 1

    diffs = compute_diff_from_scores(s1, s2)
    assert diffs[1] == [State.UNCHANGED]
    assert diffs[2] == [State.INSERTED]


def compute_diff_from_scores(s1, s2):
    from musescore_score_diff.compute_diff import _ops_for_row

    alignment = align_staves(s1, s2)
    return {i: _ops_for_row(r) for i, r in enumerate(alignment.rows, start=1)}


def test_align_removed_part_on_right():
    s1 = _minimal_score([
        ("Piano", 1, [[_MEASURE_A]]),
        ("Flute", 2, [[_MEASURE_B]]),
    ])
    s2 = _minimal_score([("Piano", 1, [[_MEASURE_A]])])
    alignment = align_staves(s1, s2)
    assert any(r.kind == RowKind.LEFT_ONLY for r in alignment.rows)
    diffs = compute_diff_from_scores(s1, s2)
    assert State.REMOVED in diffs[2]


def test_align_renamed_part_by_fingerprint():
    s1 = _minimal_score([("Old Name", 1, [[_MEASURE_A]])])
    s2 = _minimal_score([("New Name", 1, [[_MEASURE_A]])])
    alignment = align_staves(s1, s2)
    assert len(alignment.rows) == 1
    assert alignment.rows[0].kind == RowKind.RENAMED
    assert alignment.rows[0].key_left.part_name == "Old Name"
    assert alignment.rows[0].key_right.part_name == "New Name"


def test_union_layout_matches_row_count():
    s1 = _minimal_score([("Piano", 1, [[_MEASURE_A]])])
    s2 = _minimal_score([
        ("Piano", 1, [[_MEASURE_A]]),
        ("Flute", 2, [[_MEASURE_B]]),
    ])
    alignment = align_staves(s1, s2)
    parts, staves, _ = build_union_from_alignment(s1, s2, alignment)
    assert len(staves) == sum(len(p.findall("Staff")) for p in parts)
    assert len(staves) == 4  # piano lhs+rhs, flute lhs+rhs
