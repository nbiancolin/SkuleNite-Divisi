"""
End-to-end smoke test for the part formatter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mscz_formatter.mscz import format_mscz

# E2E_DIR = Path(__file__).resolve().parent / "test-data" / "e2e"
E2E_DIR = Path(__file__).resolve().parent 


# Score-level export from generate_mpos_for_mscz.py; layout only applies to parts.
_SCORE_MPOS_STEM = "bows" #noqa


def _part_mpos_map(e2e_dir: Path, score_mpos_stem: str) -> dict[str, str]:
    """Map excerpt key → absolute .mpos path for every part fixture."""
    part_mpos: dict[str, str] = {}
    for mpos_path in sorted(e2e_dir.glob("*.mpos")):
        if mpos_path.stem == score_mpos_stem:
            continue
        part_mpos[mpos_path.stem] = str(mpos_path)
    return part_mpos


# Bows:
BOWS_E2E_DIR = E2E_DIR / "bows"
BOWS_INPUT_MSCZ = BOWS_E2E_DIR / "bows.mscz"
BOWS_OUTPUT_MSCZ = BOWS_E2E_DIR / "bows-formatted.mscz"

# Breathe
BREATHE_E2E_DIR = E2E_DIR / "breathe"
BREATHE_INPUT_MSCZ = BREATHE_E2E_DIR / "breathe.mscz"
BREATHE_OUTPUT_MSCZ = BREATHE_E2E_DIR / "breathe-formatted.mscz"

# stars
STARS_E2E_DIR = E2E_DIR / "stars"
STARS_INPUT_MSCZ = STARS_E2E_DIR / "stars.mscz"
STARS_OUTPUT_MSCZ = STARS_E2E_DIR / "stars-formatted.mscz"

@pytest.mark.e2e
@pytest.mark.parametrize(
    "e2e_dir, part_mpos_key, input_mscz, output_mscz", [
        (BOWS_E2E_DIR, "bows", BOWS_INPUT_MSCZ, BOWS_OUTPUT_MSCZ), # Quick canary test
        (BREATHE_E2E_DIR, "breathe", BREATHE_INPUT_MSCZ, BREATHE_OUTPUT_MSCZ), # Longer, better for checking lines
        (STARS_E2E_DIR, "stars", STARS_INPUT_MSCZ, STARS_OUTPUT_MSCZ), # Longest - for checking page turns
    ]
)
def test_format_mscz_for_manual_inspection(e2e_dir, part_mpos_key, input_mscz, output_mscz):
    """Format mscz and leave <>-formatted.mscz for manual review."""
    assert input_mscz.is_file(), f"Missing input score: {input_mscz}"

    part_mpos = _part_mpos_map(e2e_dir, part_mpos_key)
    assert part_mpos, f"No part .mpos files found in {e2e_dir}"

    ok = format_mscz(
        str(input_mscz),
        str(output_mscz),
        part_mpos,
        {
            "selected_style": "broadway",
            "apply_mss_style": True,
            "apply_part_layout": True,
        },
    )
    assert ok, "format_mscz returned False (see logs for details)"
    assert output_mscz.is_file()
    assert output_mscz.stat().st_size > 0

    print(f"\nFormatted score ready for inspection:\n  {output_mscz}\n")
    print(f"Formatted {len(part_mpos)} part(s): {', '.join(part_mpos)}")
