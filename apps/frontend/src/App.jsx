import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './Dashboard';
import AcademicDashboard from './AcademicDashboard';
import Monitoring from './Monitoring';
import Analytics from './Analytics';
import Login from './Login';
import LandingPage from './LandingPage';
import { clearSession, isAuthenticated } from './lib/auth';

// ── Auth Guard: Redirects unauthenticated users to /login ──────────
function ProtectedRoute({ children }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const handleLogout = () => {
    clearSession();
    window.location.href = '/login'; 
  };

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />

        <Route path="/app" element={
          <ProtectedRoute>
            <Dashboard onLogout={handleLogout} />
          </ProtectedRoute>
        } />
        
        <Route path="/research" element={
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
        <Route path="/monitoring" element={<Navigate to="/app/monitoring" replace />} />
        <Route path="/analytics" element={<Navigate to="/app/analytics" replace />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
