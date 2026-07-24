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
      {row(
        value.apply_mss_style,
        (v) => patch({ apply_mss_style: v }),
        "Apply MSS style (Broadway / Jazz templates)"
      )}
      {row(
        value.apply_score_metadata,
        (v) => patch({ apply_score_metadata: v }),
        "Score metadata (show title, number, version in file properties)"
      )}
      {row(
        value.apply_part_layout,
        (v) => patch({ apply_part_layout: v }),
        "Part layout (MPOS-based line breaks and page turns)"
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
