import React, { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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

      if ((status === 422 || status === 401) && detail.includes('totp')) {
        setShowTotp(true);
        if (detail.includes('required')) {
          setError('TOTP verification is required to continue.');
          addToast('warning', 'Enter your TOTP code and submit again.');
        } else if (detail.includes('invalid')) {
          setError('Invalid TOTP code. Please try again.');
          addToast('error', 'Invalid TOTP code. Please try again.');
        } else {
          setError('TOTP verification failed.');
          addToast('error', 'TOTP verification failed.');
        }
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
      {/* Animated gradient orbs */}
      <div className="orb orb-teal" />
      <div className="orb orb-purple" />

      <motion.div
        className="login-card glass-surface"
        initial={{ opacity: 0, y: 30, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* Logo badge with pulse glow */}
        <div className="login-logo-wrap">
          <motion.div
            className="login-logo-badge glass-surface"
            animate={{ boxShadow: [
              '0 0 12px rgba(0, 255, 102, 0.35)',
              '0 0 28px rgba(0, 255, 102, 0.7)',
              '0 0 12px rgba(0, 255, 102, 0.35)',
            ]}}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          >
            <ShieldCheck size={28} />
          </motion.div>
        </div>

        <h1 className="login-title">IPsec Vault</h1>
        <p className="login-subtitle">Zero Trust Policy Management</p>

        <form onSubmit={handleSubmit} className="login-form">
          <motion.label
            className="field-wrap"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 }}
          >
            <span className="field-icon"><User size={16} /></span>
            <input
              className="input-field"
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
            />
          </motion.label>

          <motion.label
            className="field-wrap"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.25 }}
          >
            <span className="field-icon"><Lock size={16} /></span>
            <input
              className="input-field"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </motion.label>

          {/* TOTP field — animated slide-down */}
          <AnimatePresence>
            {showTotp && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
                style={{ overflow: 'hidden' }}
              >
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
                    autoComplete="one-time-code"
                  />
                </label>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error message */}
          <AnimatePresence>
            {error && (
              <motion.div
                className="error-panel glass-surface"
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.2 }}
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          <motion.button
            className="btn btn-primary login-btn"
            type="submit"
            disabled={loading}
            whileHover={{ scale: loading ? 1 : 1.02 }}
            whileTap={{ scale: loading ? 1 : 0.98 }}
          >
            {loading ? <span className="spinner" /> : null}
            <span>{submitLabel}</span>
          </motion.button>
        </form>
      </motion.div>

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default Login;
