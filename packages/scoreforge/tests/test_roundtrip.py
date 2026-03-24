"""
One test to see if the roundtrip works
"""

def test_roundtrip_for_manual_inspection():
    """Test that converts mscz -> canonical -> mscz for manual inspection.
    
    This test performs a full roundtrip conversion and saves the result
    to the output directory so it can be manually inspected.
    Uses tests/test-data/band-sting-5.mscz as the input file.
    """
    from scoreforge.cli import json_to_mscz, mscz_to_json
    from pathlib import Path
    
    # Use the specific input file
    input_mscz = Path(__file__).parent / "test-data" / "band-sting-5.mscz"
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