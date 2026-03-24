"""Unit tests for ScoreForge canonical JSON generation."""

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from scoreforge.cli import mscz_to_json
from scoreforge.io import extract_mscx
from scoreforge.parser import parse_score
from scoreforge.serialization import load_score_from_json


@pytest.fixture
def sample_mscz_path():
    """Path to the sample MSCZ file. Creates from MSCX if MSCZ doesn't exist."""
    test_data = Path(__file__).parent / "test-data"
    mscz_path = test_data / "band-sting-5.mscz"
    mscx_path = test_data / "band-sting-5.mscx"

    if not mscz_path.exists() and mscx_path.exists():
        # Create MSCZ from MSCX for template workflow (which needs a zip)
        with zipfile.ZipFile(mscz_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(mscx_path, arcname="score.mscx")

    return mscz_path if mscz_path.exists() else mscx_path


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_mscz_to_json_creates_files(sample_mscz_path, temp_output_dir):
    """Test that mscz_to_json creates both JSON and template MSCZ files."""
    output_filename = "test_output"
    
    # Run the function
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    # Check that JSON file was created
    json_path = temp_output_dir / f"{output_filename}.json"
    assert json_path.exists(), "JSON file should be created"
    
    # Check that template MSCZ file was created
    template_mscz_path = temp_output_dir / f"{output_filename}.mscz"
    assert template_mscz_path.exists(), "Template MSCZ file should be created"


def test_mscz_to_json_json_structure(sample_mscz_path, temp_output_dir):
    """Test that the generated JSON has the correct structure."""
    output_filename = "test_output"
    
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    json_path = temp_output_dir / f"{output_filename}.json"
    
    # Load and validate JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Check top-level structure
    assert "score_id" in data, "JSON should have 'score_id' key"
    assert "parts" in data, "JSON should have 'parts' key"
    assert isinstance(data["parts"], dict), "'parts' should be a dict"
    
    # Check part structure
    if len(data["parts"]) > 0:
        part_id = list(data["parts"].keys())[0]
        part = data["parts"][part_id]
        assert "measures" in part, "Part should have 'measures'"
        assert isinstance(part["measures"], dict), "'measures' should be a dict"
        
        # Check measure structure
        if len(part["measures"]) > 0:
            measure_num = list(part["measures"].keys())[0]
            measure = part["measures"][measure_num]
            assert "events" in measure, "Measure should have 'events'"
            assert isinstance(measure["events"], list), "'events' should be a list"


def test_mscz_to_json_template_has_no_measures(sample_mscz_path, temp_output_dir):
    """Test that the template MSCZ has all measures removed."""
    output_filename = "test_output"
    
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    template_mscz_path = temp_output_dir / f"{output_filename}.mscz"
    
    # Extract and parse the template MSCX
    tree = extract_mscx(template_mscz_path)
    root = tree.getroot()
    score_el = root.find("Score")
    
    assert score_el is not None, "Score element should exist"
    
    # Check that no Measure elements exist in the template
    measures = score_el.findall(".//Measure")
    assert len(measures) == 0, "Template should have no Measure elements"


def test_mscz_to_json_template_excludes_thumbnails(sample_mscz_path, temp_output_dir):
    """Test that the template MSCZ excludes the Thumbnails folder."""
    output_filename = "test_output"
    
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    template_mscz_path = temp_output_dir / f"{output_filename}.mscz"
    
    # Check that Thumbnails folder is not in the template
    with zipfile.ZipFile(template_mscz_path, "r") as z:
        names = z.namelist()
        thumbnail_files = [name for name in names if name.startswith("Thumbnails/") or name == "Thumbnails"]
        assert len(thumbnail_files) == 0, "Template should not contain Thumbnails folder"


def test_mscz_to_json_roundtrip(sample_mscz_path, temp_output_dir):
    """Test that JSON can be loaded back and has valid data."""
    output_filename = "test_output"
    
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    json_path = temp_output_dir / f"{output_filename}.json"
    
    # Try to load the JSON back into a Score object
    score = load_score_from_json(json_path)
    
    assert score is not None, "Should be able to load score from JSON"
    assert len(score.parts) > 0, "Score should have at least one part"
    
    # Verify that parts have measures
    for part in score.parts:
        assert len(part.measures) > 0, f"Part {part.part_id} should have measures"


def test_mscz_to_json_template_preserves_structure(sample_mscz_path, temp_output_dir):
    """Test that the template MSCZ preserves the overall structure."""
    output_filename = "test_output"
    
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    template_mscz_path = temp_output_dir / f"{output_filename}.mscz"
    template_tree = extract_mscx(template_mscz_path)
    template_root = template_tree.getroot()
    template_score = template_root.find("Score")
    
    assert template_score is not None, "Template should have Score element"
    
    # Check that Staff elements are preserved
    template_staffs = template_score.findall(".//Staff")
    
    assert len(template_staffs) > 0, "Template should preserve Staff elements"
    # Note: We don't check exact count as structure might differ, but should have some staffs


def test_json_to_mscz_with_template_roundtrip(sample_mscz_path, temp_output_dir):
    """Test that we can reconstruct a MSCZ file from JSON and template."""
    from scoreforge.cli import json_to_mscz
    
    output_filename = "test_output"
    
    # First, create the JSON and template
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    json_path = temp_output_dir / f"{output_filename}.json"
    template_path = temp_output_dir / f"{output_filename}.mscz"
    reconstructed_path = temp_output_dir / "reconstructed.mscz"
    
    # Reconstruct the MSCZ from JSON and template
    json_to_mscz(
        str(json_path),
        str(reconstructed_path),
        str(template_path)
    )
    
    # Verify the reconstructed file exists
    assert reconstructed_path.exists(), "Reconstructed MSCZ should be created"
    
    # Parse both original and reconstructed
    original_tree = extract_mscx(sample_mscz_path)
    original_score = parse_score(original_tree)
    
    reconstructed_tree = extract_mscx(reconstructed_path)
    reconstructed_score = parse_score(reconstructed_tree)
    
    # Compare the scores
    assert len(reconstructed_score.parts) == len(original_score.parts), \
        "Reconstructed score should have same number of parts"
    
    # Compare measures for each part
    for orig_part, recon_part in zip(original_score.parts, reconstructed_score.parts):
        assert orig_part.part_id == recon_part.part_id, \
            f"Part IDs should match: {orig_part.part_id} vs {recon_part.part_id}"
        assert len(recon_part.measures) == len(orig_part.measures), \
            f"Part {orig_part.part_id} should have same number of measures"
        
        # Compare measures
        for orig_measure, recon_measure in zip(orig_part.measures, recon_part.measures):
            assert orig_measure.number == recon_measure.number, \
                f"Measure numbers should match: {orig_measure.number} vs {recon_measure.number}"
            assert len(recon_measure.events) == len(orig_measure.events), \
                f"Measure {orig_measure.number} should have same number of events"
            
            # Compare events
            for orig_event, recon_event in zip(orig_measure.events, recon_measure.events):
                assert isinstance(orig_event, type(recon_event)) or isinstance(recon_event, type(orig_event)), \
                    f"Event types should match: {type(orig_event)} vs {type(recon_event)}"
                
                # Compare duration for Note and Rest events
                if hasattr(orig_event, "duration") and hasattr(recon_event, "duration"):
                    assert orig_event.duration == recon_event.duration, \
                        f"Event durations should match: {orig_event.duration} vs {recon_event.duration}"
                
                # Compare dots for Note and Rest events
                if hasattr(orig_event, "dots") and hasattr(recon_event, "dots"):
                    assert orig_event.dots == recon_event.dots, \
                        f"Event dots should match: {orig_event.dots} vs {recon_event.dots}"
                
                # Compare pitch for Note events
                if hasattr(orig_event, "pitch") and hasattr(recon_event, "pitch"):
                    assert orig_event.pitch == recon_event.pitch, \
                        f"Event pitches should match: {orig_event.pitch} vs {recon_event.pitch}"
                
                # Compare subtype for Dynamic events
                if hasattr(orig_event, "subtype") and hasattr(recon_event, "subtype"):
                    assert orig_event.subtype == recon_event.subtype, \
                        f"Dynamic subtypes should match: {orig_event.subtype} vs {recon_event.subtype}"


def test_json_to_mscz_with_template_has_measures(sample_mscz_path, temp_output_dir):
    """Test that reconstructed MSCZ has measures in the correct structure."""
    from scoreforge.cli import json_to_mscz
    
    output_filename = "test_output"
    
    # Create JSON and template
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    json_path = temp_output_dir / f"{output_filename}.json"
    template_path = temp_output_dir / f"{output_filename}.mscz"
    reconstructed_path = temp_output_dir / "reconstructed.mscz"
    
    # Reconstruct
    json_to_mscz(
        str(json_path),
        str(reconstructed_path),
        str(template_path)
    )
    
    # Verify measures exist in the reconstructed file
    reconstructed_tree = extract_mscx(reconstructed_path)
    root = reconstructed_tree.getroot()
    score_el = root.find("Score")
    
    assert score_el is not None, "Reconstructed file should have Score element"
    
    # Check that measures exist
    measures = score_el.findall(".//Measure")
    assert len(measures) > 0, "Reconstructed file should have measures"
    
    # Check that measures have voice elements with content
    measures_with_content = 0
    for measure_el in measures:
        voice_el = measure_el.find("voice")
        if voice_el is not None and list(voice_el):
            measures_with_content += 1
    
    # At least some measures should have content
    assert measures_with_content > 0, "At least some measures should have content"


def test_json_to_mscz_with_template_preserves_metadata(sample_mscz_path, temp_output_dir):
    """Test that reconstructed MSCZ preserves metadata from template."""
    from scoreforge.cli import json_to_mscz
    import zipfile
    
    output_filename = "test_output"
    
    # Create JSON and template
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    json_path = temp_output_dir / f"{output_filename}.json"
    template_path = temp_output_dir / f"{output_filename}.mscz"
    reconstructed_path = temp_output_dir / "reconstructed.mscz"
    
    # Reconstruct
    json_to_mscz(
        str(json_path),
        str(reconstructed_path),
        str(template_path)
    )
    
    # Check that non-MSCX files are preserved
    with zipfile.ZipFile(template_path, "r") as template_z:
        template_files = {name for name in template_z.namelist() if not name.endswith(".mscx")}
    
    with zipfile.ZipFile(reconstructed_path, "r") as recon_z:
        recon_files = {name for name in recon_z.namelist() if not name.endswith(".mscx")}
    
    # All template files (except MSCX) should be in reconstructed file
    assert template_files.issubset(recon_files), \
        "Reconstructed file should preserve all non-MSCX files from template"


def test_keysig_timesig_roundtrip(sample_mscz_path, temp_output_dir):
    """Test that KeySig and TimeSig are preserved through roundtrip."""
    from scoreforge.cli import json_to_mscz
    from scoreforge.io import extract_mscx
    from scoreforge.parser import parse_score
    import xml.etree.ElementTree as ET
    
    output_filename = "test_output"
    
    # Create JSON and template
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    json_path = temp_output_dir / f"{output_filename}.json"
    template_path = temp_output_dir / f"{output_filename}.mscz"
    reconstructed_path = temp_output_dir / "reconstructed.mscz"
    
    # Load the JSON to check if it has KeySig/TimeSig
    from scoreforge.serialization import load_score_from_json
    score = load_score_from_json(json_path)
    
    # Check if any measures have KeySig or TimeSig
    has_keysig = any(m.key_sig is not None for part in score.parts for m in part.measures)
    has_timesig = any(m.time_sig is not None for part in score.parts for m in part.measures)
    
    # Reconstruct
    json_to_mscz(
        str(json_path),
        str(reconstructed_path),
        str(template_path)
    )
    
    # Parse the reconstructed file and check for KeySig/TimeSig in XML
    reconstructed_tree = extract_mscx(reconstructed_path)
    root = reconstructed_tree.getroot()
    score_el = root.find("Score")
    
    if has_keysig or has_timesig:
            # Find measures with KeySig or TimeSig (they're inside voice elements)
            measures_with_keysig = []
            measures_with_timesig = []
            
            for measure_el in score_el.findall(".//Measure"):
                voice_el = measure_el.find("voice")
                if voice_el is not None:
                    if voice_el.find("KeySig") is not None:
                        measures_with_keysig.append(measure_el)
                    if voice_el.find("TimeSig") is not None:
                        measures_with_timesig.append(measure_el)
            
            if has_keysig:
                assert len(measures_with_keysig) > 0, \
                    "Reconstructed file should have KeySig elements if original had them"
            
            if has_timesig:
                assert len(measures_with_timesig) > 0, \
                    "Reconstructed file should have TimeSig elements if original had them"
            
            # Verify structure of KeySig/TimeSig
            for measure_el in measures_with_keysig:
                voice_el = measure_el.find("voice")
                key_sig_el = voice_el.find("KeySig") if voice_el is not None else None
                assert key_sig_el is not None, "KeySig element should exist"
                concert_key = key_sig_el.findtext("concertKey")
                assert concert_key is not None, "KeySig should have concertKey"
            
            for measure_el in measures_with_timesig:
                voice_el = measure_el.find("voice")
                time_sig_el = voice_el.find("TimeSig") if voice_el is not None else None
                assert time_sig_el is not None, "TimeSig element should exist"
                sig_n = time_sig_el.findtext("sigN")
                sig_d = time_sig_el.findtext("sigD")
                assert sig_n is not None and sig_d is not None, \
                    "TimeSig should have sigN and sigD"


def test_keysig_timesig_json_structure(sample_mscz_path, temp_output_dir):
    """Test that KeySig and TimeSig are stored in JSON correctly."""
    import json
    
    output_filename = "test_output"
    
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename
    )
    
    json_path = temp_output_dir / f"{output_filename}.json"
    
    # Load JSON and check structure
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Check if any measures have keySig or timeSig
    has_keysig = False
    has_timesig = False
    
    for part_id, part in data["parts"].items():
        for measure_num, measure in part["measures"].items():
            if "keySig" in measure:
                has_keysig = True
                key_sig = measure["keySig"]
                assert "concertKey" in key_sig, "keySig should have concertKey"
                assert isinstance(key_sig["concertKey"], int), "concertKey should be an integer"
            
            if "timeSig" in measure:
                has_timesig = True
                time_sig = measure["timeSig"]
                assert "sigN" in time_sig, "timeSig should have sigN"
                assert "sigD" in time_sig, "timeSig should have sigD"
                assert isinstance(time_sig["sigN"], int), "sigN should be an integer"
                assert isinstance(time_sig["sigD"], int), "sigD should be an integer"
    
    # Note: We don't assert that they must exist, as the test file might not have them
    # But if they exist, they should be in the correct format


