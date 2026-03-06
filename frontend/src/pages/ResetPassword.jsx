import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      const API_BASE = import.meta.env.VITE_API_BASE || '';
      const res = await fetch(
        `${API_BASE}/api/v1/auth/reset-password`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token, new_password: password }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Reset failed');
      }
      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="login-page">
        <div className="login-card">
          <h1 className="login-title">Invalid Link</h1>
          <p className="login-subtitle">This password reset link is invalid or expired.</p>
          <button className="btn btn--primary btn--full" onClick={() => navigate('/login')}>
            Back to Sign In
          </button>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="login-page">
        <div className="login-card">
          <h1 className="login-title">Password Reset</h1>
          <div className="alert alert--success">Your password has been reset successfully.</div>
          <button className="btn btn--primary btn--full" onClick={() => navigate('/login')}>
            Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-title">Set New Password</h1>
        <p className="login-subtitle">Enter your new password below</p>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="alert alert--error">{error}</div>}

          <label className="form-label" htmlFor="new-password">New Password</label>
          <input
            id="new-password"
            className="form-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoFocus
          />

          <label className="form-label" htmlFor="confirm-password">Confirm Password</label>
          <input
            id="confirm-password"
            className="form-input"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            minLength={8}
          />

          <button
            className={`btn btn--primary btn--full${loading ? ' btn--loading' : ''}`}
            type="submit"
            disabled={loading}
          >
            Reset Password
          </button>
        </form>
      </div>
    </div>
  );
}
