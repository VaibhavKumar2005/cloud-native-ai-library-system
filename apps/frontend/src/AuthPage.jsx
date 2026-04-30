import React from 'react';
import { useNavigate } from 'react-router-dom';
import EmailAuthForm from './components/EmailAuthForm';
import './styles/AuthPages.css';

export default function LoginPage() {
  const navigate = useNavigate();
  const demoMode = import.meta.env.VITE_DEMO_MODE === 'true';

  return (
    <div className="login-container">
      <div className="login-panel login-panel-left">
        <div className="login-branding">
          <div className="logo-circle">
            <span className="logo-icon">VR</span>
          </div>
          <h1>VeriRAG</h1>
          <p className="tagline">Grounded answers for research workflows</p>
        </div>
      </div>

      <div className="login-panel login-panel-right">
        <div className="login-form-wrapper">
          <h2>Sign In</h2>
          <p className="login-subtitle">Use your email to receive a secure magic link</p>

          <EmailAuthForm />

          <div className="divider">or</div>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => navigate('/research')}
            disabled={!demoMode}
            title={demoMode ? 'Enter demo workspace' : 'Enable VITE_DEMO_MODE=true to use demo entry'}
          >
            {demoMode ? 'Enter Demo Workspace' : 'Demo Mode Disabled'}
          </button>
        </div>
      </div>
    </div>
  );
}
