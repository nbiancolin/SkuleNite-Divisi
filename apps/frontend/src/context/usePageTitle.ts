import { useContext, useEffect } from 'react';

import { PageTitleContext } from './pageTitleContext';

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
