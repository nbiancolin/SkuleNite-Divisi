from musescore_score_diff.compute_diff import compute_diff
from musescore_score_diff.utils import State

from musescore_score_diff.utils import _hash_measure, _sanitize_measure

import pytest

def test_hash_measure_ignores_reordered_annotations():
    from copy import deepcopy
    import xml.etree.ElementTree as ET

    from musescore_score_diff.utils import _hash_measure, _sanitize_measure

    measure = ET.fromstring(
        """
        <Measure>
          <voice>
            <TimeSig><sigN>4</sigN><sigD>4</sigD></TimeSig>
            <StaffText><text>note to self</text></StaffText>
            <RehearsalMark><text>A</text></RehearsalMark>
            <Chord><durationType>quarter</durationType>
              <Note><pitch>60</pitch></Note>
            </Chord>
          </voice>
        </Measure>
        """
    )
    reordered = deepcopy(measure)
    voice = reordered.find("voice")
    staff_text = voice.find("StaffText")
    rehearsal = voice.find("RehearsalMark")
    voice.remove(staff_text)
    voice.remove(rehearsal)
    voice.insert(1, rehearsal)
    voice.insert(2, staff_text)

    h1 = _hash_measure(_sanitize_measure(measure))
    h2 = _hash_measure(_sanitize_measure(reordered))
    assert h1 == h2


def test_hash_measure_ignores_courtesy_timesig():
    import xml.etree.ElementTree as ET

    from musescore_score_diff.utils import _hash_measure, _sanitize_measure

    without = ET.fromstring(
        """
        <Measure>
          <voice>
            <Chord><durationType>quarter</durationType>
              <Note><pitch>60</pitch></Note>
            </Chord>
          </voice>
        </Measure>
        """
    )
    with_courtesy = ET.fromstring(
        """
        <Measure>
          <voice>
            <TimeSig>
              <visible>0</visible>
              <sigN>9</sigN>
              <sigD>8</sigD>
              <isCourtesy>1</isCourtesy>
            </TimeSig>
            <Chord><durationType>quarter</durationType>
              <Note><pitch>60</pitch></Note>
            </Chord>
          </voice>
        </Measure>
        """
    )
    assert _hash_measure(_sanitize_measure(without)) == _hash_measure(
        _sanitize_measure(with_courtesy)
    )


def test_hash_measure_ignores_layout_break():
    import xml.etree.ElementTree as ET

    from musescore_score_diff.utils import _hash_measure, _sanitize_measure

    base = ET.fromstring(
        """
        <Measure>
          <voice>
            <Chord><durationType>quarter</durationType>
              <Note><pitch>72</pitch></Note>
            </Chord>
          </voice>
        </Measure>
        """
    )
    with_break = ET.fromstring(
        """
        <Measure>
          <LayoutBreak><subtype>line</subtype></LayoutBreak>
          <voice>
            <Chord><durationType>quarter</durationType>
              <Note><pitch>72</pitch></Note>
            </Chord>
          </voice>
        </Measure>
        """
    )
    assert _hash_measure(_sanitize_measure(base)) == _hash_measure(
        _sanitize_measure(with_break)
    )


def test_merge_treats_identical_head_user_as_non_conflict():
    import xml.etree.ElementTree as ET

    from musescore_score_diff.merge import merge_staff_pair
    from musescore_score_diff.utils import State

    measure = ET.fromstring(
        """
        <Measure>
          <voice>
            <Rest><durationType>measure</durationType><duration>4/4</duration></Rest>
          </voice>
        </Measure>
        """
    )
    head_staff = ET.Element("Staff")
    user_staff = ET.Element("Staff")
    head_staff.append(measure)
    user_staff.append(ET.fromstring(ET.tostring(measure, encoding="unicode")))

    merge_staff_pair(
        head_staff,
        user_staff,
        [State.MODIFIED],
        [State.MODIFIED],
        staff_id=1,
        staff_name="Test",
    )
    assert len(user_staff.findall("Measure")) == 1


def test_merge_conflict_exception_includes_location():
    import xml.etree.ElementTree as ET

    import pytest

    from musescore_score_diff.merge import MergeConflictDetail, MergeConflictException
    from musescore_score_diff.merge import merge_staff_pair
    from musescore_score_diff.utils import State

    head_staff = ET.Element("Staff")
    user_staff = ET.Element("Staff")
    head_staff.append(
        ET.fromstring(
            "<Measure><voice><Chord><Note><pitch>60</pitch></Note></Chord></voice></Measure>"
        )
    )
    user_staff.append(
        ET.fromstring(
            "<Measure><voice><Chord><Note><pitch>62</pitch></Note></Chord></voice></Measure>"
        )
    )

    with pytest.raises(MergeConflictException) as exc_info:
        merge_staff_pair(
            head_staff,
            user_staff,
            [State.MODIFIED],
            [State.MODIFIED],
            staff_id=3,
            staff_name="Alto",
            mscx_path="score.mscx",
        )

    conflict = exc_info.value.conflicts[0]
    assert conflict.staff_id == 3
    assert conflict.staff_name == "Alto"
    assert conflict.alignment_step == 1
    assert conflict.head_measure_no == 1
    assert conflict.user_measure_no == 1
    assert conflict.mscx_path == "score.mscx"
    assert "Alto" in str(exc_info.value)
    assert "alignment step 1" in str(exc_info.value)


def test_diff_computes_correctly():
    file1 = "tests/fixtures/single-staff/test-score/test-score.mscx"
    file2 = "tests/fixtures/single-staff/test-score2/test-score2.mscx"

    ops = compute_diff(file1, file2)[1]
    assert ops[6] == State.MODIFIED
    assert ops[15] == State.INSERTED
    for idx, state in enumerate(ops):
        if idx == 6:
            assert state == State.MODIFIED, f"step {idx}: {state}"
        elif idx == 15:
            assert state == State.INSERTED, f"step {idx}: {state}"
        else:
            assert state == State.UNCHANGED, f"step {idx}: {state}"
