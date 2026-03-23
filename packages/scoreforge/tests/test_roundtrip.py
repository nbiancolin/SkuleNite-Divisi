"""
One test to see if the roundtrip works
"""

import pytest

from scoreforge.converter import pitch_to_midi


def test_pitch_to_midi_accepts_flat_and_negative_octave():
    """Regression: Bb; negative octave (D-1 matches midi_to_pitch(2))."""
    assert pitch_to_midi("D-1") == 2
    assert pitch_to_midi("Bb3") == 58


def test_tempo_parse_and_mscx_roundtrip():
    """Tempo (<Tempo>) stores text, playback <tempo>, optional followText; JSON and MSCX preserve them."""
    import tempfile
    import xml.etree.ElementTree as ET
    from pathlib import Path

    from scoreforge.converter import score_to_mscx
    from scoreforge.models import Tempo
    from scoreforge.parser import parse_score
    from scoreforge.serialization import load_score_from_json, save_canonical

    mscx = """<?xml version="1.0"?>
<museScore version="4.0">
  <Score>
    <Staff id="1">
      <Measure>
        <voice>
          <Tempo>
            <tempo>1.166667</tempo>
            <followText>1</followText>
            <text>Directed, <sym>metNoteQuarterUp</sym><font face="Edwin"></font> = 70</text>
          </Tempo>
          <Rest>
            <durationType>whole</durationType>
          </Rest>
        </voice>
      </Measure>
    </Staff>
  </Score>
</museScore>"""
    tree = ET.ElementTree(ET.fromstring(mscx))
    score = parse_score(tree)
    evs = score.parts[0].measures[0].voices["0"]
    tp = next(e for e in evs if isinstance(e, Tempo))
    assert tp.tempo == "1.166667"
    assert tp.follow_text == "1"
    assert "70" in tp.text

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.json"
        save_canonical(score, path)
        score_json = load_score_from_json(path)
    evs_j = score_json.parts[0].measures[0].voices["0"]
    tp_j = next(e for e in evs_j if isinstance(e, Tempo))
    assert tp_j.tempo == "1.166667"
    assert tp_j.follow_text == "1"
    assert tp_j.text == tp.text

    tree_mscx = score_to_mscx(score)
    t_el = tree_mscx.getroot().find(".//Tempo")
    assert t_el is not None
    assert (t_el.findtext("tempo") or "").strip() == "1.166667"
    assert (t_el.findtext("followText") or "").strip() == "1"
    text_out = t_el.find("text")
    assert text_out is not None
    assert "70" in ET.tostring(text_out, encoding="unicode")


def test_rehearsal_mark_parse_and_mscx_roundtrip():
    """Rehearsal marks (<RehearsalMark>) are events with text; JSON and MSCX emit preserve them."""
    import tempfile
    import xml.etree.ElementTree as ET
    from pathlib import Path

    from scoreforge.converter import score_to_mscx
    from scoreforge.models import RehearsalMark
    from scoreforge.parser import parse_score
    from scoreforge.serialization import load_score_from_json, save_canonical

    mscx = """<?xml version="1.0"?>
<museScore version="4.0">
  <Score>
    <Staff id="1">
      <Measure>
        <voice>
          <RehearsalMark>
            <text>A</text>
          </RehearsalMark>
          <Rest>
            <durationType>whole</durationType>
          </Rest>
        </voice>
      </Measure>
    </Staff>
  </Score>
</museScore>"""
    tree = ET.ElementTree(ET.fromstring(mscx))
    score = parse_score(tree)
    evs = score.parts[0].measures[0].voices["0"]
    rm = next(e for e in evs if isinstance(e, RehearsalMark))
    assert rm.text == "A"

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.json"
        save_canonical(score, path)
        score_json = load_score_from_json(path)
    evs_j = score_json.parts[0].measures[0].voices["0"]
    rm_j = next(e for e in evs_j if isinstance(e, RehearsalMark))
    assert rm_j.text == "A"

    tree_mscx = score_to_mscx(score)
    rm_el = tree_mscx.getroot().find(".//RehearsalMark")
    assert rm_el is not None
    assert (rm_el.findtext("text") or "").strip() == "A"


def test_cue_small_chord_and_rest_parse_json_mscx_roundtrip():
    """MuseScore cue size is <small> on <Chord> and <Rest>; JSON and MSCX preserve it."""
    import tempfile
    import xml.etree.ElementTree as ET
    from pathlib import Path

    from scoreforge.converter import score_to_mscx
    from scoreforge.models import Note, Rest
    from scoreforge.parser import parse_score
    from scoreforge.serialization import load_score_from_json, save_canonical

    mscx = """<?xml version="1.0"?>
<museScore version="4.0">
  <Score>
    <Staff id="1">
      <Measure>
        <voice>
          <Chord>
            <small>1</small>
            <durationType>quarter</durationType>
            <StemDirection>up</StemDirection>
            <Note>
              <pitch>60</pitch>
              <tpc>14</tpc>
            </Note>
          </Chord>
          <Rest>
            <small>1</small>
            <durationType>quarter</durationType>
          </Rest>
        </voice>
      </Measure>
    </Staff>
  </Score>
</museScore>"""
    tree = ET.ElementTree(ET.fromstring(mscx))
    score = parse_score(tree)
    evs = score.parts[0].measures[0].voices["0"]
    n0 = evs[0]
    r0 = evs[1]
    assert isinstance(n0, Note)
    assert n0.small is True
    assert isinstance(r0, Rest)
    assert r0.small is True

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.json"
        save_canonical(score, path)
        score_json = load_score_from_json(path)
    evs_j = score_json.parts[0].measures[0].voices["0"]
    n0j = evs_j[0]
    r0j = evs_j[1]
    assert isinstance(n0j, Note)
    assert n0j.small is True
    assert isinstance(r0j, Rest)
    assert r0j.small is True

    tree_mscx = score_to_mscx(score)
    root = tree_mscx.getroot()
    chord_el = root.find(".//Chord")
    assert chord_el is not None
    assert (chord_el.findtext("small") or "").strip() == "1"
    rest_el = root.find(".//Rest")
    assert rest_el is not None
    assert (rest_el.findtext("small") or "").strip() == "1"


