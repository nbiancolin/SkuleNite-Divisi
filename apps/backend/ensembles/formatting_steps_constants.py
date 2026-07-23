"""
Part-formatter step keys for ArrangementVersion and API validation.

Keep in sync with part-formatter-v2 (mscz_formatter) FormattingParams apply_* flags.
Legacy v1 line-break step keys are still accepted on input and mapped to
``apply_part_layout``.
"""

from __future__ import annotations

FORMATTING_STEP_KEYS: tuple[str, ...] = (
    "apply_mss_style",
    "apply_score_metadata",
    "apply_part_layout",
    "apply_broadway_vbox_header",
    "apply_part_name_in_header",
)

# Old heuristic line-break toggles — accepted for backward compat, folded into layout.
LEGACY_LAYOUT_STEP_KEYS: tuple[str, ...] = (
    "apply_scrub_existing_line_breaks",
    "apply_multimeasure_rest_prep",
    "apply_rehearsal_line_breaks",
    "apply_double_bar_line_breaks",
    "apply_measure_count_line_breaks",
    "apply_line_break_balancing",
    "apply_multimeasure_rest_cleanup",
)

# Keys clients may send (canonical + legacy).
ACCEPTED_FORMATTING_STEP_KEYS: frozenset[str] = frozenset(
    FORMATTING_STEP_KEYS + LEGACY_LAYOUT_STEP_KEYS
)

# Kept for older imports that reference LINE_BREAK_STEP_KEYS.
LINE_BREAK_STEP_KEYS: tuple[str, ...] = (
    "apply_rehearsal_line_breaks",
    "apply_double_bar_line_breaks",
    "apply_measure_count_line_breaks",
)

DEFAULT_FORMATTING_STEPS: dict[str, bool] = {
    "apply_mss_style": True,
    "apply_score_metadata": True,
    "apply_part_layout": True,
    "apply_broadway_vbox_header": True,
    "apply_part_name_in_header": True,
}


def default_formatting_steps() -> dict[str, bool]:
    return dict(DEFAULT_FORMATTING_STEPS)


def score_metadata_only_formatting_steps() -> dict[str, bool]:
    """Only embed show title/number/version in the MSCZ; no layout or style changes."""
    return {key: key == "apply_score_metadata" for key in FORMATTING_STEP_KEYS}


def merge_formatting_step_defaults(params: dict) -> None:
    """Ensure every canonical apply_* key exists on params (mutates)."""
    for key in FORMATTING_STEP_KEYS:
        if key not in params:
            params[key] = DEFAULT_FORMATTING_STEPS[key]


def normalize_formatting_steps(raw: dict) -> dict[str, bool]:
    """
    Map a partial / legacy step dict onto the canonical v2 keys.

    Legacy line-break flags imply ``apply_part_layout`` when that key is absent.
    """
    base = default_formatting_steps()
    for key in FORMATTING_STEP_KEYS:
        if key in raw:
            base[key] = bool(raw[key])

    if "apply_part_layout" not in raw:
        legacy_present = [k for k in LEGACY_LAYOUT_STEP_KEYS if k in raw]
        if legacy_present:
            # Any legacy layout-related step that is True → layout on.
            # scrub defaults False in v1; treat scrub alone as not enabling layout.
            layout_signal_keys = [
                k
                for k in LEGACY_LAYOUT_STEP_KEYS
                if k != "apply_scrub_existing_line_breaks"
            ]
            if any(k in raw for k in layout_signal_keys):
                base["apply_part_layout"] = any(bool(raw.get(k)) for k in layout_signal_keys)

    return base
