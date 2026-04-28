import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/AuthPages.css';

export default function LoginPage() {
  const apiBase = import.meta.env.VITE_API_URL || '';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${apiBase}/api/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.token);
        navigate('/research');
      } else {
        setError('Invalid email or password');
      }
    } catch {
      setError('Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoMode = () => {
    navigate('/research');
  };

  return (
    <div className="login-container">
      {/* Left Panel - Branding & Features */}
      <div className="login-panel login-panel-left">
        <div className="login-branding">
          <div className="logo-circle">
            <span className="logo-icon">📚</span>
          </div>
          <h1>VeriRAG</h1>
          <p className="tagline">Academic Research Intelligence</p>
        </div>

        <div className="features-list">
          <div className="feature-item">
            <span className="feature-icon">🔍</span>
            <div>
              <h3>Vector Search</h3>
              <p>Find papers by semantic similarity</p>
            </div>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🤖</span>
            <div>
              <h3>AI-Powered Answers</h3>
              <p>Get instant summaries from your research</p>
            </div>
          </div>
          <div className="feature-item">
            <span className="feature-icon">✨</span>
            <div>
              <h3>Citation Tracking</h3>
              <p>Stay connected to your sources</p>
            </div>
          </div>
        </div>

        <div className="footer-text">
          <p>Powered by Azure OpenAI + PostgreSQL pgvector</p>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="login-panel login-panel-right">
        <div className="login-form-wrapper">
          <h2>Welcome Back</h2>
          <p className="login-subtitle">Sign in to continue</p>

          {error && <div className="error-banner">{error}</div>}

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="email">Email Address</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="divider">or</div>

          <button onClick={handleDemoMode} className="btn btn-secondary">
            Try Demo Mode →
          </button>

          <p className="signup-link">
            Don't have an account? <a href="/signup">Sign up</a>
          </p>
        </div>
      </div>
    </div>
  );
}
