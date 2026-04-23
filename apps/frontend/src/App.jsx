import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './Dashboard';
import AcademicDashboard from './AcademicDashboard';
import Monitoring from './Monitoring';
import Analytics from './Analytics';
import Login from './Login';
import LandingPage from './LandingPage';
import GitHubHealthChecker from './GitHubHealthChecker';
import Research from './pages/Research';
import { clearSession, isAuthenticated } from './lib/auth';

// ── Auth Guard: Redirects unauthenticated users to /login ──────────
function ProtectedRoute({ children, adminOnly = false }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  
  // TODO: Check admin status from user profile if adminOnly is true
  // For now, we'll let the backend handle admin checks
  
  return children;
}

export default function App() {
  const handleLogout = () => {
    clearSession();
    window.location.href = '/login'; 
  };

  const showLegacyUI = import.meta.env.VITE_LEGACY_UI === 'true';

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/tools/github-health-checker" element={<GitHubHealthChecker />} />
        <Route path="/login" element={<Login />} />

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

        {/* Fallback: Redirect unknown routes to landing page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
