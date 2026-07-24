/** Mirrors part-formatter-v2 FormattingParams apply_* flags (plus legacy layout aliases). */

export const FORMATTING_STEP_KEYS = [
  "apply_mss_style",
  "apply_score_metadata",
  "apply_part_layout",
  "apply_broadway_vbox_header",
  "apply_part_name_in_header",
] as const;

export type FormattingStepKey = (typeof FORMATTING_STEP_KEYS)[number];

export type FormattingStepsState = Record<FormattingStepKey, boolean>;

const FORMATTING_STEP_DEFAULTS: FormattingStepsState = {
  apply_mss_style: true,
  apply_score_metadata: true,
  apply_part_layout: true,
  apply_broadway_vbox_header: true,
  apply_part_name_in_header: true,
};

export function defaultFormattingSteps(): FormattingStepsState {
  return { ...FORMATTING_STEP_DEFAULTS };
}

export function normalizedFormattingSteps(value: FormattingStepsState): FormattingStepsState {
  return { ...value };
}
