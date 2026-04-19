/** Mirrors musescore_part_formatter.utils.FORMATTING_STEP_KEYS */

export const FORMATTING_STEP_KEYS = [
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
] as const;

export type FormattingStepKey = (typeof FORMATTING_STEP_KEYS)[number];

export type FormattingStepsState = Record<FormattingStepKey, boolean>;

const FORMATTING_STEP_DEFAULTS: FormattingStepsState = {
  apply_mss_style: true,
  apply_score_metadata: true,
  apply_scrub_existing_line_breaks: false,
  apply_multimeasure_rest_prep: true,
  apply_rehearsal_line_breaks: true,
  apply_double_bar_line_breaks: true,
  apply_measure_count_line_breaks: true,
  apply_line_break_balancing: true,
  apply_multimeasure_rest_cleanup: true,
  apply_broadway_vbox_header: true,
  apply_part_name_in_header: true,
};

export function defaultFormattingSteps(): FormattingStepsState {
  return { ...FORMATTING_STEP_DEFAULTS };
}

const LINE_BREAK_STEP_KEYS: readonly FormattingStepKey[] = [
  "apply_rehearsal_line_breaks",
  "apply_double_bar_line_breaks",
  "apply_measure_count_line_breaks",
];

export function normalizedFormattingSteps(value: FormattingStepsState): FormattingStepsState {
  const next = { ...value };
  const hasLineBreakStepEnabled = LINE_BREAK_STEP_KEYS.some((key) => next[key]);
  if (hasLineBreakStepEnabled) {
    next.apply_multimeasure_rest_prep = true;
    next.apply_multimeasure_rest_cleanup = true;
  }
  return next;
}
