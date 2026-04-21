import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import { Center, Loader } from "@mantine/core";
import Layout from "./Layout";
import LandingPage from "./pages/LandingPage";
import NotFound from "./pages/NotFound";
import EnsemblesPage from "./pages/ensembles/EnsemblesPage";
import CreateEnsemblePage from "./pages/ensembles/CreateEnsemblePage";
import CreateArrangementPage from "./pages/ensembles/CreateArrangementPage";
import ArrangementsPage from "./pages/ensembles/EnsembleArrangementsPage";
import HomePage from "./pages/ensembles/HomePage";
import JoinEnsemblePage from "./pages/ensembles/JoinEnsemblePage";

const UploadArrangementVersionFromCommitPage = lazy(
  () => import("./pages/ensembles/UploadArrangementVersionAsCommitPage")
);
const UploadArrangementVersionDirectlyPage = lazy(
  () => import("./pages/ensembles/UploadArrangementVersionDirectlyPage")
);
const CreateVersionFromCommitPage = lazy(() => import("./pages/ensembles/CreateVersionFromCommitPage"));
const ArrangementDisplay = lazy(() => import("./pages/ensembles/ArrangementDetailPage"));
const UploadPartsForm = lazy(() =>
  import("./pages/testing/UploadPartsForm").then((m) => ({ default: m.UploadPartsForm }))
);
const PartFormatterPage = lazy(() => import("./pages/PartFormatterPage"));
const EnsembleDisplay = lazy(() => import("./pages/ensembles/EnsembleDetailPage"));

function RouteFallback() {
  return (
    <Center p="xl">
      <Loader size="lg" />
    </Center>
  );
}

export function AppRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/join/:token" element={<JoinEnsemblePage />} />
          <Route path="/app" element={<HomePage />} />
          <Route path="/app/ensembles" element={<EnsemblesPage />} />
          <Route path="/app/ensembles/create" element={<CreateEnsemblePage />} />
          <Route path="/app/ensembles/:slug" element={<EnsembleDisplay />} />
          <Route path="/app/ensembles/:slug/arrangements" element={<ArrangementsPage />} />
          <Route path="/app/ensembles/:slug/create-arrangement" element={<CreateArrangementPage />} />
          <Route path="/app/arrangements/:arrangementId" element={<ArrangementDisplay />} />
          <Route path="/app/arrangements/:slug/edit" element={<div>Edit Arrangement Page (Coming Soon)</div>} />
          <Route path="/app/arrangements/:arrangementId/new-commit" element={<UploadArrangementVersionFromCommitPage />} />
          <Route path="/app/arrangements/:arrangementId/new-version" element={<UploadArrangementVersionDirectlyPage />} />
          <Route
            path="/app/arrangements/:arrangementId/commits/:commitId/create-version"
            element={<CreateVersionFromCommitPage />}
          />
          <Route path="/testing/upload-arrangement" element={<UploadPartsForm />} />
          <Route path="/part-formatter" element={<PartFormatterPage />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
