"""
MSCZ container processing: unpack/repack, styles, excerpt discovery, and
orchestrating one MPOS file per part to export.
"""

from mscz_formatter.mscz.excerpts import ExcerptInfo, list_excerpts, resolve_part_mpos
from mscz_formatter.mscz.file_processing import unpack_mscz_to_tempdir
from mscz_formatter.mscz.format import FormattingParams, format_mscz, get_score_attributes
from mscz_formatter.mscz.inspect import ScoreInfo
from mscz_formatter.mscz.styles import Style, add_styles_to_score_and_parts

__all__ = [
    "ExcerptInfo",
    "FormattingParams",
    "ScoreInfo",
    "Style",
    "add_styles_to_score_and_parts",
    "format_mscz",
    "get_score_attributes",
    "list_excerpts",
    "resolve_part_mpos",
    "unpack_mscz_to_tempdir",
]
