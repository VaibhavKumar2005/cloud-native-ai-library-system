import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import Dashboard from './Dashboard';
import AcademicDashboard from './AcademicDashboard';
import Monitoring from './Monitoring';
import Analytics from './Analytics';
import GitHubHealthChecker from './GitHubHealthChecker';
import Research from './pages/Research';
import LoginPage from './AuthPage';
import { clearSession, storeSession } from './lib/auth';

// ── Auth Guard: In DEMO_MODE, skip all auth checks ──────────
// For demo/testing, bypass the login requirement entirely
function ProtectedRoute({ children }) {
  // DEMO MODE: Always allow access, skip auth checks
  return children;
}

function MagicLinkLogin() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [message, setMessage] = useState('Verifying magic link...');

  useEffect(() => {
    const emailToken = searchParams.get('email_token');
    const apiBase = import.meta.env.VITE_API_URL || '';

    if (!emailToken) {
      navigate('/', { replace: true });
      return;
    }

    let active = true;
    const verify = async () => {
      try {
        const res = await fetch(`${apiBase}/api/auth/email/verify/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: emailToken }),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data?.detail || 'Magic link verification failed.');
        }

        if (data?.access && data?.refresh) {
          storeSession(data.access, data.refresh);
        }

        if (!active) return;
        setMessage('Login successful. Redirecting...');
        setTimeout(() => navigate('/research', { replace: true }), 500);
      } catch (err) {
        if (!active) return;
        setMessage(err?.message || 'Login failed. Please request a new magic link.');
        setTimeout(() => navigate('/', { replace: true }), 1200);
      }
    };

    verify();
    return () => { active = false; };
  }, [navigate, searchParams]);

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#040207', color: '#e2e8f0' }}>
      <div style={{ padding: '1rem 1.25rem', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, background: 'rgba(15,23,42,0.45)' }}>
        {message}
      </div>
    </div>
  );
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
        <Route path="/" element={<LoginPage />} />
        <Route path="/tools/github-health-checker" element={<GitHubHealthChecker />} />
        <Route path="/login" element={<MagicLinkLogin />} />

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
