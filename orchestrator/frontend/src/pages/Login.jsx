import React, { useState } from 'react';
import axios from 'axios';
import { Lock, User, ShieldCheck } from 'lucide-react';

function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);

      const apiBaseUrl = import.meta.env.VITE_API_URL || '';
      const response = await axios.post(`${apiBaseUrl}/api/auth/login`, formData);
      onLogin(response.data.access_token);
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative'
    }}>
      <div className="glow" style={{ top: '20%', left: '25%', width: '400px', height: '400px', background: 'var(--primary)' }} />
      <div className="glow" style={{ bottom: '20%', right: '25%', width: '350px', height: '350px', background: 'var(--accent)' }} />

      <div className="glass-card" style={{ padding: '3rem', width: '100%', maxWidth: '450px' }}>
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div style={{
            display: 'inline-flex',
            padding: '1rem',
            background: 'rgba(99, 102, 241, 0.1)',
            borderRadius: '16px',
            marginBottom: '1rem',
            color: 'var(--primary)'
          }}>
            <ShieldCheck size={40} />
          </div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Admin Access</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Welcome back to the Unified Orchestrator</p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <div style={{ position: 'relative' }}>
              <User size={18} style={{ position: 'absolute', left: '16px', top: '16px', color: 'var(--text-secondary)' }} />
              <input
                type="text"
                placeholder="Username"
                className="input-field"
                style={{ paddingLeft: '45px' }}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <div style={{ position: 'relative' }}>
              <Lock size={18} style={{ position: 'absolute', left: '16px', top: '16px', color: 'var(--text-secondary)' }} />
              <input
                type="password"
                placeholder="Password"
                className="input-field"
                style={{ paddingLeft: '45px' }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          {error && <div style={{ color: 'var(--danger)', fontSize: '0.9rem', textAlign: 'center' }}>{error}</div>}

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: '0.5rem' }}>
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Login;
