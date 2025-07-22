import { Routes, Route } from 'react-router-dom';
import Layout from './Layout';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import NotFound from './pages/NotFound';
import EnsemblesPage from './pages/testing/Ensembles';
import ArrangementsPage from './pages/testing/Arrangements';
import {UploadPartsForm} from './pages/testing/UploadPartsForm'
import PartFormatterPage from './pages/PartFormatterPage'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/app/dashboard" element={<Dashboard />} />
        // app/score page eventually (for viewing scores)
        <Route path="/testing/ensembles" element={<EnsemblesPage />} />
        <Route path="/testing/arrangements" element={<ArrangementsPage />} />
        <Route path="/testing/upload-arrangement" element={<UploadPartsForm />} />

        <Route path="/part-formatter" element={<PartFormatterPage/>} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default App