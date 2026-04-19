"""
Part-formatter step keys for ArrangementVersion and API validation.

Keep in sync with musescore_part_formatter.utils.FORMATTING_STEP_KEYS.
"""

from __future__ import annotations

FORMATTING_STEP_KEYS: tuple[str, ...] = (
    "apply_mss_style",
    "apply_score_metadata",
    "apply_scrub_existing_line_breaks",
    "apply_multimeasure_rest_prep",
    "apply_rehearsal_line_breaks",
    "apply_double_bar_line_breaks",
    "apply_measure_count_line_breaks",
    "apply_line_break_balancing",
    "apply_multimeasure_rest_cleanup",
    "apply_broadway_vbox_header",
    "apply_part_name_in_header",
)

LINE_BREAK_STEP_KEYS: tuple[str, ...] = (
    "apply_rehearsal_line_breaks",
    "apply_double_bar_line_breaks",
    "apply_measure_count_line_breaks",
)

DEFAULT_FORMATTING_STEPS: dict[str, bool] = {
    "apply_mss_style": True,
    "apply_score_metadata": True,
    "apply_scrub_existing_line_breaks": False,
    "apply_multimeasure_rest_prep": True,
    "apply_rehearsal_line_breaks": True,
    "apply_double_bar_line_breaks": True,
    "apply_measure_count_line_breaks": True,
    "apply_line_break_balancing": True,
    "apply_multimeasure_rest_cleanup": True,
    "apply_broadway_vbox_header": True,
    "apply_part_name_in_header": True,
}


def default_formatting_steps() -> dict[str, bool]:
    return dict(DEFAULT_FORMATTING_STEPS)


def merge_formatting_step_defaults(params: dict) -> None:
    """Ensure every apply_* key exists on params (mutates)."""
    for key in FORMATTING_STEP_KEYS:
        if key not in params:
            params[key] = DEFAULT_FORMATTING_STEPS[key]
    if any(params.get(k, True) for k in LINE_BREAK_STEP_KEYS):
        params["apply_multimeasure_rest_prep"] = True
        params["apply_multimeasure_rest_cleanup"] = True
