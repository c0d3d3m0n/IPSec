import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings as SettingsIcon, Moon, Globe, Bell, Shield, Key, ArrowLeft, Save, RefreshCw } from 'lucide-react';

function Settings({ addToast }) {
  const navigate = useNavigate();
  const [darkMode, setDarkMode] = useState(true);
  const [language, setLanguage] = useState('en');
  const [autoRotateKeys, setAutoRotateKeys] = useState(true);
  const [heartbeatInterval, setHeartbeatInterval] = useState('30');
  const [enableAlerts, setEnableAlerts] = useState(true);
  const [saving, setSaving] = useState(false);

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      if (addToast) {
        addToast('Settings and Zero Trust preferences updated', 'success');
      }
    }, 400);
  };

  return (
    <div className="container" style={{ padding: '2.5rem 1.5rem', maxWidth: '860px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <button
          className="btn btn-secondary glass"
          onClick={() => navigate('/dashboard')}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
        >
          <ArrowLeft size={18} />
          Back to Dashboard
        </button>

        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
        >
          {saving ? <RefreshCw size={16} className="spin" /> : <Save size={16} />}
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      <div className="glass" style={{ padding: '2rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '1rem' }}>
          <div
            style={{
              padding: '12px',
              borderRadius: '14px',
              background: 'rgba(0, 255, 102, 0.1)',
              border: '1px solid rgba(0, 255, 102, 0.25)',
              display: 'flex',
            }}
          >
            <SettingsIcon size={24} color="#00ff66" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>System & Interface Settings</h1>
            <p style={{ color: 'var(--text-secondary)', margin: '2px 0 0 0', fontSize: '0.88rem' }}>
              Configure orchestrator node preferences, cryptographic rotation, and UI theme
            </p>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
        {/* Appearance & Localization */}
        <div className="glass" style={{ padding: '1.5rem' }}>
          <div className="glass-header" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Moon size={18} color="#39ff14" />
            <h3 style={{ fontSize: '1.05rem', margin: 0 }}>Appearance & Localization</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.92rem' }}>Dark Theme (OLED / High-Contrast)</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Ultra-dark canvas with cyan & purple glass overlays
                </div>
              </div>
              <input
                type="checkbox"
                checked={darkMode}
                onChange={() => setDarkMode(!darkMode)}
                style={{ width: '20px', height: '20px', cursor: 'pointer', accentColor: 'var(--accent-primary)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: '0.92rem', marginBottom: '6px' }}>
                System Language
              </label>
              <select
                className="glass-input"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                style={{ cursor: 'pointer' }}
              >
                <option value="en" style={{ background: '#090e0b', color: '#E4FCE9' }}>English (US)</option>
                <option value="de" style={{ background: '#090e0b', color: '#E4FCE9' }}>Deutsch (German)</option>
                <option value="fr" style={{ background: '#090e0b', color: '#E4FCE9' }}>Français (French)</option>
                <option value="ja" style={{ background: '#090e0b', color: '#E4FCE9' }}>日本語 (Japanese)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Security & Zero Trust Telemetry */}
        <div className="glass" style={{ padding: '1.5rem' }}>
          <div className="glass-header" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Shield size={18} color="#00ff66" />
            <h3 style={{ fontSize: '1.05rem', margin: 0 }}>Zero Trust Mesh Policy</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.92rem' }}>Automated Key Rotation</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Rotate IKEv2 / IPsec SAs every 3600 seconds
                </div>
              </div>
              <input
                type="checkbox"
                checked={autoRotateKeys}
                onChange={() => setAutoRotateKeys(!autoRotateKeys)}
                style={{ width: '20px', height: '20px', cursor: 'pointer', accentColor: 'var(--accent-success)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: '0.92rem', marginBottom: '6px' }}>
                Node Heartbeat Telemetry (Seconds)
              </label>
              <select
                className="glass-input"
                value={heartbeatInterval}
                onChange={(e) => setHeartbeatInterval(e.target.value)}
                style={{ cursor: 'pointer' }}
              >
                <option value="10" style={{ background: '#090e0b', color: '#E4FCE9' }}>10s (High Frequency)</option>
                <option value="30" style={{ background: '#090e0b', color: '#E4FCE9' }}>30s (Recommended)</option>
                <option value="60" style={{ background: '#090e0b', color: '#E4FCE9' }}>60s (Low Bandwidth)</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.92rem' }}>Security Incident Toasts</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Realtime notification on policy violations
                </div>
              </div>
              <input
                type="checkbox"
                checked={enableAlerts}
                onChange={() => setEnableAlerts(!enableAlerts)}
                style={{ width: '20px', height: '20px', cursor: 'pointer', accentColor: 'var(--accent-primary)' }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Settings;
