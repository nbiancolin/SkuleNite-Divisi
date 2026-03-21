"""
One test to see if the roundtrip works
"""

import pytest

from scoreforge.converter import pitch_to_midi


def test_pitch_to_midi_accepts_flat_and_negative_octave():
    """Regression: Bb; negative octave (D-1 matches midi_to_pitch(2))."""
    assert pitch_to_midi("D-1") == 2
    assert pitch_to_midi("Bb3") == 58


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