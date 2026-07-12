"""
MSCZ-level orchestration: unpack/repack, styles, and per-part MPOS layout.
"""

from __future__ import annotations

from logging import getLogger
from typing import NotRequired, TypedDict
import os
import shutil
import xml.etree.ElementTree as ET

from mscz_formatter.mscx.apply import apply_layout_to_tree
from mscz_formatter.mscx.lines import add_line_breaks
from mscz_formatter.mscx.load import load_in
from mscz_formatter.mscx.pages import add_page_breaks
from mscz_formatter.mscz.excerpts import list_excerpts, resolve_part_mpos
from mscz_formatter.mscz.file_processing import unpack_mscz_to_tempdir
from mscz_formatter.mscz.inspect import ScoreInfo, get_all_properties
from mscz_formatter.mscz.spatium import normalize_staff_spacing_strategy
from mscz_formatter.mscz.styles import Style, add_styles_to_score_and_parts

LOGGER = getLogger("mscz_formatter")


class FormattingParams(TypedDict):
    selected_style: NotRequired[str | Style]
    staff_spacing_strategy: NotRequired[str]
    staff_spacing_value: NotRequired[str | None]
    apply_mss_style: NotRequired[bool]
    apply_part_layout: NotRequired[bool]


def get_score_attributes(input_path: str) -> ScoreInfo:
    """Parse score-level metadata / staff counts from the root MSCX inside an MSCZ."""
    with unpack_mscz_to_tempdir(input_path, repack=False) as (_work_dir, mscx_files):
        target = ""
        for mscx_path in mscx_files:
            if "Excerpts" not in mscx_path:
                target = mscx_path
                break
        if not target:
            raise ValueError("No score .mscx found in MSCZ (expected a non-Excerpts file)")

        tree = ET.parse(target)
        root = tree.getroot()
        score = root.find("Score")
        if score is None:
            raise ValueError("No <Score> tag found in the XML.")
        return get_all_properties(score)


def _format_part_with_mpos(mscx_path: str, mpos_path: str) -> None:
    data = load_in(mscx_path, mpos_path)
    lines = add_line_breaks(data["rendered_measures"])
    pages = add_page_breaks(lines)
    apply_layout_to_tree(data["tree"], pages, data["measures_by_hash"], mscx_path)


def format_mscz(
    input_path: str,
    output_path: str,
    part_mpos: dict[str, str],
    params: FormattingParams | dict | None = None,
) -> bool:
    """
    Format one MSCZ using one MPOS file per part that should be exported.

    Args:
        input_path: Source ``.mscz`` (score + embedded Excerpts).
        output_path: Destination ``.mscz``.
        part_mpos: Map of part key → ``.mpos`` path. Every part you expect to
            export must appear here. Keys may be excerpt folder names
            (``0_Trumpet_in_Bb``), names without index (``Trumpet_in_Bb``), or
            excerpt indices (``0``).
        params: Optional style / spatium options.

    Styles are applied to the score and all excerpts. MPOS-based line/page
    layout is applied only to parts listed in ``part_mpos``.
    """
    params = dict(params or {})
    if not part_mpos:
        raise ValueError(
            "part_mpos is required: provide one .mpos path for each part to export"
        )

    style_name = params.get("selected_style") or "broadway"
    style = style_name if isinstance(style_name, Style) else Style(str(style_name))
    apply_mss_style = params.get("apply_mss_style", True)
    apply_part_layout = params.get("apply_part_layout", True)

    staff_spacing_strategy = normalize_staff_spacing_strategy(
        params.get("staff_spacing_strategy")
    )
    raw_val = params.get("staff_spacing_value")
    if raw_val is not None and not isinstance(raw_val, str):
        raw_val = str(raw_val)
    staff_spacing_value = (raw_val or "").strip() or None

    shutil.copyfile(input_path, output_path)
    score_info = get_score_attributes(input_path)

    try:
        with unpack_mscz_to_tempdir(output_path) as (work_dir, mscx_files):
            if apply_mss_style:
                add_styles_to_score_and_parts(
                    style,
                    work_dir,
                    score_info=score_info,
                    staff_spacing_strategy=staff_spacing_strategy,
                    staff_spacing_value=staff_spacing_value,
                )

            excerpts = list_excerpts(work_dir, mscx_files)
            if not excerpts:
                LOGGER.warning("No Excerpts/*.mscx parts found in %s", input_path)

            resolved = resolve_part_mpos(excerpts, part_mpos)

            if apply_part_layout:
                for excerpt_key, (excerpt, mpos_path) in resolved.items():
                    LOGGER.info(
                        "Formatting part %s with MPOS %s",
                        excerpt_key,
                        mpos_path,
                    )
                    _format_part_with_mpos(excerpt.mscx_path, mpos_path)

    except Exception:
        LOGGER.exception("Failed to process %s", input_path)
        if os.path.exists(output_path) and os.path.abspath(output_path) != os.path.abspath(
            input_path
        ):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return False

    return True
