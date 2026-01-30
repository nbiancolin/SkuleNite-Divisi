// Layout.tsx
import { AppShell } from '@mantine/core';
import { HeaderSimple } from './components/HeaderSimple';
import { Outlet } from 'react-router-dom';
import { useEffect } from 'react';
import { apiService } from './services/apiService';

export default function Layout() {
  // Fetch CSRF token on app initialization to ensure cookie is set
  //TODO: Uncomment this if still getting CSRF errors
  useEffect(() => {
    apiService.fetchCsrfToken();
  }, []);

  return (
    <AppShell
      header={{height: 60}}
      padding="md"
    >
      <AppShell.Header>
        <HeaderSimple />
      </AppShell.Header>
      {/* Ensure the main content area is the scroll container */}
      <AppShell.Main style={{ height: 'calc(100dvh - 60px)', overflowY: 'auto' }}>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
