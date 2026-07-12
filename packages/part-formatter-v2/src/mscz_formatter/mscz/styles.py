"""Apply Broadway / Jazz .mss style templates inside an unpacked MSCZ."""

from __future__ import annotations

import os
import re
from enum import Enum
from logging import getLogger
from pathlib import Path

import importlib.resources as resources

from mscz_formatter.mscz.inspect import set_style_params
from mscz_formatter.mscz.spatium import (
    normalize_staff_spacing_strategy,
    predict_style_params,
)

LOGGER = getLogger("mscz_formatter")


class Style(Enum):
    BROADWAY = "broadway"
    JAZZ = "jazz"


def get_resource_path(filename: str) -> Path:
    return Path(str(resources.files("mscz_formatter").joinpath("resources", filename)))


BROADWAY_SCORE_STYLE_PATH = get_resource_path("broadway_score.mss")
BROADWAY_PART_STYLE_PATH = get_resource_path("broadway_part.mss")
JAZZ_SCORE_STYLE_PATH = get_resource_path("jazz_score.mss")
JAZZ_PART_STYLE_PATH = get_resource_path("jazz_part.mss")


def collect_spatium_from_existing_mss_files(work_dir: str) -> dict[str, str]:
    """
    Read <spatium> from each .mss under work_dir before templates overwrite them.
    Keys are paths relative to work_dir using forward slashes.
    """
    found: dict[str, str] = {}
    for root, _, files in os.walk(work_dir):
        for filename in files:
            if not filename.lower().endswith(".mss"):
                continue
            full_path = os.path.join(root, filename)
            rel = os.path.relpath(full_path, work_dir).replace("\\", "/")
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    txt = f.read()
            except OSError:
                continue
            m = re.search(r"<spatium>\s*([^<]+?)\s*</spatium>", txt)
            if not m:
                continue
            val = m.group(1).strip()
            if val and not val.startswith("DIVISI:"):
                found[rel] = val
    return found


def _style_params_for_mss(
    *,
    strategy: str,
    rel_key: str,
    is_excerpt: bool,
    score_info,
    preserved: dict[str, str],
    override_value: str | None,
) -> dict[str, str]:
    strategy = normalize_staff_spacing_strategy(strategy)
    if strategy == "override" and override_value:
        return {"staff_spacing": override_value}
    if strategy == "preserve":
        raw = preserved.get(rel_key)
        if raw:
            return {"staff_spacing": raw}
    if is_excerpt:
        return predict_style_params({"num_staves": 1})
    return predict_style_params(score_info)


def add_styles_to_score_and_parts(
    style: Style,
    work_dir: str,
    score_info=None,
    staff_spacing_strategy: str = "predict",
    staff_spacing_value: str | None = None,
) -> None:
    """
    Replace every .mss under work_dir with the Broadway/Jazz score or part template.
    """
    if style == Style.BROADWAY:
        score_style_path = BROADWAY_SCORE_STYLE_PATH
        part_style_path = BROADWAY_PART_STYLE_PATH
    elif style == Style.JAZZ:
        score_style_path = JAZZ_SCORE_STYLE_PATH
        part_style_path = JAZZ_PART_STYLE_PATH
    else:
        raise ValueError(f"Unsupported style: {style}")

    strategy = normalize_staff_spacing_strategy(staff_spacing_strategy)
    override_val = (staff_spacing_value or "").strip() or None
    preserved: dict[str, str] = {}
    if strategy == "preserve":
        preserved = collect_spatium_from_existing_mss_files(work_dir)

    for root, _, files in os.walk(work_dir):
        for filename in files:
            if not filename.lower().endswith(".mss"):
                continue

            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, work_dir)
            rel_key = rel_path.replace("\\", "/")
            is_excerpt = "Excerpts" in rel_path

            source_style = part_style_path if is_excerpt else score_style_path
            style_params = _style_params_for_mss(
                strategy=strategy,
                rel_key=rel_key,
                is_excerpt=is_excerpt,
                score_info=score_info,
                preserved=preserved,
                override_value=override_val,
            )

            with open(source_style, "r", encoding="utf-8") as f:
                style_text = set_style_params(f.read(), **style_params)

            with open(full_path, "w", encoding="utf-8") as out_f:
                out_f.write(style_text)

            LOGGER.info(
                "Replaced %s style: %s",
                "part" if is_excerpt else "score",
                full_path,
            )
