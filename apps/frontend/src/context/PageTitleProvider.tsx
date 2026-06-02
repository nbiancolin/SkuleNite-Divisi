import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

import { PageTitleContext } from './pageTitleContext';
import { APP_NAME, getStaticRouteTitle } from './pageTitleUtils';

export function PageTitleProvider({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const [overrideTitle, setOverrideTitle] = useState<string | null>(null);

  useEffect(() => {
    setOverrideTitle(null);
  }, [pathname]);

  const routeTitle = getStaticRouteTitle(pathname);
  const pageTitle = overrideTitle ?? routeTitle;
  const documentTitle = pageTitle ? `${pageTitle} - ${APP_NAME}` : APP_NAME;

  useEffect(() => {
    document.title = documentTitle;
  }, [documentTitle]);

  const setPageTitle = useCallback((title: string | null) => {
    setOverrideTitle(title);
  }, []);

  const value = useMemo(() => ({ setPageTitle }), [setPageTitle]);

  return <PageTitleContext.Provider value={value}>{children}</PageTitleContext.Provider>;
}
