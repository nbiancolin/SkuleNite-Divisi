import { useCallback, useState } from 'react';
import { ActionIcon, Menu, useMantineColorScheme } from '@mantine/core';
import { IconDeviceDesktop, IconMoon, IconSun } from '@tabler/icons-react';
import type { MantineColorScheme } from '@mantine/core';

const SCHEME_OPTIONS: {
  value: MantineColorScheme;
  label: string;
  icon: typeof IconSun;
}[] = [
  { value: 'light', label: 'Light', icon: IconSun },
  { value: 'dark', label: 'Dark', icon: IconMoon },
  { value: 'auto', label: 'System', icon: IconDeviceDesktop },
];

function readStoredColorScheme(): MantineColorScheme {
  try {
    const stored = localStorage.getItem('mantine-color-scheme-value');
    if (stored === 'light' || stored === 'dark' || stored === 'auto') {
      return stored;
    }
  } catch {
    /* ignore */
  }
  return 'light';
}

function schemeIcon(scheme: MantineColorScheme) {
  const match = SCHEME_OPTIONS.find((o) => o.value === scheme);
  const Icon = match?.icon ?? IconDeviceDesktop;
  return <Icon size={18} stroke={1.5} />;
}

export function ColorSchemeSwitcher() {
  const { setColorScheme } = useMantineColorScheme();
  const [preference, setPreference] = useState<MantineColorScheme>(readStoredColorScheme);

  const selectScheme = useCallback(
    (value: MantineColorScheme) => {
      setColorScheme(value);
      setPreference(value);
    },
    [setColorScheme]
  );

  return (
    <Menu shadow="md" width={160} withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="default"
          size="lg"
          aria-label="Color scheme"
          title="Color scheme"
        >
          {schemeIcon(preference)}
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        {SCHEME_OPTIONS.map(({ value, label, icon: Icon }) => (
          <Menu.Item
            key={value}
            leftSection={<Icon size={16} stroke={1.5} />}
            onClick={() => selectScheme(value)}
            fw={preference === value ? 600 : 400}
          >
            {label}
          </Menu.Item>
        ))}
      </Menu.Dropdown>
    </Menu>
  );
}
