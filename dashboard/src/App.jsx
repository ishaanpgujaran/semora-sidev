import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';

import LandingPage from './pages/LandingPage';
import DocsPage from './pages/DocsPage';
import EmailLogin from './auth/EmailLogin';
import ProjectPortfolio from './pages/ProjectPortfolio';
import AuditTimeline from './pages/AuditTimeline';
import SpecMatrix from './pages/SpecMatrix';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/login" element={<EmailLogin />} />
        <Route path="/signup" element={<EmailLogin />} />

        {/* Authenticated routes — wrapped in ProtectedRoute + AppLayout */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/portfolio" element={<ProjectPortfolio />} />
            <Route path="/timeline" element={<AuditTimeline />} />
            <Route path="/matrix" element={<SpecMatrix />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
