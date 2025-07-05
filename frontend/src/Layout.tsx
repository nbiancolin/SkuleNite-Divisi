// Layout.tsx
import { AppShell } from '@mantine/core';
import { HeaderSimple } from './components/headerSimple';
import { Outlet } from 'react-router-dom';

export default function Layout() {
  return (
    <AppShell
      header={{height: 60}}
      padding="md"
    >
      <AppShell.Header>
        <HeaderSimple />
      </AppShell.Header>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
