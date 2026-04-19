/** Mirrors musescore_part_formatter.utils.FORMATTING_STEP_KEYS */

export const FORMATTING_STEP_KEYS = [
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
] as const;

export type FormattingStepKey = (typeof FORMATTING_STEP_KEYS)[number];

export type FormattingStepsState = Record<FormattingStepKey, boolean>;

export function defaultFormattingSteps(): FormattingStepsState {
  return Object.fromEntries(FORMATTING_STEP_KEYS.map((k) => [k, true])) as FormattingStepsState;
}