def test_measure_len_in_json(sample_mscz_path, temp_output_dir):
    """Test that pickup/irregular measures have 'len' field in the generated JSON."""
    output_filename = "test_output"

    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename,
    )

    json_path = temp_output_dir / f"{output_filename}.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # band-sting-5 has a 1/4 pickup measure as the first measure
    found_measure_len = False
    for part_id, part in data["parts"].items():
        measures = part.get("measures", {})
        if "1" in measures:
            measure_1 = measures["1"]
            if "len" in measure_1:
                assert measure_1["len"] == "1/4", \
                    "First (pickup) measure should have len='1/4'"
                found_measure_len = True
                break

    assert found_measure_len, "At least one part's first measure should have 'len' field (pickup measure)"


def test_measure_len_roundtrip(sample_mscz_path, temp_output_dir):
    """Test that measure length is preserved through mscz -> json -> mscz roundtrip."""
    from scoreforge.cli import json_to_mscz

    output_filename = "test_output"

    # Create JSON and template from source
    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename,
    )

    json_path = temp_output_dir / f"{output_filename}.json"
    template_path = temp_output_dir / f"{output_filename}.mscz"
    reconstructed_path = temp_output_dir / "reconstructed.mscz"

    # Reconstruct MSCZ from JSON and template
    json_to_mscz(
        str(json_path),
        str(reconstructed_path),
        str(template_path),
    )

    # Parse original and reconstructed, compare measure_len
    original_tree = extract_mscx(sample_mscz_path)
    original_score = parse_score(original_tree)

    reconstructed_tree = extract_mscx(reconstructed_path)
    reconstructed_score = parse_score(reconstructed_tree)

    # First measure (pickup) should have measure_len in both
    for orig_part, recon_part in zip(original_score.parts, reconstructed_score.parts):
        assert len(orig_part.measures) > 0 and len(recon_part.measures) > 0
        orig_m1 = orig_part.measures[0]
        recon_m1 = recon_part.measures[0]
        assert orig_m1.measure_len == recon_m1.measure_len, \
            f"Part {orig_part.part_id}: measure_len should match " \
            f"({orig_m1.measure_len} vs {recon_m1.measure_len})"
        if orig_m1.measure_len is not None:
            assert orig_m1.measure_len == "1/4", \
                "Pickup measure should have len '1/4'"


def test_measure_len_in_reconstructed_xml(sample_mscz_path, temp_output_dir):
    """Test that reconstructed MSCX has len attribute on pickup measures."""
    from scoreforge.cli import json_to_mscz

    output_filename = "test_output"

    mscz_to_json(
        str(sample_mscz_path),
        str(temp_output_dir),
        output_filename,
    )

    json_path = temp_output_dir / f"{output_filename}.json"
    template_path = temp_output_dir / f"{output_filename}.mscz"
    reconstructed_path = temp_output_dir / "reconstructed.mscz"

    json_to_mscz(
        str(json_path),
        str(reconstructed_path),
        str(template_path),
    )

    # Check that Measure elements in output have len attribute for pickup
    reconstructed_tree = extract_mscx(reconstructed_path)
    root = reconstructed_tree.getroot()
    measures_with_len = [
        m for m in root.findall(".//Measure")
        if m.get("len") is not None
    ]
    assert len(measures_with_len) > 0, \
        "Reconstructed file should have at least one Measure with len attribute"
    assert all(m.get("len") == "1/4" for m in measures_with_len[:5]), \
        "Pickup measures should have len='1/4'"



