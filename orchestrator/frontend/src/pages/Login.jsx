import React, { useMemo, useState } from 'react';
import { ShieldCheck, Lock, User } from 'lucide-react';
import authService from '../services/authService';
import ToastStack from '../components/ToastStack';

function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [showTotp, setShowTotp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [toasts, setToasts] = useState([]);

  const submitLabel = useMemo(() => (loading ? 'Authenticating...' : 'Sign In'), [loading]);

  const addToast = (type, message) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.login(username.trim(), password, showTotp ? totpCode.trim() : undefined);
      onLogin();
    } catch (err) {
      const status = err?.response?.status;
      const detail = String(err?.response?.data?.detail || '').toLowerCase();

      if (status === 422 && detail.includes('totp')) {
        setShowTotp(true);
        setError('TOTP verification is required to continue.');
        addToast('warning', 'Enter your TOTP code and submit again.');
      } else if (status === 401) {
        setError('Invalid credentials');
        addToast('error', 'Invalid credentials');
      } else if (status === 500) {
        setError('Server error - check backend status');
        addToast('error', 'Server error - check backend status');
      } else {
        setError(err?.response?.data?.detail || 'Login failed. Try again.');
        addToast('error', err?.response?.data?.detail || 'Login failed. Try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="orb orb-purple" />
      <div className="orb orb-teal" />

      <div className="login-card glass-surface">
        <div className="login-logo-wrap">
          <div className="login-logo-badge glass-surface">
            <ShieldCheck size={28} />
          </div>
        </div>

        <h1 className="login-title">IPsec Orchestrator</h1>
        <p className="login-subtitle">Zero Trust Policy Management</p>

        <form onSubmit={handleSubmit} className="login-form">
          <label className="field-wrap">
            <span className="field-icon"><User size={16} /></span>
            <input
              className="input-field"
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>

          <label className="field-wrap">
            <span className="field-icon"><Lock size={16} /></span>
            <input
              className="input-field"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          <div className={`totp-collapse ${showTotp ? 'open' : ''}`}>
            <label className="field-wrap">
              <span className="field-icon"><ShieldCheck size={16} /></span>
              <input
                className="input-field"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                placeholder="TOTP Code"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
              />
            </label>
          </div>

          {error ? <div className="error-panel glass-surface">{error}</div> : null}

          <button className="btn btn-primary login-btn" type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : null}
            <span>{submitLabel}</span>
          </button>
        </form>
      </div>

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default Login;
