"""
MSCZ-level orchestration: unpack/repack, styles, metadata, and per-part MPOS layout.
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
from mscz_formatter.mscx.pages import pages_from_lines
from mscz_formatter.mscz.excerpts import list_excerpts, resolve_part_mpos
from mscz_formatter.mscz.file_processing import unpack_mscz_to_tempdir
from mscz_formatter.mscz.inspect import ScoreInfo, get_all_properties
from mscz_formatter.mscz.metadata import apply_metadata_and_headers_to_mscx
from mscz_formatter.mscz.spatium import normalize_staff_spacing_strategy
from mscz_formatter.mscz.styles import Style, add_styles_to_score_and_parts

LOGGER = getLogger("mscz_formatter")


class FormattingParams(TypedDict):
    selected_style: NotRequired[str | Style]
    staff_spacing_strategy: NotRequired[str]
    staff_spacing_value: NotRequired[str | None]
    show_title: NotRequired[str]
    show_number: NotRequired[str]
    version_num: NotRequired[str]
    work_title: NotRequired[str]
    composer: NotRequired[str]
    arranger: NotRequired[str]
    apply_mss_style: NotRequired[bool]
    apply_score_metadata: NotRequired[bool]
    apply_broadway_vbox_header: NotRequired[bool]
    apply_part_name_in_header: NotRequired[bool]
    apply_part_layout: NotRequired[bool]
    optimize_for_page_turns: NotRequired[bool]


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


def _format_part_with_mpos(
    mscx_path: str,
    mpos_path: str,
    *,
    optimize_for_page_turns: bool = True,
) -> None:
    data = load_in(mscx_path, mpos_path)
    lines = add_line_breaks(data["rendered_measures"])
    pages = pages_from_lines(lines, optimize_for_page_turns=optimize_for_page_turns)
    apply_layout_to_tree(data["tree"], pages, data["measures_by_hash"], mscx_path)


def _apply_metadata_and_headers(mscx_files: list[str], params: dict, style: Style) -> None:
    show_title = params.get("show_title") or ""
    show_number = params.get("show_number") or ""
    version_num = params.get("version_num") or ""
    work_title = params.get("work_title") or ""
    composer = params.get("composer")
    arranger = params.get("arranger")
    apply_score_metadata = params.get("apply_score_metadata", True)
    apply_broadway_vbox_header = params.get("apply_broadway_vbox_header", True)
    apply_part_name_in_header = params.get("apply_part_name_in_header", True)

    if not (
        apply_score_metadata
        or apply_broadway_vbox_header
        or apply_part_name_in_header
    ):
        return

    for mscx_path in mscx_files:
        LOGGER.info("Applying metadata/headers to %s", mscx_path)
        apply_metadata_and_headers_to_mscx(
            mscx_path,
            show_title=show_title,
            show_number=show_number,
            version_num=version_num,
            work_title=work_title,
            composer=composer if isinstance(composer, str) else None,
            arranger=arranger if isinstance(arranger, str) else None,
            apply_score_metadata=apply_score_metadata,
            apply_broadway_vbox_header=apply_broadway_vbox_header,
            apply_part_name_in_header=apply_part_name_in_header,
            is_broadway=style == Style.BROADWAY,
        )


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
            export must appear here when ``apply_part_layout`` is True. Keys may
            be excerpt folder names (``0_Trumpet_in_Bb``), names without index
            (``Trumpet_in_Bb``), or excerpt indices (``0``). May be empty when
            ``apply_part_layout`` is False.
        params: Style, metadata, spatium, and step toggles.

    Pipeline:
      1. Optional MSS styles (score + excerpts)
      2. Optional score metaTags + Broadway / part-name VBox headers
      3. Optional MPOS-based line/page layout on listed parts

    When ``optimize_for_page_turns`` is False, line breaks are still planned
    and applied, but the page-turn DP (page breaks / V.S. blanks) is skipped.
    """
    params = dict(params or {})
    style_name = params.get("selected_style") or "broadway"
    style = style_name if isinstance(style_name, Style) else Style(str(style_name))
    apply_mss_style = params.get("apply_mss_style", True)
    apply_part_layout = params.get("apply_part_layout", True)
    optimize_for_page_turns = params.get("optimize_for_page_turns", True)

    if apply_part_layout and not part_mpos:
        raise ValueError(
            "part_mpos is required when apply_part_layout is True: "
            "provide one .mpos path for each part to export"
        )

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

            _apply_metadata_and_headers(mscx_files, params, style)

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
                    _format_part_with_mpos(
                        excerpt.mscx_path,
                        mpos_path,
                        optimize_for_page_turns=optimize_for_page_turns,
                    )

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
