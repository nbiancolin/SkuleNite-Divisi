import { Routes, Route } from 'react-router-dom';
import Layout from './Layout';
import LandingPage from './pages/LandingPage';
import NotFound from './pages/NotFound';
import EnsemblesPage from './pages/ensembles/EnsemblesPage';
import CreateEnsemblePage from './pages/ensembles/CreateEnsemblePage'
import CreateArrangementPage from './pages/ensembles/CreateArrangementPage'
import ArrangementsPage from './pages/ensembles/ArrangementsPage';
import UploadArrangementVersionPage from './pages/ensembles/UploadArrangementVersionPage';
import {UploadPartsForm} from './pages/testing/UploadPartsForm'
import PartFormatterPage from './pages/PartFormatterPage'
import HomePage from './pages/ensembles/HomePage';

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/app" element={<HomePage />} />
        <Route path="/app/ensembles" element={<EnsemblesPage />} />
        <Route path="/app/ensembles/create" element={<CreateEnsemblePage />} />
        <Route path="/app/ensembles/:slug/arrangements" element={<ArrangementsPage />} />
        <Route path="/app/ensembles/:slug/create-arrangement" element={<CreateArrangementPage />} />
        {/* Future routes */}
        <Route path="/app/arrangements/:slug" element={<div>Arrangement Detail Page (Coming Soon)</div>} />
        {/* route: /arangements/:slug/v/(latest || versionNum) should get a specific version */}
        <Route path="/app/arrangements/:slug/edit" element={<div>Edit Arrangement Page (Coming Soon)</div>} />
        <Route path="/app/arrangements/:arrangementId/new-version" element={<UploadArrangementVersionPage />} />
        <Route path="/testing/upload-arrangement" element={<UploadPartsForm />} />

        <Route path="/part-formatter" element={<PartFormatterPage/>} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default App