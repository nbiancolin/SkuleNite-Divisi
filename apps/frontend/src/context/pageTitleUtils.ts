import { matchPath } from 'react-router-dom';

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

export function getStaticRouteTitle(pathname: string): string | null {
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
