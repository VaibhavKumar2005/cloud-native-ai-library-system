import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './Dashboard';
import AcademicDashboard from './AcademicDashboard';
import Monitoring from './Monitoring';
import Analytics from './Analytics';
import Login from './Login';
import GitHubHealthChecker from './GitHubHealthChecker';
import Research from './pages/Research';
import { clearSession } from './lib/auth';

// ── Auth Guard: In DEMO_MODE, skip all auth checks ──────────
// For demo/testing, bypass the login requirement entirely
function ProtectedRoute({ children, adminOnly = false }) {
  // DEMO MODE: Always allow access, skip auth checks
  return children;
}

export default function App() {
  const handleLogout = () => {
    clearSession();
    window.location.href = '/';
  };

  const showLegacyUI = import.meta.env.VITE_LEGACY_UI === 'true';

  return (
    <Router>
      <Routes>
        <Route path="/" element={<Research onLogout={handleLogout} />} />
        <Route path="/tools/github-health-checker" element={<GitHubHealthChecker />} />
        <Route path="/login" element={<Navigate to="/" replace />} />

        {/* NEW: Main Research Interface (replaces /app) */}
        <Route path="/research" element={
          <ProtectedRoute>
            <Research onLogout={handleLogout} />
          </ProtectedRoute>
        } />
        
        {/* Admin-Only: Monitoring (requires is_staff on backend) */}
        <Route path="/admin/monitoring" element={
          <ProtectedRoute adminOnly>
            <Monitoring />
          </ProtectedRoute>
        } />

        {/* Legacy Routes (hidden by default, enabled with REACT_APP_LEGACY_UI=true) */}
        {showLegacyUI && (
          <>
            <Route path="/app" element={
              <ProtectedRoute>
                <Dashboard onLogout={handleLogout} />
              </ProtectedRoute>
            } />
            
            <Route path="/research-old" element={
              <ProtectedRoute>
                <AcademicDashboard onLogout={handleLogout} />
              </ProtectedRoute>
            } />
            
            <Route path="/app/monitoring" element={
              <ProtectedRoute>
                <Monitoring />
              </ProtectedRoute>
            } />
            
            <Route path="/app/analytics" element={
              <ProtectedRoute>
                <Analytics />
              </ProtectedRoute>
            } />
          </>
        )}

        {/* Redirect legacy monitoring to new admin route */}
        <Route path="/monitoring" element={<Navigate to="/admin/monitoring" replace />} />
        <Route path="/analytics" element={<Navigate to="/admin/monitoring" replace />} />

        {/* Fallback: Redirect unknown routes to the demo query UI */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
