import { createContext } from 'react';

export type PageTitleContextValue = {
  setPageTitle: (title: string | null) => void;
};

export const PageTitleContext = createContext<PageTitleContextValue | null>(null);
