// Layout.tsx
import { AppShell } from '@mantine/core';
import { HeaderSimple } from './components/headerSimple';
import { Outlet } from 'react-router-dom';

export default function Layout() {
  return (
    <AppShell
      header={<HeaderSimple />}
    >
      <Outlet />
    </AppShell>
  );
}
