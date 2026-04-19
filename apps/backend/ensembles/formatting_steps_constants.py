"""
Part-formatter step keys for ArrangementVersion and API validation.

Keep in sync with musescore_part_formatter.utils.FORMATTING_STEP_KEYS.
"""

from __future__ import annotations

FORMATTING_STEP_KEYS: tuple[str, ...] = (
    "apply_mss_style",
    "apply_score_metadata",
    "apply_multimeasure_rest_prep",
    "apply_rehearsal_line_breaks",
    "apply_double_bar_line_breaks",
    "apply_measure_count_line_breaks",
    "apply_line_break_balancing",
    "apply_multimeasure_rest_cleanup",
    "apply_broadway_vbox_header",
    "apply_part_name_in_header",
)


def default_formatting_steps() -> dict[str, bool]:
    return {k: True for k in FORMATTING_STEP_KEYS}


def merge_formatting_step_defaults(params: dict) -> None:
    """Ensure every apply_* key exists on params (mutates)."""
    for key in FORMATTING_STEP_KEYS:
        if key not in params:
            params[key] = True
