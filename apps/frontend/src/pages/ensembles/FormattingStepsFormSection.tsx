import { Checkbox, Stack, Text, Button } from "@mantine/core";
import type { FormattingStepsState } from "./formattingSteps";
import { defaultFormattingSteps } from "./formattingSteps";

type Props = {
  value: FormattingStepsState;
  onChange: (next: FormattingStepsState) => void;
};

function row(
  checked: boolean,
  onChecked: (v: boolean) => void,
  label: string,
  description?: string
) {
  return (
    <Checkbox
      checked={checked}
      onChange={(e) => onChecked(e.currentTarget.checked)}
      label={label}
      description={description}
    />
  );
}

export default function FormattingStepsFormSection({ value, onChange }: Props) {
  const patch = (partial: Partial<FormattingStepsState>) => {
    onChange({ ...value, ...partial });
  };

  return (
    <Stack gap="sm" mt="md">
      <Text size="sm" fw={600}>
        Part formatter steps
      </Text>
      <Text size="xs" c="dimmed">
        Turn off steps you do not want. Defaults match the full Divisi pipeline.
      </Text>

      <Text size="xs" fw={500} mt="xs">
        Score appearance
      </Text>
      {row(value.apply_mss_style, (v) => patch({ apply_mss_style: v }), "Apply MSS style (Broadway / Jazz templates)")}
      {row(
        value.apply_score_metadata,
        (v) => patch({ apply_score_metadata: v }),
        "Score metadata (show title, number, version in file properties)"
      )}

      <Text size="xs" fw={500} mt="xs">
        Line breaks
      </Text>
      {row(
        value.apply_scrub_existing_line_breaks,
        (v) => patch({ apply_scrub_existing_line_breaks: v }),
        "Scrub all existing line breaks before applying formatter line breaks"
      )}
      {row(
        value.apply_rehearsal_line_breaks,
        (v) => patch({ apply_rehearsal_line_breaks: v }),
        "Line breaks before rehearsal marks"
      )}
      {row(
        value.apply_double_bar_line_breaks,
        (v) => patch({ apply_double_bar_line_breaks: v }),
        "Line breaks at double barlines"
      )}
      {row(
        value.apply_measure_count_line_breaks,
        (v) => patch({ apply_measure_count_line_breaks: v }),
        "Line breaks every N measures (uses score/part counts above)"
      )}
      {row(
        value.apply_line_break_balancing,
        (v) => patch({ apply_line_break_balancing: v }),
        "Balance short lines (final pass)"
      )}

      <Text size="xs" fw={500} mt="xs">
        Headers
      </Text>
      {row(
        value.apply_broadway_vbox_header,
        (v) => patch({ apply_broadway_vbox_header: v }),
        "Broadway header block (show number & title in the part header)"
      )}
      {row(
        value.apply_part_name_in_header,
        (v) => patch({ apply_part_name_in_header: v }),
        "Part name in header (e.g. CONDUCTOR SCORE)"
      )}

      <Button variant="subtle" size="compact-xs" onClick={() => onChange(defaultFormattingSteps())}>
        Reset all steps to on
      </Button>
    </Stack>
  );
}
