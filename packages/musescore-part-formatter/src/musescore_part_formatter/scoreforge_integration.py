from __future__ import annotations

import tempfile
from pathlib import Path

from scoreforge.cli import json_to_mscz, mscz_to_json

from .main import format_mscz
from .utils import FormattingParams


def format_scoreforge_checkout(
    *,
    checkout_dir: Path,
    output_mscz_path: Path,
    params: FormattingParams,
) -> None:
    """
    Format a scoreforge canonical checkout for rendering.

    Steps:
    1) Build an MSCZ from checkout canonical files.
    2) Apply part-formatter styling + layout changes to that MSCZ.
    3) Re-generate canonical files from the formatted MSCZ so canonical.json
       contains line/page breaks and related layout state.
    """
    canonical_json_path = checkout_dir / "canonical.json"
    canonical_template_path = checkout_dir / "canonical.mscz"

    if not canonical_json_path.is_file():
        raise FileNotFoundError(f"Missing canonical JSON: {canonical_json_path}")

    with tempfile.TemporaryDirectory(prefix="scoreforge_format_") as tmp:
        tmp_dir = Path(tmp)
        unformatted_mscz_path = tmp_dir / "unformatted.mscz"

        if canonical_template_path.is_file():
            json_to_mscz(
                str(canonical_json_path),
                str(unformatted_mscz_path),
                str(canonical_template_path),
            )
        else:
            json_to_mscz(str(canonical_json_path), str(unformatted_mscz_path))

        success = format_mscz(
            str(unformatted_mscz_path),
            str(output_mscz_path),
            params,
        )
        if not success:
            raise RuntimeError("part_formatter failed while formatting scoreforge checkout")

        # Keep canonical in sync with the rendered result.
        mscz_to_json(str(output_mscz_path), str(checkout_dir), "canonical")
