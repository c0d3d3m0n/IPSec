import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, User } from 'lucide-react';
import ToastStack from '../components/ToastStack';

function MasterAdminLogin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  
  const [step, setStep] = useState('login'); // 'login' | 'totp' | 'setup_totp'
  const [setupData, setSetupData] = useState(null);
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [toasts, setToasts] = useState([]);
  
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
  
  const navigate = useNavigate();

  const getBasicAuthHeader = () => {
    return 'Basic ' + btoa(`${username}:${password}`);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const authHeader = getBasicAuthHeader();
      const res = await fetch('/api/_master_admin/totp/status', {
        headers: {
          'Authorization': authHeader
        }
      });
      
      if (!res.ok) {
        throw new Error('Invalid master admin credentials');
      }

      const data = await res.json();
      
      if (data.totp_enabled) {
        setStep('totp');
      } else {
        // Fetch setup data
        const setupRes = await fetch('/api/_master_admin/totp/setup', {
          method: 'POST',
          headers: { 'Authorization': authHeader }
        });
        const sData = await setupRes.json();
        setSetupData(sData);
        setStep('setup_totp');
      }

    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleTotpSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      const authHeader = getBasicAuthHeader();
      
      if (step === 'setup_totp') {
        const res = await fetch('/api/_master_admin/totp/verify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authHeader
          },
          body: JSON.stringify({ code: totpCode, secret: setupData.secret })
        });
        
        if (!res.ok) {
          throw new Error('Invalid TOTP code during setup');
        }
      } else {
        // Just verify standard TOTP header
        const res = await fetch('/api/_master_admin/tenants/', {
          headers: {
            'Authorization': authHeader,
            'X-TOTP-Code': totpCode
          }
        });
        
        if (res.status === 401 || res.status === 403) {
          throw new Error('Invalid TOTP code');
        }
      }

      // Success
      localStorage.setItem('master_admin_username', username);
      localStorage.setItem('master_admin_password', password);
      localStorage.setItem('master_admin_totp', totpCode);
      
      navigate('/_master_admin/dashboard');

    } catch (err) {
      setError(err.message || 'Verification failed');
      addToast('error', err.message || 'Verification failed');
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

        <h1 className="login-title">Master Admin Portal</h1>
        <p className="login-subtitle">System & Tenant Orchestration</p>

        {step === 'login' && (
          <form onSubmit={handleLogin} className="login-form">
            <label className="field-wrap">
              <span className="field-icon"><User size={16} /></span>
              <input
                className="input-field"
                type="text"
                placeholder="Master Admin Username"
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

            {error ? <div className="error-panel glass-surface">{error}</div> : null}

            <button className="btn btn-primary login-btn" type="submit" disabled={loading}>
              {loading ? <span className="spinner" /> : null}
              <span>Sign In</span>
            </button>
          </form>
        )}

        {step === 'setup_totp' && (
          <form onSubmit={handleTotpSubmit} className="login-form">
            <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
              <p style={{ fontSize: '0.85rem', opacity: 0.8, marginBottom: '1rem' }}>
                First time login requires setting up Two-Factor Authentication. Scan this QR code with Google Authenticator or Authy.
              </p>
              {setupData?.qr_base64 && (
                <img 
                  src={`data:image/png;base64,${setupData.qr_base64}`} 
                  alt="TOTP QR Code" 
                  style={{ margin: '0 auto', border: '4px solid white', borderRadius: '0.5rem', marginBottom: '1rem' }} 
                />
              )}
              <p style={{ fontSize: '0.75rem', fontFamily: 'monospace', background: 'rgba(255,255,255,0.1)', padding: '0.5rem', borderRadius: '0.25rem', userSelect: 'all' }}>
                {setupData?.secret}
              </p>
            </div>
            
            <label className="field-wrap">
              <span className="field-icon"><ShieldCheck size={16} /></span>
              <input
                className="input-field"
                style={{ textAlign: 'center', letterSpacing: '0.25em', fontSize: '1.25rem' }}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                placeholder="000000"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                maxLength={6}
                required
                autoFocus
              />
            </label>
            
            {error ? <div className="error-panel glass-surface">{error}</div> : null}

            <button className="btn btn-primary login-btn" type="submit" disabled={loading}>
              {loading ? <span className="spinner" /> : null}
              <span>Verify & Complete Setup</span>
            </button>
          </form>
        )}

        {step === 'totp' && (
          <form onSubmit={handleTotpSubmit} className="login-form">
            <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
              <p style={{ fontSize: '0.9rem', opacity: 0.8 }}>
                Enter your Authenticator Code
              </p>
            </div>
            
            <label className="field-wrap">
              <span className="field-icon"><ShieldCheck size={16} /></span>
              <input
                className="input-field"
                style={{ textAlign: 'center', letterSpacing: '0.25em', fontSize: '1.25rem' }}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                placeholder="000000"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                maxLength={6}
                required
                autoFocus
              />
            </label>
            
            {error ? <div className="error-panel glass-surface">{error}</div> : null}

            <button className="btn btn-primary login-btn" type="submit" disabled={loading}>
              {loading ? <span className="spinner" /> : null}
              <span>Verify</span>
            </button>
          </form>
        )}

      </div>
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default MasterAdminLogin;
