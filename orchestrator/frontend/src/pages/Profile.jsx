import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Key, Lock, User, ArrowLeft, CheckCircle, Smartphone, Clock, RefreshCw } from 'lucide-react';
import authService from '../services/authService';

function Profile({ onLogout }) {
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);

  const user = {
    username: authService.getCurrentUser() || 'secops_admin',
    role: 'Security Administrator',
    trustScore: '98.5',
    mTLSCertSubject: 'CN=node-01.internal.ipsecvault.tech, O=IPsecVault, C=US',
    fingerprint: 'SHA256:4f8a9e21bc7d0e91a56f3458c091e2b489a712f5e3a8901c247de31fa0931298',
    lastAuth: 'Today at 09:42 UTC',
    ipAddress: '10.240.0.14',
    totpEnabled: true,
  };

  const handleCopyFingerprint = () => {
    navigator.clipboard.writeText(user.fingerprint);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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

        <span className="glass-badge glass-badge-green">
          <CheckCircle size={14} /> Zero Trust Active
        </span>
      </div>

      <div className="glass" style={{ padding: '2rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div
            style={{
              width: '72px',
              height: '72px',
              borderRadius: '20px',
              background: 'linear-gradient(135deg, rgba(0, 255, 102, 0.2), rgba(57, 255, 20, 0.25))',
              border: '1px solid rgba(0, 255, 102, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(0, 255, 102, 0.3)',
            }}
          >
            <Shield size={36} color="#00ff66" />
          </div>

          <div style={{ flex: 1, minWidth: '220px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: '1.6rem', fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>
                {user.username}
              </h1>
              <span className="glass-badge glass-badge-purple">{user.role}</span>
            </div>
            <p style={{ color: 'var(--text-secondary)', margin: '4px 0 0 0', fontSize: '0.9rem' }}>
              Zero Trust Mesh Node Operator · Authenticated via mTLS & TOTP
            </p>
          </div>

          <div
            className="glass"
            style={{
              padding: '0.75rem 1.25rem',
              textAlign: 'center',
              border: '1px solid rgba(0, 255, 157, 0.3)',
              background: 'rgba(0, 255, 157, 0.06)',
            }}
          >
            <div style={{ fontSize: '0.75rem', color: 'var(--accent-success)', textTransform: 'uppercase', fontWeight: 600 }}>
              Trust Score
            </div>
            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-success)' }}>
              {user.trustScore}
              <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>/100</span>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <div className="glass" style={{ padding: '1.5rem' }}>
          <div className="glass-header" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Key size={18} color="#00ff66" />
            <h3 style={{ fontSize: '1.05rem', margin: 0 }}>Cryptographic Identity</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.88rem' }}>
            <div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', marginBottom: '4px' }}>
                mTLS Certificate Subject
              </div>
              <code style={{ fontSize: '0.82rem', wordBreak: 'break-all', color: 'var(--accent-primary)' }}>
                {user.mTLSCertSubject}
              </code>
            </div>

            <div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', marginBottom: '4px' }}>
                SHA-256 Fingerprint
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <code
                  style={{
                    fontSize: '0.78rem',
                    wordBreak: 'break-all',
                    background: 'rgba(0, 0, 0, 0.3)',
                    padding: '6px 8px',
                    borderRadius: '6px',
                    flex: 1,
                  }}
                >
                  {user.fingerprint}
                </code>
                <button
                  className="btn btn-secondary glass"
                  onClick={handleCopyFingerprint}
                  style={{ padding: '6px 10px', fontSize: '0.75rem' }}
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="glass" style={{ padding: '1.5rem' }}>
          <div className="glass-header" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Lock size={18} color="#39ff14" />
            <h3 style={{ fontSize: '1.05rem', margin: 0 }}>Security Posture</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.88rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Two-Factor Authentication</span>
              <span className="glass-badge glass-badge-green">
                <Smartphone size={12} /> Active
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Session Source IP</span>
              <code style={{ color: 'var(--text-primary)' }}>{user.ipAddress}</code>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Last Cryptographic Handshake</span>
              <span style={{ color: 'var(--text-primary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <Clock size={14} color="var(--text-secondary)" /> {user.lastAuth}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Profile;