def test_chord_symbol_harmony_parse_and_mscx_roundtrip():
    """MuseScore chord symbols (<Harmony> with harmonyInfo); JSON and MSCX preserve canonical XML."""
    import tempfile
    import xml.etree.ElementTree as ET
    from pathlib import Path

    from scoreforge.converter import score_to_mscx
    from scoreforge.models import ChordSymbol
    from scoreforge.parser import parse_score
    from scoreforge.serialization import load_score_from_json, save_canonical

    mscx = """<?xml version="1.0"?>
<museScore version="4.0">
  <Score>
    <Staff id="1">
      <Measure>
        <voice>
          <Harmony>
            <harmonyInfo>
              <name>-</name>
              <root>14</root>
            </harmonyInfo>
          </Harmony>
          <Rest>
            <durationType>whole</durationType>
          </Rest>
        </voice>
      </Measure>
    </Staff>
  </Score>
</museScore>"""
    tree = ET.ElementTree(ET.fromstring(mscx))
    score = parse_score(tree)
    evs = score.parts[0].measures[0].voices["0"]
    cs = next(e for e in evs if isinstance(e, ChordSymbol))
    assert "<Harmony>" in cs.xml
    assert "harmonyInfo" in cs.xml
    assert "14" in cs.xml

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.json"
        save_canonical(score, path)
        score_json = load_score_from_json(path)
    evs_j = score_json.parts[0].measures[0].voices["0"]
    cs_j = next(e for e in evs_j if isinstance(e, ChordSymbol))
    assert cs_j.xml == cs.xml

    tree_mscx = score_to_mscx(score)
    h_el = tree_mscx.getroot().find(".//Harmony")
    assert h_el is not None
    hi = h_el.find("harmonyInfo")
    assert hi is not None
    assert (hi.findtext("root") or "").strip() == "14"


def test_roundtrip_for_manual_inspection():
    """Test that converts mscz -> canonical -> mscz for manual inspection.
    
    This test performs a full roundtrip conversion and saves the result
    to the output directory so it can be manually inspected.
    Uses tests/test-data/band-sting-5.mscz as the input file.
    """
    from scoreforge.cli import json_to_mscz, mscz_to_json
    from pathlib import Path
    
    # Use the specific input file
    # input_mscz = Path(__file__).parent / "test-data" / "band-sting-5.mscz"
    # input_mscz = Path(__file__).parent / "test-data" / "10-Mirror-Blue Night.mscz"
    input_mscz = Path(__file__).parent / "test-data" / "My Funny Valentine.mscz"
    assert input_mscz.exists(), f"Input file not found: {input_mscz}"
    
    # Use the output directory at the project root for easy access
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Step 1: Convert mscz to canonical JSON and template
    output_filename = "roundtrip_test"
    mscz_to_json(
        str(input_mscz),
        str(output_dir),
        output_filename
    )
    
    json_path = output_dir / f"{output_filename}.json"
    template_path = output_dir / f"{output_filename}.mscz"
    reconstructed_path = output_dir / f"{output_filename}_reconstructed.mscz"
    
    # Step 2: Convert canonical JSON back to mscz
    json_to_mscz(
        str(json_path),
        str(reconstructed_path),
        str(template_path)
    )
    
    # Verify the reconstructed file exists
    assert reconstructed_path.exists(), \
        f"Reconstructed MSCZ should be created at {reconstructed_path}"
    
    print("\n✓ Roundtrip conversion complete!")
    print(f"  Original: {input_mscz}")
    print(f"  Canonical JSON: {json_path}")
    print(f"  Template: {template_path}")
    print(f"  Reconstructed: {reconstructed_path}")
    print(f"\nYou can now manually inspect {reconstructed_path}")


def test_mirror_blue_night_mscz_roundtrip_parse_equality():
    """Regression for MS4 scores: excerpts in MSCZ, 16th notes, measure rests."""
    from scoreforge.cli import json_to_mscz, mscz_to_json
    from scoreforge.io import extract_mscx
    from scoreforge.parser import parse_score
    from pathlib import Path
    import tempfile

    input_mscz = Path(__file__).parent / "test-data" / "10-Mirror-Blue Night.mscz"
    if not input_mscz.exists():
        pytest.skip("test-data/10-Mirror-Blue Night.mscz not present")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        name = "mirror"
        mscz_to_json(str(input_mscz), str(out), name)
        json_path = out / f"{name}.json"
        template_path = out / f"{name}.mscz"
        recon_path = out / "reconstructed.mscz"
        json_to_mscz(str(json_path), str(recon_path), str(template_path))

        original_score = parse_score(extract_mscx(input_mscz))
        reconstructed_score = parse_score(extract_mscx(recon_path))

        assert len(reconstructed_score.parts) == len(original_score.parts)
        for orig_part, recon_part in zip(original_score.parts, reconstructed_score.parts):
            assert orig_part.part_id == recon_part.part_id
            assert len(recon_part.measures) == len(orig_part.measures)
            for om, rm in zip(orig_part.measures, recon_part.measures):
                assert om.number == rm.number
                assert om.measure_repeat_count == rm.measure_repeat_count
                assert om.double_bar == rm.double_bar
                assert om.voices == rm.voices