import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { matchPath, useLocation } from 'react-router-dom';

export const APP_NAME = 'Divisi App';

const STATIC_ROUTE_TITLES: { path: string; title: string }[] = [
  { path: '/app', title: 'Dashboard' },
  { path: '/app/ensembles', title: 'Ensembles' },
  { path: '/app/ensembles/create', title: 'Create Ensemble' },
  { path: '/app/ensembles/:slug/create-arrangement', title: 'Create Arrangement' },
  { path: '/app/arrangements/:arrangementId/new-commit', title: 'Upload Commit' },
  { path: '/app/arrangements/:arrangementId/new-version', title: 'Upload Version' },
  {
    path: '/app/arrangements/:arrangementId/commits/:commitId/create-version',
    title: 'Create Version',
  },
  { path: '/app/arrangements/:id/review-score', title: 'Review Score' },
  { path: '/part-formatter', title: 'Part Formatter' },
  { path: '/join/:token', title: 'Join Ensemble' },
  { path: '/testing/upload-arrangement', title: 'Upload Arrangement' },
];

function getStaticRouteTitle(pathname: string): string | null {
  for (const { path, title } of STATIC_ROUTE_TITLES) {
    if (matchPath({ path, end: true }, pathname)) {
      return title;
    }
  }
  return null;
}

export function formatArrangementTitle(arrangement: {
  mvt_no?: string | null;
  title: string;
}): string {
  return arrangement.mvt_no ? `${arrangement.mvt_no}: ${arrangement.title}` : arrangement.title;
}

type PageTitleContextValue = {
  setPageTitle: (title: string | null) => void;
};

const PageTitleContext = createContext<PageTitleContextValue | null>(null);

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

export function usePageTitleContext() {
  const context = useContext(PageTitleContext);
  if (!context) {
    throw new Error('usePageTitleContext must be used within PageTitleProvider');
  }
  return context;
}

/** Set the browser tab title for the current page. Resets when the route changes. */
export function usePageTitle(title: string | null) {
  const { setPageTitle } = usePageTitleContext();

  useEffect(() => {
    setPageTitle(title);
  }, [title, setPageTitle]);
}
