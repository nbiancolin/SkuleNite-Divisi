"""
End-to-end smoke test for the part formatter.

Runs the full pipeline on ``bows.mscz`` with the sibling per-part ``.mpos``
files, then writes a finished ``.mscz`` next to the fixtures so you can open
it in MuseScore and inspect layout by eye.

Usage::

    pytest packages/part-formatter-v2/tests/e2e.py -s
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mscz_formatter.mscz import format_mscz

E2E_DIR = Path(__file__).resolve().parent / "test-data" / "e2e"
INPUT_MSCZ = E2E_DIR / "bows.mscz"
OUTPUT_MSCZ = E2E_DIR / "bows-formatted.mscz"

# Score-level export from generate_mpos_for_mscz.py; layout only applies to parts.
_SCORE_MPOS_STEM = "bows"


def _part_mpos_map(e2e_dir: Path) -> dict[str, str]:
    """Map excerpt key → absolute .mpos path for every part fixture."""
    part_mpos: dict[str, str] = {}
    for mpos_path in sorted(e2e_dir.glob("*.mpos")):
        if mpos_path.stem == _SCORE_MPOS_STEM:
            continue
        part_mpos[mpos_path.stem] = str(mpos_path)
    return part_mpos


@pytest.mark.e2e
def test_format_bows_mscz_for_manual_inspection():
    """Format bows.mscz and leave bows-formatted.mscz for manual review."""
    assert INPUT_MSCZ.is_file(), f"Missing input score: {INPUT_MSCZ}"

    part_mpos = _part_mpos_map(E2E_DIR)
    assert part_mpos, f"No part .mpos files found in {E2E_DIR}"

    ok = format_mscz(
        str(INPUT_MSCZ),
        str(OUTPUT_MSCZ),
        part_mpos,
        {
            "selected_style": "broadway",
            "apply_mss_style": True,
            "apply_part_layout": True,
        },
    )
    assert ok, "format_mscz returned False (see logs for details)"
    assert OUTPUT_MSCZ.is_file()
    assert OUTPUT_MSCZ.stat().st_size > 0

    print(f"\nFormatted score ready for inspection:\n  {OUTPUT_MSCZ}\n")
    print(f"Formatted {len(part_mpos)} part(s): {', '.join(part_mpos)}")
