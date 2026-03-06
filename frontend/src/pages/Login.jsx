import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import useAuth from '../hooks/useAuth';

export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [needs2fa, setNeeds2fa] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [forgotMode, setForgotMode] = useState(false);
  const [forgotSent, setForgotSent] = useState(false);

  const SAFE_PATHS = ['/dashboard', '/clients', '/approvals', '/reconciliation',
    '/documents', '/employees', '/payroll', '/reports', '/tax-exports'];
  function getSafeRedirect() {
    const from = location.state?.from?.pathname;
    if (from && (SAFE_PATHS.includes(from) || from.startsWith('/clients/'))) {
      return from;
    }
    return '/dashboard';
  }

  if (isAuthenticated) {
    navigate(getSafeRedirect(), { replace: true });
    return null;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login(email, password, needs2fa ? totpCode : undefined);
      if (result?.requires_2fa) {
        setNeeds2fa(true);
        setLoading(false);
        return;
      }
      navigate(getSafeRedirect());
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.error ||
        'Login failed. Please check your credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleForgotPassword(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const API_BASE = import.meta.env.VITE_API_BASE || '';
      await fetch(`${API_BASE}/api/v1/auth/forgot-password?email=${encodeURIComponent(email)}`, {
        method: 'POST',
      });
      setForgotSent(true);
    } catch {
      setError('Failed to send reset email. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  if (forgotMode) {
    return (
      <div className="login-page">
        <div className="login-card">
          <h1 className="login-title">Reset Password</h1>
          <p className="login-subtitle">Enter your email to receive a reset link</p>

          {forgotSent ? (
            <div>
              <div className="alert alert--success">
                If an account with that email exists, a reset link has been sent.
              </div>
              <button
                className="btn btn--outline btn--full"
                style={{ marginTop: 12 }}
                onClick={() => { setForgotMode(false); setForgotSent(false); }}
              >
                Back to Sign In
              </button>
            </div>
          ) : (
            <form onSubmit={handleForgotPassword} className="login-form">
              {error && <div className="alert alert--error">{error}</div>}
              <label className="form-label" htmlFor="reset-email">Email</label>
              <input
                id="reset-email"
                className="form-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                placeholder="you@firm.com"
              />
              <button
                className={`btn btn--primary btn--full${loading ? ' btn--loading' : ''}`}
                type="submit"
                disabled={loading}
              >
                Send Reset Link
              </button>
              <button
                type="button"
                className="btn btn--outline btn--full"
                style={{ marginTop: 8 }}
                onClick={() => setForgotMode(false)}
              >
                Back to Sign In
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-title">755 Accounting</h1>
        <p className="login-subtitle">Accounting System</p>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="alert alert--error">{error}</div>}

          <label className="form-label" htmlFor="email">Email</label>
          <input
            id="email"
            className="form-input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
            autoFocus={!needs2fa}
            placeholder="you@firm.com"
            disabled={needs2fa}
          />

          <label className="form-label" htmlFor="password">Password</label>
          <input
            id="password"
            className="form-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            disabled={needs2fa}
          />

          {needs2fa && (
            <>
              <label className="form-label" htmlFor="totp">Authenticator Code</label>
              <input
                id="totp"
                className="form-input"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                autoComplete="one-time-code"
                required
                autoFocus
                placeholder="000000"
                style={{ letterSpacing: 8, fontSize: 20, textAlign: 'center' }}
              />
            </>
          )}

          <button
            className={`btn btn--primary btn--full${loading ? ' btn--loading' : ''}`}
            type="submit"
            disabled={loading}
          >
            {loading ? 'Signing in...' : needs2fa ? 'Verify & Sign In' : 'Sign in'}
          </button>

          <div style={{ textAlign: 'center', marginTop: 12 }}>
            <button
              type="button"
              onClick={() => setForgotMode(true)}
              style={{ background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', fontSize: 13, fontFamily: 'inherit' }}
            >
              Forgot password?
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
